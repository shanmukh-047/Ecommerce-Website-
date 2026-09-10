"""
Tests for apps.notifications models.
"""

from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import User
from apps.notifications.models import (
    NotificationChannel,
    NotificationEvent,
    NotificationLog,
    NotificationStatus,
)


class NotificationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="notify_user@example.com",
            phone_number="+919876543210",
            first_name="Ravi",
            last_name="Shankar",
        )

    def test_notification_log_creation_and_str(self):
        log = NotificationLog.objects.create(
            recipient=self.user,
            recipient_target="notify_user@example.com",
            channel=NotificationChannel.EMAIL,
            event=NotificationEvent.ORDER_CONFIRMED,
            idempotency_key="test-order-1:ORDER_CONFIRMED:EMAIL",
            subject="Order Confirmed",
            content="<p>Order Confirmed</p>",
        )
        self.assertEqual(log.status, NotificationStatus.PENDING)
        self.assertIn("EMAIL", str(log))
        self.assertIn("ORDER_CONFIRMED", str(log))

    def test_mark_sent(self):
        log = NotificationLog.objects.create(
            recipient=self.user,
            recipient_target="notify_user@example.com",
            channel=NotificationChannel.EMAIL,
            event=NotificationEvent.ORDER_CONFIRMED,
            idempotency_key="test-order-2:ORDER_CONFIRMED:EMAIL",
            content="Content",
        )
        log.mark_sent()
        log.refresh_from_db()

        self.assertEqual(log.status, NotificationStatus.SENT)
        self.assertIsNotNone(log.sent_at)

    def test_mark_failed(self):
        log = NotificationLog.objects.create(
            recipient=self.user,
            recipient_target="notify_user@example.com",
            channel=NotificationChannel.EMAIL,
            event=NotificationEvent.ORDER_CONFIRMED,
            idempotency_key="test-order-3:ORDER_CONFIRMED:EMAIL",
            content="Content",
        )
        log.mark_failed("SMTP Connection Timeout")
        log.refresh_from_db()

        self.assertEqual(log.status, NotificationStatus.FAILED)
        self.assertEqual(log.error_message, "SMTP Connection Timeout")
        self.assertEqual(log.retry_count, 1)

    def test_mark_skipped(self):
        log = NotificationLog.objects.create(
            recipient=self.user,
            recipient_target="NOT_CONFIGURED",
            channel=NotificationChannel.SMS,
            event=NotificationEvent.ORDER_CONFIRMED,
            idempotency_key="test-order-4:ORDER_CONFIRMED:SMS",
            content="Content",
        )
        log.mark_skipped("No phone number available")
        log.refresh_from_db()

        self.assertEqual(log.status, NotificationStatus.SKIPPED)
        self.assertEqual(log.error_message, "No phone number available")

    def test_idempotency_key_uniqueness(self):
        NotificationLog.objects.create(
            recipient=self.user,
            recipient_target="notify_user@example.com",
            channel=NotificationChannel.EMAIL,
            event=NotificationEvent.ORDER_CONFIRMED,
            idempotency_key="unique-key-123",
            content="Content",
        )
        with self.assertRaises(IntegrityError):
            NotificationLog.objects.create(
                recipient=self.user,
                recipient_target="notify_user@example.com",
                channel=NotificationChannel.EMAIL,
                event=NotificationEvent.ORDER_CONFIRMED,
                idempotency_key="unique-key-123",
                content="Content",
            )
