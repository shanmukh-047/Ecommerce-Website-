"""
Staff management views for inspecting and resending communication logs.
"""

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStaffOrManager
from apps.notifications.models import NotificationLog
from apps.notifications.serializers import NotificationLogSerializer
from apps.notifications.services.notification_service import NotificationService


class StaffNotificationLogListView(generics.ListAPIView):
    """
    GET /api/v1/staff/notifications/
    Lists notification logs with filtering by channel, event, status, and order.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]
    serializer_class = NotificationLogSerializer

    def get_queryset(self):
        queryset = NotificationLog.objects.select_related("recipient", "order").all()

        channel = self.request.query_params.get("channel")
        if channel:
            queryset = queryset.filter(channel=channel.upper())

        event = self.request.query_params.get("event")
        if event:
            queryset = queryset.filter(event=event.upper())

        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param.upper())

        order_number = self.request.query_params.get("order_number")
        if order_number:
            queryset = queryset.filter(order__order_number__icontains=order_number.strip())

        recipient_target = self.request.query_params.get("recipient_target")
        if recipient_target:
            queryset = queryset.filter(recipient_target__icontains=recipient_target.strip())

        return queryset


class StaffNotificationLogDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/staff/notifications/<uuid:id>/
    Retrieves full details of a specific communication log.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]
    serializer_class = NotificationLogSerializer
    queryset = NotificationLog.objects.select_related("recipient", "order")
    lookup_field = "id"


class StaffResendNotificationView(APIView):
    """
    POST /api/v1/staff/notifications/<uuid:id>/resend/
    Re-dispatches a notification log across its transport adapter.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def post(self, request, id):
        log = get_object_or_404(NotificationLog, id=id)
        success = NotificationService.resend(log)
        serializer = NotificationLogSerializer(log)
        return Response(
            {
                "detail": "Notification dispatch attempted.",
                "success": success,
                "notification": serializer.data,
            },
            status=status.HTTP_200_OK if success else status.HTTP_502_BAD_GATEWAY,
        )
