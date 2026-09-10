import logging
from typing import Optional

from django.db.models import Max, Min, Prefetch, Q, QuerySet

from apps.catalog.models import (
    Category,
    ModerationStatus,
    Product,
    ProductImage,
    ProductReview,
    ProductVariant,
    WholesaleTierPricing,
)

logger = logging.getLogger(__name__)


class CatalogService:
    """
    Core domain service providing optimized database queries, filtering,
    sorting, and secure prefetching for product catalog listings and details.
    """

    @staticmethod
    def get_base_product_queryset(user=None) -> QuerySet[Product]:
        """
        Builds an optimized, anti-N+1 queryset with select_related on category
        and conditional prefetching on wholesale tier pricing based on user authorization.
        """
        is_wholesale = (
            user is not None
            and getattr(user, "is_authenticated", False)
            and getattr(user, "is_wholesale_buyer", False)
        )

        variant_prefetches = [
            Prefetch(
                "variants",
                queryset=ProductVariant.objects.filter(is_active=True).order_by(
                    "sort_order", "selling_price"
                ),
            ),
            Prefetch(
                "images",
                queryset=ProductImage.objects.filter(is_active=True).order_by(
                    "-is_hero", "sort_order"
                ),
            ),
        ]

        if is_wholesale:
            variant_prefetches.append(
                Prefetch(
                    "variants__wholesale_slabs",
                    queryset=WholesaleTierPricing.objects.filter(is_active=True).order_by(
                        "min_quantity"
                    ),
                )
            )

        return (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related(*variant_prefetches)
        )

    @classmethod
    def filter_and_order_products(
        cls,
        user=None,
        category_slug: Optional[str] = None,
        tier: Optional[str] = None,
        form: Optional[str] = None,
        origin: Optional[str] = None,
        featured: Optional[str] = None,
        bestseller: Optional[str] = None,
        search_query: Optional[str] = None,
        ordering: Optional[str] = None,
    ) -> QuerySet[Product]:
        """
        Applies verified filters, search, and sorting criteria to the catalog queryset.
        """
        qs = cls.get_base_product_queryset(user=user)

        # 1. Category filter (matches direct category or children subcategories)
        if category_slug:
            try:
                target_category = Category.objects.get(slug=category_slug, is_active=True)
                descendant_ids = list(
                    Category.objects.filter(
                        Q(id=target_category.id) | Q(parent_id=target_category.id),
                        is_active=True,
                    ).values_list("id", flat=True)
                )
                qs = qs.filter(category_id__in=descendant_ids)
            except Category.DoesNotExist:
                qs = qs.filter(category__slug=category_slug)

        # 2. Tier filter (RESERVE vs EVERYDAY)
        if tier:
            qs = qs.filter(tier__iexact=tier.strip())

        # 3. Form filter (WHOLE, GROUND, BLEND, RAW)
        if form:
            qs = qs.filter(form__iexact=form.strip())

        # 4. Provenance / Origin filter
        if origin:
            qs = qs.filter(origin_region__icontains=origin.strip())

        # 5. Merchandising Flags
        if featured is not None:
            is_feat = str(featured).lower() in {"true", "1", "yes"}
            if is_feat:
                qs = qs.filter(is_featured_from_home=True)

        if bestseller is not None:
            is_best = str(bestseller).lower() in {"true", "1", "yes"}
            if is_best:
                qs = qs.filter(is_bestseller=True)

        # 6. Full-text / Substring Search
        if search_query:
            query = search_query.strip()
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(short_description__icontains=query)
                | Q(detailed_description__icontains=query)
                | Q(origin_region__icontains=query)
                | Q(origin_stamp__icontains=query)
            )

        # 7. Safe Ordering (Newest, Price asc, Price desc)
        if ordering == "price_low_to_high":
            qs = qs.annotate(
                min_variant_price=Min("variants__selling_price", filter=Q(variants__is_active=True))
            ).order_by("min_variant_price", "-created_at")
        elif ordering == "price_high_to_low":
            qs = qs.annotate(
                max_variant_price=Max("variants__selling_price", filter=Q(variants__is_active=True))
            ).order_by("-max_variant_price", "-created_at")
        else:
            # Default to newest first
            qs = qs.order_by("-created_at")

        return qs

    @classmethod
    def get_product_by_slug(cls, slug: str, user=None) -> Product:
        """
        Retrieves a single active product by slug with all required eager-loaded relations,
        including approved customer reviews and conditional wholesale pricing.
        """
        qs = cls.get_base_product_queryset(user=user)
        reviews_prefetch = Prefetch(
            "reviews",
            queryset=ProductReview.objects.filter(moderation_status=ModerationStatus.APPROVED)
            .select_related("user")
            .prefetch_related("images")
            .order_by("-created_at"),
        )
        return qs.prefetch_related(reviews_prefetch).get(slug=slug, is_active=True)
