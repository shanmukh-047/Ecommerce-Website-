# GST CREDIT NOTE & INVOICE LIFECYCLE COMPATIBILITY AUDIT

**Target:** Indian Statutory GST Credit Notes, Order Cancellation, Post-Fulfillment Returns & Refunds  
**Domain:** `apps.invoices` / `apps.orders` / `apps.shipping` / `apps.payments`  
**Date:** September 2026  
**Status:** COMPLETED & READY FOR ARCHITECTURAL REVIEW  

---

### 1. Executive Summary & Legal Framework

Under **Section 34 of the Central Goods and Services Tax (CGST) Act, 2017**, once a registered supplier issues a tax invoice for the supply of goods, the invoice cannot simply be cancelled, deleted, or altered if goods are returned, order is cancelled post-issuance, or taxable value/tax charged is found to exceed the actual liability.

Instead, the supplier is statutorily mandated to issue a formal **Statutory GST Credit Note**.

```
                           Order Lifecycle & Invoice Point
                                         │
               ┌─────────────────────────┴─────────────────────────┐
               ▼                                                   ▼
       Pre-Confirmation                                   Post-Confirmation
     (PENDING_PAYMENT)                                 (CONFIRMED / PROCESSING)
               │                                                   │
      No Invoice Issued                                    Tax Invoice Issued
               │                                                   │
               ▼                                                   ▼
      Order Cancelled                                     Order Cancelled / Returned
               │                                                   │
  Inventory Released to Stock                             Statutory GST Credit Note
   No Tax Adjustment Needed                             Reverses CGST / SGST / IGST
                                                       Restores Stock via Inventory Ledger
```

---

### 2. Statutory Requirements Under Indian GST Law

#### 2.1 Legal Grounds for Issuing a Credit Note (Section 34(1) CGST Act)
A registered supplier may issue a credit note to the recipient in the following circumstances:
1. **Cancellation after Invoice Issuance:** The buyer cancels an order for which a tax invoice was already generated and recorded.
2. **Sales Return / RTO (Return to Origin):** Goods supplied are returned by the recipient (or returned un-delivered by courier).
3. **Deficiency in Goods / Price Adjustment:** Post-dispatch discount, damaged stock adjustment, or deficiency in goods received.

#### 2.2 Mandatory Particulars of a GST Credit Note (Rule 53(1A) CGST Rules)
Every Credit Note issued under Section 34 must contain:
1. Name, address, and GSTIN of the supplier (**Bharath Masala Products**).
2. Nature of the document: Prominently titled **"TAX CREDIT NOTE"**.
3. Consecutive serial number not exceeding 16 characters, unique for a financial year (e.g., `BMP/CN/2026-27/00001`).
4. Date of issue of the Credit Note.
5. Name, address, and GSTIN/PAN of the recipient (if registered B2B). If unregistered (B2C), name, delivery address, state, and pincode.
6. **Original Tax Invoice Reference:** Serial number and date of the corresponding original tax invoice (`BMP/2026-27/00001` dated `DD-MM-YYYY`).
7. HSN code and description of goods credited.
8. Taxable value, rate of tax, and breakup of tax credited (**CGST + SGST** for intra-state Karnataka, or **IGST** for inter-state).
9. Reason for issuance (Order Cancellation, Return to Origin, Quality Rejection, Post-Sale Discount).
10. Signature or digital authorization of the supplier.

#### 2.3 Reporting & GST Compliance Timelines
* **GSTR-1 Reporting:** Credit notes must be reported in Table 9B of GSTR-1 (Registered B2B) and Table 9B (Unregistered B2C).
* **GSTR-3B Tax Offset:** Output tax liability is reduced in Table 4(B)(2) of GSTR-3B in the month of issuance.
* **Statutory Deadline:** Credit notes must be issued and declared no later than the **30th day of November** following the end of the financial year, or the date of furnishing of the annual return (GSTR-9), whichever is earlier.

---

### 3. Current Architecture & Gap Analysis

#### 3.1 Invoice Generation Timing vs. Cancellation
* **Current State:**
  - When payment is captured, `OrderStateMachine.transition_status(CONFIRMED)` triggers `generate_invoice_for_order_task` via `transaction.on_commit`.
  - The tax invoice (`BMP/2026-27/xxxxx`) is created immediately with sequential lock.
  - If a customer or staff cancels the order while in `CONFIRMED` or `PROCESSING`:
    - `OrderStateMachine.cancel_order()` sets `order.order_status = CANCELLED` and restocks physical inventory via `InventoryService.add_stock()`.
    - **GAP:** The existing `Invoice` remains in the database in active state, with no linkage to cancellation, and no offsetting `CreditNote` is generated. This creates a statutory audit discrepancy where GST liability is declared on cancelled sales.

