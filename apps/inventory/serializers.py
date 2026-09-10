from rest_framework import serializers

from apps.inventory.models import StockItem, StockMovement, StockReservation


class StockItemSerializer(serializers.ModelSerializer):
    variant_id = serializers.UUIDField(source="variant.id", read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    variant_name = serializers.CharField(source="variant.variant_name", read_only=True)
    quantity_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = StockItem
        fields = [
            "id",
            "variant_id",
            "sku",
            "product_name",
            "variant_name",
            "quantity_on_hand",
            "quantity_reserved",
            "quantity_available",
            "reorder_level",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class StockMovementSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "movement_type",
            "quantity_delta",
            "reserved_quantity_delta",
            "reference_type",
            "reference_id",
            "actor_email",
            "note",
            "created_at",
        ]
        read_only_fields = fields


class StockReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockReservation
        fields = [
            "id",
            "reference_type",
            "reference_id",
            "quantity",
            "expires_at",
            "status",
            "released_at",
            "consumed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class StockRestockSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class StockAdjustmentSerializer(serializers.Serializer):
    quantity_delta = serializers.IntegerField()
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")

    def validate_quantity_delta(self, value):
        if value == 0:
            raise serializers.ValidationError("Stock adjustment cannot be zero.")
        return value


class StockItemStaffUpdateSerializer(serializers.Serializer):
    quantity_on_hand = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    reorder_level = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")

