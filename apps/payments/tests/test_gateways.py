from decimal import Decimal

from django.test import TestCase

from apps.payments.gateways import RazorpayGateway, get_payment_gateway
from apps.payments.models import PaymentGateway
from apps.payments.tests.factories import (
    generate_valid_signature,
    generate_valid_webhook_signature,
)


class PaymentGatewayTests(TestCase):
    def setUp(self):
        self.gateway = RazorpayGateway(
            key_id="rzp_test_key123",
            key_secret="secret_key_456",
            webhook_secret="webhook_secret_789",
        )

    def test_factory_resolver(self):
        adapter = get_payment_gateway(PaymentGateway.RAZORPAY)
        self.assertIsInstance(adapter, RazorpayGateway)

    def test_create_order_converts_to_subunits(self):
        order_payload = self.gateway.create_order(
            amount=Decimal("185.50"),
            currency="INR",
            receipt="BMP-20260906-ABCDE",
            notes={"test": "note"},
        )
        self.assertTrue(order_payload["id"].startswith("order_"))
        self.assertEqual(order_payload["amount"], 18550)  # 185.50 * 100 paise
        self.assertEqual(order_payload["currency"], "INR")
        self.assertEqual(order_payload["receipt"], "BMP-20260906-ABCDE")

    def test_verify_payment_signature_valid(self):
        order_id = "order_O12345"
        payment_id = "pay_P67890"
        signature = generate_valid_signature(order_id, payment_id, secret="secret_key_456")

        is_valid = self.gateway.verify_payment_signature(order_id, payment_id, signature)
        self.assertTrue(is_valid)

    def test_verify_payment_signature_invalid_tampered(self):
        order_id = "order_O12345"
        payment_id = "pay_P67890"

        # Tampered signature
        is_valid = self.gateway.verify_payment_signature(
            order_id, payment_id, "forged_signature_hex"
        )
        self.assertFalse(is_valid)

        # Empty values
        self.assertFalse(self.gateway.verify_payment_signature("", payment_id, "sig"))
        self.assertFalse(self.gateway.verify_payment_signature(order_id, "", "sig"))
        self.assertFalse(self.gateway.verify_payment_signature(order_id, payment_id, ""))

    def test_verify_webhook_signature_valid(self):
        raw_body = b'{"event":"payment.captured","id":"evt_123"}'
        signature = generate_valid_webhook_signature(raw_body, secret="webhook_secret_789")

        is_valid = self.gateway.verify_webhook_signature(raw_body, signature)
        self.assertTrue(is_valid)

    def test_verify_webhook_signature_invalid(self):
        raw_body = b'{"event":"payment.captured","id":"evt_123"}'
        self.assertFalse(self.gateway.verify_webhook_signature(raw_body, "tampered_sig"))
        self.assertFalse(self.gateway.verify_webhook_signature(b"", "tampered_sig"))

    def test_fetch_payment(self):
        details = self.gateway.fetch_payment("pay_123")
        self.assertEqual(details["id"], "pay_123")
        self.assertEqual(details["status"], "captured")
