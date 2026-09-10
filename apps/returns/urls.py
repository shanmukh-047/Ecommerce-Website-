from django.urls import path

from apps.returns.views import (
    CustomerOrderReturnCancelView,
    CustomerOrderReturnDetailView,
    CustomerOrderReturnListCreateView,
)

app_name = "returns"

urlpatterns = [
    path(
        "<uuid:order_id>/returns/",
        CustomerOrderReturnListCreateView.as_view(),
        name="order-returns-list-create",
    ),
    path(
        "<uuid:order_id>/returns/<uuid:id>/",
        CustomerOrderReturnDetailView.as_view(),
        name="order-returns-detail",
    ),
    path(
        "<uuid:order_id>/returns/<uuid:id>/cancel/",
        CustomerOrderReturnCancelView.as_view(),
        name="order-returns-cancel",
    ),
]
