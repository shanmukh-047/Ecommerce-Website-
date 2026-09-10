import datetime
import logging
import uuid
from decimal import Decimal
from typing import Any, Optional

from django.db import transaction
from django.utils import timezone

from apps.inventory.services import InventoryService
from apps.invoices.models import CreditNoteReason
from apps.invoices.services.credit_note_service import CreditNoteService
from apps.notifications.models import NotificationEvent
from apps.orders.models import Order, OrderLineItem, OrderStatus
from apps.orders.services.checkout_service import OrderStateMachine
from apps.payments.models import Payment, PaymentStatus
from apps.payments.services.payment_service import PaymentService
from apps.returns.exceptions import ReturnConflict, ReturnPolicyViolation
from apps.returns.models import (
    InspectionResult,
    InventoryDisposition,
    ResolutionType,
    ReturnRequest,
    ReturnRequestStatus,
)
from apps.returns.services.return_service import ReturnService

logger = logging.getLogger(__name__)


class ReturnResolutionService:
    """
    Final RMA resolution service executing statutory refunds (credit note + payment refund)
    or generating zero-cost replacement orders with strict idempotency and deadlock-free locking.
    """

    @classmethod
    def complete_return(
        cls,
        return_request_id: uuid.UUID,
        actor: Any,
        resolution_override: Optional[str] = None,
    ) -> ReturnRequest:
        """
        Executes the resolution for an INSPECTED return request.
        Guarantees:
        - Maximum 1 Credit Note per Return Resolution
        - Maximum 1 Gateway Refund Execution per Return Resolution
        - Maximum 1 Replacement Order per Return Resolution
        - Universal lock order: Order -> Payment -> CreditNoteSequence
        """
        return_request = (
            ReturnRequest.objects.prefetch_related("items__order_line_item__variant")
            .filter(pk=return_request_id)
            .first()
        )
        if not return_request:
            raise ReturnConflict("Return request not found.")

        # Idempotency: if already completed, return safely
        if return_request.status == ReturnRequestStatus.COMPLETED:
            return return_request

        if return_request.status != ReturnRequestStatus.INSPECTED:
            raise ReturnConflict(
                f"Cannot complete return request in status '{return_request.status}'. "
                "Request must be INSPECTED first."
            )

        # Verify warehouse QA inspection record and outcome
        inspection = getattr(return_request, "inspection", None)
        if not inspection:
            from apps.returns.models import ReturnInspection

            inspection = ReturnInspection.objects.filter(return_request=return_request).first()

        if not inspection:
            raise ReturnConflict(
                f"Cannot complete return request '{return_request.return_number}' without inspection report. "
                "Request must be INSPECTED first."
            )

        if (
            inspection.result == InspectionResult.FAILED
            or inspection.disposition == InventoryDisposition.RETURN_TO_CUSTOMER
        ):
            with transaction.atomic():
                locked_ret = ReturnRequest.objects.select_for_update().get(pk=return_request_id)
                rejection_notes = inspection.notes or "Failed quality assurance inspection."
                locked_ret.status = ReturnRequestStatus.REJECTED
                locked_ret.rejection_reason = (
                    f"Rejected post-inspection: {rejection_notes} "
                    f"(Result: {inspection.result}, Disposition: {inspection.disposition})."
                )
                locked_ret.save(
                    update_fields=[
                        "status",
                        "rejection_reason",
                        "updated_at",
                    ]
                )
                return_request.status = locked_ret.status
                return_request.rejection_reason = locked_ret.rejection_reason
                transaction.on_commit(
                    lambda: ReturnService._dispatch_return_notification(
                        locked_ret.id, NotificationEvent.RETURN_REJECTED
                    )
                )
                logger.warning(
                    f"ReturnRequest {locked_ret.return_number} REJECTED due to failed inspection "
                    f"({inspection.result} / {inspection.disposition}) by {getattr(actor, 'email', str(actor))}."
                )

            raise ReturnPolicyViolation(
                f"Return request {return_request.return_number} cannot be resolved for refund or replacement "
                f"due to failed QA inspection ({inspection.result} / {inspection.disposition}). "
                "Request marked REJECTED."
            )

        resolution = (
            resolution_override
            or return_request.approved_resolution
            or return_request.requested_resolution
        )

        with transaction.atomic():
            locked_return_request = (
                ReturnRequest.objects.select_for_update()
                .prefetch_related("items__order_line_item__variant")
                .get(pk=return_request_id)
            )
            if locked_return_request.status == ReturnRequestStatus.COMPLETED:
                return locked_return_request

            order = Order.objects.select_for_update().get(pk=locked_return_request.order_id)

            if resolution == ResolutionType.REFUND:
                cls._execute_refund_resolution(locked_return_request, order, actor)
            elif resolution == ResolutionType.REPLACEMENT:
                cls._execute_replacement_resolution(locked_return_request, order, actor)
            else:
                raise ReturnConflict(f"Unknown resolution type '{resolution}'.")

            locked_return_request.status = ReturnRequestStatus.COMPLETED
            locked_return_request.completed_at = timezone.now()
            locked_return_request.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "credit_note",
                    "refund_amount",
                    "refund_transaction_id",
                    "replacement_order",
                    "updated_at",
                ]
            )

            logger.info(
                f"ReturnRequest {locked_return_request.return_number} COMPLETED successfully by {actor.email} "
                f"(Resolution: {resolution})."
            )

            # Dispatch completion notification
            transaction.on_commit(
                lambda: ReturnService._dispatch_return_notification(
                    locked_return_request.id, NotificationEvent.RETURN_COMPLETED
                )
            )

            return locked_return_request

    @classmethod
    def _execute_refund_resolution(
        cls,
        return_request: ReturnRequest,
        order: Order,
        actor: Any,
    ) -> None:
        """
        Executes statutory Credit Note and payment gateway refund with strict idempotency.
        """
        # 1. Statutory Credit Note (Idempotent: maximum 1 per return request)
        if not return_request.credit_note:
            items_data = [
                {
                    "order_line_item_id": str(item.order_line_item_id),
                    "quantity": item.quantity,
                }
                for item in return_request.items.all()
            ]
            credit_note = CreditNoteService.generate_credit_note(
                order=order,
                items_data=items_data,
                reason=CreditNoteReason.CUSTOMER_RETURN,
                reason_notes=f"Statutory refund for return {return_request.return_number}",
            )
            if credit_note:
                return_request.credit_note = credit_note

        # 2. Compute refund amount from returned items
        refund_amount = sum(
            (item.unit_price * item.quantity for item in return_request.items.all()),
            Decimal("0.00"),
        )
        if return_request.credit_note:
            refund_amount = return_request.credit_note.grand_total

        # 3. Gateway Refund Execution (Idempotent: maximum 1 refund per return)
        if return_request.refund_amount <= Decimal("0.00"):
            payment = (
                Payment.objects.select_for_update()
                .filter(
                    order=order,
                    status__in=[PaymentStatus.CAPTURED, PaymentStatus.PARTIALLY_REFUNDED],
                )
                .order_by("-created_at")
                .first()
            )
            if payment:
                refunded_payment = PaymentService.refund_payment(
                    payment=payment,
                    amount=refund_amount,
                    reason=f"Refund for return {return_request.return_number}",
                    actor=actor,
                )
                return_request.refund_amount = refund_amount
                return_request.refund_transaction_id = refunded_payment.refund_transaction_id or ""
            else:
                logger.info(
                    f"No captured payment found for order {order.order_number}. "
                    "Recorded offline refund adjustment."
                )
                return_request.refund_amount = refund_amount

        # 4. If all items in the order have been returned, mark order REFUNDED
        all_lines_delivered_qty = sum(item_line.quantity for item_line in order.lines.all())
        active_returns_qty = sum(
            i.quantity
            for i in ReturnRequest.objects.filter(
                order=order,
                status=ReturnRequestStatus.COMPLETED,
            ).values_list("items__quantity", flat=True)
            if i is not None
        ) + sum(item.quantity for item in return_request.items.all())

        if (
            active_returns_qty >= all_lines_delivered_qty
            and order.order_status != OrderStatus.REFUNDED
        ):
            try:
                OrderStateMachine.transition_status(
                    order,
                    OrderStatus.REFUNDED,
                    actor=actor,
                    notes=f"Order fully refunded following completion of return {return_request.return_number}.",
                )
            except Exception as e:
                logger.warning(f"Could not transition order {order.order_number} to REFUNDED: {e}")

    @classmethod
    def _execute_replacement_resolution(
        cls,
        return_request: ReturnRequest,
        order: Order,
        actor: Any,
    ) -> None:
        """
        Creates a zero-cost replacement Order and reserves replacement inventory.
        Guaranteed idempotent via ReturnRequest -> replacement_order (OneToOne).
        """
        if return_request.replacement_order:
            logger.info(
                f"Replacement order {return_request.replacement_order.order_number} already exists "
                f"for return {return_request.return_number}."
            )
            return

        date_str = timezone.now().strftime("%Y%m%d")
        rpl_number = f"BMP-RPL-{date_str}-{uuid.uuid4().hex[:5].upper()}"

        items_subtotal = Decimal("0.00")
        total_quantity = 0
        total_weight = 0

        for item in return_request.items.select_related("order_line_item__variant").all():
            line = item.order_line_item
            line_cost = line.unit_price * item.quantity
            items_subtotal += line_cost
            total_quantity += item.quantity
            total_weight += (line.variant.weight_in_grams or 0) * item.quantity

        # Create zero-cost replacement Order (items_subtotal - total_discount = 0 grand_total)
        replacement_order = Order.objects.create(
            order_number=rpl_number,
            user=order.user,
            order_status=OrderStatus.PENDING_PAYMENT,
            currency="INR",
            items_subtotal=items_subtotal,
            shipping_fee=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_discount=items_subtotal,
            grand_total=Decimal("0.00"),
            total_quantity=total_quantity,
            total_weight_in_grams=total_weight,
            is_wholesale_order=order.is_wholesale_order,
            shipping_recipient_name=order.shipping_recipient_name,
            shipping_phone_number=order.shipping_phone_number,
            shipping_address_line_1=order.shipping_address_line_1,
            shipping_address_line_2=order.shipping_address_line_2,
            shipping_landmark=order.shipping_landmark,
            shipping_city=order.shipping_city,
            shipping_state=order.shipping_state,
            shipping_pincode=order.shipping_pincode,
            customer_notes=f"Zero-cost replacement order for return {return_request.return_number}.",
        )

        for item in return_request.items.select_related("order_line_item__variant").all():
            line = item.order_line_item
            OrderLineItem.objects.create(
                order=replacement_order,
                variant=line.variant,
                quantity=item.quantity,
                product_name=line.product_name,
                variant_name=line.variant_name,
                sku=line.sku,
                weight_in_grams=line.weight_in_grams,
                mrp=line.mrp,
                unit_price=line.unit_price,
                line_subtotal=line.unit_price * item.quantity,
                pricing_tier_applied="REPLACEMENT",
            )

            # Reserve stock for the replacement item
            InventoryService.reserve_stock(
                variant=line.variant,
                quantity=item.quantity,
                reference_type="ORDER",
                reference_id=replacement_order.id,
                actor=actor,
                expires_at=timezone.now() + datetime.timedelta(days=7),
            )

        # Transition replacement order to CONFIRMED (which consumes reservations & triggers fulfillment)
        OrderStateMachine.transition_status(
            replacement_order,
            OrderStatus.CONFIRMED,
            actor=actor,
            notes=f"Zero-cost replacement confirmed for return {return_request.return_number}.",
        )

        return_request.replacement_order = replacement_order
        logger.info(
            f"Created and confirmed replacement order {replacement_order.order_number} "
            f"for return {return_request.return_number}."
        )
