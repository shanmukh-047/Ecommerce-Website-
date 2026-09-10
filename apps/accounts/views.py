import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Address, WholesaleProfile
from .permissions import IsManagerOrAdmin, IsOwnerOrAdmin
from .serializers import (
    AddressSerializer,
    ChangePasswordSerializer,
    CustomerRegistrationSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserSerializer,
    UserUpdateSerializer,
    WholesaleProfileSerializer,
    WholesaleRegistrationSerializer,
    WholesaleVerificationSerializer,
)
from .services.auth_service import AuthService

logger = logging.getLogger(__name__)


class AuthRateThrottle(AnonRateThrottle):
    """Specific rate limiter for authentication endpoints to prevent brute-force attacks."""

    scope = "auth"


class CustomerRegistrationView(APIView):
    """Retail customer registration endpoint."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = CustomerRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.register_retail_customer(serializer.validated_data)
        access_token, refresh_token = AuthService.generate_tokens_for_user(user)

        user_data = UserSerializer(user).data
        response = Response(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "user": user_data,
                "_message": "Registration successful. Welcome to Bharath Masala Products!",
            },
            status=status.HTTP_201_CREATED,
        )
        AuthService.set_refresh_cookie(response, refresh_token)
        return response


class WholesaleRegistrationView(APIView):
    """B2B Wholesale customer application endpoint."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = WholesaleRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, profile = AuthService.register_wholesale_customer(serializer.validated_data)
        access_token, refresh_token = AuthService.generate_tokens_for_user(user)

        user_data = UserSerializer(user).data
        response = Response(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "user": user_data,
                "_message": "Wholesale application submitted successfully. Account is pending verification.",
            },
            status=status.HTTP_201_CREATED,
        )
        AuthService.set_refresh_cookie(response, refresh_token)
        return response


class LoginView(APIView):
    """Authentication endpoint returning Access Token and setting HttpOnly Refresh Cookie."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        access_token, refresh_token = AuthService.generate_tokens_for_user(user)
        guest_cart_token = request.COOKIES.get(
            getattr(settings, "GUEST_CART_COOKIE_NAME", "guest_cart_token")
        )
        cart_merge_adjustments = []
        if guest_cart_token:
            # Local import avoids coupling the accounts domain to cart at startup.
            from apps.cart.services import CartService

            _, cart_merge_adjustments = CartService.merge_guest_cart_into_user_cart(
                user, guest_cart_token
            )

        user_data = UserSerializer(user).data
        response = Response(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "user": user_data,
                "cart_merge_adjustments": cart_merge_adjustments,
                "_message": "Login successful.",
            },
            status=status.HTTP_200_OK,
        )
        AuthService.set_refresh_cookie(response, refresh_token)
        if guest_cart_token:
            response.delete_cookie(
                getattr(settings, "GUEST_CART_COOKIE_NAME", "guest_cart_token"),
                path=getattr(settings, "GUEST_CART_COOKIE_PATH", "/api/v1/cart/"),
                domain=getattr(settings, "COOKIE_DOMAIN", None),
            )
        return response


class TokenRefreshView(APIView):
    """
    Token refresh endpoint. Reads refresh token from HttpOnly cookie (or body fallback),
    rotates the token, blacklists the old one, and returns a new Access Token.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        cookie_name = getattr(settings, "JWT_REFRESH_COOKIE_NAME", "refresh_token")
        raw_refresh_token = request.COOKIES.get(cookie_name) or request.data.get("refresh")

        if not raw_refresh_token:
            raise AuthenticationFailed("Refresh token was not provided in cookie or request body.")

        try:
            refresh = RefreshToken(raw_refresh_token)

            # Blacklist old token if enabled
            if settings.SIMPLE_JWT.get("BLACKLIST_AFTER_ROTATION", True):
                try:
                    refresh.blacklist()
                except AttributeError:
                    pass

            # Token rotation: generate new access token and rotate refresh JTI
            refresh.set_jti()
            refresh.set_exp()
            new_access_token = str(refresh.access_token)
            new_refresh_token = refresh

        except TokenError as e:
            logger.warning("Token refresh failed: %s", str(e))
            raise AuthenticationFailed(f"Token is invalid or expired: {str(e)}")

        response = Response(
            {
                "access_token": new_access_token,
                "token_type": "Bearer",
                "_message": "Token refreshed successfully.",
            },
            status=status.HTTP_200_OK,
        )
        AuthService.set_refresh_cookie(response, new_refresh_token)
        return response


