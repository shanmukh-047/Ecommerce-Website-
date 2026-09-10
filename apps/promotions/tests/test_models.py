from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.orders.models import Order, OrderStatus
from apps.promotions.models import (
    Coupon,
    CouponUsage,
    DiscountType,
    OrderDiscountSnapshot,
    Promotion,
    PromotionType,
)


class PromotionModelTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = User.objects.create_user(
            "promo_test@example.com", "9876543230", "StrongPassword123!"
        )

    def test_coupon_creation_and_normalization(self):
        coupon = Coupon.objects.create(
            code="  save20  ",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("20.00"),
            valid_from=self.now,
            valid_to=self.now + timedelta(days=7),
        )
        self.assertEqual(coupon.code, "SAVE20")
        self.assertTrue(coupon.is_currently_active)

    def test_coupon_percentage_exceeding_100_rejected(self):
        coupon = Coupon(
            code="INVALID150",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("150.00"),
            valid_from=self.now,
            valid_to=self.now + timedelta(days=7),
        )
        with self.assertRaises(ValidationError):
            coupon.full_clean()

    def test_coupon_valid_to_before_valid_from_rejected(self):
        coupon = Coupon(
            code="TIMETRAVEL",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("50.00"),
            valid_from=self.now,
            valid_to=self.now - timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            coupon.full_clean()

    def test_coupon_usage_uniqueness_per_order(self):
        coupon = Coupon.objects.create(
            code="SINGLEORDER",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("50.00"),
            valid_from=self.now,
            valid_to=self.now + timedelta(days=7),
        )
        order = Order.objects.create(
            order_number="BMP-ORD-TEST-PROMO-1",
            user=self.user,
            order_status=OrderStatus.PENDING_PAYMENT,
            items_subtotal=Decimal("500.00"),
            grand_total=Decimal("450.00"),
            shipping_recipient_name="Deepa Rao",
            shipping_phone_number="9876543210",
            shipping_address_line_1="123 Malenadu Way",
            shipping_city="Thirthahalli",
            shipping_state="KARNATAKA",
            shipping_pincode="577432",
        )

        CouponUsage.objects.create(
            coupon=coupon,
            user=self.user,
            order=order,
            discount_amount=Decimal("50.00"),
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            CouponUsage.objects.create(
                coupon=coupon,
                user=self.user,
                order=order,
                discount_amount=Decimal("50.00"),
            )

    def test_promotion_creation_and_clean(self):
        promo = Promotion.objects.create(
            name="Diwali Festival Discount",
            promo_type=PromotionType.ORDER_DISCOUNT,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            valid_from=self.now,
            valid_to=self.now + timedelta(days=14),
            priority=50,
        )
        self.assertEqual(promo.name, "Diwali Festival Discount")
        self.assertTrue(promo.is_currently_active)

    def test_order_discount_snapshot(self):
        coupon = Coupon.objects.create(
            code="SNAPTEST",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("100.00"),
            valid_from=self.now,
            valid_to=self.now + timedelta(days=7),
        )
        order = Order.objects.create(
            order_number="BMP-ORD-TEST-PROMO-2",
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
        snapshot = OrderDiscountSnapshot.objects.create(
            order=order,
            coupon=coupon,
            discount_name=f"Coupon: {coupon.code}",
            discount_type=coupon.discount_type,
            discount_value=coupon.discount_value,
            applied_amount=Decimal("100.00"),
            statutory_gst_adjusted=True,
        )
        self.assertEqual(snapshot.order, order)
        self.assertEqual(snapshot.applied_amount, Decimal("100.00"))
        self.assertTrue(snapshot.statutory_gst_adjusted)
