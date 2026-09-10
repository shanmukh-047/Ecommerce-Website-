from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStaffOrManager
from apps.core.pagination import StandardResultsSetPagination
from apps.inventory.models import StockItem
from apps.inventory.serializers import StockItemSerializer, StockItemStaffUpdateSerializer
from apps.inventory.services.inventory_service import InventoryService


class StaffInventoryListView(APIView):
    """
    GET: List all inventory stock items with search and low-stock filter.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def get(self, request):
        queryset = (
            StockItem.objects.select_related("variant__product", "variant")
            .order_by("variant__product__name", "variant__sort_order")
        )

        low_stock = request.query_params.get("low_stock")
        if low_stock and low_stock.lower() in ["true", "1"]:
            # Available stock <= reorder_level
            queryset = queryset.filter(quantity_on_hand__lte=F("quantity_reserved") + F("reorder_level"))

        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(variant__sku__icontains=search)
                | Q(variant__product__name__icontains=search)
                | Q(variant__variant_name__icontains=search)
            )

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = StockItemSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class StaffInventoryUpdateView(APIView):
    """
    GET: Retrieve inventory stock details for a specific StockItem or Variant.
    PATCH/POST: Update quantity_on_hand or reorder_level for a specific StockItem or Variant.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def get_stock_item(self, pk):
        try:
            return StockItem.objects.select_related("variant__product", "variant").get(pk=pk)
        except StockItem.DoesNotExist:
            return get_object_or_404(
                StockItem.objects.select_related("variant__product", "variant"), variant_id=pk
            )

    def get(self, request, pk):
        stock_item = self.get_stock_item(pk)
        return Response(
            {
                "stock_item": StockItemSerializer(stock_item).data,
                "_message": f"Inventory details for {stock_item.variant.sku} retrieved successfully.",
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request, pk):
        stock_item = self.get_stock_item(pk)
        serializer = StockItemStaffUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qty = serializer.validated_data.get("quantity_on_hand")
        reorder = serializer.validated_data.get("reorder_level")
        note = serializer.validated_data.get("note", "Manual admin inventory update")

        if qty is not None:
            delta = qty - stock_item.quantity_on_hand
            if delta != 0:
                stock_item = InventoryService.adjust_stock(
                    stock_item_id=stock_item.id,
                    quantity_delta=delta,
                    actor=request.user,
                    note=note,
                )

        if reorder is not None:
            stock_item.reorder_level = reorder
            stock_item.save(update_fields=["reorder_level", "updated_at"])

        return Response(
            {
                "stock_item": StockItemSerializer(stock_item).data,
                "_message": f"Inventory for {stock_item.variant.sku} updated successfully.",
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk):
        return self.patch(request, pk)