class LogoutView(APIView):
    """
    Logout endpoint. Blacklists the submitted refresh token and clears the HttpOnly cookie.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        cookie_name = getattr(settings, "JWT_REFRESH_COOKIE_NAME", "refresh_token")
        raw_refresh_token = request.COOKIES.get(cookie_name) or request.data.get("refresh")

        if raw_refresh_token:
            try:
                refresh = RefreshToken(raw_refresh_token)
                refresh.blacklist()
            except (TokenError, AttributeError):
                # Even if token is already invalid/expired, we still clear the cookie
                pass

        response = Response(
            {"_message": "Successfully logged out."},
            status=status.HTTP_200_OK,
        )
        AuthService.clear_refresh_cookie(response)
        return response


class UserProfileView(APIView):
    """Endpoint for retrieving and updating the authenticated user's profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        full_user_data = UserSerializer(request.user).data
        return Response(
            {
                **full_user_data,
                "_message": "Profile updated successfully.",
            },
            status=status.HTTP_200_OK,
        )


class AddressListCreateView(APIView):
    """List or create saved addresses for the authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        addresses = Address.objects.filter(user=request.user)
        serializer = AddressSerializer(addresses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = AddressSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        address = serializer.save()
        return Response(
            {
                **AddressSerializer(address).data,
                "_message": "Address created successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


class AddressDetailView(APIView):
    """Retrieve, update, or delete a specific address belonging to the user."""

    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_object(self, pk, user):
        # Strict user scoping prevents IDOR
        address = get_object_or_404(Address, pk=pk, user=user)
        self.check_object_permissions(self.request, address)
        return address

    def get(self, request, pk, *args, **kwargs):
        address = self.get_object(pk, request.user)
        serializer = AddressSerializer(address)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk, *args, **kwargs):
        address = self.get_object(pk, request.user)
        serializer = AddressSerializer(
            address, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(
            {
                **AddressSerializer(updated).data,
                "_message": "Address updated successfully.",
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk, *args, **kwargs):
        address = self.get_object(pk, request.user)
        address.delete()
        # Clean 204 No Content
        return Response(status=status.HTTP_204_NO_CONTENT)


class AddressSetDefaultView(APIView):
    """Set an address as default shipping or billing."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        address = get_object_or_404(Address, pk=pk, user=request.user)
        default_type = request.data.get("type", "shipping").lower()

        if default_type == "shipping":
            address.is_default_shipping = True
            address.save()
            msg = "Address set as default shipping."
        elif default_type == "billing":
            address.is_default_billing = True
            address.save()
            msg = "Address set as default billing."
        else:
            raise ValidationError({"type": "Invalid type. Must be 'shipping' or 'billing'."})

        return Response(
            {
                **AddressSerializer(address).data,
                "_message": msg,
            },
            status=status.HTTP_200_OK,
        )


class WholesaleVerificationView(APIView):
    """Staff/Manager endpoint to approve or reject a B2B wholesale profile."""

    permission_classes = [IsManagerOrAdmin]

    def post(self, request, pk, *args, **kwargs):
        profile = get_object_or_404(WholesaleProfile, pk=pk)
        serializer = WholesaleVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        rejection_reason = serializer.validated_data.get("rejection_reason", "")

        updated_profile = AuthService.verify_wholesale_account(
            profile=profile,
            action=action,
            verified_by=request.user,
            rejection_reason=rejection_reason,
        )

        return Response(
            {
                **WholesaleProfileSerializer(updated_profile).data,
                "_message": f"Wholesale profile has been successfully {action.lower()}d.",
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    """
    Initiates password recovery via one-time secure link.
    Strictly protects against email enumeration attacks by returning
    the exact same generic message regardless of email existence.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        AuthService.request_password_reset(email)

        return Response(
            {
                "_message": (
                    "If an account exists for this email address, you will receive "
                    "password reset instructions shortly."
                )
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    Validates token and updates password.
    Tokens are one-time use and immediately invalidated after password update.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        AuthService.confirm_password_reset(uidb64=uid, token=token, new_password=new_password)

        return Response(
            {
                "_message": "Your password has been successfully reset. Please log in with your new password."
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """
    Authenticated endpoint allowing users (customer or staff) to change their password.
    Requires current password verification and validates strength.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        current_password = serializer.validated_data["current_password"]
        new_password = serializer.validated_data["new_password"]

        AuthService.change_password(
            user=request.user,
            current_password=current_password,
            new_password=new_password,
        )

        return Response(
            {"_message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )

