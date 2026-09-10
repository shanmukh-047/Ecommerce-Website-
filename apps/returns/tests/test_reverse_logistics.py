import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import IndianStates, Role, User
from apps.catalog.models import Category, Product, ProductVariant
from apps.inventory.models import StockItem
from apps.orders.models import Order, OrderLineItem, OrderStatus
from apps.returns.exceptions import ReturnConflict
from apps.returns.models import (
    ResolutionType,
    ReturnReason,
    ReturnRequestStatus,
    ReturnShipmentStatus,
)
from apps.returns.services.return_service import ReturnService
from apps.returns.services.reverse_logistics import ReverseLogisticsService
from apps.returns.services.review_service import ReturnReviewService
from apps.shipping.models import CourierProvider


class ReverseLogisticsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.customer = User.objects.create_user(
            email="vasant@example.com",
            phone_number="+919876543220",
            first_name="Vasant",
            last_name="Kamat",
            password="StrongPassword123!",
        )

        self.staff_user = User.objects.create_user(
            email="staff_rma@bharathmasala.com",
            phone_number="+919876543221",
            first_name="Staff",
            last_name="Logistics",
            role=Role.STAFF,
            password="StrongPassword123!",
        )
        self.staff_user.is_staff = True
        self.staff_user.save()

        self.category = Category.objects.create(name="Spices", slug="spices")
        self.product = Product.objects.create(
            category=self.category,
            name="Byadgi Chilli Powder",
            slug="byadgi-chilli",
            hsn_code="0904",
            gst_rate=Decimal("5.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="500g",
            sku="BYADGI-500G",
            weight_in_grams=500,
            mrp=Decimal("320.00"),
            selling_price=Decimal("320.00"),
        )
        self.stock = StockItem.objects.create(
            variant=self.variant,
            quantity_on_hand=50,
            quantity_reserved=0,
        )

    def _create_return_request(self):
        order = Order.objects.create(
            order_number=f"BMP-ORD-{timezone.now().timestamp()}",
            user=self.customer,
            order_status=OrderStatus.DELIVERED,
            items_subtotal=Decimal("640.00"),
            tax_amount=Decimal("0.00"),
            shipping_fee=Decimal("0.00"),
            grand_total=Decimal("640.00"),
            currency="INR",
            total_quantity=2,
            shipping_recipient_name="Vasant Kamat",
            shipping_phone_number="+919876543220",
            shipping_address_line_1="Market Road",
            shipping_city="Sirsi",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="581401",
            delivered_at=timezone.now() - datetime.timedelta(days=1),
        )
        line = OrderLineItem.objects.create(
            order=order,
            variant=self.variant,
            quantity=2,
            mrp=Decimal("320.00"),
            unit_price=Decimal("320.00"),
            line_subtotal=Decimal("640.00"),
            product_name="Byadgi Chilli Powder",
            variant_name="500g",
            sku="BYADGI-500G",
        )
        return ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 1}],
            reason=ReturnReason.DEFECTIVE_QUALITY,
        )

    def test_staff_can_approve_return_request(self):
        ret = self._create_return_request()
        self.client.force_authenticate(user=self.staff_user)

        url = f"/api/v1/staff/returns/{ret.id}/review/"
        payload = {
            "action": "APPROVE",
            "approved_resolution": ResolutionType.REFUND,
            "review_notes": "Defect verified from photo evidence.",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ret.refresh_from_db()
        self.assertEqual(ret.status, ReturnRequestStatus.APPROVED)
        self.assertEqual(ret.approved_resolution, ResolutionType.REFUND)
        self.assertEqual(ret.reviewed_by, self.staff_user)

    def test_staff_can_reject_return_request_with_reason(self):
        ret = self._create_return_request()
        self.client.force_authenticate(user=self.staff_user)

        url = f"/api/v1/staff/returns/{ret.id}/review/"
        payload = {
            "action": "REJECT",
            "rejection_reason": "Broken seal caused by customer post-delivery.",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ret.refresh_from_db()
        self.assertEqual(ret.status, ReturnRequestStatus.REJECTED)
        self.assertEqual(ret.rejection_reason, "Broken seal caused by customer post-delivery.")

    def test_reject_without_reason_fails(self):
        ret = self._create_return_request()
        self.client.force_authenticate(user=self.staff_user)

        url = f"/api/v1/staff/returns/{ret.id}/review/"
        payload = {
            "action": "REJECT",
            "rejection_reason": "",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_approve_already_approved_request(self):
        ret = self._create_return_request()
        ReturnReviewService.approve_return(ret.id, self.staff_user)

        with self.assertRaises(ReturnConflict):
            ReturnReviewService.approve_return(ret.id, self.staff_user)

    def test_staff_schedules_reverse_pickup_with_courier_adapter(self):
        ret = self._create_return_request()
        ReturnReviewService.approve_return(ret.id, self.staff_user)

        self.client.force_authenticate(user=self.staff_user)
        url = f"/api/v1/staff/returns/{ret.id}/shipment/schedule/"
        payload = {
            "courier_name": CourierProvider.DELHIVERY,
            "scheduled_date": str(timezone.now().date() + datetime.timedelta(days=1)),
            "notes": "Doorstep pickup required.",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            res.data["awb_number"].startswith("BMP-AWB-") or "AWB" in res.data["awb_number"]
        )
        ret.refresh_from_db()
        self.assertEqual(ret.status, ReturnRequestStatus.PICKUP_SCHEDULED)

    def test_reverse_awb_and_pickup_address_snapshot_created(self):
        ret = self._create_return_request()
        ReturnReviewService.approve_return(ret.id, self.staff_user)

        shipment = ReverseLogisticsService.schedule_reverse_pickup(
            return_request_id=ret.id,
            actor=self.staff_user,
            courier_name=CourierProvider.MANUAL,
        )
        self.assertEqual(shipment.pickup_city, "Sirsi")
        self.assertEqual(shipment.pickup_state, IndianStates.KARNATAKA)
        self.assertEqual(shipment.pickup_pincode, "581401")
        self.assertEqual(shipment.pickup_phone_number, "+919876543220")

    def test_cannot_schedule_pickup_for_unapproved_request(self):
        ret = self._create_return_request()
        with self.assertRaises(ReturnConflict):
            ReverseLogisticsService.schedule_reverse_pickup(ret.id, self.staff_user)

    def test_cannot_schedule_duplicate_reverse_pickup(self):
        ret = self._create_return_request()
        ReturnReviewService.approve_return(ret.id, self.staff_user)
        ReverseLogisticsService.schedule_reverse_pickup(ret.id, self.staff_user)

        with self.assertRaises(ReturnConflict):
            ReverseLogisticsService.schedule_reverse_pickup(ret.id, self.staff_user)

    def test_reverse_shipment_status_update_to_in_transit(self):
        ret = self._create_return_request()
        ReturnReviewService.approve_return(ret.id, self.staff_user)
        ReverseLogisticsService.schedule_reverse_pickup(ret.id, self.staff_user)

        self.client.force_authenticate(user=self.staff_user)
        url = f"/api/v1/staff/returns/{ret.id}/shipment/status/"
        payload = {"status": ReturnShipmentStatus.IN_TRANSIT, "notes": "Handed to driver"}
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ret.refresh_from_db()
        self.assertEqual(ret.status, ReturnRequestStatus.IN_TRANSIT)

    def test_reverse_shipment_delivered_transitions_return_to_received(self):
        ret = self._create_return_request()
        ReturnReviewService.approve_return(ret.id, self.staff_user)
        shipment = ReverseLogisticsService.schedule_reverse_pickup(ret.id, self.staff_user)

        ReverseLogisticsService.update_shipment_status(shipment.id, ReturnShipmentStatus.DELIVERED)
        ret.refresh_from_db()
        self.assertEqual(ret.status, ReturnRequestStatus.RECEIVED)
        shipment.refresh_from_db()
        self.assertIsNotNone(shipment.received_at_warehouse)

    def test_customer_cannot_access_staff_return_endpoints(self):
        self.client.force_authenticate(user=self.customer)
        ret = self._create_return_request()

        res = self.client.get("/api/v1/staff/returns/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        res = self.client.post(f"/api/v1/staff/returns/{ret.id}/review/", {"action": "APPROVE"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_list_and_filter_returns_by_status(self):
        ret = self._create_return_request()
        self.client.force_authenticate(user=self.staff_user)

        res = self.client.get("/api/v1/staff/returns/?status=PENDING_REVIEW")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data.get("results", res.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(ret.id))
