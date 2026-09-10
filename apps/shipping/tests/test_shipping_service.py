from django.test import TestCase

from apps.inventory.models import StockItem
from apps.inventory.services import InventoryService
from apps.inventory.tests.factories import create_variant
from apps.orders.exceptions import OrderConflict
from apps.orders.models import OrderStatus
from apps.orders.services import OrderStateMachine
from apps.orders.tests.factories import (
    add_to_cart,
    create_order_address,
    create_order_user,
    create_staff_user,
)
from apps.shipping.exceptions import ShipmentConflict
from apps.shipping.models import CourierProvider, ShipmentStatus
from apps.shipping.services import ShippingService
from apps.shipping.tests.factories import create_shipping_test_order


class ShippingServiceTests(TestCase):
    def setUp(self):
        self.user = create_order_user(email="service_user@example.com", phone="9876543221")
        self.staff = create_staff_user(email="shipping_staff@example.com", phone="9876543222")
        self.variant1 = create_variant("ship_service_1")
        self.variant2 = create_variant("ship_service_2")
        self.address = create_order_address(self.user)

        # Provide stock
        InventoryService.add_stock(self.variant1, 50)
        InventoryService.add_stock(self.variant2, 50)

        add_to_cart(self.user, self.variant1, 5)
        add_to_cart(self.user, self.variant2, 2)

        from apps.orders.services import CheckoutService

        self.order = CheckoutService.create_order_from_cart(
            user=self.user,
            shipping_address_id=self.address.id,
        )
        # Advance order to CONFIRMED
        OrderStateMachine.transition_status(
            self.order,
            OrderStatus.CONFIRMED,
            actor=self.staff,
            notes="Payment confirmed",
        )

    def test_create_default_full_shipment(self):
        shipment = ShippingService.create_shipment(
            order=self.order,
            courier_name=CourierProvider.BLUEDART,
            notes="Handle with care - whole spices",
            actor=self.staff,
        )

        self.assertEqual(shipment.order_id, self.order.id)
        self.assertEqual(shipment.status, ShipmentStatus.PENDING)
        self.assertEqual(shipment.courier_name, CourierProvider.BLUEDART)
        self.assertEqual(shipment.items.count(), 2)
        self.assertEqual(shipment.tracking_events.count(), 1)
        self.assertEqual(shipment.shipping_city, "Sirsi")

        # Order should automatically advance to PROCESSING
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.PROCESSING)

    def test_create_shipment_blocked_for_unconfirmed_orders(self):
        # Create unconfirmed PENDING_PAYMENT order
        unconfirmed = create_shipping_test_order(
            user=self.user,
            variant=create_variant("unconfirmed_var"),
            target_status=OrderStatus.PENDING_PAYMENT,
        )
        with self.assertRaises(ShipmentConflict) as ctx:
            ShippingService.create_shipment(order=unconfirmed)
        self.assertIn("Order must be CONFIRMED or PROCESSING", str(ctx.exception))

    def test_partial_fulfillment_and_multi_shipment(self):
        lines = list(self.order.lines.all())
        line1 = lines[0] if lines[0].variant_id == self.variant1.id else lines[1]
        line2 = lines[1] if lines[1].variant_id == self.variant2.id else lines[0]

        # 1. Create Shipment 1: Only 3 of variant 1 (out of 5)
        shipment1 = ShippingService.create_shipment(
            order=self.order,
            items_data=[{"order_line_item_id": line1.id, "quantity": 3}],
            actor=self.staff,
        )
        self.assertEqual(shipment1.items.count(), 1)
        self.assertEqual(shipment1.items.first().quantity, 3)

        # Verify fulfillment summary
        summary = ShippingService.get_order_fulfillment_summary(self.order)
        self.assertFalse(summary["is_fully_fulfilled"])

        # 2. Over-fulfillment attempt: shipping 3 more of line 1 (only 2 remaining)
        with self.assertRaises(ShipmentConflict) as ctx:
            ShippingService.create_shipment(
                order=self.order,
                items_data=[{"order_line_item_id": line1.id, "quantity": 3}],
            )
        self.assertIn("exceeds remaining unfulfilled quantity", str(ctx.exception))

        # 3. Create Shipment 2: 2 of variant 1 and 2 of variant 2 (completes fulfillment)
        shipment2 = ShippingService.create_shipment(
            order=self.order,
            items_data=[
                {"order_line_item_id": line1.id, "quantity": 2},
                {"order_line_item_id": line2.id, "quantity": 2},
            ],
            actor=self.staff,
        )
        self.assertEqual(shipment2.items.count(), 2)

        # Verify order is now fully allocated
        summary2 = ShippingService.get_order_fulfillment_summary(self.order)
        self.assertTrue(summary2["is_fully_fulfilled"])

        # 4. Attempting to create another shipment should fail
        with self.assertRaises(ShipmentConflict) as ctx:
            ShippingService.create_shipment(order=self.order)
        self.assertIn("Order is already fully fulfilled", str(ctx.exception))

    def test_carrier_allocation_and_label_generation(self):
        shipment = ShippingService.create_shipment(order=self.order)
        self.assertEqual(shipment.status, ShipmentStatus.PENDING)
        self.assertEqual(shipment.awb_number, "")

        shipment = ShippingService.book_carrier_and_generate_label(
            shipment=shipment,
            courier_name=CourierProvider.DELHIVERY,
            actor=self.staff,
        )
        self.assertEqual(shipment.status, ShipmentStatus.LABEL_GENERATED)
        self.assertEqual(shipment.courier_name, CourierProvider.DELHIVERY)
        self.assertTrue(shipment.awb_number.startswith("BMP-AWB-"))
        self.assertIn("labels", shipment.shipping_label_url)
        self.assertEqual(shipment.tracking_events.count(), 2)

    def test_order_status_sync_on_dispatch_and_delivery(self):
        shipment = ShippingService.create_shipment(order=self.order)
        shipment = ShippingService.book_carrier_and_generate_label(shipment=shipment)

        # Advance to READY_FOR_PICKUP
        shipment = ShippingService.transition_shipment_status(
            shipment=shipment,
            to_status=ShipmentStatus.READY_FOR_PICKUP,
            location="Sirsi Warehouse",
            description="Carton packed and manifesting completed.",
        )

        # Advance to IN_TRANSIT -> Order becomes SHIPPED
        shipment = ShippingService.transition_shipment_status(
            shipment=shipment,
            to_status=ShipmentStatus.IN_TRANSIT,
            location="Hubli Sorting Facility",
            description="Handed over to carrier.",
            actor=self.staff,
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.SHIPPED)
        self.assertIsNotNone(self.order.shipped_at)

        # Advance to OUT_FOR_DELIVERY
        shipment = ShippingService.transition_shipment_status(
            shipment=shipment,
            to_status=ShipmentStatus.OUT_FOR_DELIVERY,
            location="Customer City Hub",
            description="Out with delivery agent.",
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.SHIPPED)

        # Advance to DELIVERED -> Order becomes DELIVERED
        shipment = ShippingService.transition_shipment_status(
            shipment=shipment,
            to_status=ShipmentStatus.DELIVERED,
            location="Customer Doorstep",
            description="Delivered and signature received.",
            actor=self.staff,
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.DELIVERED)
        self.assertIsNotNone(self.order.delivered_at)

    def test_idempotent_status_transition(self):
        shipment = ShippingService.create_shipment(order=self.order)
        shipment = ShippingService.transition_shipment_status(
            shipment=shipment,
            to_status=ShipmentStatus.READY_FOR_PICKUP,
        )
        count_before = shipment.tracking_events.count()

        # Call again with identical status
        shipment2 = ShippingService.transition_shipment_status(
            shipment=shipment,
            to_status=ShipmentStatus.READY_FOR_PICKUP,
        )
        self.assertEqual(shipment2.status, ShipmentStatus.READY_FOR_PICKUP)
        self.assertEqual(shipment2.tracking_events.count(), count_before)

    def test_invalid_status_transition_raises_conflict(self):
        shipment = ShippingService.create_shipment(order=self.order)
        # Cannot jump straight from PENDING to DELIVERED
        with self.assertRaises(ShipmentConflict):
            ShippingService.transition_shipment_status(
                shipment=shipment,
                to_status=ShipmentStatus.DELIVERED,
            )

    def test_cancel_shipment_before_dispatch(self):
        shipment = ShippingService.create_shipment(order=self.order)
        shipment = ShippingService.cancel_shipment(
            shipment=shipment,
            reason="Carton repack required",
            actor=self.staff,
        )
        self.assertEqual(shipment.status, ShipmentStatus.CANCELLED)
        self.assertEqual(shipment.cancellation_reason, "Carton repack required")

        # After cancellation, items can be fulfilled in a new shipment
        new_shipment = ShippingService.create_shipment(order=self.order)
        self.assertEqual(new_shipment.status, ShipmentStatus.PENDING)

    def test_dispatched_shipment_blocks_order_cancellation(self):
        shipment = ShippingService.create_shipment(order=self.order)
        ShippingService.transition_shipment_status(
            shipment=shipment,
            to_status=ShipmentStatus.IN_TRANSIT,
            actor=self.staff,
        )
        self.order.refresh_from_db()

        # Attempt to cancel order should be blocked
        with self.assertRaises(OrderConflict) as ctx:
            OrderStateMachine.cancel_order(self.order, actor=self.staff)
        self.assertIn("shipment(s) are already in transit or delivered", str(ctx.exception))

    def test_rto_restocks_physical_inventory(self):
        # At CONFIRMED, inventory was consumed. On-hand was 50 - 5 = 45 for variant 1.
        stock1 = StockItem.objects.get(variant=self.variant1)
        self.assertEqual(stock1.quantity_on_hand, 45)

        shipment = ShippingService.create_shipment(order=self.order)
        ShippingService.transition_shipment_status(
            shipment=shipment,
            to_status=ShipmentStatus.IN_TRANSIT,
            actor=self.staff,
        )
        ShippingService.transition_shipment_status(
            shipment=shipment,
            to_status=ShipmentStatus.FAILED_DELIVERY,
            description="Address not found",
        )
        # Mark RETURNED_TO_ORIGIN
        ShippingService.transition_shipment_status(
            shipment=shipment,
            to_status=ShipmentStatus.RETURNED_TO_ORIGIN,
            location="Sirsi Warehouse",
            description="Consignment returned to warehouse and restocked.",
            actor=self.staff,
        )

        stock1_after = StockItem.objects.get(variant=self.variant1)
        self.assertEqual(stock1_after.quantity_on_hand, 50)  # Restocked by 5!
