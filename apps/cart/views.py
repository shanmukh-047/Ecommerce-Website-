from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.serializers import AddCartItemSerializer, CartSerializer, UpdateCartItemSerializer
from apps.cart.services import CartService
from apps.catalog.models import ProductVariant


class CartIdentityMixin:
    permission_classes = [AllowAny]

    def get_cart(self, request):
        if request.user.is_authenticated:
            return CartService.get_or_create_user_cart(request.user), False
        token = request.COOKIES.get(settings.GUEST_CART_COOKIE_NAME)
        return CartService.get_or_create_guest_cart(token)

    def cart_response(self, request, cart, created_cookie, message, status_code=status.HTTP_200_OK):
        cart = CartService.hydrate(cart)
        response = Response(
            {
                "cart": CartSerializer(cart, context={"user": request.user}).data,
                "_message": message,
            },
            status=status_code,
        )
        if created_cookie:
            response.set_cookie(
                settings.GUEST_CART_COOKIE_NAME,
                cart.guest_token,
                max_age=settings.GUEST_CART_COOKIE_MAX_AGE,
                path=settings.GUEST_CART_COOKIE_PATH,
                domain=settings.COOKIE_DOMAIN,
                secure=settings.SECURE_COOKIE,
                httponly=True,
                samesite=settings.COOKIE_SAMESITE,
            )
        return response


class CartView(CartIdentityMixin, APIView):
    def get(self, request):
        cart, created_cookie = self.get_cart(request)
        return self.cart_response(request, cart, created_cookie, "Cart retrieved successfully.")

    def delete(self, request):
        cart, created_cookie = self.get_cart(request)
        CartService.clear_cart(cart)
        return self.cart_response(request, cart, created_cookie, "Cart cleared successfully.")


class CartItemListCreateView(CartIdentityMixin, APIView):
    def post(self, request):
        cart, created_cookie = self.get_cart(request)
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        variant = get_object_or_404(ProductVariant, pk=serializer.validated_data["variant_id"])
        CartService.add_item(cart, variant, serializer.validated_data["quantity"])
        return self.cart_response(request, cart, created_cookie, "Item added to cart.")


class CartItemDetailView(CartIdentityMixin, APIView):
    def patch(self, request, pk):
        cart, created_cookie = self.get_cart(request)
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        CartService.update_item(cart, pk, serializer.validated_data["quantity"])
        return self.cart_response(request, cart, created_cookie, "Cart item updated.")

    def delete(self, request, pk):
        cart, created_cookie = self.get_cart(request)
        CartService.remove_item(cart, pk)
        return self.cart_response(request, cart, created_cookie, "Cart item removed.")
