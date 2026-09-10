from rest_framework import serializers

from apps.promotions.models import (
    Coupon,
    DiscountType,
    OrderDiscountSnapshot,
    Promotion,
    PromotionRule,
)


class ApplyCouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50, required=True, trim_whitespace=True)

    def validate_code(self, value):
        if not value.strip():
            raise serializers.ValidationError("Coupon code cannot be blank.")
        return value.strip().upper()


class PublicCouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "description",
            "discount_type",
            "discount_value",
            "min_order_value",
            "max_discount_amount",
            "valid_from",
            "valid_to",
            "scope",
        ]
        read_only_fields = fields


class StaffCouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "description",
            "discount_type",
            "discount_value",
            "min_order_value",
            "max_discount_amount",
            "valid_from",
            "valid_to",
            "usage_limit_total",
            "usage_limit_per_user",
            "times_used",
            "is_active",
            "applicable_to_wholesale",
            "scope",
            "applicable_categories",
            "applicable_variants",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "times_used", "created_at", "updated_at"]

    def validate(self, attrs):
        discount_type = attrs.get("discount_type") or getattr(self.instance, "discount_type", None)
        discount_value = attrs.get("discount_value") or getattr(
            self.instance, "discount_value", None
        )
        valid_from = attrs.get("valid_from") or getattr(self.instance, "valid_from", None)
        valid_to = attrs.get("valid_to") or getattr(self.instance, "valid_to", None)

        if valid_from and valid_to and valid_to <= valid_from:
            raise serializers.ValidationError(
                {"valid_to": "valid_to must be strictly after valid_from."}
            )

        if discount_type == DiscountType.PERCENTAGE and discount_value and discount_value > 100:
            raise serializers.ValidationError(
                {"discount_value": "Percentage discount cannot exceed 100%."}
            )

        return attrs


class PromotionRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionRule
        fields = ["id", "target_category", "target_variant", "min_quantity"]
        read_only_fields = ["id"]


class StaffPromotionSerializer(serializers.ModelSerializer):
    rules = PromotionRuleSerializer(many=True, required=False)

    class Meta:
        model = Promotion
        fields = [
            "id",
            "name",
            "description",
            "promo_type",
            "discount_type",
            "discount_value",
            "min_order_value",
            "max_discount_amount",
            "priority",
            "valid_from",
            "valid_to",
            "is_active",
            "applicable_to_wholesale",
            "stackable_with_coupons",
            "rules",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OrderDiscountSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDiscountSnapshot
        fields = [
            "id",
            "discount_name",
            "discount_type",
            "discount_value",
            "applied_amount",
            "statutory_gst_adjusted",
            "created_at",
        ]
        read_only_fields = fields
