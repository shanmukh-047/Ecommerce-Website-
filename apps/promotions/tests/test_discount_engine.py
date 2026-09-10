from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Category, Form, Product, ProductVariant, Tier
from apps.promotions.models import (
    Coupon,
    CouponScope,
    DiscountType,
    Promotion,
    PromotionType,
)
from apps.promotions.services.discount_engine import DiscountEngine


class MockCartItem:
    def __init__(self, variant, quantity, unit_price):
        self.variant = variant
        self.quantity = quantity
        self.unit_price = unit_price


class DiscountEngineTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.category_spices = Category.objects.create(name="Whole Spices", slug="whole-spices")
        self.category_masalas = Category.objects.create(
            name="Blended Masalas", slug="blended-masalas"
        )

        self.product_pepper = Product.objects.create(
            name="Sirsi Black Pepper",
            slug="sirsi-black-pepper",
            category=self.category_spices,
            tier=Tier.EVERYDAY,
            form=Form.WHOLE,
            hsn_code="09041110",
            gst_rate=Decimal("5.00"),
        )
        self.variant_pepper = ProductVariant.objects.create(
            product=self.product_pepper,
            variant_name="500g Pouch",
            sku="BMP-PEPPER-500G",
            weight_in_grams=500,
            mrp=Decimal("450.00"),
            selling_price=Decimal("400.00"),
        )

        self.product_sambar = Product.objects.create(
            name="Udupi Sambar Powder",
            slug="udupi-sambar-powder",
            category=self.category_masalas,
            tier=Tier.EVERYDAY,
            form=Form.BLEND,
            hsn_code="09109100",
            gst_rate=Decimal("5.00"),
        )

        self.variant_sambar = ProductVariant.objects.create(
            product=self.product_sambar,
            variant_name="250g Jar",
            sku="BMP-SAMBAR-250G",
            weight_in_grams=250,
            mrp=Decimal("180.00"),
            selling_price=Decimal("150.00"),
        )

    def test_percentage_coupon_calculation(self):
        coupon = Coupon.objects.create(
            code="FESTIVE10",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
        )
        items = [
            MockCartItem(self.variant_pepper, 2, Decimal("400.00")),  # 800.00
            MockCartItem(self.variant_sambar, 1, Decimal("150.00")),  # 150.00
        ]
        # Total subtotal = 950.00 -> 10% = 95.00
        result = DiscountEngine.evaluate_discounts(items, applied_coupon=coupon)
        self.assertEqual(result.items_subtotal, Decimal("950.00"))
        self.assertEqual(result.total_discount, Decimal("95.00"))
        self.assertEqual(result.coupon_discount, Decimal("95.00"))
        self.assertEqual(result.net_subtotal, Decimal("855.00"))

    def test_percentage_coupon_with_cap(self):
        coupon = Coupon.objects.create(
            code="BIGSAVE",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("20.00"),
            max_discount_amount=Decimal("50.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
        )
        items = [
            MockCartItem(self.variant_pepper, 2, Decimal("400.00"))
        ]  # 800.00 -> 20% is 160.00, capped at 50.00
        result = DiscountEngine.evaluate_discounts(items, applied_coupon=coupon)
        self.assertEqual(result.total_discount, Decimal("50.00"))
        self.assertEqual(result.net_subtotal, Decimal("750.00"))

    def test_fixed_amount_coupon(self):
        coupon = Coupon.objects.create(
            code="FLAT100",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("100.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
        )
        items = [MockCartItem(self.variant_pepper, 1, Decimal("400.00"))]
        result = DiscountEngine.evaluate_discounts(items, applied_coupon=coupon)
        self.assertEqual(result.total_discount, Decimal("100.00"))
        self.assertEqual(result.net_subtotal, Decimal("300.00"))

    def test_fixed_amount_cannot_exceed_subtotal(self):
        coupon = Coupon.objects.create(
            code="FLAT500",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("500.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
        )
        items = [MockCartItem(self.variant_sambar, 1, Decimal("150.00"))]
        result = DiscountEngine.evaluate_discounts(items, applied_coupon=coupon)
        self.assertEqual(result.total_discount, Decimal("150.00"))
        self.assertEqual(result.net_subtotal, Decimal("0.00"))

    def test_category_scoped_coupon(self):
        coupon = Coupon.objects.create(
            code="SPICEONLY",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("20.00"),
            scope=CouponScope.CATEGORY,
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
        )
        coupon.applicable_categories.add(self.category_spices)

        items = [
            MockCartItem(
                self.variant_pepper, 1, Decimal("400.00")
            ),  # Whole Spices (eligible: 400.00)
            MockCartItem(
                self.variant_sambar, 2, Decimal("150.00")
            ),  # Blended Masalas (ineligible: 300.00)
        ]
        # Total subtotal = 700.00, qualifying = 400.00 -> 20% of 400 = 80.00
        result = DiscountEngine.evaluate_discounts(items, applied_coupon=coupon)
        self.assertEqual(result.items_subtotal, Decimal("700.00"))
        self.assertEqual(result.total_discount, Decimal("80.00"))
        self.assertEqual(result.net_subtotal, Decimal("620.00"))

    def test_minimum_order_value_requirement(self):
        coupon = Coupon.objects.create(
            code="MIN1000",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("100.00"),
            min_order_value=Decimal("1000.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
        )
        items = [MockCartItem(self.variant_pepper, 2, Decimal("400.00"))]  # 800.00 < 1000.00
        result = DiscountEngine.evaluate_discounts(items, applied_coupon=coupon)
        self.assertEqual(result.total_discount, Decimal("0.00"))
        self.assertEqual(result.net_subtotal, Decimal("800.00"))

    def test_wholesale_exclusion(self):
        coupon = Coupon.objects.create(
            code="RETAILONLY",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("15.00"),
            applicable_to_wholesale=False,
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
        )
        items = [MockCartItem(self.variant_pepper, 10, Decimal("350.00"))]
        result = DiscountEngine.evaluate_discounts(items, applied_coupon=coupon, is_wholesale=True)
        self.assertEqual(result.total_discount, Decimal("0.00"))

    def test_stacking_automatic_promotion_and_coupon(self):
        promo = Promotion.objects.create(
            name="Summer Sale 5%",
            promo_type=PromotionType.ORDER_DISCOUNT,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("5.00"),
            priority=10,
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
            stackable_with_coupons=True,
        )
        coupon = Coupon.objects.create(
            code="EXTRA10",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
        )
        items = [MockCartItem(self.variant_pepper, 1, Decimal("1000.00"))]
        # Promo: 5% of 1000 = 50.00
        # Coupon: 10% of 1000 = 100.00
        # Total discount = 150.00, Net = 850.00
        result = DiscountEngine.evaluate_discounts(items, applied_coupon=coupon, promotions=[promo])
        self.assertEqual(result.items_subtotal, Decimal("1000.00"))
        self.assertEqual(result.promotion_discount, Decimal("50.00"))
        self.assertEqual(result.coupon_discount, Decimal("100.00"))
        self.assertEqual(result.total_discount, Decimal("150.00"))
        self.assertEqual(result.net_subtotal, Decimal("850.00"))
        self.assertEqual(len(result.breakdown), 2)
