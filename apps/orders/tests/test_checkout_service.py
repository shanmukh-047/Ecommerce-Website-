from decimal import Decimal

from django.test import TestCase

from apps.cart.models import CartItem
from apps.cart.services import CartService
from apps.catalog.models import WholesaleTierPricing
from apps.inventory.models import ReservationStatus, StockItem, StockReservation
from apps.inventory.services import InventoryService
from apps.inventory.tests.factories import create_variant
from apps.orders.exceptions import OrderConflict
from apps.orders.models import OrderStatus
from apps.orders.services import CheckoutService
from apps.orders.tests.factories import (
    add_to_cart,
    create_order_address,
    create_order_user,
    create_wholesale_user,
)


class CheckoutServiceTests(TestCase):
    def setUp(self):
        self.user = create_order_user()
        self.address = create_order_address(self.user)
        self.variant_1 = create_variant("chilli")
        self.variant_2 = create_variant("turmeric")
        InventoryService.add_stock(self.variant_1, 50)
        InventoryService.add_stock(self.variant_2, 30)

    def test_create_order_retail_success(self):
        add_to_cart(self.user, self.variant_1, 2)
        order = CheckoutService.create_order_from_cart(
            user=self.user,
            shipping_address_id=self.address.id,
            customer_notes="Deliver between 10am and 1pm",
        )

        self.assertIsNotNone(order)
        self.assertTrue(order.order_number.startswith("BMP-"))
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.order_status, OrderStatus.PENDING_PAYMENT)
        self.assertFalse(order.is_wholesale_order)
        self.assertEqual(order.total_quantity, 2)
        self.assertEqual(order.items_subtotal, Decimal("180.00"))
        self.assertEqual(order.grand_total, Decimal("180.00"))
        self.assertEqual(order.customer_notes, "Deliver between 10am and 1pm")

        # Snapshot checks
        self.assertEqual(order.shipping_recipient_name, self.address.recipient_name)
        self.assertEqual(order.shipping_address_line_1, self.address.address_line_1)
        self.assertEqual(order.shipping_city, self.address.city)
        self.assertEqual(order.shipping_state, self.address.state)
        self.assertEqual(order.shipping_pincode, self.address.pincode)

        # Line items
        self.assertEqual(order.lines.count(), 1)
        line = order.lines.first()
        self.assertEqual(line.variant, self.variant_1)
        self.assertEqual(line.quantity, 2)
        self.assertEqual(line.mrp, Decimal("100.00"))
        self.assertEqual(line.unit_price, Decimal("90.00"))
        self.assertEqual(line.line_subtotal, Decimal("180.00"))
        self.assertEqual(line.pricing_tier_applied, "RETAIL")

        # Cart cleared
        self.assertEqual(CartItem.objects.filter(cart__user=self.user).count(), 0)

        # Inventory reservation created
        reservation = StockReservation.objects.filter(
            reference_type="ORDER",
            reference_id=order.id,
        ).first()
        self.assertIsNotNone(reservation)
        self.assertEqual(reservation.status, ReservationStatus.ACTIVE)
        self.assertEqual(reservation.quantity, 2)

        stock_item = StockItem.objects.get(variant=self.variant_1)
        self.assertEqual(stock_item.quantity_reserved, 2)
        self.assertEqual(stock_item.quantity_available, 48)

        # Order history
        self.assertEqual(order.status_history.count(), 1)
        history = order.status_history.first()
        self.assertEqual(history.to_status, OrderStatus.PENDING_PAYMENT)
        self.assertEqual(history.actor, self.user)

    def test_create_order_wholesale_tier_pricing(self):
        wholesale_user = create_wholesale_user()
        ws_address = create_order_address(wholesale_user)

        WholesaleTierPricing.objects.create(
            variant=self.variant_1,
            min_quantity=10,
            wholesale_price_per_unit=Decimal("70.00"),
        )

        add_to_cart(wholesale_user, self.variant_1, 10)
        order = CheckoutService.create_order_from_cart(
            user=wholesale_user,
            shipping_address_id=ws_address.id,
        )

        self.assertTrue(order.is_wholesale_order)
        self.assertEqual(order.items_subtotal, Decimal("700.00"))
        self.assertEqual(order.grand_total, Decimal("700.00"))

        line = order.lines.first()
        self.assertEqual(line.unit_price, Decimal("70.00"))
        self.assertEqual(line.line_subtotal, Decimal("700.00"))
        self.assertEqual(line.pricing_tier_applied, "WHOLESALE")

    def test_create_order_multiple_items_and_deterministic_order(self):
        add_to_cart(self.user, self.variant_1, 3)
        add_to_cart(self.user, self.variant_2, 2)

        order = CheckoutService.create_order_from_cart(
            user=self.user,
            shipping_address_id=self.address.id,
        )

        self.assertEqual(order.total_quantity, 5)
        self.assertEqual(order.lines.count(), 2)

        # Subtotal: 3 * 90 + 2 * 90 = 270 + 180 = 450
        self.assertEqual(order.items_subtotal, Decimal("450.00"))
        self.assertEqual(order.grand_total, Decimal("450.00"))

        res_1 = StockReservation.objects.get(
            reference_id=order.id, stock_item__variant=self.variant_1
        )
        res_2 = StockReservation.objects.get(
            reference_id=order.id, stock_item__variant=self.variant_2
        )
        self.assertEqual(res_1.quantity, 3)
        self.assertEqual(res_2.quantity, 2)

    def test_checkout_empty_cart_raises_conflict(self):
        CartService.get_or_create_user_cart(self.user)
        with self.assertRaises(OrderConflict) as ctx:
            CheckoutService.create_order_from_cart(
                user=self.user,
                shipping_address_id=self.address.id,
            )
        self.assertIn("Cart is empty", str(ctx.exception))

    def test_checkout_unauthenticated_raises_conflict(self):
        with self.assertRaises(OrderConflict) as ctx:
            CheckoutService.create_order_from_cart(
                user=None,
                shipping_address_id=self.address.id,
            )
        self.assertIn("Authentication is required", str(ctx.exception))

    def test_checkout_address_idor_prevention(self):
        other_user = create_order_user(email="other@example.com", phone="9876543299")
        other_address = create_order_address(other_user)

        add_to_cart(self.user, self.variant_1, 1)
        with self.assertRaises(OrderConflict) as ctx:
            CheckoutService.create_order_from_cart(
                user=self.user,
                shipping_address_id=other_address.id,
            )
        self.assertIn("Valid shipping address", str(ctx.exception))

    def test_checkout_inactive_variant_raises_conflict(self):
        add_to_cart(self.user, self.variant_1, 1)
        self.variant_1.is_active = False
        self.variant_1.save()

        with self.assertRaises(OrderConflict) as ctx:
            CheckoutService.create_order_from_cart(
                user=self.user,
                shipping_address_id=self.address.id,
            )
        self.assertIn("no longer active", str(ctx.exception))

    def test_checkout_insufficient_stock_raises_conflict(self):
        add_to_cart(self.user, self.variant_1, 5)
        # Manually reduce available stock after adding to cart
        stock = StockItem.objects.get(variant=self.variant_1)
        stock.quantity_on_hand = 3
        stock.save()

        with self.assertRaises(OrderConflict) as ctx:
            CheckoutService.create_order_from_cart(
                user=self.user,
                shipping_address_id=self.address.id,
            )
        self.assertIn("Insufficient available inventory", str(ctx.exception))

    def test_order_number_generation_uniqueness(self):
        numbers = {CheckoutService.generate_order_number() for _ in range(20)}
        self.assertEqual(len(numbers), 20)
        for num in numbers:
            self.assertTrue(num.startswith("BMP-"))
