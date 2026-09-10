import secrets

from django.db import IntegrityError, transaction
from django.db.models import Prefetch

from apps.cart.exceptions import CartConflict
from apps.cart.models import Cart, CartItem
from apps.inventory.models import StockItem


class CartService:
    @staticmethod
    def generate_guest_token():
        return secrets.token_urlsafe(32)

    @classmethod
    def get_or_create_user_cart(cls, user):
        return Cart.objects.get_or_create(user=user)[0]

    @classmethod
    def get_guest_cart(cls, token):
        return Cart.objects.filter(guest_token=token).first() if token else None

    @classmethod
    def get_or_create_guest_cart(cls, token=None):
        if token:
            cart = cls.get_guest_cart(token)
            if cart:
                return cart, False
            raise CartConflict("Invalid guest cart token.")
        token = cls.generate_guest_token()
        return Cart.objects.create(guest_token=token), True

    @staticmethod
    def unit_price(variant, quantity, user=None):
        if user and user.is_authenticated and user.is_wholesale_buyer:
            slabs = [
                s
                for s in variant.wholesale_slabs.all()
                if s.is_active and s.min_quantity <= quantity
            ]
            if slabs:
                return max(slabs, key=lambda slab: slab.min_quantity).wholesale_price_per_unit
        return variant.selling_price

    @staticmethod
    def available_quantity(variant):
        try:
            return variant.stock_item.quantity_available
        except StockItem.DoesNotExist:
            return 0

    @classmethod
    @transaction.atomic
    def add_item(cls, cart, variant, quantity):
        if not variant.is_active:
            raise CartConflict("This product variant is no longer active.")
        if quantity <= 0:
            raise CartConflict("Quantity must be greater than zero.")

        stock = StockItem.objects.select_for_update().filter(variant=variant).first()
        if not stock or stock.quantity_available < quantity:
            raise CartConflict("Insufficient inventory for the requested quantity.")

        item = CartItem.objects.select_for_update().filter(cart=cart, variant=variant).first()
        if item:
            requested = item.quantity + quantity
            if stock.quantity_available < requested:
                raise CartConflict("Insufficient inventory for the requested quantity.")
            item.quantity = requested
            item.save(update_fields=["quantity", "updated_at"])
        else:
            try:
                with transaction.atomic():
                    item = CartItem.objects.create(cart=cart, variant=variant, quantity=quantity)
            except IntegrityError:
                item = CartItem.objects.select_for_update().get(cart=cart, variant=variant)
                requested = item.quantity + quantity
                if stock.quantity_available < requested:
                    raise CartConflict("Insufficient inventory for the requested quantity.")
                item.quantity = requested
                item.save(update_fields=["quantity", "updated_at"])

        return item

    @classmethod
    @transaction.atomic
    def update_item(cls, cart, item_id, quantity):
        if quantity <= 0:
            raise CartConflict("Quantity must be greater than zero.")
        item = (
            CartItem.objects.select_for_update()
            .select_related("variant")
            .filter(cart=cart, pk=item_id)
            .first()
        )
        if not item:
            raise CartConflict("Cart item was not found.")
        stock = StockItem.objects.select_for_update().filter(variant=item.variant).first()
        if not item.variant.is_active or not stock or stock.quantity_available < quantity:
            raise CartConflict("Insufficient inventory for the requested quantity.")
        item.quantity = quantity
        item.save(update_fields=["quantity", "updated_at"])
        return item

    @classmethod
    @transaction.atomic
    def remove_item(cls, cart, item_id):
        item = CartItem.objects.select_for_update().filter(cart=cart, pk=item_id).first()
        if not item:
            raise CartConflict("Cart item was not found.")
        item.delete()

    @classmethod
    @transaction.atomic
    def clear_cart(cls, cart):
        CartItem.objects.filter(cart=cart).delete()

    @classmethod
    @transaction.atomic
    def merge_guest_cart_into_user_cart(cls, user, token):
        guest = cls.get_guest_cart(token)
        user_cart = cls.get_or_create_user_cart(user)
        adjustments = []
        if not guest:
            return user_cart, adjustments

        for guest_item in guest.items.select_related("variant").select_for_update():
            stock = StockItem.objects.select_for_update().filter(variant=guest_item.variant).first()
            user_item = (
                CartItem.objects.select_for_update()
                .filter(cart=user_cart, variant=guest_item.variant)
                .first()
            )
            current_qty = user_item.quantity if user_item else 0
            desired = current_qty + guest_item.quantity
            available = stock.quantity_available if (stock and guest_item.variant.is_active) else 0
            allowed = min(desired, available)

            if allowed != desired:
                adjustments.append(
                    {
                        "variant_id": str(guest_item.variant_id),
                        "requested": desired,
                        "accepted": allowed,
                    }
                )

            if allowed > 0:
                if user_item:
                    user_item.quantity = allowed
                    user_item.save(update_fields=["quantity", "updated_at"])
                else:
                    CartItem.objects.create(
                        cart=user_cart, variant=guest_item.variant, quantity=allowed
                    )
            elif user_item:
                user_item.delete()

        guest.delete()
        return user_cart, adjustments

    @classmethod
    def validate_cart(cls, cart, user=None):
        issues = []
        for item in cart.items.all():
            if not item.variant.is_active:
                issues.append({"item_id": str(item.id), "code": "INACTIVE_VARIANT"})
            elif cls.available_quantity(item.variant) < item.quantity:
                issues.append({"item_id": str(item.id), "code": "INSUFFICIENT_STOCK"})
        return issues

    @staticmethod
    def hydrate(cart):
        return (
            Cart.objects.select_related("applied_coupon")
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=CartItem.objects.select_related(
                        "variant__product__category", "variant__stock_item"
                    ).prefetch_related("variant__wholesale_slabs"),
                )
            )
            .get(pk=cart.pk)
        )
