import hashlib
import hmac

from django.conf import settings

from apps.accounts.models import Role
from apps.inventory.services import InventoryService
from apps.inventory.tests.factories import create_variant
from apps.orders.models import Order
from apps.orders.services import CheckoutService
from apps.orders.tests.factories import add_to_cart, create_order_address, create_order_user


def create_payment_order(
    user=None,
    email="pay_user@example.com",
    phone="9876543233",
    variant_suffix="pay",
    quantity=2,
) -> Order:
    if not user:
        user = create_order_user(email=email, phone=phone, role=Role.CUSTOMER)
    address = create_order_address(user)
    variant = create_variant(variant_suffix)
    InventoryService.add_stock(variant, 50)
    add_to_cart(user, variant, quantity)
    order = CheckoutService.create_order_from_cart(user, address.id)
    return order


def generate_valid_signature(order_id: str, payment_id: str, secret: str = None) -> str:
    key_secret = secret or getattr(settings, "RAZORPAY_KEY_SECRET", "test_secret_placeholder")
    message = f"{order_id}|{payment_id}"
    return hmac.new(
        key_secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def generate_valid_webhook_signature(raw_body: bytes, secret: str = None) -> str:
    webhook_secret = secret or getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret")
    return hmac.new(
        webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
