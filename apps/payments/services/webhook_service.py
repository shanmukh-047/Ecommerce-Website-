import hashlib
import json
import logging
from decimal import Decimal
from typing import Any, Dict

from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order, OrderStatus
from apps.orders.services import OrderStateMachine
from apps.payments.exceptions import PaymentVerificationError
from apps.payments.gateways import get_payment_gateway
from apps.payments.models import (
    Payment,
    PaymentAttempt,
    PaymentGateway,
    PaymentMethod,
    PaymentStatus,
    PaymentWebhookEvent,
)
from apps.payments.services.payment_service import PaymentService

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Service responsible for ingesting, validating, deduplicating, and processing
    gateway webhooks with idempotent database row locking.
    """

    @classmethod
    @transaction.atomic
    def process_razorpay_webhook(cls, raw_body: bytes, signature: str) -> PaymentWebhookEvent:
        # 1. Cryptographic validation of webhook authenticity
        adapter = get_payment_gateway(PaymentGateway.RAZORPAY)
        if not adapter.verify_webhook_signature(raw_body, signature):
            logger.warning("Rejected Razorpay webhook with invalid HMAC signature.")
            raise PaymentVerificationError("Invalid webhook signature.")

        # 2. Parse JSON payload
        try:
            data: Dict[str, Any] = json.loads(raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            raise PaymentVerificationError(f"Malformed webhook JSON payload: {e}")

        event_id = str(data.get("id") or hashlib.sha256(raw_body).hexdigest())
        event_type = data.get("event", "unknown")

        # 3. Webhook Deduplication: if event_id has already been processed, return cleanly
        existing_event = PaymentWebhookEvent.objects.filter(
            provider="RAZORPAY", event_id=event_id
        ).first()
        if existing_event:
            logger.info("Ignoring duplicate webhook event %s (%s).", event_id, event_type)
            return existing_event

        # 4. Create event record
        webhook_event = PaymentWebhookEvent.objects.create(
            provider="RAZORPAY",
            event_id=event_id,
            event_type=event_type,
            payload=data,
            signature_verified=True,
        )

        # 5. Process event based on type
        payment_entity = data.get("payload", {}).get("payment", {}).get("entity", {})
        order_entity = data.get("payload", {}).get("order", {}).get("entity", {})
        refund_entity = data.get("payload", {}).get("refund", {}).get("entity", {})

        gateway_order_id = payment_entity.get("order_id") or order_entity.get("id")
        gateway_payment_id = payment_entity.get("id", "") or refund_entity.get("payment_id", "")
        method = payment_entity.get("method", PaymentMethod.RAZORPAY)

        # Enforce Universal Global Lock Hierarchy: Order -> Payment -> StockReservation -> StockItem
        # 1. Non-locking ID resolution: determine order_id and payment_id first
        order_id = None
        payment_id = None

        if gateway_order_id:
            target_ids = (
                Payment.objects.filter(gateway_order_id=gateway_order_id)
                .values_list("order_id", "id")
                .first()
            )
            if target_ids:
                order_id, payment_id = target_ids

        if not payment_id and gateway_payment_id:
            target_ids = (
                Payment.objects.filter(gateway_payment_id=gateway_payment_id)
                .values_list("order_id", "id")
                .first()
            )
            if target_ids:
                order_id, payment_id = target_ids

        if not payment_id:
            # Fallback 1: check notes attached by adapter during order creation
            notes_order_id = payment_entity.get("notes", {}).get("order_id") or order_entity.get(
                "notes", {}
            ).get("order_id")
            if notes_order_id:
                target_ids = (
                    Payment.objects.filter(order_id=notes_order_id)
                    .order_by("-created_at")
                    .values_list("order_id", "id")
                    .first()
                )
                if target_ids:
                    order_id, payment_id = target_ids

        if not payment_id:
            # Fallback 2: check order receipt/number in order_entity
            receipt = order_entity.get("receipt")
            if receipt:
                target_ids = (
                    Payment.objects.filter(order__order_number=receipt)
                    .order_by("-created_at")
                    .values_list("order_id", "id")
                    .first()
                )
                if target_ids:
                    order_id, payment_id = target_ids

        # 2. Acquire row locks strictly following global lock hierarchy: Order FIRST, Payment SECOND
        order = None
        payment = None
        if order_id:
            order = Order.objects.select_for_update().filter(pk=order_id).first()
        if payment_id:
            payment = Payment.objects.select_for_update().filter(pk=payment_id).first()

        if payment:
            webhook_event.payment = payment

        if event_type in ["payment.captured", "order.paid"] and payment:
            # Check idempotency on payment and order
            if order and order.order_status == OrderStatus.PENDING_PAYMENT:
                OrderStateMachine.transition_status(
                    order=order,
                    to_status=OrderStatus.CONFIRMED,
                    actor=None,
                    notes=f"Order confirmed via Razorpay webhook ({event_type}).",
                )
            elif order and order.order_status in [OrderStatus.FAILED, OrderStatus.CANCELLED]:
                logger.warning(
                    "Payment captured via webhook for %s order %s (%s). Reconciliation required.",
                    order.order_status,
                    order.order_number,
                    gateway_order_id,
                )

            if payment.status != PaymentStatus.CAPTURED:
                now = timezone.now()
                payment.status = PaymentStatus.CAPTURED
                payment.gateway_payment_id = gateway_payment_id or payment.gateway_payment_id
                payment.captured_at = now
                payment.payment_method = method
                if order and order.order_status in [OrderStatus.FAILED, OrderStatus.CANCELLED]:
                    payment.failure_reason = f"RECONCILIATION_REQUIRED: Captured via webhook after order {order.order_status}."
                payment.save(
                    update_fields=[
                        "status",
                        "gateway_payment_id",
                        "captured_at",
                        "payment_method",
                        "failure_reason",
                        "updated_at",
                    ]
                )
                PaymentService.record_payment_attempt(
                    payment=payment,
                    gateway_payment_id=gateway_payment_id,
                    status=PaymentStatus.CAPTURED,
                    raw_response=payment_entity,
                )

        elif event_type == "payment.failed" and payment:
            error_code = payment_entity.get("error_code", "PAYMENT_FAILED")
            error_desc = payment_entity.get("error_description", "Payment attempt failed.")
            PaymentService.record_payment_attempt(
                payment=payment,
                gateway_payment_id=gateway_payment_id,
                status=PaymentStatus.FAILED,
                error_code=error_code,
                error_description=error_desc,
                raw_response=payment_entity,
            )
            # Payment marked failed, but order reservations remain active within TTL for customer retries
            payment.status = PaymentStatus.FAILED
            payment.failed_at = timezone.now()
            payment.failure_reason = error_desc
            payment.save(update_fields=["status", "failed_at", "failure_reason", "updated_at"])

        elif event_type in ["refund.processed", "payment.refunded"] and payment:
            refund_id = refund_entity.get("id", "")
            refund_amount_subunits = refund_entity.get("amount")
            refund_amount = (
                Decimal(str(refund_amount_subunits)) / Decimal("100")
                if refund_amount_subunits is not None
                else payment.amount
            )

            # Idempotency: verify if this gateway refund ID was already recorded
            is_duplicate = False
            if refund_id:
                is_duplicate = PaymentAttempt.objects.filter(
                    payment=payment,
                    gateway_payment_id=refund_id,
                    status__in=[PaymentStatus.REFUNDED, PaymentStatus.PARTIALLY_REFUNDED],
                ).exists()

            if not is_duplicate:
                existing_refunded = payment.amount_refunded or Decimal("0.00")
                new_total_refunded = min(payment.amount, existing_refunded + refund_amount)
                if new_total_refunded >= payment.amount:
                    target_status = PaymentStatus.REFUNDED
                else:
                    target_status = PaymentStatus.PARTIALLY_REFUNDED

                payment.status = target_status
                payment.refund_transaction_id = (
                    refund_id
                    or payment.refund_transaction_id
                    or f"rfnd_{timezone.now().timestamp()}"
                )
                payment.amount_refunded = new_total_refunded
                payment.refunded_at = timezone.now()
                payment.save(
                    update_fields=[
                        "status",
                        "refund_transaction_id",
                        "amount_refunded",
                        "refunded_at",
                        "updated_at",
                    ]
                )
                PaymentService.record_payment_attempt(
                    payment=payment,
                    gateway_payment_id=refund_id,
                    status=target_status,
                    raw_response=refund_entity or payment_entity,
                )

                if order and new_total_refunded >= payment.amount:
                    allowed = OrderStateMachine.ALLOWED_TRANSITIONS.get(order.order_status, [])
                    if OrderStatus.REFUNDED in allowed:
                        try:
                            OrderStateMachine.transition_status(
                                order=order,
                                to_status=OrderStatus.REFUNDED,
                                actor=None,
                                notes=f"Order refunded via Razorpay webhook ({event_type}).",
                            )
                        except Exception as exc:
                            logger.warning(
                                "Order %s status transition to REFUNDED skipped: %s",
                                order.order_number,
                                exc,
                            )

        webhook_event.processed = True
        webhook_event.processed_at = timezone.now()
        webhook_event.save(update_fields=["payment", "processed", "processed_at", "updated_at"])
        return webhook_event
