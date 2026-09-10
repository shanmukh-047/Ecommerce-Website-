from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.inventory.models import ReservationStatus, StockItem, StockReservation
from apps.orders.models import OrderStatus
from apps.orders.services import OrderStateMachine
from apps.orders.tests.factories import create_order_user
from apps.payments.exceptions import PaymentConflict, PaymentVerificationError
from apps.payments.models import (
    Payment,
    PaymentStatus,
)
from apps.payments.services import PaymentService
from apps.payments.tests.factories import (
    create_payment_order,
    generate_valid_signature,
)


class PaymentServiceTests(TestCase):
    def setUp(self):
        self.order = create_payment_order(variant_suffix="svc")
        self.user = self.order.user

    def test_initiate_payment_success(self):
        payment, gateway_order = PaymentService.initiate_payment(
            order=self.order,
            user=self.user,
        )

        self.assertIsNotNone(payment)
        self.assertTrue(payment.payment_number.startswith("PAY-"))
        self.assertEqual(payment.order, self.order)
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.status, PaymentStatus.PENDING)
        self.assertEqual(payment.amount, self.order.grand_total)
        self.assertTrue(payment.gateway_order_id.startswith("order_"))

        # Check attempt logged
        self.assertEqual(payment.attempts.count(), 1)
        self.assertEqual(payment.attempts.first().status, PaymentStatus.PENDING)

    def test_initiate_payment_reuses_existing_pending_payment(self):
        payment_1, gateway_1 = PaymentService.initiate_payment(self.order, self.user)
        payment_2, gateway_2 = PaymentService.initiate_payment(self.order, self.user)

        self.assertEqual(payment_1.id, payment_2.id)
        self.assertEqual(payment_1.gateway_order_id, payment_2.gateway_order_id)
        self.assertEqual(Payment.objects.filter(order=self.order).count(), 1)

    def test_initiate_payment_idor_rejected(self):
        other_user = create_order_user(email="other_pay@example.com", phone="9876543292")
        with self.assertRaises(PaymentConflict) as ctx:
            PaymentService.initiate_payment(self.order, other_user)
        self.assertIn("permission", str(ctx.exception))

    def test_initiate_payment_rejected_for_cancelled_order(self):
        OrderStateMachine.cancel_order(self.order, actor=self.user, reason="Cancelled")
        with self.assertRaises(PaymentConflict) as ctx:
            PaymentService.initiate_payment(self.order, self.user)
        self.assertIn("cannot be paid", str(ctx.exception))

    def test_initiate_payment_rejected_when_reservations_expired(self):
        # Manually expire reservation
        res = StockReservation.objects.filter(reference_id=self.order.id).first()
        res.expires_at = timezone.now() - timedelta(minutes=5)
        res.save()

        with self.assertRaises(PaymentConflict) as ctx:
            PaymentService.initiate_payment(self.order, self.user)
        self.assertIn("expired", str(ctx.exception))

    def test_verify_and_capture_payment_success(self):
        payment, gateway_order = PaymentService.initiate_payment(self.order, self.user)
        razorpay_order_id = payment.gateway_order_id
        razorpay_payment_id = "pay_live123456"
        signature = generate_valid_signature(razorpay_order_id, razorpay_payment_id)

        # Pre-capture state
        line = self.order.lines.first()
        stock = StockItem.objects.get(variant=line.variant)
        qty_on_hand_before = stock.quantity_on_hand
        qty_reserved_before = stock.quantity_reserved

        # Verify and capture
        captured_payment = PaymentService.verify_and_capture_payment(
            order_id=self.order.id,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=signature,
            user=self.user,
        )

        self.assertEqual(captured_payment.status, PaymentStatus.CAPTURED)
        self.assertEqual(captured_payment.gateway_payment_id, razorpay_payment_id)
        self.assertIsNotNone(captured_payment.captured_at)

        # Order state
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.CONFIRMED)
        self.assertIsNotNone(self.order.paid_at)

        # Reservation state
        res = StockReservation.objects.get(reference_id=self.order.id)
        self.assertEqual(res.status, ReservationStatus.CONSUMED)

        # Stock quantity decremented
        stock.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, qty_on_hand_before - line.quantity)
        self.assertEqual(stock.quantity_reserved, qty_reserved_before - line.quantity)

        # Audit attempt logged
        self.assertTrue(captured_payment.attempts.filter(status=PaymentStatus.CAPTURED).exists())

    def test_verify_and_capture_idempotency(self):
        payment, gateway_order = PaymentService.initiate_payment(self.order, self.user)
        razorpay_order_id = payment.gateway_order_id
        razorpay_payment_id = "pay_idem123456"
        signature = generate_valid_signature(razorpay_order_id, razorpay_payment_id)

        # First capture
        captured_1 = PaymentService.verify_and_capture_payment(
            order_id=self.order.id,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=signature,
            user=self.user,
        )

        line = self.order.lines.first()
        stock = StockItem.objects.get(variant=line.variant)
        stock_on_hand = stock.quantity_on_hand

        # Second capture (e.g. duplicate request)
        captured_2 = PaymentService.verify_and_capture_payment(
            order_id=self.order.id,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=signature,
            user=self.user,
        )

        self.assertEqual(captured_1.id, captured_2.id)
        self.assertEqual(captured_2.status, PaymentStatus.CAPTURED)

        # Stock is NOT double decremented
        stock.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, stock_on_hand)

    def test_verify_and_capture_invalid_signature_records_failure(self):
        payment, gateway_order = PaymentService.initiate_payment(self.order, self.user)
        razorpay_order_id = payment.gateway_order_id
        razorpay_payment_id = "pay_fraud123"

        with self.assertRaises(PaymentVerificationError):
            PaymentService.verify_and_capture_payment(
                order_id=self.order.id,
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature="forged_signature",
                user=self.user,
            )

        # Order must NOT be confirmed
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.PENDING_PAYMENT)

        # Reservation remains ACTIVE
        res = StockReservation.objects.get(reference_id=self.order.id)
        self.assertEqual(res.status, ReservationStatus.ACTIVE)

        # Failed attempt recorded in database
        self.assertTrue(
            payment.attempts.filter(
                status=PaymentStatus.FAILED,
                error_code="SIGNATURE_VERIFICATION_FAILED",
            ).exists()
        )

    def test_verify_and_capture_payment_with_expired_reservation_raises_conflict(self):
        payment, _ = PaymentService.initiate_payment(self.order, self.user)
        razorpay_order_id = payment.gateway_order_id
        razorpay_payment_id = "pay_exp123"
        signature = generate_valid_signature(razorpay_order_id, razorpay_payment_id)

        # Expire the reservation post-initiation
        res = StockReservation.objects.get(reference_id=self.order.id)
        res.expires_at = timezone.now() - timedelta(minutes=1)
        res.save()

        with self.assertRaises(PaymentConflict) as ctx:
            PaymentService.verify_and_capture_payment(
                order_id=self.order.id,
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature=signature,
                user=self.user,
            )
        self.assertIn("expired", str(ctx.exception).lower())

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.PENDING_PAYMENT)
        self.assertIsNone(self.order.paid_at)

    def test_initiate_payment_already_confirmed_order_raises_conflict(self):
        # Confirm order first
        OrderStateMachine.transition_status(
            self.order,
            OrderStatus.CONFIRMED,
            actor=self.user,
            notes="Confirmed prior to payment attempt",
        )
        with self.assertRaises(PaymentConflict) as ctx:
            PaymentService.initiate_payment(self.order, self.user)
        self.assertIn("cannot be paid", str(ctx.exception).lower())

    def test_verify_and_capture_webhook_then_frontend_verify_idempotent(self):
        import json

        from apps.payments.services import WebhookService
        from apps.payments.tests.factories import generate_valid_webhook_signature

        payment, _ = PaymentService.initiate_payment(self.order, self.user)
        payload = {
            "entity": "event",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_whk_first_123",
                        "amount": int(payment.amount * 100),
                        "order_id": payment.gateway_order_id,
                    }
                }
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        sig = generate_valid_webhook_signature(raw_body)
        WebhookService.process_razorpay_webhook(raw_body, sig)

        # Now simulate customer frontend verification arriving after webhook
        frontend_sig = generate_valid_signature(payment.gateway_order_id, "pay_whk_first_123")
        verified_payment = PaymentService.verify_and_capture_payment(
            order_id=self.order.id,
            razorpay_order_id=payment.gateway_order_id,
            razorpay_payment_id="pay_whk_first_123",
            razorpay_signature=frontend_sig,
            user=self.user,
        )

        self.assertEqual(verified_payment.status, PaymentStatus.CAPTURED)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.CONFIRMED)
