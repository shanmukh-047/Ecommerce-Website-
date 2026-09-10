from django.urls import path

from .staff_dashboard_view import StaffDashboardView
from .views import WholesaleVerificationView

app_name = "staff"

urlpatterns = [
    # Admin / Staff Dashboard Stats
    path("dashboard/", StaffDashboardView.as_view(), name="staff-dashboard"),
    # B2B Wholesale KYC Verification
    path(
        "wholesale/<uuid:pk>/verify/", WholesaleVerificationView.as_view(), name="wholesale-verify"
    ),
]

