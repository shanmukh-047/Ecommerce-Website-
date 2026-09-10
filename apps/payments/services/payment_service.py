import logging
import secrets
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from apps.inventory.models import ReservationStatus, StockReservation
from apps.orders.models import Order, OrderStatus
from apps.orders.services import OrderStateMachine
from apps.payments.exceptions import PaymentConflict, PaymentVerificationError
from apps.payments.gateways import get_payment_gateway
from apps.payments.models import (
    Payment,
    PaymentAttempt,
    PaymentGateway,
    PaymentMethod,
    PaymentStatus,
)

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Authoritative payment service orchestrating payment initiation,
    cryptographic verification, order status transitions, and attempt logging.
    """

    PAYMENT_NUMBER_CHARSET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"

    @classmethod
    def generate_payment_number(cls) -> str:
        date_str = timezone.now().strftime("%Y%m%d")
        for _ in range(5):
            suffix = "".join(secrets.choice(cls.PAYMENT_NUMBER_CHARSET) for _ in range(5))
            candidate = f"PAY-{date_str}-{suffix}"
            if not Payment.objects.filter(payment_number=candidate).exists():
                return candidate
        return f"PAY-{date_str}-{uuid.uuid4().hex[:8].upper()}"

    @classmethod
    @transaction.atomic
    def initiate_payment(
        cls,
        order: Order,
        user,
        gateway: str = PaymentGateway.RAZORPAY,
    ) -> Tuple[Payment, Dict[str, Any]]:
        """
        Initiates a payment for an order in PENDING_PAYMENT status with active reservations.
        Returns the Payment entity and the gateway configuration payload.
        """
        if not user or not user.is_authenticated:
            raise PaymentConflict("Authentication required to initiate payment.")

        # IDOR protection: only the order owner or staff can initiate payment
        if order.user != user and not (user.is_staff or getattr(user, "is_manager", False)):
            raise PaymentConflict("You do not have permission to pay for this order.")

        # Order must be in PENDING_PAYMENT
        if order.order_status != OrderStatus.PENDING_PAYMENT:
            raise PaymentConflict(f"Order in status '{order.order_status}' cannot be paid.")

        # Verify active stock reservations have not expired
        active_reservations = StockReservation.objects.filter(
            reference_type="ORDER",
            reference_id=order.id,
            status=ReservationStatus.ACTIVE,
        )
        if not active_reservations.exists():
            raise PaymentConflict("No active stock reservations found for this order.")

        now = timezone.now()
        if any(r.expires_at <= now for r in active_reservations):
            raise PaymentConflict(
                "Stock reservations for this order have expired. Please place a new order."
            )

        # Re-use existing pending payment for this order if one already exists
        existing_payment = (
            Payment.objects.select_for_update()
            .filter(order=order, status=PaymentStatus.PENDING, gateway=gateway)
            .first()
        )
        if existing_payment and existing_payment.gateway_order_id:
            gateway_data = existing_payment.gateway_response or {}
            if not gateway_data:
                gateway_data = {
                    "id": existing_payment.gateway_order_id,
                    "amount": int(Decimal(str(existing_payment.amount)) * 100),
                    "currency": existing_payment.currency,
                }
            return existing_payment, gateway_data

        # Initialize with Gateway
        adapter = get_payment_gateway(gateway)
        receipt = order.order_number
        gateway_order = adapter.create_order(
            amount=order.grand_total,
            currency=order.currency,
            receipt=receipt,
            notes={"order_id": str(order.id), "order_number": order.order_number},
        )

        payment_number = cls.generate_payment_number()
        payment = Payment.objects.create(
            payment_number=payment_number,
            order=order,
            user=order.user,
            status=PaymentStatus.PENDING,
            gateway=gateway,
            gateway_order_id=gateway_order.get("id", ""),
            amount=order.grand_total,
            currency=order.currency,
            gateway_response=gateway_order,
        )

        cls.record_payment_attempt(
            payment=payment,
            status=PaymentStatus.PENDING,
            raw_response=gateway_order,
        )

        return payment, gateway_order

    @classmethod
    def verify_and_capture_payment(
        cls,
        order_id,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        user=None,
        payment_method: str = PaymentMethod.RAZORPAY,
    ) -> Payment:
        """
        Cryptographically verifies the payment signature, locks order and payment records,
        atomically transitions the order to CONFIRMED (consuming reservations),
        and marks the payment CAPTURED.
        """
        # 1. Fetch order and validate ownership
        order = Order.objects.filter(pk=order_id).first()
        if not order:
            raise PaymentConflict("Order was not found.")

        if (
            user
            and order.user != user
            and not (user.is_staff or getattr(user, "is_manager", False))
        ):
            raise PaymentConflict("You do not have permission to verify payment for this order.")

        # 2. Fetch payment
        payment = (
            Payment.objects.filter(order=order, gateway_order_id=razorpay_order_id).first()
            or Payment.objects.filter(order=order).order_by("-created_at").first()
        )
        if not payment:
            raise PaymentConflict("No payment record was found for this order.")

        # 3. Idempotency Check: if already captured and confirmed, return safely
        if payment.status == PaymentStatus.CAPTURED and order.order_status == OrderStatus.CONFIRMED:
            return payment

        # 4. Order must be in PENDING_PAYMENT
        if order.order_status != OrderStatus.PENDING_PAYMENT:
            raise PaymentConflict(
                f"Cannot capture payment. Order is currently in '{order.order_status}' status."
            )

        # 5. Cryptographic signature validation
        adapter = get_payment_gateway(payment.gateway)
        valid = adapter.verify_payment_signature(
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
        )
        if not valid:
            cls.record_payment_attempt(
                payment=payment,
                gateway_payment_id=razorpay_payment_id,
                status=PaymentStatus.FAILED,
                error_code="SIGNATURE_VERIFICATION_FAILED",
                error_description="Razorpay HMAC signature verification failed.",
            )
            raise PaymentVerificationError("Invalid payment signature.")

        # 6. Atomic order confirmation, stock reservation consumption, and payment capture
        with transaction.atomic():
            locked_order = Order.objects.select_for_update().filter(pk=order.id).first()
            locked_payment = Payment.objects.select_for_update().filter(pk=payment.id).first()

            if (
                locked_payment.status == PaymentStatus.CAPTURED
                and locked_order.order_status == OrderStatus.CONFIRMED
            ):
                return locked_payment

            active_reservations = StockReservation.objects.filter(
                reference_type="ORDER",
                reference_id=locked_order.id,
                status=ReservationStatus.ACTIVE,
            )
            if not active_reservations.exists():
                raise PaymentConflict("No active stock reservations found for this order.")

            now = timezone.now()
            if any(r.expires_at <= now for r in active_reservations):
                raise PaymentConflict("Stock reservations have expired. Order cannot be confirmed.")

            # Transition order to CONFIRMED via OrderStateMachine
            OrderStateMachine.transition_status(
                order=locked_order,
                to_status=OrderStatus.CONFIRMED,
                actor=user or locked_order.user,
                notes=f"Payment captured via {locked_payment.gateway} (Payment ID: {razorpay_payment_id}).",
            )

            # Update payment to CAPTURED
            locked_payment.status = PaymentStatus.CAPTURED
            locked_payment.gateway_payment_id = razorpay_payment_id
            locked_payment.gateway_signature = razorpay_signature
            locked_payment.payment_method = payment_method or PaymentMethod.RAZORPAY
            locked_payment.captured_at = now
            locked_payment.save(
                update_fields=[
                    "status",
                    "gateway_payment_id",
                    "gateway_signature",
                    "payment_method",
                    "captured_at",
                    "updated_at",
                ]
            )

            # Record captured attempt
            cls.record_payment_attempt(
                payment=locked_payment,
                gateway_payment_id=razorpay_payment_id,
                status=PaymentStatus.CAPTURED,
            )

            return locked_payment

    @classmethod
    @transaction.atomic
    def submit_utr(
        cls,
        order_id,
        utr_number: str,
        user,
        payment_screenshot=None,
    ) -> Payment:
        """
        Customer submits a 12-digit UPI UTR / RRN transaction number for manual verification.
        Order must be in PENDING_PAYMENT.
        Transitions or creates Payment in PENDING_VERIFICATION status.
        """
        order = Order.objects.filter(pk=order_id).first()
        if not order:
            raise PaymentConflict("Order was not found.")

        if (
            user
            and order.user != user
            and not (user.is_staff or getattr(user, "is_manager", False))
        ):
            raise PaymentConflict("You do not have permission to submit payment for this order.")

        if order.order_status != OrderStatus.PENDING_PAYMENT:
            raise PaymentConflict(
                f"Cannot submit payment for order in '{order.order_status}' status."
            )

        active_reservations = StockReservation.objects.filter(
            reference_type="ORDER",
            reference_id=order.id,
            status=ReservationStatus.ACTIVE,
        )
        if not active_reservations.exists():
            raise PaymentConflict("No active stock reservations found for this order.")

        now = timezone.now()
        if any(r.expires_at <= now for r in active_reservations):
            raise PaymentConflict(
                "Stock reservations have expired. Please place a new order."
            )

        # Find or create Payment record
        payment = (
            Payment.objects.select_for_update()
            .filter(order=order, status__in=[PaymentStatus.PENDING, PaymentStatus.PENDING_VERIFICATION])
            .first()
        )

        if not payment:
            payment_number = cls.generate_payment_number()
            payment = Payment.objects.create(
                payment_number=payment_number,
                order=order,
                user=order.user,
                status=PaymentStatus.PENDING_VERIFICATION,
                gateway=PaymentGateway.PHONEPE_QR,
                payment_method=PaymentMethod.UPI,
                gateway_payment_id=utr_number,
                utr_number=utr_number,
                payment_screenshot=payment_screenshot,
                amount=order.grand_total,
                currency=order.currency,
            )
        else:
            payment.status = PaymentStatus.PENDING_VERIFICATION
            payment.gateway = PaymentGateway.PHONEPE_QR
            payment.payment_method = PaymentMethod.UPI
            payment.gateway_payment_id = utr_number
            payment.utr_number = utr_number
            if payment_screenshot:
                payment.payment_screenshot = payment_screenshot
            payment.save(
                update_fields=[
                    "status",
                    "gateway",
                    "payment_method",
                    "gateway_payment_id",
                    "utr_number",
                    "payment_screenshot",
                    "updated_at",
                ]
            )

        cls.record_payment_attempt(
            payment=payment,
            gateway_payment_id=utr_number,
            status=PaymentStatus.PENDING_VERIFICATION,
            error_description=f"Customer submitted UTR: {utr_number}",
        )

        return payment

    @classmethod
    def verify_manual_payment(
        cls,
        payment_id,
        actor,
        notes: str = "",
    ) -> Payment:
        """
        Admin/Staff manual verification of a submitted UPI payment.
        Atomically marks payment CAPTURED, confirms order, and logs actor note.
        """
        with transaction.atomic():
            payment = (
                Payment.objects.select_for_update()
                .select_related("order", "user")
                .filter(pk=payment_id)
                .first()
            )
            if not payment:
                raise PaymentConflict("Payment record not found.")

            if payment.status == PaymentStatus.CAPTURED:
                return payment

            if payment.status != PaymentStatus.PENDING_VERIFICATION:
                raise PaymentConflict(
                    f"Cannot verify payment in '{payment.status}' status. Must be PENDING_VERIFICATION."
                )

            order = Order.objects.select_for_update().filter(pk=payment.order_id).first()
            if not order:
                raise PaymentConflict("Order record not found.")

            if order.order_status != OrderStatus.PENDING_PAYMENT:
                raise PaymentConflict(f"Order is in '{order.order_status}' status; cannot confirm.")

            # Transition order to CONFIRMED
            verification_note = (
                notes or f"Manual UPI payment verified by {actor.email} (UTR: {payment.utr_number})"
            )
            OrderStateMachine.transition_status(
                order=order,
                to_status=OrderStatus.CONFIRMED,
                actor=actor,
                notes=verification_note,
            )

            # Update payment
            now = timezone.now()
            payment.status = PaymentStatus.CAPTURED
            payment.captured_at = now
            payment.authorized_at = now
            payment.save(
                update_fields=[
                    "status",
                    "captured_at",
                    "authorized_at",
                    "updated_at",
                ]
            )

            cls.record_payment_attempt(
                payment=payment,
                gateway_payment_id=payment.utr_number,
                status=PaymentStatus.CAPTURED,
                error_description=f"Verified by admin {actor.email}",
            )

            return payment

    @classmethod
    def reject_manual_payment(
        cls,
        payment_id,
        actor,
        reason: str,
    ) -> Payment:
        """
        Admin/Staff marks an unverified manual payment as FAILED.
        Order remains in PENDING_PAYMENT so the customer can re-enter their valid UTR.
        """
        with transaction.atomic():
            payment = Payment.objects.select_for_update().filter(pk=payment_id).first()
            if not payment:
                raise PaymentConflict("Payment record not found.")

            if payment.status == PaymentStatus.CAPTURED:
                raise PaymentConflict("Cannot reject an already captured payment.")

            payment.status = PaymentStatus.FAILED
            payment.failure_reason = reason
            payment.failed_at = timezone.now()
            payment.save(
                update_fields=[
                    "status",
                    "failure_reason",
                    "failed_at",
                    "updated_at",
                ]
            )

            cls.record_payment_attempt(
                payment=payment,
                gateway_payment_id=payment.utr_number,
                status=PaymentStatus.FAILED,
                error_code="MANUAL_VERIFICATION_REJECTED",
                error_description=f"Rejected by {actor.email}: {reason}",
            )

            return payment

    @classmethod
    def record_payment_attempt(
        cls,
        payment: Payment,
        gateway_payment_id: str = "",
        status: str = PaymentStatus.PENDING,
        error_code: str = "",
        error_description: str = "",
        raw_response: Optional[Dict[str, Any]] = None,
    ) -> PaymentAttempt:
        """
        Appends an attempt log record for tracking retries without corrupting main payment status.
        """
        attempt_number = payment.attempts.count() + 1
        return PaymentAttempt.objects.create(
            payment=payment,
            attempt_number=attempt_number,
            gateway_payment_id=gateway_payment_id,
            status=status,
            error_code=error_code,
            error_description=error_description,
            raw_response=raw_response or {},
        )

    @classmethod
    def refund_payment(
        cls,
        payment: Payment,
        amount: Optional[Decimal] = None,
        reason: str = "",
        actor=None,
    ) -> Payment:
        """
        Executes a gateway refund for a CAPTURED or PARTIALLY_REFUNDED payment
        using universal lock hierarchy: Order -> Payment.
        Accumulates amount_refunded, transitions status to PARTIALLY_REFUNDED
        or REFUNDED, records refund_transaction_id, and refunded_at timestamp.
        """
        if payment.status not in (
            PaymentStatus.CAPTURED,
            PaymentStatus.PARTIALLY_REFUNDED,
            PaymentStatus.REFUNDED,
        ):
            raise PaymentConflict(
                f"Cannot refund payment with status '{payment.status}'. "
                "Only CAPTURED or PARTIALLY_REFUNDED payments can be refunded."
            )

        with transaction.atomic():
            # Universal lock ordering: Order -> Payment
            locked_order = Order.objects.select_for_update().get(id=payment.order_id)
            locked_payment = Payment.objects.select_for_update().get(id=payment.id)

            existing_refunded = locked_payment.amount_refunded or Decimal("0.00")
            max_refundable = locked_payment.amount - existing_refunded

            if max_refundable <= Decimal("0.00"):
                if locked_payment.status != PaymentStatus.REFUNDED:
                    locked_payment.status = PaymentStatus.REFUNDED
                    locked_payment.save(update_fields=["status", "updated_at"])
                # Idempotent return for fully refunded payment
                return locked_payment

            refund_amount = amount if amount is not None else max_refundable
            if refund_amount <= Decimal("0.00"):
                raise PaymentConflict("Refund amount must be greater than 0.")

            if refund_amount > max_refundable:
                raise PaymentConflict(
                    f"Refund amount {refund_amount} exceeds maximum eligible remaining refund {max_refundable} "
                    f"(Paid: {locked_payment.amount}, Already refunded: {existing_refunded})."
                )

            # Gateway refund
            adapter = get_payment_gateway(locked_payment.gateway)
            gateway_refund_id = ""
            if (
                locked_payment.gateway == PaymentGateway.RAZORPAY
                and locked_payment.gateway_payment_id
            ):
                try:
                    refund_res = adapter.refund_payment(
                        gateway_payment_id=locked_payment.gateway_payment_id,
                        amount=refund_amount,
                        notes={
                            "reason": reason,
                            "order_number": locked_order.order_number,
                        },
                    )
                    gateway_refund_id = refund_res.get("id", "")
                except Exception as exc:
                    logger.exception(
                        "Gateway refund failed for payment %s: %s",
                        locked_payment.payment_number,
                        exc,
                    )
                    raise PaymentConflict(f"Gateway refund failed: {exc}") from exc
            else:
                gateway_refund_id = f"rfnd_manual_{uuid.uuid4().hex[:12]}"

            now = timezone.now()
            new_total_refunded = existing_refunded + refund_amount
            if new_total_refunded >= locked_payment.amount:
                target_status = PaymentStatus.REFUNDED
            else:
                target_status = PaymentStatus.PARTIALLY_REFUNDED

            locked_payment.status = target_status
            locked_payment.refund_transaction_id = gateway_refund_id
            locked_payment.amount_refunded = new_total_refunded
            locked_payment.refunded_at = now
            locked_payment.save(
                update_fields=[
                    "status",
                    "refund_transaction_id",
                    "amount_refunded",
                    "refunded_at",
                    "updated_at",
                ]
            )

            cls.record_payment_attempt(
                payment=locked_payment,
                gateway_payment_id=gateway_refund_id,
                status=target_status,
                raw_response={
                    "reason": reason,
                    "amount": str(refund_amount),
                    "total_refunded": str(new_total_refunded),
                    "actor": str(actor) if actor else None,
                },
            )

            # Transition order only if full refund was achieved and transition is valid
            if new_total_refunded >= locked_payment.amount:
                allowed = OrderStateMachine.ALLOWED_TRANSITIONS.get(locked_order.order_status, [])
                if OrderStatus.REFUNDED in allowed:
                    try:
                        OrderStateMachine.transition_status(
                            order=locked_order,
                            to_status=OrderStatus.REFUNDED,
                            actor=actor,
                            notes=reason
                            or f"Order fully refunded ({locked_payment.payment_number}).",
                        )
                    except Exception as exc:
                        logger.warning("Failed order transition to REFUNDED: %s", exc)

            # Dispatch notification on commit
            transaction.on_commit(lambda: cls._dispatch_refund_notification(locked_order.id))

            # Synchronize caller in-memory reference
            payment.status = locked_payment.status
            payment.amount_refunded = locked_payment.amount_refunded
            payment.refund_transaction_id = locked_payment.refund_transaction_id
            return locked_payment

    @classmethod
    def _dispatch_refund_notification(cls, order_id: Any) -> None:
        """
        Dispatches background notification task upon transaction commit.
        """
        try:
            from apps.notifications.models import NotificationEvent
            from apps.notifications.tasks import send_order_notifications_task

            send_order_notifications_task.delay(
                str(order_id),
                NotificationEvent.REFUND_PROCESSED,
            )
        except Exception as exc:
            logger.exception(
                "Failed to dispatch refund notification for order %s: %s",
                order_id,
                exc,
            )

    @classmethod
    @transaction.atomic
    def create_cod_payment(
        cls,
        order: Order,
        user,
    ) -> Payment:
        """
        Creates a Cash on Delivery (COD) payment record in PENDING status,
        and transitions the order to CONFIRMED (consuming inventory reservations).
        """
        if not user or not user.is_authenticated:
            raise PaymentConflict("Authentication required to select Cash on Delivery.")

        if order.user != user and not (user.is_staff or getattr(user, "is_manager", False)):
            raise PaymentConflict("You do not have permission to place this COD order.")

        if order.order_status != OrderStatus.PENDING_PAYMENT:
            raise PaymentConflict(f"Order in status '{order.order_status}' cannot select COD.")

        # Re-use existing COD payment if one was already initialized
        existing = (
            Payment.objects.select_for_update()
            .filter(order=order, payment_method=PaymentMethod.COD)
            .first()
        )
        if existing:
            return existing

        payment_number = cls.generate_payment_number()
        payment = Payment.objects.create(
            payment_number=payment_number,
            order=order,
            user=order.user,
            status=PaymentStatus.PENDING,
            gateway=PaymentGateway.COD,
            payment_method=PaymentMethod.COD,
            amount=order.grand_total,
            currency=order.currency,
        )

        cls.record_payment_attempt(
            payment=payment,
            status=PaymentStatus.PENDING,
            raw_response={"message": "Order placed with Cash on Delivery."},
        )

        # Transition order to CONFIRMED
        OrderStateMachine.transition_status(
            order=order,
            to_status=OrderStatus.CONFIRMED,
            actor=user,
            notes="Order placed via Cash on Delivery. Payment pending upon delivery.",
        )

        return payment

    @classmethod
    @transaction.atomic
    def mark_cod_collected(
        cls,
        payment_id,
        staff_user,
    ) -> Payment:
        """
        Authorized staff endpoint to confirm cash payment has been collected upon delivery.
        Transitions payment status from PENDING to CAPTURED.
        """
        if not staff_user or not (staff_user.is_staff or staff_user.is_superuser):
            raise PaymentConflict("Only authorized staff can mark COD payments collected.")

        payment = Payment.objects.select_for_update().filter(pk=payment_id).first()
        if not payment:
            raise PaymentConflict("Payment record not found.")

        if payment.payment_method != PaymentMethod.COD and payment.gateway != PaymentGateway.COD:
            raise PaymentConflict("Only Cash on Delivery payments can be marked collected.")

        if payment.status == PaymentStatus.CAPTURED:
            return payment  # Idempotent

        if payment.status != PaymentStatus.PENDING:
            raise PaymentConflict(f"Cannot mark COD payment with status '{payment.status}' as collected.")

        payment.status = PaymentStatus.CAPTURED
        payment.captured_at = timezone.now()
        payment.save(update_fields=["status", "captured_at", "updated_at"])

        cls.record_payment_attempt(
            payment=payment,
            status=PaymentStatus.CAPTURED,
            raw_response={"message": f"COD payment collected by staff {staff_user.email}."},
        )

        return payment
