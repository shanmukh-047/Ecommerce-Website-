from rest_framework import serializers

from apps.catalog.models import (
    Category,
    Product,
    ProductImage,
    ProductReview,
    ProductVariant,
    ReviewImage,
    WholesaleTierPricing,
)


class CategorySummarySerializer(serializers.ModelSerializer):
    """Concise representation of category for embedded product views without recursive subcategories."""

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "image", "sort_order"]


class SubcategorySerializer(serializers.ModelSerializer):
    """Concise representation of nested subcategories."""

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "image", "sort_order"]


class CategorySerializer(serializers.ModelSerializer):
    """
    Category hierarchy serializer providing active subcategories
    for structured navigation and collection browsing.
    """

    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "image",
            "sort_order",
            "parent",
            "subcategories",
        ]

    def get_subcategories(self, obj):
        # Return direct active children
        children = obj.subcategories.filter(is_active=True).order_by("sort_order", "name")
        return SubcategorySerializer(children, many=True).data


class WholesaleTierPricingSerializer(serializers.ModelSerializer):
    """
    Wholesale slab pricing serializer.
    STRICT SECURITY RULE: Only exposed to approved wholesale customers.
    """

    class Meta:
        model = WholesaleTierPricing
        fields = [
            "id",
            "min_quantity",
            "wholesale_price_per_unit",
        ]


class ProductVariantSerializer(serializers.ModelSerializer):
    """
    Pack size variant serializer with automated MRP discount math,
    and login-gated wholesale slab pricing.
    """

    savings_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    savings_label = serializers.CharField(read_only=True)
    wholesale_slabs = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "variant_name",
            "sku",
            "weight_in_grams",
            "mrp",
            "selling_price",
            "savings_amount",
            "discount_percentage",
            "savings_label",
            "is_most_chosen",
            "sort_order",
            "wholesale_slabs",
        ]

    def get_wholesale_slabs(self, obj):
        """
        Conditionally include wholesale slab pricing ONLY if the requesting
        user is authenticated and has an approved wholesale account.
        """
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if (
            user
            and getattr(user, "is_authenticated", False)
            and getattr(user, "is_wholesale_buyer", False)
        ):
            # Safe access to prefetched wholesale_slabs
            slabs = [slab for slab in obj.wholesale_slabs.all() if slab.is_active]
            return WholesaleTierPricingSerializer(slabs, many=True).data
        return None

    def to_representation(self, instance):
        """
        Completely remove wholesale_slabs key from response for non-wholesale users
        to prevent any inadvertent commercial data leak.
        """
        data = super().to_representation(instance)
        if data.get("wholesale_slabs") is None:
            data.pop("wholesale_slabs", None)
        return data


class ProductImageSerializer(serializers.ModelSerializer):
    """Product gallery image serializer."""

    class Meta:
        model = ProductImage
        fields = [
            "id",
            "image",
            "alt_text",
            "is_hero",
            "sort_order",
        ]


class ReviewImageSerializer(serializers.ModelSerializer):
    """Customer review photo serializer."""

    class Meta:
        model = ReviewImage
        fields = ["id", "image", "sort_order"]


class ProductReviewSerializer(serializers.ModelSerializer):
    """
    Customer review serializer with PII masking of reviewer names
    and strict read-only enforcement of verified_purchase and moderation_status.
    """

    reviewer_name = serializers.SerializerMethodField()
    images = ReviewImageSerializer(many=True, read_only=True)
    verified_purchase = serializers.BooleanField(read_only=True)
    moderation_status = serializers.CharField(read_only=True)

    class Meta:
        model = ProductReview
        fields = [
            "id",
            "rating",
            "title",
            "review_body",
            "reviewer_name",
            "verified_purchase",
            "moderation_status",
            "images",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "reviewer_name",
            "verified_purchase",
            "moderation_status",
            "created_at",
        ]

    def get_reviewer_name(self, obj) -> str:
        """
        Mask user name to 'Firstname L.' (e.g. 'Ramesh K.') to preserve PII privacy.
        """
        user = obj.user
        if not user:
            return "Verified Customer"
        first = user.first_name.strip().title() if user.first_name else ""
        last = user.last_name.strip() if user.last_name else ""
        if first and last:
            return f"{first} {last[0].upper()}."
        if first:
            return first
        return "Customer"

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5 stars.")
        return value


