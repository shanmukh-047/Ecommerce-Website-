import threading
import unittest
from datetime import timedelta
from decimal import Decimal

from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone

from apps.accounts.models import Address, User
from apps.cart.services import CartService
from apps.catalog.models import Category, Form, Product, ProductVariant, Tier
from apps.inventory.services import InventoryService
from apps.orders.exceptions import OrderConflict
from apps.promotions.models import Coupon, DiscountType


class ConcurrencyCouponCheckoutTests(TransactionTestCase):
    """
    Validates row-level locking concurrency protection during checkout
    with competitive single-use coupons across threads.
    """

    def setUp(self):
        self.now = timezone.now()
        self.user1 = User.objects.create_user(
            "racer1@example.com", "9876543241", "StrongPassword123!"
        )
        self.user2 = User.objects.create_user(
            "racer2@example.com", "9876543242", "StrongPassword123!"
        )

        self.address1 = Address.objects.create(
            user=self.user1,
            recipient_name="Racer One",
            phone_number="9876543241",
            address_line_1="Track 1",
            city="Bengaluru",
            state="KARNATAKA",
            pincode="560001",
        )
        self.address2 = Address.objects.create(
            user=self.user2,
            recipient_name="Racer Two",
            phone_number="9876543242",
            address_line_1="Track 2",
            city="Bengaluru",
            state="KARNATAKA",
            pincode="560001",
        )

        self.category = Category.objects.create(name="Spices", slug="spices-race")
        self.product = Product.objects.create(
            name="Guntur Chilli",
            slug="guntur-chilli-race",
            category=self.category,
            tier=Tier.EVERYDAY,
            form=Form.WHOLE,
            hsn_code="09042110",
            gst_rate=Decimal("5.00"),
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="1kg",
            sku="BMP-GUNTUR-1KG",
            weight_in_grams=1000,
            mrp=Decimal("500.00"),
            selling_price=Decimal("400.00"),
        )
        InventoryService.add_stock(self.variant, 100)

        # Strictly 1 total usage allowed globally!
        self.single_use_coupon = Coupon.objects.create(
            code="SOLO100",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("100.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
            usage_limit_total=1,
            usage_limit_per_user=1,
        )

    @unittest.skipIf(
        connection.vendor == "sqlite",
        "SQLite does not support concurrent write transactions across OS threads.",
    )
    def test_concurrent_checkout_competing_for_single_use_coupon(self):
        # Setup cart 1
        cart1 = CartService.get_or_create_user_cart(self.user1)
        CartService.add_item(cart1, self.variant, 1)
        cart1.applied_coupon = self.single_use_coupon
        cart1.save()

        # Setup cart 2
        cart2 = CartService.get_or_create_user_cart(self.user2)
        CartService.add_item(cart2, self.variant, 1)
        cart2.applied_coupon = self.single_use_coupon
        cart2.save()

        results = []
        errors = []

        def run_checkout(user, address_id):
            connection.close()
            from apps.orders.services.checkout_service import CheckoutService

            try:
                order = CheckoutService.create_order_from_cart(user, address_id)
                results.append(order)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=run_checkout, args=(self.user1, self.address1.id))
        t2 = threading.Thread(target=run_checkout, args=(self.user2, self.address2.id))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Exactly 1 order must have succeeded with the discount
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        from django.db import OperationalError

        self.assertTrue(
            isinstance(errors[0], (OrderConflict, OperationalError)),
            f"Expected OrderConflict or OperationalError, got {type(errors[0])}: {errors[0]}",
        )

        self.single_use_coupon.refresh_from_db()
        self.assertEqual(self.single_use_coupon.times_used, 1)

    def test_subsequent_checkout_blocked_when_limit_exhausted_under_lock(self):
        """Validates that under row locks, once limit is reached, subsequent checkout raises OrderConflict."""
        cart1 = CartService.get_or_create_user_cart(self.user1)
        CartService.add_item(cart1, self.variant, 1)
        cart1.applied_coupon = self.single_use_coupon
        cart1.save()

        cart2 = CartService.get_or_create_user_cart(self.user2)
        CartService.add_item(cart2, self.variant, 1)
        cart2.applied_coupon = self.single_use_coupon
        cart2.save()

        from apps.orders.services.checkout_service import CheckoutService

        order1 = CheckoutService.create_order_from_cart(self.user1, self.address1.id)
        self.assertIsNotNone(order1)
        self.single_use_coupon.refresh_from_db()
        self.assertEqual(self.single_use_coupon.times_used, 1)

        with self.assertRaises(OrderConflict) as ctx:
            CheckoutService.create_order_from_cart(self.user2, self.address2.id)

        self.assertIn("maximum global usage limit", str(ctx.exception))
