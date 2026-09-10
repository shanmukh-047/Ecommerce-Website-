"""
Staff URLs for notification logs.
"""

from django.urls import path

from apps.notifications.staff_views import (
    StaffNotificationLogDetailView,
    StaffNotificationLogListView,
    StaffResendNotificationView,
)

app_name = "staff_notifications"

urlpatterns = [
    path("", StaffNotificationLogListView.as_view(), name="notification-list"),
    path(
        "<uuid:id>/",
        StaffNotificationLogDetailView.as_view(),
        name="notification-detail",
    ),
    path(
        "<uuid:id>/resend/",
        StaffResendNotificationView.as_view(),
        name="notification-resend",
    ),
]
