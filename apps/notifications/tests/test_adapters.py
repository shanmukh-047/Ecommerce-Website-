"""
Tests for notification channel transport adapters.
"""

from django.core import mail
from django.test import TestCase

from apps.notifications.channels.email_adapter import EmailChannelAdapter
from apps.notifications.channels.factory import get_channel_adapter
from apps.notifications.channels.sms_adapter import SMSChannelAdapter
from apps.notifications.channels.whatsapp_adapter import WhatsAppChannelAdapter
from apps.notifications.exceptions import ChannelDeliveryError
from apps.notifications.models import NotificationChannel


class ChannelAdapterTests(TestCase):
    def test_email_adapter_success(self):
        adapter = EmailChannelAdapter()
        success = adapter.send(
            recipient_target="customer@example.com",
            subject="Order Placed",
            content="<p>Thank you for your order!</p>",
        )
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["customer@example.com"])
        self.assertEqual(mail.outbox[0].subject, "Order Placed")

    def test_email_adapter_invalid_recipient_raises_error(self):
        adapter = EmailChannelAdapter()
        with self.assertRaises(ChannelDeliveryError):
            adapter.send(
                recipient_target="invalid-email",
                subject="Test",
                content="Body",
            )

    def test_whatsapp_adapter_success(self):
        adapter = WhatsAppChannelAdapter()
        success = adapter.send(
            recipient_target="9876543210",
            subject="Order Shipped",
            content="Your order is on the way!",
        )
        self.assertTrue(success)

    def test_whatsapp_adapter_empty_phone_raises_error(self):
        adapter = WhatsAppChannelAdapter()
        with self.assertRaises(ChannelDeliveryError):
            adapter.send(
                recipient_target="",
                subject="Test",
                content="Body",
            )

    def test_sms_adapter_success(self):
        adapter = SMSChannelAdapter()
        success = adapter.send(
            recipient_target="+919876543210",
            subject="OTP",
            content="Your delivery OTP is 123456",
        )
        self.assertTrue(success)

    def test_sms_adapter_empty_phone_raises_error(self):
        adapter = SMSChannelAdapter()
        with self.assertRaises(ChannelDeliveryError):
            adapter.send(
                recipient_target="",
                subject="Test",
                content="Body",
            )

    def test_channel_factory(self):
        self.assertIsInstance(get_channel_adapter(NotificationChannel.EMAIL), EmailChannelAdapter)
        self.assertIsInstance(
            get_channel_adapter(NotificationChannel.WHATSAPP), WhatsAppChannelAdapter
        )
        self.assertIsInstance(get_channel_adapter(NotificationChannel.SMS), SMSChannelAdapter)

        with self.assertRaises(ChannelDeliveryError):
            get_channel_adapter("TELEGRAM")