#### 3.2 Post-Fulfillment Returns (RTO & Customer Returns)
* **Current State:**
  - When courier marks a shipment `RETURNED_TO_ORIGIN`, `ShippingService.handle_rto_restock()` restocks damaged/undelivered spices into quarantine or active warehouse stock.
  - **GAP:** Output GST is not reversed because no Credit Note is generated for the RTO items.

#### 3.3 Refund Reconciliation (`apps.payments`)
* **Current State:**
  - `Payment` model tracks transaction IDs and capture status.
  - Full/partial refund issuance requires financial linkage between `RefundTransaction` and statutory `CreditNote`.

---

### 4. Proposed Technical Architecture for Credit Notes

#### 4.1 New Models in `apps.invoices`

```python
class CreditNoteSequence(TimeStampedModel):
    """
    Year-bounded sequence generator for statutory Credit Notes (Rule 53(1A)).
    Format: BMP/CN/YYYY-YY/XXXXX (max 16 characters).
    """
    financial_year = models.CharField(max_length=9, unique=True)
    last_sequence_number = models.PositiveIntegerField(default=0)


class CreditNoteReason(models.TextChoices):
    ORDER_CANCELLED = "ORDER_CANCELLED", "Order Cancelled Post-Invoicing"
    RETURN_TO_ORIGIN = "RETURN_TO_ORIGIN", "Courier Undelivered / Return to Origin"
    CUSTOMER_RETURN = "CUSTOMER_RETURN", "Customer Return / Defective Goods"
    PRICE_ADJUSTMENT = "PRICE_ADJUSTMENT", "Post-Sale Price Adjustment / Discount"


class CreditNote(TimeStampedModel):
    """
    Immutable statutory Credit Note under Section 34 of CGST Act.
    Strictly linked to original Invoice.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    credit_note_number = models.CharField(max_length=16, unique=True, db_index=True)
    original_invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.PROTECT,
        related_name="credit_notes",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="credit_notes",
    )
    credit_note_date = models.DateField(default=timezone.now)
    financial_year = models.CharField(max_length=9, db_index=True)
    reason = models.CharField(max_length=30, choices=CreditNoteReason.choices)
    reason_notes = models.TextField(blank=True, default="")
    
    # Statutory Place of Supply & GSTIN Snapshot
    place_of_supply = models.CharField(max_length=50)
    is_b2b = models.BooleanField(default=False)
    recipient_gstin = models.CharField(max_length=15, blank=True, default="")
    recipient_legal_name = models.CharField(max_length=255, blank=True, default="")

    # Tax totals credited
    total_taxable_amount = models.DecimalField(max_digits=12, decimal_places=2)
    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    grand_total_credited = models.DecimalField(max_digits=12, decimal_places=2)
    
    pdf_file = models.FileField(upload_to="credit_notes/", null=True, blank=True)


class CreditNoteLine(TimeStampedModel):
    credit_note = models.ForeignKey(CreditNote, on_delete=models.CASCADE, related_name="lines")
    original_invoice_line = models.ForeignKey(
        "invoices.InvoiceLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    product_name = models.CharField(max_length=255)
    variant_name = models.CharField(max_length=100)
    sku = models.CharField(max_length=50)
    hsn_code = models.CharField(max_length=10)
    quantity_credited = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    taxable_amount = models.DecimalField(max_digits=10, decimal_places=2)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2)
    cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    igst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    igst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
```

#### 4.2 Automated Orchestration Hooks
When an order is cancelled:
1. Check if `Invoice.objects.filter(order=order).exists()`:
   - If **NO**: Order was cancelled before confirmation (e.g. `PENDING_PAYMENT`). No credit note is needed.
   - If **YES**: Trigger `generate_credit_note_for_order_task.delay(str(order.id), reason=CreditNoteReason.ORDER_CANCELLED)` via `transaction.on_commit`.
2. Generate PDF document for the Credit Note formatted according to Rule 53(1A).
3. Dispatch customer notification with Credit Note PDF attachment.

---

### 5. Audit Conclusion & Readiness Assessment

1. **Production Hardening (Current Stage):**
   - The current production hardening (orchestrating `CONFIRMED -> Invoice`, `SHIPPED -> Notification`, `DELIVERED -> Notification`, and `CANCELLED -> Notification`) is complete, robust, and correctly uses `transaction.on_commit`.
2. **Phase 3.9 Dependency:**
   - Full Credit Note model and sequence implementation should be scheduled as a dedicated financial module (either as Phase 3.8.1 or alongside Returns & Refunds in Phase 3.9).
   - The architecture documented in this audit is fully backward-compatible with all existing tables, foreign keys, and Celery task interfaces.
