from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.orders.tests.factories import create_order_user, create_staff_user
from apps.shipping.models import CourierProvider, ShipmentStatus
from apps.shipping.services import ShippingService
from apps.shipping.tests.factories import create_shipping_test_order


class StaffShippingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = create_staff_user(email="staff_logistics@example.com", phone="9876543241")
        self.customer = create_order_user(email="normal_customer@example.com", phone="9876543242")

        self.order = create_shipping_test_order()
        self.shipment = ShippingService.create_shipment(
            order=self.order,
            courier_name=CourierProvider.DELHIVERY,
            notes="Fragile glass jars",
        )

    def test_customer_forbidden_from_staff_shipping_endpoints(self):
        self.client.force_authenticate(user=self.customer)
        url = "/api/v1/staff/shipping/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        url_create = f"/api/v1/staff/shipping/orders/{self.order.id}/shipments/"
        response_create = self.client.post(url_create, {})
        self.assertEqual(response_create.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_list_and_filter_shipments(self):
        self.client.force_authenticate(user=self.staff)
        url = "/api/v1/staff/shipping/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)

        # Filter by courier
        res_filter = self.client.get(f"{url}?courier={CourierProvider.DELHIVERY}")
        self.assertEqual(res_filter.status_code, status.HTTP_200_OK)
        self.assertEqual(res_filter.data["results"][0]["courier_name"], CourierProvider.DELHIVERY)

        # Filter by search
        res_search = self.client.get(f"{url}?search={self.order.order_number}")
        self.assertEqual(res_search.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(res_search.data["count"], 1)

    def test_staff_retrieve_shipment_detail(self):
        self.client.force_authenticate(user=self.staff)
        url = f"/api/v1/staff/shipping/{self.shipment.id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["shipment"]["id"], str(self.shipment.id))
        self.assertEqual(response.data["shipment"]["order_number"], self.order.order_number)

    def test_staff_create_shipment_for_order(self):
        self.client.force_authenticate(user=self.staff)
        new_order = create_shipping_test_order(
            user=self.customer,
            initial_stock=30,
        )
        url = f"/api/v1/staff/shipping/orders/{new_order.id}/shipments/"
        payload = {
            "courier_name": CourierProvider.BLUEDART,
            "weight_in_grams": 650,
            "notes": "Special packing request",
        }
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["shipment"]["courier_name"], CourierProvider.BLUEDART)
        self.assertEqual(response.data["shipment"]["weight_in_grams"], 650)

    def test_staff_query_fulfillment_summary(self):
        self.client.force_authenticate(user=self.staff)
        url = f"/api/v1/staff/shipping/orders/{self.order.id}/fulfillment-summary/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["order_id"], str(self.order.id))
        self.assertIn("lines", response.data)

    def test_staff_generate_label(self):
        self.client.force_authenticate(user=self.staff)
        url = f"/api/v1/staff/shipping/{self.shipment.id}/label/"
        payload = {"courier_name": CourierProvider.DELHIVERY}
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        shipment_data = response.data["shipment"]
        self.assertEqual(shipment_data["status"], ShipmentStatus.LABEL_GENERATED)
        self.assertTrue(shipment_data["awb_number"].startswith("BMP-AWB-"))
        self.assertIn(".pdf", shipment_data["shipping_label_url"])

    def test_staff_update_status_and_append_event(self):
        self.client.force_authenticate(user=self.staff)
        # Advance to READY_FOR_PICKUP
        url = f"/api/v1/staff/shipping/{self.shipment.id}/status/"
        payload = {
            "status": ShipmentStatus.READY_FOR_PICKUP,
            "location": "Warehouse Dock 4",
            "description": "Carton weighed and staged for courier handover.",
        }
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["shipment"]["status"], ShipmentStatus.READY_FOR_PICKUP)

    def test_staff_cancel_shipment(self):
        self.client.force_authenticate(user=self.staff)
        url = f"/api/v1/staff/shipping/{self.shipment.id}/cancel/"
        payload = {"reason": "Customer requested address change before dispatch."}
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["shipment"]["status"], ShipmentStatus.CANCELLED)
        self.assertEqual(
            response.data["shipment"]["cancellation_reason"],
            "Customer requested address change before dispatch.",
        )
