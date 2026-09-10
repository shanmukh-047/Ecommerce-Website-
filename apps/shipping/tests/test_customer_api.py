from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.orders.tests.factories import create_order_user
from apps.shipping.models import CourierProvider
from apps.shipping.services import ShippingService
from apps.shipping.tests.factories import create_shipping_test_order


class CustomerShippingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_order_user(email="customer1@example.com", phone="9876543231")
        self.other_user = create_order_user(email="customer2@example.com", phone="9876543232")

        self.order = create_shipping_test_order(user=self.user)
        self.shipment = ShippingService.create_shipment(
            order=self.order,
            courier_name=CourierProvider.BLUEDART,
        )
        self.shipment = ShippingService.book_carrier_and_generate_label(self.shipment)

    def test_customer_can_track_own_order(self):
        self.client.force_authenticate(user=self.user)
        url = f"/api/v1/shipping/orders/{self.order.id}/tracking/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["order_number"], self.order.order_number)
        self.assertEqual(len(data["shipments"]), 1)
        self.assertEqual(data["shipments"][0]["shipment_number"], self.shipment.shipment_number)

    def test_customer_cannot_track_other_users_order_idor(self):
        self.client.force_authenticate(user=self.other_user)
        url = f"/api/v1/shipping/orders/{self.order.id}/tracking/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_request_rejected(self):
        url = f"/api/v1/shipping/orders/{self.order.id}/tracking/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_can_retrieve_own_shipment_detail(self):
        self.client.force_authenticate(user=self.user)
        url = f"/api/v1/shipping/{self.shipment.shipment_number}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["shipment"]["shipment_number"], self.shipment.shipment_number
        )

    def test_customer_cannot_retrieve_other_users_shipment(self):
        self.client.force_authenticate(user=self.other_user)
        url = f"/api/v1/shipping/{self.shipment.shipment_number}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_tracking_milestones_and_pii_redaction(self):
        url = f"/api/v1/shipping/track/?awb={self.shipment.awb_number}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tracking = response.data["tracking"]
        self.assertEqual(tracking["shipment_number"], self.shipment.shipment_number)
        self.assertEqual(tracking["courier_name"], CourierProvider.BLUEDART)
        self.assertEqual(tracking["awb_number"], self.shipment.awb_number)
        self.assertEqual(tracking["destination_city"], "Sirsi")

        # Verify strict PII redaction
        self.assertNotIn("shipping_recipient_name", tracking)
        self.assertNotIn("shipping_phone_number", tracking)
        self.assertNotIn("shipping_address_line_1", tracking)
        self.assertNotIn("items", tracking)
        self.assertNotIn("order_id", tracking)

    def test_public_tracking_not_found(self):
        url = "/api/v1/shipping/track/?awb=NON_EXISTENT_AWB"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
