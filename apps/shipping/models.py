import uuid

from django.db import models
from django.db.models import Q

from apps.accounts.models import IndianStates
from apps.core.models import TimeStampedModel


class ShipmentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    LABEL_GENERATED = "LABEL_GENERATED", "Label Generated"
    READY_FOR_PICKUP = "READY_FOR_PICKUP", "Ready for Pickup"
    IN_TRANSIT = "IN_TRANSIT", "In Transit"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for Delivery"
    DELIVERED = "DELIVERED", "Delivered"
    FAILED_DELIVERY = "FAILED_DELIVERY", "Failed Delivery"
    RETURNED_TO_ORIGIN = "RETURNED_TO_ORIGIN", "Returned to Origin (RTO)"
    CANCELLED = "CANCELLED", "Cancelled"


class CourierProvider(models.TextChoices):
    DELHIVERY = "DELHIVERY", "Delhivery"
    BLUEDART = "BLUEDART", "Blue Dart"
    SHIPROCKET = "SHIPROCKET", "Shiprocket"
    INDIAPOST = "INDIAPOST", "India Post"
    MANUAL = "MANUAL", "Manual / Internal Fleet"


class Shipment(TimeStampedModel):
    """
    Physical consignment entity tracking carrier allocation, AWB numbers,
    labels, volumetric packaging, and transit milestones for an order.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment_number = models.CharField(max_length=32, unique=True, db_index=True)
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="shipments",
    )
    status = models.CharField(
        max_length=30,
        choices=ShipmentStatus.choices,
        default=ShipmentStatus.PENDING,
        db_index=True,
    )
    courier_name = models.CharField(
        max_length=50,
        choices=CourierProvider.choices,
        default=CourierProvider.MANUAL,
        db_index=True,
    )
    awb_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
    )
    shipping_label_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
    )
    estimated_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)

    # Package Dimensions and Physical Weight
    weight_in_grams = models.PositiveIntegerField(
        help_text="Total package physical or volumetric weight in grams."
    )
    length_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    breadth_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Immutable Dispatch Address Snapshot (cloned from Order)
    shipping_recipient_name = models.CharField(max_length=100)
    shipping_phone_number = models.CharField(max_length=15)
    shipping_address_line_1 = models.CharField(max_length=255)
    shipping_address_line_2 = models.CharField(max_length=255, blank=True, default="")
    shipping_landmark = models.CharField(max_length=100, blank=True, default="")
    shipping_city = models.CharField(max_length=100, db_index=True)
    shipping_state = models.CharField(max_length=50, choices=IndianStates.choices, db_index=True)
    shipping_pincode = models.CharField(max_length=6, db_index=True)

    notes = models.TextField(blank=True, default="")
    cancellation_reason = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["awb_number"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(weight_in_grams__gt=0),
                name="shipment_weight_positive",
            ),
        ]

    def __str__(self):
        return f"Shipment {self.shipment_number} ({self.status}) - {self.courier_name}"


class ShipmentItem(TimeStampedModel):
    """
    Mapping table defining exactly which line items and quantities are packed
    inside this specific shipment carton.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name="items",
    )
    order_line_item = models.ForeignKey(
        "orders.OrderLineItem",
        on_delete=models.PROTECT,
        related_name="shipment_items",
    )
    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(quantity__gt=0),
                name="shipment_item_quantity_positive",
            ),
            models.UniqueConstraint(
                fields=["shipment", "order_line_item"],
                name="unique_shipment_line_item",
            ),
        ]

    def __str__(self):
        return f"{self.shipment.shipment_number}: {self.order_line_item.sku} x {self.quantity}"


class ShipmentTrackingEvent(models.Model):
    """
    Append-only milestone timeline capturing parcel scans, transit hubs,
    and delivery attempts.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name="tracking_events",
    )
    status = models.CharField(max_length=30, choices=ShipmentStatus.choices)
    location = models.CharField(max_length=150, blank=True, default="")
    description = models.CharField(max_length=500)
    event_timestamp = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-event_timestamp", "-created_at"]

    def __str__(self):
        return f"{self.shipment.shipment_number} [{self.status}] {self.location} at {self.event_timestamp}"
