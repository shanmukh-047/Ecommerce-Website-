from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Address, User
from apps.cart.services import CartService
from apps.catalog.models import Category, Form, Product, ProductVariant, Tier
from apps.inventory.services import InventoryService
from apps.orders.services.checkout_service import CheckoutService, OrderStateMachine
from apps.promotions.models import Coupon, CouponUsage, DiscountType, OrderDiscountSnapshot


class CheckoutDiscountIntegrationTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = User.objects.create_user(
            "checkout_shopper@example.com", "9876543234", "StrongPassword123!"
        )
        self.address = Address.objects.create(
            user=self.user,
            recipient_name="Deepa Rao",
            phone_number="9876543210",
            address_line_1="123 Malenadu Way",
            city="Thirthahalli",
            state="KARNATAKA",
            pincode="577432",
        )
        self.category = Category.objects.create(name="Spices", slug="spices-checkout")
        self.product = Product.objects.create(
            name="Sirsi Clove",
            slug="sirsi-clove",
            category=self.category,
            tier=Tier.EVERYDAY,
            form=Form.WHOLE,
            hsn_code="09071000",
            gst_rate=Decimal("5.00"),
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="100g Pouch",
            sku="BMP-CLOVE-100G",
            weight_in_grams=100,
            mrp=Decimal("250.00"),
            selling_price=Decimal("200.00"),
        )
        InventoryService.add_stock(self.variant, 50)

        self.coupon = Coupon.objects.create(
            code="CLOVE50",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("50.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
            usage_limit_total=5,
            usage_limit_per_user=1,
        )

    def test_checkout_applies_discount_and_creates_snapshots(self):
        cart = CartService.get_or_create_user_cart(self.user)
        CartService.add_item(cart, self.variant, 3)  # 3 x 200 = 600
        cart.applied_coupon = self.coupon
        cart.save()

        order = CheckoutService.create_order_from_cart(
            user=self.user,
            shipping_address_id=self.address.id,
            customer_notes="Please pack securely.",
        )

        self.assertEqual(order.items_subtotal, Decimal("600.00"))
        self.assertEqual(order.total_discount, Decimal("50.00"))
        self.assertEqual(order.grand_total, Decimal("550.00"))

        # Check CouponUsage
        usage = CouponUsage.objects.filter(order=order).first()
        self.assertIsNotNone(usage)
        self.assertEqual(usage.coupon, self.coupon)
        self.assertEqual(usage.user, self.user)
        self.assertEqual(usage.discount_amount, Decimal("50.00"))

        # Check coupon times_used
        self.coupon.refresh_from_db()
        self.assertEqual(self.coupon.times_used, 1)

        # Check OrderDiscountSnapshot
        snapshot = OrderDiscountSnapshot.objects.filter(order=order).first()
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.coupon, self.coupon)
        self.assertEqual(snapshot.applied_amount, Decimal("50.00"))
        self.assertTrue(snapshot.statutory_gst_adjusted)

        # Check cart cleaned
        cart.refresh_from_db()
        self.assertIsNone(cart.applied_coupon)
        self.assertFalse(cart.items.exists())

    def test_order_cancellation_releases_coupon_usage(self):
        cart = CartService.get_or_create_user_cart(self.user)
        CartService.add_item(cart, self.variant, 2)
        cart.applied_coupon = self.coupon
        cart.save()

        order = CheckoutService.create_order_from_cart(
            user=self.user,
            shipping_address_id=self.address.id,
        )
        self.coupon.refresh_from_db()
        self.assertEqual(self.coupon.times_used, 1)

        # Cancel order
        OrderStateMachine.cancel_order(order, actor=self.user, reason="Customer cancelled")
        self.coupon.refresh_from_db()
        self.assertEqual(self.coupon.times_used, 0)
        self.assertFalse(CouponUsage.objects.filter(order=order).exists())
