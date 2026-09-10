from django.contrib import admin

from .models import Order, OrderLineItem, OrderStatusHistory


class OrderLineItemInline(admin.TabularInline):
    model = OrderLineItem
    extra = 0
    readonly_fields = [
        "product_name",
        "variant_name",
        "sku",
        "mrp",
        "unit_price",
        "quantity",
        "line_subtotal",
        "pricing_tier_applied",
    ]


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ["from_status", "to_status", "actor", "notes", "created_at"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "user",
        "order_status",
        "grand_total",
        "total_quantity",
        "is_wholesale_order",
        "created_at",
    ]
    list_filter = ["order_status", "is_wholesale_order", "created_at"]
    search_fields = [
        "order_number",
        "user__email",
        "user__phone_number",
        "shipping_recipient_name",
        "shipping_phone_number",
        "shipping_pincode",
    ]
    readonly_fields = [
        "order_number",
        "user",
        "grand_total",
        "items_subtotal",
        "shipping_fee",
        "tax_amount",
        "total_discount",
        "total_quantity",
        "total_weight_in_grams",
        "is_wholesale_order",
        "shipping_recipient_name",
        "shipping_phone_number",
        "shipping_address_line_1",
        "shipping_address_line_2",
        "shipping_landmark",
        "shipping_city",
        "shipping_state",
        "shipping_pincode",
        "created_at",
        "updated_at",
    ]
    inlines = [OrderLineItemInline, OrderStatusHistoryInline]


@admin.register(OrderLineItem)
class OrderLineItemAdmin(admin.ModelAdmin):
    list_display = ["order", "sku", "variant_name", "quantity", "unit_price", "line_subtotal"]
    search_fields = ["order__order_number", "sku", "product_name"]


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ["order", "from_status", "to_status", "actor", "created_at"]
    search_fields = ["order__order_number"]
