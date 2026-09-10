import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import IndianStates
from apps.core.models import TimeStampedModel


class InvoiceSequence(models.Model):
    """
    Database-level atomic sequence tracker guaranteeing collision-free,
    consecutive tax invoice numbering across concurrent Celery workers.
    """

    financial_year = models.CharField(max_length=10, primary_key=True)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Invoice Sequence"
        verbose_name_plural = "Invoice Sequences"

    def __str__(self):
        return f"{self.financial_year}: #{self.last_number}"


class InvoiceStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    PARTIALLY_CREDIT_NOTED = "PARTIALLY_CREDIT_NOTED", "Partially Credit Noted"
    CREDIT_NOTED = "CREDIT_NOTED", "Credit Noted"
    CANCELLED = "CANCELLED", "Cancelled"


class Invoice(TimeStampedModel):
    """
    Statutory Indian GST Tax Invoice entity snapshotting seller credentials,
    buyer identity, place of supply, and precise CGST/SGST/IGST tax breakdowns.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    status = models.CharField(
        max_length=30,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.ACTIVE,
        db_index=True,
    )
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="invoice",
    )
    invoice_date = models.DateField(default=timezone.now, db_index=True)

    # Statutory Seller Snapshot
    seller_name = models.CharField(
        max_length=200,
        default=getattr(settings, "INVOICE_SELLER_NAME", "Bharath Masala Products"),
    )
    seller_gstin = models.CharField(
        max_length=15,
        default=getattr(settings, "INVOICE_SELLER_GSTIN", "29AAAAA0000A1Z5"),
    )
    seller_fssai = models.CharField(
        max_length=20,
        default=getattr(settings, "INVOICE_SELLER_FSSAI", "11223344556677"),
    )
    seller_address = models.TextField(
        default=getattr(
            settings,
            "INVOICE_SELLER_ADDRESS",
            "Main Road, Thirthahalli, Shimoga District, Karnataka 577432",
        )
    )
    seller_state = models.CharField(
        max_length=50,
        choices=IndianStates.choices,
        default=IndianStates.KARNATAKA,
    )

    # Buyer Snapshot (Retail or Wholesale)
    buyer_name = models.CharField(max_length=150)
    buyer_email = models.CharField(max_length=150)
    buyer_phone = models.CharField(max_length=15)
    buyer_company_name = models.CharField(max_length=200, blank=True, default="")
    buyer_gstin = models.CharField(max_length=15, blank=True, default="")
    buyer_pan = models.CharField(max_length=10, blank=True, default="")
    shipping_address = models.TextField()

    # Place of Supply and GST Taxation Breakdown
    place_of_supply = models.CharField(max_length=50, choices=IndianStates.choices, db_index=True)
    is_interstate = models.BooleanField(default=False, db_index=True)
    is_b2b = models.BooleanField(default=False, db_index=True)

    items_subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    total_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Order-level discount deducted from invoice gross value.",
    )
    taxable_subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    igst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)

    payment_method = models.CharField(max_length=50, blank=True, default="")
    payment_transaction_id = models.CharField(max_length=100, blank=True, default="")

    pdf_file = models.FileField(upload_to="invoices/%Y/", blank=True, null=True)
    pdf_generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-invoice_date", "-created_at"]
        indexes = [
            models.Index(fields=["invoice_number"]),
            models.Index(fields=["invoice_date", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(grand_total__gte=0),
                name="invoice_grand_total_non_negative",
            ),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number} - Order {self.order.order_number}"


class InvoiceLineItem(TimeStampedModel):
    """
    Statutory line item tax breakdown recording HSN, taxable value,
    statutory GST rate, and CGST/SGST/IGST tax splits.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    order_line_item = models.ForeignKey(
        "orders.OrderLineItem",
        on_delete=models.PROTECT,
        related_name="invoice_lines",
    )
    product_name = models.CharField(max_length=200)
    variant_name = models.CharField(max_length=100)
    sku = models.CharField(max_length=64)
    hsn_code = models.CharField(max_length=10, db_index=True)
    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Allocated discount for this line item.",
    )
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2)

    cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    igst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    igst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(quantity__gt=0),
                name="invoice_line_quantity_positive",
            ),
        ]

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.sku} (HSN {self.hsn_code})"


