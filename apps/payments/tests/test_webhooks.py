import json

from django.test import TestCase

from apps.inventory.models import ReservationStatus, StockReservation
from apps.orders.models import OrderStatus
from apps.payments.exceptions import PaymentVerificationError
from apps.payments.models import (
    PaymentStatus,
    PaymentWebhookEvent,
)
from apps.payments.services import PaymentService, WebhookService
from apps.payments.tests.factories import (
    create_payment_order,
    generate_valid_webhook_signature,
)


class PaymentWebhookTests(TestCase):
    def setUp(self):
        self.order = create_payment_order(variant_suffix="whk")
        self.user = self.order.user
        self.payment, _ = PaymentService.initiate_payment(self.order, self.user)

    def test_payment_captured_webhook_success(self):
        payload = {
            "entity": "event",
            "account_id": "acc_12345",
            "event": "payment.captured",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_whk_capture_999",
                        "entity": "payment",
                        "amount": int(self.payment.amount * 100),
                        "currency": "INR",
                        "status": "captured",
                        "order_id": self.payment.gateway_order_id,
                        "method": "upi",
                    }
                }
            },
            "created_at": 1725624000,
        }
        raw_body = json.dumps(payload).encode("utf-8")
        signature = generate_valid_webhook_signature(raw_body)

        event = WebhookService.process_razorpay_webhook(raw_body, signature)

        self.assertIsNotNone(event)
        self.assertTrue(event.processed)
        self.assertEqual(event.event_type, "payment.captured")

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.CAPTURED)
        self.assertEqual(self.payment.gateway_payment_id, "pay_whk_capture_999")

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.CONFIRMED)
        self.assertIsNotNone(self.order.paid_at)

        res = StockReservation.objects.get(reference_id=self.order.id)
        self.assertEqual(res.status, ReservationStatus.CONSUMED)

    def test_webhook_deduplication_idempotency(self):
        payload = {
            "id": "evt_unique_dedup_001",
            "entity": "event",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_whk_dedup_001",
                        "amount": int(self.payment.amount * 100),
                        "order_id": self.payment.gateway_order_id,
                    }
                }
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        signature = generate_valid_webhook_signature(raw_body)

        event_1 = WebhookService.process_razorpay_webhook(raw_body, signature)
        event_2 = WebhookService.process_razorpay_webhook(raw_body, signature)

        self.assertEqual(event_1.id, event_2.id)
        self.assertEqual(
            PaymentWebhookEvent.objects.filter(event_id="evt_unique_dedup_001").count(), 1
        )

    def test_webhook_invalid_signature_raises_error(self):
        raw_body = b'{"event": "payment.captured"}'
        with self.assertRaises(PaymentVerificationError):
            WebhookService.process_razorpay_webhook(raw_body, "invalid_sig")

    def test_payment_failed_webhook_records_attempt(self):
        payload = {
            "entity": "event",
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_fail_001",
                        "order_id": self.payment.gateway_order_id,
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_description": "Payment was declined by issuing bank",
                    }
                }
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        signature = generate_valid_webhook_signature(raw_body)

        event = WebhookService.process_razorpay_webhook(raw_body, signature)
        self.assertTrue(event.processed)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.FAILED)
        self.assertEqual(self.payment.failure_reason, "Payment was declined by issuing bank")

        # Order must remain PENDING_PAYMENT
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.PENDING_PAYMENT)

        # Reservations remain ACTIVE for retries
        res = StockReservation.objects.get(reference_id=self.order.id)
        self.assertEqual(res.status, ReservationStatus.ACTIVE)

    def test_webhook_after_frontend_verify_is_idempotent(self):
        from apps.payments.tests.factories import generate_valid_signature

        # 1. Customer frontend verify captures payment
        sig = generate_valid_signature(self.payment.gateway_order_id, "pay_front_capture_001")
        PaymentService.verify_and_capture_payment(
            order_id=self.order.id,
            razorpay_order_id=self.payment.gateway_order_id,
            razorpay_payment_id="pay_front_capture_001",
            razorpay_signature=sig,
            user=self.user,
        )

        # 2. Razorpay webhook fires subsequently for the same captured payment
        payload = {
            "id": "evt_late_whk_001",
            "entity": "event",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_front_capture_001",
                        "amount": int(self.payment.amount * 100),
                        "order_id": self.payment.gateway_order_id,
                    }
                }
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        signature = generate_valid_webhook_signature(raw_body)

        event = WebhookService.process_razorpay_webhook(raw_body, signature)
        self.assertTrue(event.processed)

        # Payment remains CAPTURED and order CONFIRMED
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.CAPTURED)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.CONFIRMED)

    def test_webhook_missing_signature_header_returns_400(self):
        from django.urls import reverse
        from rest_framework import status
        from rest_framework.test import APIClient

        client = APIClient()
        url = reverse("payments:razorpay-webhook")
        res = client.post(
            url,
            data=b'{"event":"test"}',
            content_type="application/json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_webhook_payment_captured_after_order_failed_reconciliation(self):
        from apps.orders.services import OrderStateMachine

        # Expire reservation and fail order
        res = StockReservation.objects.get(reference_id=self.order.id)
        res.status = ReservationStatus.EXPIRED
        res.save()

        OrderStateMachine.transition_status(
            self.order,
            OrderStatus.FAILED,
            actor=None,
            notes="Order abandoned due to reservation expiry",
        )

        payload = {
            "id": "evt_late_post_expiry_001",
            "entity": "event",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_late_capture_001",
                        "amount": int(self.payment.amount * 100),
                        "order_id": self.payment.gateway_order_id,
                    }
                }
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        signature = generate_valid_webhook_signature(raw_body)

        event = WebhookService.process_razorpay_webhook(raw_body, signature)
        self.assertTrue(event.processed)

        # 1. Order remains FAILED (never changed to CONFIRMED)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.FAILED)

        # 2. Reservation remains EXPIRED (never consumed)
        res.refresh_from_db()
        self.assertEqual(res.status, ReservationStatus.EXPIRED)

        # 3. Payment captured info preserved but flagged for reconciliation
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.CAPTURED)
        self.assertEqual(self.payment.gateway_payment_id, "pay_late_capture_001")
        self.assertIn("RECONCILIATION_REQUIRED", self.payment.failure_reason)
