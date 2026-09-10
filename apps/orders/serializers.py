from rest_framework import serializers

from .models import Order, OrderLineItem, OrderStatus, OrderStatusHistory


class OrderLineItemSerializer(serializers.ModelSerializer):
    variant_id = serializers.UUIDField(source="variant.id", read_only=True)
    product_slug = serializers.CharField(source="variant.product.slug", read_only=True)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderLineItem
        fields = [
            "id",
            "variant_id",
            "product_name",
            "product_slug",
            "product_image",
            "variant_name",
            "sku",
            "weight_in_grams",
            "mrp",
            "unit_price",
            "quantity",
            "line_subtotal",
            "pricing_tier_applied",
        ]

    def get_product_image(self, line):
        product = getattr(line.variant, "product", None)
        if not product:
            return None
        request = self.context.get("request")
        active_images = [img for img in product.images.all() if img.is_active]
        hero = next((img for img in active_images if img.is_hero), None)
        if not hero and active_images:
            hero = active_images[0]
        if hero and hero.image:
            return request.build_absolute_uri(hero.image.url) if request else hero.image.url
        return None


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source="actor.email", default="", read_only=True)

    class Meta:
        model = OrderStatusHistory
        fields = ["id", "from_status", "to_status", "actor_email", "notes", "created_at"]


class OrderSerializer(serializers.ModelSerializer):
    lines = OrderLineItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    status = serializers.CharField(source="order_status", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    payment_method = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    payment_gateway = serializers.SerializerMethodField()

    def _get_latest_payment(self, obj):
        if hasattr(obj, "_latest_payment_cached"):
            return obj._latest_payment_cached
        if hasattr(obj, "_prefetched_objects_cache") and "payments" in obj._prefetched_objects_cache:
            payments = obj._prefetched_objects_cache["payments"]
            obj._latest_payment_cached = payments[0] if payments else None
        else:
            obj._latest_payment_cached = obj.payments.order_by("-created_at").first()
        return obj._latest_payment_cached

    def get_payment_method(self, obj):
        payment = self._get_latest_payment(obj)
        return payment.payment_method if payment else None

    def get_payment_status(self, obj):
        payment = self._get_latest_payment(obj)
        return payment.status if payment else None

    def get_payment_gateway(self, obj):
        payment = self._get_latest_payment(obj)
        return payment.gateway if payment else None

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "order_status",
            "status",
            "user_email",
            "payment_method",
            "payment_status",
            "payment_gateway",
            "currency",
            "items_subtotal",
            "shipping_fee",
            "tax_amount",
            "total_discount",
            "grand_total",
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
            "customer_notes",
            "cancellation_reason",
            "lines",
            "status_history",
            "created_at",
            "updated_at",
            "paid_at",
            "shipped_at",
            "delivered_at",
            "cancelled_at",
        ]


class CheckoutRequestSerializer(serializers.Serializer):
    shipping_address_id = serializers.UUIDField()
    customer_notes = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )


class OrderCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderStatus.choices)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