class CreditNoteSequence(models.Model):
    """
    Database-level atomic sequence tracker guaranteeing collision-free,
    consecutive credit note numbering (BMP/CN/YYYY-YY/XXXXX) under Rule 53(1A).
    """

    financial_year = models.CharField(max_length=10, primary_key=True)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Credit Note Sequence"
        verbose_name_plural = "Credit Note Sequences"

    def __str__(self):
        return f"CN-{self.financial_year}: #{self.last_number}"

    @classmethod
    def get_next_number(cls, financial_year: str) -> str:
        with transaction.atomic():
            seq, _ = cls.objects.select_for_update().get_or_create(financial_year=financial_year)
            seq.last_number += 1
            seq.save(update_fields=["last_number"])
            return f"BMP/CN/{financial_year}/{seq.last_number:05d}"


class CreditNoteReason(models.TextChoices):
    ORDER_CANCELLATION = "ORDER_CANCELLATION", "Order Cancelled Post-Invoicing"
    RETURN_TO_ORIGIN = "RETURN_TO_ORIGIN", "Courier Undelivered / Return to Origin"
    CUSTOMER_RETURN = "CUSTOMER_RETURN", "Customer Return / Defective Goods"
    PRICE_ADJUSTMENT = "PRICE_ADJUSTMENT", "Post-Sale Price Adjustment / Discount"


class CreditNote(TimeStampedModel):
    """
    Statutory Indian GST Tax Credit Note entity (Section 34 CGST Act, Rule 53(1A)).
    Strictly references the original tax invoice and adjusts output tax liability.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    credit_note_number = models.CharField(max_length=50, unique=True, db_index=True)
    original_invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name="credit_notes",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="credit_notes",
    )
    credit_note_date = models.DateField(default=timezone.now, db_index=True)
    financial_year = models.CharField(max_length=10, db_index=True)
    reason = models.CharField(
        max_length=30,
        choices=CreditNoteReason.choices,
        default=CreditNoteReason.ORDER_CANCELLATION,
        db_index=True,
    )
    reason_notes = models.TextField(blank=True, default="")

    # Statutory Seller Snapshot
    seller_name = models.CharField(max_length=200)
    seller_gstin = models.CharField(max_length=15)
    seller_fssai = models.CharField(max_length=20)
    seller_address = models.TextField()
    seller_state = models.CharField(
        max_length=50,
        choices=IndianStates.choices,
        default=IndianStates.KARNATAKA,
    )

    # Buyer Snapshot
    buyer_name = models.CharField(max_length=150)
    buyer_email = models.CharField(max_length=150)
    buyer_phone = models.CharField(max_length=15)
    buyer_company_name = models.CharField(max_length=200, blank=True, default="")
    buyer_gstin = models.CharField(max_length=15, blank=True, default="")
    buyer_pan = models.CharField(max_length=10, blank=True, default="")
    shipping_address = models.TextField()

    # Place of Supply and GST Tax Breakdown Credited
    place_of_supply = models.CharField(max_length=50, choices=IndianStates.choices, db_index=True)
    is_interstate = models.BooleanField(default=False, db_index=True)
    is_b2b = models.BooleanField(default=False, db_index=True)

    items_subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    taxable_subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    igst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)

    pdf_file = models.FileField(upload_to="credit_notes/%Y/", blank=True, null=True)
    pdf_generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-credit_note_date", "-created_at"]
        indexes = [
            models.Index(fields=["credit_note_number"]),
            models.Index(fields=["credit_note_date", "-created_at"]),
            models.Index(fields=["order", "reason"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(grand_total__gte=0),
                name="credit_note_grand_total_non_negative",
            ),
        ]

    def __str__(self):
        return f"Credit Note {self.credit_note_number} for Invoice {self.original_invoice.invoice_number}"


class CreditNoteLine(TimeStampedModel):
    """
    Statutory line item tax breakdown for credit notes.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    credit_note = models.ForeignKey(
        CreditNote,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    invoice_line = models.ForeignKey(
        "invoices.InvoiceLineItem",
        on_delete=models.PROTECT,
        related_name="credit_lines",
        null=True,
        blank=True,
    )
    order_line_item = models.ForeignKey(
        "orders.OrderLineItem",
        on_delete=models.PROTECT,
        related_name="credit_lines",
        null=True,
        blank=True,
    )
    product_name = models.CharField(max_length=200)
    variant_name = models.CharField(max_length=100)
    sku = models.CharField(max_length=64)
    hsn_code = models.CharField(max_length=10, db_index=True)
    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2)

    cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    igst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    igst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(quantity__gt=0),
                name="credit_note_line_quantity_positive",
            ),
        ]

    def __str__(self):
        return f"{self.credit_note.credit_note_number} - {self.sku} (HSN {self.hsn_code})"
