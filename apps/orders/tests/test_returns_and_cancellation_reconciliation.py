"""
Tests for Order Cancellation, Returns & Refund Financial Reconciliation:
- Cancellation of invoiced order triggers inventory restock and statutory Credit Note task.
- Return to Origin (RTO) triggers physical restock and statutory Credit Note task.
- End-to-end reconciliation flow: Invoicing -> Cancellation -> Credit Note -> Payment Refund.
"""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import IndianStates, User
from apps.catalog.models import Category, Product, ProductVariant
from apps.inventory.models import StockItem
from apps.invoices.models import (
    CreditNote,
    CreditNoteReason,
    InvoiceStatus,
)
from apps.invoices.services.credit_note_service import CreditNoteService
from apps.invoices.services.invoice_service import InvoiceService
from apps.invoices.tasks import generate_credit_note_for_order_task
from apps.orders.models import Order, OrderLineItem, OrderStatus
from apps.orders.services import OrderStateMachine
from apps.payments.models import Payment, PaymentGateway, PaymentStatus
from apps.payments.services import PaymentService
from apps.shipping.models import CourierProvider, ShipmentStatus
from apps.shipping.services import ShippingService


class ReturnsAndCancellationReconciliationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="reconcile@example.com",
            phone_number="+919876543299",
            first_name="Reconcile",
            last_name="Tester",
        )
        self.category = Category.objects.create(name="Spices", slug="spices-reconcile")
        self.product = Product.objects.create(
            category=self.category,
            name="Turmeric Powder",
            slug="turmeric-powder",
            hsn_code="0910",
            gst_rate=Decimal("5.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="500g",
            sku="TURM-500G",
            weight_in_grams=500,
            mrp=Decimal("200.00"),
            selling_price=Decimal("200.00"),
        )
        self.stock_item = StockItem.objects.create(
            variant=self.variant,
            quantity_on_hand=100,
            quantity_reserved=0,
        )

        self.order = Order.objects.create(
            order_number=f"BMP-REC-{timezone.now().timestamp()}",
            user=self.user,
            order_status=OrderStatus.CONFIRMED,
            shipping_recipient_name="Reconcile Tester",
            shipping_phone_number="+919876543299",
            shipping_address_line_1="Bazaar Road",
            shipping_city="Thirthahalli",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="577432",
            items_subtotal=Decimal("400.00"),
            tax_amount=Decimal("20.00"),
            shipping_fee=Decimal("0.00"),
            grand_total=Decimal("420.00"),
            total_quantity=2,
            total_weight_in_grams=1000,
        )
        self.line_item = OrderLineItem.objects.create(
            order=self.order,
            variant=self.variant,
            product_name="Turmeric Powder",
            variant_name="500g",
            sku="TURM-500G",
            weight_in_grams=500,
            quantity=2,
            mrp=Decimal("200.00"),
            unit_price=Decimal("200.00"),
            line_subtotal=Decimal("400.00"),
        )

    @patch("apps.notifications.tasks.send_order_notifications_task.delay")
    @patch("apps.invoices.tasks.generate_credit_note_for_order_task.delay")
    def test_cancellation_dispatches_credit_note_task(self, mock_cn_task, mock_notif_task):
        initial_stock = StockItem.objects.get(variant=self.variant).quantity_on_hand

        with self.captureOnCommitCallbacks(execute=True):
            OrderStateMachine.cancel_order(self.order, reason="Customer cancelled before dispatch")

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.CANCELLED)

        # Inventory restocked
        current_stock = StockItem.objects.get(variant=self.variant).quantity_on_hand
        self.assertEqual(current_stock, initial_stock + 2)

        # Credit note generation dispatched
        mock_cn_task.assert_called_once_with(
            str(self.order.id),
            CreditNoteReason.ORDER_CANCELLATION,
            "Customer cancelled before dispatch",
        )

    def test_cancellation_end_to_end_credit_note_generation(self):
        # 1. Invoice generated for order
        invoice = InvoiceService.generate_invoice(self.order)
        self.assertEqual(invoice.status, InvoiceStatus.ACTIVE)

        # 2. Cancel order
        OrderStateMachine.cancel_order(self.order, reason="Defective order cancelled")

        # 3. Execute credit note task
        cn_id = generate_credit_note_for_order_task(
            str(self.order.id),
            reason=CreditNoteReason.ORDER_CANCELLATION,
            reason_notes="Defective order cancelled",
        )
        self.assertIsNotNone(cn_id)

        # 4. Verify Credit Note and updated invoice status
        cn = CreditNote.objects.get(id=cn_id)
        self.assertEqual(cn.order, self.order)
        self.assertEqual(cn.original_invoice, invoice)
        self.assertEqual(cn.reason, CreditNoteReason.ORDER_CANCELLATION)

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, InvoiceStatus.CREDIT_NOTED)

    @patch("apps.notifications.tasks.send_order_notifications_task.delay")
    @patch("apps.invoices.tasks.generate_credit_note_for_order_task.delay")
    def test_rto_shipment_dispatches_credit_note_task(self, mock_cn_task, mock_notif_task):
        shipment = ShippingService.create_shipment(
            order=self.order,
            courier_name=CourierProvider.MANUAL,
        )
        ShippingService.transition_shipment_status(shipment, to_status=ShipmentStatus.IN_TRANSIT)

        initial_stock = StockItem.objects.get(variant=self.variant).quantity_on_hand

        # Process RTO
        with self.captureOnCommitCallbacks(execute=True):
            ShippingService.transition_shipment_status(
                shipment=shipment,
                to_status=ShipmentStatus.RETURNED_TO_ORIGIN,
                location="Thirthahalli Hub",
                description="Delivery failed, returned to merchant hub.",
            )

        # Inventory restocked
        current_stock = StockItem.objects.get(variant=self.variant).quantity_on_hand
        self.assertEqual(current_stock, initial_stock + 2)

        # RTO credit note task dispatched
        mock_cn_task.assert_called_once_with(
            str(self.order.id),
            CreditNoteReason.RETURN_TO_ORIGIN,
            f"Return to origin for shipment {shipment.shipment_number}.",
        )

    def test_full_reconciliation_flow_with_refund(self):
        # 1. Invoice generated
        invoice = InvoiceService.generate_invoice(self.order)

        # 2. Payment captured
        payment = Payment.objects.create(
            payment_number=f"PAY-{timezone.now().timestamp()}",
            order=self.order,
            user=self.user,
            status=PaymentStatus.CAPTURED,
            amount=self.order.grand_total,
            currency="INR",
            gateway=PaymentGateway.RAZORPAY,
            gateway_payment_id="pay_reconcile_001",
        )

        # 3. Order cancelled -> Credit Note generated
        OrderStateMachine.cancel_order(self.order, reason="Customer cancelled")
        cn = CreditNoteService.generate_credit_note(
            order=self.order,
            reason=CreditNoteReason.ORDER_CANCELLATION,
        )
        self.assertIsNotNone(cn)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, InvoiceStatus.CREDIT_NOTED)

        # 4. Payment refund initiated
        refunded = PaymentService.refund_payment(
            payment=payment,
            reason="Cancellation refund",
        )
        self.assertEqual(refunded.status, PaymentStatus.REFUNDED)

        # 5. Order reaches terminal REFUNDED status
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.REFUNDED)
