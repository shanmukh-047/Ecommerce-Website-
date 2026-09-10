from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.orders.tests.factories import create_order_user, create_staff_user
from apps.payments.models import PaymentStatus
from apps.payments.services import PaymentService
from apps.payments.tests.factories import create_payment_order


class StaffPaymentAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = create_staff_user(email="staff_pay@example.com", phone="9876543288")
        self.customer = create_order_user(email="cust_pay@example.com", phone="9876543287")
        self.order = create_payment_order(user=self.customer, variant_suffix="stf")
        self.payment, _ = PaymentService.initiate_payment(self.order, self.customer)

    def test_staff_payment_rbac(self):
        url = reverse("staff-payments:staff-payment-list")

        # Unauthenticated -> 401
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # Customer -> 403
        self.client.force_authenticate(user=self.customer)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Staff -> 200
        self.client.force_authenticate(user=self.staff)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_staff_payment_list_filters_and_search(self):
        self.client.force_authenticate(user=self.staff)
        url = reverse("staff-payments:staff-payment-list")

        # Basic list
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)

        # Filter by status
        res = self.client.get(url, {"status": PaymentStatus.PENDING})
        self.assertEqual(len(res.data["results"]), 1)

        res = self.client.get(url, {"status": PaymentStatus.CAPTURED})
        self.assertEqual(len(res.data["results"]), 0)

        # Search by payment_number
        res = self.client.get(url, {"search": self.payment.payment_number})
        self.assertEqual(len(res.data["results"]), 1)

        # Search by order_number
        res = self.client.get(url, {"search": self.order.order_number})
        self.assertEqual(len(res.data["results"]), 1)

    def test_staff_payment_detail(self):
        self.client.force_authenticate(user=self.staff)
        url = reverse("staff-payments:staff-payment-detail", kwargs={"payment_id": self.payment.id})
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["payment"]["id"], str(self.payment.id))
        self.assertIn("attempts", res.data["payment"])
