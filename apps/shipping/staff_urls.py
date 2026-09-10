from django.urls import path

from apps.shipping.staff_views import (
    StaffOrderFulfillmentSummaryView,
    StaffOrderShipmentCreateView,
    StaffShipmentCancelView,
    StaffShipmentDetailView,
    StaffShipmentLabelGenerateView,
    StaffShipmentListView,
    StaffShipmentStatusUpdateView,
)

app_name = "staff-shipping"

urlpatterns = [
    path("", StaffShipmentListView.as_view(), name="staff-shipment-list"),
    path("<uuid:shipment_id>/", StaffShipmentDetailView.as_view(), name="staff-shipment-detail"),
    path(
        "<uuid:shipment_id>/status/",
        StaffShipmentStatusUpdateView.as_view(),
        name="staff-shipment-status-update",
    ),
    path(
        "<uuid:shipment_id>/label/",
        StaffShipmentLabelGenerateView.as_view(),
        name="staff-shipment-label",
    ),
    path(
        "<uuid:shipment_id>/cancel/",
        StaffShipmentCancelView.as_view(),
        name="staff-shipment-cancel",
    ),
    path(
        "orders/<uuid:order_id>/shipments/",
        StaffOrderShipmentCreateView.as_view(),
        name="staff-order-shipment-create",
    ),
    path(
        "orders/<uuid:order_id>/fulfillment-summary/",
        StaffOrderFulfillmentSummaryView.as_view(),
        name="staff-order-fulfillment-summary",
    ),
]
