"""
Factory for instantiating notification channel adapters.
"""

from apps.notifications.channels.base import BaseChannelAdapter
from apps.notifications.channels.email_adapter import EmailChannelAdapter
from apps.notifications.channels.sms_adapter import SMSChannelAdapter
from apps.notifications.channels.whatsapp_adapter import WhatsAppChannelAdapter
from apps.notifications.exceptions import ChannelDeliveryError
from apps.notifications.models import NotificationChannel


def get_channel_adapter(channel: str) -> BaseChannelAdapter:
    """
    Returns the appropriate adapter instance for the specified communication channel.
    """
    if channel == NotificationChannel.EMAIL:
        return EmailChannelAdapter()
    elif channel == NotificationChannel.WHATSAPP:
        return WhatsAppChannelAdapter()
    elif channel == NotificationChannel.SMS:
        return SMSChannelAdapter()
    else:
        raise ChannelDeliveryError(f"Unsupported notification channel: '{channel}'")
