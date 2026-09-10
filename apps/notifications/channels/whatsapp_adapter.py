"""
WhatsApp channel adapter for customer mobile communications.
"""

import logging
from typing import Any, Dict, Optional

from apps.notifications.channels.base import BaseChannelAdapter
from apps.notifications.exceptions import ChannelDeliveryError

logger = logging.getLogger(__name__)


class WhatsAppChannelAdapter(BaseChannelAdapter):
    """
    Delivers transactional WhatsApp alerts (Order Confirmed, Dispatched, Delivered).
    Operates as mock/log-delivery in development and test environments.
    """

    def send(
        self,
        recipient_target: str,
        subject: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        phone = recipient_target.strip().replace(" ", "").replace("-", "")
        if not phone:
            raise ChannelDeliveryError("WhatsApp recipient phone number is empty.")

        # Ensure Indian country code or international format
        if len(phone) == 10 and phone.isdigit():
            phone = f"+91{phone}"

        logger.info(
            f"[WhatsApp Delivery] To: {phone} | Title: {subject} | " f"Content: {content[:100]}..."
        )
        return True
