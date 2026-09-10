"""
Tests for customer and staff invoice REST API endpoints.
"""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import IndianStates, Role, User
from apps.catalog.models import Category, Product, ProductVariant
from apps.invoices.models import Invoice
from apps.invoices.services.invoice_service import InvoiceService
from apps.invoices.tasks import (
    generate_invoice_for_order_task,
    regenerate_invoice_pdf_task,
)
from apps.orders.models import Order, OrderLineItem, OrderStatus


class InvoiceAPITests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            email="cust1@example.com",
            phone_number="+919876543210",
            first_name="Customer",
            last_name="One",
        )
        self.other_customer = User.objects.create_user(
            email="cust2@example.com",
            phone_number="+919876543211",
            first_name="Customer",
            last_name="Two",
        )
        self.staff_user = User.objects.create_superuser(
            email="staff@example.com",
            phone_number="+919876543219",
            password="securepassword123",
            first_name="Admin",
            last_name="Staff",
        )

        self.category = Category.objects.create(name="Spices", slug="spices")
        self.product = Product.objects.create(
            category=self.category,
            name="Turmeric Powder",
            slug="turmeric-powder",
            hsn_code="0904",
            gst_rate=Decimal("5.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="500g",
            sku="TURMERIC-500G",
            weight_in_grams=500,
            mrp=Decimal("180.00"),
            selling_price=Decimal("180.00"),
        )

        self.order = Order.objects.create(
            order_number="BMP-API-ORD-1",
            user=self.customer,
            order_status=OrderStatus.CONFIRMED,
            shipping_recipient_name="Customer One",
            shipping_phone_number="+919876543210",
            shipping_address_line_1="Koppa Road",
            shipping_city="Thirthahalli",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="577432",
            items_subtotal=Decimal("180.00"),
            shipping_fee=Decimal("50.00"),
            grand_total=Decimal("230.00"),
        )
        self.order_line = OrderLineItem.objects.create(
            order=self.order,
            variant=self.variant,
            product_name="Turmeric Powder",
            variant_name="500g",
            sku="TURMERIC-500G",
            weight_in_grams=500,
            quantity=1,
            mrp=Decimal("180.00"),
            unit_price=Decimal("180.00"),
            line_subtotal=Decimal("180.00"),
        )

    def test_customer_retrieve_invoice_json(self):
        self.client.force_authenticate(user=self.customer)
        url = f"/api/v1/orders/{self.order.id}/invoice/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["invoice_number"].startswith("BMP/"))
        self.assertEqual(response.data["order_number"], self.order.order_number)
        self.assertIn("download_url", response.data)
        self.assertIn("html_url", response.data)
        self.assertEqual(len(response.data["lines"]), 1)

    def test_customer_download_invoice_pdf(self):
        self.client.force_authenticate(user=self.customer)
        url = f"/api/v1/orders/{self.order.id}/invoice/download/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF-1.4"))

    def test_customer_view_invoice_html(self):
        self.client.force_authenticate(user=self.customer)
        url = f"/api/v1/orders/{self.order.id}/invoice/html/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("TAX INVOICE", response.content.decode("utf-8"))
        self.assertIn(self.order.order_number, response.content.decode("utf-8"))

    def test_idor_protection_customer_cannot_access_other_user_invoice(self):
        self.client.force_authenticate(user=self.other_customer)
        url = f"/api/v1/orders/{self.order.id}/invoice/"
        response = self.client.get(url)

        # Must return 404, strictly preventing IDOR leakage
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_access_rejected(self):
        url = f"/api/v1/orders/{self.order.id}/invoice/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_invoice_list(self):
        InvoiceService.generate_invoice(self.order)
        self.client.force_authenticate(user=self.staff_user)

        url = "/api/v1/staff/invoices/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Results can be paginated or direct list
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["order_number"], self.order.order_number)

    def test_staff_invoice_filtering(self):
        InvoiceService.generate_invoice(self.order)
        self.client.force_authenticate(user=self.staff_user)

        # Filter by place of supply
        response = self.client.get(
            "/api/v1/staff/invoices/", {"place_of_supply": IndianStates.KARNATAKA}
        )
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)

        # Filter by mismatch
        response = self.client.get(
            "/api/v1/staff/invoices/", {"place_of_supply": IndianStates.KERALA}
        )
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 0)

    def test_staff_regenerate_invoice_pdf(self):
        invoice = InvoiceService.generate_invoice(self.order)
        self.client.force_authenticate(user=self.staff_user)

        url = f"/api/v1/staff/invoices/{invoice.id}/regenerate-pdf/"
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Successfully regenerated PDF", response.data["detail"])

    def test_regular_user_cannot_access_staff_endpoints(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get("/api/v1/staff/invoices/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_role_user_can_access_invoices(self):
        staff_role_user = User.objects.create_user(
            email="staff_role@example.com",
            phone_number="+919876543277",
            role=Role.STAFF,
        )
        InvoiceService.generate_invoice(self.order)
        self.client.force_authenticate(user=staff_role_user)
        response = self.client.get("/api/v1/staff/invoices/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_manager_role_user_can_access_invoices(self):
        manager_user = User.objects.create_user(
            email="manager_role@example.com",
            phone_number="+919876543266",
            role=Role.MANAGER,
        )
        InvoiceService.generate_invoice(self.order)
        self.client.force_authenticate(user=manager_user)
        response = self.client.get("/api/v1/staff/invoices/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_celery_task_generate_invoice_for_order(self):
        task_result = generate_invoice_for_order_task(str(self.order.id))
        self.assertIsNotNone(task_result)
        self.assertTrue(Invoice.objects.filter(order=self.order).exists())

    def test_celery_task_regenerate_invoice_pdf(self):
        invoice = InvoiceService.generate_invoice(self.order)
        task_result = regenerate_invoice_pdf_task(str(invoice.id))
        self.assertEqual(task_result, str(invoice.id))
