import uuid
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Category, Product, ProductVariant
from apps.inventory.models import StockItem, StockReservation, ReservationStatus
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.payments.models import Payment, PaymentGateway, PaymentMethod, PaymentStatus

User = get_user_model()


class ManualUPIPaymentFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff_client = APIClient()

        # Users
        self.customer = User.objects.create_user(
            email="customer_upi@example.com",
            phone_number="9876543210",
            password="StrongPassword123!",
            first_name="Ramesh",
            last_name="Hegde",
            role="CUSTOMER",
        )
        self.staff_user = User.objects.create_user(
            email="admin_upi@bharathmasala.com",
            phone_number="9876543211",
            password="AdminPassword123!",
            first_name="Admin",
            last_name="Staff",
            role="STAFF",
            is_staff=True,
        )

        self.client.force_authenticate(user=self.customer)
        self.staff_client.force_authenticate(user=self.staff_user)

        # Catalog & inventory
        self.category = Category.objects.create(name="Whole Spices", slug="whole-spices")
        self.product = Product.objects.create(
            name="Sirsi Black Pepper",
            slug="sirsi-black-pepper",
            category=self.category,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="100g",
            sku="SBP-100G",
            weight_in_grams=100,
            mrp=Decimal("180.00"),
            selling_price=Decimal("150.00"),
        )
        self.inventory = StockItem.objects.create(
            variant=self.variant,
            quantity_on_hand=50,
            quantity_reserved=1,
        )

        # Order in PENDING_PAYMENT
        self.order = Order.objects.create(
            order_number="BMP-2026-TESTUPI",
            user=self.customer,
            order_status=OrderStatus.PENDING_PAYMENT,
            items_subtotal=Decimal("150.00"),
            shipping_fee=Decimal("50.00"),
            tax_amount=Decimal("10.00"),
            total_discount=Decimal("0.00"),
            grand_total=Decimal("210.00"),
            total_quantity=1,
            total_weight_in_grams=100,
            shipping_recipient_name="Ramesh Hegde",
            shipping_phone_number="9876543210",
            shipping_address_line_1="12 Estate Road",
            shipping_city="Sirsi",
            shipping_state="KA",
            shipping_pincode="581401",
        )
        self.order_line = OrderItem.objects.create(
            order=self.order,
            variant=self.variant,
            product_name="Sirsi Black Pepper",
            variant_name="100g",
            sku="SBP-100G",
            weight_in_grams=100,
            unit_price=Decimal("150.00"),
            mrp=Decimal("180.00"),
            quantity=1,
            line_subtotal=Decimal("150.00"),
        )
        self.reservation = StockReservation.objects.create(
            stock_item=self.inventory,
            reference_type="ORDER",
            reference_id=self.order.id,
            quantity=1,
            status=ReservationStatus.ACTIVE,
            expires_at=timezone.now() + timezone.timedelta(minutes=30),
        )

    def test_customer_can_submit_utr(self):
        url = f"/api/v1/payments/orders/{self.order.id}/submit-utr/"
        payload = {"utr_number": "425612984012"}

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payment_data = response.data["payment"]
        self.assertEqual(payment_data["status"], PaymentStatus.PENDING_VERIFICATION)
        self.assertEqual(payment_data["utr_number"], "425612984012")
        self.assertEqual(payment_data["gateway"], PaymentGateway.PHONEPE_QR)

        # Verify DB state
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.status, PaymentStatus.PENDING_VERIFICATION)
        self.assertEqual(payment.utr_number, "425612984012")

    def test_customer_cannot_submit_invalid_utr(self):
        url = f"/api/v1/payments/orders/{self.order.id}/submit-utr/"
        # Too short UTR
        response = self.client.post(url, {"utr_number": "123"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_user_cannot_submit_utr(self):
        unauth_client = APIClient()
        url = f"/api/v1/payments/orders/{self.order.id}/submit-utr/"
        response = unauth_client.post(url, {"utr_number": "425612984012"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_can_verify_payment_and_confirm_order(self):
        # 1. Customer submits UTR
        self.client.post(
            f"/api/v1/payments/orders/{self.order.id}/submit-utr/",
            {"utr_number": "425612984012"},
            format="json",
        )
        payment = Payment.objects.get(order=self.order)

        # 2. Regular customer cannot verify payment
        cust_verify_resp = self.client.post(
            f"/api/v1/staff/payments/{payment.id}/verify/",
            {"notes": "Customer tried to verify own payment"},
            format="json",
        )
        self.assertEqual(cust_verify_resp.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Staff verifies payment
        staff_verify_resp = self.staff_client.post(
            f"/api/v1/staff/payments/{payment.id}/verify/",
            {"notes": "Verified against PhonePe merchant statement."},
            format="json",
        )
        self.assertEqual(staff_verify_resp.status_code, status.HTTP_200_OK)

        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.CAPTURED)
        self.assertEqual(self.order.order_status, OrderStatus.CONFIRMED)

    def test_staff_can_reject_unverified_payment(self):
        # 1. Customer submits UTR
        self.client.post(
            f"/api/v1/payments/orders/{self.order.id}/submit-utr/",
            {"utr_number": "000000000000"},
            format="json",
        )
        payment = Payment.objects.get(order=self.order)

        # 2. Staff rejects
        reject_resp = self.staff_client.post(
            f"/api/v1/staff/payments/{payment.id}/reject/",
            {"reason": "UTR not received in bank account statement."},
            format="json",
        )
        self.assertEqual(reject_resp.status_code, status.HTTP_200_OK)

        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.FAILED)
        self.assertEqual(payment.failure_reason, "UTR not received in bank account statement.")
        # Order remains in PENDING_PAYMENT allowing customer to retry
        self.assertEqual(self.order.order_status, OrderStatus.PENDING_PAYMENT)
