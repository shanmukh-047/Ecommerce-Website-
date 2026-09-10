"""
Comprehensive tests for statutory GST Credit Notes (Section 34 CGST Act, Rule 53(1A)).
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import IndianStates, Role, User
from apps.catalog.models import Category, Product, ProductVariant
from apps.invoices.exceptions import InvoiceGenerationError
from apps.invoices.models import (
    CreditNote,
    CreditNoteReason,
    CreditNoteSequence,
    InvoiceStatus,
)
from apps.invoices.services.credit_note_service import CreditNoteService
from apps.invoices.services.invoice_service import InvoiceService
from apps.orders.models import Order, OrderLineItem, OrderStatus


class CreditNoteModelAndServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="ramesh@example.com",
            phone_number="+919876543210",
            first_name="Ramesh",
            last_name="Bhat",
        )
        self.category = Category.objects.create(name="Spices", slug="spices")
        self.product = Product.objects.create(
            category=self.category,
            name="Sambar Powder",
            slug="sambar-powder",
            hsn_code="0904",
            gst_rate=Decimal("5.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="500g",
            sku="SAMBAR-500G",
            weight_in_grams=500,
            mrp=Decimal("210.00"),
            selling_price=Decimal("210.00"),
        )

    def _create_order_with_invoice(self, state=IndianStates.KARNATAKA):
        order = Order.objects.create(
            order_number=f"BMP-ORD-{timezone.now().timestamp()}",
            user=self.user,
            order_status=OrderStatus.CONFIRMED,
            items_subtotal=Decimal("400.00"),
            tax_amount=Decimal("20.00"),
            shipping_fee=Decimal("0.00"),
            grand_total=Decimal("420.00"),
            currency="INR",
            total_quantity=2,
            shipping_recipient_name="Ramesh Bhat",
            shipping_phone_number="+919876543210",
            shipping_address_line_1="Car Street",
            shipping_city="Thirthahalli",
            shipping_state=state,
            shipping_pincode="577432",
        )
        OrderLineItem.objects.create(
            order=order,
            variant=self.variant,
            quantity=2,
            mrp=Decimal("210.00"),
            unit_price=Decimal("210.00"),
            line_subtotal=Decimal("420.00"),
            product_name="Sambar Powder",
            variant_name="500g",
            sku="SAMBAR-500G",
        )
        invoice = InvoiceService.generate_invoice(order)
        return order, invoice

    def test_credit_note_sequence_generation(self):
        CreditNoteSequence.objects.create(
            financial_year="2026-27",
            last_number=0,
        )
        num1 = CreditNoteSequence.get_next_number("2026-27")
        self.assertEqual(num1, "BMP/CN/2026-27/00001")

        num2 = CreditNoteSequence.get_next_number("2026-27")
        self.assertEqual(num2, "BMP/CN/2026-27/00002")

    def test_generate_credit_note_intra_state(self):
        order, invoice = self._create_order_with_invoice(state=IndianStates.KARNATAKA)
        self.assertEqual(invoice.status, InvoiceStatus.ACTIVE)

        cn = CreditNoteService.generate_credit_note(
            order=order,
            reason=CreditNoteReason.ORDER_CANCELLATION,
            reason_notes="Customer cancelled order.",
        )
        self.assertIsNotNone(cn)
        self.assertEqual(cn.order, order)
        self.assertEqual(cn.original_invoice, invoice)
        self.assertEqual(cn.reason, CreditNoteReason.ORDER_CANCELLATION)
        self.assertFalse(cn.is_interstate)
        self.assertGreater(cn.cgst_amount, Decimal("0.00"))
        self.assertGreater(cn.sgst_amount, Decimal("0.00"))
        self.assertEqual(cn.igst_amount, Decimal("0.00"))
        self.assertEqual(cn.grand_total, invoice.grand_total)

        # Original invoice status is updated
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, InvoiceStatus.CREDIT_NOTED)

        # PDF file generated
        self.assertTrue(bool(cn.pdf_file))
        content = cn.pdf_file.read()
        self.assertTrue(content.startswith(b"%PDF-1.4"))

    def test_generate_credit_note_inter_state(self):
        order, invoice = self._create_order_with_invoice(state=IndianStates.MAHARASHTRA)

        cn = CreditNoteService.generate_credit_note(
            order=order,
            reason=CreditNoteReason.RETURN_TO_ORIGIN,
            reason_notes="Carrier RTO delivery.",
        )
        self.assertIsNotNone(cn)
        self.assertTrue(cn.is_interstate)
        self.assertEqual(cn.cgst_amount, Decimal("0.00"))
        self.assertEqual(cn.sgst_amount, Decimal("0.00"))
        self.assertGreater(cn.igst_amount, Decimal("0.00"))
        self.assertEqual(cn.grand_total, invoice.grand_total)

    def test_generate_credit_note_idempotency(self):
        order, invoice = self._create_order_with_invoice()
        cn1 = CreditNoteService.generate_credit_note(order=order)
        cn2 = CreditNoteService.generate_credit_note(order=order)
        self.assertEqual(cn1.id, cn2.id)
        self.assertEqual(cn1.credit_note_number, cn2.credit_note_number)
        self.assertEqual(CreditNote.objects.filter(order=order).count(), 1)

    def test_generate_credit_note_non_invoiced_order_returns_none(self):
        order = Order.objects.create(
            order_number=f"BMP-ORD-NOINV-{timezone.now().timestamp()}",
            user=self.user,
            order_status=OrderStatus.PENDING_PAYMENT,
            items_subtotal=Decimal("200.00"),
            tax_amount=Decimal("10.00"),
            shipping_fee=Decimal("0.00"),
            grand_total=Decimal("210.00"),
            currency="INR",
            total_quantity=1,
            shipping_recipient_name="Ramesh Bhat",
            shipping_phone_number="+919876543210",
            shipping_address_line_1="Car Street",
            shipping_city="Thirthahalli",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="577432",
        )
        cn = CreditNoteService.generate_credit_note(order=order)
        self.assertIsNone(cn)

    def test_regenerate_credit_note_pdf(self):
        order, invoice = self._create_order_with_invoice()
        cn = CreditNoteService.generate_credit_note(order=order)
        original_generated_at = cn.pdf_generated_at

        pdf_bytes = CreditNoteService.regenerate_pdf(cn)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-1.4"))
        cn.refresh_from_db()
        self.assertGreaterEqual(cn.pdf_generated_at, original_generated_at)

    def test_partial_credit_note_marks_invoice_partially_credit_noted(self):
        """Partial credit note marks invoice PARTIALLY_CREDIT_NOTED and validates quantities."""
        order, invoice = self._create_order_with_invoice()
        order_line = order.lines.first()

        # Credit 1 out of 2 units
        cn = CreditNoteService.generate_credit_note(
            order=order,
            reason=CreditNoteReason.CUSTOMER_RETURN,
            reason_notes="Returned 1 defective unit.",
            items_data=[{"order_line_item_id": str(order_line.id), "quantity": 1}],
        )
        self.assertIsNotNone(cn)
        self.assertEqual(cn.lines.count(), 1)
        self.assertEqual(cn.lines.first().quantity, 1)

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, InvoiceStatus.PARTIALLY_CREDIT_NOTED)

    def test_consecutive_partial_credit_notes_transition_to_credit_noted(self):
        """Successive partial credit notes transition invoice to CREDIT_NOTED on 100% credit."""
        order, invoice = self._create_order_with_invoice()
        order_line = order.lines.first()

        # Credit 1 unit
        cn1 = CreditNoteService.generate_credit_note(
            order=order,
            reason=CreditNoteReason.CUSTOMER_RETURN,
            items_data=[{"order_line_item_id": str(order_line.id), "quantity": 1}],
        )
        self.assertIsNotNone(cn1)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, InvoiceStatus.PARTIALLY_CREDIT_NOTED)

        # Credit remaining 1 unit
        cn2 = CreditNoteService.generate_credit_note(
            order=order,
            reason=CreditNoteReason.CUSTOMER_RETURN,
            items_data=[{"order_line_item_id": str(order_line.id), "quantity": 1}],
        )
        self.assertIsNotNone(cn2)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, InvoiceStatus.CREDIT_NOTED)

    def test_credit_note_exceeding_remaining_quantity_is_rejected(self):
        """Attempting to credit more units than remaining eligible raises InvoiceGenerationError."""
        order, invoice = self._create_order_with_invoice()
        order_line = order.lines.first()

        # First credit 1 unit out of 2
        CreditNoteService.generate_credit_note(
            order=order,
            reason=CreditNoteReason.CUSTOMER_RETURN,
            items_data=[{"order_line_item_id": str(order_line.id), "quantity": 1}],
        )

        # Attempting to credit 2 units when only 1 is remaining
        with self.assertRaises(InvoiceGenerationError) as ctx:
            CreditNoteService.generate_credit_note(
                order=order,
                reason=CreditNoteReason.CUSTOMER_RETURN,
                items_data=[{"order_line_item_id": str(order_line.id), "quantity": 2}],
            )
        self.assertIn("exceeds remaining eligible quantity", str(ctx.exception))

    def test_credit_note_on_already_credited_invoice_is_rejected(self):
        """Attempting to credit an invoice in CREDIT_NOTED raises InvoiceGenerationError."""
        order, invoice = self._create_order_with_invoice()
        order_line = order.lines.first()

        # Full credit
        CreditNoteService.generate_credit_note(
            order=order,
            reason=CreditNoteReason.ORDER_CANCELLATION,
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, InvoiceStatus.CREDIT_NOTED)

        with self.assertRaises(InvoiceGenerationError) as ctx:
            CreditNoteService.generate_credit_note(
                order=order,
                reason=CreditNoteReason.CUSTOMER_RETURN,
                items_data=[{"order_line_item_id": str(order_line.id), "quantity": 1}],
            )
        self.assertIn("already fully credited", str(ctx.exception))


class CreditNoteAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            email="customer@example.com",
            phone_number="+919876543211",
            first_name="Customer",
            last_name="One",
        )
        self.other_customer = User.objects.create_user(
            email="other@example.com",
            phone_number="+919876543212",
            first_name="Other",
            last_name="User",
        )
        self.staff_user = User.objects.create_user(
            email="staff@bharathmasala.com",
            phone_number="+919876543213",
            first_name="Staff",
            last_name="Member",
            is_staff=True,
            role=Role.STAFF,
        )

        self.category = Category.objects.create(name="Masalas", slug="masalas")
        self.product = Product.objects.create(
            category=self.category,
            name="Garam Masala",
            slug="garam-masala",
            hsn_code="0910",
            gst_rate=Decimal("5.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="250g",
            sku="GM-250G",
            weight_in_grams=250,
            mrp=Decimal("150.00"),
            selling_price=Decimal("150.00"),
        )

        self.order = Order.objects.create(
            order_number="BMP-ORD-CN-001",
            user=self.customer,
            order_status=OrderStatus.CONFIRMED,
            items_subtotal=Decimal("300.00"),
            tax_amount=Decimal("15.00"),
            shipping_fee=Decimal("0.00"),
            grand_total=Decimal("315.00"),
            currency="INR",
            total_quantity=2,
            shipping_recipient_name="Customer One",
            shipping_phone_number="+919876543211",
            shipping_address_line_1="Temple Road",
            shipping_city="Shimoga",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="577201",
        )
        OrderLineItem.objects.create(
            order=self.order,
            variant=self.variant,
            quantity=2,
            mrp=Decimal("150.00"),
            unit_price=Decimal("150.00"),
            line_subtotal=Decimal("300.00"),
            product_name="Garam Masala",
            variant_name="250g",
            sku="GM-250G",
        )
        self.invoice = InvoiceService.generate_invoice(self.order)
        self.credit_note = CreditNoteService.generate_credit_note(
            order=self.order,
            reason=CreditNoteReason.ORDER_CANCELLATION,
            reason_notes="Cancelled by customer",
        )

    def test_customer_list_credit_notes(self):
        self.client.force_authenticate(user=self.customer)
        url = f"/api/v1/orders/{self.order.id}/credit-notes/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["credit_note_number"],
            self.credit_note.credit_note_number,
        )

    def test_customer_download_credit_note_pdf(self):
        self.client.force_authenticate(user=self.customer)
        url = f"/api/v1/orders/{self.order.id}/credit-notes/{self.credit_note.id}/download/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment; filename=", response["Content-Disposition"])

    def test_customer_idor_protection(self):
        self.client.force_authenticate(user=self.other_customer)
        list_url = f"/api/v1/orders/{self.order.id}/credit-notes/"
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        download_url = (
            f"/api/v1/orders/{self.order.id}/credit-notes/{self.credit_note.id}/download/"
        )
        response = self.client.get(download_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_access_blocked(self):
        list_url = f"/api/v1/orders/{self.order.id}/credit-notes/"
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_list_credit_notes(self):
        self.client.force_authenticate(user=self.staff_user)
        url = "/api/v1/staff/invoices/credit-notes/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertGreaterEqual(len(results), 1)

    def test_staff_filter_credit_notes(self):
        self.client.force_authenticate(user=self.staff_user)
        url = f"/api/v1/staff/invoices/credit-notes/?credit_note_number={self.credit_note.credit_note_number}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)

        # Filter by reason
        url = "/api/v1/staff/invoices/credit-notes/?reason=ORDER_CANCELLATION"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)

    def test_staff_credit_note_detail(self):
        self.client.force_authenticate(user=self.staff_user)
        url = f"/api/v1/staff/invoices/credit-notes/{self.credit_note.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.credit_note.id))

    def test_staff_regenerate_credit_note_pdf(self):
        self.client.force_authenticate(user=self.staff_user)
        url = f"/api/v1/staff/invoices/credit-notes/{self.credit_note.id}/regenerate-pdf/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)

    def test_staff_endpoints_forbidden_for_regular_user(self):
        self.client.force_authenticate(user=self.customer)
        url = "/api/v1/staff/invoices/credit-notes/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
