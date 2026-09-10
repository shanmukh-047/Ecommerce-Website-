"""
Admin interface registration for apps.notifications domain.
"""

from django.contrib import admin

from apps.notifications.models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "channel",
        "event",
        "recipient_target",
        "order",
        "status",
        "sent_at",
        "retry_count",
        "created_at",
    ]
    list_filter = ["channel", "event", "status", "created_at"]
    search_fields = [
        "recipient_target",
        "order__order_number",
        "idempotency_key",
        "subject",
    ]
    readonly_fields = [
        "id",
        "recipient",
        "recipient_target",
        "channel",
        "event",
        "order",
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
