from django.contrib import admin

from .models import (
    Category,
    ModerationStatus,
    Product,
    ProductImage,
    ProductReview,
    ProductVariant,
    ReviewImage,
    WholesaleTierPricing,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent", "sort_order", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["sort_order", "name"]


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = [
        "variant_name",
        "sku",
        "weight_in_grams",
        "mrp",
        "selling_price",
        "is_most_chosen",
        "sort_order",
        "is_active",
    ]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ["image", "alt_text", "is_hero", "sort_order", "is_active"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category",
        "tier",
        "form",
        "origin_region",
        "is_bestseller",
        "is_featured_from_home",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "tier",
        "form",
        "is_active",
        "is_bestseller",
        "is_featured_from_home",
        "category",
    ]
    search_fields = ["name", "slug", "origin_region", "hsn_code"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductVariantInline, ProductImageInline]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "name",
                    "slug",
                    "category",
                    "tier",
                    "form",
                    "is_active",
                )
            },
        ),
        (
            "Merchandising",
            {
                "fields": (
                    "is_bestseller",
                    "is_featured_from_home",
                )
            },
        ),
        (
            "Provenance & Terroir Storytelling",
            {
                "fields": (
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
                )
            },
        ),
        (
            "Statutory Legal Metrology & Tax",
            {
                "fields": (
                    "fssai_license",
                    "hsn_code",
                    "gst_rate",
                    "packer_name",
                    "packer_address",
                    "best_before_guidance",
                )
            },
        ),
    )


class WholesaleTierPricingInline(admin.TabularInline):
    model = WholesaleTierPricing
    extra = 1
    fields = ["min_quantity", "wholesale_price_per_unit", "is_active"]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = [
        "sku",
        "product",
        "variant_name",
        "mrp",
        "selling_price",
        "is_most_chosen",
        "is_active",
    ]
    list_filter = ["is_active", "is_most_chosen"]
    search_fields = ["sku", "variant_name", "product__name"]
    inlines = [WholesaleTierPricingInline]


class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 0
    fields = ["image", "sort_order"]


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "user",
        "rating",
        "title",
        "verified_purchase",
        "moderation_status",
        "created_at",
    ]
    list_filter = ["moderation_status", "rating", "verified_purchase"]
    search_fields = ["product__name", "user__email", "title", "review_body"]
    readonly_fields = ["verified_purchase", "created_at", "updated_at"]
    inlines = [ReviewImageInline]
    actions = ["approve_reviews", "reject_reviews"]

    @admin.action(description="Approve selected reviews for public catalog display")
    def approve_reviews(self, request, queryset):
        updated_count = queryset.update(moderation_status=ModerationStatus.APPROVED)
        self.message_user(request, f"{updated_count} review(s) successfully marked as APPROVED.")

    @admin.action(description="Reject selected reviews")
    def reject_reviews(self, request, queryset):
        updated_count = queryset.update(moderation_status=ModerationStatus.REJECTED)
        self.message_user(request, f"{updated_count} review(s) marked as REJECTED.")
