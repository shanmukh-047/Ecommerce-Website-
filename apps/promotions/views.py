from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsManagerOrAdmin, IsStaffOrManager
from apps.cart.views import CartIdentityMixin
from apps.promotions.models import Coupon, Promotion
from apps.promotions.serializers import (
    ApplyCouponSerializer,
    StaffCouponSerializer,
    StaffPromotionSerializer,
)
from apps.promotions.services.coupon_service import CouponService


class CartCouponApplyView(CartIdentityMixin, APIView):
    """Applies or removes a promotional coupon code on the active customer/guest cart."""

    permission_classes = [AllowAny]

    def post(self, request):
        cart, created_cookie = self.get_cart(request)
        serializer = ApplyCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user if request.user.is_authenticated else None
        cart, coupon, discount_amount = CouponService.apply_coupon_to_cart(
            cart=cart,
            code=serializer.validated_data["code"],
            user=user,
        )

        return self.cart_response(
            request,
            cart,
            created_cookie,
            f"Coupon '{coupon.code}' applied successfully. Saved Rs. {discount_amount}.",
        )

    def delete(self, request):
        cart, created_cookie = self.get_cart(request)
        CouponService.remove_coupon_from_cart(cart)
        return self.cart_response(request, cart, created_cookie, "Coupon removed from cart.")


class CartCouponRemoveView(CartIdentityMixin, APIView):
    """Removes any applied coupon code from the active cart."""

    permission_classes = [AllowAny]

    def delete(self, request):
        cart, created_cookie = self.get_cart(request)
        CouponService.remove_coupon_from_cart(cart)
        return self.cart_response(request, cart, created_cookie, "Coupon removed from cart.")


class StaffCouponListCreateView(generics.ListCreateAPIView):
    """Staff endpoint to list and create discount coupons."""

    queryset = Coupon.objects.prefetch_related("applicable_categories", "applicable_variants").all()
    serializer_class = StaffCouponSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsManagerOrAdmin()]
        return [IsAuthenticated(), IsStaffOrManager()]


class StaffCouponDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Staff endpoint to view, update, or delete a specific coupon."""

    queryset = Coupon.objects.prefetch_related("applicable_categories", "applicable_variants").all()
    serializer_class = StaffCouponSerializer

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated(), IsManagerOrAdmin()]
        return [IsAuthenticated(), IsStaffOrManager()]


class StaffCouponToggleView(APIView):
    """Staff endpoint to quickly activate or deactivate a coupon."""

    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def post(self, request, pk):
        coupon = get_object_or_404(Coupon, pk=pk)
        coupon.is_active = not coupon.is_active
        coupon.save(update_fields=["is_active", "updated_at"])
        status_str = "activated" if coupon.is_active else "deactivated"
        return Response(
            {
                "coupon": StaffCouponSerializer(coupon).data,
                "_message": f"Coupon '{coupon.code}' successfully {status_str}.",
            },
            status=status.HTTP_200_OK,
        )


class StaffPromotionListCreateView(generics.ListCreateAPIView):
    """Staff endpoint to list and create automatic promotions."""

    queryset = Promotion.objects.prefetch_related("rules").all()
    serializer_class = StaffPromotionSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsManagerOrAdmin()]
        return [IsAuthenticated(), IsStaffOrManager()]


class StaffPromotionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Staff endpoint to view, update, or delete an automatic promotion."""

    queryset = Promotion.objects.prefetch_related("rules").all()
    serializer_class = StaffPromotionSerializer

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated(), IsManagerOrAdmin()]
        return [IsAuthenticated(), IsStaffOrManager()]
