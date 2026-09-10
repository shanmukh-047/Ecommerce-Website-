from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.shipping.models import (
    CourierProvider,
    Shipment,
    ShipmentItem,
    ShipmentStatus,
    ShipmentTrackingEvent,
)
from apps.shipping.tests.factories import create_shipping_test_order


class ShipmentModelTests(TestCase):
    def setUp(self):
        self.order = create_shipping_test_order()
        self.line = self.order.lines.first()

    def test_shipment_creation_and_address_snapshot(self):
        shipment = Shipment.objects.create(
            shipment_number="SHP-20260906-TEST1",
            order=self.order,
            status=ShipmentStatus.PENDING,
            courier_name=CourierProvider.BLUEDART,
            weight_in_grams=450,
            shipping_recipient_name=self.order.shipping_recipient_name,
            shipping_phone_number=self.order.shipping_phone_number,
            shipping_address_line_1=self.order.shipping_address_line_1,
            shipping_address_line_2=self.order.shipping_address_line_2,
            shipping_landmark=self.order.shipping_landmark,
            shipping_city=self.order.shipping_city,
            shipping_state=self.order.shipping_state,
            shipping_pincode=self.order.shipping_pincode,
        )

        self.assertEqual(shipment.shipment_number, "SHP-20260906-TEST1")
        self.assertEqual(shipment.status, ShipmentStatus.PENDING)
        self.assertEqual(shipment.courier_name, CourierProvider.BLUEDART)
        self.assertEqual(shipment.shipping_recipient_name, self.order.shipping_recipient_name)
        self.assertEqual(shipment.shipping_city, self.order.shipping_city)
        self.assertIn("SHP-20260906-TEST1", str(shipment))

    def test_unique_shipment_number(self):
        Shipment.objects.create(
            shipment_number="SHP-UNIQUE-001",
            order=self.order,
            status=ShipmentStatus.PENDING,
            weight_in_grams=300,
            shipping_recipient_name=self.order.shipping_recipient_name,
            shipping_phone_number=self.order.shipping_phone_number,
            shipping_address_line_1=self.order.shipping_address_line_1,
            shipping_city=self.order.shipping_city,
            shipping_state=self.order.shipping_state,
            shipping_pincode=self.order.shipping_pincode,
        )

        with self.assertRaises(IntegrityError):
            Shipment.objects.create(
                shipment_number="SHP-UNIQUE-001",
                order=self.order,
                status=ShipmentStatus.PENDING,
                weight_in_grams=500,
                shipping_recipient_name=self.order.shipping_recipient_name,
                shipping_phone_number=self.order.shipping_phone_number,
                shipping_address_line_1=self.order.shipping_address_line_1,
                shipping_city=self.order.shipping_city,
                shipping_state=self.order.shipping_state,
                shipping_pincode=self.order.shipping_pincode,
            )

    def test_shipment_item_creation_and_constraints(self):
        shipment = Shipment.objects.create(
            shipment_number="SHP-ITEM-001",
            order=self.order,
            status=ShipmentStatus.PENDING,
            weight_in_grams=300,
            shipping_recipient_name=self.order.shipping_recipient_name,
            shipping_phone_number=self.order.shipping_phone_number,
            shipping_address_line_1=self.order.shipping_address_line_1,
            shipping_city=self.order.shipping_city,
            shipping_state=self.order.shipping_state,
            shipping_pincode=self.order.shipping_pincode,
        )

        item = ShipmentItem.objects.create(
            shipment=shipment,
            order_line_item=self.line,
            quantity=2,
        )
        self.assertEqual(item.quantity, 2)
        self.assertIn(self.line.sku, str(item))

        # Duplicate item for same shipment violates unique constraint
        with self.assertRaises(IntegrityError):
            ShipmentItem.objects.create(
                shipment=shipment,
                order_line_item=self.line,
                quantity=1,
            )

    def test_tracking_event_creation_and_ordering(self):
        shipment = Shipment.objects.create(
            shipment_number="SHP-TRACK-001",
            order=self.order,
            status=ShipmentStatus.PENDING,
            weight_in_grams=300,
            shipping_recipient_name=self.order.shipping_recipient_name,
            shipping_phone_number=self.order.shipping_phone_number,
            shipping_address_line_1=self.order.shipping_address_line_1,
            shipping_city=self.order.shipping_city,
            shipping_state=self.order.shipping_state,
            shipping_pincode=self.order.shipping_pincode,
        )

        now = timezone.now()
        event1 = ShipmentTrackingEvent.objects.create(
            shipment=shipment,
            status=ShipmentStatus.PENDING,
            location="Sirsi Hub",
            description="Package created",
            event_timestamp=now - timezone.timedelta(hours=1),
        )
        event2 = ShipmentTrackingEvent.objects.create(
            shipment=shipment,
            status=ShipmentStatus.IN_TRANSIT,
            location="Hubli Hub",
            description="In transit to destination",
            event_timestamp=now,
        )

        events = list(shipment.tracking_events.all())
        self.assertEqual(events[0].id, event2.id)  # newest first
        self.assertEqual(events[1].id, event1.id)
        self.assertIn(ShipmentStatus.IN_TRANSIT, str(event2))
