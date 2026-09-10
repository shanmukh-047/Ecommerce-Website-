"""
Comprehensive tests for multi-item partial refunds, financial invariants,
accumulated refunds, and payment statuses (ISSUE-002).
"""

import json
from decimal import Decimal
from unittest.mock import patch

from django.db import models
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import IndianStates, User
from apps.catalog.models import Category, Product, ProductVariant
from apps.orders.models import Order, OrderStatus
from apps.payments.exceptions import PaymentConflict
from apps.payments.models import (
    Payment,
    PaymentGateway,
    PaymentMethod,
    PaymentStatus,
)
from apps.payments.services.payment_service import PaymentService
from apps.payments.services.webhook_service import WebhookService


class PartialRefundServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="refund_tester@bharathmasala.com",
            phone_number="+919876543002",
            first_name="Refund",
            last_name="Tester",
        )
        self.category = Category.objects.create(name="Spices", slug="spices-refund")
        self.product = Product.objects.create(
            category=self.category,
            name="Garam Masala",
            slug="garam-masala-refund",
            hsn_code="0910",
            gst_rate=Decimal("5.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="250g",
            sku="GARAM-250G-REFUND",
            weight_in_grams=250,
            mrp=Decimal("500.00"),
            selling_price=Decimal("500.00"),
        )
        self.order = Order.objects.create(
            order_number=f"BMP-ORD-RFND-{timezone.now().timestamp()}",
            user=self.user,
            order_status=OrderStatus.CONFIRMED,
            items_subtotal=Decimal("1000.00"),
            tax_amount=Decimal("50.00"),
            shipping_fee=Decimal("0.00"),
            grand_total=Decimal("1000.00"),
            currency="INR",
            total_quantity=2,
            shipping_recipient_name="Refund Tester",
            shipping_phone_number="+919876543002",
            shipping_address_line_1="456 Refund Lane",
            shipping_city="Bangalore",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="560001",
        )
        self.payment = Payment.objects.create(
            payment_number=f"BMP-PAY-{timezone.now().timestamp()}",
            order=self.order,
            user=self.user,
            status=PaymentStatus.CAPTURED,
            gateway=PaymentGateway.MANUAL,
            payment_method=PaymentMethod.UPI,
            amount=Decimal("1000.00"),
            amount_refunded=Decimal("0.00"),
            currency="INR",
        )

    def test_first_partial_refund_sets_partially_refunded_status(self):
        """1. First partial refund updates amount_refunded and sets PARTIALLY_REFUNDED."""
        refunded = PaymentService.refund_payment(
            payment=self.payment,
            amount=Decimal("400.00"),
            reason="Return of 1 item",
            actor=self.user,
        )

        self.assertEqual(refunded.status, PaymentStatus.PARTIALLY_REFUNDED)
        self.assertEqual(refunded.amount_refunded, Decimal("400.00"))
        self.assertTrue(refunded.refund_transaction_id)
        self.assertIsNotNone(refunded.refunded_at)

        # Order must remain in current state (NOT fully refunded)
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.order_status, OrderStatus.REFUNDED)

    def test_multiple_partial_refunds_accumulate_correctly(self):
        """2. Multiple partial refunds accumulate: 400 + 300 = 700, remaining in PARTIALLY_REFUNDED."""
        # First refund: 400
        PaymentService.refund_payment(
            payment=self.payment,
            amount=Decimal("400.00"),
            reason="Partial return 1",
            actor=self.user,
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.PARTIALLY_REFUNDED)
        self.assertEqual(self.payment.amount_refunded, Decimal("400.00"))

        # Second refund: 300
        PaymentService.refund_payment(
            payment=self.payment,
            amount=Decimal("300.00"),
            reason="Partial return 2",
            actor=self.user,
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.PARTIALLY_REFUNDED)
        self.assertEqual(self.payment.amount_refunded, Decimal("700.00"))

        # Order still not fully refunded
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.order_status, OrderStatus.REFUNDED)

    def test_final_partial_refund_transitions_to_fully_refunded(self):
        """3. Final refund of remaining balance transitions status to REFUNDED and transitions Order."""
        # 1. Refund 700
        PaymentService.refund_payment(
            payment=self.payment,
            amount=Decimal("700.00"),
            reason="Partial return 1",
            actor=self.user,
        )

        # 2. Refund remaining 300
        PaymentService.refund_payment(
            payment=self.payment,
            amount=Decimal("300.00"),
            reason="Final return 2",
            actor=self.user,
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.REFUNDED)
        self.assertEqual(self.payment.amount_refunded, Decimal("1000.00"))

        # Order transitions to REFUNDED
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.REFUNDED)

    def test_over_refund_prevention(self):
        """4. Refund attempt exceeding remaining refundable balance raises PaymentConflict."""
        # Refund 800
        PaymentService.refund_payment(
            payment=self.payment,
            amount=Decimal("800.00"),
            reason="First large refund",
            actor=self.user,
        )

        # Attempt to refund 300 (800 + 300 = 1100 > 1000)
        with self.assertRaises(PaymentConflict) as ctx:
            PaymentService.refund_payment(
                payment=self.payment,
                amount=Decimal("300.00"),
                reason="Excessive refund attempt",
                actor=self.user,
            )

        self.assertIn("exceeds maximum eligible remaining refund", str(ctx.exception))
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.amount_refunded, Decimal("800.00"))
        self.assertEqual(self.payment.status, PaymentStatus.PARTIALLY_REFUNDED)

    @patch("apps.payments.gateways.razorpay_gateway.RazorpayGateway.verify_webhook_signature")
    def test_duplicate_webhook_deduplication_does_not_double_count(self, mock_verify):
        """5. Duplicate refund webhook events are deduplicated via PaymentAttempt and not double-counted."""
        import json

        mock_verify.return_value = True

        self.payment.gateway = PaymentGateway.RAZORPAY
        self.payment.gateway_payment_id = "pay_test_gateway_123"
        self.payment.gateway_order_id = "order_rzp_123"
        self.payment.save(update_fields=["gateway", "gateway_payment_id", "gateway_order_id"])

        webhook_payload = {
            "event": "refund.processed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_gateway_123",
                        "order_id": "order_rzp_123",
                        "amount": 100000,
                        "status": "captured",
                    }
                },
                "refund": {
                    "entity": {
                        "id": "rfnd_test_single_webhook_456",
                        "payment_id": "pay_test_gateway_123",
                        "amount": 40000,  # 400.00 in subunits
                        "status": "processed",
                    }
                },
            },
        }

        # First webhook arrival
        body1 = json.dumps({"id": "evt_webhook_001", **webhook_payload}).encode("utf-8")
        WebhookService.process_razorpay_webhook(
            raw_body=body1,
            signature="valid_test_signature_1",
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.PARTIALLY_REFUNDED)
        self.assertEqual(self.payment.amount_refunded, Decimal("400.00"))

        # Duplicate webhook arrival with same refund_id but different event_id
        body2 = json.dumps({"id": "evt_webhook_002", **webhook_payload}).encode("utf-8")
        WebhookService.process_razorpay_webhook(
            raw_body=body2,
            signature="valid_test_signature_2",
        )
        self.payment.refresh_from_db()
        # Must still be exactly 400.00, NOT 800.00!
        self.assertEqual(self.payment.amount_refunded, Decimal("400.00"))
        self.assertEqual(self.payment.status, PaymentStatus.PARTIALLY_REFUNDED)

    def test_idempotent_refund_on_already_fully_refunded_payment(self):
        """6. Calling refund on an already fully refunded payment returns cleanly without error."""
        # Fully refund payment
        PaymentService.refund_payment(
            payment=self.payment,
            amount=Decimal("1000.00"),
            reason="Full refund",
            actor=self.user,
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.REFUNDED)

        # Idempotent re-invocation
        res = PaymentService.refund_payment(
            payment=self.payment,
            amount=Decimal("1000.00"),
            reason="Duplicate call",
            actor=self.user,
        )
        self.assertEqual(res.status, PaymentStatus.REFUNDED)
        self.assertEqual(res.amount_refunded, Decimal("1000.00"))

    @patch("apps.payments.gateways.razorpay_gateway.RazorpayGateway.verify_webhook_signature")
    def test_webhook_lock_order_primary_lookup_path(self, mock_verify):
        """7. Primary webhook lookup path (gateway_order_id) strictly locks Order first, Payment second."""
        mock_verify.return_value = True

        self.payment.gateway_order_id = "order_rzp_primary_123"
        self.payment.gateway_payment_id = "pay_rzp_primary_456"
        self.payment.status = PaymentStatus.PENDING
        self.payment.save(update_fields=["gateway_order_id", "gateway_payment_id", "status"])

        self.order.order_status = OrderStatus.PENDING_PAYMENT
        self.order.save(update_fields=["order_status"])

        webhook_payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_rzp_primary_456",
                        "order_id": "order_rzp_primary_123",
                        "amount": 100000,
                        "status": "captured",
                        "method": "upi",
                    }
                }
            },
        }

        lock_order = []
        original_sfu = models.QuerySet.select_for_update

        def spy_sfu(qs, *args, **kwargs):
            lock_order.append(qs.model.__name__)
            return original_sfu(qs, *args, **kwargs)

        body = json.dumps({"id": f"evt_p_{timezone.now().timestamp()}", **webhook_payload}).encode(
            "utf-8"
        )
        with patch.object(models.QuerySet, "select_for_update", side_effect=spy_sfu, autospec=True):
            WebhookService.process_razorpay_webhook(raw_body=body, signature="sig_primary")

        # CRITICAL CONCURRENCY INVARIANT: Order must be locked before Payment
        self.assertEqual(lock_order, ["Order", "Payment"])

    @patch("apps.payments.gateways.razorpay_gateway.RazorpayGateway.verify_webhook_signature")
    def test_webhook_lock_order_fallback_gateway_payment_id(self, mock_verify):
        """8. Fallback webhook lookup path (gateway_payment_id only) strictly locks Order first, Payment second."""
        mock_verify.return_value = True

        self.payment.gateway_order_id = "order_rzp_diff_789"
        self.payment.gateway_payment_id = "pay_rzp_fb_payment_id"
        self.payment.status = PaymentStatus.PENDING
        self.payment.save(update_fields=["gateway_order_id", "gateway_payment_id", "status"])

        webhook_payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_rzp_fb_payment_id",
                        # Missing/empty order_id to trigger gateway_payment_id fallback
                        "order_id": "",
                        "amount": 100000,
                        "status": "captured",
                        "method": "card",
                    }
                }
            },
        }

        lock_order = []
        original_sfu = models.QuerySet.select_for_update

        def spy_sfu(qs, *args, **kwargs):
            lock_order.append(qs.model.__name__)
            return original_sfu(qs, *args, **kwargs)

        body = json.dumps(
            {"id": f"evt_fb_pay_{timezone.now().timestamp()}", **webhook_payload}
        ).encode("utf-8")
        with patch.object(models.QuerySet, "select_for_update", side_effect=spy_sfu, autospec=True):
            WebhookService.process_razorpay_webhook(raw_body=body, signature="sig_fb1")

        self.assertEqual(lock_order, ["Order", "Payment"])

    @patch("apps.payments.gateways.razorpay_gateway.RazorpayGateway.verify_webhook_signature")
    def test_webhook_lock_order_fallback_notes_order_id(self, mock_verify):
        """9. Fallback webhook lookup path via notes.order_id strictly locks Order first, Payment second."""
        mock_verify.return_value = True

        self.payment.gateway_order_id = "order_rzp_old_111"
        self.payment.gateway_payment_id = "pay_rzp_old_222"
        self.payment.status = PaymentStatus.PENDING
        self.payment.save(update_fields=["gateway_order_id", "gateway_payment_id", "status"])

        webhook_payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        # Unknown IDs on payment entity
                        "id": "pay_rzp_unknown_999",
                        "order_id": "order_rzp_unknown_888",
                        "amount": 100000,
                        "status": "captured",
                        "notes": {
                            "order_id": str(self.order.id),
                        },
                    }
                }
            },
        }

        lock_order = []
        original_sfu = models.QuerySet.select_for_update

        def spy_sfu(qs, *args, **kwargs):
            lock_order.append(qs.model.__name__)
            return original_sfu(qs, *args, **kwargs)

        body = json.dumps(
            {"id": f"evt_notes_{timezone.now().timestamp()}", **webhook_payload}
        ).encode("utf-8")
        with patch.object(models.QuerySet, "select_for_update", side_effect=spy_sfu, autospec=True):
            WebhookService.process_razorpay_webhook(raw_body=body, signature="sig_notes")

        self.assertEqual(lock_order, ["Order", "Payment"])

    @patch("apps.payments.gateways.razorpay_gateway.RazorpayGateway.verify_webhook_signature")
    def test_webhook_lock_order_fallback_receipt(self, mock_verify):
        """10. Fallback webhook lookup path via order.receipt strictly locks Order first, Payment second."""
        mock_verify.return_value = True

        self.payment.gateway_order_id = "order_rzp_init_333"
        self.payment.status = PaymentStatus.PENDING
        self.payment.save(update_fields=["gateway_order_id", "status"])

        webhook_payload = {
            "event": "payment.captured",
            "payload": {
                "order": {
                    "entity": {
                        "id": "order_rzp_unknown_555",
                        "receipt": self.order.order_number,
                    }
                },
                "payment": {
                    "entity": {
                        "id": "pay_rzp_rcpt_666",
                        "amount": 100000,
                        "status": "captured",
                    }
                },
            },
        }

        lock_order = []
        original_sfu = models.QuerySet.select_for_update

        def spy_sfu(qs, *args, **kwargs):
            lock_order.append(qs.model.__name__)
            return original_sfu(qs, *args, **kwargs)

        body = json.dumps(
            {"id": f"evt_rcpt_{timezone.now().timestamp()}", **webhook_payload}
        ).encode("utf-8")
        with patch.object(models.QuerySet, "select_for_update", side_effect=spy_sfu, autospec=True):
            WebhookService.process_razorpay_webhook(raw_body=body, signature="sig_rcpt")

        self.assertEqual(lock_order, ["Order", "Payment"])
