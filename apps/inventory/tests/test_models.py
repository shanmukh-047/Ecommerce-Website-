from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.inventory.models import MovementType, StockItem, StockMovement, StockReservation
from apps.inventory.tests.factories import create_variant


class InventoryModelTests(TestCase):
    def setUp(self):
        self.variant = create_variant()
        self.stock_item = StockItem.objects.create(variant=self.variant, quantity_on_hand=10)

    def test_stock_item_is_unique_per_variant(self):
        with self.assertRaises(IntegrityError):
            StockItem.objects.create(variant=self.variant)

    def test_stock_item_rejects_invalid_quantities_at_database_level(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            StockItem.objects.create(variant=create_variant("negative"), quantity_on_hand=-1)

        with self.assertRaises(IntegrityError), transaction.atomic():
            StockItem.objects.filter(pk=self.stock_item.pk).update(quantity_reserved=11)

    def test_reservation_quantity_must_be_positive(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            StockReservation.objects.create(
                stock_item=self.stock_item,
                quantity=0,
                expires_at=timezone.now() + timedelta(minutes=15),
            )

    def test_stock_movements_are_append_only(self):
        movement = StockMovement.objects.create(
            stock_item=self.stock_item,
            movement_type=MovementType.INBOUND,
            quantity_delta=10,
        )

        movement.note = "tamper attempt"
        with self.assertRaises(ValidationError):
            movement.save()
        with self.assertRaises(ValidationError):
            movement.delete()
