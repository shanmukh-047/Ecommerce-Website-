"""
DRF Serializers for notification audit logs.
"""

from rest_framework import serializers

from apps.notifications.models import NotificationLog


class NotificationLogSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    recipient_email = serializers.CharField(source="recipient.email", read_only=True)

    class Meta:
        model = NotificationLog
        fields = [
            "id",
            "recipient",
            "recipient_email",
            "recipient_target",
            "channel",
            "event",
            "order",
            "order_number",
            "status",
            "idempotency_key",
            "subject",
            "content",
            "metadata",
            "error_message",
            "sent_at",
            "retry_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
