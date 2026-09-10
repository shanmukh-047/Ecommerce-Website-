import json

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.orders.models import OrderStatus
from apps.orders.tests.factories import create_order_user
from apps.payments.models import PaymentStatus
from apps.payments.services import PaymentService
from apps.payments.tests.factories import (
    create_payment_order,
    generate_valid_signature,
    generate_valid_webhook_signature,
)


class CustomerPaymentAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.order = create_payment_order(variant_suffix="api")
        self.user = self.order.user

    def test_initiate_payment_unauthenticated(self):
        url = reverse("payments:initiate", kwargs={"order_id": self.order.id})
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_initiate_payment_success(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("payments:initiate", kwargs={"order_id": self.order.id})
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("payment", res.data)
        self.assertIn("gateway", res.data)
        self.assertEqual(res.data["payment"]["status"], PaymentStatus.PENDING)
        self.assertTrue(res.data["gateway"]["gateway_order_id"].startswith("order_"))

    def test_initiate_payment_idor_prevention(self):
        other_user = create_order_user(email="other_api@example.com", phone="9876543290")
        self.client.force_authenticate(user=other_user)
        url = reverse("payments:initiate", kwargs={"order_id": self.order.id})
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_verify_payment_success(self):
        payment, _ = PaymentService.initiate_payment(self.order, self.user)
        order_id = payment.gateway_order_id
        payment_id = "pay_test_api_success"
        signature = generate_valid_signature(order_id, payment_id)

        self.client.force_authenticate(user=self.user)
        url = reverse("payments:verify", kwargs={"order_id": self.order.id})
        payload = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        }
        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["payment"]["status"], PaymentStatus.CAPTURED)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.CONFIRMED)

    def test_verify_payment_invalid_signature_error(self):
        payment, _ = PaymentService.initiate_payment(self.order, self.user)
        self.client.force_authenticate(user=self.user)
        url = reverse("payments:verify", kwargs={"order_id": self.order.id})
        payload = {
            "razorpay_order_id": payment.gateway_order_id,
            "razorpay_payment_id": "pay_fake",
            "razorpay_signature": "invalid_signature",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_payment_detail_success_and_idor(self):
        payment, _ = PaymentService.initiate_payment(self.order, self.user)
        url = reverse("payments:detail", kwargs={"order_id": self.order.id})

        # Owner gets 200
        self.client.force_authenticate(user=self.user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["payment"]["id"], str(payment.id))

        # Other user gets 404
        other_user = create_order_user(email="other_det@example.com", phone="9876543289")
        self.client.force_authenticate(user=other_user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_payment_detail_multiple_payments_returns_latest(self):
        # Order with multiple payments (e.g. online initiated then COD) must not crash with MultipleObjectsReturned
        payment1, _ = PaymentService.initiate_payment(self.order, self.user)
        payment2 = PaymentService.create_cod_payment(order=self.order, user=self.user)

        self.client.force_authenticate(user=self.user)
        url = reverse("payments:detail", kwargs={"order_id": self.order.id})
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Should return the latest created payment (payment2)
        self.assertEqual(res.data["payment"]["id"], str(payment2.id))
        self.assertEqual(res.data["payment"]["payment_method"], "COD")

    def test_payment_detail_no_payment_returns_404(self):
        # Order with no payments returns 404 cleanly
        self.client.force_authenticate(user=self.user)
        url = reverse("payments:detail", kwargs={"order_id": self.order.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_razorpay_webhook_endpoint_public_authenticated_by_signature(self):
        payment, _ = PaymentService.initiate_payment(self.order, self.user)
        payload = {
            "id": "evt_api_test_001",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_api_webhook_capture",
                        "order_id": payment.gateway_order_id,
                        "amount": int(payment.amount * 100),
                    }
                }
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        signature = generate_valid_webhook_signature(raw_body)

        url = reverse("payments:razorpay-webhook")
        res = self.client.post(
            url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=signature,
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "processed")

    def test_initiate_payment_cannot_override_amount(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("payments:initiate", kwargs={"order_id": self.order.id})
        res = self.client.post(url, {"amount": 1.00}, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # Server-authoritative: amount must equal order.grand_total, ignoring client input
        self.assertEqual(res.data["payment"]["amount"], str(self.order.grand_total))

    def test_initiate_payment_already_confirmed_order_returns_409(self):
        from apps.orders.services import OrderStateMachine

        OrderStateMachine.transition_status(
            self.order,
            OrderStatus.CONFIRMED,
            actor=self.user,
            notes="Confirmed order test",
        )
        self.client.force_authenticate(user=self.user)
        url = reverse("payments:initiate", kwargs={"order_id": self.order.id})
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    def test_verify_payment_after_webhook_is_idempotent(self):
        from apps.payments.services import WebhookService

        payment, _ = PaymentService.initiate_payment(self.order, self.user)
        whk_payload = {
            "entity": "event",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_whk_then_api",
                        "order_id": payment.gateway_order_id,
                        "amount": int(payment.amount * 100),
                    }
                }
            },
        }
        raw_body = json.dumps(whk_payload).encode("utf-8")
        sig = generate_valid_webhook_signature(raw_body)
        WebhookService.process_razorpay_webhook(raw_body, sig)

        # Now client calls verify
        self.client.force_authenticate(user=self.user)
        url = reverse("payments:verify", kwargs={"order_id": self.order.id})
        payload = {
            "razorpay_order_id": payment.gateway_order_id,
            "razorpay_payment_id": "pay_whk_then_api",
            "razorpay_signature": generate_valid_signature(
                payment.gateway_order_id, "pay_whk_then_api"
            ),
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["payment"]["status"], PaymentStatus.CAPTURED)

    def test_verify_payment_expired_reservation_returns_409(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.inventory.models import StockReservation

        payment, _ = PaymentService.initiate_payment(self.order, self.user)
        res_record = StockReservation.objects.get(reference_id=self.order.id)
        res_record.expires_at = timezone.now() - timedelta(minutes=2)
        res_record.save()

        self.client.force_authenticate(user=self.user)
        url = reverse("payments:verify", kwargs={"order_id": self.order.id})
        payload = {
            "razorpay_order_id": payment.gateway_order_id,
            "razorpay_payment_id": "pay_expired_rev",
            "razorpay_signature": generate_valid_signature(
                payment.gateway_order_id, "pay_expired_rev"
            ),
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
