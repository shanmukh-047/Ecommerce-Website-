"""
Abstract base class for notification channel adapters.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseChannelAdapter(ABC):
    """
    Interface for notification channel delivery adapters.
    """

    @abstractmethod
    def send(
        self,
        recipient_target: str,
        subject: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Sends message to recipient_target. Returns True if delivery succeeded.
        Raises ChannelDeliveryError on transport failure.
        """
        pass
