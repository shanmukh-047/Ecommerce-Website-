from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from PIL import Image

from apps.accounts.models import User
from apps.catalog.models import (
    Category,
    Form,
    ModerationStatus,
    Product,
    ProductImage,
    ProductReview,
    ProductVariant,
    Tier,
    WholesaleTierPricing,
)


def create_dummy_image(name="test.jpg", color="green", format="JPEG"):
    """Helper creating an in-memory valid image file for testing."""
    file_obj = BytesIO()
    image = Image.new("RGB", (100, 100), color=color)
    image.save(file_obj, format=format)
    file_obj.seek(0)
    return SimpleUploadedFile(name, file_obj.read(), content_type=f"image/{format.lower()}")


class CatalogModelTests(TestCase):
    """Tests verifying catalog models, constraints, and business logic methods."""

    def setUp(self):
        self.root_category = Category.objects.create(
            name="Spices & Seasonings",
            slug="spices-and-seasonings",
            description="Pure Malenadu spices",
            sort_order=1,
        )
        self.sub_category = Category.objects.create(
            name="Signature Blends",
            slug="signature-blends",
            parent=self.root_category,
            sort_order=2,
        )
        self.product = Product.objects.create(
            category=self.sub_category,
            name="Malenadu Saaru Pudi",
            slug="malenadu-saaru-pudi",
            tier=Tier.RESERVE,
            form=Form.BLEND,
            short_description="Traditional Malenadu aromatic rasam blend.",
            detailed_description="Slow roasted in cold-pressed coconut oil with heirloom spices.",
            origin_region="Sirsi, Uttara Kannada, Karnataka",
            plantation_provenance="Estate heritage batch",
            origin_stamp="Grown in Malenadu · Uttara Kannada",
            grade="Aromatic First Grade",
            hsn_code="0910",
            gst_rate=Decimal("5.00"),
            sharada_note="Use a small pinch while boiling dal for pure Malenadu comfort.",
            is_bestseller=True,
            is_featured_from_home=True,
        )
        self.user = User.objects.create_user(
            email="shopper@bharathmasala.com",
            phone_number="+919876543210",
            password="SecurePassword123!",
            first_name="Ramesh",
            last_name="Kamat",
        )

    def test_category_hierarchy_and_string(self):
        """Verify category parent-child representation."""
        self.assertEqual(str(self.root_category), "Spices & Seasonings")
        self.assertEqual(str(self.sub_category), "Spices & Seasonings > Signature Blends")
        self.assertIn(self.sub_category, self.root_category.subcategories.all())

    def test_product_str(self):
        """Verify product string representation."""
        self.assertEqual(str(self.product), "Malenadu Saaru Pudi (Reserve Tier)")

    def test_variant_creation_and_savings_calculation(self):
        """Verify variant pricing, savings amounts, and percentage labels."""
        variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="250g Glass Jar",
            sku="BMP-SRP-250G",
            weight_in_grams=250,
            mrp=Decimal("300.00"),
            selling_price=Decimal("240.00"),
            is_most_chosen=True,
        )
        self.assertEqual(variant.savings_amount, Decimal("60.00"))
        self.assertEqual(variant.discount_percentage, 20)
        self.assertEqual(variant.savings_label, "Save ₹60 (20% OFF)")
        self.assertIn("BMP-SRP-250G", str(variant))

    def test_variant_check_constraint_selling_price_lte_mrp(self):
        """Ensure selling_price cannot exceed MRP at database level."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductVariant.objects.create(
                    product=self.product,
                    variant_name="500g Pack",
                    sku="BMP-SRP-500G",
                    weight_in_grams=500,
                    mrp=Decimal("200.00"),
                    selling_price=Decimal("250.00"),  # Invalid: selling_price > mrp
                )

    def test_variant_check_constraint_positive_prices(self):
        """Ensure variant prices must be strictly greater than 0."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductVariant.objects.create(
                    product=self.product,
                    variant_name="100g Pack",
                    sku="BMP-SRP-100G",
                    mrp=Decimal("0.00"),
                    selling_price=Decimal("0.00"),
                )

    def test_wholesale_tier_pricing_uniqueness_and_positive_checks(self):
        """Verify wholesale slab MOQ uniqueness per variant and positive pricing."""
        variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="1kg Pack",
            sku="BMP-SRP-1KG",
            weight_in_grams=1000,
            mrp=Decimal("1000.00"),
            selling_price=Decimal("800.00"),
        )
        slab1 = WholesaleTierPricing.objects.create(
            variant=variant,
            min_quantity=10,
            wholesale_price_per_unit=Decimal("700.00"),
        )
        self.assertEqual(str(slab1), "BMP-SRP-1KG - MOQ 10+ @ ₹700.00")

        # Duplicate slab with same min_quantity for same variant must raise IntegrityError
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WholesaleTierPricing.objects.create(
                    variant=variant,
                    min_quantity=10,
                    wholesale_price_per_unit=Decimal("680.00"),
                )

    def test_hero_image_single_active_constraint_and_save_hook(self):
        """
        Verify that marking a new image as hero automatically clears prior hero
        flags on the same product, while unique constraint prevents duplicates.
        """
        img1 = ProductImage.objects.create(
            product=self.product,
            image=create_dummy_image("hero1.jpg"),
            alt_text="Hero Image 1",
            is_hero=True,
            is_active=True,
        )
        self.assertTrue(img1.is_hero)

        # Create a second hero image: save() hook should clear img1's is_hero flag
        img2 = ProductImage.objects.create(
            product=self.product,
            image=create_dummy_image("hero2.jpg"),
            alt_text="Hero Image 2",
            is_hero=True,
            is_active=True,
        )

        img1.refresh_from_db()
        img2.refresh_from_db()
        self.assertFalse(img1.is_hero)
        self.assertTrue(img2.is_hero)

    def test_product_review_validation_and_uniqueness(self):
        """Verify rating bounds and unique review per user per product constraint."""
        review = ProductReview.objects.create(
            product=self.product,
            user=self.user,
            rating=5,
            title="Authentic Malenadu taste!",
            review_body="The roasted aroma took me straight back to my grandmother's kitchen.",
            moderation_status=ModerationStatus.APPROVED,
        )
        self.assertEqual(review.moderation_status, ModerationStatus.APPROVED)
        self.assertIn("Ramesh Kamat", str(review))

        # Duplicate review from same user for same product must fail constraint
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductReview.objects.create(
                    product=self.product,
                    user=self.user,
                    rating=4,
                    title="Another review",
                    review_body="Should be blocked by database constraint.",
                )
