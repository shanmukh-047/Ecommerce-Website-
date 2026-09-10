from django.urls import path

from apps.shipping.views import (
    CustomerOrderTrackingView,
    CustomerShipmentDetailView,
    PublicAwbTrackingView,
)

app_name = "shipping"

urlpatterns = [
    path("track/", PublicAwbTrackingView.as_view(), name="public-tracking"),
    path(
        "orders/<uuid:order_id>/tracking/",
        CustomerOrderTrackingView.as_view(),
        name="order-tracking",
    ),
    path("<str:shipment_number>/", CustomerShipmentDetailView.as_view(), name="shipment-detail"),
]
