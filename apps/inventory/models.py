import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.catalog.models import ProductVariant
from apps.core.models import TimeStampedModel


class StockItem(TimeStampedModel):
    """The single canonical inventory record for a product variant."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.OneToOneField(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name="stock_item",
    )
    quantity_on_hand = models.PositiveIntegerField(default=0)
    quantity_reserved = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["variant__sku"]
        constraints = [
            models.CheckConstraint(
                check=Q(quantity_on_hand__gte=0),
                name="inventory_on_hand_non_negative",
            ),
            models.CheckConstraint(
                check=Q(quantity_reserved__gte=0),
                name="inventory_reserved_non_negative",
            ),
            models.CheckConstraint(
                check=Q(quantity_on_hand__gte=models.F("quantity_reserved")),
                name="inventory_reserved_not_above_on_hand",
            ),
        ]

    @property
    def quantity_available(self) -> int:
        return self.quantity_on_hand - self.quantity_reserved

    def __str__(self):
        return f"{self.variant.sku}: {self.quantity_available} available"


class MovementType(models.TextChoices):
    INBOUND = "INBOUND", "Inbound stock"
    SALE = "SALE", "Sale"
    RESERVATION = "RESERVATION", "Reservation"
    CANCELLATION = "CANCELLATION", "Reservation cancellation"
    EXPIRY = "EXPIRY", "Reservation expiry"
    ADJUSTMENT = "ADJUSTMENT", "Stock adjustment"


class StockMovement(TimeStampedModel):
    """Append-only ledger of physical and reserved inventory changes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock_item = models.ForeignKey(StockItem, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=20, choices=MovementType.choices, db_index=True)
    quantity_delta = models.IntegerField(
        help_text="Physical quantity-on-hand change; zero for pure reservation events."
    )
    reserved_quantity_delta = models.IntegerField(
        default=0,
        help_text="Reserved allocation change; zero for pure physical stock events.",
    )
    reference_type = models.CharField(max_length=30, blank=True, default="")
    reference_id = models.UUIDField(null=True, blank=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inventory_movements",
    )
    note = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["stock_item", "created_at"]),
            models.Index(fields=["movement_type", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Stock movements are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Stock movements are immutable and cannot be deleted.")

    def __str__(self):
        return f"{self.stock_item.variant.sku} {self.movement_type} ({self.quantity_delta:+d})"


class ReservationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    RELEASED = "RELEASED", "Released"
    CONSUMED = "CONSUMED", "Consumed"
    EXPIRED = "EXPIRED", "Expired"


class StockReservation(TimeStampedModel):
    """Reserved stock with no dependency on future cart or order applications."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock_item = models.ForeignKey(StockItem, on_delete=models.PROTECT, related_name="reservations")
    reference_type = models.CharField(
        max_length=30,
        blank=True,
        default="",
        help_text="Future owner type, such as CART or ORDER; deliberately not a foreign key.",
    )
    reference_id = models.UUIDField(null=True, blank=True, db_index=True)
    quantity = models.PositiveIntegerField()
    expires_at = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.ACTIVE,
        db_index=True,
    )
    released_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["expires_at"]
        indexes = [
            models.Index(fields=["status", "expires_at"]),
            models.Index(fields=["stock_item", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(quantity__gt=0),
                name="inventory_reservation_quantity_positive",
            )
        ]

    def __str__(self):
        return f"{self.stock_item.variant.sku}: {self.quantity} ({self.status})"
