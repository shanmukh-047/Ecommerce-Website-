from rest_framework import serializers

from apps.shipping.models import (
    CourierProvider,
    Shipment,
    ShipmentItem,
    ShipmentStatus,
    ShipmentTrackingEvent,
)


class ShipmentTrackingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentTrackingEvent
        fields = [
            "id",
            "status",
            "location",
            "description",
            "event_timestamp",
            "created_at",
        ]
        read_only_fields = fields


class ShipmentItemSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="order_line_item.sku", read_only=True)
    product_name = serializers.CharField(source="order_line_item.product_name", read_only=True)
    variant_name = serializers.CharField(source="order_line_item.variant_name", read_only=True)

    class Meta:
        model = ShipmentItem
        fields = [
            "id",
            "order_line_item",
            "sku",
            "product_name",
            "variant_name",
            "quantity",
        ]
        read_only_fields = fields


class ShipmentSerializer(serializers.ModelSerializer):
    order_id = serializers.UUIDField(source="order.id", read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    items = ShipmentItemSerializer(many=True, read_only=True)
    tracking_events = ShipmentTrackingEventSerializer(many=True, read_only=True)

    class Meta:
        model = Shipment
        fields = [
            "id",
            "shipment_number",
            "order_id",
            "order_number",
            "status",
            "courier_name",
            "awb_number",
            "shipping_label_url",
            "estimated_delivery_date",
            "actual_delivery_date",
            "shipped_at",
            "weight_in_grams",
            "length_cm",
            "breadth_cm",
            "height_cm",
            "shipping_recipient_name",
            "shipping_phone_number",
            "shipping_address_line_1",
            "shipping_address_line_2",
            "shipping_landmark",
            "shipping_city",
            "shipping_state",
            "shipping_pincode",
            "notes",
            "cancellation_reason",
            "items",
            "tracking_events",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CreateShipmentItemRequestSerializer(serializers.Serializer):
    order_line_item_id = serializers.UUIDField(required=True)
    quantity = serializers.IntegerField(min_value=1, required=True)


class CreateShipmentRequestSerializer(serializers.Serializer):
    courier_name = serializers.ChoiceField(
        choices=CourierProvider.choices,
        required=False,
        default=CourierProvider.MANUAL,
    )
    weight_in_grams = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    length_cm = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    breadth_cm = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    height_cm = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    items = serializers.ListField(
        child=CreateShipmentItemRequestSerializer(),
        required=False,
        allow_empty=True,
    )


class UpdateShipmentStatusRequestSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ShipmentStatus.choices, required=True)
    location = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    description = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )


class CancelShipmentRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class PublicTrackingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentTrackingEvent
        fields = [
            "status",
            "location",
            "description",
            "event_timestamp",
        ]
        read_only_fields = fields


class PublicTrackingSerializer(serializers.ModelSerializer):
    """
    Public milestone serializer with strict customer PII redaction.
    """

    destination_city = serializers.CharField(source="shipping_city", read_only=True)
    destination_state = serializers.CharField(source="shipping_state", read_only=True)
    tracking_events = PublicTrackingEventSerializer(many=True, read_only=True)

    class Meta:
        model = Shipment
        fields = [
            "shipment_number",
            "courier_name",
            "awb_number",
            "status",
            "estimated_delivery_date",
            "shipped_at",
            "actual_delivery_date",
            "destination_city",
            "destination_state",
            "tracking_events",
        ]
        read_only_fields = fields
