from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Iterable, List, Optional

from apps.promotions.models import Coupon, CouponScope, DiscountType, Promotion


@dataclass
class AppliedDiscountDetail:
    name: str
    source_type: str  # "COUPON" or "PROMOTION"
    source_id: str
    discount_type: str
    discount_value: Decimal
    applied_amount: Decimal


@dataclass
class DiscountResult:
    items_subtotal: Decimal
    total_discount: Decimal
    coupon_discount: Decimal
    promotion_discount: Decimal
    net_subtotal: Decimal
    applied_coupon: Optional[Coupon] = None
    applied_promotions: List[Promotion] = field(default_factory=list)
    breakdown: List[AppliedDiscountDetail] = field(default_factory=list)


class DiscountEngine:
    """
    Authoritative calculation engine that evaluates cart/order items against
    coupons and promotions to determine deterministic discount breakdowns.
    Guarantees non-negative totals and prevents discount > subtotal.
    """

    @classmethod
    def calculate_coupon_discount(
        cls,
        coupon: Coupon,
        items: Iterable[Any],
        is_wholesale: bool = False,
    ) -> Decimal:
        """
        Calculates the exact discount for a validated coupon given line items.
        Returns Decimal('0.00') if criteria are not met.
        """
        if not coupon or not coupon.is_currently_active:
            return Decimal("0.00")

        if is_wholesale and not coupon.applicable_to_wholesale:
            return Decimal("0.00")

        qualifying_amount = Decimal("0.00")
        total_cart_amount = Decimal("0.00")

        # Extract allowed categories and variants
        allowed_cat_ids = set(coupon.applicable_categories.values_list("id", flat=True))
        allowed_var_ids = set(coupon.applicable_variants.values_list("id", flat=True))

        for item in items:
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

        if total_cart_amount < coupon.min_order_value or qualifying_amount <= Decimal("0.00"):
            return Decimal("0.00")

        if coupon.discount_type == DiscountType.PERCENTAGE:
            discount = (qualifying_amount * coupon.discount_value) / Decimal("100.00")
        else:  # FIXED_AMOUNT
            discount = min(coupon.discount_value, qualifying_amount)

        if coupon.max_discount_amount is not None and coupon.max_discount_amount > Decimal("0.00"):
            discount = min(discount, coupon.max_discount_amount)

        discount = discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return min(discount, qualifying_amount)

    @classmethod
    def evaluate_discounts(
        cls,
        items: Iterable[Any],
        applied_coupon: Optional[Coupon] = None,
        user: Any = None,
        is_wholesale: bool = False,
        promotions: Optional[Iterable[Promotion]] = None,
    ) -> DiscountResult:
        """
        Evaluates active promotions and an applied coupon to determine the final
        net subtotal and discount breakdown.
        """
        items_subtotal = Decimal("0.00")
        for item in items:
            unit_price = getattr(item, "unit_price", Decimal("0.00"))
            qty = getattr(item, "quantity", 1)
            items_subtotal += Decimal(str(unit_price)) * qty

        items_subtotal = items_subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if items_subtotal <= Decimal("0.00"):
            return DiscountResult(
                items_subtotal=Decimal("0.00"),
                total_discount=Decimal("0.00"),
                coupon_discount=Decimal("0.00"),
                promotion_discount=Decimal("0.00"),
                net_subtotal=Decimal("0.00"),
            )

        promo_discount = Decimal("0.00")
        applied_promos: List[Promotion] = []
        breakdown: List[AppliedDiscountDetail] = []

        # 1. Automatic promotions evaluation
        if promotions:
            remaining_for_promos = items_subtotal
            for promo in promotions:
                if not promo.is_currently_active:
                    continue
                if is_wholesale and not promo.applicable_to_wholesale:
                    continue
                if items_subtotal < promo.min_order_value:
                    continue

                if promo.discount_type == DiscountType.PERCENTAGE:
                    curr_disc = (remaining_for_promos * promo.discount_value) / Decimal("100.00")
                else:
                    curr_disc = min(promo.discount_value, remaining_for_promos)

                if promo.max_discount_amount and promo.max_discount_amount > Decimal("0.00"):
                    curr_disc = min(curr_disc, promo.max_discount_amount)

                curr_disc = curr_disc.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                curr_disc = min(curr_disc, remaining_for_promos)

                if curr_disc > Decimal("0.00"):
                    promo_discount += curr_disc
                    remaining_for_promos -= curr_disc
                    applied_promos.append(promo)
                    breakdown.append(
                        AppliedDiscountDetail(
                            name=promo.name,
                            source_type="PROMOTION",
                            source_id=str(promo.id),
                            discount_type=promo.discount_type,
                            discount_value=promo.discount_value,
                            applied_amount=curr_disc,
                        )
                    )

        # 2. Coupon evaluation on top
        coupon_discount = Decimal("0.00")
        if applied_coupon:
            # If active promotions exist and stackable_with_coupons is False, check stacking
            can_apply_coupon = True
            for promo in applied_promos:
                if not promo.stackable_with_coupons:
                    can_apply_coupon = False
                    break

            if can_apply_coupon:
                raw_coupon_disc = cls.calculate_coupon_discount(
                    applied_coupon, items, is_wholesale=is_wholesale
                )
                # Ensure total discount cannot exceed items_subtotal
                max_allowed = max(Decimal("0.00"), items_subtotal - promo_discount)
                coupon_discount = min(raw_coupon_disc, max_allowed)

                if coupon_discount > Decimal("0.00"):
                    breakdown.append(
                        AppliedDiscountDetail(
                            name=f"Coupon: {applied_coupon.code}",
                            source_type="COUPON",
                            source_id=str(applied_coupon.id),
                            discount_type=applied_coupon.discount_type,
                            discount_value=applied_coupon.discount_value,
                            applied_amount=coupon_discount,
                        )
                    )

        total_discount = promo_discount + coupon_discount
        total_discount = min(total_discount, items_subtotal)
        net_subtotal = max(Decimal("0.00"), items_subtotal - total_discount)

        return DiscountResult(
            items_subtotal=items_subtotal,
            total_discount=total_discount,
            coupon_discount=coupon_discount,
            promotion_discount=promo_discount,
            net_subtotal=net_subtotal,
            applied_coupon=applied_coupon if coupon_discount > Decimal("0.00") else None,
            applied_promotions=applied_promos,
            breakdown=breakdown,
        )
