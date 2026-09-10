from django.contrib import admin

from apps.inventory.models import StockItem, StockMovement, StockReservation


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = [
        "variant",
        "quantity_on_hand",
        "quantity_reserved",
        "quantity_available",
        "reorder_level",
        "updated_at",
    ]
    list_filter = ["variant__product__category"]
    search_fields = ["variant__sku", "variant__variant_name", "variant__product__name"]
    readonly_fields = [
        "variant",
        "quantity_on_hand",
        "quantity_reserved",
        "reorder_level",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        "stock_item",
        "movement_type",
        "quantity_delta",
        "reserved_quantity_delta",
        "actor",
        "reference_type",
        "reference_id",
        "created_at",
    ]
    list_filter = ["movement_type", "created_at"]
    search_fields = ["stock_item__variant__sku", "actor__email", "reference_id"]
    readonly_fields = [field.name for field in StockMovement._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = [
        "stock_item",
        "quantity",
        "status",
        "reference_type",
        "expires_at",
        "created_at",
    ]
    list_filter = ["status", "expires_at"]
    search_fields = ["stock_item__variant__sku", "reference_id"]
    readonly_fields = [field.name for field in StockReservation._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
