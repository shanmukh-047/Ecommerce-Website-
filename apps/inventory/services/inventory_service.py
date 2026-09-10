from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.inventory.exceptions import InventoryConflict
from apps.inventory.models import (
    MovementType,
    ReservationStatus,
    StockItem,
    StockMovement,
    StockReservation,
)


class InventoryService:
    """Transactional inventory operations. PostgreSQL row locks serialize stock mutations."""

    @staticmethod
    def _locked_stock_item(variant) -> StockItem:
        try:
            return StockItem.objects.select_for_update().get(variant=variant)
        except StockItem.DoesNotExist:
            try:
                with transaction.atomic():
                    StockItem.objects.create(variant=variant)
            except IntegrityError:
                # Another transaction created the one-to-one record first.
                pass
            return StockItem.objects.select_for_update().get(variant=variant)

    @staticmethod
    def _movement(stock_item, movement_type, quantity_delta, reserved_delta, actor, **kwargs):
        return StockMovement.objects.create(
            stock_item=stock_item,
            movement_type=movement_type,
            quantity_delta=quantity_delta,
            reserved_quantity_delta=reserved_delta,
            actor=actor,
            **kwargs,
        )

    @classmethod
    @transaction.atomic
    def add_stock(
        cls,
        variant,
        quantity: int,
        actor=None,
        note: str = "",
        movement_type: str = MovementType.INBOUND,
        reference_type: str = "",
        reference_id=None,
    ) -> StockItem:
        if quantity <= 0:
            raise ValidationError("Restock quantity must be greater than zero.")

        stock_item = cls._locked_stock_item(variant)
        stock_item.quantity_on_hand += quantity
        stock_item.save(update_fields=["quantity_on_hand", "updated_at"])
        cls._movement(
            stock_item,
            movement_type,
            quantity,
            0,
            actor,
            reference_type=reference_type,
            reference_id=reference_id,
            note=note,
        )
        return stock_item

    @classmethod
    @transaction.atomic
    def adjust_stock(
        cls, stock_item_id, quantity_delta: int, actor=None, note: str = ""
    ) -> StockItem:
        if quantity_delta == 0:
            raise ValidationError("Stock adjustment cannot be zero.")

        stock_item = StockItem.objects.select_for_update().get(pk=stock_item_id)
        new_quantity = stock_item.quantity_on_hand + quantity_delta
        if new_quantity < stock_item.quantity_reserved:
            raise InventoryConflict("Adjustment would reduce stock below the reserved quantity.")

        stock_item.quantity_on_hand = new_quantity
        stock_item.save(update_fields=["quantity_on_hand", "updated_at"])
        cls._movement(stock_item, MovementType.ADJUSTMENT, quantity_delta, 0, actor, note=note)
        return stock_item

    @classmethod
    @transaction.atomic
    def reserve_stock(
        cls,
        variant,
        quantity: int,
        expires_at,
        actor=None,
        reference_type: str = "",
        reference_id=None,
    ) -> StockReservation:
        if quantity <= 0:
            raise ValidationError("Reservation quantity must be greater than zero.")
        if expires_at <= timezone.now():
            raise ValidationError("Reservation expiry must be in the future.")

        stock_item = cls._locked_stock_item(variant)
        if stock_item.quantity_available < quantity:
            raise InventoryConflict("Insufficient available inventory for this reservation.")

        stock_item.quantity_reserved += quantity
        stock_item.save(update_fields=["quantity_reserved", "updated_at"])
        reservation = StockReservation.objects.create(
            stock_item=stock_item,
            quantity=quantity,
            expires_at=expires_at,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        cls._movement(
            stock_item,
            MovementType.RESERVATION,
            0,
            quantity,
            actor,
            reference_type=reference_type,
            reference_id=reference_id or reservation.id,
        )
        return reservation

    @classmethod
    @transaction.atomic
    def release_reservation(
        cls, reservation_id, actor=None, expired: bool = False
    ) -> StockReservation:
        reservation = StockReservation.objects.select_for_update().get(pk=reservation_id)
        stock_item = StockItem.objects.select_for_update().get(pk=reservation.stock_item_id)

        if reservation.status in [ReservationStatus.RELEASED, ReservationStatus.EXPIRED]:
            return reservation
        if reservation.status == ReservationStatus.CONSUMED:
            raise InventoryConflict("A consumed reservation cannot be released.")

        stock_item.quantity_reserved -= reservation.quantity
        stock_item.save(update_fields=["quantity_reserved", "updated_at"])
        reservation.status = ReservationStatus.EXPIRED if expired else ReservationStatus.RELEASED
        reservation.released_at = timezone.now()
        reservation.save(update_fields=["status", "released_at", "updated_at"])
        cls._movement(
            stock_item,
            MovementType.EXPIRY if expired else MovementType.CANCELLATION,
            0,
            -reservation.quantity,
            actor,
            reference_type=reservation.reference_type,
            reference_id=reservation.reference_id or reservation.id,
        )
        return reservation

    @classmethod
    @transaction.atomic
    def consume_reservation(cls, reservation_id, actor=None) -> StockReservation:
        reservation = StockReservation.objects.select_for_update().get(pk=reservation_id)
        stock_item = StockItem.objects.select_for_update().get(pk=reservation.stock_item_id)

        if reservation.status == ReservationStatus.CONSUMED:
            return reservation
        if reservation.status != ReservationStatus.ACTIVE:
            raise InventoryConflict("Only an active reservation can be consumed.")
        if reservation.expires_at <= timezone.now():
            raise InventoryConflict("An expired reservation cannot be consumed.")

        stock_item.quantity_on_hand -= reservation.quantity
        stock_item.quantity_reserved -= reservation.quantity
        stock_item.save(update_fields=["quantity_on_hand", "quantity_reserved", "updated_at"])
        reservation.status = ReservationStatus.CONSUMED
        reservation.consumed_at = timezone.now()
        reservation.save(update_fields=["status", "consumed_at", "updated_at"])
        cls._movement(
            stock_item,
            MovementType.SALE,
            -reservation.quantity,
            -reservation.quantity,
            actor,
            reference_type=reservation.reference_type,
            reference_id=reservation.reference_id or reservation.id,
        )
        return reservation
