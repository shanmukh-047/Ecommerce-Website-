import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel
from apps.shipping.models import CourierProvider


class ReturnRequestStatus(models.TextChoices):
    PENDING_REVIEW = "PENDING_REVIEW", "Pending Staff Review"
    APPROVED = "APPROVED", "Approved for Pickup"
    REJECTED = "REJECTED", "Rejected"
    PICKUP_SCHEDULED = "PICKUP_SCHEDULED", "Reverse Pickup Scheduled"
    IN_TRANSIT = "IN_TRANSIT", "In Transit to Warehouse"
    RECEIVED = "RECEIVED", "Received at Warehouse"
    INSPECTED = "INSPECTED", "Inspection Completed"
    COMPLETED = "COMPLETED", "Completed (Resolved)"
    CANCELLED = "CANCELLED", "Cancelled by Customer"


class ReturnReason(models.TextChoices):
    DAMAGED_IN_TRANSIT = "DAMAGED_IN_TRANSIT", "Damaged in Transit / Crushed Packaging"
    DEFECTIVE_QUALITY = "DEFECTIVE_QUALITY", "Quality Defect / Moisture / Aroma Loss"
    WRONG_ITEM_DELIVERED = "WRONG_ITEM_DELIVERED", "Wrong Item / Variant Delivered"
    TAMPERED_SEAL = "TAMPERED_SEAL", "Tampered Safety Seal / Broken Seal"
    EXPIRED_OR_NEAR_EXPIRY = "EXPIRED_OR_NEAR_EXPIRY", "Expired or Close to Expiry Date"
    MISSING_ITEMS = "MISSING_ITEMS", "Missing Items / Shortage in Package"
    OTHER = "OTHER", "Other (Requires Staff Review)"


class ResolutionType(models.TextChoices):
    REFUND = "REFUND", "Monetary Refund & GST Credit Note"
    REPLACEMENT = "REPLACEMENT", "Free Replacement Shipment"


class InspectionResult(models.TextChoices):
    PASSED = "PASSED", "Passed Quality Inspection"
    FAILED = "FAILED", "Failed Quality Inspection"
    SCRAP_DAMAGED = "SCRAP_DAMAGED", "Authentic Defect / Food Safety Scrap"


class InventoryDisposition(models.TextChoices):
    RESTOCK = "RESTOCK", "Restock into Saleable Physical Inventory"
    DISCARD = "DISCARD", "Write-Off / Discard as Unsaleable Scrap"
    RETURN_TO_CUSTOMER = "RETURN_TO_CUSTOMER", "Reject & Return to Customer"


class ReturnShipmentStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Pickup Scheduled"
    OUT_FOR_PICKUP = "OUT_FOR_PICKUP", "Out for Pickup"
    PICKED_UP = "PICKED_UP", "Picked Up"
    IN_TRANSIT = "IN_TRANSIT", "In Transit to Warehouse"
    DELIVERED = "DELIVERED", "Delivered to Warehouse"
    FAILED_PICKUP = "FAILED_PICKUP", "Failed Pickup"
    CANCELLED = "CANCELLED", "Cancelled"


