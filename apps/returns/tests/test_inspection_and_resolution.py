import datetime
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import IndianStates, Role, User
from apps.catalog.models import Category, Product, ProductVariant
from apps.inventory.models import StockItem
from apps.invoices.models import InvoiceStatus
from apps.invoices.services.invoice_service import InvoiceService
from apps.orders.models import Order, OrderLineItem, OrderStatus
from apps.payments.models import Payment, PaymentGateway, PaymentStatus
from apps.returns.exceptions import ReturnConflict, ReturnPolicyViolation
from apps.returns.models import (
    InspectionResult,
    InventoryDisposition,
    ResolutionType,
    ReturnRequestStatus,
    ReturnShipmentStatus,
)
from apps.returns.services.inspection_service import ReturnInspectionService
from apps.returns.services.resolution_service import ReturnResolutionService
from apps.returns.services.return_service import ReturnService
from apps.returns.services.reverse_logistics import ReverseLogisticsService
from apps.returns.services.review_service import ReturnReviewService


class InspectionAndResolutionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.customer = User.objects.create_user(
            email="manjunath@example.com",
            phone_number="+919876543230",
            first_name="Manjunath",
            last_name="Bhat",
            password="StrongPassword123!",
        )

        self.staff_user = User.objects.create_user(
            email="inspector@bharathmasala.com",
            phone_number="+919876543231",
            first_name="Inspector",
            last_name="Quality",
            role=Role.STAFF,
            password="StrongPassword123!",
        )
        self.staff_user.is_staff = True
        self.staff_user.save()

        self.category = Category.objects.create(name="Spices", slug="spices")
        self.product = Product.objects.create(
            category=self.category,
            name="Sirsi Bold Black Pepper",
            slug="sirsi-bold-pepper",
            hsn_code="0904",
            gst_rate=Decimal("5.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="250g",
            sku="PEPPER-250G",
            weight_in_grams=250,
            mrp=Decimal("350.00"),
            selling_price=Decimal("350.00"),
        )
        self.stock = StockItem.objects.create(
            variant=self.variant,
            quantity_on_hand=20,
            quantity_reserved=0,
        )

    def _create_delivered_order_with_payment_and_invoice(self, quantity=2):
        order = Order.objects.create(
            order_number=f"BMP-ORD-{timezone.now().timestamp()}",
            user=self.customer,
            order_status=OrderStatus.PENDING_PAYMENT,
            items_subtotal=Decimal("350.00") * quantity,
            tax_amount=Decimal("0.00"),
            shipping_fee=Decimal("0.00"),
            grand_total=Decimal("350.00") * quantity,
            currency="INR",
            total_quantity=quantity,
            shipping_recipient_name="Manjunath Bhat",
            shipping_phone_number="+919876543230",
            shipping_address_line_1="Temple Road",
            shipping_city="Sirsi",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="581401",
        )
        line = OrderLineItem.objects.create(
            order=order,
            variant=self.variant,
            quantity=quantity,
            mrp=Decimal("350.00"),
            unit_price=Decimal("350.00"),
            line_subtotal=Decimal("350.00") * quantity,
            product_name="Sirsi Bold Black Pepper",
            variant_name="250g",
            sku="PEPPER-250G",
        )
        # Create and Capture Payment directly
        payment = Payment.objects.create(
            payment_number=f"PAY-{uuid_str()[:12].upper()}",
            order=order,
            user=self.customer,
            gateway=PaymentGateway.RAZORPAY,
            gateway_order_id=f"order_{uuid_str()[:14]}",
            gateway_payment_id=f"pay_{uuid_str()[:14]}",
            status=PaymentStatus.CAPTURED,
            amount=Decimal("350.00") * quantity,
            currency="INR",
            amount_refunded=Decimal("0.00"),
        )

        # Advance order to DELIVERED
        order.order_status = OrderStatus.DELIVERED
        order.delivered_at = timezone.now() - datetime.timedelta(days=1)
        order.save(update_fields=["order_status", "delivered_at", "updated_at"])

        # Generate statutory invoice
        invoice = InvoiceService.generate_invoice(order)
        return order, line, payment, invoice

    def _advance_to_received(self, return_request):
        ReturnReviewService.approve_return(return_request.id, self.staff_user)
        shipment = ReverseLogisticsService.schedule_reverse_pickup(
            return_request.id, self.staff_user
        )
        ReverseLogisticsService.update_shipment_status(shipment.id, ReturnShipmentStatus.DELIVERED)
        return_request.refresh_from_db()
        return return_request

    def test_record_inspection_passed_with_restock_increases_inventory(self):
        order, line, _, _ = self._create_delivered_order_with_payment_and_invoice(quantity=2)
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 2}],
        )
        ret = self._advance_to_received(ret)

        initial_stock = self.stock.quantity_on_hand

        self.client.force_authenticate(user=self.staff_user)
        url = f"/api/v1/staff/returns/{ret.id}/inspection/"
        payload = {
            "result": InspectionResult.PASSED,
            "disposition": InventoryDisposition.RESTOCK,
            "quantity_passed": 2,
            "quantity_failed": 0,
            "notes": "Original seals intact, verified authentic.",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ret.refresh_from_db()
        self.assertEqual(ret.status, ReturnRequestStatus.INSPECTED)

        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity_on_hand, initial_stock + 2)

    def test_record_inspection_fssai_discard_does_not_increase_inventory(self):
        order, line, _, _ = self._create_delivered_order_with_payment_and_invoice(quantity=2)
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 2}],
        )
        ret = self._advance_to_received(ret)

        initial_stock = self.stock.quantity_on_hand

        self.client.force_authenticate(user=self.staff_user)
        url = f"/api/v1/staff/returns/{ret.id}/inspection/"
        payload = {
            "result": InspectionResult.SCRAP_DAMAGED,
            "disposition": InventoryDisposition.DISCARD,
            "quantity_passed": 0,
            "quantity_failed": 2,
            "notes": "Package was torn, food safety scrap.",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ret.refresh_from_db()
        self.assertEqual(ret.status, ReturnRequestStatus.INSPECTED)

        # Inventory must NOT have increased!
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity_on_hand, initial_stock)

    def test_record_inspection_partial_pass_restocks_only_passed_quantity(self):
        """
        FSSAI Food Safety: When 2 units are returned and 1 passes and 1 fails,
        only the 1 passed unit must be restocked into saleable inventory.
        """
        order, line, _, _ = self._create_delivered_order_with_payment_and_invoice(quantity=2)
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 2}],
        )
        ret = self._advance_to_received(ret)

        initial_stock = self.stock.quantity_on_hand

        self.client.force_authenticate(user=self.staff_user)
        url = f"/api/v1/staff/returns/{ret.id}/inspection/"
        payload = {
            "result": InspectionResult.PASSED,
            "disposition": InventoryDisposition.RESTOCK,
            "quantity_passed": 1,
            "quantity_failed": 1,
            "notes": "1 box sealed intact, 1 box damaged package scrapped.",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ret.refresh_from_db()
        self.assertEqual(ret.status, ReturnRequestStatus.INSPECTED)

        # Inventory must have increased by exactly 1 unit (passed), NOT 2!
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity_on_hand, initial_stock + 1)

    def test_record_inspection_quantity_sum_mismatch_fails(self):
        """
        Inspection must reject when quantity_passed + quantity_failed does not equal total return items.
        """
        order, line, _, _ = self._create_delivered_order_with_payment_and_invoice(quantity=2)
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 2}],
        )
        ret = self._advance_to_received(ret)

        self.client.force_authenticate(user=self.staff_user)
        url = f"/api/v1/staff/returns/{ret.id}/inspection/"
        payload = {
            "result": InspectionResult.PASSED,
            "disposition": InventoryDisposition.RESTOCK,
            "quantity_passed": 1,
            "quantity_failed": 0,  # Total 1 != 2 returned
            "notes": "Mismatch test",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("must equal total returned items quantity", res.data["detail"])

    def test_cannot_inspect_request_not_in_received_status(self):
        order, line, _, _ = self._create_delivered_order_with_payment_and_invoice()
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 1}],
        )
        with self.assertRaises(ReturnConflict):
            ReturnInspectionService.record_inspection(ret.id, self.staff_user)

    def test_duplicate_inspection_rejected(self):
        order, line, _, _ = self._create_delivered_order_with_payment_and_invoice()
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 1}],
        )
        ret = self._advance_to_received(ret)
        ReturnInspectionService.record_inspection(ret.id, self.staff_user)

        with self.assertRaises(ReturnConflict):
            ReturnInspectionService.record_inspection(ret.id, self.staff_user)

    @patch("apps.payments.gateways.razorpay_gateway.RazorpayGateway.refund_payment")
    def test_complete_return_with_refund_resolution(self, mock_gateway_refund):
        mock_gateway_refund.return_value = {
            "id": "rfnd_test_return_12345",
            "amount": 70000,
            "currency": "INR",
            "status": "processed",
        }
        order, line, payment, invoice = self._create_delivered_order_with_payment_and_invoice(
            quantity=2
        )
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 2}],
            requested_resolution=ResolutionType.REFUND,
        )
        ret = self._advance_to_received(ret)
        ReturnInspectionService.record_inspection(ret.id, self.staff_user)

        self.client.force_authenticate(user=self.staff_user)
        url = f"/api/v1/staff/returns/{ret.id}/complete/"
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ret.refresh_from_db()
        self.assertEqual(ret.status, ReturnRequestStatus.COMPLETED)
        self.assertIsNotNone(ret.credit_note)
        self.assertEqual(ret.credit_note.order, order)
        self.assertEqual(ret.refund_amount, Decimal("700.00"))

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, InvoiceStatus.CREDIT_NOTED)

    @patch("apps.payments.gateways.razorpay_gateway.RazorpayGateway.refund_payment")
    def test_refund_resolution_idempotency_double_completion_safe(self, mock_gateway_refund):
        mock_gateway_refund.return_value = {
            "id": "rfnd_test_return_12345",
            "amount": 35000,
            "currency": "INR",
            "status": "processed",
        }
        order, line, payment, invoice = self._create_delivered_order_with_payment_and_invoice(
            quantity=1
        )
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 1}],
            requested_resolution=ResolutionType.REFUND,
        )
        ret = self._advance_to_received(ret)
        ReturnInspectionService.record_inspection(ret.id, self.staff_user)

        # First completion
        ReturnResolutionService.complete_return(ret.id, self.staff_user)
        ret.refresh_from_db()
        first_cn = ret.credit_note
        first_refund_tx = ret.refund_transaction_id

        # Second completion attempt (must be completely idempotent)
        ReturnResolutionService.complete_return(ret.id, self.staff_user)
        ret.refresh_from_db()
        self.assertEqual(ret.credit_note, first_cn)
        self.assertEqual(ret.refund_transaction_id, first_refund_tx)

    def test_complete_return_with_replacement_resolution(self):
        order, line, payment, _ = self._create_delivered_order_with_payment_and_invoice(quantity=2)
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 2}],
            requested_resolution=ResolutionType.REPLACEMENT,
        )
        ReturnReviewService.approve_return(
            ret.id, self.staff_user, approved_resolution=ResolutionType.REPLACEMENT
        )
        shipment = ReverseLogisticsService.schedule_reverse_pickup(ret.id, self.staff_user)
        ReverseLogisticsService.update_shipment_status(shipment.id, ReturnShipmentStatus.DELIVERED)
        ReturnInspectionService.record_inspection(ret.id, self.staff_user)

        self.client.force_authenticate(user=self.staff_user)
        url = f"/api/v1/staff/returns/{ret.id}/complete/"
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ret.refresh_from_db()
        self.assertEqual(ret.status, ReturnRequestStatus.COMPLETED)
        self.assertIsNotNone(ret.replacement_order)
        self.assertEqual(ret.replacement_order.order_status, OrderStatus.CONFIRMED)
        self.assertEqual(ret.replacement_order.grand_total, Decimal("0.00"))
        self.assertEqual(ret.replacement_order.total_quantity, 2)

    def test_replacement_resolution_idempotency_double_completion_safe(self):
        order, line, payment, _ = self._create_delivered_order_with_payment_and_invoice(quantity=1)
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 1}],
            requested_resolution=ResolutionType.REPLACEMENT,
        )
        ReturnReviewService.approve_return(
            ret.id, self.staff_user, approved_resolution=ResolutionType.REPLACEMENT
        )
        shipment = ReverseLogisticsService.schedule_reverse_pickup(ret.id, self.staff_user)
        ReverseLogisticsService.update_shipment_status(shipment.id, ReturnShipmentStatus.DELIVERED)
        ReturnInspectionService.record_inspection(ret.id, self.staff_user)

        # First run
        ReturnResolutionService.complete_return(ret.id, self.staff_user)
        ret.refresh_from_db()
        first_rpl = ret.replacement_order

        # Second run
        ReturnResolutionService.complete_return(ret.id, self.staff_user)
        ret.refresh_from_db()
        self.assertEqual(ret.replacement_order, first_rpl)

    def test_replacement_order_reserves_and_consumes_inventory(self):
        initial_stock = self.stock.quantity_on_hand
        order, line, _, _ = self._create_delivered_order_with_payment_and_invoice(quantity=2)
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 2}],
            requested_resolution=ResolutionType.REPLACEMENT,
        )
        ReturnReviewService.approve_return(
            ret.id, self.staff_user, approved_resolution=ResolutionType.REPLACEMENT
        )
        shipment = ReverseLogisticsService.schedule_reverse_pickup(ret.id, self.staff_user)
        ReverseLogisticsService.update_shipment_status(shipment.id, ReturnShipmentStatus.DELIVERED)
        ReturnInspectionService.record_inspection(
            ret.id,
            self.staff_user,
            result=InspectionResult.SCRAP_DAMAGED,
            disposition=InventoryDisposition.DISCARD,
            quantity_failed=2,
        )

        ReturnResolutionService.complete_return(ret.id, self.staff_user)
        self.stock.refresh_from_db()
        # Because damaged item was discarded (+0) and replacement order consumed 2 fresh units:
        self.assertEqual(self.stock.quantity_on_hand, initial_stock - 2)

    @patch("apps.payments.gateways.razorpay_gateway.RazorpayGateway.refund_payment")
    def test_order_transitions_to_refunded_when_all_items_returned(self, mock_gateway_refund):
        mock_gateway_refund.return_value = {
            "id": "rfnd_test_order_fully_refunded",
            "amount": 70000,
            "currency": "INR",
            "status": "processed",
        }
        order, line, _, _ = self._create_delivered_order_with_payment_and_invoice(quantity=2)
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 2}],
            requested_resolution=ResolutionType.REFUND,
        )
        ret = self._advance_to_received(ret)
        ReturnInspectionService.record_inspection(ret.id, self.staff_user)
        ReturnResolutionService.complete_return(ret.id, self.staff_user)

        order.refresh_from_db()
        self.assertEqual(order.order_status, OrderStatus.REFUNDED)

    @patch("apps.payments.gateways.razorpay_gateway.RazorpayGateway.refund_payment")
    def test_partial_return_refund_leaves_order_in_delivered(self, mock_gateway_refund):
        mock_gateway_refund.return_value = {
            "id": "rfnd_test_order_partial_refunded",
            "amount": 35000,
            "currency": "INR",
            "status": "processed",
        }
        order, line, _, _ = self._create_delivered_order_with_payment_and_invoice(quantity=3)
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 1}],
            requested_resolution=ResolutionType.REFUND,
        )
        ret = self._advance_to_received(ret)
        ReturnInspectionService.record_inspection(ret.id, self.staff_user)
        ReturnResolutionService.complete_return(ret.id, self.staff_user)

        order.refresh_from_db()
        self.assertEqual(order.order_status, OrderStatus.DELIVERED)

    def test_cannot_complete_uninspected_return(self):
        order, line, _, _ = self._create_delivered_order_with_payment_and_invoice()
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 1}],
        )
        with self.assertRaises(ReturnConflict):
            ReturnResolutionService.complete_return(ret.id, self.staff_user)

    @patch("apps.returns.services.return_service.ReturnService._dispatch_return_notification")
    def test_complete_return_rejected_when_inspection_fails(self, mock_notif):
        order, line, payment, invoice = self._create_delivered_order_with_payment_and_invoice(
            quantity=1
        )
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 1}],
            requested_resolution=ResolutionType.REFUND,
        )
        ret = self._advance_to_received(ret)
        ReturnInspectionService.record_inspection(
            return_request_id=ret.id,
            actor=self.staff_user,
            result=InspectionResult.FAILED,
            disposition=InventoryDisposition.RETURN_TO_CUSTOMER,
            notes="Counterfeit product / broken safety seal by customer.",
        )

        with self.assertRaises(ReturnPolicyViolation):
            ReturnResolutionService.complete_return(ret.id, self.staff_user)

        ret.refresh_from_db()
        self.assertEqual(ret.status, ReturnRequestStatus.REJECTED)
        self.assertIn("Rejected post-inspection", ret.rejection_reason)
        self.assertIn("Counterfeit product", ret.rejection_reason)
        self.assertIsNone(ret.credit_note)
        self.assertEqual(ret.refund_amount, Decimal("0.00"))
        self.assertIsNone(ret.replacement_order)

    @patch("apps.returns.services.return_service.ReturnService._dispatch_return_notification")
    def test_complete_return_rejected_when_disposition_is_return_to_customer(self, mock_notif):
        order, line, payment, invoice = self._create_delivered_order_with_payment_and_invoice(
            quantity=1
        )
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 1}],
            requested_resolution=ResolutionType.REPLACEMENT,
        )
        ret = self._advance_to_received(ret)
        ReturnInspectionService.record_inspection(
            return_request_id=ret.id,
            actor=self.staff_user,
            result=InspectionResult.FAILED,
            disposition=InventoryDisposition.RETURN_TO_CUSTOMER,
            notes="Customer damaged item, returned to sender.",
        )

        with self.assertRaises(ReturnPolicyViolation):
            ReturnResolutionService.complete_return(ret.id, self.staff_user)

        ret.refresh_from_db()
        self.assertEqual(ret.status, ReturnRequestStatus.REJECTED)
        self.assertIsNone(ret.replacement_order)

    @patch("apps.payments.gateways.razorpay_gateway.RazorpayGateway.refund_payment")
    def test_complete_return_allows_scrap_damaged_resolution(self, mock_gateway_refund):
        mock_gateway_refund.return_value = {
            "id": "rfnd_test_scrap_damaged_123",
            "amount": 35000,
            "currency": "INR",
            "status": "processed",
        }
        order, line, payment, invoice = self._create_delivered_order_with_payment_and_invoice(
            quantity=1
        )
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 1}],
            requested_resolution=ResolutionType.REFUND,
        )
        ret = self._advance_to_received(ret)
        ReturnInspectionService.record_inspection(
            return_request_id=ret.id,
            actor=self.staff_user,
            result=InspectionResult.SCRAP_DAMAGED,
            disposition=InventoryDisposition.DISCARD,
            notes="Damaged in transit by carrier, food safety write-off.",
        )

        ReturnResolutionService.complete_return(ret.id, self.staff_user)

        ret.refresh_from_db()
        self.assertEqual(ret.status, ReturnRequestStatus.COMPLETED)
        self.assertIsNotNone(ret.credit_note)
        self.assertEqual(ret.refund_amount, Decimal("350.00"))

    def test_complete_return_api_returns_400_when_inspection_failed(self):
        order, line, _, _ = self._create_delivered_order_with_payment_and_invoice(quantity=1)
        ret = ReturnService.create_return_request(
            order_id=order.id,
            user=self.customer,
            items_data=[{"order_line_item_id": line.id, "quantity": 1}],
            requested_resolution=ResolutionType.REFUND,
        )
        ret = self._advance_to_received(ret)
        ReturnInspectionService.record_inspection(
            return_request_id=ret.id,
            actor=self.staff_user,
            result=InspectionResult.FAILED,
            disposition=InventoryDisposition.RETURN_TO_CUSTOMER,
            notes="Failed QA inspection.",
        )

        self.client.force_authenticate(user=self.staff_user)
        url = f"/api/v1/staff/returns/{ret.id}/complete/"
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot be resolved for refund or replacement", res.data.get("detail", ""))

        ret.refresh_from_db()
        self.assertEqual(ret.status, ReturnRequestStatus.REJECTED)


def uuid_str():
    import uuid

    return uuid.uuid4().hex
