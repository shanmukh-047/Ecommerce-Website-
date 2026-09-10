from django.contrib import admin

from apps.shipping.models import Shipment, ShipmentItem, ShipmentTrackingEvent


class ShipmentItemInline(admin.TabularInline):
    model = ShipmentItem
    extra = 0
    readonly_fields = ["order_line_item", "quantity", "created_at"]
    can_delete = False


class ShipmentTrackingEventInline(admin.TabularInline):
    model = ShipmentTrackingEvent
    extra = 0
    readonly_fields = ["status", "location", "description", "event_timestamp", "created_at"]
    can_delete = False


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = [
        "shipment_number",
        "order",
        "status",
        "courier_name",
        "awb_number",
        "weight_in_grams",
        "shipped_at",
        "actual_delivery_date",
        "created_at",
    ]
    list_filter = ["status", "courier_name", "created_at"]
    search_fields = [
        "shipment_number",
        "order__order_number",
        "awb_number",
        "shipping_recipient_name",
        "shipping_phone_number",
    ]
    readonly_fields = [
        "id",
        "shipment_number",
        "order",
        "shipped_at",
        "actual_delivery_date",
        "created_at",
        "updated_at",
    ]
    inlines = [ShipmentItemInline, ShipmentTrackingEventInline]
