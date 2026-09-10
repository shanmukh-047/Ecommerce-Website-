import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import IndianStates, User
from apps.catalog.models import Category, Product, ProductVariant
from apps.inventory.models import StockItem
from apps.orders.models import Order, OrderLineItem, OrderStatus
from apps.returns.exceptions import ReturnConflict, ReturnPolicyViolation
from apps.returns.models import (
    ResolutionType,
    ReturnReason,
    ReturnRequestStatus,
)
from apps.returns.services.return_service import ReturnService


class ReturnRequestTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="ananya@example.com",
            phone_number="+919876543210",
            first_name="Ananya",
            last_name="Hegde",
            password="StrongPassword123!",
        )
        self.client.force_authenticate(user=self.user)

        self.other_user = User.objects.create_user(
            email="shankar@example.com",
            phone_number="+919876543211",
            first_name="Shankar",
            last_name="Bhat",
            password="StrongPassword123!",
        )

        self.category = Category.objects.create(name="Spices", slug="spices")
        self.product = Product.objects.create(
            category=self.category,
            name="Sirsi Cardamom",
            slug="sirsi-cardamom",
            hsn_code="0908",
            gst_rate=Decimal("5.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="250g",
            sku="CARDAMOM-250G",
            weight_in_grams=250,
            mrp=Decimal("550.00"),
            selling_price=Decimal("550.00"),
        )
        self.stock = StockItem.objects.create(
            variant=self.variant,
            quantity_on_hand=100,
            quantity_reserved=0,
        )

    def _create_order(
        self, user=None, order_status=OrderStatus.DELIVERED, delivered_days_ago=1, quantity=3
    ):
        owner = user or self.user
        delivered_at = timezone.now() - datetime.timedelta(days=delivered_days_ago)
        order = Order.objects.create(
            order_number=f"BMP-ORD-{timezone.now().timestamp()}",
            user=owner,
            order_status=order_status,
            items_subtotal=Decimal("550.00") * quantity,
            tax_amount=Decimal("0.00"),
            shipping_fee=Decimal("0.00"),
            grand_total=Decimal("550.00") * quantity,
            currency="INR",
            total_quantity=quantity,
            shipping_recipient_name="Ananya Hegde",
            shipping_phone_number="+919876543210",
            shipping_address_line_1="Near Court",
            shipping_city="Sirsi",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="581401",
            delivered_at=delivered_at if order_status == OrderStatus.DELIVERED else None,
        )
        line = OrderLineItem.objects.create(
            order=order,
            variant=self.variant,
            quantity=quantity,
            mrp=Decimal("550.00"),
            unit_price=Decimal("550.00"),
            line_subtotal=Decimal("550.00") * quantity,
            product_name="Sirsi Cardamom",
            variant_name="250g",
            sku="CARDAMOM-250G",
        )
        return order, line

    def test_customer_can_create_return_request_for_delivered_order(self):
        order, line = self._create_order()
        url = f"/api/v1/orders/{order.id}/returns/"
        payload = {
            "reason": ReturnReason.DAMAGED_IN_TRANSIT,
            "requested_resolution": ResolutionType.REFUND,
            "customer_notes": "Crushed spice tin during transit.",
            "items": [{"order_line_item_id": str(line.id), "quantity": 1}],
            "evidence_urls": [
                {"file_url": "https://cdn.example.com/proof1.jpg", "description": "Crushed lid"}
            ],
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["status"], ReturnRequestStatus.PENDING_REVIEW)
        self.assertEqual(res.data["reason"], ReturnReason.DAMAGED_IN_TRANSIT)
        self.assertEqual(len(res.data["items"]), 1)
        self.assertEqual(res.data["items"][0]["quantity"], 1)
        self.assertEqual(len(res.data["evidence"]), 1)

    def test_cannot_create_return_request_for_non_delivered_order(self):
        order, line = self._create_order(order_status=OrderStatus.SHIPPED)
        url = f"/api/v1/orders/{order.id}/returns/"
        payload = {
            "reason": ReturnReason.DEFECTIVE_QUALITY,
            "items": [{"order_line_item_id": str(line.id), "quantity": 1}],
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("DELIVERED", res.data["detail"])

    def test_return_window_7_days_enforced_strictly(self):
        # 8 days ago exceeds default 7 days
        order, line = self._create_order(delivered_days_ago=8)
        url = f"/api/v1/orders/{order.id}/returns/"
        payload = {
            "reason": ReturnReason.DEFECTIVE_QUALITY,
            "items": [{"order_line_item_id": str(line.id), "quantity": 1}],
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expired", res.data["detail"].lower())

    def test_return_within_7_days_succeeds(self):
        # 6 days ago is within the 7-day policy window
        order, line = self._create_order(delivered_days_ago=6)
        url = f"/api/v1/orders/{order.id}/returns/"
        payload = {
            "reason": ReturnReason.TAMPERED_SEAL,
            "items": [{"order_line_item_id": str(line.id), "quantity": 1}],
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_quantity_exceeding_delivered_is_rejected(self):
        order, line = self._create_order(quantity=2)
        url = f"/api/v1/orders/{order.id}/returns/"
        payload = {
            "reason": ReturnReason.DEFECTIVE_QUALITY,
            "items": [{"order_line_item_id": str(line.id), "quantity": 3}],
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("eligible", res.data["detail"].lower())

    def test_zero_or_negative_quantity_rejected(self):
        order, line = self._create_order(quantity=2)
        url = f"/api/v1/orders/{order.id}/returns/"
        payload = {
            "reason": ReturnReason.DEFECTIVE_QUALITY,
            "items": [{"order_line_item_id": str(line.id), "quantity": 0}],
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_partial_return_quantity_succeeds(self):
        order, line = self._create_order(quantity=5)
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.user,
            items_data=[{"order_line_item_id": line.id, "quantity": 2}],
        )
        self.assertEqual(ret.items.first().quantity, 2)

    def test_subsequent_return_cannot_exceed_remaining_quantity(self):
        order, line = self._create_order(quantity=3)
        # First return 2 units
        ReturnService.create_return_request(
            order_id=order.id,
            user=self.user,
            items_data=[{"order_line_item_id": line.id, "quantity": 2}],
        )
        # Attempt to return 2 more units (only 1 remaining)
        with self.assertRaises(ReturnPolicyViolation):
            ReturnService.create_return_request(
                order_id=order.id,
                user=self.user,
                items_data=[{"order_line_item_id": line.id, "quantity": 2}],
            )

    def test_duplicate_return_request_for_already_requested_quantity_rejected(self):
        order, line = self._create_order(quantity=1)
        ReturnService.create_return_request(
            order_id=order.id,
            user=self.user,
            items_data=[{"order_line_item_id": line.id, "quantity": 1}],
        )
        with self.assertRaises(ReturnPolicyViolation):
            ReturnService.create_return_request(
                order_id=order.id,
                user=self.user,
                items_data=[{"order_line_item_id": line.id, "quantity": 1}],
            )

    def test_evidence_urls_attached_correctly(self):
        order, line = self._create_order(quantity=1)
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.user,
            items_data=[{"order_line_item_id": line.id, "quantity": 1}],
            evidence_urls=[
                {"file_url": "https://img.example.com/1.png", "description": "Broken seal photo"},
                {"file_url": "https://img.example.com/2.png", "description": "Package box photo"},
            ],
        )
        self.assertEqual(ret.evidence.count(), 2)

    def test_customer_idor_prevention_on_create(self):
        order, line = self._create_order(user=self.other_user)
        url = f"/api/v1/orders/{order.id}/returns/"
        payload = {
            "reason": ReturnReason.DEFECTIVE_QUALITY,
            "items": [{"order_line_item_id": str(line.id), "quantity": 1}],
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_idor_prevention_on_list_and_detail(self):
        order, line = self._create_order(user=self.other_user)
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.other_user,
            items_data=[{"order_line_item_id": line.id, "quantity": 1}],
        )
        list_url = f"/api/v1/orders/{order.id}/returns/"
        res_list = self.client.get(list_url)
        self.assertEqual(res_list.status_code, status.HTTP_404_NOT_FOUND)

        detail_url = f"/api/v1/orders/{order.id}/returns/{ret.id}/"
        res_detail = self.client.get(detail_url)
        self.assertEqual(res_detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_can_cancel_pending_return_request(self):
        order, line = self._create_order(quantity=1)
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.user,
            items_data=[{"order_line_item_id": line.id, "quantity": 1}],
        )
        url = f"/api/v1/orders/{order.id}/returns/{ret.id}/cancel/"
        res = self.client.post(url, {"reason": "Decided to keep it"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ret.refresh_from_db()
        self.assertEqual(ret.status, ReturnRequestStatus.CANCELLED)

    def test_customer_cannot_cancel_unsupported_status(self):
        order, line = self._create_order(quantity=1)
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.user,
            items_data=[{"order_line_item_id": line.id, "quantity": 1}],
        )
        ret.status = ReturnRequestStatus.RECEIVED
        ret.save()

        with self.assertRaises(ReturnConflict):
            ReturnService.cancel_return_request(ret.id, self.user)

    def test_unauthenticated_request_rejected(self):
        self.client.force_authenticate(user=None)
        order, _ = self._create_order()
        url = f"/api/v1/orders/{order.id}/returns/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
