from django.urls import path

from .views import (
    AddressDetailView,
    AddressListCreateView,
    AddressSetDefaultView,
    ChangePasswordView,
    CustomerRegistrationView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    TokenRefreshView,
    UserProfileView,
    WholesaleRegistrationView,
)

app_name = "auth"

urlpatterns = [
    # Registration & Authentication
    path("register/", CustomerRegistrationView.as_view(), name="register"),
    path("register/wholesale/", WholesaleRegistrationView.as_view(), name="register-wholesale"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # Password Management & Recovery
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    # User Profile
    path("me/", UserProfileView.as_view(), name="me"),
    # Address Book Management
    path("addresses/", AddressListCreateView.as_view(), name="address-list-create"),
    path("addresses/<uuid:pk>/", AddressDetailView.as_view(), name="address-detail"),
    path(
        "addresses/<uuid:pk>/set-default/",
        AddressSetDefaultView.as_view(),
        name="address-set-default",
    ),
]
