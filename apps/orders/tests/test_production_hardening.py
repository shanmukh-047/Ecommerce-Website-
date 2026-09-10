"""
Tests for Production Hardening:
- Automated post-order orchestration (CONFIRMED -> Invoice generation + Notification)
- Shipping lifecycle notification hooks (IN_TRANSIT -> SHIPPED, DELIVERED -> DELIVERED)
- Order cancellation notification hooks (CANCELLED -> Notification)
- Atomic transaction boundary and rollback protection
- Fail-fast production gateway configuration enforcement
"""

from decimal import Decimal
from unittest.mock import patch

from django.db import transaction
from django.test import TestCase

from apps.accounts.models import IndianStates, User
from apps.catalog.models import Category, Product, ProductVariant
from apps.inventory.models import StockItem
from apps.orders.models import Order, OrderLineItem, OrderStatus
from apps.orders.services import OrderStateMachine
from apps.shipping.models import CourierProvider, ShipmentStatus
from apps.shipping.services import ShippingService


class ProductionHardeningOrchestrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="hardening_test@example.com",
            phone_number="+919876543210",
            first_name="Hardening",
            last_name="Tester",
        )
        self.category = Category.objects.create(name="Spices", slug="spices-hardening")
        self.product = Product.objects.create(
            category=self.category,
            name="Garam Masala",
            slug="garam-masala-hardening",
            hsn_code="0910",
            gst_rate=Decimal("5.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="250g",
            sku="GM-250G-HARDEN",
            weight_in_grams=250,
            mrp=Decimal("150.00"),
            selling_price=Decimal("150.00"),
        )
        self.stock_item = StockItem.objects.create(
            variant=self.variant,
            quantity_on_hand=100,
            quantity_reserved=0,
        )

        self.order = Order.objects.create(
            order_number="BMP-HARDEN-001",
            user=self.user,
            order_status=OrderStatus.PENDING_PAYMENT,
            shipping_recipient_name="Hardening Tester",
            shipping_phone_number="+919876543210",
            shipping_address_line_1="Station Road",
            shipping_city="Sirsi",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="581401",
            items_subtotal=Decimal("300.00"),
            shipping_fee=Decimal("0.00"),
            grand_total=Decimal("300.00"),
            total_quantity=2,
            total_weight_in_grams=500,
        )
        self.line_item = OrderLineItem.objects.create(
            order=self.order,
            variant=self.variant,
            product_name="Garam Masala",
            variant_name="250g",
            sku="GM-250G-HARDEN",
            weight_in_grams=250,
            quantity=2,
            mrp=Decimal("150.00"),
            unit_price=Decimal("150.00"),
            line_subtotal=Decimal("300.00"),
        )

    @patch("apps.notifications.tasks.send_order_notifications_task.delay")
    @patch("apps.invoices.tasks.generate_invoice_for_order_task.delay")
    def test_order_confirmation_triggers_invoice_and_notification(
        self, mock_invoice_task, mock_notif_task
    ):
        """
        Confirming an order must trigger both invoice generation and order confirmation
        notifications upon successful transaction commit.
        """
        with self.captureOnCommitCallbacks(execute=True):
            OrderStateMachine.transition_status(self.order, OrderStatus.CONFIRMED)

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.CONFIRMED)
        mock_invoice_task.assert_called_once_with(str(self.order.id))
        mock_notif_task.assert_called_once_with(str(self.order.id), "ORDER_CONFIRMED")

    @patch("apps.notifications.tasks.send_order_notifications_task.delay")
    def test_order_cancellation_triggers_notification(self, mock_notif_task):
        """
        Cancelling an order must trigger an ORDER_CANCELLED notification upon commit.
        """
        with self.captureOnCommitCallbacks(execute=True):
            OrderStateMachine.cancel_order(self.order, reason="Customer cancelled")

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.CANCELLED)
        mock_notif_task.assert_called_once_with(str(self.order.id), "ORDER_CANCELLED")

    @patch("apps.notifications.tasks.send_order_notifications_task.delay")
    def test_shipping_in_transit_triggers_shipped_notification(self, mock_notif_task):
        """
        Transitioning a shipment to IN_TRANSIT advances order to SHIPPED and
        triggers ORDER_SHIPPED notification upon transaction commit.
        """
        OrderStateMachine.transition_status(self.order, OrderStatus.CONFIRMED)
        shipment = ShippingService.create_shipment(
            order=self.order,
            courier_name=CourierProvider.MANUAL,
        )

        with self.captureOnCommitCallbacks(execute=True):
            ShippingService.transition_shipment_status(
                shipment,
                ShipmentStatus.IN_TRANSIT,
                location="Hub 1",
                description="Package departed facility",
            )

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.SHIPPED)
        mock_notif_task.assert_called_with(str(self.order.id), "ORDER_SHIPPED")

    @patch("apps.notifications.tasks.send_order_notifications_task.delay")
    def test_shipping_delivered_triggers_delivered_notification(self, mock_notif_task):
        """
        Transitioning final shipment to DELIVERED advances order to DELIVERED and
        triggers ORDER_DELIVERED notification upon transaction commit.
        """
        OrderStateMachine.transition_status(self.order, OrderStatus.CONFIRMED)
        shipment = ShippingService.create_shipment(
            order=self.order,
            courier_name=CourierProvider.MANUAL,
        )
        ShippingService.transition_shipment_status(shipment, ShipmentStatus.IN_TRANSIT)

        with self.captureOnCommitCallbacks(execute=True):
            ShippingService.transition_shipment_status(
                shipment,
                ShipmentStatus.DELIVERED,
                location="Customer Doorstep",
                description="Handed over to customer",
            )

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.DELIVERED)
        mock_notif_task.assert_called_with(str(self.order.id), "ORDER_DELIVERED")

    @patch("apps.notifications.tasks.send_order_notifications_task.delay")
    @patch("apps.invoices.tasks.generate_invoice_for_order_task.delay")
    def test_transaction_rollback_prevents_task_execution(self, mock_invoice_task, mock_notif_task):
        """
        If a transaction rolls back due to an exception, transaction.on_commit
        callbacks must NOT be executed, preventing orphaned tasks.
        """
        try:
            with transaction.atomic():
                OrderStateMachine.transition_status(self.order, OrderStatus.CONFIRMED)
                raise RuntimeError("Simulated mid-transaction failure")
        except RuntimeError:
            pass

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.PENDING_PAYMENT)
        mock_invoice_task.assert_not_called()
        mock_notif_task.assert_not_called()


class ProductionSettingsFailFastTests(TestCase):
    def test_production_settings_validation_rejects_placeholders(self):
        """
        Importing production settings with default placeholder Razorpay credentials
        must raise a RuntimeError to prevent accidental deployment with dummy keys.
        """
        import importlib
        import os

        env_overrides = {
            "DJANGO_SECRET_KEY": "a" * 60,
            "DJANGO_ALLOWED_HOSTS": "bharathmasala.com",
            "DATABASE_URL": "postgres://user:pass@localhost:5432/db",
            "RAZORPAY_KEY_ID": "rzp_test_placeholder",
            "RAZORPAY_KEY_SECRET": "test_secret_placeholder",
            "RAZORPAY_WEBHOOK_SECRET": "test_webhook_secret",
        }
        with patch.dict(os.environ, env_overrides):
            with self.assertRaises(RuntimeError) as cm:
                import config.settings.production

                importlib.reload(config.settings.production)
            self.assertIn("RAZORPAY_KEY_ID", str(cm.exception))
