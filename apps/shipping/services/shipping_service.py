import logging
import secrets
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db import models, transaction
from django.utils import timezone

from apps.inventory.models import MovementType
from apps.inventory.services import InventoryService
from apps.orders.exceptions import OrderConflict
from apps.orders.models import Order, OrderStatus
from apps.orders.services import OrderStateMachine
from apps.shipping.couriers.factory import get_courier_adapter
from apps.shipping.exceptions import ShipmentConflict
from apps.shipping.models import (
    CourierProvider,
    Shipment,
    ShipmentItem,
    ShipmentStatus,
    ShipmentTrackingEvent,
)

logger = logging.getLogger(__name__)


class ShippingService:
    """
    Authoritative logistics engine coordinating parcel packaging, split fulfillments,
    carrier bookings, AWB allocation, tracking milestones, RTO restocks,
    and bidirectional order lifecycle synchronization.
    """

    SHIPMENT_NUMBER_CHARSET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"

    ALLOWED_TRANSITIONS = {
        ShipmentStatus.PENDING: [
            ShipmentStatus.LABEL_GENERATED,
            ShipmentStatus.READY_FOR_PICKUP,
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.CANCELLED,
        ],
        ShipmentStatus.LABEL_GENERATED: [
            ShipmentStatus.READY_FOR_PICKUP,
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.CANCELLED,
        ],
        ShipmentStatus.READY_FOR_PICKUP: [
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.CANCELLED,
        ],
        ShipmentStatus.IN_TRANSIT: [
            ShipmentStatus.OUT_FOR_DELIVERY,
            ShipmentStatus.FAILED_DELIVERY,
            ShipmentStatus.RETURNED_TO_ORIGIN,
            ShipmentStatus.DELIVERED,
        ],
        ShipmentStatus.OUT_FOR_DELIVERY: [
            ShipmentStatus.DELIVERED,
            ShipmentStatus.FAILED_DELIVERY,
            ShipmentStatus.RETURNED_TO_ORIGIN,
        ],
        ShipmentStatus.FAILED_DELIVERY: [
            ShipmentStatus.OUT_FOR_DELIVERY,
            ShipmentStatus.RETURNED_TO_ORIGIN,
        ],
        ShipmentStatus.DELIVERED: [],
        ShipmentStatus.RETURNED_TO_ORIGIN: [],
        ShipmentStatus.CANCELLED: [],
    }

    @classmethod
    def generate_shipment_number(cls) -> str:
        date_str = timezone.now().strftime("%Y%m%d")
        for _ in range(5):
            suffix = "".join(secrets.choice(cls.SHIPMENT_NUMBER_CHARSET) for _ in range(5))
            candidate = f"SHP-{date_str}-{suffix}"
            if not Shipment.objects.filter(shipment_number=candidate).exists():
                return candidate
        return f"SHP-{date_str}-{uuid.uuid4().hex[:8].upper()}"

    @classmethod
    def get_order_fulfillment_summary(cls, order: Order) -> Dict[str, Any]:
        """
        Calculates fulfilled and remaining quantities for each line item of an order.
        """
        active_items = ShipmentItem.objects.filter(order_line_item__order=order).exclude(
            shipment__status=ShipmentStatus.CANCELLED
        )

        fulfilled_map: Dict[uuid.UUID, int] = {}
        for item in active_items:
            line_id = item.order_line_item_id
            fulfilled_map[line_id] = fulfilled_map.get(line_id, 0) + item.quantity

        lines_summary = []
        is_fully_fulfilled = True

        for line in order.lines.all():
            fulfilled = fulfilled_map.get(line.id, 0)
            remaining = line.quantity - fulfilled
            if remaining > 0:
                is_fully_fulfilled = False

            lines_summary.append(
                {
                    "line_id": str(line.id),
                    "sku": line.sku,
                    "product_name": line.product_name,
                    "variant_name": line.variant_name,
                    "ordered_quantity": line.quantity,
                    "fulfilled_quantity": fulfilled,
                    "remaining_quantity": remaining,
                }
            )

        return {
            "order_id": str(order.id),
            "order_number": order.order_number,
            "is_fully_fulfilled": is_fully_fulfilled,
            "lines": lines_summary,
        }

    @classmethod
    @transaction.atomic
    def create_shipment(
        cls,
        order: Order,
        items_data: Optional[List[Dict[str, Any]]] = None,
        courier_name: str = CourierProvider.MANUAL,
        weight_in_grams: Optional[int] = None,
        length_cm: Optional[Decimal] = None,
        breadth_cm: Optional[Decimal] = None,
        height_cm: Optional[Decimal] = None,
        notes: str = "",
        actor: Optional[Any] = None,
    ) -> Shipment:
        """
        Creates a new shipment carton for an order, snapshotting the destination
        address, allocating items, and optionally advancing Order to PROCESSING.
        """
        # 1. Deterministic lock on Order
        order = Order.objects.select_for_update().get(pk=order.id)

        # 2. Prerequisite Check: Order must be CONFIRMED or PROCESSING
        if order.order_status not in [OrderStatus.CONFIRMED, OrderStatus.PROCESSING]:
            raise ShipmentConflict(
                f"Cannot create shipment for order in status '{order.order_status}'. "
                "Order must be CONFIRMED or PROCESSING."
            )

        # 3. Calculate fulfillment accounting
        active_items = ShipmentItem.objects.filter(order_line_item__order=order).exclude(
            shipment__status=ShipmentStatus.CANCELLED
        )

        fulfilled_map: Dict[uuid.UUID, int] = {}
        for item in active_items:
            line_id = item.order_line_item_id
            fulfilled_map[line_id] = fulfilled_map.get(line_id, 0) + item.quantity

        line_map = {line.id: line for line in order.lines.all()}
        remaining_map: Dict[uuid.UUID, int] = {}
        for line_id, line in line_map.items():
            rem = line.quantity - fulfilled_map.get(line_id, 0)
            if rem > 0:
                remaining_map[line_id] = rem

        if not remaining_map:
            raise ShipmentConflict("Order is already fully fulfilled. No remaining items to ship.")

        # 4. Resolve items to pack in this shipment
        items_to_create = []
        calculated_weight = 0

        if items_data:
            for entry in items_data:
                line_id = entry.get("order_line_item_id")
                if isinstance(line_id, str):
                    try:
                        line_id = uuid.UUID(line_id)
                    except ValueError:
                        raise ShipmentConflict(f"Invalid line item ID format: '{line_id}'.")

                if line_id not in line_map:
                    raise ShipmentConflict(
                        f"Line item '{line_id}' does not belong to order {order.order_number}."
                    )

                qty = entry.get("quantity", 0)
                if not isinstance(qty, int) or qty <= 0:
                    raise ShipmentConflict("Shipped quantity must be a positive integer.")

                available = remaining_map.get(line_id, 0)
                if qty > available:
                    line = line_map[line_id]
                    raise ShipmentConflict(
                        f"Requested quantity {qty} exceeds remaining unfulfilled quantity {available} for SKU {line.sku}."
                    )

                line = line_map[line_id]
                items_to_create.append((line, qty))
                remaining_map[line_id] -= qty
                calculated_weight += (line.weight_in_grams or 100) * qty
        else:
            # Default single-shipment fulfillment: Pack all remaining items
            for line_id, rem in remaining_map.items():
                line = line_map[line_id]
                items_to_create.append((line, rem))
                calculated_weight += (line.weight_in_grams or 100) * rem

        if not items_to_create:
            raise ShipmentConflict("No valid items specified for shipment.")

        final_weight = (
            weight_in_grams
            if (weight_in_grams and weight_in_grams > 0)
            else (calculated_weight or 500)
        )

        # 5. Generate collision-safe shipment number
        shipment_number = cls.generate_shipment_number()

        # 6. Create Shipment with immutable destination snapshot from Order
        shipment = Shipment.objects.create(
            shipment_number=shipment_number,
            order=order,
            status=ShipmentStatus.PENDING,
            courier_name=courier_name or CourierProvider.MANUAL,
            weight_in_grams=final_weight,
            length_cm=length_cm,
            breadth_cm=breadth_cm,
            height_cm=height_cm,
            shipping_recipient_name=order.shipping_recipient_name,
            shipping_phone_number=order.shipping_phone_number,
            shipping_address_line_1=order.shipping_address_line_1,
            shipping_address_line_2=order.shipping_address_line_2,
            shipping_landmark=order.shipping_landmark,
            shipping_city=order.shipping_city,
            shipping_state=order.shipping_state,
            shipping_pincode=order.shipping_pincode,
            notes=notes,
        )

        # 7. Create ShipmentItem records
        for line, qty in items_to_create:
            ShipmentItem.objects.create(
                shipment=shipment,
                order_line_item=line,
                quantity=qty,
            )

        # 8. Record initial milestone event
        ShipmentTrackingEvent.objects.create(
            shipment=shipment,
            status=ShipmentStatus.PENDING,
            location="Sirsi Warehouse",
            description=f"Shipment {shipment_number} created with {len(items_to_create)} item line(s).",
            event_timestamp=timezone.now(),
        )

        # 9. Order State Synchronization: Advance CONFIRMED to PROCESSING
        if order.order_status == OrderStatus.CONFIRMED:
            OrderStateMachine.transition_status(
                order,
                OrderStatus.PROCESSING,
                actor=actor,
                notes=f"Shipment {shipment_number} created.",
            )

        return shipment

    @classmethod
    @transaction.atomic
    def book_carrier_and_generate_label(
        cls,
        shipment: Shipment,
        courier_name: Optional[str] = None,
        actor: Optional[Any] = None,
    ) -> Shipment:
        """
        Invokes courier adapter to book carrier consignment, assign AWB,
        and generate shipping label URL. Advances status to LABEL_GENERATED.
        """
        shipment = Shipment.objects.select_for_update().get(pk=shipment.id)

        if shipment.status == ShipmentStatus.CANCELLED:
            raise ShipmentConflict("Cannot book carrier for a cancelled shipment.")

        if courier_name:
            shipment.courier_name = courier_name

        adapter = get_courier_adapter(shipment.courier_name)

        # Call adapter
        booking_result = adapter.create_shipment(shipment)
        awb_number = booking_result.get("awb_number", "")
        shipment.awb_number = awb_number

        label_result = adapter.generate_label(shipment)
        label_url = label_result.get("label_url", "")
        shipment.shipping_label_url = label_url

        if shipment.status == ShipmentStatus.PENDING:
            shipment.status = ShipmentStatus.LABEL_GENERATED

        shipment.save(
            update_fields=[
                "courier_name",
                "awb_number",
                "shipping_label_url",
                "status",
                "updated_at",
            ]
        )

        ShipmentTrackingEvent.objects.create(
            shipment=shipment,
            status=shipment.status,
            location="Sirsi Warehouse",
            description=f"Carrier {shipment.courier_name} allocated. AWB: {awb_number}. Label generated.",
            event_timestamp=timezone.now(),
        )

        return shipment

    @classmethod
    @transaction.atomic
    def transition_shipment_status(
        cls,
        shipment: Shipment,
        to_status: str,
        location: str = "",
        description: str = "",
        actor: Optional[Any] = None,
        event_timestamp: Optional[Any] = None,
    ) -> Shipment:
        """
        Transitions shipment status through FSM, records append-only tracking milestone,
        and synchronizes parent Order status (SHIPPED, DELIVERED).
        """
        # Deterministic locking: Order then Shipment
        order = Order.objects.select_for_update().get(pk=shipment.order_id)
        shipment = Shipment.objects.select_for_update().get(pk=shipment.id)

        # Idempotency: if already in target status, return cleanly
        if shipment.status == to_status:
            return shipment

        allowed = cls.ALLOWED_TRANSITIONS.get(shipment.status, [])
        if to_status not in allowed:
            raise ShipmentConflict(
                f"Cannot transition shipment from '{shipment.status}' to '{to_status}'."
            )

        from_status = shipment.status
        now = timezone.now()
        timestamp = event_timestamp or now

        shipment.status = to_status
        update_fields = ["status", "updated_at"]

        if to_status == ShipmentStatus.IN_TRANSIT and not shipment.shipped_at:
            shipment.shipped_at = timestamp
            update_fields.append("shipped_at")

        if to_status == ShipmentStatus.DELIVERED and not shipment.actual_delivery_date:
            shipment.actual_delivery_date = timestamp
            update_fields.append("actual_delivery_date")

        shipment.save(update_fields=update_fields)

        # Append audit tracking event
        event_desc = description or f"Shipment transitioned from {from_status} to {to_status}."
        ShipmentTrackingEvent.objects.create(
            shipment=shipment,
            status=to_status,
            location=location,
            description=event_desc,
            event_timestamp=timestamp,
        )

        # Synchronize parent Order status
        if to_status == ShipmentStatus.IN_TRANSIT:
            if order.order_status in [OrderStatus.CONFIRMED, OrderStatus.PROCESSING]:
                OrderStateMachine.transition_status(
                    order,
                    OrderStatus.SHIPPED,
                    actor=actor,
                    notes=f"Shipment {shipment.shipment_number} dispatched via {shipment.courier_name} (AWB: {shipment.awb_number}).",
                )

        elif to_status == ShipmentStatus.DELIVERED:
            # Check if all active shipments for this order are DELIVERED
            active_shipments = order.shipments.exclude(status=ShipmentStatus.CANCELLED)
            all_shipments_delivered = (
                active_shipments.filter(status=ShipmentStatus.DELIVERED).count()
                == active_shipments.count()
            )

            # Check if total delivered quantity fulfills order total
            delivered_quantity = (
                ShipmentItem.objects.filter(
                    shipment__order=order,
                    shipment__status=ShipmentStatus.DELIVERED,
                ).aggregate(total=models.Sum("quantity"))["total"]
                or 0
            )

            if all_shipments_delivered and delivered_quantity >= order.total_quantity:
                if order.order_status == OrderStatus.SHIPPED:
                    OrderStateMachine.transition_status(
                        order,
                        OrderStatus.DELIVERED,
                        actor=actor,
                        notes=f"All shipments delivered (Final delivery: {shipment.shipment_number}).",
                    )

        elif to_status == ShipmentStatus.RETURNED_TO_ORIGIN:
            cls.handle_rto_restock(shipment, actor=actor)

        return shipment

    @classmethod
    @transaction.atomic
    def cancel_shipment(
        cls,
        shipment: Shipment,
        reason: str = "",
        actor: Optional[Any] = None,
    ) -> Shipment:
        """
        Cancels a shipment prior to courier dispatch. Releases allocated items
        back to the order's unfulfilled pool.
        """
        shipment = Shipment.objects.select_for_update().get(pk=shipment.id)

        if shipment.status == ShipmentStatus.CANCELLED:
            return shipment

        if shipment.status in [
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.OUT_FOR_DELIVERY,
            ShipmentStatus.DELIVERED,
        ]:
            raise ShipmentConflict(
                f"Cannot cancel shipment in status '{shipment.status}'. Only pre-dispatch shipments can be cancelled."
            )

        # Cancel with courier provider if AWB was booked
        if shipment.awb_number:
            adapter = get_courier_adapter(shipment.courier_name)
            adapter.cancel_shipment(shipment)

        shipment.status = ShipmentStatus.CANCELLED
        shipment.cancellation_reason = reason or "Cancelled by warehouse staff."
        shipment.save(update_fields=["status", "cancellation_reason", "updated_at"])

        ShipmentTrackingEvent.objects.create(
            shipment=shipment,
            status=ShipmentStatus.CANCELLED,
            location="Sirsi Warehouse",
            description=f"Shipment cancelled: {shipment.cancellation_reason}",
            event_timestamp=timezone.now(),
        )

        return shipment

    @classmethod
    @transaction.atomic
    def handle_rto_restock(
        cls,
        shipment: Shipment,
        actor: Optional[Any] = None,
    ) -> None:
        """
        When a shipment is marked RETURNED_TO_ORIGIN:
        1. Restocks physical inventory for the shipment's items via InventoryService.add_stock.
        2. Evaluates parent order: if all active shipments are RTO, transitions order to CANCELLED.
        3. Issues a gateway refund for the RTO items' value.
        4. Dispatches statutory GST Credit Note task.
        5. Dispatches customer notification.
        """
        order = Order.objects.select_for_update().get(id=shipment.order_id)
        locked_shipments = list(order.shipments.select_for_update().order_by("id"))

        # 1. Restock items in this RTO shipment
        for item in shipment.items.select_related("order_line_item__variant"):
            InventoryService.add_stock(
                variant=item.order_line_item.variant,
                quantity=item.quantity,
                actor=actor,
                note=f"RTO restock for shipment {shipment.shipment_number}",
                movement_type=MovementType.INBOUND,
                reference_type="SHIPMENT_RTO",
                reference_id=shipment.id,
            )

        # 2. Check sibling shipments to determine if all active shipments are RTO
        active_or_rto = [s for s in locked_shipments if s.status != ShipmentStatus.CANCELLED]
        all_rto = bool(
            active_or_rto
            and all(s.status == ShipmentStatus.RETURNED_TO_ORIGIN for s in active_or_rto)
        )

        if all_rto and order.order_status in [
            OrderStatus.CONFIRMED,
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
        ]:
            OrderStateMachine.transition_status(
                order=order,
                to_status=OrderStatus.CANCELLED,
                actor=actor,
                notes=f"Order cancelled: all consignments returned to origin (Last RTO: {shipment.shipment_number}).",
            )

        # 3. Compute refund amount for items in this RTO shipment
        rto_items_total = sum(
            (item.order_line_item.unit_price * item.quantity for item in shipment.items.all()),
            Decimal("0.00"),
        )
        if all_rto and order.order_status in [
            OrderStatus.CANCELLED,
            OrderStatus.REFUNDED,
        ]:
            rto_refund_amount = order.grand_total
        else:
            rto_refund_amount = rto_items_total

        # 4. Gateway Refund Execution
        from apps.payments.models import Payment, PaymentStatus
        from apps.payments.services.payment_service import PaymentService

        payment = (
            Payment.objects.select_for_update()
            .filter(
                order=order,
                status__in=[PaymentStatus.CAPTURED, PaymentStatus.PARTIALLY_REFUNDED],
            )
            .order_by("-created_at")
            .first()
        )
        if payment and rto_refund_amount > Decimal("0.00"):
            current_refunded = payment.amount_refunded or Decimal("0.00")
            max_refundable = payment.amount - current_refunded
            eligible_refund = min(rto_refund_amount, max_refundable)
            if eligible_refund > Decimal("0.00"):
                PaymentService.refund_payment(
                    payment=payment,
                    amount=eligible_refund,
                    reason=f"Automated refund for RTO shipment {shipment.shipment_number}",
                    actor=actor,
                )

        # 5. Phase 3.9: Dispatch credit note for Return to Origin
        transaction.on_commit(
            lambda: cls._dispatch_rto_credit_note(shipment.order_id, shipment.shipment_number)
        )

        # 6. Customer Notification Hook
        transaction.on_commit(lambda: cls._dispatch_rto_notification(shipment.order_id, all_rto))

    @classmethod
    def _dispatch_rto_credit_note(cls, order_id, shipment_number: str) -> None:
        """
        Dispatches background task to generate a statutory GST Credit Note for RTO.
        """
        try:
            from apps.invoices.models import CreditNoteReason
            from apps.invoices.tasks import generate_credit_note_for_order_task

            generate_credit_note_for_order_task.delay(
                str(order_id),
                CreditNoteReason.RETURN_TO_ORIGIN,
                f"Return to origin for shipment {shipment_number}.",
            )
        except Exception as exc:
            logger.exception(
                "Failed to dispatch RTO credit note task for order %s: %s",
                order_id,
                exc,
            )

    @classmethod
    def _dispatch_rto_notification(cls, order_id, all_rto: bool = False) -> None:
        """
        Dispatches background notification to the customer for RTO delivery failure and refund.
        """
        try:
            from apps.notifications.models import NotificationEvent
            from apps.notifications.tasks import send_order_notifications_task

            event = (
                NotificationEvent.ORDER_CANCELLED if all_rto else NotificationEvent.REFUND_PROCESSED
            )
            send_order_notifications_task.delay(str(order_id), event)
        except Exception as exc:
            logger.exception(
                "Failed to dispatch RTO notification task for order %s: %s",
                order_id,
                exc,
            )

    @classmethod
    def check_order_cancellation_allowed(cls, order: Order) -> None:
        """
        Guards Order cancellation: if any shipment is in transit, out for delivery,
        or delivered, order cancellation is strictly prohibited.
        """
        dispatched_shipments = order.shipments.filter(
            status__in=[
                ShipmentStatus.IN_TRANSIT,
                ShipmentStatus.OUT_FOR_DELIVERY,
                ShipmentStatus.DELIVERED,
            ]
        )
        if dispatched_shipments.exists():
            raise OrderConflict(
                "Order cannot be cancelled because shipment(s) are already in transit or delivered."
            )
