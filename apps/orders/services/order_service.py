import logging
from typing import List

from django.db import connection, transaction
from django.utils import timezone

from apps.inventory.models import ReservationStatus, StockReservation
from apps.inventory.services import InventoryService
from apps.orders.models import Order, OrderLineItem, OrderStatus, OrderStatusHistory

logger = logging.getLogger(__name__)


class OrderService:
    """
    Authoritative order domain service coordinating order lifecycle queries,
    background abandoned order recovery, and reservation expiry.
    """

    @classmethod
    def expire_abandoned_orders(cls, batch_size: int = 100) -> List[str]:
        """
        Identifies orders in PENDING_PAYMENT status with expired active reservations,
        safely acquires row-level locks, releases reservations with expired=True,
        and transitions orders to FAILED with audit history.

        Executes with per-order atomic transaction isolation so that a failure on
        one order does not prevent other orders in the batch from completing.
        """
        now = timezone.now()

        # Step 1: Candidate discovery: Find distinct order IDs with expired active reservations
        candidate_order_ids = list(
            StockReservation.objects.filter(
                reference_type="ORDER",
                status=ReservationStatus.ACTIVE,
                expires_at__lte=now,
            )
            .values_list("reference_id", flat=True)
            .distinct()[:batch_size]
        )

        if not candidate_order_ids:
            return []

        expired_order_numbers = []
        lock_kwargs = (
            {"skip_locked": True} if connection.features.has_select_for_update_skip_locked else {}
        )

        for order_id in candidate_order_ids:
            if not order_id:
                continue
            try:
                # Per-order transaction isolation
                with transaction.atomic():
                    # 1. Lock Order FIRST (Universal Lock Hierarchy: Order -> StockReservation -> StockItem)
                    order = (
                        Order.objects.select_for_update(**lock_kwargs)
                        .filter(pk=order_id, order_status=OrderStatus.PENDING_PAYMENT)
                        .first()
                    )
                    if not order:
                        # Order locked by another worker (skip_locked), or already confirmed/failed
                        continue

                    # 2. Lock and fetch all active reservations for this order
                    active_reservations = list(
                        StockReservation.objects.select_for_update()
                        .filter(
                            reference_type="ORDER",
                            reference_id=order.id,
                            status=ReservationStatus.ACTIVE,
                        )
                        .order_by("id")
                    )

                    # Guard: verify at least one reservation is actually expired
                    if not any(r.expires_at <= now for r in active_reservations):
                        continue

                    # 3. Release each reservation with expired=True
                    for res in active_reservations:
                        InventoryService.release_reservation(
                            reservation_id=res.id,
                            actor=None,
                            expired=True,
                        )

                    # 4. Transition Order to FAILED
                    order.order_status = OrderStatus.FAILED
                    order.save(update_fields=["order_status", "updated_at"])

                    # 4b. Release any redeemed coupon usage
                    from apps.promotions.services.coupon_service import CouponService

                    CouponService.release_coupon_usage(order)

                    # 5. Create OrderStatusHistory
                    OrderStatusHistory.objects.create(
                        order=order,
                        from_status=OrderStatus.PENDING_PAYMENT,
                        to_status=OrderStatus.FAILED,
                        actor=None,
                        notes="Order automatically failed because payment reservation expired.",
                    )

                    expired_order_numbers.append(order.order_number)
                    logger.info(
                        "Abandoned order %s failed and reservations expired.",
                        order.order_number,
                    )
            except Exception as e:
                logger.error(
                    "Error expiring abandoned order %s: %s",
                    order_id,
                    e,
                    exc_info=True,
                )
                continue

        return expired_order_numbers

    @classmethod
    def has_user_purchased_product(cls, user, product) -> bool:
        """
        Determines whether the given authenticated user has purchased and received
        (DELIVERED) any variant of the specified product.
        """
        if not user or not getattr(user, "is_authenticated", False):
            return False

        return OrderLineItem.objects.filter(
            order__user=user,
            order__order_status=OrderStatus.DELIVERED,
            variant__product=product,
        ).exists()
