from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.inventory.models import StockItem
from apps.inventory.tests.factories import create_variant


class InventoryAPITests(APITestCase):
    def setUp(self):
        self.variant = create_variant()
        self.customer = User.objects.create_user(
            email="inventory-customer@example.com",
            phone_number="9876543210",
            password="StrongPassword123!",
            role=Role.CUSTOMER,
        )
        self.staff = User.objects.create_user(
            email="inventory-staff@example.com",
            phone_number="9876543211",
            password="StrongPassword123!",
            role=Role.STAFF,
        )
        self.manager = User.objects.create_user(
            email="inventory-manager@example.com",
            phone_number="9876543212",
            password="StrongPassword123!",
            role=Role.MANAGER,
        )

    def test_unauthenticated_inventory_access_is_denied(self):
        response = self.client.get(reverse("inventory:stock-item-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_inventory_access_is_denied(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("inventory:stock-item-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_restock_and_view_inventory(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            reverse("inventory:stock-restock"),
            {"variant_id": str(self.variant.id), "quantity": 8, "note": "Receiving"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["quantity_on_hand"], 8)

        response = self.client.get(reverse("inventory:stock-item-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["count"], 1)

    def test_staff_cannot_adjust_and_manager_can_adjust(self):
        stock_item = StockItem.objects.create(variant=self.variant, quantity_on_hand=8)
        url = reverse("inventory:stock-adjust", kwargs={"pk": stock_item.id})

        self.client.force_authenticate(self.staff)
        response = self.client.post(url, {"quantity_delta": -2}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.manager)
        response = self.client.post(
            url, {"quantity_delta": -2, "note": "Count correction"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["quantity_on_hand"], 6)

    def test_invalid_restock_and_adjustment_are_rejected(self):
        self.client.force_authenticate(self.manager)
        response = self.client.post(
            reverse("inventory:stock-restock"),
            {"variant_id": str(self.variant.id), "quantity": 0},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        stock_item = StockItem.objects.create(variant=self.variant, quantity_on_hand=8)
        response = self.client.post(
            reverse("inventory:stock-adjust", kwargs={"pk": stock_item.id}),
            {"quantity_delta": 0},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
