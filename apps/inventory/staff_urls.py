from django.urls import path

from .staff_views import StaffInventoryListView, StaffInventoryUpdateView

app_name = "staff-inventory"

urlpatterns = [
    path("", StaffInventoryListView.as_view(), name="staff-inventory-list"),
    path("<uuid:pk>/", StaffInventoryUpdateView.as_view(), name="staff-inventory-update"),
]
