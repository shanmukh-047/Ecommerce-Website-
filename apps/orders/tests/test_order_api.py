from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.models import ReservationStatus, StockReservation
from apps.inventory.services import InventoryService
from apps.inventory.tests.factories import create_variant
from apps.orders.models import OrderStatus
from apps.orders.services import CheckoutService, OrderStateMachine
from apps.orders.tests.factories import (
    add_to_cart,
    create_order_address,
    create_order_user,
    create_staff_user,
)


class CustomerOrderAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_order_user()
        self.address = create_order_address(self.user)
        self.variant = create_variant("custapi")
        InventoryService.add_stock(self.variant, 50)

    def test_checkout_unauthenticated(self):
        response = self.client.post(
            reverse("orders:checkout"),
            {"shipping_address_id": str(self.address.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_checkout_missing_address_id(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("orders:checkout"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_empty_cart(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("orders:checkout"),
            {"shipping_address_id": str(self.address.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_checkout_address_idor_blocked(self):
        other_user = create_order_user(email="other_addr@example.com", phone="9876543277")
        other_address = create_order_address(other_user)

        add_to_cart(self.user, self.variant, 2)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("orders:checkout"),
            {"shipping_address_id": str(other_address.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("Valid shipping address", response.data["message"])

    def test_checkout_success(self):
        add_to_cart(self.user, self.variant, 2)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("orders:checkout"),
            {
                "shipping_address_id": str(self.address.id),
                "customer_notes": "Handle with extra care please.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data["order"]
        self.assertTrue(data["order_number"].startswith("BMP-"))
        self.assertEqual(data["order_status"], OrderStatus.PENDING_PAYMENT)
        self.assertEqual(Decimal(data["grand_total"]), Decimal("180.00"))
        self.assertEqual(len(data["lines"]), 1)
        self.assertEqual(data["lines"][0]["quantity"], 2)
        self.assertEqual(data["shipping_city"], "Sirsi")

    def test_order_list_isolation(self):
        other_user = create_order_user(email="other_list@example.com", phone="9876543276")
        other_address = create_order_address(other_user)

        # Create 2 orders for user
        add_to_cart(self.user, self.variant, 1)
        order_1 = CheckoutService.create_order_from_cart(self.user, self.address.id)

        add_to_cart(self.user, self.variant, 1)
        order_2 = CheckoutService.create_order_from_cart(self.user, self.address.id)

        # Create 1 order for other_user
        add_to_cart(other_user, self.variant, 1)
        CheckoutService.create_order_from_cart(other_user, other_address.id)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("orders:order-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        order_ids = [o["id"] for o in response.data["results"]]
        self.assertEqual(len(order_ids), 2)
        self.assertIn(str(order_1.id), order_ids)
        self.assertIn(str(order_2.id), order_ids)

    def test_order_detail_and_idor_prevention(self):
        add_to_cart(self.user, self.variant, 1)
        order = CheckoutService.create_order_from_cart(self.user, self.address.id)

        other_user = create_order_user(email="other_detail@example.com", phone="9876543275")

        # Owner gets 200 OK
        self.client.force_authenticate(user=self.user)
        url = reverse("orders:order-detail", kwargs={"pk": order.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["order"]["id"], str(order.id))
        self.assertIn("status_history", response.data["order"])

        # Other user gets 404 NOT FOUND
        self.client.force_authenticate(user=other_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_order_cancel_success(self):
        add_to_cart(self.user, self.variant, 2)
        order = CheckoutService.create_order_from_cart(self.user, self.address.id)

        self.client.force_authenticate(user=self.user)
        url = reverse("orders:order-cancel", kwargs={"pk": order.id})
        response = self.client.post(url, {"reason": "Found better spice mix"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["order"]["order_status"], OrderStatus.CANCELLED)

        # Reservation released
        res = StockReservation.objects.get(reference_type="ORDER", reference_id=order.id)
        self.assertEqual(res.status, ReservationStatus.RELEASED)

    def test_order_cancel_not_allowed_for_confirmed_order(self):
        add_to_cart(self.user, self.variant, 2)
        order = CheckoutService.create_order_from_cart(self.user, self.address.id)
        staff = create_staff_user(email="staff_transit@example.com", phone="9876543274")
        OrderStateMachine.transition_status(order, OrderStatus.CONFIRMED, actor=staff)

        # Customer attempts to cancel confirmed order -> 409 Conflict
        self.client.force_authenticate(user=self.user)
        url = reverse("orders:order-cancel", kwargs={"pk": order.id})
        response = self.client.post(url, {"reason": "Cancel please"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
