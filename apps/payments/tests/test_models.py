from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.payments.models import (
    Payment,
    PaymentAttempt,
    PaymentGateway,
    PaymentStatus,
    PaymentWebhookEvent,
)
from apps.payments.tests.factories import create_payment_order


class PaymentModelTests(TestCase):
    def setUp(self):
        self.order = create_payment_order(variant_suffix="mod1")
        self.user = self.order.user

    def test_payment_creation_and_defaults(self):
        payment = Payment.objects.create(
            payment_number="PAY-TEST-0001",
            order=self.order,
            user=self.user,
            amount=Decimal("180.00"),
            currency="INR",
            gateway=PaymentGateway.RAZORPAY,
            gateway_order_id="order_test123",
        )
        self.assertIsNotNone(payment.id)
        self.assertEqual(payment.status, PaymentStatus.PENDING)
        self.assertEqual(payment.currency, "INR")
        self.assertIn("PAY-TEST-0001", str(payment))

    def test_payment_amount_positive_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Payment.objects.create(
                payment_number="PAY-TEST-ZERO",
                order=self.order,
                user=self.user,
                amount=Decimal("0.00"),
                currency="INR",
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Payment.objects.create(
                payment_number="PAY-TEST-NEG",
                order=self.order,
                user=self.user,
                amount=Decimal("-50.00"),
                currency="INR",
            )

    def test_payment_attempt_creation_and_uniqueness(self):
        payment = Payment.objects.create(
            payment_number="PAY-TEST-ATT",
            order=self.order,
            user=self.user,
            amount=Decimal("180.00"),
            currency="INR",
        )

        attempt_1 = PaymentAttempt.objects.create(
            payment=payment,
            attempt_number=1,
            status=PaymentStatus.FAILED,
            error_code="BAD_REQUEST",
            error_description="Card declined",
        )
        self.assertIn("Attempt #1", str(attempt_1))

        # Duplicate attempt number raises IntegrityError
        with self.assertRaises(IntegrityError), transaction.atomic():
            PaymentAttempt.objects.create(
                payment=payment,
                attempt_number=1,
                status=PaymentStatus.FAILED,
            )

    def test_payment_webhook_event_creation(self):
        event = PaymentWebhookEvent.objects.create(
            provider="RAZORPAY",
            event_id="evt_test_123456",
            event_type="payment.captured",
            payload={"id": "evt_test_123456"},
            signature_verified=True,
        )
        self.assertIsNotNone(event.id)
        self.assertIn("evt_test_123456", str(event))
        self.assertFalse(event.processed)

        # Duplicate event_id raises IntegrityError
        with self.assertRaises(IntegrityError), transaction.atomic():
            PaymentWebhookEvent.objects.create(
                provider="RAZORPAY",
                event_id="evt_test_123456",
                event_type="payment.captured",
            )
