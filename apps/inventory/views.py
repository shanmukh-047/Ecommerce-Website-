from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsManagerOrAdmin, IsStaffOrManager
from apps.catalog.models import ProductVariant
from apps.core.pagination import StandardResultsSetPagination
from apps.inventory.models import StockItem
from apps.inventory.serializers import (
    StockAdjustmentSerializer,
    StockItemSerializer,
    StockRestockSerializer,
)
from apps.inventory.services import InventoryService


class StockItemListView(APIView):
    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def get(self, request, *args, **kwargs):
        stock_items = StockItem.objects.select_related("variant__product").order_by("variant__sku")
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(stock_items, request)
        serializer = StockItemSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class StockItemDetailView(APIView):
    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def get(self, request, pk, *args, **kwargs):
        stock_item = get_object_or_404(StockItem.objects.select_related("variant__product"), pk=pk)
        return Response(StockItemSerializer(stock_item).data)


class StockRestockView(APIView):
    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def post(self, request, *args, **kwargs):
        serializer = StockRestockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            variant = ProductVariant.objects.get(pk=serializer.validated_data["variant_id"])
        except ProductVariant.DoesNotExist:
            raise NotFound("Product variant not found.")

        try:
            stock_item = InventoryService.add_stock(
                variant=variant,
                quantity=serializer.validated_data["quantity"],
                actor=request.user,
                note=serializer.validated_data["note"],
            )
        except DjangoValidationError as exc:
            raise ValidationError({"detail": exc.messages})

        response_data = StockItemSerializer(stock_item).data
        response_data["_message"] = "Stock restocked successfully."
        return Response(response_data, status=status.HTTP_200_OK)


class StockAdjustmentView(APIView):
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def post(self, request, pk, *args, **kwargs):
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            stock_item = InventoryService.adjust_stock(
                stock_item_id=pk,
                quantity_delta=serializer.validated_data["quantity_delta"],
                actor=request.user,
                note=serializer.validated_data["note"],
            )
        except StockItem.DoesNotExist:
            raise NotFound("Stock item not found.")
        except DjangoValidationError as exc:
            raise ValidationError({"detail": exc.messages})

        response_data = StockItemSerializer(stock_item).data
        response_data["_message"] = "Stock adjusted successfully."
        return Response(response_data, status=status.HTTP_200_OK)
