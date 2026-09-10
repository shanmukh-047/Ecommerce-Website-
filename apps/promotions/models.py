import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.core.models import TimeStampedModel


class DiscountType(models.TextChoices):
    PERCENTAGE = "PERCENTAGE", "Percentage"
    FIXED_AMOUNT = "FIXED_AMOUNT", "Fixed Amount"


class CouponScope(models.TextChoices):
    ORDER = "ORDER", "Entire Order"
    CATEGORY = "CATEGORY", "Specific Categories"
    PRODUCT = "PRODUCT", "Specific Products/Variants"


class PromotionType(models.TextChoices):
    ORDER_DISCOUNT = "ORDER_DISCOUNT", "Order Level Discount"
    BUY_X_GET_Y = "BUY_X_GET_Y", "Buy X Get Y"
    CATEGORY_DISCOUNT = "CATEGORY_DISCOUNT", "Category Discount"
    FREE_SHIPPING = "FREE_SHIPPING", "Free Shipping"


class Coupon(TimeStampedModel):
    """Represents a promotional discount coupon redeemable by customer code."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.CharField(max_length=255, blank=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    max_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    usage_limit_total = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum global redemptions allowed across all customers.",
    )
    usage_limit_per_user = models.PositiveIntegerField(
        default=1,
        help_text="Maximum redemptions allowed per individual customer account.",
    )
    times_used = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    applicable_to_wholesale = models.BooleanField(
        default=False,
        help_text="Whether this coupon can be combined with wholesale contract pricing.",
    )
    scope = models.CharField(max_length=20, choices=CouponScope.choices, default=CouponScope.ORDER)
    applicable_categories = models.ManyToManyField(
        "catalog.Category", blank=True, related_name="coupons"
    )
    applicable_variants = models.ManyToManyField(
        "catalog.ProductVariant", blank=True, related_name="coupons"
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(discount_value__gt=Decimal("0.00")),
                name="coupon_discount_value_positive",
            ),
            models.CheckConstraint(
                check=Q(min_order_value__gte=Decimal("0.00")),
                name="coupon_min_order_value_non_negative",
            ),
            models.CheckConstraint(
                check=Q(valid_to__gt=F("valid_from")),
                name="coupon_valid_to_after_valid_from",
            ),
            models.CheckConstraint(
                check=Q(times_used__gte=0),
                name="coupon_times_used_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.discount_type}: {self.discount_value})"

    def clean(self) -> None:
        super().clean()
        if self.code:
            self.code = self.code.strip().upper()
        if self.valid_to and self.valid_from and self.valid_to <= self.valid_from:
            raise ValidationError({"valid_to": "valid_to must be strictly after valid_from."})
        if self.discount_type == DiscountType.PERCENTAGE:
            if self.discount_value > Decimal("100.00"):
                raise ValidationError({"discount_value": "Percentage discount cannot exceed 100%."})

    def save(self, *args, **kwargs) -> None:
        if self.code:
            self.code = self.code.strip().upper()
        update_fields = kwargs.get("update_fields")
        if not update_fields:
            self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_currently_active(self) -> bool:
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_to:
            return False
        if self.usage_limit_total is not None and self.times_used >= self.usage_limit_total:
            return False
        return True


class CouponUsage(TimeStampedModel):
    """Tracks each individual redemption of a coupon by a user for an order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT, related_name="usages")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="coupon_usages",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="coupon_usages",
        null=True,
        blank=True,
    )
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-used_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["coupon", "order"],
                condition=Q(order__isnull=False),
                name="unique_coupon_per_order",
            ),
            models.CheckConstraint(
                check=Q(discount_amount__gte=Decimal("0.00")),
                name="coupon_usage_discount_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} used {self.coupon.code} for Rs. {self.discount_amount}"


class Promotion(TimeStampedModel):
    """Automatic promotional campaigns evaluated without requiring a promo code."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    promo_type = models.CharField(max_length=30, choices=PromotionType.choices)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    max_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    priority = models.PositiveIntegerField(
        default=100, help_text="Evaluation precedence: lower values evaluate first."
    )
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    applicable_to_wholesale = models.BooleanField(
        default=False,
        help_text="Whether this promotion applies to wholesale/B2B tier customers.",
    )
    stackable_with_coupons = models.BooleanField(
        default=True,
        help_text="Whether customer coupons can be combined on top of this automatic promotion.",
    )

    class Meta:
        ordering = ["priority", "-created_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(discount_value__gt=Decimal("0.00")),
                name="promotion_discount_value_positive",
            ),
            models.CheckConstraint(
                check=Q(min_order_value__gte=Decimal("0.00")),
                name="promotion_min_order_value_non_negative",
            ),
            models.CheckConstraint(
                check=Q(valid_to__gt=F("valid_from")),
                name="promotion_valid_to_after_valid_from",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.promo_type})"

    def clean(self) -> None:
        super().clean()
        if self.valid_to and self.valid_from and self.valid_to <= self.valid_from:
            raise ValidationError({"valid_to": "valid_to must be strictly after valid_from."})
        if self.discount_type == DiscountType.PERCENTAGE:
            if self.discount_value > Decimal("100.00"):
                raise ValidationError({"discount_value": "Percentage discount cannot exceed 100%."})

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_currently_active(self) -> bool:
        now = timezone.now()
        return self.is_active and (self.valid_from <= now <= self.valid_to)


class PromotionRule(TimeStampedModel):
    """Specific SKU, category, or bundle requirement for a Promotion."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name="rules")
    target_category = models.ForeignKey(
        "catalog.Category",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="promotion_rules",
    )
    target_variant = models.ForeignKey(
        "catalog.ProductVariant",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="promotion_rules",
    )
    min_quantity = models.PositiveIntegerField(
        default=1,
        help_text="Minimum required item quantity for this rule to trigger.",
    )

    class Meta:
        ordering = ["created_at"]


class OrderDiscountSnapshot(TimeStampedModel):
    """Immutable audit trail capturing exact promotional discounts applied to an Order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="discount_snapshots",
    )
    coupon = models.ForeignKey(
        Coupon,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_snapshots",
    )
    promotion = models.ForeignKey(
        Promotion,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_snapshots",
    )
    discount_name = models.CharField(max_length=255)
    discount_type = models.CharField(max_length=20)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    applied_amount = models.DecimalField(max_digits=10, decimal_places=2)
    statutory_gst_adjusted = models.BooleanField(
        default=True,
        help_text="Affirms discount reduces GST taxable consideration under Section 15(3) CGST Act.",
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Order {self.order_id}: {self.discount_name} (-Rs. {self.applied_amount})"
