import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import F, Q

from apps.core.models import TimeStampedModel

from .validators import (
    category_image_upload_path,
    product_image_upload_path,
    review_image_upload_path,
    validate_image_file,
)


class Category(TimeStampedModel):
    """
    Product categories with self-referential hierarchical support
    (e.g., Spices -> Signature Blends, or Dry Fruits -> Cashews).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, db_index=True)
    slug = models.SlugField(max_length=140, unique=True, db_index=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subcategories",
    )
    description = models.TextField(blank=True, default="")
    image = models.ImageField(
        upload_to=category_image_upload_path,
        blank=True,
        null=True,
        validators=[validate_image_file],
    )
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["sort_order", "name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Tier(models.TextChoices):
    RESERVE = "RESERVE", "Reserve Tier"
    EVERYDAY = "EVERYDAY", "Everyday Fresh"


class Form(models.TextChoices):
    WHOLE = "WHOLE", "Whole Spice"
    GROUND = "GROUND", "Ground / Powdered"
    BLEND = "BLEND", "Signature Blend"
    RAW = "RAW", "Raw / Whole Nut / Dry Fruit"


class Product(TimeStampedModel):
    """
    Master product definition capturing Malenadu terroir, origin stamps,
    Sharada's oral culinary stories, and statutory Indian Legal Metrology.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    tier = models.CharField(max_length=20, choices=Tier.choices, db_index=True)
    form = models.CharField(max_length=20, choices=Form.choices, db_index=True)

    short_description = models.CharField(max_length=500, blank=True, default="")
    detailed_description = models.TextField(blank=True, default="")

    # Provenance & Storytelling
    origin_region = models.CharField(
        max_length=150, db_index=True, default="Malenadu, Karnataka, India"
    )
    plantation_provenance = models.TextField(
        blank=True,
        default="",
        help_text="Family plantation history and valley micro-climate notes.",
    )
    origin_stamp = models.CharField(max_length=200, default="Grown in Malenadu · Uttara Kannada")
    grade = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="e.g. Bold 8mm+, Grade A Export Quality",
    )
    harvest_date = models.DateField(null=True, blank=True)
    grinding_date = models.DateField(null=True, blank=True)
    sharada_note = models.TextField(
        blank=True,
        default="",
        help_text="Spoken narrative in Sharada's voice: culinary advice and flavor memories.",
    )
    qr_audio_url = models.URLField(
        blank=True,
        default="",
        help_text="Direct link to customer-accessible QR folklore audio snippet.",
    )

    # Statutory Indian Legal Metrology & Taxation Block
    fssai_license = models.CharField(max_length=20, default="11223344556677", blank=True)
    hsn_code = models.CharField(
        max_length=10,
        db_index=True,
        help_text="Statutory GST Harmonized System of Nomenclature code (e.g. 0904, 0801).",
    )
    gst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("5.00"),
        help_text="Applicable GST percentage (e.g. 5.00 or 12.00).",
    )
    packer_name = models.CharField(max_length=200, default="Bharath Masala Products")
    packer_address = models.TextField(
        default="Main Road, Thirthahalli, Shimoga District, Karnataka 577432"
    )
    best_before_guidance = models.CharField(
        max_length=150, default="Best before 12 months from packing date"
    )

    # Merchandising & Visibility Flags
    is_bestseller = models.BooleanField(default=False, db_index=True)
    is_featured_from_home = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Highlight in homepage 'From home' Reserve collection showcase.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["tier", "is_active"]),
            models.Index(fields=["is_featured_from_home", "is_active"]),
            models.Index(fields=["is_bestseller", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_tier_display()})"


