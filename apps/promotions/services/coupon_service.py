import logging
from decimal import Decimal
from typing import Any, Iterable, Optional, Tuple

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.promotions.models import Coupon, CouponScope, CouponUsage
from apps.promotions.services.discount_engine import DiscountEngine

logger = logging.getLogger(__name__)


class CouponService:
    """
    Authoritative service managing coupon validation, application,
    concurrency locking, usage recording, and rollback.
    """

    @classmethod
    def validate_coupon(
        cls,
        code: str,
        user: Any = None,
        cart_items: Optional[Iterable[Any]] = None,
        is_wholesale: bool = False,
    ) -> Coupon:
        """
        Validates coupon existence, active state, date validity, wholesale rules,
        global usage limit, user redemption limit, and qualifying cart criteria.
        Raises ValidationError if invalid.
        """
        if not code or not code.strip():
            raise ValidationError({"code": "Coupon code is required."})

        cleaned_code = code.strip().upper()
        try:
            coupon = Coupon.objects.prefetch_related(
                "applicable_categories", "applicable_variants"
            ).get(code=cleaned_code)
        except Coupon.DoesNotExist:
            raise ValidationError({"code": "Invalid coupon code."})

        if not coupon.is_active:
            raise ValidationError({"code": "This coupon is no longer active."})

        now = timezone.now()
        if now < coupon.valid_from:
            raise ValidationError({"code": "This coupon promotion has not started yet."})
        if now > coupon.valid_to:
            raise ValidationError({"code": "This coupon has expired."})

        if is_wholesale and not coupon.applicable_to_wholesale:
            raise ValidationError(
                {"code": "This coupon cannot be combined with wholesale contract pricing."}
            )

        if coupon.usage_limit_total is not None and coupon.times_used >= coupon.usage_limit_total:
            raise ValidationError(
                {"code": "This coupon has reached its maximum global usage limit."}
            )

        if user and user.is_authenticated:
            user_usages = CouponUsage.objects.filter(coupon=coupon, user=user).count()
            if user_usages >= coupon.usage_limit_per_user:
                raise ValidationError(
                    {"code": "You have already reached the redemption limit for this coupon."}
                )

        if cart_items:
            items_list = list(cart_items)
            qualifying_amount = Decimal("0.00")
            total_cart_amount = Decimal("0.00")

            allowed_cat_ids = set(coupon.applicable_categories.values_list("id", flat=True))
            allowed_var_ids = set(coupon.applicable_variants.values_list("id", flat=True))

            for item in items_list:
                unit_price = getattr(item, "unit_price", None)
                if unit_price is None:
                    continue
                qty = getattr(item, "quantity", 1)
                line_val = Decimal(str(unit_price)) * qty
                total_cart_amount += line_val

                variant = getattr(item, "variant", None)
                if not variant:
                    continue

                if coupon.scope == CouponScope.ORDER:
                    qualifying_amount += line_val
                elif coupon.scope == CouponScope.CATEGORY:
                    category_id = getattr(getattr(variant, "product", None), "category_id", None)
                    if category_id and category_id in allowed_cat_ids:
                        qualifying_amount += line_val
                elif coupon.scope == CouponScope.PRODUCT:
                    if variant.id in allowed_var_ids:
                        qualifying_amount += line_val

            if total_cart_amount < coupon.min_order_value:
                raise ValidationError(
                    {
                        "code": (
                            f"A minimum order value of Rs. {coupon.min_order_value} is required "
                            f"to use this coupon. (Cart: Rs. {total_cart_amount})"
                        )
                    }
                )

            if qualifying_amount <= Decimal("0.00"):
                raise ValidationError(
                    {"code": "None of the items in your cart qualify for this coupon."}
                )

        return coupon

    @classmethod
    def apply_coupon_to_cart(
        cls, cart: Any, code: str, user: Any = None
    ) -> Tuple[Any, Coupon, Decimal]:
        """
        Validates coupon and attaches it to the cart. Calculates estimated discount.
        """
        items = list(cart.items.select_related("variant__product__category").all())
        if not items:
            raise ValidationError({"cart": "Cannot apply coupon to an empty cart."})

        # Augment items with unit_price for evaluation
        from apps.cart.services.cart_service import CartService

        for item in items:
            item.unit_price = CartService.unit_price(item.variant, item.quantity, user)

        is_wholesale = bool(user and getattr(user, "is_wholesale_buyer", False))
        coupon = cls.validate_coupon(
            code=code, user=user, cart_items=items, is_wholesale=is_wholesale
        )

        discount_amount = DiscountEngine.calculate_coupon_discount(
            coupon=coupon, items=items, is_wholesale=is_wholesale
        )
        if discount_amount <= Decimal("0.00"):
            raise ValidationError(
                {"code": "This coupon provides no discount for the items in your cart."}
            )

        cart.applied_coupon = coupon
        cart.save(update_fields=["applied_coupon", "updated_at"])

        logger.info(
            f"Coupon {coupon.code} applied to Cart {cart.id} by user {user} (Est. discount: Rs. {discount_amount})"
        )
        return cart, coupon, discount_amount

    @classmethod
    def remove_coupon_from_cart(cls, cart: Any) -> Any:
        """Removes any currently applied coupon from the cart."""
        cart.applied_coupon = None
        cart.save(update_fields=["applied_coupon", "updated_at"])
        return cart

    @classmethod
    @transaction.atomic
    def lock_and_record_usage(
        cls, coupon_id: Any, user: Any, order: Any, discount_amount: Decimal
    ) -> CouponUsage:
        """
        Acquires an exclusive row-level lock on the Coupon, validates usage limits
        under lock, increments times_used, and creates a CouponUsage record.
        Must be called within transaction.atomic() during checkout.
        """
        coupon = Coupon.objects.select_for_update().get(id=coupon_id)

        if not coupon.is_active:
            raise ValidationError("Applied coupon is no longer active.")

        now = timezone.now()
        if now < coupon.valid_from or now > coupon.valid_to:
            raise ValidationError("Applied coupon has expired.")

        if coupon.usage_limit_total is not None and coupon.times_used >= coupon.usage_limit_total:
            raise ValidationError("Applied coupon has reached its maximum global usage limit.")

        if user and user.is_authenticated:
            user_usages = CouponUsage.objects.filter(coupon=coupon, user=user).count()
            if user_usages >= coupon.usage_limit_per_user:
                raise ValidationError(
                    "You have already reached the redemption limit for this coupon."
                )

        # Atomically increment counter
        Coupon.objects.filter(id=coupon.id).update(
            times_used=F("times_used") + 1, updated_at=timezone.now()
        )

        usage = CouponUsage.objects.create(
            coupon=coupon,
            user=user,
            order=order,
            discount_amount=discount_amount,
        )

        logger.info(
            f"Coupon {coupon.code} redeemed for Order {order.order_number} "
            f"(Discount: Rs. {discount_amount}, User: {user})"
        )
        return usage

    @classmethod
    @transaction.atomic
    def release_coupon_usage(cls, order: Any) -> bool:
        """
        Idempotently releases coupon usage and decrements times_used counter
        when an order is cancelled or expires in PENDING_PAYMENT.
        """
        usages = list(
            CouponUsage.objects.select_for_update().filter(order=order).select_related("coupon")
        )
        if not usages:
            return False

        for usage in usages:
            Coupon.objects.filter(id=usage.coupon_id, times_used__gt=0).update(
                times_used=F("times_used") - 1, updated_at=timezone.now()
            )
            usage.delete()
            logger.info(
                f"Released coupon usage for {usage.coupon.code} from Order {order.order_number}"
            )

        return True
