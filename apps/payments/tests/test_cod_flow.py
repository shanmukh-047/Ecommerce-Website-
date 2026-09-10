from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.orders.models import OrderStatus
from apps.orders.tests.factories import create_order_user, create_staff_user
from apps.payments.models import PaymentGateway, PaymentMethod, PaymentStatus
from apps.payments.services import PaymentService
from apps.payments.tests.factories import create_payment_order


class CashOnDeliveryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = create_order_user(email="cod_customer@example.com", phone="9876543201")
        self.staff = create_staff_user(email="cod_staff@example.com", phone="9876543202")
        self.other_user = create_order_user(email="cod_other@example.com", phone="9876543203")
        self.order = create_payment_order(user=self.customer, variant_suffix="cod1")

    def test_customer_can_create_cod_payment(self):
        self.client.force_authenticate(user=self.customer)
        url = reverse("payments:cod", kwargs={"order_id": self.order.id})
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("payment", res.data)
        payment_data = res.data["payment"]
        self.assertEqual(payment_data["status"], PaymentStatus.PENDING)
        self.assertEqual(payment_data["payment_method"], PaymentMethod.COD)
        self.assertEqual(payment_data["gateway"], PaymentGateway.COD)

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.CONFIRMED)

    def test_unauthenticated_cannot_create_cod_payment(self):
        url = reverse("payments:cod", kwargs={"order_id": self.order.id})
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_idor_cannot_create_cod_payment_for_other_user_order(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("payments:cod", kwargs={"order_id": self.order.id})
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_can_mark_cod_collected(self):
        # First place COD payment
        payment = PaymentService.create_cod_payment(self.order, self.customer)
        self.assertEqual(payment.status, PaymentStatus.PENDING)

        # Staff marks payment collected
        self.client.force_authenticate(user=self.staff)
        url = reverse("staff-payments:staff-payment-mark-cod-collected", kwargs={"payment_id": payment.id})
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.CAPTURED)
        self.assertIsNotNone(payment.captured_at)

    def test_customer_cannot_mark_cod_collected(self):
        payment = PaymentService.create_cod_payment(self.order, self.customer)

        self.client.force_authenticate(user=self.customer)
        url = reverse("staff-payments:staff-payment-mark-cod-collected", kwargs={"payment_id": payment.id})
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PENDING)

    def test_mark_cod_collected_idempotence(self):
        payment = PaymentService.create_cod_payment(self.order, self.customer)

        # First collection
        PaymentService.mark_cod_collected(payment.id, self.staff)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.CAPTURED)

        # Second collection call via API returns 200 idempotently
        self.client.force_authenticate(user=self.staff)
        url = reverse("staff-payments:staff-payment-mark-cod-collected", kwargs={"payment_id": payment.id})
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["payment"]["status"], PaymentStatus.CAPTURED)

    def test_cannot_mark_razorpay_payment_as_cod_collected(self):
        razorpay_payment, _ = PaymentService.initiate_payment(self.order, self.customer)

        self.client.force_authenticate(user=self.staff)
        url = reverse("staff-payments:staff-payment-mark-cod-collected", kwargs={"payment_id": razorpay_payment.id})
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
