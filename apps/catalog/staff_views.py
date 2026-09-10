import uuid
from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStaffOrManager
from apps.catalog.models import Category, Product, ProductImage, ProductVariant
from apps.catalog.serializers import (
    CategorySummarySerializer,
    StaffProductCreateUpdateSerializer,
    StaffProductSerializer,
)
from apps.core.pagination import StandardResultsSetPagination
from apps.inventory.models import StockItem


class StaffProductListView(APIView):
    """
    GET: List all products for staff/admin with search and filtering.
    POST: Create a new product with initial variant and inventory stock.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def get(self, request):
        queryset = (
            Product.objects.select_related("category")
            .prefetch_related("variants__stock_item", "images")
            .order_by("-created_at")
        )

        category_param = request.query_params.get("category")
        if category_param:
            queryset = queryset.filter(
                Q(category__slug=category_param) | Q(category__id=category_param)
            )

        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(slug__icontains=search)
                | Q(variants__sku__icontains=search)
            ).distinct()

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = StaffProductSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = StaffProductCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        variant_name = data.pop("variant_name", "Standard Pack")
        sku = data.pop("sku", None)
        weight_in_grams = data.pop("weight_in_grams", 100)
        mrp = data.pop("mrp", Decimal("100.00"))
        selling_price = data.pop("selling_price", Decimal("90.00"))
        initial_stock = data.pop("initial_stock", 50)

        # Auto-generate slug if not provided
        if not data.get("slug"):
            base_slug = slugify(data["name"])
            candidate_slug = base_slug
            idx = 1
            while Product.objects.filter(slug=candidate_slug).exists():
                candidate_slug = f"{base_slug}-{idx}"
                idx += 1
            data["slug"] = candidate_slug

        with transaction.atomic():
            product = Product.objects.create(**data)

            # Generate SKU if not provided
            if not sku:
                sku = f"{product.slug[:4].upper()}-{weight_in_grams}G-{uuid.uuid4().hex[:4].upper()}"

            variant = ProductVariant.objects.create(
                product=product,
                variant_name=variant_name,
                sku=sku,
                weight_in_grams=weight_in_grams,
                mrp=mrp,
                selling_price=selling_price,
                is_most_chosen=True,
            )

            StockItem.objects.create(
                variant=variant,
                quantity_on_hand=initial_stock,
                reorder_level=10,
            )

        return Response(
            {
                "product": StaffProductSerializer(product, context={"request": request}).data,
                "_message": f"Product '{product.name}' created successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


class StaffProductDetailView(APIView):
    """
    GET: Retrieve full product configuration for administration.
    PATCH: Update product metadata, pricing, or visibility flags.
    DELETE: Remove or archive product.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def get(self, request, pk):
        product = get_object_or_404(
            Product.objects.select_related("category").prefetch_related(
                "variants__stock_item", "images"
            ),
            pk=pk,
        )
        return Response(
            {
                "product": StaffProductSerializer(product, context={"request": request}).data,
                "_message": "Product retrieved successfully.",
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request, pk):
        product = get_object_or_404(Product, pk=pk)

        # Allowed product-level update fields
        updatable_fields = [
            "name",
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
        ]

        for field in updatable_fields:
            if field in request.data:
                val = request.data[field]
                if field == "category" and isinstance(val, (str, int, uuid.UUID)):
                    val = get_object_or_404(Category, pk=val)
                setattr(product, field, val)

        product.save()

        # Update primary variant if price/stock provided in payload
        if "selling_price" in request.data or "mrp" in request.data or "stock" in request.data:
            primary_var = product.variants.first()
            if primary_var:
                if "selling_price" in request.data:
                    primary_var.selling_price = Decimal(str(request.data["selling_price"]))
                if "mrp" in request.data:
                    primary_var.mrp = Decimal(str(request.data["mrp"]))
                primary_var.save()

                if "stock" in request.data:
                    stock_item, _ = StockItem.objects.get_or_create(variant=primary_var)
                    stock_item.quantity_on_hand = max(0, int(request.data["stock"]))
                    stock_item.save(update_fields=["quantity_on_hand", "updated_at"])

        return Response(
            {
                "product": StaffProductSerializer(product, context={"request": request}).data,
                "_message": f"Product '{product.name}' updated successfully.",
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        name = product.name
        # Delete related images and variants or soft-disable
        product.delete()
        return Response(
            {"_message": f"Product '{name}' deleted successfully."},
            status=status.HTTP_200_OK,
        )


class StaffProductImageUploadView(APIView):
    """
    POST: Upload an image file for a product.
    Supports multipart form data with image file, is_hero flag, alt_text.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        image_file = request.FILES.get("image")
        if not image_file:
            return Response(
                {"error": "No image file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_hero = request.data.get("is_hero", "").lower() in ["true", "1"]
        alt_text = request.data.get("alt_text", product.name)

        if is_hero:
            # Clear existing hero flag for this product
            product.images.filter(is_hero=True).update(is_hero=False)

        product_image = ProductImage.objects.create(
            product=product,
            image=image_file,
            alt_text=alt_text,
            is_hero=is_hero,
        )

        return Response(
            {
                "image": {
                    "id": str(product_image.id),
                    "url": request.build_absolute_uri(product_image.image.url),
                    "is_hero": product_image.is_hero,
                    "alt_text": product_image.alt_text,
                },
                "_message": "Product image uploaded successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


class StaffCategoryListView(APIView):
    """
    GET: List all categories for administrative dropdowns.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def get(self, request):
        categories = Category.objects.all().order_by("sort_order", "name")
        return Response(
            {"categories": CategorySummarySerializer(categories, many=True).data},
            status=status.HTTP_200_OK,
        )