class ProductListSerializer(serializers.ModelSerializer):
    """
    Concise product serializer optimized for grid views, catalog search,
    and category listings with price bounds and hero image.
    """

    category = serializers.SerializerMethodField()
    hero_image = serializers.SerializerMethodField()
    starting_price = serializers.SerializerMethodField()
    starting_price_label = serializers.SerializerMethodField()
    variant_count = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "category",
            "tier",
            "form",
            "short_description",
            "origin_region",
            "origin_stamp",
            "grade",
            "is_bestseller",
            "is_featured_from_home",
            "hero_image",
            "starting_price",
            "starting_price_label",
            "variant_count",
            "variants",
            "created_at",
        ]

    def get_category(self, obj):
        return {
            "id": str(obj.category_id),
            "name": obj.category.name,
            "slug": obj.category.slug,
        }

    def get_hero_image(self, obj):
        request = self.context.get("request")
        active_images = [img for img in obj.images.all() if img.is_active]
        hero = next((img for img in active_images if img.is_hero), None)
        if not hero and active_images:
            hero = active_images[0]
        if hero and hero.image:
            return request.build_absolute_uri(hero.image.url) if request else hero.image.url
        return None

    def get_starting_price(self, obj):
        active_variants = [v for v in obj.variants.all() if v.is_active]
        if active_variants:
            min_price = min(v.selling_price for v in active_variants)
            return str(min_price)
        return None

    def get_starting_price_label(self, obj):
        sp = self.get_starting_price(obj)
        return f"From ₹{sp}" if sp else ""

    def get_variant_count(self, obj):
        return len([v for v in obj.variants.all() if v.is_active])

    def get_variants(self, obj):
        active_variants = [v for v in obj.variants.all() if v.is_active]
        return ProductVariantSerializer(active_variants, many=True, context=self.context).data


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive product detail serializer including provenance,
    Sharada's audio folklore story link, Indian Legal Metrology block,
    gallery images, active pack-size variants, and approved customer reviews.
    """

    category = CategorySummarySerializer(read_only=True)
    hero_image = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    variants = serializers.SerializerMethodField()
    legal_metrology = serializers.SerializerMethodField()
    reviews_summary = serializers.SerializerMethodField()
    recent_reviews = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "category",
            "tier",
            "form",
            "short_description",
            "detailed_description",
            "origin_region",
            "plantation_provenance",
            "origin_stamp",
            "grade",
            "harvest_date",
            "grinding_date",
            "sharada_note",
            "qr_audio_url",
            "legal_metrology",
            "is_bestseller",
            "is_featured_from_home",
            "hero_image",
            "images",
            "variants",
            "reviews_summary",
            "recent_reviews",
            "created_at",
            "updated_at",
        ]

    def get_hero_image(self, obj):
        request = self.context.get("request")
        active_images = [img for img in obj.images.all() if img.is_active]
        hero = next((img for img in active_images if img.is_hero), None)
        if not hero and active_images:
            hero = active_images[0]
        if hero and hero.image:
            return request.build_absolute_uri(hero.image.url) if request else hero.image.url
        return None

    def get_variants(self, obj):
        active_variants = [v for v in obj.variants.all() if v.is_active]
        return ProductVariantSerializer(active_variants, many=True, context=self.context).data

    def get_legal_metrology(self, obj):
        return {
            "fssai_license": obj.fssai_license,
            "hsn_code": obj.hsn_code,
            "gst_rate": str(obj.gst_rate),
            "packer_name": obj.packer_name,
            "packer_address": obj.packer_address,
            "best_before_guidance": obj.best_before_guidance,
        }

    def get_reviews_summary(self, obj):
        approved_reviews = [r for r in obj.reviews.all() if r.moderation_status == "APPROVED"]
        count = len(approved_reviews)
        if count > 0:
            avg = sum(r.rating for r in approved_reviews) / count
            return {
                "total_reviews": count,
                "average_rating": round(float(avg), 1),
            }
        return {
            "total_reviews": 0,
            "average_rating": 0.0,
        }

    def get_recent_reviews(self, obj):
        approved_reviews = [r for r in obj.reviews.all() if r.moderation_status == "APPROVED"][:5]
        return ProductReviewSerializer(approved_reviews, many=True, context=self.context).data


class ReviewModerationSerializer(serializers.Serializer):
    """Staff action serializer for approving or rejecting customer reviews."""

    action = serializers.ChoiceField(choices=["APPROVE", "REJECT"])


class StaffVariantSerializer(serializers.ModelSerializer):
    quantity_on_hand = serializers.SerializerMethodField()
    quantity_reserved = serializers.SerializerMethodField()
    quantity_available = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "variant_name",
            "sku",
            "weight_in_grams",
            "mrp",
            "selling_price",
            "is_most_chosen",
            "sort_order",
            "is_active",
            "quantity_on_hand",
            "quantity_reserved",
            "quantity_available",
        ]

    def get_quantity_on_hand(self, obj):
        stock = getattr(obj, "stock_item", None)
        return stock.quantity_on_hand if stock else 0

    def get_quantity_reserved(self, obj):
        stock = getattr(obj, "stock_item", None)
        return stock.quantity_reserved if stock else 0

    def get_quantity_available(self, obj):
        stock = getattr(obj, "stock_item", None)
        return stock.quantity_available if stock else 0


class StaffProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    variants = StaffVariantSerializer(many=True, read_only=True)
    images = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "category",
            "category_name",
            "tier",
            "form",
            "short_description",
            "detailed_description",
            "origin_region",
            "origin_stamp",
            "grade",
            "fssai_license",
            "hsn_code",
            "gst_rate",
            "is_bestseller",
            "is_featured_from_home",
            "images",
            "variants",
            "created_at",
            "updated_at",
        ]

    def get_images(self, obj):
        request = self.context.get("request")
        return [
            {
                "id": str(img.id),
                "url": request.build_absolute_uri(img.image.url) if request else img.image.url,
                "is_hero": img.is_hero,
                "alt_text": img.alt_text,
            }
            for img in obj.images.all()
            if img.image
        ]


class StaffProductCreateUpdateSerializer(serializers.ModelSerializer):
    variant_name = serializers.CharField(max_length=100, required=False, default="Standard Pack")
    sku = serializers.CharField(max_length=64, required=False, allow_blank=True)
    weight_in_grams = serializers.IntegerField(min_value=1, required=False, default=100)
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=100)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=90)
    initial_stock = serializers.IntegerField(min_value=0, required=False, default=50)
    hsn_code = serializers.CharField(max_length=10, required=False, default="0910")
    slug = serializers.SlugField(max_length=220, required=False, allow_blank=True)

    class Meta:
        model = Product
        fields = [
            "name",
            "slug",
            "category",
            "tier",
            "form",
            "short_description",
            "detailed_description",
            "origin_region",
            "origin_stamp",
            "grade",
            "fssai_license",
            "hsn_code",
            "gst_rate",
            "is_bestseller",
            "is_featured_from_home",
            "variant_name",
            "sku",
            "weight_in_grams",
            "mrp",
            "selling_price",
            "initial_stock",
        ]

