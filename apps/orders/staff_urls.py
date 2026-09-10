from django.urls import path

from .staff_views import StaffOrderDetailView, StaffOrderListView, StaffOrderStatusUpdateView

app_name = "staff-orders"

urlpatterns = [
    path("", StaffOrderListView.as_view(), name="staff-order-list"),
    path("<uuid:pk>/", StaffOrderDetailView.as_view(), name="staff-order-detail"),
    path(
        "<uuid:pk>/status/", StaffOrderStatusUpdateView.as_view(), name="staff-order-status-update"
    ),
]
