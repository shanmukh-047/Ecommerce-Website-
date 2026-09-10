from rest_framework import serializers

from apps.cart.models import Cart
from apps.cart.services import CartService


class CartItemSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    variant_id = serializers.UUIDField(source="variant.id", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    product_slug = serializers.CharField(source="variant.product.slug", read_only=True)
    product_image = serializers.SerializerMethodField()
    variant_name = serializers.CharField(source="variant.variant_name", read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    weight_in_grams = serializers.IntegerField(source="variant.weight_in_grams", read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    mrp = serializers.DecimalField(
        source="variant.mrp", max_digits=10, decimal_places=2, read_only=True
    )
    unit_price = serializers.SerializerMethodField()
    line_total = serializers.SerializerMethodField()
    stock_available = serializers.SerializerMethodField()

    def get_product_image(self, item):
        product = getattr(item.variant, "product", None)
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

    def get_unit_price(self, item):
        return CartService.unit_price(item.variant, item.quantity, self.context.get("user"))

    def get_line_total(self, item):
        return self.get_unit_price(item) * item.quantity

    def get_stock_available(self, item):
        return CartService.available_quantity(item.variant) >= item.quantity


class CartSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    validation_issues = serializers.SerializerMethodField()
    applied_coupon_code = serializers.SerializerMethodField()
    items_subtotal = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    net_subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "items",
            "validation_issues",
            "applied_coupon_code",
            "items_subtotal",
            "discount_amount",
            "net_subtotal",
            "created_at",
            "updated_at",
        ]

    def _get_discount_result(self, cart):
        if not hasattr(cart, "_cached_discount_res"):
            from apps.promotions.services.discount_engine import DiscountEngine
            from apps.promotions.services.promotion_service import PromotionService

            user = self.context.get("user")
            is_wholesale = bool(user and getattr(user, "is_wholesale_buyer", False))
            items = list(cart.items.all())
            for item in items:
                item.unit_price = CartService.unit_price(item.variant, item.quantity, user)

            promotions = PromotionService.get_active_promotions(is_wholesale=is_wholesale)
            cart._cached_discount_res = DiscountEngine.evaluate_discounts(
                items=items,
                applied_coupon=cart.applied_coupon,
                user=user,
                is_wholesale=is_wholesale,
                promotions=promotions,
            )
        return cart._cached_discount_res

    def get_items(self, cart):
        return CartItemSerializer(cart.items.all(), many=True, context=self.context).data

    def get_validation_issues(self, cart):
        return CartService.validate_cart(cart, self.context.get("user"))

    def get_applied_coupon_code(self, cart):
        return cart.applied_coupon.code if cart.applied_coupon else None

    def get_items_subtotal(self, cart):
        res = self._get_discount_result(cart)
        return str(res.items_subtotal)

    def get_discount_amount(self, cart):
        res = self._get_discount_result(cart)
        return str(res.total_discount)

    def get_net_subtotal(self, cart):
        res = self._get_discount_result(cart)
        return str(res.net_subtotal)


class AddCartItemSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
