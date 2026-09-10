from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.cart.services import CartService
from apps.catalog.models import Category, Form, Product, ProductVariant, Tier
from apps.inventory.services import InventoryService
from apps.promotions.models import Coupon, DiscountType


class CartCouponAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.now = timezone.now()
        self.user = User.objects.create_user(
            "api_shopper@example.com", "9876543233", "StrongPassword123!"
        )
        self.client.force_authenticate(user=self.user)

        self.category = Category.objects.create(name="Spices", slug="spices-api")
        self.product = Product.objects.create(
            name="Kumta Turmeric",
            slug="kumta-turmeric",
            category=self.category,
            tier=Tier.EVERYDAY,
            form=Form.GROUND,
            hsn_code="09103030",
            gst_rate=Decimal("5.00"),
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="500g Jar",
            sku="BMP-TURMERIC-500G",
            weight_in_grams=500,
            mrp=Decimal("300.00"),
            selling_price=Decimal("250.00"),
        )
        InventoryService.add_stock(self.variant, 50)

        self.coupon = Coupon.objects.create(
            code="SAVE10",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            min_order_value=Decimal("200.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
        )

    def test_apply_valid_coupon_to_cart(self):
        # 1. Add item to cart (2 x 250 = 500)
        cart = CartService.get_or_create_user_cart(self.user)
        CartService.add_item(cart, self.variant, 2)

        # 2. POST /api/v1/cart/coupon/
        url = reverse("cart-coupon-apply")
        response = self.client.post(url, {"code": "save10"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json().get("data", response.json())
        self.assertIn("cart", data)
        self.assertEqual(data["cart"]["applied_coupon_code"], "SAVE10")
        self.assertEqual(data["cart"]["items_subtotal"], "500.00")
        self.assertEqual(data["cart"]["discount_amount"], "50.00")
        self.assertEqual(data["cart"]["net_subtotal"], "450.00")

    def test_apply_invalid_coupon_returns_400(self):
        cart = CartService.get_or_create_user_cart(self.user)
        CartService.add_item(cart, self.variant, 2)

        url = reverse("cart-coupon-apply")
        response = self.client.post(url, {"code": "NONEXISTENT"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_apply_coupon_below_min_order_value_returns_400(self):
        Coupon.objects.create(
            code="BIGSPEND",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("100.00"),
            min_order_value=Decimal("1000.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
        )
        cart = CartService.get_or_create_user_cart(self.user)
        CartService.add_item(cart, self.variant, 1)  # 1 x 250 = 250 < 1000

        url = reverse("cart-coupon-apply")
        response = self.client.post(url, {"code": "BIGSPEND"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_apply_coupon_to_empty_cart_returns_400(self):
        url = reverse("cart-coupon-apply")
        response = self.client.post(url, {"code": "SAVE10"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remove_coupon_via_delete(self):
        cart = CartService.get_or_create_user_cart(self.user)
        CartService.add_item(cart, self.variant, 2)
        cart.applied_coupon = self.coupon
        cart.save()

        url = reverse("cart-coupon-apply")
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json().get("data", response.json())
        self.assertIsNone(data["cart"]["applied_coupon_code"])
        self.assertEqual(data["cart"]["discount_amount"], "0.00")
        self.assertEqual(data["cart"]["net_subtotal"], "500.00")

    def test_remove_coupon_via_remove_route(self):
        cart = CartService.get_or_create_user_cart(self.user)
        CartService.add_item(cart, self.variant, 2)
        cart.applied_coupon = self.coupon
        cart.save()

        url = reverse("cart-coupon-remove")
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json().get("data", response.json())
        self.assertIsNone(data["cart"]["applied_coupon_code"])
