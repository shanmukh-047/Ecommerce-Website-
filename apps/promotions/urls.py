from django.urls import path

from apps.promotions.views import (
    CartCouponApplyView,
    CartCouponRemoveView,
    StaffCouponDetailView,
    StaffCouponListCreateView,
    StaffCouponToggleView,
    StaffPromotionDetailView,
    StaffPromotionListCreateView,
)

urlpatterns = [
    # Customer Cart Coupon Endpoints
    path("cart/coupon/", CartCouponApplyView.as_view(), name="cart-coupon-apply"),
    path("cart/coupon/remove/", CartCouponRemoveView.as_view(), name="cart-coupon-remove"),
    # Staff Coupon Management
    path(
        "staff/promotions/coupons/",
        StaffCouponListCreateView.as_view(),
        name="staff-coupon-list-create",
    ),
    path(
        "staff/promotions/coupons/<uuid:pk>/",
        StaffCouponDetailView.as_view(),
        name="staff-coupon-detail",
    ),
    path(
        "staff/promotions/coupons/<uuid:pk>/toggle/",
        StaffCouponToggleView.as_view(),
        name="staff-coupon-toggle",
    ),
    # Staff Promotion Management
    path(
        "staff/promotions/promotions/",
        StaffPromotionListCreateView.as_view(),
        name="staff-promotion-list-create",
    ),
    path(
        "staff/promotions/promotions/<uuid:pk>/",
        StaffPromotionDetailView.as_view(),
        name="staff-promotion-detail",
    ),
]
