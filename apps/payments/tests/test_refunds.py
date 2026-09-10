"""
Tests for Payment Refund Processing, Gateway Abstraction, Staff API, and Webhooks.
"""

import json
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.orders.models import OrderStatus
from apps.orders.tests.factories import create_order_user, create_staff_user
from apps.payments.exceptions import PaymentConflict
from apps.payments.gateways.razorpay_gateway import RazorpayGateway
from apps.payments.models import PaymentStatus
from apps.payments.services import PaymentService, WebhookService
from apps.payments.tests.factories import (
    create_payment_order,
    generate_valid_signature,
    generate_valid_webhook_signature,
)


class PaymentRefundServiceAndGatewayTests(TestCase):
    def setUp(self):
        self.customer = create_order_user(email="refund_cust@example.com", phone="9876543201")
        self.staff = create_staff_user(email="refund_staff@example.com", phone="9876543202")
        self.order = create_payment_order(user=self.customer, variant_suffix="rfnd")
        self.payment, self.gateway_data = PaymentService.initiate_payment(self.order, self.customer)

        # Capture payment to prepare for refund
        sig = generate_valid_signature(
            order_id=self.payment.gateway_order_id,
            payment_id="pay_test_cap_001",
        )
        self.captured_payment = PaymentService.verify_and_capture_payment(
            order_id=self.order.id,
            razorpay_order_id=self.payment.gateway_order_id,
            razorpay_payment_id="pay_test_cap_001",
            razorpay_signature=sig,
            user=self.customer,
        )

    def test_razorpay_gateway_refund_method(self):
        gateway = RazorpayGateway()
        res = gateway.refund_payment(
            gateway_payment_id="pay_test_cap_001",
            amount=Decimal("150.00"),
            notes={"reason": "Customer cancellation"},
        )
        self.assertTrue(res["id"].startswith("rfnd_"))
        self.assertEqual(res["payment_id"], "pay_test_cap_001")
        self.assertEqual(res["amount"], 15000)  # 150.00 in paise
        self.assertEqual(res["status"], "processed")

    def test_payment_service_full_refund(self):
        refunded = PaymentService.refund_payment(
            payment=self.captured_payment,
            reason="Order cancellation refund",
            actor=self.staff,
        )
        self.assertEqual(refunded.status, PaymentStatus.REFUNDED)
        self.assertEqual(refunded.amount_refunded, self.captured_payment.amount)
        self.assertTrue(refunded.refund_transaction_id.startswith("rfnd_"))
        self.assertIsNotNone(refunded.refunded_at)

        # Order transitions to REFUNDED on full refund
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.REFUNDED)

        # Attempt log record created
        latest_attempt = refunded.attempts.order_by("-attempt_number").first()
        self.assertEqual(latest_attempt.status, PaymentStatus.REFUNDED)

    def test_payment_service_partial_refund(self):
        partial_amount = Decimal("50.00")
        refunded = PaymentService.refund_payment(
            payment=self.captured_payment,
            amount=partial_amount,
            reason="Goodwill discount refund",
            actor=self.staff,
        )
        self.assertEqual(refunded.status, PaymentStatus.PARTIALLY_REFUNDED)
        self.assertEqual(refunded.amount_refunded, partial_amount)

        # Order remains CONFIRMED for partial refund
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.CONFIRMED)

    def test_payment_service_refund_idempotent(self):
        refunded_1 = PaymentService.refund_payment(payment=self.captured_payment)
        refunded_2 = PaymentService.refund_payment(payment=self.captured_payment)
        self.assertEqual(refunded_1.id, refunded_2.id)
        self.assertEqual(refunded_1.status, PaymentStatus.REFUNDED)
        self.assertEqual(refunded_2.status, PaymentStatus.REFUNDED)

    def test_payment_service_refund_rejects_pending_payment(self):
        order2 = create_payment_order(user=self.customer, variant_suffix="rfnd_pending")
        pending_payment, _ = PaymentService.initiate_payment(order2, self.customer)
        with self.assertRaises(PaymentConflict):
            PaymentService.refund_payment(pending_payment)

    def test_payment_service_refund_rejects_invalid_amount(self):
        # Exceeding payment amount
        with self.assertRaises(PaymentConflict):
            PaymentService.refund_payment(
                payment=self.captured_payment,
                amount=self.captured_payment.amount + Decimal("100.00"),
            )

        # Zero or negative amount
        with self.assertRaises(PaymentConflict):
            PaymentService.refund_payment(
                payment=self.captured_payment,
                amount=Decimal("0.00"),
            )


class StaffPaymentRefundAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = create_order_user(email="staff_rf_cust@example.com", phone="9876543203")
        self.staff = create_staff_user(email="staff_rf_staff@example.com", phone="9876543204")
        self.manager = create_order_user(
            email="staff_rf_mgr@example.com", phone="9876543205", role=Role.MANAGER
        )
        self.manager.is_staff = True
        self.manager.save()
        self.order = create_payment_order(user=self.customer, variant_suffix="stf_rf")
        self.payment, _ = PaymentService.initiate_payment(self.order, self.customer)

        sig = generate_valid_signature(
            order_id=self.payment.gateway_order_id,
            payment_id="pay_test_cap_staff",
        )
        self.captured_payment = PaymentService.verify_and_capture_payment(
            order_id=self.order.id,
            razorpay_order_id=self.payment.gateway_order_id,
            razorpay_payment_id="pay_test_cap_staff",
            razorpay_signature=sig,
            user=self.customer,
        )
        self.url = reverse(
            "staff-payments:staff-payment-refund",
            kwargs={"payment_id": self.captured_payment.id},
        )

    def test_staff_refund_rbac(self):
        # Unauthenticated -> 401
        res = self.client.post(self.url, {})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # Customer -> 403
        self.client.force_authenticate(user=self.customer)
        res = self.client.post(self.url, {})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Junior Staff (Role.STAFF) -> 403 Forbidden (RBAC financial protection)
        self.client.force_authenticate(user=self.staff)
        res = self.client.post(self.url, {"reason": "Staff attempt"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Manager (Role.MANAGER) -> 200 OK
        self.client.force_authenticate(user=self.manager)
        res = self.client.post(self.url, {"reason": "Customer cancellation approved by manager"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["payment"]["status"], PaymentStatus.REFUNDED)
        self.assertTrue(bool(res.data["payment"]["refund_transaction_id"]))


class WebhookRefundTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = create_order_user(email="wh_rf_cust@example.com", phone="9876543205")
        self.order = create_payment_order(user=self.customer, variant_suffix="wh_rf")
        self.payment, _ = PaymentService.initiate_payment(self.order, self.customer)

        sig = generate_valid_signature(
            order_id=self.payment.gateway_order_id,
            payment_id="pay_wh_test_001",
        )
        self.captured_payment = PaymentService.verify_and_capture_payment(
            order_id=self.order.id,
            razorpay_order_id=self.payment.gateway_order_id,
            razorpay_payment_id="pay_wh_test_001",
            razorpay_signature=sig,
            user=self.customer,
        )

    def test_webhook_refund_processed(self):
        payload = {
            "entity": "event",
            "event": "refund.processed",
            "id": "evt_refund_processed_001",
            "payload": {
                "refund": {
                    "entity": {
                        "id": "rfnd_webhook_001",
                        "payment_id": "pay_wh_test_001",
                        "amount": int(self.payment.amount * 100),
                        "status": "processed",
                    }
                },
                "payment": {
                    "entity": {
                        "id": "pay_wh_test_001",
                        "order_id": self.payment.gateway_order_id,
                    }
                },
            },
        }
        body = json.dumps(payload).encode("utf-8")
        sig = generate_valid_webhook_signature(body)

        evt = WebhookService.process_razorpay_webhook(raw_body=body, signature=sig)
        self.assertTrue(evt.processed)

        self.captured_payment.refresh_from_db()
        self.assertEqual(self.captured_payment.status, PaymentStatus.REFUNDED)
        self.assertEqual(self.captured_payment.refund_transaction_id, "rfnd_webhook_001")

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.REFUNDED)
