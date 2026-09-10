"""
Email channel adapter using Django's email subsystem.
"""

import logging
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

from apps.notifications.channels.base import BaseChannelAdapter
from apps.notifications.exceptions import ChannelDeliveryError

logger = logging.getLogger(__name__)


class EmailChannelAdapter(BaseChannelAdapter):
    """
    Sends transactional emails via configured Django EMAIL_BACKEND.
    """

    def send(
        self,
        recipient_target: str,
        subject: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if not recipient_target or "@" not in recipient_target:
            raise ChannelDeliveryError(f"Invalid email address: '{recipient_target}'")

        from_email = getattr(
            settings, "DEFAULT_FROM_EMAIL", "Bharath Masala <orders@bharathmasala.com>"
        )

        try:
            # Determine if content is HTML
            is_html = (
                "<html" in content.lower() or "<div" in content.lower() or "<p" in content.lower()
            )
            plain_text = strip_tags(content) if is_html else content

            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_text,
                from_email=from_email,
                to=[recipient_target],
            )
            if is_html:
                msg.attach_alternative(content, "text/html")

            msg.send(fail_silently=False)
            logger.info(f"Successfully sent email to {recipient_target} (Subject: {subject})")
            return True
        except Exception as exc:
            logger.error(f"Failed to send email to {recipient_target}: {exc}", exc_info=True)
            raise ChannelDeliveryError(f"Email delivery failed: {str(exc)}") from exc
