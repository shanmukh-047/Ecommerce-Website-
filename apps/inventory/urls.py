from django.urls import path

from apps.inventory.views import (
    StockAdjustmentView,
    StockItemDetailView,
    StockItemListView,
    StockRestockView,
)

app_name = "inventory"

urlpatterns = [
    path("", StockItemListView.as_view(), name="stock-item-list"),
    path("restock/", StockRestockView.as_view(), name="stock-restock"),
    path("<uuid:pk>/", StockItemDetailView.as_view(), name="stock-item-detail"),
    path("<uuid:pk>/adjust/", StockAdjustmentView.as_view(), name="stock-adjust"),
]
