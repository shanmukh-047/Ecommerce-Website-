from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.cart.services import CartService
from apps.catalog.models import Category, Form, Product, ProductVariant, Tier
from apps.inventory.services import InventoryService
from apps.orders.models import Order, OrderStatus
from apps.promotions.models import Coupon, CouponUsage, DiscountType
from apps.promotions.services.coupon_service import CouponService


class CouponServiceTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = User.objects.create_user(
            "shopper@example.com", "9876543231", "StrongPassword123!"
        )
        self.wholesale_user = User.objects.create_user(
            "wholesale_buyer@example.com", "9876543232", "StrongPassword123!"
        )
        self.wholesale_user.role = "WHOLESALE"
        self.wholesale_user.save()

        self.category = Category.objects.create(name="Spices", slug="spices")
        self.product = Product.objects.create(
            name="Byadgi Chilli",
            slug="byadgi-chilli",
            category=self.category,
            tier=Tier.EVERYDAY,
            form=Form.WHOLE,
            hsn_code="09042110",
            gst_rate=Decimal("5.00"),
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="1kg Pack",
            sku="BMP-CHILLI-1KG",
            weight_in_grams=1000,
            mrp=Decimal("600.00"),
            selling_price=Decimal("500.00"),
        )
        InventoryService.add_stock(self.variant, 50)

    def test_invalid_coupon_code_raises_validation_error(self):
        with self.assertRaises(ValidationError) as ctx:
            CouponService.validate_coupon("DOESNOTEXIST")
        self.assertIn("Invalid coupon code", str(ctx.exception))

    def test_inactive_coupon_raises_validation_error(self):
        Coupon.objects.create(
            code="INACTIVE10",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
            is_active=False,
        )
        with self.assertRaises(ValidationError) as ctx:
            CouponService.validate_coupon("INACTIVE10")
        self.assertIn("no longer active", str(ctx.exception))

    def test_expired_coupon_raises_validation_error(self):
        Coupon.objects.create(
            code="EXPIRED10",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            valid_from=self.now - timedelta(days=10),
            valid_to=self.now - timedelta(days=1),
        )
        with self.assertRaises(ValidationError) as ctx:
            CouponService.validate_coupon("EXPIRED10")
        self.assertIn("expired", str(ctx.exception))

    def test_future_coupon_raises_validation_error(self):
        Coupon.objects.create(
            code="FUTURE10",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            valid_from=self.now + timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
        )
        with self.assertRaises(ValidationError) as ctx:
            CouponService.validate_coupon("FUTURE10")
        self.assertIn("not started yet", str(ctx.exception))

    def test_wholesale_user_rejected_for_retail_coupon(self):
        Coupon.objects.create(
            code="RETAILONLY",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            applicable_to_wholesale=False,
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
        )
        with self.assertRaises(ValidationError) as ctx:
            CouponService.validate_coupon("RETAILONLY", is_wholesale=True)
        self.assertIn("wholesale contract pricing", str(ctx.exception))

    def test_global_usage_limit_enforced(self):
        Coupon.objects.create(
            code="MAXUSAGE",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("50.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
            usage_limit_total=2,
            times_used=2,
        )
        with self.assertRaises(ValidationError) as ctx:
            CouponService.validate_coupon("MAXUSAGE")
        self.assertIn("maximum global usage limit", str(ctx.exception))

    def test_per_user_usage_limit_enforced(self):
        coupon = Coupon.objects.create(
            code="ONCEONLY",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("50.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
            usage_limit_per_user=1,
        )
        CouponUsage.objects.create(
            coupon=coupon,
            user=self.user,
            discount_amount=Decimal("50.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            CouponService.validate_coupon("ONCEONLY", user=self.user)
        self.assertIn("already reached the redemption limit", str(ctx.exception))

    def test_apply_and_remove_coupon_from_cart(self):
        coupon = Coupon.objects.create(
            code="FLAT50",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("50.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
        )
        cart = CartService.get_or_create_user_cart(self.user)
        CartService.add_item(cart, self.variant, 2)  # 2 x 500 = 1000

        cart, applied_coupon, discount = CouponService.apply_coupon_to_cart(
            cart, "FLAT50", self.user
        )
        self.assertEqual(cart.applied_coupon, coupon)
        self.assertEqual(discount, Decimal("50.00"))

        CouponService.remove_coupon_from_cart(cart)
        cart.refresh_from_db()
        self.assertIsNone(cart.applied_coupon)

    def test_apply_coupon_to_empty_cart_fails(self):
        Coupon.objects.create(
            code="FLAT50",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("50.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
        )
        cart = CartService.get_or_create_user_cart(self.user)
        with self.assertRaises(ValidationError) as ctx:
            CouponService.apply_coupon_to_cart(cart, "FLAT50", self.user)
        self.assertIn("empty cart", str(ctx.exception))

    def test_release_coupon_usage_restores_limits(self):
        coupon = Coupon.objects.create(
            code="REVERSIBLE",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("100.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
            usage_limit_total=1,
            times_used=0,
        )
        order = Order.objects.create(
            order_number="BMP-ORD-REVERSAL-1",
            user=self.user,
            order_status=OrderStatus.PENDING_PAYMENT,
            items_subtotal=Decimal("500.00"),
            grand_total=Decimal("400.00"),
            shipping_recipient_name="Deepa Rao",
            shipping_phone_number="9876543210",
            shipping_address_line_1="123 Malenadu Way",
            shipping_city="Thirthahalli",
            shipping_state="KARNATAKA",
            shipping_pincode="577432",
        )
        CouponService.lock_and_record_usage(
            coupon_id=coupon.id,
            user=self.user,
            order=order,
            discount_amount=Decimal("100.00"),
        )
        coupon.refresh_from_db()
        self.assertEqual(coupon.times_used, 1)

        # Release coupon usage
        released = CouponService.release_coupon_usage(order)
        self.assertTrue(released)
        coupon.refresh_from_db()
        self.assertEqual(coupon.times_used, 0)
        self.assertFalse(CouponUsage.objects.filter(order=order).exists())
