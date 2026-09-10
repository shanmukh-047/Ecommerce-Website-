from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.inventory.services import InventoryService
from apps.inventory.tests.factories import create_variant
from apps.orders.models import OrderStatus
from apps.orders.services import CheckoutService, OrderStateMachine
from apps.orders.tests.factories import (
    add_to_cart,
    create_order_address,
    create_order_user,
    create_staff_user,
    create_wholesale_user,
)


class StaffOrderAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = create_staff_user(email="staff1@example.com", phone="9876543260")
        self.manager = create_order_user(
            email="manager1@example.com", phone="9876543261", role=Role.MANAGER
        )
        self.customer = create_order_user(email="cust1@example.com", phone="9876543262")
        self.address = create_order_address(self.customer, recipient_name="Customer One")
        self.variant = create_variant("staffapi")
        InventoryService.add_stock(self.variant, 100)

        # Create sample order
        add_to_cart(self.customer, self.variant, 2)
        self.order = CheckoutService.create_order_from_cart(self.customer, self.address.id)

    def test_staff_endpoints_rbac(self):
        url = reverse("staff-orders:staff-order-list")

        # Unauthenticated -> 401
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # Regular customer -> 403
        self.client.force_authenticate(user=self.customer)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Staff -> 200
        self.client.force_authenticate(user=self.staff)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Manager -> 200
        self.client.force_authenticate(user=self.manager)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_staff_order_list_and_filters(self):
        # Create wholesale order
        ws_user = create_wholesale_user(email="ws_staff@example.com", phone="9876543263")
        ws_addr = create_order_address(ws_user, recipient_name="Wholesale Buyer")
        add_to_cart(ws_user, self.variant, 5)
        ws_order = CheckoutService.create_order_from_cart(ws_user, ws_addr.id)

        self.client.force_authenticate(user=self.staff)
        url = reverse("staff-orders:staff-order-list")

        # List all
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)

        # Filter by wholesale
        res = self.client.get(url, {"is_wholesale": "true"})
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["id"], str(ws_order.id))

        # Filter by status
        OrderStateMachine.transition_status(self.order, OrderStatus.CONFIRMED, actor=self.staff)
        res = self.client.get(url, {"status": OrderStatus.CONFIRMED})
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["id"], str(self.order.id))

        # Search by order_number
        res = self.client.get(url, {"search": self.order.order_number})
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["id"], str(self.order.id))

        # Search by recipient name
        res = self.client.get(url, {"search": "Customer One"})
        self.assertEqual(len(res.data["results"]), 1)

    def test_staff_order_detail(self):
        self.client.force_authenticate(user=self.staff)
        url = reverse("staff-orders:staff-order-detail", kwargs={"pk": self.order.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["order"]["id"], str(self.order.id))
        self.assertEqual(len(res.data["order"]["lines"]), 1)
        self.assertIn("status_history", res.data["order"])

    def test_staff_order_status_update_success(self):
        self.client.force_authenticate(user=self.staff)
        url = reverse("staff-orders:staff-order-status-update", kwargs={"pk": self.order.id})

        # Transition to CONFIRMED
        payload = {
            "status": OrderStatus.CONFIRMED,
            "notes": "Razorpay payment ID pay_12345 verified.",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["order"]["order_status"], OrderStatus.CONFIRMED)
        self.assertIsNotNone(res.data["order"]["paid_at"])

        # Transition to PROCESSING
        payload = {"status": OrderStatus.PROCESSING, "notes": "Dispatched to packing bay."}
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["order"]["order_status"], OrderStatus.PROCESSING)

    def test_staff_order_status_update_invalid_transition(self):
        self.client.force_authenticate(user=self.staff)
        url = reverse("staff-orders:staff-order-status-update", kwargs={"pk": self.order.id})

        # Cannot jump straight to DELIVERED from PENDING_PAYMENT
        payload = {"status": OrderStatus.DELIVERED, "notes": "Invalid jump."}
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("Cannot transition order", res.data["message"])

    def test_staff_order_status_update_validation_error(self):
        self.client.force_authenticate(user=self.staff)
        url = reverse("staff-orders:staff-order-status-update", kwargs={"pk": self.order.id})

        # Missing status
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid choice
        res = self.client.post(url, {"status": "INVALID_STATUS"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
