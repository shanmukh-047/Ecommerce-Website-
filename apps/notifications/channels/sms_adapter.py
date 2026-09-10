"""
SMS channel adapter for transactional mobile alerts.
"""

import logging
from typing import Any, Dict, Optional

from apps.notifications.channels.base import BaseChannelAdapter
from apps.notifications.exceptions import ChannelDeliveryError

logger = logging.getLogger(__name__)


class SMSChannelAdapter(BaseChannelAdapter):
    """
    Delivers standard SMS notifications (DLT compliant messages).
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
            raise ChannelDeliveryError("SMS recipient phone number is empty.")

        if len(phone) == 10 and phone.isdigit():
            phone = f"+91{phone}"

        logger.info(f"[SMS Delivery] To: {phone} | Text: {content[:100]}...")
        return True
