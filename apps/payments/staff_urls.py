from django.urls import path

from .staff_views import (
    StaffPaymentDetailView,
    StaffPaymentListView,
    StaffPaymentMarkCODCollectedView,
    StaffPaymentRefundView,
    StaffPaymentRejectView,
    StaffPaymentVerifyView,
)

app_name = "staff-payments"

urlpatterns = [
    path("", StaffPaymentListView.as_view(), name="staff-payment-list"),
    path("<uuid:payment_id>/", StaffPaymentDetailView.as_view(), name="staff-payment-detail"),
    path(
        "<uuid:payment_id>/verify/",
        StaffPaymentVerifyView.as_view(),
        name="staff-payment-verify",
    ),
    path(
        "<uuid:payment_id>/reject/",
        StaffPaymentRejectView.as_view(),
        name="staff-payment-reject",
    ),
    path(
        "<uuid:payment_id>/refund/",
        StaffPaymentRefundView.as_view(),
        name="staff-payment-refund",
    ),
    path(
        "<uuid:payment_id>/mark-cod-collected/",
        StaffPaymentMarkCODCollectedView.as_view(),
        name="staff-payment-mark-cod-collected",
    ),
]
