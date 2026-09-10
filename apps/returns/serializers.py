from rest_framework import serializers

from apps.returns.models import (
    InspectionResult,
    InventoryDisposition,
    ResolutionType,
    ReturnEvidence,
    ReturnInspection,
    ReturnItem,
    ReturnReason,
    ReturnRequest,
    ReturnShipment,
    ReturnShipmentStatus,
)
from apps.shipping.models import CourierProvider


class ReturnEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnEvidence
        fields = ["id", "file_url", "description", "created_at"]
        read_only_fields = ["id", "created_at"]


class ReturnItemCreateSerializer(serializers.Serializer):
    order_line_item_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    reason = serializers.ChoiceField(choices=ReturnReason.choices, required=False)


class ReturnItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="order_line_item.product_name", read_only=True)
    variant_name = serializers.CharField(source="order_line_item.variant_name", read_only=True)
    sku = serializers.CharField(source="order_line_item.sku", read_only=True)

    class Meta:
        model = ReturnItem
        fields = [
            "id",
            "order_line_item_id",
            "product_name",
            "variant_name",
            "sku",
            "quantity",
            "unit_price",
            "total_amount",
            "reason",
        ]
        read_only_fields = fields


class ReturnShipmentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    courier_display = serializers.CharField(source="get_courier_name_display", read_only=True)

    class Meta:
        model = ReturnShipment
        fields = [
            "id",
            "shipment_number",
            "courier_name",
            "courier_display",
            "awb_number",
            "status",
            "status_display",
            "scheduled_pickup_date",
            "actual_pickup_date",
            "received_at_warehouse",
            "tracking_notes",
        ]
        read_only_fields = fields


class ReturnInspectionSerializer(serializers.ModelSerializer):
    result_display = serializers.CharField(source="get_result_display", read_only=True)
    disposition_display = serializers.CharField(source="get_disposition_display", read_only=True)
    inspector_email = serializers.CharField(source="inspected_by.email", read_only=True)

    class Meta:
        model = ReturnInspection
        fields = [
            "id",
            "result",
            "result_display",
            "disposition",
            "disposition_display",
            "quantity_passed",
            "quantity_failed",
            "notes",
            "inspector_email",
            "inspected_at",
        ]
        read_only_fields = fields


class ReturnRequestCreateSerializer(serializers.Serializer):
    items = ReturnItemCreateSerializer(many=True)
    reason = serializers.ChoiceField(choices=ReturnReason.choices)
    requested_resolution = serializers.ChoiceField(
        choices=ResolutionType.choices, default=ResolutionType.REFUND
    )
    customer_notes = serializers.CharField(required=False, allow_blank=True, default="")
    evidence_urls = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


class ReturnRequestListSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)
    items_count = serializers.SerializerMethodField()
    total_refund_claimed = serializers.SerializerMethodField()

    class Meta:
        model = ReturnRequest
        fields = [
            "id",
            "return_number",
            "order_id",
            "order_number",
            "status",
            "status_display",
            "reason",
            "reason_display",
            "requested_resolution",
            "approved_resolution",
            "items_count",
            "total_refund_claimed",
            "created_at",
            "completed_at",
        ]
        read_only_fields = fields

    def get_items_count(self, obj) -> int:
        return sum(item.quantity for item in obj.items.all())

    def get_total_refund_claimed(self, obj) -> str:
        total = sum((item.total_amount for item in obj.items.all()), 0)
        return str(total)


class ReturnRequestDetailSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)
    items = ReturnItemSerializer(many=True, read_only=True)
    evidence = ReturnEvidenceSerializer(many=True, read_only=True)
    reverse_shipment = ReturnShipmentSerializer(read_only=True)
    inspection = ReturnInspectionSerializer(read_only=True)
    credit_note_number = serializers.CharField(
        source="credit_note.credit_note_number", read_only=True
    )
    replacement_order_number = serializers.CharField(
        source="replacement_order.order_number", read_only=True
    )

    class Meta:
        model = ReturnRequest
        fields = [
            "id",
            "return_number",
            "order_id",
            "order_number",
            "status",
            "status_display",
            "reason",
            "reason_display",
            "requested_resolution",
            "approved_resolution",
            "customer_notes",
            "staff_review_notes",
            "rejection_reason",
            "items",
            "evidence",
            "reverse_shipment",
            "inspection",
            "credit_note_id",
            "credit_note_number",
            "refund_amount",
            "refund_transaction_id",
            "replacement_order_id",
            "replacement_order_number",
            "created_at",
            "reviewed_at",
            "completed_at",
            "cancelled_at",
        ]
        read_only_fields = fields


class StaffReturnReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    approved_resolution = serializers.ChoiceField(
        choices=ResolutionType.choices,
        required=False,
        default=ResolutionType.REFUND,
    )
    rejection_reason = serializers.CharField(required=False, allow_blank=True, default="")
    review_notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["action"] == "REJECT" and not attrs.get("rejection_reason", "").strip():
            raise serializers.ValidationError(
                {"rejection_reason": "Rejection reason is required when rejecting."}
            )
        return attrs


class StaffReversePickupScheduleSerializer(serializers.Serializer):
    courier_name = serializers.ChoiceField(
        choices=CourierProvider.choices,
        default=CourierProvider.MANUAL,
    )
    scheduled_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class StaffReverseShipmentStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ReturnShipmentStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class StaffReturnInspectionSerializer(serializers.Serializer):
    result = serializers.ChoiceField(
        choices=InspectionResult.choices, default=InspectionResult.PASSED
    )
    disposition = serializers.ChoiceField(
        choices=InventoryDisposition.choices, default=InventoryDisposition.RESTOCK
    )
    quantity_passed = serializers.IntegerField(min_value=0, default=0)
    quantity_failed = serializers.IntegerField(min_value=0, default=0)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class StaffReturnCompleteSerializer(serializers.Serializer):
    resolution = serializers.ChoiceField(
        choices=ResolutionType.choices,
        required=False,
        allow_null=True,
    )
