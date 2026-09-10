import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStaffOrManager
from apps.catalog.models import Category, ModerationStatus, Product, ProductReview
from apps.catalog.serializers import (
    CategorySerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductReviewSerializer,
    ReviewModerationSerializer,
)
from apps.catalog.services import CatalogService, ReviewService
from apps.core.pagination import StandardResultsSetPagination

logger = logging.getLogger(__name__)


class CategoryListView(APIView):
    """
    Public listing of active categories and subcategories
    organized by display sort order.
    """

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        categories = (
            Category.objects.filter(parent__isnull=True, is_active=True)
            .prefetch_related("subcategories")
            .order_by("sort_order", "name")
        )
        serializer = CategorySerializer(categories, many=True, context={"request": request})
        return Response(serializer.data)


class CategoryDetailView(APIView):
    """
    Public retrieval of category details and its direct children by slug.
    """

    permission_classes = [AllowAny]

    def get(self, request, slug, *args, **kwargs):
        try:
            category = Category.objects.filter(is_active=True).get(slug=slug)
        except Category.DoesNotExist:
            raise NotFound("Category not found.")

        serializer = CategorySerializer(category, context={"request": request})
        return Response(serializer.data)


class ProductListView(APIView):
    """
    Public product catalog listing endpoint.
    Supports filtering by category, tier, form, origin, featured flag, bestseller flag,
    full-text substring search, and price/recency ordering.
    """

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        category_slug = request.query_params.get("category")
        tier = request.query_params.get("tier")
        form = request.query_params.get("form")
        origin = request.query_params.get("origin")
        featured = request.query_params.get("featured")
        bestseller = request.query_params.get("bestseller")
        search_query = request.query_params.get("search")
        ordering = request.query_params.get("ordering")

        products = CatalogService.filter_and_order_products(
            user=request.user,
            category_slug=category_slug,
            tier=tier,
            form=form,
            origin=origin,
            featured=featured,
            bestseller=bestseller,
            search_query=search_query,
            ordering=ordering,
        )

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(products, request)
        serializer = ProductListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class ProductDetailView(APIView):
    """
    Public product detail view retrieving complete information by slug.
    Exposes pack-size variants, legal metrology, terroir notes,
    and login-gated wholesale slab pricing for approved B2B buyers.
    """

    permission_classes = [AllowAny]

    def get(self, request, slug, *args, **kwargs):
        try:
            product = CatalogService.get_product_by_slug(slug, user=request.user)
        except Product.DoesNotExist:
            raise NotFound("Product not found.")

        serializer = ProductDetailSerializer(product, context={"request": request})
        return Response(serializer.data)


class ProductReviewListCreateView(APIView):
    """
    Product reviews endpoint:
    - GET: Public list of approved reviews for the given product slug (paginated).
    - POST: Authenticated review submission (auto-queued for administrative moderation).
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request, slug, *args, **kwargs):
        try:
            product = Product.objects.get(slug=slug, is_active=True)
        except Product.DoesNotExist:
            raise NotFound("Product not found.")

        reviews = (
            ProductReview.objects.filter(
                product=product, moderation_status=ModerationStatus.APPROVED
            )
            .select_related("user")
            .prefetch_related("images")
            .order_by("-created_at")
        )

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(reviews, request)
        serializer = ProductReviewSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, slug, *args, **kwargs):
        try:
            product = Product.objects.get(slug=slug, is_active=True)
        except Product.DoesNotExist:
            raise NotFound("Product not found.")

        raw_rating = request.data.get("rating")
        title = request.data.get("title", "")
        review_body = request.data.get("review_body", "")

        if raw_rating is None:
            raise ValidationError({"rating": ["Rating is required."]})

        try:
            rating = int(raw_rating)
        except (ValueError, TypeError):
            raise ValidationError({"rating": ["Rating must be an integer between 1 and 5."]})

        if not title or not str(title).strip():
            raise ValidationError({"title": ["Review title cannot be empty."]})

        if not review_body or not str(review_body).strip():
            raise ValidationError({"review_body": ["Review body cannot be empty."]})

        uploaded_images = request.FILES.getlist("images") if request.FILES else []

        try:
            review = ReviewService.create_review(
                user=request.user,
                product=product,
                rating=rating,
                title=title,
                review_body=review_body,
                images=uploaded_images,
            )
        except DjangoValidationError as e:
            raise ValidationError({"detail": e.messages if hasattr(e, "messages") else str(e)})

        serializer = ProductReviewSerializer(review, context={"request": request})
        response_data = serializer.data
        response_data["_message"] = (
            "Review submitted successfully and is pending administrative moderation."
        )
        return Response(response_data, status=status.HTTP_201_CREATED)


class StaffReviewModerationView(APIView):
    """
    Staff / Operations Manager review moderation endpoint.
    Allows approving or rejecting customer-submitted product reviews.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def post(self, request, pk, *args, **kwargs):
        try:
            review = ProductReview.objects.select_related("product", "user").get(pk=pk)
        except ProductReview.DoesNotExist:
            raise NotFound("Review not found.")

        serializer = ReviewModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        try:
            moderated_review = ReviewService.moderate_review(
                review=review, action=action, staff_user=request.user
            )
        except DjangoValidationError as e:
            raise ValidationError({"detail": str(e)})

        return Response(
            {
                "id": str(moderated_review.id),
                "product_slug": moderated_review.product.slug,
                "moderation_status": moderated_review.moderation_status,
                "_message": f"Review {moderated_review.moderation_status.lower()} successfully.",
            },
            status=status.HTTP_200_OK,
        )
