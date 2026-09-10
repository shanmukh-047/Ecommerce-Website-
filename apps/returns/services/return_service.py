import datetime
import logging
import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.notifications.models import NotificationEvent
from apps.orders.models import Order, OrderStatus
from apps.returns.exceptions import (
    ReturnConflict,
    ReturnPermissionDenied,
    ReturnPolicyViolation,
)
from apps.returns.models import (
    ResolutionType,
    ReturnEvidence,
    ReturnItem,
    ReturnReason,
    ReturnRequest,
    ReturnRequestStatus,
)

logger = logging.getLogger(__name__)


class ReturnService:
    """
    Core domain service orchestrating customer return requests, policy validation,
    concurrency-safe quantity checks, and state machine lifecycle.
    """

    ALLOWED_TRANSITIONS: Dict[str, List[str]] = {
        ReturnRequestStatus.PENDING_REVIEW: [
            ReturnRequestStatus.APPROVED,
            ReturnRequestStatus.REJECTED,
            ReturnRequestStatus.CANCELLED,
        ],
        ReturnRequestStatus.APPROVED: [
            ReturnRequestStatus.PICKUP_SCHEDULED,
            ReturnRequestStatus.CANCELLED,
        ],
        ReturnRequestStatus.PICKUP_SCHEDULED: [
            ReturnRequestStatus.IN_TRANSIT,
            ReturnRequestStatus.CANCELLED,
        ],
        ReturnRequestStatus.IN_TRANSIT: [
            ReturnRequestStatus.RECEIVED,
        ],
        ReturnRequestStatus.RECEIVED: [
            ReturnRequestStatus.INSPECTED,
        ],
        ReturnRequestStatus.INSPECTED: [
            ReturnRequestStatus.COMPLETED,
            ReturnRequestStatus.REJECTED,
        ],
        ReturnRequestStatus.COMPLETED: [],
        ReturnRequestStatus.REJECTED: [],
        ReturnRequestStatus.CANCELLED: [],
    }

    @classmethod
    def generate_return_number(cls) -> str:
        date_str = timezone.now().strftime("%Y%m%d")
        suffix = uuid.uuid4().hex[:5].upper()
        return f"BMP-RET-{date_str}-{suffix}"

    @classmethod
    @transaction.atomic
    def create_return_request(
        cls,
        order_id: uuid.UUID,
        user: Any,
        items_data: List[Dict[str, Any]],
        reason: str = ReturnReason.DEFECTIVE_QUALITY,
        requested_resolution: str = ResolutionType.REFUND,
        customer_notes: str = "",
        evidence_urls: Optional[List[Dict[str, str]]] = None,
    ) -> ReturnRequest:
        """
        Validates order delivery, 7-day window, and item quantities inside an
        atomic row-locked transaction, creating a PENDING_REVIEW ReturnRequest.
        """
        # 1. Row-level lock on Order to ensure deterministic check against concurrent returns
        order = Order.objects.select_for_update().filter(pk=order_id).first()
        if not order:
            raise ReturnConflict("Order not found.")

        # 2. Ownership & IDOR Validation
        is_privileged = user.is_staff or getattr(user, "is_manager", False)
        if order.user != user and not is_privileged:
            raise ReturnPermissionDenied(
                "You do not have permission to request a return for this order."
            )

        # 3. Order Status Validation
        if order.order_status != OrderStatus.DELIVERED:
            raise ReturnPolicyViolation(
                f"Returns can only be requested for DELIVERED orders. Current status: '{order.order_status}'."
            )

        # 4. Return Window Policy Check (Default 7 Days)
        window_days = getattr(settings, "RETURN_POLICY_WINDOW_DAYS", 7)
        delivery_time = order.delivered_at or order.updated_at
        cutoff_time = delivery_time + datetime.timedelta(days=window_days)
        if timezone.now() > cutoff_time:
            raise ReturnPolicyViolation(
                f"Return policy window has expired. Returns must be requested within {window_days} days of delivery."
            )

        if not items_data:
            raise ReturnPolicyViolation("At least one line item must be selected for return.")

        # 5. Lock Order Line Items and Validate Eligible Quantities
        line_items_map = {line.id: line for line in order.lines.select_for_update().all()}

        active_statuses = [
            ReturnRequestStatus.PENDING_REVIEW,
            ReturnRequestStatus.APPROVED,
            ReturnRequestStatus.PICKUP_SCHEDULED,
            ReturnRequestStatus.IN_TRANSIT,
            ReturnRequestStatus.RECEIVED,
            ReturnRequestStatus.INSPECTED,
            ReturnRequestStatus.COMPLETED,
        ]

        # Calculate already committed quantities per line item
        existing_return_items = (
            ReturnItem.objects.filter(
                return_request__order=order,
                return_request__status__in=active_statuses,
            )
            .values("order_line_item_id")
            .annotate(total_requested=models.Sum("quantity"))
        )

        committed_qty_map = {
            row["order_line_item_id"]: row["total_requested"] for row in existing_return_items
        }

        validated_items = []
        for item_data in items_data:
            line_id_raw = item_data.get("order_line_item_id")
            try:
                line_id = uuid.UUID(str(line_id_raw))
            except (ValueError, TypeError):
                raise ReturnPolicyViolation(f"Invalid order_line_item_id: '{line_id_raw}'.")

            line = line_items_map.get(line_id)
            if not line:
                raise ReturnPolicyViolation(
                    f"Order line item '{line_id}' does not belong to order {order.order_number}."
                )

            qty = item_data.get("quantity", 1)
            if not isinstance(qty, int) or qty <= 0:
                raise ReturnPolicyViolation("Return quantity must be a positive integer.")

            committed = committed_qty_map.get(line.id, 0)
            eligible_qty = line.quantity - committed
            if qty > eligible_qty:
                raise ReturnPolicyViolation(
                    f"Cannot return {qty} units of '{line.variant_name}'. Only {eligible_qty} units eligible."
                )

            item_reason = item_data.get("reason") or reason
            unit_price = line.unit_price
            line_total = (unit_price * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # Update committed map for this run to avoid internal duplicates
            committed_qty_map[line.id] = committed + qty

            validated_items.append(
                {
                    "order_line_item": line,
                    "quantity": qty,
                    "reason": item_reason,
                    "unit_price": unit_price,
                    "total_amount": line_total,
                }
            )

        # 6. Create ReturnRequest
        return_number = cls.generate_return_number()
        return_request = ReturnRequest.objects.create(
            return_number=return_number,
            order=order,
            user=order.user,
            status=ReturnRequestStatus.PENDING_REVIEW,
            requested_resolution=requested_resolution,
            reason=reason,
            customer_notes=customer_notes,
        )

        # 7. Create ReturnItems
        for v in validated_items:
            ReturnItem.objects.create(
                return_request=return_request,
                order_line_item=v["order_line_item"],
                quantity=v["quantity"],
                reason=v["reason"],
                unit_price=v["unit_price"],
                total_amount=v["total_amount"],
            )

        # 8. Attach Evidence Photos if provided
        if evidence_urls:
            for ev in evidence_urls:
                url = ev.get("file_url", "").strip()
                if url:
                    ReturnEvidence.objects.create(
                        return_request=return_request,
                        file_url=url,
                        description=ev.get("description", "").strip(),
                    )

        logger.info(
            f"Created ReturnRequest {return_number} for Order {order.order_number} by User {order.user.email}."
        )

        # 9. Schedule Customer Notification
        transaction.on_commit(
            lambda: cls._dispatch_return_notification(
                return_request.id, NotificationEvent.RETURN_REQUESTED
            )
        )

        return return_request

    @classmethod
    @transaction.atomic
    def cancel_return_request(
        cls, return_request_id: uuid.UUID, user: Any, reason: str = ""
    ) -> ReturnRequest:
        """
        Allows a customer or staff to cancel a return request before reverse pickup is completed.
        """
        return_request = (
            ReturnRequest.objects.select_for_update().filter(pk=return_request_id).first()
        )
        if not return_request:
            raise ReturnConflict("Return request not found.")

        is_privileged = user.is_staff or getattr(user, "is_manager", False)
        if return_request.user != user and not is_privileged:
            raise ReturnPermissionDenied(
                "You do not have permission to cancel this return request."
            )

        cancellable_statuses = [
            ReturnRequestStatus.PENDING_REVIEW,
            ReturnRequestStatus.APPROVED,
            ReturnRequestStatus.PICKUP_SCHEDULED,
        ]
        if return_request.status not in cancellable_statuses:
            raise ReturnConflict(
                f"Cannot cancel return request in status '{return_request.status}'. "
                "Cancellations are only permitted prior to courier pickup handover."
            )

        return_request.status = ReturnRequestStatus.CANCELLED
        return_request.cancelled_at = timezone.now()
        if reason:
            return_request.customer_notes = (
                f"{return_request.customer_notes}\nCancellation note: {reason}".strip()
            )
        return_request.save(
            update_fields=["status", "cancelled_at", "customer_notes", "updated_at"]
        )

        # Also cancel linked reverse shipment if scheduled
        if hasattr(return_request, "reverse_shipment"):
            shipment = return_request.reverse_shipment
            shipment.status = "CANCELLED"
            shipment.save(update_fields=["status", "updated_at"])

        logger.info(f"ReturnRequest {return_request.return_number} cancelled by {user.email}.")
        return return_request

    @classmethod
    @transaction.atomic
    def transition_status(
        cls,
        return_request: ReturnRequest,
        to_status: str,
        actor: Optional[Any] = None,
        notes: str = "",
    ) -> ReturnRequest:
        """
        Validates state machine rules and transitions ReturnRequest status.
        """
        from_status = return_request.status
        allowed = cls.ALLOWED_TRANSITIONS.get(from_status, [])
        if to_status not in allowed:
            raise ReturnConflict(
                f"Cannot transition return request from '{from_status}' to '{to_status}'."
            )

        return_request.status = to_status
        update_fields = ["status", "updated_at"]
        return_request.save(update_fields=update_fields)

        logger.info(
            f"ReturnRequest {return_request.return_number} transitioned from {from_status} to {to_status} by {actor}."
        )
        return return_request

    @classmethod
    def _dispatch_return_notification(cls, return_request_id: uuid.UUID, event: str) -> None:
        """
        Asynchronously triggers transactional notifications for return events.
        """
        try:
            from apps.returns.tasks import send_return_notification_task

            send_return_notification_task.delay(str(return_request_id), event)
        except Exception as exc:
            logger.warning(
                f"Failed to enqueue return notification task for {return_request_id}: {exc}"
            )
