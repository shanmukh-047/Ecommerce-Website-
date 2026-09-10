"""
Concurrency and dispatch race condition tests for OrderStateMachine.cancel_order (ISSUE-001).
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import IndianStates, User
from apps.catalog.models import Category, Product, ProductVariant
from apps.inventory.models import StockItem
from apps.orders.exceptions import OrderConflict
from apps.orders.models import Order, OrderLineItem, OrderStatus
from apps.orders.services.checkout_service import OrderStateMachine
from apps.shipping.models import CourierProvider, Shipment, ShipmentStatus
from apps.shipping.services.shipping_service import ShippingService


class OrderCancellationConcurrencyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="cancellation_test@bharathmasala.com",
            phone_number="+919876543001",
            first_name="Concurrency",
            last_name="Tester",
        )
        self.category = Category.objects.create(name="Spices", slug="spices-cancel")
        self.product = Product.objects.create(
            category=self.category,
            name="Turmeric Powder",
            slug="turmeric-powder-cancel",
            hsn_code="0910",
            gst_rate=Decimal("5.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="500g",
            sku="TURM-500G-CANCEL",
            weight_in_grams=500,
            mrp=Decimal("150.00"),
            selling_price=Decimal("150.00"),
        )
        self.stock = StockItem.objects.create(
            variant=self.variant,
            quantity_on_hand=100,
            quantity_reserved=0,
        )

    def _create_order_with_line(self, status=OrderStatus.CONFIRMED, quantity=5):
        order = Order.objects.create(
            order_number=f"BMP-ORD-{timezone.now().timestamp()}",
            user=self.user,
            order_status=status,
            items_subtotal=Decimal("750.00"),
            tax_amount=Decimal("37.50"),
            shipping_fee=Decimal("50.00"),
            grand_total=Decimal("800.00"),
            currency="INR",
            total_quantity=quantity,
            shipping_recipient_name="Concurrency Tester",
            shipping_phone_number="+919876543001",
            shipping_address_line_1="123 Test St",
            shipping_city="Bangalore",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="560001",
        )
        OrderLineItem.objects.create(
            order=order,
            variant=self.variant,
            quantity=quantity,
            product_name="Turmeric Powder",
            variant_name="500g",
            sku=self.variant.sku,
            weight_in_grams=500,
            mrp=Decimal("150.00"),
            unit_price=Decimal("150.00"),
            line_subtotal=Decimal("750.00"),
            pricing_tier_applied="RETAIL",
        )
        return order

    def _create_shipment(self, order, status=ShipmentStatus.LABEL_GENERATED):
        return Shipment.objects.create(
            shipment_number=f"SHP-{timezone.now().timestamp()}",
            order=order,
            status=status,
            courier_name=CourierProvider.DELHIVERY,
            awb_number=f"AWB-{timezone.now().timestamp()}",
            weight_in_grams=500,
            shipping_recipient_name=order.shipping_recipient_name,
            shipping_phone_number=order.shipping_phone_number,
            shipping_address_line_1=order.shipping_address_line_1,
            shipping_city=order.shipping_city,
            shipping_state=order.shipping_state,
            shipping_pincode=order.shipping_pincode,
        )

    def test_cancellation_before_dispatch_succeeds_and_cancels_pending_shipment(self):
        """1. Cancellation before shipment dispatch succeeds and marks shipment CANCELLED."""
        order = self._create_order_with_line(status=OrderStatus.CONFIRMED, quantity=3)
        shipment = self._create_shipment(order=order, status=ShipmentStatus.LABEL_GENERATED)

        initial_stock = self.stock.quantity_on_hand
        cancelled_order = OrderStateMachine.cancel_order(
            order, actor=self.user, reason="Customer changed mind before dispatch."
        )

        self.assertEqual(cancelled_order.order_status, OrderStatus.CANCELLED)
        shipment.refresh_from_db()
        self.assertEqual(shipment.status, ShipmentStatus.CANCELLED)

        self.stock.refresh_from_db()
        # Physical stock should be restocked cleanly
        self.assertEqual(self.stock.quantity_on_hand, initial_stock + 3)

    def test_cancellation_after_dispatch_raises_order_conflict(self):
        """2. Cancellation after courier dispatch (IN_TRANSIT) is strictly rejected."""
        order = self._create_order_with_line(status=OrderStatus.PROCESSING, quantity=4)
        self._create_shipment(order=order, status=ShipmentStatus.IN_TRANSIT)

        initial_stock = self.stock.quantity_on_hand
        with self.assertRaises(OrderConflict) as ctx:
            OrderStateMachine.cancel_order(order, actor=self.user, reason="Try cancel in transit")

        self.assertIn("already in transit or delivered", str(ctx.exception))

        # Invariants preserved
        order.refresh_from_db()
        self.assertEqual(order.order_status, OrderStatus.PROCESSING)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity_on_hand, initial_stock)

    def test_cancellation_racing_with_shipment_dispatch_blocked_under_lock(self):
        """3. Simultaneous shipment dispatch and cancellation: whichever acquires lock first prevails."""
        order = self._create_order_with_line(status=OrderStatus.PROCESSING, quantity=2)
        shipment = self._create_shipment(order=order, status=ShipmentStatus.LABEL_GENERATED)

        # Simulate race condition: shipment status is transitioned to IN_TRANSIT
        # before cancellation acquires the lock
        ShippingService.transition_shipment_status(
            shipment=shipment,
            to_status=ShipmentStatus.IN_TRANSIT,
            description="Carrier picked up package.",
        )

        # Now when cancellation attempts to run, it re-queries under select_for_update and observes IN_TRANSIT
        with self.assertRaises(OrderConflict):
            OrderStateMachine.cancel_order(order, actor=self.user, reason="Late cancel")

        order.refresh_from_db()
        self.assertEqual(order.order_status, OrderStatus.SHIPPED)

    def test_no_double_inventory_restock_on_repeated_cancellation(self):
        """4. Repeated cancellation attempts cannot double-restock inventory."""
        order = self._create_order_with_line(status=OrderStatus.CONFIRMED, quantity=5)
        initial_stock = self.stock.quantity_on_hand

        # First cancellation succeeds
        OrderStateMachine.cancel_order(order, actor=self.user, reason="First cancel")
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity_on_hand, initial_stock + 5)

        # Second cancellation attempt must be rejected by status check
        with self.assertRaises(OrderConflict):
            OrderStateMachine.cancel_order(order, actor=self.user, reason="Duplicate cancel")

        # Inventory must NOT have been incremented again
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity_on_hand, initial_stock + 5)
