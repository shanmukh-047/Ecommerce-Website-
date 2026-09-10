import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.accounts.models import IndianStates
from apps.core.models import TimeStampedModel


class OrderStatus(models.TextChoices):
    PENDING_PAYMENT = "PENDING_PAYMENT", "Pending Payment"
    CONFIRMED = "CONFIRMED", "Confirmed"
    PROCESSING = "PROCESSING", "Processing"
    SHIPPED = "SHIPPED", "Shipped"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"
    FAILED = "FAILED", "Failed"
    REFUNDED = "REFUNDED", "Refunded"


class OrderQuerySet(models.QuerySet):
    def with_details(self):
        """
        Optimized queryset that eager loads user, payments, order status history,
        line items, pack variants, products, and active product images in a single batch.
        Eliminates N+1 queries across customer and staff order views.
        """
        from apps.catalog.models import ProductImage
        from apps.payments.models import Payment

        return self.select_related("user").prefetch_related(
            models.Prefetch(
                "payments",
                queryset=Payment.objects.order_by("-created_at"),
            ),
            models.Prefetch(
                "status_history",
                queryset=self.model.status_history.rel.related_model.objects.select_related("actor"),
            ),
            models.Prefetch(
                "lines",
                queryset=self.model.lines.rel.related_model.objects.select_related(
                    "variant__product"
                ).prefetch_related(
                    models.Prefetch(
                        "variant__product__images",
                        queryset=ProductImage.objects.filter(is_active=True),
                    )
                ),
            ),
        )


class Order(TimeStampedModel):
    """
    Authoritative order entity capturing customer purchases, snapshotting
    immutable shipping addresses and financial summaries.
    """

    objects = OrderQuerySet.as_manager()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=32, unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    # Named order_status for direct compatibility with ReviewService.verify_user_purchase()
    order_status = models.CharField(
        max_length=30,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING_PAYMENT,
        db_index=True,
    )

    currency = models.CharField(max_length=3, default="INR")
    items_subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)
    total_quantity = models.PositiveIntegerField(default=1)
    total_weight_in_grams = models.PositiveIntegerField(default=0)
    is_wholesale_order = models.BooleanField(default=False, db_index=True)

    # Immutable Flat Shipping Address Snapshot
    shipping_recipient_name = models.CharField(max_length=100)
    shipping_phone_number = models.CharField(max_length=15)
    shipping_address_line_1 = models.CharField(max_length=255)
    shipping_address_line_2 = models.CharField(max_length=255, blank=True, default="")
    shipping_landmark = models.CharField(max_length=100, blank=True, default="")
    shipping_city = models.CharField(max_length=100, db_index=True)
    shipping_state = models.CharField(max_length=50, choices=IndianStates.choices, db_index=True)
    shipping_pincode = models.CharField(max_length=6, db_index=True)
    shipping_address = models.ForeignKey(
        "accounts.Address",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    customer_notes = models.CharField(max_length=500, blank=True, default="")
    cancellation_reason = models.TextField(blank=True, default="")
    cancelled_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["order_status", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(grand_total__gte=0),
                name="order_grand_total_non_negative",
            ),
            models.CheckConstraint(
                check=Q(items_subtotal__gte=0),
                name="order_items_subtotal_non_negative",
            ),
        ]

    def __str__(self):
        return f"Order {self.order_number} ({self.get_order_status_display()})"

    @property
    def status(self) -> str:
        return self.order_status

    @status.setter
    def status(self, value: str):
        self.order_status = value


class OrderLineItem(TimeStampedModel):
    """
    Immutable line item snapshot capturing product, variant, SKU, weights,
    printed MRP, and charged unit price at the time of purchase.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="order_lines",
    )
    quantity = models.PositiveIntegerField()

    # Immutable Product & Pricing Snapshot
    product_name = models.CharField(max_length=200)
    variant_name = models.CharField(max_length=100)
    sku = models.CharField(max_length=64)
    weight_in_grams = models.PositiveIntegerField(null=True, blank=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    pricing_tier_applied = models.CharField(max_length=50, default="RETAIL")

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(quantity__gt=0),
                name="order_line_quantity_positive",
            ),
            models.CheckConstraint(
                check=Q(unit_price__gt=0),
                name="order_line_unit_price_positive",
            ),
            models.CheckConstraint(
                check=Q(line_subtotal__gt=0),
                name="order_line_subtotal_positive",
            ),
            models.UniqueConstraint(
                fields=["order", "variant"],
                name="unique_order_variant",
            ),
        ]

    def __str__(self):
        return f"{self.sku} x {self.quantity} (Order {self.order.order_number})"


# Backwards-compatible alias for apps.catalog.services.ReviewService
OrderItem = OrderLineItem


class OrderStatusHistory(models.Model):
    """
    Append-only audit trail logging status transitions, responsible actors,
    and operational notes throughout the order lifecycle.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField(max_length=30, blank=True, default="")
    to_status = models.CharField(max_length=30, choices=OrderStatus.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_status_changes",
    )
    notes = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.order.order_number}: {self.from_status} -> {self.to_status}"
