from django.test import TestCase

from apps.shipping.couriers.factory import get_courier_adapter
from apps.shipping.couriers.mock_courier import MockCourierAdapter
from apps.shipping.models import CourierProvider
from apps.shipping.tests.factories import create_test_shipment


class CourierAdapterTests(TestCase):
    def setUp(self):
        self.shipment = create_test_shipment(courier_name=CourierProvider.DELHIVERY)

    def test_mock_courier_create_shipment(self):
        adapter = MockCourierAdapter()
        res = adapter.create_shipment(self.shipment)

        self.assertTrue(res["success"])
        self.assertTrue(res["awb_number"].startswith("BMP-AWB-"))
        self.assertEqual(res["carrier"], CourierProvider.DELHIVERY)

    def test_mock_courier_generate_label(self):
        adapter = MockCourierAdapter()
        res = adapter.generate_label(self.shipment)

        self.assertTrue(res["success"])
        self.assertIn(self.shipment.shipment_number, res["label_url"])
        self.assertEqual(res["label_format"], "PDF_4X6")

    def test_mock_courier_track_and_cancel(self):
        adapter = MockCourierAdapter()
        events = adapter.track_shipment("BMP-AWB-TEST123")
        self.assertIsInstance(events, list)
        self.assertGreaterEqual(len(events), 1)

        cancel_res = adapter.cancel_shipment(self.shipment)
        self.assertTrue(cancel_res)

    def test_courier_factory_resolution(self):
        for provider in CourierProvider.values:
            adapter = get_courier_adapter(provider)
            self.assertIsInstance(adapter, MockCourierAdapter)
