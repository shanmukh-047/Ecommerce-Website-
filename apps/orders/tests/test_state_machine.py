from django.test import TestCase

from apps.catalog.services import ReviewService
from apps.inventory.models import ReservationStatus, StockItem, StockReservation
from apps.inventory.services import InventoryService
from apps.inventory.tests.factories import create_variant
from apps.orders.exceptions import OrderConflict
from apps.orders.models import OrderStatus
from apps.orders.services import CheckoutService, OrderStateMachine
from apps.orders.tests.factories import (
    add_to_cart,
    create_order_address,
    create_order_user,
    create_staff_user,
)


class OrderStateMachineTests(TestCase):
    def setUp(self):
        self.user = create_order_user()
        self.staff = create_staff_user()
        self.address = create_order_address(self.user)
        self.variant = create_variant("fsm")
        InventoryService.add_stock(self.variant, 50)
        add_to_cart(self.user, self.variant, 4)
        self.order = CheckoutService.create_order_from_cart(
            user=self.user,
            shipping_address_id=self.address.id,
        )

    def test_full_successful_order_lifecycle(self):
        # 1. PENDING_PAYMENT -> CONFIRMED
        order = OrderStateMachine.transition_status(
            self.order, OrderStatus.CONFIRMED, actor=self.staff, notes="Payment verified"
        )
        self.assertEqual(order.order_status, OrderStatus.CONFIRMED)
        self.assertIsNotNone(order.paid_at)

        res = StockReservation.objects.get(reference_type="ORDER", reference_id=order.id)
        self.assertEqual(res.status, ReservationStatus.CONSUMED)

        stock = StockItem.objects.get(variant=self.variant)
        self.assertEqual(stock.quantity_on_hand, 46)  # 50 - 4
        self.assertEqual(stock.quantity_reserved, 0)

        # 2. CONFIRMED -> PROCESSING
        order = OrderStateMachine.transition_status(
            order, OrderStatus.PROCESSING, actor=self.staff, notes="Packing in warehouse"
        )
        self.assertEqual(order.order_status, OrderStatus.PROCESSING)

        # 3. PROCESSING -> SHIPPED
        order = OrderStateMachine.transition_status(
            order, OrderStatus.SHIPPED, actor=self.staff, notes="Dispatched via BlueDart"
        )
        self.assertEqual(order.order_status, OrderStatus.SHIPPED)
        self.assertIsNotNone(order.shipped_at)

        # 4. SHIPPED -> DELIVERED
        order = OrderStateMachine.transition_status(
            order, OrderStatus.DELIVERED, actor=self.staff, notes="Delivered to customer"
        )
        self.assertEqual(order.order_status, OrderStatus.DELIVERED)
        self.assertIsNotNone(order.delivered_at)

        # Check all history logs
        self.assertEqual(order.status_history.count(), 5)  # Initial + 4 transitions

    def test_invalid_status_transition_blocked(self):
        # Direct jump from PENDING_PAYMENT to SHIPPED
        with self.assertRaises(OrderConflict) as ctx:
            OrderStateMachine.transition_status(self.order, OrderStatus.SHIPPED, actor=self.staff)
        self.assertIn("Cannot transition order", str(ctx.exception))

        # Direct jump from PENDING_PAYMENT to DELIVERED
        with self.assertRaises(OrderConflict):
            OrderStateMachine.transition_status(self.order, OrderStatus.DELIVERED, actor=self.staff)

    def test_cancel_pending_payment_order_releases_reservation(self):
        # Initial: 50 on hand, 4 reserved, 46 available
        stock_before = StockItem.objects.get(variant=self.variant)
        self.assertEqual(stock_before.quantity_reserved, 4)
        self.assertEqual(stock_before.quantity_available, 46)

        order = OrderStateMachine.cancel_order(
            self.order, actor=self.user, reason="Customer changed mind"
        )
        self.assertEqual(order.order_status, OrderStatus.CANCELLED)
        self.assertIsNotNone(order.cancelled_at)
        self.assertEqual(order.cancellation_reason, "Customer changed mind")

        # Reservation is released
        res = StockReservation.objects.get(reference_type="ORDER", reference_id=order.id)
        self.assertEqual(res.status, ReservationStatus.RELEASED)

        stock_after = StockItem.objects.get(variant=self.variant)
        self.assertEqual(stock_after.quantity_reserved, 0)
        self.assertEqual(stock_after.quantity_available, 50)

    def test_cancel_confirmed_order_restocks_physical_inventory(self):
        # First confirm order (consumes reservation, quantity_on_hand becomes 46)
        order = OrderStateMachine.transition_status(
            self.order, OrderStatus.CONFIRMED, actor=self.staff
        )
        stock_after_confirm = StockItem.objects.get(variant=self.variant)
        self.assertEqual(stock_after_confirm.quantity_on_hand, 46)

        # Now cancel confirmed order (should restock via add_stock, restoring quantity_on_hand to 50)
        cancelled_order = OrderStateMachine.cancel_order(
            order, actor=self.staff, reason="Customer requested refund before dispatch"
        )
        self.assertEqual(cancelled_order.order_status, OrderStatus.CANCELLED)

        stock_after_cancel = StockItem.objects.get(variant=self.variant)
        self.assertEqual(stock_after_cancel.quantity_on_hand, 50)

    def test_cancel_shipped_order_blocked(self):
        order = OrderStateMachine.transition_status(
            self.order, OrderStatus.CONFIRMED, actor=self.staff
        )
        order = OrderStateMachine.transition_status(order, OrderStatus.PROCESSING, actor=self.staff)
        order = OrderStateMachine.transition_status(order, OrderStatus.SHIPPED, actor=self.staff)

        with self.assertRaises(OrderConflict) as ctx:
            OrderStateMachine.cancel_order(order, actor=self.staff, reason="Too late to cancel")
        self.assertIn("cannot be cancelled", str(ctx.exception))

    def test_review_service_integration_verified_purchase(self):
        product = self.variant.product

        # Before delivery, verified purchase is False
        self.assertFalse(ReviewService.verify_user_purchase(self.user, product))

        # Transition through to DELIVERED
        order = OrderStateMachine.transition_status(
            self.order, OrderStatus.CONFIRMED, actor=self.staff
        )
        order = OrderStateMachine.transition_status(order, OrderStatus.PROCESSING, actor=self.staff)
        order = OrderStateMachine.transition_status(order, OrderStatus.SHIPPED, actor=self.staff)
        OrderStateMachine.transition_status(order, OrderStatus.DELIVERED, actor=self.staff)

        # Once DELIVERED, verified purchase is True for this user and product
        self.assertTrue(ReviewService.verify_user_purchase(self.user, product))

        # For another user, still False
        other_user = create_order_user(email="other_reviewer@example.com", phone="9876543291")
        self.assertFalse(ReviewService.verify_user_purchase(other_user, product))

        # For another product, still False
        other_variant = create_variant("other_spice")
        self.assertFalse(ReviewService.verify_user_purchase(self.user, other_variant.product))
