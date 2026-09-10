from django.contrib import admin

from apps.returns.models import (
    ReturnEvidence,
    ReturnInspection,
    ReturnItem,
    ReturnRequest,
    ReturnShipment,
)


class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    extra = 0
    readonly_fields = ["order_line_item", "quantity", "unit_price", "total_amount", "reason"]


class ReturnEvidenceInline(admin.TabularInline):
    model = ReturnEvidence
    extra = 0
    readonly_fields = ["file_url", "description", "created_at"]


class ReturnShipmentInline(admin.StackedInline):
    model = ReturnShipment
    extra = 0
    readonly_fields = ["shipment_number", "awb_number", "courier_name", "status"]


class ReturnInspectionInline(admin.StackedInline):
    model = ReturnInspection
    extra = 0
    readonly_fields = [
        "inspected_by",
        "result",
        "disposition",
        "quantity_passed",
        "quantity_failed",
        "inspected_at",
    ]


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = [
        "return_number",
        "order",
        "user",
        "status",
        "reason",
        "requested_resolution",
        "approved_resolution",
        "created_at",
    ]
    list_filter = ["status", "reason", "requested_resolution", "approved_resolution"]
    search_fields = ["return_number", "order__order_number", "user__email"]
    readonly_fields = [
        "return_number",
        "order",
        "user",
        "created_at",
        "updated_at",
        "reviewed_at",
        "completed_at",
        "cancelled_at",
    ]
    inlines = [ReturnItemInline, ReturnEvidenceInline, ReturnShipmentInline, ReturnInspectionInline]


@admin.register(ReturnShipment)
class ReturnShipmentAdmin(admin.ModelAdmin):
    list_display = ["shipment_number", "return_request", "courier_name", "awb_number", "status"]
    list_filter = ["status", "courier_name"]
    search_fields = ["shipment_number", "awb_number", "return_request__return_number"]


@admin.register(ReturnInspection)
class ReturnInspectionAdmin(admin.ModelAdmin):
    list_display = ["return_request", "result", "disposition", "inspected_by", "inspected_at"]
    list_filter = ["result", "disposition"]
    search_fields = ["return_request__return_number", "inspected_by__email"]
