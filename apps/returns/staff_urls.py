from django.urls import path

from apps.returns.staff_views import (
    StaffReturnCompleteView,
    StaffReturnDetailView,
    StaffReturnInspectionView,
    StaffReturnListView,
    StaffReturnReviewView,
    StaffReverseShipmentScheduleView,
    StaffReverseShipmentStatusUpdateView,
)

app_name = "staff-returns"

urlpatterns = [
    path("", StaffReturnListView.as_view(), name="staff-returns-list"),
    path("<uuid:id>/", StaffReturnDetailView.as_view(), name="staff-returns-detail"),
    path("<uuid:id>/review/", StaffReturnReviewView.as_view(), name="staff-returns-review"),
    path(
        "<uuid:id>/shipment/schedule/",
        StaffReverseShipmentScheduleView.as_view(),
        name="staff-returns-shipment-schedule",
    ),
    path(
        "<uuid:id>/shipment/status/",
        StaffReverseShipmentStatusUpdateView.as_view(),
        name="staff-returns-shipment-status",
    ),
    path(
        "<uuid:id>/inspection/",
        StaffReturnInspectionView.as_view(),
        name="staff-returns-inspection",
    ),
    path(
        "<uuid:id>/complete/",
        StaffReturnCompleteView.as_view(),
        name="staff-returns-complete",
    ),
]
