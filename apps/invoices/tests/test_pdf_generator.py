"""
Tests for zero-dependency PDF generation service.
"""

from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import IndianStates, User
from apps.catalog.models import Category, Product, ProductVariant
from apps.invoices.services.invoice_service import InvoiceService
from apps.invoices.services.pdf_generator import InvoicePDFGenerator, MinimalPDFWriter
from apps.orders.models import Order, OrderLineItem, OrderStatus


class PDFGeneratorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="pdf_buyer@example.com",
            phone_number="+919876543210",
            first_name="Ananya",
            last_name="Hegde",
        )
        self.category = Category.objects.create(name="Spices", slug="spices")
        self.product = Product.objects.create(
            category=self.category,
            name="Byadgi Chilli Powder",
            slug="byadgi-chilli-powder",
            hsn_code="0904",
            gst_rate=Decimal("5.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="500g",
            sku="BYADGI-500G",
            weight_in_grams=500,
            mrp=Decimal("250.00"),
            selling_price=Decimal("250.00"),
        )
        self.order = Order.objects.create(
            order_number="BMP-PDF-TEST-1",
            user=self.user,
            order_status=OrderStatus.CONFIRMED,
            shipping_recipient_name="Ananya Hegde",
            shipping_phone_number="+919876543210",
            shipping_address_line_1="Post Office Road",
            shipping_city="Thirthahalli",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="577432",
            items_subtotal=Decimal("250.00"),
            shipping_fee=Decimal("50.00"),
            grand_total=Decimal("300.00"),
        )
        self.order_line = OrderLineItem.objects.create(
            order=self.order,
            variant=self.variant,
            product_name="Byadgi Chilli Powder",
            variant_name="500g",
            sku="BYADGI-500G",
            weight_in_grams=500,
            quantity=1,
            mrp=Decimal("250.00"),
            unit_price=Decimal("250.00"),
            line_subtotal=Decimal("250.00"),
        )

    def test_minimal_pdf_writer_structure(self):
        writer = MinimalPDFWriter()
        writer.set_font("F1", 12)
        writer.draw_text("Test Minimal PDF Stream", 50, 750)
        pdf_bytes = writer.compile_pdf()

        self.assertTrue(pdf_bytes.startswith(b"%PDF-1.4"))
        self.assertTrue(pdf_bytes.strip().endswith(b"%%EOF"))
        self.assertIn(b"/Type /Catalog", pdf_bytes)
        self.assertIn(b"/Type /Pages", pdf_bytes)
        self.assertIn(b"/Type /Page", pdf_bytes)
        self.assertIn(b"xref", pdf_bytes)
        self.assertIn(b"trailer", pdf_bytes)

    def test_invoice_pdf_generator_produces_valid_pdf(self):
        invoice = InvoiceService.generate_invoice(self.order)
        pdf_bytes = InvoicePDFGenerator.generate(invoice)

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(len(pdf_bytes) > 500)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-1.4"))
        self.assertTrue(pdf_bytes.strip().endswith(b"%%EOF"))

    def test_regenerate_pdf_persists_file(self):
        invoice = InvoiceService.generate_invoice(self.order)
        self.assertIsNotNone(invoice.pdf_file)
        self.assertIsNotNone(invoice.pdf_generated_at)

        initial_generated_at = invoice.pdf_generated_at
        InvoiceService.regenerate_pdf(invoice)
        invoice.refresh_from_db()

        self.assertGreaterEqual(invoice.pdf_generated_at, initial_generated_at)
        self.assertTrue(invoice.pdf_file.name.endswith(".pdf"))
        base_name = f"Invoice_{invoice.invoice_number.replace('/', '_')}"
        self.assertIn(base_name, invoice.pdf_file.name)
        self.assertGreater(len(invoice.pdf_file.name), len(base_name) + 12)