class ProductVariant(TimeStampedModel):
    """
    Pack-size variants (e.g. 100g Pouch, 250g Glass Jar, 500g Eco-pack, 1kg Wholesale).
    Enforces strict MRP and selling price integrity.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    variant_name = models.CharField(max_length=100)
    sku = models.CharField(max_length=64, unique=True, db_index=True)
    weight_in_grams = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Net weight in grams for shipping and legal metrology.",
    )
    mrp = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Maximum Retail Price printed on pack.",
    )
    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Offered retail price (must be <= MRP).",
    )
    is_most_chosen = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Flag for highlighting the most popular pack size in the UI.",
    )
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"
        ordering = ["sort_order", "selling_price"]
        indexes = [
            models.Index(fields=["product", "is_active", "sort_order"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(selling_price__lte=F("mrp")),
                name="check_variant_selling_price_lte_mrp",
            ),
            models.CheckConstraint(
                check=Q(selling_price__gt=0),
                name="check_variant_selling_price_gt_zero",
            ),
            models.CheckConstraint(
                check=Q(mrp__gt=0),
                name="check_variant_mrp_gt_zero",
            ),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.variant_name} [{self.sku}] (₹{self.selling_price})"

    @property
    def savings_amount(self) -> Decimal:
        """Returns savings amount in rupees between MRP and Selling Price."""
        return max(Decimal("0.00"), self.mrp - self.selling_price)

    @property
    def discount_percentage(self) -> int:
        """Computes rounded percentage discount against MRP."""
        if self.mrp > Decimal("0.00") and self.mrp > self.selling_price:
            return int(round(((self.mrp - self.selling_price) / self.mrp) * 100))
        return 0

    @property
    def savings_label(self) -> str:
        """Formatted user-facing savings label."""
        if self.savings_amount > Decimal("0.00"):
            if self.savings_amount == int(self.savings_amount):
                formatted_amount = f"{int(self.savings_amount)}"
            else:
                formatted_amount = f"{self.savings_amount:.2f}"
            return f"Save ₹{formatted_amount} ({self.discount_percentage}% OFF)"
        return ""


class WholesaleTierPricing(TimeStampedModel):
    """
    Login-gated bulk wholesale pricing slabs for approved B2B customers.
    Example: 10+ units @ ₹420/ea, 25+ units @ ₹390/ea, 50+ units @ ₹360/ea.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="wholesale_slabs"
    )
    min_quantity = models.PositiveIntegerField(
        help_text="Minimum order quantity threshold for this price tier."
    )
    wholesale_price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Tax-exclusive wholesale price per unit.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Wholesale Tier Pricing"
        verbose_name_plural = "Wholesale Tier Pricing Slabs"
        ordering = ["min_quantity"]
        indexes = [
            models.Index(fields=["variant", "min_quantity"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["variant", "min_quantity"],
                name="unique_wholesale_variant_slab",
            ),
            models.CheckConstraint(
                check=Q(wholesale_price_per_unit__gt=0),
                name="check_wholesale_price_gt_zero",
            ),
            models.CheckConstraint(
                check=Q(min_quantity__gte=1),
                name="check_wholesale_min_quantity_gte_one",
            ),
        ]

    def __str__(self):
        return f"{self.variant.sku} - MOQ {self.min_quantity}+ @ ₹{self.wholesale_price_per_unit}"


class ProductImage(TimeStampedModel):
    """
    Product gallery images. Enforces that only one active hero image exists
    per product via PostgreSQL-compatible conditional UniqueConstraint and save hook.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=product_image_upload_path, validators=[validate_image_file])
    alt_text = models.CharField(max_length=200, blank=True, default="")
    is_hero = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
        ordering = ["-is_hero", "sort_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=Q(is_hero=True, is_active=True),
                name="unique_active_hero_image_per_product",
            )
        ]

    def __str__(self):
        hero_tag = " [HERO]" if self.is_hero else ""
        return f"Image for {self.product.name}{hero_tag}"

    def save(self, *args, **kwargs):
        """
        Atomically clear any existing hero image on the product when
        saving a new or updated image with is_hero=True and is_active=True.
        """
        if self.is_hero and self.is_active:
            with transaction.atomic():
                ProductImage.objects.filter(
                    product=self.product, is_hero=True, is_active=True
                ).exclude(pk=self.pk).update(is_hero=False)
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


class ModerationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Moderation"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class ProductReview(TimeStampedModel):
    """
    Product reviews by authenticated customers.
    Ratings range 1-5. Verified purchase status is strictly backend-determined.
    Only reviews with APPROVED status are publicly visible in the catalog.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="product_reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=150)
    review_body = models.TextField()
    verified_purchase = models.BooleanField(default=False)
    moderation_status = models.CharField(
        max_length=20,
        choices=ModerationStatus.choices,
        default=ModerationStatus.PENDING,
        db_index=True,
    )

    class Meta:
        verbose_name = "Product Review"
        verbose_name_plural = "Product Reviews"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "moderation_status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(rating__gte=1) & Q(rating__lte=5),
                name="check_review_rating_1_to_5",
            ),
            models.UniqueConstraint(
                fields=["product", "user"],
                name="unique_review_per_user_product",
            ),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.rating}★ by {self.user.get_full_name()}"


class ReviewImage(TimeStampedModel):
    """
    Optional photo uploads attached to customer reviews.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(ProductReview, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=review_image_upload_path, validators=[validate_image_file])
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Review Image"
        verbose_name_plural = "Review Images"
        ordering = ["sort_order"]

    def __str__(self):
        return f"Review image for {self.review_id}"
