from decimal import Decimal
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, User, VerificationStatus, WholesaleProfile
from apps.cart.exceptions import CartConflict
from apps.cart.models import Cart, CartItem
from apps.cart.services import CartService
from apps.catalog.models import WholesaleTierPricing
from apps.inventory.services import InventoryService
from apps.inventory.tests.factories import create_variant


class CartTests(TestCase):
    def setUp(self):
        self.variant = create_variant("cart")
        self.user = User.objects.create_user("cart@example.com", "9876543220", "StrongPassword123!")
        self.other = User.objects.create_user(
            "other@example.com", "9876543221", "StrongPassword123!"
        )
        InventoryService.add_stock(self.variant, 10)

    def test_user_cart(self):
        cart = CartService.get_or_create_user_cart(self.user)
        self.assertEqual(cart.user, self.user)
        self.assertIsNone(cart.guest_token)

    def test_guest_cart(self):
        cart, created = CartService.get_or_create_guest_cart()
        self.assertTrue(created)
        self.assertTrue(cart.guest_token)
        self.assertIsNone(cart.user)

    def test_invalid_guest_token(self):
        with self.assertRaises(CartConflict):
            CartService.get_or_create_guest_cart("invalid-nonexistent-token")

    def test_owner_constraint_orphan_forbidden(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cart.objects.create()

    def test_owner_constraint_both_user_and_guest_forbidden(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cart.objects.create(user=self.user, guest_token="some-guest-token")

    def test_owner_constraint_empty_guest_token_forbidden(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cart.objects.create(guest_token="")

    def test_cart_item_quantity_positive(self):
        cart = CartService.get_or_create_user_cart(self.user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItem.objects.create(cart=cart, variant=self.variant, quantity=0)

    def test_duplicate_items_blocked(self):
        cart = CartService.get_or_create_user_cart(self.user)
        CartItem.objects.create(cart=cart, variant=self.variant, quantity=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItem.objects.create(cart=cart, variant=self.variant, quantity=1)

    def test_add_and_accumulate(self):
        cart = CartService.get_or_create_user_cart(self.user)
        CartService.add_item(cart, self.variant, 2)
        CartService.add_item(cart, self.variant, 3)
        self.assertEqual(cart.items.get().quantity, 5)

    def test_update(self):
        cart = CartService.get_or_create_user_cart(self.user)
        item = CartService.add_item(cart, self.variant, 2)
        CartService.update_item(cart, item.id, 4)
        self.assertEqual(cart.items.get().quantity, 4)

    def test_remove(self):
        cart = CartService.get_or_create_user_cart(self.user)
        item = CartService.add_item(cart, self.variant, 2)
        CartService.remove_item(cart, item.id)
        self.assertFalse(cart.items.exists())

    def test_clear(self):
        cart = CartService.get_or_create_user_cart(self.user)
        CartService.add_item(cart, self.variant, 2)
        CartService.clear_cart(cart)
        self.assertFalse(cart.items.exists())

    def test_insufficient(self):
        cart = CartService.get_or_create_user_cart(self.user)
        with self.assertRaises(CartConflict):
            CartService.add_item(cart, self.variant, 11)

    def test_inactive(self):
        self.variant.is_active = False
        self.variant.save()
        cart = CartService.get_or_create_user_cart(self.user)
        with self.assertRaises(CartConflict):
            CartService.add_item(cart, self.variant, 1)

    def test_cart_does_not_reserve_inventory(self):
        cart = CartService.get_or_create_user_cart(self.user)
        CartService.add_item(cart, self.variant, 2)
        self.variant.stock_item.refresh_from_db()
        self.assertEqual(self.variant.stock_item.quantity_reserved, 0)
        self.assertEqual(self.variant.stock_item.quantity_available, 10)

    def test_merge_caps_quantity(self):
        guest, _ = CartService.get_or_create_guest_cart()
        CartService.add_item(guest, self.variant, 7)
        user_cart = CartService.get_or_create_user_cart(self.user)
        CartService.add_item(user_cart, self.variant, 5)

        _, adjustments = CartService.merge_guest_cart_into_user_cart(self.user, guest.guest_token)
        self.assertEqual(user_cart.items.get().quantity, 10)
        self.assertTrue(adjustments)
        self.assertEqual(adjustments[0]["requested"], 12)
        self.assertEqual(adjustments[0]["accepted"], 10)

    def test_guest_retail_price(self):
        cart, _ = CartService.get_or_create_guest_cart()
        item = CartService.add_item(cart, self.variant, 1)
        self.assertEqual(CartService.unit_price(item.variant, 1), Decimal("90.00"))

    def test_wholesale_price(self):
        self.user.role = Role.WHOLESALE_APPROVED
        self.user.save()
        WholesaleProfile.objects.create(
            user=self.user,
            company_name="Malenadu Organics",
            gstin="29ABCDE1234F1Z5",
            pan_number="ABCDE1234F",
            verification_status=VerificationStatus.APPROVED,
        )
        WholesaleTierPricing.objects.create(
            variant=self.variant,
            min_quantity=2,
            wholesale_price_per_unit=Decimal("70.00"),
        )
        self.variant = (
            type(self.variant).objects.prefetch_related("wholesale_slabs").get(pk=self.variant.pk)
        )
        self.assertEqual(CartService.unit_price(self.variant, 2, self.user), Decimal("70.00"))

    def test_api_guest_add_and_cookie(self):
        client = APIClient()
        response = client.post(
            reverse("cart:cart-item-list"),
            {"variant_id": str(self.variant.id), "quantity": 2},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("guest_cart_token", response.cookies)

    def test_api_guest_retrieve_cart(self):
        client = APIClient()
        add_response = client.post(
            reverse("cart:cart-item-list"),
            {"variant_id": str(self.variant.id), "quantity": 2},
            format="json",
        )
        self.assertEqual(add_response.status_code, status.HTTP_200_OK)
        token = add_response.cookies["guest_cart_token"].value

        client.cookies["guest_cart_token"] = token
        get_response = client.get(reverse("cart:cart"))
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        data = get_response.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]["cart"]["items"]), 1)
        self.assertEqual(data["data"]["cart"]["items"][0]["quantity"], 2)

    def test_api_idor(self):
        cart = CartService.get_or_create_user_cart(self.user)
        item = CartService.add_item(cart, self.variant, 1)

        client = APIClient()
        client.force_authenticate(self.other)
        response = client.patch(
            reverse("cart:cart-item-detail", kwargs={"pk": item.id}),
            {"quantity": 2},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_api_envelope(self):
        client = APIClient()
        response = client.get(reverse("cart:cart"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("cart", payload["data"])
        self.assertIn("request_id", payload)

    def test_validate_cart(self):
        cart = CartService.get_or_create_user_cart(self.user)
        CartService.add_item(cart, self.variant, 5)

        issues = CartService.validate_cart(cart, self.user)
        self.assertEqual(len(issues), 0)

        # Deactivate variant
        self.variant.is_active = False
        self.variant.save()
        issues = CartService.validate_cart(cart, self.user)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["code"], "INACTIVE_VARIANT")
