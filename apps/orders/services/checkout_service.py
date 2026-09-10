import secrets
import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Address
from apps.cart.models import Cart, CartItem
from apps.cart.services import CartService
from apps.inventory.models import MovementType, ReservationStatus, StockItem, StockReservation
from apps.inventory.services import InventoryService
from apps.orders.exceptions import OrderConflict
from apps.orders.models import Order, OrderLineItem, OrderStatus, OrderStatusHistory


class CheckoutService:
    """
    Authoritative checkout engine coordinating atomic cart locking,
    deterministic stock locking, server-side repricing, address snapshotting,
    and inventory reservations.
    """

    ORDER_NUMBER_CHARSET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"

    @classmethod
    def generate_order_number(cls) -> str:
        date_str = timezone.now().strftime("%Y%m%d")
        for _ in range(5):
            suffix = "".join(secrets.choice(cls.ORDER_NUMBER_CHARSET) for _ in range(5))
            candidate = f"BMP-{date_str}-{suffix}"
            if not Order.objects.filter(order_number=candidate).exists():
                return candidate
        # Fallback with higher entropy
        return f"BMP-{date_str}-{uuid.uuid4().hex[:8].upper()}"

    @classmethod
    @transaction.atomic
    def create_order_from_cart(cls, user, shipping_address_id, customer_notes: str = "") -> Order:
        if not user or not user.is_authenticated:
            raise OrderConflict("Authentication is required for checkout.")

        # 1. Lock user cart
        cart = Cart.objects.select_for_update().filter(user=user).first()
        if not cart:
            raise OrderConflict("Cart was not found.")

        # 2. Lock all cart items explicitly
        cart_items = list(
            CartItem.objects.select_for_update()
            .select_related("variant__product")
            .filter(cart=cart)
        )
        if not cart_items:
            raise OrderConflict("Cart is empty.")

        # 3. Validate shipping address ownership strictly to prevent IDOR
        address = Address.objects.filter(user=user, id=shipping_address_id).first()
        if not address:
            raise OrderConflict("Valid shipping address belonging to the customer is required.")

        is_wholesale = getattr(user, "is_wholesale_buyer", False)

        # 3b. Coupon Row-Locking & Validation (Strict Hierarchy: Coupon -> StockItem)
        coupon = None
        if cart.applied_coupon_id:
            from apps.promotions.models import Coupon, CouponUsage

            try:
                coupon = Coupon.objects.select_for_update().get(id=cart.applied_coupon_id)
            except Coupon.DoesNotExist:
                raise OrderConflict("Applied coupon does not exist.")

            if not coupon.is_active:
                raise OrderConflict("Applied coupon is no longer active.")

            now = timezone.now()
            if now < coupon.valid_from or now > coupon.valid_to:
                raise OrderConflict("Applied coupon has expired.")

            if is_wholesale and not coupon.applicable_to_wholesale:
                raise OrderConflict(
                    "Applied coupon cannot be combined with wholesale contract pricing."
                )

            if (
                coupon.usage_limit_total is not None
                and coupon.times_used >= coupon.usage_limit_total
            ):
                raise OrderConflict("Applied coupon has reached its maximum global usage limit.")

            if user and user.is_authenticated:
                user_usage_count = CouponUsage.objects.filter(coupon=coupon, user=user).count()
                if user_usage_count >= coupon.usage_limit_per_user:
                    raise OrderConflict(
                        "You have already reached the redemption limit for this coupon."
                    )

        # 4. Deterministic database-level stock locking
        # CAUTION HEEDED: Query includes order_by("variant_id") so PostgreSQL/DB engine
        # acquires row locks in a strictly deterministic ascending order to prevent deadlocks.
        variant_ids = sorted([item.variant_id for item in cart_items])
        stock_items_query = (
            StockItem.objects.select_for_update()
            .filter(variant_id__in=variant_ids)
            .order_by("variant_id")
        )
        stock_items_map = {si.variant_id: si for si in stock_items_query}

        # 5. Verify active variants and inventory availability
        for item in cart_items:
            variant = item.variant
            if not variant.is_active:
                raise OrderConflict(f"Variant '{variant.variant_name}' is no longer active.")
            stock = stock_items_map.get(variant.id)
            if not stock or stock.quantity_available < item.quantity:
                raise OrderConflict(
                    f"Insufficient available inventory for variant '{variant.variant_name}'."
                )

        # 6. Authoritative server-side repricing (ignoring any client-sent prices)
        subtotal = Decimal("0.00")
        total_quantity = 0
        total_weight = 0
        line_specs = []

        for item in cart_items:
            variant = item.variant
            unit_price = CartService.unit_price(variant, item.quantity, user)
            item.unit_price = unit_price  # Augment item for discount evaluation
            line_subtotal = unit_price * item.quantity
            subtotal += line_subtotal
            total_quantity += item.quantity
            total_weight += (variant.weight_in_grams or 0) * item.quantity

            tier_applied = (
                "WHOLESALE" if (is_wholesale and unit_price < variant.selling_price) else "RETAIL"
            )

            line_specs.append(
                {
                    "variant": variant,
                    "quantity": item.quantity,
                    "product_name": variant.product.name,
                    "variant_name": variant.variant_name,
                    "sku": variant.sku,
                    "weight_in_grams": variant.weight_in_grams,
                    "mrp": variant.mrp,
                    "unit_price": unit_price,
                    "line_subtotal": line_subtotal,
                    "pricing_tier_applied": tier_applied,
                }
            )

        # 6b. Promotions and Discount Engine Evaluation
        from apps.promotions.models import OrderDiscountSnapshot, Promotion
        from apps.promotions.services.coupon_service import CouponService
        from apps.promotions.services.discount_engine import DiscountEngine
        from apps.promotions.services.promotion_service import PromotionService

        promotions = PromotionService.get_active_promotions(is_wholesale=is_wholesale)
        discount_res = DiscountEngine.evaluate_discounts(
            items=cart_items,
            applied_coupon=coupon,
            user=user,
            is_wholesale=is_wholesale,
            promotions=promotions,
        )

        total_discount = discount_res.total_discount
        grand_total = max(Decimal("0.00"), subtotal - total_discount)

        # 7. Collision-safe Order Number
        order_number = cls.generate_order_number()

        # 8. Create Order with Immutable Flat Address Snapshot
        order = Order.objects.create(
            order_number=order_number,
            user=user,
            order_status=OrderStatus.PENDING_PAYMENT,
            currency="INR",
            items_subtotal=subtotal,
            shipping_fee=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_discount=total_discount,
            grand_total=grand_total,
            total_quantity=total_quantity,
            total_weight_in_grams=total_weight,
            is_wholesale_order=is_wholesale,
            shipping_recipient_name=address.recipient_name,
            shipping_phone_number=address.phone_number,
            shipping_address_line_1=address.address_line_1,
            shipping_address_line_2=address.address_line_2,
            shipping_landmark=address.landmark,
            shipping_city=address.city,
            shipping_state=address.state,
            shipping_pincode=address.pincode,
            shipping_address=address,
            customer_notes=customer_notes,
        )

        # 8b. Record Coupon Redemption and Immutable Order Discount Snapshots
        if coupon and discount_res.coupon_discount > Decimal("0.00"):
            CouponService.lock_and_record_usage(
                coupon_id=coupon.id,
                user=user,
                order=order,
                discount_amount=discount_res.coupon_discount,
            )

        for detail in discount_res.breakdown:
            OrderDiscountSnapshot.objects.create(
                order=order,
                coupon=coupon if detail.source_type == "COUPON" else None,
                promotion=(
                    Promotion.objects.filter(id=detail.source_id).first()
                    if detail.source_type == "PROMOTION"
                    else None
                ),
                discount_name=detail.name,
                discount_type=detail.discount_type,
                discount_value=detail.discount_value,
                applied_amount=detail.applied_amount,
                statutory_gst_adjusted=True,
            )

        # 9. Create OrderLineItems and Reserve Inventory
        reservation_expiry = timezone.now() + timedelta(
            minutes=getattr(settings, "ORDER_RESERVATION_TIMEOUT_MINUTES", 30)
        )

        for spec in line_specs:
            OrderLineItem.objects.create(
                order=order,
                variant=spec["variant"],
                quantity=spec["quantity"],
                product_name=spec["product_name"],
                variant_name=spec["variant_name"],
                sku=spec["sku"],
                weight_in_grams=spec["weight_in_grams"],
                mrp=spec["mrp"],
                unit_price=spec["unit_price"],
                line_subtotal=spec["line_subtotal"],
                pricing_tier_applied=spec["pricing_tier_applied"],
            )

            # Atomic reservation through InventoryService
            InventoryService.reserve_stock(
                variant=spec["variant"],
                quantity=spec["quantity"],
                expires_at=reservation_expiry,
                actor=user,
                reference_type="ORDER",
                reference_id=order.id,
            )

        # 10. Audit History & Clear Cart
        OrderStatusHistory.objects.create(
            order=order,
            from_status="",
            to_status=OrderStatus.PENDING_PAYMENT,
            actor=user,
            notes="Order created via checkout.",
        )
        cart.applied_coupon = None
        cart.save(update_fields=["applied_coupon", "updated_at"])
        CartService.clear_cart(cart)

        return order


