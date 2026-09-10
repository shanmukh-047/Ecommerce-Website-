import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.inventory.exceptions import InventoryConflict
from apps.inventory.models import MovementType, ReservationStatus, StockItem, StockMovement
from apps.inventory.services import InventoryService
from apps.inventory.tests.factories import create_variant


class InventoryServiceTests(TestCase):
    def setUp(self):
        self.variant = create_variant()

    def test_restock_creates_stock_item_and_ledger_entry(self):
        stock_item = InventoryService.add_stock(self.variant, 12, note="Initial count")

        self.assertEqual(stock_item.quantity_on_hand, 12)
        self.assertEqual(stock_item.quantity_available, 12)
        movement = StockMovement.objects.get(stock_item=stock_item)
        self.assertEqual(movement.movement_type, MovementType.INBOUND)
        self.assertEqual(movement.quantity_delta, 12)

    def test_adjustment_cannot_reduce_stock_below_reservations(self):
        stock_item = InventoryService.add_stock(self.variant, 10)
        InventoryService.reserve_stock(self.variant, 7, timezone.now() + timedelta(minutes=15))

        with self.assertRaises(InventoryConflict):
            InventoryService.adjust_stock(stock_item.id, -4)

        stock_item.refresh_from_db()
        self.assertEqual(stock_item.quantity_on_hand, 10)
        self.assertEqual(stock_item.quantity_reserved, 7)

    def test_zero_adjustment_is_rejected(self):
        stock_item = InventoryService.add_stock(self.variant, 10)
        with self.assertRaises(ValidationError):
            InventoryService.adjust_stock(stock_item.id, 0)

    def test_reserve_release_is_idempotent(self):
        InventoryService.add_stock(self.variant, 10)
        reservation = InventoryService.reserve_stock(
            self.variant, 4, timezone.now() + timedelta(minutes=15), reference_type="MANUAL"
        )

        released = InventoryService.release_reservation(reservation.id)
        repeated = InventoryService.release_reservation(reservation.id)

        self.assertEqual(released.status, ReservationStatus.RELEASED)
        self.assertEqual(repeated.status, ReservationStatus.RELEASED)
        stock_item = StockItem.objects.get(variant=self.variant)
        self.assertEqual(stock_item.quantity_reserved, 0)
        self.assertEqual(StockMovement.objects.filter(stock_item=stock_item).count(), 3)

    def test_unavailable_stock_cannot_be_reserved(self):
        InventoryService.add_stock(self.variant, 2)

        with self.assertRaises(InventoryConflict):
            InventoryService.reserve_stock(self.variant, 3, timezone.now() + timedelta(minutes=15))

    def test_consume_is_idempotent_and_prevents_release(self):
        InventoryService.add_stock(self.variant, 10)
        reservation = InventoryService.reserve_stock(
            self.variant, 3, timezone.now() + timedelta(minutes=15)
        )

        consumed = InventoryService.consume_reservation(reservation.id)
        repeated = InventoryService.consume_reservation(reservation.id)

        self.assertEqual(consumed.status, ReservationStatus.CONSUMED)
        self.assertEqual(repeated.status, ReservationStatus.CONSUMED)
        stock_item = StockItem.objects.get(variant=self.variant)
        self.assertEqual(stock_item.quantity_on_hand, 7)
        self.assertEqual(stock_item.quantity_reserved, 0)
        self.assertEqual(StockMovement.objects.filter(stock_item=stock_item).count(), 3)
        with self.assertRaises(InventoryConflict):
            InventoryService.release_reservation(reservation.id)

    def test_expired_reservation_cannot_be_consumed(self):
        InventoryService.add_stock(self.variant, 10)
        reservation = InventoryService.reserve_stock(
            self.variant, 3, timezone.now() + timedelta(minutes=15)
        )
        reservation.expires_at = timezone.now() - timedelta(seconds=1)
        reservation.save(update_fields=["expires_at"])

        with self.assertRaises(InventoryConflict):
            InventoryService.consume_reservation(reservation.id)

    def test_add_stock_with_explicit_movement_and_audit_references(self):
        ref_id = uuid.uuid4()
        stock_item = InventoryService.add_stock(
            variant=self.variant,
            quantity=15,
            note="Return RMA restock",
            movement_type=MovementType.INBOUND,
            reference_type="RETURN_RMA",
            reference_id=ref_id,
        )
        self.assertEqual(stock_item.quantity_on_hand, 15)
        movement = StockMovement.objects.filter(stock_item=stock_item).latest("created_at")
        self.assertEqual(movement.movement_type, MovementType.INBOUND)
        self.assertEqual(movement.reference_type, "RETURN_RMA")
        self.assertEqual(movement.reference_id, ref_id)
        self.assertEqual(movement.quantity_delta, 15)
        self.assertEqual(movement.note, "Return RMA restock")
