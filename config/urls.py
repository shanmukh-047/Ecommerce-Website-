"""
Root URL Configuration for Bharath Masala Products Platform.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.core.views import LivenessCheckView, ReadinessCheckView

urlpatterns = [
    # Administration
    path("admin/", admin.site.urls),
    # Production Health & Readiness Probes (Root and API level)
    path("health/", ReadinessCheckView.as_view(), name="health-check"),
    path("health/liveness/", LivenessCheckView.as_view(), name="liveness-check"),
    path("health/readiness/", ReadinessCheckView.as_view(), name="readiness-check"),
    path("api/health/", ReadinessCheckView.as_view(), name="api-health-check"),
    # API v1 Namespaces
    path("api/v1/auth/", include("apps.accounts.urls", namespace="auth")),
    path("api/v1/staff/", include("apps.accounts.staff_urls", namespace="staff")),
    path("api/v1/catalog/", include("apps.catalog.urls", namespace="catalog")),
    path("api/v1/staff/catalog/", include("apps.catalog.staff_urls", namespace="staff-catalog")),
    path("api/v1/inventory/", include("apps.inventory.urls", namespace="inventory")),
    path("api/v1/cart/", include("apps.cart.urls", namespace="cart")),
    path("api/v1/orders/", include("apps.invoices.urls", namespace="invoices")),
    path("api/v1/orders/", include("apps.returns.urls", namespace="returns")),
    path("api/v1/orders/", include("apps.orders.urls", namespace="orders")),
    path("api/v1/staff/orders/", include("apps.orders.staff_urls", namespace="staff-orders")),
    path("api/v1/payments/", include("apps.payments.urls", namespace="payments")),
    path("api/v1/staff/payments/", include("apps.payments.staff_urls", namespace="staff-payments")),
    path("api/v1/shipping/", include("apps.shipping.urls", namespace="shipping")),
    path("api/v1/staff/shipping/", include("apps.shipping.staff_urls", namespace="staff-shipping")),
    path("api/v1/staff/inventory/", include("apps.inventory.staff_urls", namespace="staff-inventory")),
    path("api/v1/staff/invoices/", include("apps.invoices.staff_urls", namespace="staff-invoices")),
    path("api/v1/staff/returns/", include("apps.returns.staff_urls", namespace="staff-returns")),
    path(
        "api/v1/staff/notifications/",
        include("apps.notifications.staff_urls", namespace="staff-notifications"),
    ),
    # Administrative Aliases (/api/v1/admin/...)
    path("api/v1/admin/", include("apps.accounts.staff_urls", namespace="admin-portal")),
    path("api/v1/admin/catalog/", include("apps.catalog.staff_urls", namespace="admin-catalog")),
    path("api/v1/admin/inventory/", include("apps.inventory.staff_urls", namespace="admin-inventory")),
    path("api/v1/admin/orders/", include("apps.orders.staff_urls", namespace="admin-orders")),
    path("api/v1/admin/payments/", include("apps.payments.staff_urls", namespace="admin-payments")),
    path("api/v1/", include("apps.promotions.urls")),
    # OpenAPI 3.0 Documentation & Swagger UI
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