class ReturnRequest(TimeStampedModel):
    """
    Central Return Merchandise Authorization (RMA) entity governing post-delivery
    customer claims, policy window checks, staff review, and resolution execution.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_number = models.CharField(max_length=32, unique=True, db_index=True)
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="return_requests",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="return_requests",
    )
    status = models.CharField(
        max_length=30,
        choices=ReturnRequestStatus.choices,
        default=ReturnRequestStatus.PENDING_REVIEW,
        db_index=True,
    )
    requested_resolution = models.CharField(
        max_length=20,
        choices=ResolutionType.choices,
        default=ResolutionType.REFUND,
    )
    approved_resolution = models.CharField(
        max_length=20,
        choices=ResolutionType.choices,
        blank=True,
        default="",
    )
    reason = models.CharField(
        max_length=35,
        choices=ReturnReason.choices,
        default=ReturnReason.DEFECTIVE_QUALITY,
    )
    customer_notes = models.TextField(blank=True, default="")
    staff_review_notes = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    # Durable Idempotency Relationships
    replacement_order = models.OneToOneField(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replacement_for_return",
    )
    credit_note = models.OneToOneField(
        "invoices.CreditNote",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_return_request",
    )
    refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    refund_transaction_id = models.CharField(max_length=100, blank=True, default="")

    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        return (
            f"{self.return_number} (Order {self.order.order_number} - {self.get_status_display()})"
        )


class ReturnItem(TimeStampedModel):
    """
    Itemized product lines within a return request, tracking quantities
    and price snapshots for partial returns.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_request = models.ForeignKey(
        ReturnRequest,
        on_delete=models.CASCADE,
        related_name="items",
    )
    order_line_item = models.ForeignKey(
        "orders.OrderLineItem",
        on_delete=models.PROTECT,
        related_name="return_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    reason = models.CharField(
        max_length=35,
        choices=ReturnReason.choices,
        blank=True,
        default="",
    )
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(quantity__gt=0),
                name="return_item_quantity_positive",
            ),
        ]

    def __str__(self):
        return f"{self.return_request.return_number} - {self.order_line_item.sku} (Qty: {self.quantity})"


class ReturnEvidence(models.Model):
    """
    Photographic and video proof uploaded by customer to substantiate damage/defects.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_request = models.ForeignKey(
        ReturnRequest,
        on_delete=models.CASCADE,
        related_name="evidence",
    )
    file_url = models.URLField(max_length=500, blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Evidence for {self.return_request.return_number} ({self.description or 'No desc'})"


class ReturnShipment(TimeStampedModel):
    """
    Reverse logistics consignment record tracking courier pickup, reverse AWB,
    and transit milestones back to Sirsi warehouse.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_request = models.OneToOneField(
        ReturnRequest,
        on_delete=models.PROTECT,
        related_name="reverse_shipment",
    )
    shipment_number = models.CharField(max_length=32, unique=True, db_index=True)
    courier_name = models.CharField(
        max_length=50,
        choices=CourierProvider.choices,
        default=CourierProvider.MANUAL,
        db_index=True,
    )
    awb_number = models.CharField(max_length=100, blank=True, default="", db_index=True)
    status = models.CharField(
        max_length=30,
        choices=ReturnShipmentStatus.choices,
        default=ReturnShipmentStatus.SCHEDULED,
        db_index=True,
    )
    scheduled_pickup_date = models.DateField(null=True, blank=True)
    actual_pickup_date = models.DateTimeField(null=True, blank=True)
    received_at_warehouse = models.DateTimeField(null=True, blank=True)

    # Pickup Address Flat Snapshot (from Order destination)
    pickup_recipient_name = models.CharField(max_length=100)
    pickup_phone_number = models.CharField(max_length=15)
    pickup_address_line_1 = models.CharField(max_length=255)
    pickup_address_line_2 = models.CharField(max_length=255, blank=True, default="")
    pickup_landmark = models.CharField(max_length=100, blank=True, default="")
    pickup_city = models.CharField(max_length=100)
    pickup_state = models.CharField(max_length=50)
    pickup_pincode = models.CharField(max_length=6)
    tracking_notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reverse Shipment {self.shipment_number} - {self.get_status_display()}"


class ReturnInspection(models.Model):
    """
    Warehouse quality assurance inspection record enforcing FSSAI food safety
    segregation (saleable restock vs scrap write-off).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_request = models.OneToOneField(
        ReturnRequest,
        on_delete=models.PROTECT,
        related_name="inspection",
    )
    inspected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    result = models.CharField(
        max_length=20,
        choices=InspectionResult.choices,
        default=InspectionResult.PASSED,
        db_index=True,
    )
    disposition = models.CharField(
        max_length=30,
        choices=InventoryDisposition.choices,
        default=InventoryDisposition.RESTOCK,
        db_index=True,
    )
    quantity_passed = models.PositiveIntegerField(default=0)
    quantity_failed = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, default="")
    inspected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-inspected_at"]

    def __str__(self):
        return f"Inspection for {self.return_request.return_number}: {self.get_result_display()} ({self.get_disposition_display()})"
