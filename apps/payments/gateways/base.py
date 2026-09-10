from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, Optional


class PaymentGatewayInterface(ABC):
    """
    Abstract contract for payment gateway integrations (Razorpay, COD, etc.)
    decoupling provider-specific APIs from core business models and orders.
    """

    @abstractmethod
    def create_order(
        self,
        amount: Decimal,
        currency: str,
        receipt: str,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a payment order at the gateway provider and returns order payload
        including gateway order ID.
        """
        pass

    @abstractmethod
    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:
        """
        Cryptographically validates the HMAC-SHA256 signature returned by the client-side
        checkout modal upon successful user authorization.
        """
        pass

    @abstractmethod
    def verify_webhook_signature(
        self,
        raw_body: bytes,
        signature: str,
    ) -> bool:
        """
        Cryptographically validates the HMAC-SHA256 signature on an incoming gateway webhook.
        """
        pass

    @abstractmethod
    def fetch_payment(self, gateway_payment_id: str) -> Dict[str, Any]:
        """
        Retrieves authoritative payment status and details from the gateway API.
        """
        pass

    @abstractmethod
    def refund_payment(
        self,
        gateway_payment_id: str,
        amount: Optional[Decimal] = None,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Initiates a refund via the payment gateway for a captured payment.
        """
        pass
