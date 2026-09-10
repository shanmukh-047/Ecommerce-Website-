from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import IndianStates
from apps.catalog.models import Category, Product, ProductVariant
from apps.inventory.models import StockItem
from apps.invoices.models import CreditNoteReason
from apps.orders.models import Order, OrderLineItem, OrderStatus
from apps.orders.services.checkout_service import OrderStateMachine
from apps.payments.models import Payment, PaymentGateway, PaymentStatus
from apps.shipping.models import CourierProvider, ShipmentStatus
from apps.shipping.services.shipping_service import ShippingService

User = get_user_model()


class ShipmentRTOAutomationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+919876543210",
            email="rto_tester@bharathmasala.com",
            first_name="RTO",
            last_name="Tester",
        )
        self.category = Category.objects.create(name="Spices", slug="spices")
        self.product = Product.objects.create(
            name="Sambar Powder",
            slug="sambar-powder",
            category=self.category,
            hsn_code="0910",
            gst_rate=Decimal("5.00"),
        )
        self.variant1 = ProductVariant.objects.create(
            product=self.product,
            sku="SAMBAR-100G",
            variant_name="100g",
            weight_in_grams=100,
            selling_price=Decimal("50.00"),
            mrp=Decimal("60.00"),
        )
        self.variant2 = ProductVariant.objects.create(
            product=self.product,
            sku="SAMBAR-500G",
            variant_name="500g",
            weight_in_grams=500,
            selling_price=Decimal("200.00"),
            mrp=Decimal("220.00"),
        )
        self.stock1 = StockItem.objects.create(
            variant=self.variant1,
            quantity_on_hand=50,
            quantity_reserved=0,
        )
        self.stock2 = StockItem.objects.create(
            variant=self.variant2,
            quantity_on_hand=30,
            quantity_reserved=0,
        )

    @patch("apps.notifications.tasks.send_order_notifications_task.delay")
    @patch("apps.invoices.tasks.generate_credit_note_for_order_task.delay")
    def test_full_rto_transitions_order_and_refunds_captured_payment(self, mock_cn, mock_notif):
        order = Order.objects.create(
            order_number=f"BMP-RTO-FULL-{timezone.now().timestamp()}",
            user=self.user,
            order_status=OrderStatus.CONFIRMED,
            shipping_recipient_name="RTO Receiver",
            shipping_phone_number="+919876543210",
            shipping_address_line_1="Market Road",
            shipping_city="Sirsi",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="581401",
            items_subtotal=Decimal("100.00"),
            tax_amount=Decimal("5.00"),
            shipping_fee=Decimal("0.00"),
            grand_total=Decimal("105.00"),
            total_quantity=2,
            total_weight_in_grams=200,
        )
        OrderLineItem.objects.create(
            order=order,
            variant=self.variant1,
            product_name="Sambar Powder",
            variant_name="100g",
            sku="SAMBAR-100G",
            weight_in_grams=100,
            quantity=2,
            mrp=Decimal("60.00"),
            unit_price=Decimal("50.00"),
            line_subtotal=Decimal("100.00"),
        )
        payment = Payment.objects.create(
            payment_number=f"PAY-RTO-{timezone.now().timestamp()}",
            order=order,
            user=self.user,
            status=PaymentStatus.CAPTURED,
            amount=Decimal("105.00"),
            currency="INR",
            gateway=PaymentGateway.RAZORPAY,
            gateway_payment_id="pay_rto_test_123",
        )

        shipment = ShippingService.create_shipment(
            order=order,
            courier_name=CourierProvider.MANUAL,
        )
        OrderStateMachine.transition_status(order, OrderStatus.PROCESSING)
        OrderStateMachine.transition_status(order, OrderStatus.SHIPPED)
        ShippingService.transition_shipment_status(shipment, to_status=ShipmentStatus.IN_TRANSIT)

        initial_stock = StockItem.objects.get(variant=self.variant1).quantity_on_hand

        with self.captureOnCommitCallbacks(execute=True):
            ShippingService.transition_shipment_status(
                shipment=shipment,
                to_status=ShipmentStatus.RETURNED_TO_ORIGIN,
                location="Sirsi Return Center",
                description="Customer unavailable after 3 attempts",
            )

        # 1. Inventory restocked
        current_stock = StockItem.objects.get(variant=self.variant1).quantity_on_hand
        self.assertEqual(current_stock, initial_stock + 2)

        # 2. Payment refunded
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.REFUNDED)
        self.assertEqual(payment.amount_refunded, Decimal("105.00"))

        # 3. Order status reaches terminal REFUNDED (or CANCELLED if non-prepaid)
        order.refresh_from_db()
        self.assertEqual(order.order_status, OrderStatus.REFUNDED)

        # 4. Credit note task and notification dispatched
        mock_cn.assert_called_once_with(
            str(order.id),
            CreditNoteReason.RETURN_TO_ORIGIN,
            f"Return to origin for shipment {shipment.shipment_number}.",
        )
        mock_notif.assert_called()

    @patch("apps.notifications.tasks.send_order_notifications_task.delay")
    @patch("apps.invoices.tasks.generate_credit_note_for_order_task.delay")
    def test_partial_rto_multi_shipment_leaves_order_active_and_refunds_partial_amount(
        self, mock_cn, mock_notif
    ):
        order = Order.objects.create(
            order_number=f"BMP-RTO-PART-{timezone.now().timestamp()}",
            user=self.user,
            order_status=OrderStatus.CONFIRMED,
            shipping_recipient_name="Multi Receiver",
            shipping_phone_number="+919876543210",
            shipping_address_line_1="Temple Road",
            shipping_city="Sirsi",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="581401",
            items_subtotal=Decimal("300.00"),
            tax_amount=Decimal("15.00"),
            shipping_fee=Decimal("0.00"),
            grand_total=Decimal("315.00"),
            total_quantity=3,
            total_weight_in_grams=700,
        )
        line1 = OrderLineItem.objects.create(
            order=order,
            variant=self.variant1,
            product_name="Sambar Powder",
            variant_name="100g",
            sku="SAMBAR-100G",
            weight_in_grams=100,
            quantity=2,
            mrp=Decimal("60.00"),
            unit_price=Decimal("50.00"),
            line_subtotal=Decimal("100.00"),
        )
        line2 = OrderLineItem.objects.create(
            order=order,
            variant=self.variant2,
            product_name="Sambar Powder",
            variant_name="500g",
            sku="SAMBAR-500G",
            weight_in_grams=500,
            quantity=1,
            mrp=Decimal("220.00"),
            unit_price=Decimal("200.00"),
            line_subtotal=Decimal("200.00"),
        )
        payment = Payment.objects.create(
            payment_number=f"PAY-PART-{timezone.now().timestamp()}",
            order=order,
            user=self.user,
            status=PaymentStatus.CAPTURED,
            amount=Decimal("315.00"),
            currency="INR",
            gateway=PaymentGateway.RAZORPAY,
            gateway_payment_id="pay_rto_part_456",
        )

        # Create two separate consignments
        shipment1 = ShippingService.create_shipment(
            order=order,
            courier_name=CourierProvider.MANUAL,
            items_data=[{"order_line_item_id": str(line1.id), "quantity": 2}],
        )
        shipment2 = ShippingService.create_shipment(
            order=order,
            courier_name=CourierProvider.MANUAL,
            items_data=[{"order_line_item_id": str(line2.id), "quantity": 1}],
        )
        OrderStateMachine.transition_status(order, OrderStatus.PROCESSING)
        OrderStateMachine.transition_status(order, OrderStatus.SHIPPED)

        ShippingService.transition_shipment_status(shipment1, to_status=ShipmentStatus.IN_TRANSIT)
        ShippingService.transition_shipment_status(shipment2, to_status=ShipmentStatus.IN_TRANSIT)

        initial_stock1 = StockItem.objects.get(variant=self.variant1).quantity_on_hand
        initial_stock2 = StockItem.objects.get(variant=self.variant2).quantity_on_hand

        # Only shipment 1 is RTO
        with self.captureOnCommitCallbacks(execute=True):
            ShippingService.transition_shipment_status(
                shipment=shipment1,
                to_status=ShipmentStatus.RETURNED_TO_ORIGIN,
                location="Sirsi Hub",
                description="Failed to reach consignee",
            )

        # 1. Variant 1 restocked, Variant 2 unaffected
        self.assertEqual(
            StockItem.objects.get(variant=self.variant1).quantity_on_hand, initial_stock1 + 2
        )
        self.assertEqual(
            StockItem.objects.get(variant=self.variant2).quantity_on_hand, initial_stock2
        )

        # 2. Payment partially refunded for shipment 1 value (100.00)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PARTIALLY_REFUNDED)
        self.assertEqual(payment.amount_refunded, Decimal("100.00"))

        # 3. Order remains in SHIPPED (not cancelled, since shipment2 is still IN_TRANSIT)
        order.refresh_from_db()
        self.assertEqual(order.order_status, OrderStatus.SHIPPED)