class OrderStateMachine:
    """
    Finite state machine governing allowed order status transitions,
    inventory reservation releases, and post-confirmation restocks.
    """

    ALLOWED_TRANSITIONS = {
        OrderStatus.PENDING_PAYMENT: [
            OrderStatus.CONFIRMED,
            OrderStatus.CANCELLED,
            OrderStatus.FAILED,
        ],
        OrderStatus.CONFIRMED: [
            OrderStatus.PROCESSING,
            OrderStatus.CANCELLED,
            OrderStatus.REFUNDED,
        ],
        OrderStatus.PROCESSING: [
            OrderStatus.SHIPPED,
            OrderStatus.CANCELLED,
            OrderStatus.REFUNDED,
        ],
        OrderStatus.SHIPPED: [
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED,
            OrderStatus.REFUNDED,
        ],
        OrderStatus.DELIVERED: [
            OrderStatus.REFUNDED,
        ],
        OrderStatus.CANCELLED: [
            OrderStatus.REFUNDED,
        ],
        OrderStatus.FAILED: [],
        OrderStatus.REFUNDED: [],
    }

    @classmethod
    @transaction.atomic
    def cancel_order(cls, order: Order, actor=None, reason: str = "") -> Order:
        from apps.shipping.models import ShipmentStatus, ShipmentTrackingEvent

        # Deterministic locking: Order then Shipments (ordered by primary key)
        locked_order = Order.objects.select_for_update().get(id=order.id)
        locked_shipments = list(locked_order.shipments.select_for_update().order_by("id"))

        ineligible_shipment_statuses = {
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.OUT_FOR_DELIVERY,
            ShipmentStatus.DELIVERED,
            ShipmentStatus.RETURNED_TO_ORIGIN,
        }
        if any(s.status in ineligible_shipment_statuses for s in locked_shipments):
            raise OrderConflict(
                "Order cannot be cancelled because shipment(s) are already in transit or delivered."
            )

        if locked_order.order_status not in [
            OrderStatus.PENDING_PAYMENT,
            OrderStatus.CONFIRMED,
            OrderStatus.PROCESSING,
        ]:
            raise OrderConflict(
                f"Order in status '{locked_order.order_status}' cannot be cancelled."
            )

        prev_status = locked_order.order_status

        # Safely cancel active or un-dispatched shipments under lock
        cancellable_shipment_statuses = {
            ShipmentStatus.PENDING,
            ShipmentStatus.LABEL_GENERATED,
            ShipmentStatus.READY_FOR_PICKUP,
        }
        for shp in locked_shipments:
            if shp.status in cancellable_shipment_statuses:
                shp.status = ShipmentStatus.CANCELLED
                shp.save(update_fields=["status", "updated_at"])
                ShipmentTrackingEvent.objects.create(
                    shipment=shp,
                    status=ShipmentStatus.CANCELLED,
                    description=f"Shipment cancelled due to order cancellation: {reason or 'Order cancelled'}.",
                    event_timestamp=timezone.now(),
                )

        if prev_status == OrderStatus.PENDING_PAYMENT:
            # Active reservations are safely released
            active_reservations = StockReservation.objects.filter(
                reference_type="ORDER",
                reference_id=locked_order.id,
                status=ReservationStatus.ACTIVE,
            )
            for res in active_reservations:
                InventoryService.release_reservation(res.id, actor=actor, expired=False)

        elif prev_status in [OrderStatus.CONFIRMED, OrderStatus.PROCESSING]:
            # Consumed reservations cannot be released. Physical stock was already decremented.
            # Must restock physical items cleanly using InventoryService.add_stock.
            for line in locked_order.lines.select_related("variant"):
                InventoryService.add_stock(
                    variant=line.variant,
                    quantity=line.quantity,
                    actor=actor,
                    note=f"Restock from cancelled order {locked_order.order_number}",
                    movement_type=MovementType.CANCELLATION,
                    reference_type="ORDER_CANCELLATION",
                    reference_id=locked_order.id,
                )

        # Release any redeemed coupon usage
        from apps.promotions.services.coupon_service import CouponService

        CouponService.release_coupon_usage(locked_order)

        locked_order.order_status = OrderStatus.CANCELLED
        locked_order.cancelled_at = timezone.now()
        locked_order.cancellation_reason = reason
        locked_order.save(
            update_fields=["order_status", "cancelled_at", "cancellation_reason", "updated_at"]
        )

        OrderStatusHistory.objects.create(
            order=locked_order,
            from_status=prev_status,
            to_status=OrderStatus.CANCELLED,
            actor=actor,
            notes=reason or "Order cancelled.",
        )

        # Production Hardening: Customer cancellation notification hook
        transaction.on_commit(lambda: cls._dispatch_cancelled_notification(locked_order.id))

        # Phase 3.9: Statutory Credit Note generation if invoice was issued
        if prev_status in [OrderStatus.CONFIRMED, OrderStatus.PROCESSING]:
            transaction.on_commit(
                lambda: cls._dispatch_credit_note_on_cancellation(locked_order.id, reason)
            )

        # Synchronize in-memory instance
        order.order_status = locked_order.order_status
        order.cancelled_at = locked_order.cancelled_at
        order.cancellation_reason = locked_order.cancellation_reason
        return locked_order

    @classmethod
    @transaction.atomic
    def transition_status(cls, order: Order, to_status: str, actor=None, notes: str = "") -> Order:
        from_status = order.order_status
        allowed = cls.ALLOWED_TRANSITIONS.get(from_status, [])
        if to_status not in allowed:
            raise OrderConflict(f"Cannot transition order from '{from_status}' to '{to_status}'.")

        if to_status == OrderStatus.CANCELLED:
            from apps.shipping.models import ShipmentStatus

            shipments = list(order.shipments.all())
            is_rto_cancellation = bool(shipments) and all(
                s.status in (ShipmentStatus.RETURNED_TO_ORIGIN, ShipmentStatus.CANCELLED)
                for s in shipments
            )
            if is_rto_cancellation:
                order.order_status = OrderStatus.CANCELLED
                order.cancelled_at = timezone.now()
                order.cancellation_reason = notes or "Consignments returned to origin."
                order.save(
                    update_fields=[
                        "order_status",
                        "cancelled_at",
                        "cancellation_reason",
                        "updated_at",
                    ]
                )
                OrderStatusHistory.objects.create(
                    order=order,
                    from_status=from_status,
                    to_status=OrderStatus.CANCELLED,
                    notes=notes or "Order cancelled due to return to origin.",
                    actor=actor,
                )
                return order

            return cls.cancel_order(order, actor=actor, reason=notes)

        # Inventory actions upon confirmation
        if to_status == OrderStatus.CONFIRMED:
            active_reservations = StockReservation.objects.filter(
                reference_type="ORDER",
                reference_id=order.id,
                status=ReservationStatus.ACTIVE,
            )
            for res in active_reservations:
                InventoryService.consume_reservation(res.id, actor=actor)
            order.paid_at = timezone.now()

            # Production Hardening: Post-order automated orchestration
            transaction.on_commit(lambda: cls._dispatch_confirmed_orchestration(order.id))

        elif to_status == OrderStatus.SHIPPED:
            order.shipped_at = timezone.now()
            transaction.on_commit(lambda: cls._dispatch_shipped_notification(order.id))
        elif to_status == OrderStatus.DELIVERED:
            order.delivered_at = timezone.now()
            transaction.on_commit(lambda: cls._dispatch_delivered_notification(order.id))

        order.order_status = to_status
        update_fields = ["order_status", "updated_at"]
        if order.paid_at and to_status == OrderStatus.CONFIRMED:
            update_fields.append("paid_at")
        if order.shipped_at and to_status == OrderStatus.SHIPPED:
            update_fields.append("shipped_at")
        if order.delivered_at and to_status == OrderStatus.DELIVERED:
            update_fields.append("delivered_at")

        order.save(update_fields=update_fields)

        OrderStatusHistory.objects.create(
            order=order,
            from_status=from_status,
            to_status=to_status,
            actor=actor,
            notes=notes or f"Order transitioned to {to_status}.",
        )
        return order

    @classmethod
    def _dispatch_confirmed_orchestration(cls, order_id) -> None:
        """
        Dispatches background tasks for statutory GST invoice compilation
        and customer order confirmation notifications upon database transaction commit.
        """
        try:
            from apps.invoices.tasks import generate_invoice_for_order_task
            from apps.notifications.models import NotificationEvent
            from apps.notifications.tasks import send_order_notifications_task

            generate_invoice_for_order_task.delay(str(order_id))
            send_order_notifications_task.delay(str(order_id), NotificationEvent.ORDER_CONFIRMED)
        except Exception as exc:
            import logging

            logging.getLogger(__name__).exception(
                f"Failed to dispatch post-confirmation tasks for order {order_id}: {exc}"
            )

    @classmethod
    def _dispatch_shipped_notification(cls, order_id) -> None:
        """
        Dispatches background task for customer order shipment notifications
        upon database transaction commit.
        """
        try:
            from apps.notifications.models import NotificationEvent
            from apps.notifications.tasks import send_order_notifications_task

            send_order_notifications_task.delay(str(order_id), NotificationEvent.ORDER_SHIPPED)
        except Exception as exc:
            import logging

            logging.getLogger(__name__).exception(
                f"Failed to dispatch shipping notification for order {order_id}: {exc}"
            )

    @classmethod
    def _dispatch_delivered_notification(cls, order_id) -> None:
        """
        Dispatches background task for customer order delivery notifications
        upon database transaction commit.
        """
        try:
            from apps.notifications.models import NotificationEvent
            from apps.notifications.tasks import send_order_notifications_task

            send_order_notifications_task.delay(str(order_id), NotificationEvent.ORDER_DELIVERED)
        except Exception as exc:
            import logging

            logging.getLogger(__name__).exception(
                f"Failed to dispatch delivery notification for order {order_id}: {exc}"
            )

    @classmethod
    def _dispatch_cancelled_notification(cls, order_id) -> None:
        """
        Dispatches background task for customer order cancellation notifications
        upon database transaction commit.
        """
        try:
            from apps.notifications.models import NotificationEvent
            from apps.notifications.tasks import send_order_notifications_task

            send_order_notifications_task.delay(str(order_id), NotificationEvent.ORDER_CANCELLED)
        except Exception as exc:
            import logging

            logging.getLogger(__name__).exception(
                f"Failed to dispatch cancellation notification for order {order_id}: {exc}"
            )

    @classmethod
    def _dispatch_credit_note_on_cancellation(cls, order_id, reason: str = "") -> None:
        """
        Dispatches background task to generate a statutory GST Credit Note if an invoice exists.
        """
        try:
            from apps.invoices.models import CreditNoteReason
            from apps.invoices.tasks import generate_credit_note_for_order_task

            generate_credit_note_for_order_task.delay(
                str(order_id),
                CreditNoteReason.ORDER_CANCELLATION,
                reason or "Order cancelled after invoice issuance.",
            )
        except Exception as exc:
            import logging

            logging.getLogger(__name__).exception(
                f"Failed to dispatch credit note task for order {order_id}: {exc}"
            )


# Re-export OrderService for module convenience
