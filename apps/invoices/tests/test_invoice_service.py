"""
Tests for apps.invoices service layer.
"""

from datetime import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import IndianStates, User, WholesaleProfile
from apps.catalog.models import Category, Product, ProductVariant
from apps.invoices.exceptions import InvoiceConflict
from apps.invoices.models import Invoice
from apps.invoices.services.invoice_service import InvoiceService
from apps.orders.models import Order, OrderLineItem, OrderStatus
from apps.payments.models import Payment, PaymentMethod, PaymentStatus


class InvoiceServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="ramesh@example.com",
            phone_number="+919876543210",
            first_name="Ramesh",
            last_name="Bhat",
        )
        self.category = Category.objects.create(name="Spices", slug="spices")
        self.product_5 = Product.objects.create(
            category=self.category,
            name="Rasam Powder",
            slug="rasam-powder",
            hsn_code="0904",
            gst_rate=Decimal("5.00"),
        )
        self.variant_5 = ProductVariant.objects.create(
            product=self.product_5,
            variant_name="500g",
            sku="RASAM-500G",
            weight_in_grams=500,
            mrp=Decimal("210.00"),
            selling_price=Decimal("210.00"),
        )

        self.product_12 = Product.objects.create(
            category=self.category,
            name="Ready Gravy Paste",
            slug="ready-gravy-paste",
            hsn_code="2103",
            gst_rate=Decimal("12.00"),
        )
        self.variant_12 = ProductVariant.objects.create(
            product=self.product_12,
            variant_name="200g",
            sku="GRAVY-200G",
            weight_in_grams=200,
            mrp=Decimal("112.00"),
            selling_price=Decimal("112.00"),
        )

    def _create_order(
        self, state=IndianStates.KARNATAKA, status=OrderStatus.CONFIRMED, is_wholesale=False
    ):
        order = Order.objects.create(
            order_number=f"BMP-ORD-{timezone.now().timestamp()}",
            user=self.user,
            order_status=status,
            is_wholesale_order=is_wholesale,
            shipping_recipient_name="Ramesh Bhat",
            shipping_phone_number="+919876543210",
            shipping_address_line_1="45 Car Street",
            shipping_city="Thirthahalli",
            shipping_state=state,
            shipping_pincode="577432",
            items_subtotal=Decimal("322.00"),
            shipping_fee=Decimal("40.00"),
            grand_total=Decimal("362.00"),
        )
        OrderLineItem.objects.create(
            order=order,
            variant=self.variant_5,
            product_name="Rasam Powder",
            variant_name="500g",
            sku="RASAM-500G",
            weight_in_grams=500,
            quantity=1,
            mrp=Decimal("210.00"),
            unit_price=Decimal("210.00"),
            line_subtotal=Decimal("210.00"),
        )
        OrderLineItem.objects.create(
            order=order,
            variant=self.variant_12,
            product_name="Ready Gravy Paste",
            variant_name="200g",
            sku="GRAVY-200G",
            weight_in_grams=200,
            quantity=1,
            mrp=Decimal("112.00"),
            unit_price=Decimal("112.00"),
            line_subtotal=Decimal("112.00"),
        )
        return order

    def test_financial_year_calculation(self):
        from datetime import timezone as dt_tz

        # September 2026 -> 2026-27
        dt_sep = datetime(2026, 9, 6, tzinfo=dt_tz.utc)
        self.assertEqual(InvoiceService.get_financial_year(dt_sep), "2026-27")

        # April 2026 -> 2026-27
        dt_apr = datetime(2026, 4, 1, tzinfo=dt_tz.utc)
        self.assertEqual(InvoiceService.get_financial_year(dt_apr), "2026-27")

        # March 2026 -> 2025-26
        dt_mar = datetime(2026, 3, 31, tzinfo=dt_tz.utc)
        self.assertEqual(InvoiceService.get_financial_year(dt_mar), "2025-26")

        # January 2027 -> 2026-27
        dt_jan = datetime(2027, 1, 15, tzinfo=dt_tz.utc)
        self.assertEqual(InvoiceService.get_financial_year(dt_jan), "2026-27")

    def test_generate_invoice_intrastate_karnataka(self):
        order = self._create_order(state=IndianStates.KARNATAKA)
        invoice = InvoiceService.generate_invoice(order)

        self.assertIsNotNone(invoice)
        self.assertTrue(invoice.invoice_number.startswith("BMP/"))
        self.assertFalse(invoice.is_interstate)
        self.assertEqual(invoice.place_of_supply, IndianStates.KARNATAKA)

        # Intra-state must split tax into CGST and SGST, with IGST = 0
        self.assertGreater(invoice.cgst_amount, Decimal("0.00"))
        self.assertGreater(invoice.sgst_amount, Decimal("0.00"))
        self.assertEqual(invoice.igst_amount, Decimal("0.00"))
        self.assertEqual(invoice.cgst_amount, invoice.sgst_amount)

        # Lines check
        lines = list(invoice.lines.all())
        self.assertEqual(len(lines), 2)
        rasam_line = next(line for line in lines if line.sku == "RASAM-500G")
        self.assertEqual(rasam_line.gst_rate, Decimal("5.00"))
        self.assertEqual(rasam_line.cgst_rate, Decimal("2.50"))
        self.assertEqual(rasam_line.sgst_rate, Decimal("2.50"))
        self.assertEqual(rasam_line.igst_rate, Decimal("0.00"))

        gravy_line = next(line for line in lines if line.sku == "GRAVY-200G")
        self.assertEqual(gravy_line.gst_rate, Decimal("12.00"))
        self.assertEqual(gravy_line.cgst_rate, Decimal("6.00"))
        self.assertEqual(gravy_line.sgst_rate, Decimal("6.00"))
        self.assertEqual(gravy_line.igst_rate, Decimal("0.00"))

    def test_generate_invoice_interstate_tamil_nadu(self):
        order = self._create_order(state=IndianStates.TAMIL_NADU)
        invoice = InvoiceService.generate_invoice(order)

        self.assertIsNotNone(invoice)
        self.assertTrue(invoice.is_interstate)
        self.assertEqual(invoice.place_of_supply, IndianStates.TAMIL_NADU)

        # Inter-state must charge full tax to IGST, with CGST = SGST = 0
        self.assertEqual(invoice.cgst_amount, Decimal("0.00"))
        self.assertEqual(invoice.sgst_amount, Decimal("0.00"))
        self.assertGreater(invoice.igst_amount, Decimal("0.00"))
        self.assertEqual(invoice.total_tax, invoice.igst_amount)

        lines = list(invoice.lines.all())
        rasam_line = next(line for line in lines if line.sku == "RASAM-500G")
        self.assertEqual(rasam_line.igst_rate, Decimal("5.00"))
        self.assertEqual(rasam_line.cgst_amount, Decimal("0.00"))
        self.assertEqual(rasam_line.sgst_amount, Decimal("0.00"))

    def test_generate_invoice_idempotency(self):
        order = self._create_order()
        inv1 = InvoiceService.generate_invoice(order)
        inv2 = InvoiceService.generate_invoice(order)

        self.assertEqual(inv1.id, inv2.id)
        self.assertEqual(inv1.invoice_number, inv2.invoice_number)
        self.assertEqual(Invoice.objects.filter(order=order).count(), 1)

    def test_consecutive_numbering_across_orders(self):
        order1 = self._create_order()
        order2 = self._create_order()

        inv1 = InvoiceService.generate_invoice(order1)
        inv2 = InvoiceService.generate_invoice(order2)

        num1 = int(inv1.invoice_number.split("/")[-1])
        num2 = int(inv2.invoice_number.split("/")[-1])
        self.assertEqual(num2, num1 + 1)

    def test_ineligible_order_status_raises_conflict(self):
        order_pending = self._create_order(status=OrderStatus.PENDING_PAYMENT)
        with self.assertRaises(InvoiceConflict):
            InvoiceService.generate_invoice(order_pending)

        order_cancelled = self._create_order(status=OrderStatus.CANCELLED)
        with self.assertRaises(InvoiceConflict):
            InvoiceService.generate_invoice(order_cancelled)

    def test_wholesale_b2b_buyer_snapshot(self):
        WholesaleProfile.objects.create(
            user=self.user,
            company_name="Bhat Enterprises",
            gstin="29AAAAA0000A1Z5",
            pan_number="AAAAA0000A",
        )
        order = self._create_order(is_wholesale=True)
        invoice = InvoiceService.generate_invoice(order)

        self.assertTrue(invoice.is_b2b)
        self.assertEqual(invoice.buyer_company_name, "Bhat Enterprises")
        self.assertEqual(invoice.buyer_gstin, "29AAAAA0000A1Z5")
        self.assertEqual(invoice.buyer_pan, "AAAAA0000A")

    def test_captured_payment_metadata_snapshot(self):
        order = self._create_order()
        Payment.objects.create(
            payment_number=f"PAY-{timezone.now().timestamp()}",
            order=order,
            user=self.user,
            gateway_order_id="order_dummy_123",
            gateway_payment_id="pay_dummy_999",
            amount=Decimal("362.00"),
            currency="INR",
            payment_method=PaymentMethod.UPI,
            status=PaymentStatus.CAPTURED,
        )
        invoice = InvoiceService.generate_invoice(order)
        self.assertEqual(invoice.payment_method, PaymentMethod.UPI)
        self.assertEqual(invoice.payment_transaction_id, "pay_dummy_999")
