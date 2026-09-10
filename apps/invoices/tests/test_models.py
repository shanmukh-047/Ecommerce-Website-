"""
Tests for apps.invoices models.
"""

from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import IndianStates, User
from apps.catalog.models import Category, Product, ProductVariant
from apps.invoices.models import Invoice, InvoiceLineItem, InvoiceSequence
from apps.orders.models import Order, OrderLineItem, OrderStatus


class InvoiceModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="buyer@example.com",
            phone_number="+919876543210",
            first_name="Ramesh",
            last_name="Kumar",
        )
        self.category = Category.objects.create(name="Spices", slug="spices")
        self.product = Product.objects.create(
            category=self.category,
            name="Sambar Masala",
            slug="sambar-masala",
            hsn_code="0904",
            gst_rate=Decimal("5.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="250g",
            sku="SAMBAR-250G",
            weight_in_grams=250,
            mrp=Decimal("150.00"),
            selling_price=Decimal("150.00"),
        )
        self.order = Order.objects.create(
            order_number="BMP-TEST-0001",
            user=self.user,
            order_status=OrderStatus.CONFIRMED,
            shipping_recipient_name="Ramesh Kumar",
            shipping_phone_number="+919876543210",
            shipping_address_line_1="123 Temple Road",
            shipping_city="Bengaluru",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="560001",
            items_subtotal=Decimal("150.00"),
            shipping_fee=Decimal("50.00"),
            grand_total=Decimal("200.00"),
        )
        self.order_line = OrderLineItem.objects.create(
            order=self.order,
            variant=self.variant,
            product_name="Sambar Masala",
            variant_name="250g",
            sku="SAMBAR-250G",
            weight_in_grams=250,
            quantity=1,
            mrp=Decimal("150.00"),
            unit_price=Decimal("150.00"),
            line_subtotal=Decimal("150.00"),
        )

    def test_invoice_sequence_generation(self):
        seq = InvoiceSequence.objects.create(financial_year="2026-27", last_number=10)
        self.assertEqual(str(seq), "2026-27: #10")

    def test_invoice_creation_and_string_representation(self):
        invoice = Invoice.objects.create(
            invoice_number="BMP/2026-27/00001",
            order=self.order,
            buyer_name="Ramesh Kumar",
            buyer_email="buyer@example.com",
            buyer_phone="+919876543210",
            shipping_address="123 Temple Road, Bengaluru, KA 560001",
            place_of_supply=IndianStates.KARNATAKA,
            is_interstate=False,
            is_b2b=False,
            items_subtotal=Decimal("150.00"),
            taxable_subtotal=Decimal("142.86"),
            cgst_amount=Decimal("3.57"),
            sgst_amount=Decimal("3.57"),
            igst_amount=Decimal("0.00"),
            total_tax=Decimal("7.14"),
            shipping_fee=Decimal("50.00"),
            grand_total=Decimal("200.00"),
        )
        self.assertIn("BMP/2026-27/00001", str(invoice))
        self.assertEqual(invoice.order, self.order)

    def test_invoice_line_item_creation(self):
        invoice = Invoice.objects.create(
            invoice_number="BMP/2026-27/00002",
            order=self.order,
            buyer_name="Ramesh Kumar",
            buyer_email="buyer@example.com",
            buyer_phone="+919876543210",
            shipping_address="123 Temple Road, Bengaluru, KA 560001",
            place_of_supply=IndianStates.KARNATAKA,
            items_subtotal=Decimal("150.00"),
            taxable_subtotal=Decimal("142.86"),
            grand_total=Decimal("200.00"),
        )
        line = InvoiceLineItem.objects.create(
            invoice=invoice,
            order_line_item=self.order_line,
            product_name="Sambar Masala",
            variant_name="250g",
            sku="SAMBAR-250G",
            hsn_code="0904",
            quantity=1,
            unit_price=Decimal("150.00"),
            taxable_amount=Decimal("142.86"),
            gst_rate=Decimal("5.00"),
            cgst_rate=Decimal("2.50"),
            cgst_amount=Decimal("3.57"),
            sgst_rate=Decimal("2.50"),
            sgst_amount=Decimal("3.57"),
            igst_rate=Decimal("0.00"),
            igst_amount=Decimal("0.00"),
            total_amount=Decimal("150.00"),
        )
        self.assertEqual(line.hsn_code, "0904")
        self.assertIn("SAMBAR-250G", str(line))

    def test_invoice_unique_number_constraint(self):
        Invoice.objects.create(
            invoice_number="BMP/2026-27/DUPLICATE",
            order=self.order,
            buyer_name="Ramesh Kumar",
            buyer_email="buyer@example.com",
            buyer_phone="+919876543210",
            shipping_address="123 Temple Road",
            place_of_supply=IndianStates.KARNATAKA,
            items_subtotal=Decimal("150.00"),
            taxable_subtotal=Decimal("142.86"),
            grand_total=Decimal("200.00"),
        )
        order2 = Order.objects.create(
            order_number="BMP-TEST-0002",
            user=self.user,
            order_status=OrderStatus.CONFIRMED,
            shipping_recipient_name="Ramesh Kumar",
            shipping_phone_number="+919876543210",
            shipping_address_line_1="123 Temple Road",
            shipping_city="Bengaluru",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="560001",
            items_subtotal=Decimal("150.00"),
            shipping_fee=Decimal("50.00"),
            grand_total=Decimal("200.00"),
        )
        with self.assertRaises(IntegrityError):
            Invoice.objects.create(
                invoice_number="BMP/2026-27/DUPLICATE",
                order=order2,
                buyer_name="Ramesh Kumar",
                buyer_email="buyer@example.com",
                buyer_phone="+919876543210",
                shipping_address="123 Temple Road",
                place_of_supply=IndianStates.KARNATAKA,
                items_subtotal=Decimal("150.00"),
                taxable_subtotal=Decimal("142.86"),
                grand_total=Decimal("200.00"),
            )
