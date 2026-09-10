"""
Models for multi-channel notifications and communication audit trail.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class NotificationChannel(models.TextChoices):
    EMAIL = "EMAIL", "Email"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    SMS = "SMS", "SMS"


class NotificationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    SKIPPED = "SKIPPED", "Skipped"


class NotificationEvent(models.TextChoices):
    ORDER_CONFIRMED = "ORDER_CONFIRMED", "Order Confirmed"
    ORDER_PROCESSING = "ORDER_PROCESSING", "Order Processing"
    ORDER_SHIPPED = "ORDER_SHIPPED", "Order Shipped"
    ORDER_DELIVERED = "ORDER_DELIVERED", "Order Delivered"
    ORDER_CANCELLED = "ORDER_CANCELLED", "Order Cancelled"
    PAYMENT_FAILED = "PAYMENT_FAILED", "Payment Failed"
    REFUND_PROCESSED = "REFUND_PROCESSED", "Refund Processed"
    CREDIT_NOTE_ISSUED = "CREDIT_NOTE_ISSUED", "Credit Note Issued"
    RETURN_REQUESTED = "RETURN_REQUESTED", "Return Requested"
    RETURN_APPROVED = "RETURN_APPROVED", "Return Approved"
    RETURN_REJECTED = "RETURN_REJECTED", "Return Rejected"
    RETURN_PICKUP_SCHEDULED = "RETURN_PICKUP_SCHEDULED", "Return Pickup Scheduled"
    RETURN_RECEIVED = "RETURN_RECEIVED", "Return Received at Warehouse"
    RETURN_COMPLETED = "RETURN_COMPLETED", "Return Completed"


class NotificationLog(TimeStampedModel):
    """
    Immutable audit record for every multi-channel notification triggered across the system.
    Tracks channel, delivery status, payload snapshot, and deduplication keys.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    recipient_target = models.CharField(max_length=255, db_index=True)
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        db_index=True,
    )
    event = models.CharField(
        max_length=50,
        choices=NotificationEvent.choices,
        db_index=True,
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        db_index=True,
    )
    idempotency_key = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
    )
    subject = models.CharField(max_length=255, blank=True, default="")
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    sent_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["channel", "status"]),
            models.Index(fields=["event", "-created_at"]),
            models.Index(fields=["recipient_target", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.channel}] {self.event} -> {self.recipient_target} ({self.status})"

    def mark_sent(self):
        self.status = NotificationStatus.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "sent_at", "updated_at"])

    def mark_failed(self, error: str):
        self.status = NotificationStatus.FAILED
        self.error_message = str(error)
        self.retry_count += 1
        self.save(update_fields=["status", "error_message", "retry_count", "updated_at"])

    def mark_skipped(self, reason: str):
        self.status = NotificationStatus.SKIPPED
        self.error_message = str(reason)
        self.save(update_fields=["status", "error_message", "updated_at"])
