from apps.payments.models import PaymentGateway

from .base import PaymentGatewayInterface
from .razorpay_gateway import RazorpayGateway


def get_payment_gateway(gateway_type: str = PaymentGateway.RAZORPAY) -> PaymentGatewayInterface:
    """
    Factory resolving concrete payment gateway adapter based on configured gateway provider.
    """
    if gateway_type == PaymentGateway.RAZORPAY:
        return RazorpayGateway()
    # Fallback to RazorpayGateway as primary provider
    return RazorpayGateway()
