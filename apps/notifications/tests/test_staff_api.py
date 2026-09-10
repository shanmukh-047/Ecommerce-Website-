"""
Tests for staff notification REST API endpoints.
"""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import IndianStates, Role, User
from apps.notifications.models import (
    NotificationChannel,
    NotificationEvent,
    NotificationLog,
    NotificationStatus,
)
from apps.orders.models import Order, OrderStatus


class StaffNotificationAPITests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_superuser(
            email="staff_notify@example.com",
            phone_number="+919876543299",
            password="securepassword123",
            first_name="Admin",
            last_name="Staff",
        )
        self.customer = User.objects.create_user(
            email="customer_notify@example.com",
            phone_number="+919876543288",
            first_name="Customer",
            last_name="One",
        )
        self.order = Order.objects.create(
            order_number="BMP-NOTIF-API",
            user=self.customer,
            order_status=OrderStatus.CONFIRMED,
            shipping_recipient_name="Customer One",
            shipping_phone_number="+919876543288",
            shipping_address_line_1="Market Road",
            shipping_city="Thirthahalli",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="577432",
            items_subtotal=Decimal("120.00"),
            shipping_fee=Decimal("40.00"),
            grand_total=Decimal("160.00"),
        )
        self.log = NotificationLog.objects.create(
            recipient=self.customer,
            recipient_target="customer_notify@example.com",
            channel=NotificationChannel.EMAIL,
            event=NotificationEvent.ORDER_CONFIRMED,
            order=self.order,
            idempotency_key="staff-api-test-1:ORDER_CONFIRMED:EMAIL",
            subject="Order Placed",
            content="<p>Order Placed</p>",
            status=NotificationStatus.SENT,
        )

    def test_staff_list_notifications(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get("/api/v1/staff/notifications/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["order_number"], self.order.order_number)

    def test_staff_filter_notifications(self):
        self.client.force_authenticate(user=self.staff_user)

        # Filter by matching channel
        response = self.client.get("/api/v1/staff/notifications/", {"channel": "EMAIL"})
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)

        # Filter by non-matching channel
        response = self.client.get("/api/v1/staff/notifications/", {"channel": "SMS"})
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 0)

    def test_staff_detail_notification(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(f"/api/v1/staff/notifications/{self.log.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["idempotency_key"], self.log.idempotency_key)

    def test_staff_resend_notification(self):
        self.client.force_authenticate(user=self.staff_user)
        url = f"/api/v1/staff/notifications/{self.log.id}/resend/"
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

    def test_regular_customer_forbidden(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get("/api/v1/staff/notifications/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_role_user_can_access_notifications(self):
        staff_role_user = User.objects.create_user(
            email="staff_role_notif@example.com",
            phone_number="+919876543255",
            role=Role.STAFF,
        )
        self.client.force_authenticate(user=staff_role_user)
        response = self.client.get("/api/v1/staff/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_manager_role_user_can_access_notifications(self):
        manager_user = User.objects.create_user(
            email="manager_role_notif@example.com",
            phone_number="+919876543244",
            role=Role.MANAGER,
        )
        self.client.force_authenticate(user=manager_user)
        response = self.client.get("/api/v1/staff/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_unauthorized(self):
        response = self.client.get("/api/v1/staff/notifications/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
