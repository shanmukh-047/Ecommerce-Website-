"""
Tests for apps.notifications service layer.
"""

from decimal import Decimal

from django.core import mail
from django.test import TestCase

from apps.accounts.models import IndianStates, User
from apps.catalog.models import Category, Product, ProductVariant
from apps.notifications.models import (
    NotificationChannel,
    NotificationEvent,
    NotificationLog,
    NotificationStatus,
)
from apps.notifications.services.notification_service import NotificationService
from apps.orders.models import Order, OrderLineItem, OrderStatus


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="service_buyer@example.com",
            phone_number="+919876543210",
            first_name="Deepa",
            last_name="Rao",
        )
        self.category = Category.objects.create(name="Spices", slug="spices")
        self.product = Product.objects.create(
            category=self.category,
            name="Garam Masala",
            slug="garam-masala",
            hsn_code="0904",
            gst_rate=Decimal("5.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="100g",
            sku="GARAM-100G",
            weight_in_grams=100,
            mrp=Decimal("95.00"),
            selling_price=Decimal("95.00"),
        )
        self.order = Order.objects.create(
            order_number="BMP-NOTIF-001",
            user=self.user,
            order_status=OrderStatus.CONFIRMED,
            shipping_recipient_name="Deepa Rao",
            shipping_phone_number="+919876543210",
            shipping_address_line_1="10 Main Road",
            shipping_city="Shimoga",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="577201",
            items_subtotal=Decimal("95.00"),
            shipping_fee=Decimal("40.00"),
            grand_total=Decimal("135.00"),
        )
        self.order_line = OrderLineItem.objects.create(
            order=self.order,
            variant=self.variant,
            product_name="Garam Masala",
            variant_name="100g",
            sku="GARAM-100G",
            weight_in_grams=100,
            quantity=1,
            mrp=Decimal("95.00"),
            unit_price=Decimal("95.00"),
            line_subtotal=Decimal("95.00"),
        )

    def test_send_order_notifications_multi_channel(self):
        logs = NotificationService.send_order_notifications(
            order=self.order,
            event=NotificationEvent.ORDER_CONFIRMED,
        )

        self.assertEqual(len(logs), 3)
        channels = {log.channel for log in logs}
        self.assertEqual(
            channels,
            {
                NotificationChannel.EMAIL,
                NotificationChannel.WHATSAPP,
                NotificationChannel.SMS,
            },
        )

        for log in logs:
            self.assertEqual(log.status, NotificationStatus.SENT)
            self.assertIsNotNone(log.sent_at)

        # Ensure email was actually queued in Django test outbox
        self.assertTrue(len(mail.outbox) >= 1)
        email_msg = mail.outbox[0]
        self.assertEqual(email_msg.to, ["service_buyer@example.com"])
        self.assertIn("BMP-NOTIF-001", email_msg.subject)

    def test_deduplication_skips_duplicate_dispatches(self):
        NotificationService.send_order_notifications(
            order=self.order,
            event=NotificationEvent.ORDER_CONFIRMED,
        )
        initial_count = NotificationLog.objects.count()
        self.assertEqual(initial_count, 3)

        # Subsequent call with same order and event
        logs2 = NotificationService.send_order_notifications(
            order=self.order,
            event=NotificationEvent.ORDER_CONFIRMED,
        )
        self.assertEqual(NotificationLog.objects.count(), 3)
        self.assertEqual(len(logs2), 3)

    def test_graceful_handling_missing_recipient_contact(self):
        user_empty_email = User.objects.create_user(
            email="temp@example.com",
            phone_number="+919999999999",
            first_name="No",
            last_name="Email",
        )
        user_empty_email.email = ""
        user_empty_email.save(update_fields=["email"])

        order = Order.objects.create(
            order_number="BMP-NO-EMAIL",
            user=user_empty_email,
            order_status=OrderStatus.CONFIRMED,
            shipping_recipient_name="No Email",
            shipping_phone_number="",
            shipping_address_line_1="Station Road",
            shipping_city="Thirthahalli",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="577432",
            items_subtotal=Decimal("95.00"),
            shipping_fee=Decimal("40.00"),
            grand_total=Decimal("135.00"),
        )
        logs = NotificationService.send_order_notifications(
            order=order,
            event=NotificationEvent.ORDER_CONFIRMED,
            channels=[NotificationChannel.EMAIL],
        )
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].status, NotificationStatus.SKIPPED)

    def test_events_templates_rendering(self):
        events = [
            NotificationEvent.ORDER_SHIPPED,
            NotificationEvent.ORDER_DELIVERED,
            NotificationEvent.ORDER_CANCELLED,
        ]
        for ev in events:
            logs = NotificationService.send_order_notifications(
                order=self.order,
                event=ev,
                channels=[NotificationChannel.EMAIL],
            )
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].status, NotificationStatus.SENT)

    def test_resend_notification(self):
        log = NotificationLog.objects.create(
            recipient=self.user,
            recipient_target="service_buyer@example.com",
            channel=NotificationChannel.EMAIL,
            event=NotificationEvent.ORDER_CONFIRMED,
            idempotency_key="resend-test:ORDER_CONFIRMED:EMAIL",
            subject="Test Resend",
            content="<p>Test Content</p>",
            status=NotificationStatus.FAILED,
        )
        success = NotificationService.resend(log)
        self.assertTrue(success)
        log.refresh_from_db()
        self.assertEqual(log.status, NotificationStatus.SENT)
