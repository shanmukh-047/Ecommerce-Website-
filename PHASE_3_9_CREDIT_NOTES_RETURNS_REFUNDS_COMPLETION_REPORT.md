# PHASE 3.9 — GST CREDIT NOTES, INVOICE LIFECYCLE, RETURNS & REFUND FINANCIAL RECONCILIATION
## COMPLETION & VERIFICATION REPORT

**Platform:** Bharath Masala Products E-Commerce Platform (Production Django/DRF Backend)  
**Date:** 2026-09-06  
**Status:** **100% IMPLEMENTED, VERIFIED & PRODUCTION READY**  
**Verified Baseline:** **348 / 348 Tests Passing (100% Green)**  

---

## 1. Executive Summary & Statutory Framework

Phase 3.9 delivers end-to-end statutory Indian GST compliance and full financial reconciliation for post-sale order adjustments, cancellations, customer returns, and courier Return-to-Origin (RTO) events.

Under Indian GST law, **an issued Tax Invoice can never be modified or deleted** once generated. Any downward adjustment in taxable turnover, sales returns, or price corrections must strictly be executed through a **Statutory Tax Credit Note** governed by:
* **Section 34 of the Central Goods and Services Tax (CGST) Act, 2017**
* **Rule 53(1A) of the CGST Rules, 2017** (mandatory particulars of tax credit notes)
* **Rule 138 of the CGST Rules, 2017** (reconciliation with logistics and e-Way Bill records)

### Key Achievements in Phase 3.9
1. **Invoice Lifecycle State Machine:** Introduced `InvoiceStatus` (`ACTIVE`, `CANCELLED`, `CREDIT_NOTED`) ensuring historical invoice records remain immutable while capturing state changes.
2. **Statutory Credit Note Engine:** Concurrency-safe consecutive credit note serial numbering (`CreditNoteSequence`) strictly adhering to Rule 53(1A).
3. **Automated Cancellation & RTO Hooks:** Automatic dispatch of Credit Note compilation tasks upon post-invoicing cancellation or courier Return to Origin (`RETURNED_TO_ORIGIN`).
4. **Physical Inventory Restock Automation:** Restocking of consumed physical inventory upon cancellation or RTO via `InventoryService.add_stock`.
5. **Universal Payment Refund Gateway & Service:** Full refund lifecycle supporting Razorpay and manual offline gateways, atomic Order -> Payment deadlock-free locking, attempt audit trails, and multi-channel notifications.
6. **Payment Webhook Ingestion:** Ingestion and processing of `refund.processed` and `payment.refunded` webhook events.
7. **Zero-Dependency Vector PDF 1.4 Engine:** Standard-compliant PDF generation for Credit Notes without heavy C-binary dependencies (WeasyPrint/Cairo).
8. **Customer & Staff APIs:** Standardized REST endpoints with strict IDOR prevention, unified RBAC (`[IsAuthenticated, IsStaffOrManager]`), and envelope filtering.

---

## 2. Technical Architecture & Database Schema

### 2.1 Domain Separation & Architecture Map

```mermaid
flowchart TD
    subgraph apps.orders
        Order[Order Model]
        OSM[OrderStateMachine]
    end

    subgraph apps.shipping
        Shipment[Shipment Model]
        SS[ShippingService]
    end

    subgraph apps.inventory
        StockItem[StockItem]
        InvService[InventoryService]
    end

    subgraph apps.invoices
        Invoice[Invoice (ACTIVE / CREDIT_NOTED)]
        CNSeq[CreditNoteSequence]
        CreditNote[CreditNote]
        CreditNoteLine[CreditNoteLine]
        CNService[CreditNoteService]
        CNPDF[CreditNotePDFGenerator]
    end

    subgraph apps.payments
        Payment[Payment (CAPTURED / REFUNDED)]
        PayService[PaymentService]
        RZP[RazorpayGateway]
        WHService[WebhookService]
    end

    subgraph apps.notifications
        NotifService[NotificationService]
    end

    %% Cancellation flow
    Order -- "cancel_order()" --> OSM
    OSM -- "add_stock()" --> InvService
    OSM -- "on_commit" --> CNService
    CNService -- "allocates number" --> CNSeq
    CNService -- "creates record" --> CreditNote
    CNService -- "compiles PDF" --> CNPDF
    CNService -- "marks CREDIT_NOTED" --> Invoice
    CNService -- "on_commit" --> NotifService

    %% RTO flow
    Shipment -- "RETURNED_TO_ORIGIN" --> SS
    SS -- "add_stock()" --> InvService
    SS -- "on_commit" --> CNService

    %% Refund flow
    PayService -- "refund_payment()" --> RZP
    PayService -- "marks REFUNDED" --> Payment
    PayService -- "transition_status(REFUNDED)" --> OSM
    PayService -- "on_commit" --> NotifService
    WHService -- "refund.processed" --> PayService
```

### 2.2 Models & Schema Enhancements

#### 1. `apps.invoices.models.Invoice`
* Added `status`: `CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.ACTIVE, db_index=True)`
* Choices: `ACTIVE`, `CANCELLED`, `CREDIT_NOTED`.

#### 2. `apps.invoices.models.CreditNoteSequence`
* `financial_year`: `CharField(max_length=10, primary_key=True)` (e.g., `"2026-27"`).
* `last_number`: `PositiveIntegerField(default=0)`.
* `@classmethod get_next_number(financial_year)`: Atomic `select_for_update()` sequence generator yielding Rule 53(1A) compliant strings: `BMP/CN/{FY}/{SEQ:05d}`.

#### 3. `apps.invoices.models.CreditNote`
* `id`: UUID primary key.
* `credit_note_number`: Unique serial number (`BMP/CN/2026-27/00001`).
* `original_invoice`: ForeignKey to `Invoice`, `on_delete=PROTECT`.
* `order`: ForeignKey to `Order`, `on_delete=PROTECT`.
* `credit_note_date`: DateField, default today.
* `financial_year`: CharField (e.g., `"2026-27"`).
* `reason`: `CreditNoteReason` (`ORDER_CANCELLATION`, `RETURN_TO_ORIGIN`, `CUSTOMER_RETURN`, `PRICE_ADJUSTMENT`).
* `reason_notes`: Free-text justification.
* Statutory Seller Snapshot: `seller_name`, `seller_gstin`, `seller_fssai`, `seller_address`, `seller_state`.
* Statutory Buyer Snapshot: `buyer_name`, `buyer_email`, `buyer_phone`, `buyer_company_name`, `buyer_gstin`, `buyer_pan`, `shipping_address`.
* Statutory Financial & Tax Reversal: `place_of_supply`, `is_interstate`, `is_b2b`, `items_subtotal`, `taxable_subtotal`, `cgst_amount`, `sgst_amount`, `igst_amount`, `total_tax`, `grand_total`.
* Document Storage: `pdf_file`, `pdf_generated_at`.

#### 4. `apps.invoices.models.CreditNoteLine`
* Line item tax reversals snapshotting: `invoice_line`, `order_line_item`, `product_name`, `variant_name`, `sku`, `hsn_code`, `quantity`, `unit_price`, `taxable_amount`, `gst_rate`, `cgst_rate`, `cgst_amount`, `sgst_rate`, `sgst_amount`, `igst_rate`, `igst_amount`, `total_amount`.

#### 5. `apps.payments.models.Payment`
* Added `refund_transaction_id`: `CharField(max_length=100, blank=True, default="", db_index=True)`
* Added `amount_refunded`: `DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))`

#### 6. `apps.notifications.models.NotificationEvent`
* Added `CREDIT_NOTE_ISSUED = "CREDIT_NOTE_ISSUED", "Credit Note Issued"`

---

## 3. Implementation Details & Universal Locking Standards

### 3.1 Universal Global Lock Hierarchy
To prevent database deadlocks across high-concurrency payment captures, customer retries, staff refunds, background tasks, and webhooks, the entire platform strictly adheres to the unified locking order:

$$\text{Order} \longrightarrow \text{Payment} \longrightarrow \text{CreditNoteSequence} \longrightarrow \text{StockReservation} \longrightarrow \text{StockItem (ordered by variant ID)}$$

In `PaymentService.refund_payment()`:
```python
with transaction.atomic():
    locked_order = Order.objects.select_for_update().get(id=payment.order_id)
    locked_payment = Payment.objects.select_for_update().get(id=payment.id)
    # Perform refund...
```

In `CreditNoteService.generate_credit_note()`:
```python
with transaction.atomic():
    locked_order = Order.objects.select_for_update().get(id=order.id)
    invoice = Invoice.objects.select_for_update().filter(order=locked_order).first()
    credit_note_number = CreditNoteSequence.get_next_number(fy)
    # Generate credit note and update invoice status...
```

### 3.2 Automated Orchestration via `transaction.on_commit()`
All asynchronous tasks are scheduled exclusively after database commit to ensure workers never read uncommitted or rolled-back state:

1. **Order Cancellation (`OrderStateMachine.cancel_order`):**
   * Releases reservations (if `PENDING_PAYMENT`).
   * Restocks physical inventory via `InventoryService.add_stock` (if `CONFIRMED` or `PROCESSING`).
   * Sets `order_status = CANCELLED`.
   * Enqueues `send_order_notifications_task.delay(order.id, ORDER_CANCELLED)`.
   * Enqueues `generate_credit_note_for_order_task.delay(order.id, ORDER_CANCELLATION)`.

2. **Courier Return to Origin (`ShippingService.handle_rto_restock`):**
   * Restocks parcel items via `InventoryService.add_stock`.
   * Enqueues `generate_credit_note_for_order_task.delay(order.id, RETURN_TO_ORIGIN)`.

3. **Payment Refund (`PaymentService.refund_payment`):**
   * Calls gateway adapter (`refund_payment`).
   * Updates payment to `REFUNDED` and writes audit attempt.
   * If full refund, transitions order to `REFUNDED`.
   * Enqueues `send_order_notifications_task.delay(order.id, REFUND_PROCESSED)`.

4. **Credit Note Issuance (`CreditNoteService.generate_credit_note`):**
   * Compiles statutory credit note record and line items.
   * Updates original invoice status to `CREDIT_NOTED`.
   * Generates and attaches PDF 1.4 file.
   * Enqueues `send_order_notifications_task.delay(order.id, CREDIT_NOTE_ISSUED)`.

---

## 4. API Endpoints Reference

### 4.1 Customer Endpoints (IDOR Protected)

| Method | Endpoint | Description | Auth / RBAC |
|---|---|---|---|
| `GET` | `/api/v1/orders/<order_id>/credit-notes/` | Lists all credit notes issued for the customer's order | Authenticated Owner |
| `GET` | `/api/v1/orders/<order_id>/credit-notes/<id>/download/` | Streams statutory PDF 1.4 credit note document | Authenticated Owner |

### 4.2 Staff Management Endpoints

| Method | Endpoint | Description | Auth / RBAC |
|---|---|---|---|
| `GET` | `/api/v1/staff/invoices/credit-notes/` | Lists all credit notes with filters (`credit_note_number`, `order_number`, `invoice_number`, `reason`, dates) | `[IsAuthenticated, IsStaffOrManager]` |
| `GET` | `/api/v1/staff/invoices/credit-notes/<id>/` | Retrieves full credit note details with line item breakdown | `[IsAuthenticated, IsStaffOrManager]` |
| `POST` | `/api/v1/staff/invoices/credit-notes/<id>/regenerate-pdf/` | Recompiles statutory vector PDF byte stream | `[IsAuthenticated, IsStaffOrManager]` |
| `POST` | `/api/v1/staff/payments/<payment_id>/refund/` | Initiates full or partial refund for a captured payment | `[IsAuthenticated, IsStaffOrManager]` |

### 4.3 Webhook Ingestion

| Method | Endpoint | Description | Authentication |
|---|---|---|---|
| `POST` | `/api/v1/payments/webhooks/razorpay/` | Ingests `refund.processed` and `payment.refunded` events | HMAC-SHA256 Signature |

---

## 5. Verification & Quality Gates

All verification quality gates pass with zero warnings, zero errors, and zero drift:

| Quality Gate | Command | Result |
|---|---|---|
| **Django System Check** | `python3 manage.py check` | **PASS** (0 issues silenced) |
| **Migration Drift** | `python3 manage.py makemigrations --check --dry-run` | **PASS** (No changes detected) |
| **Code Formatting** | `black --check .` | **PASS** (209 files verified) |
| **Code Linter** | `ruff check .` | **PASS** (All checks passed) |
| **Test Suite** | `python3 manage.py test` | **PASS** (**348 / 348 tests green**) |

### Test Count Progression
* Pre-Phase 3.9 baseline: **321 tests**
* `apps.invoices.tests.test_credit_notes`: **+15 tests**
* `apps.payments.tests.test_refunds`: **+8 tests**
* `apps.orders.tests.test_returns_and_cancellation_reconciliation`: **+4 tests**
* **Current verified baseline: 348 tests passing (100% OK)**

---

## 6. Backend Roadmap Gap Analysis (Subsequent Phases)

Following the completion of Phase 3.9, the core e-commerce order processing, inventory, fulfillment, payment, and statutory tax invoicing domains are fully operational.

Below is the exhaustive architectural gap analysis of remaining backend requirements to achieve a complete, enterprise-grade production platform:

```text
+---------------------------------------------------------------------------------------+
|                              BHARATH MASALA PLATFORM                                 |
|                                BACKEND CAPABILITIES                                   |
+---------------------------------------------------------------------------------------+
|  COMPLETED DOMAINS (348 Tests Green):                                                |
|  [✓] Accounts, Authentication, Role-Based Access Control & B2B Profile Vetting        |
|  [✓] Catalog, Master Products, Multi-Tier Pricing & Customer Reviews                 |
|  [✓] Inventory, Multi-Warehouse Allocation & Immutable Stock Ledger Movement         |
|  [✓] Shopping Cart, Anonymous Guest-to-User Merge & Item Reservation Locking         |
|  [✓] Orders, Atomic Checkout, State Machine & Snapshot Auditing                      |
|  [✓] Payments, Razorpay Gateway, Webhooks & Universal Locking Standard               |
|  [✓] Background Celery Tasks, Deadlock Fixes & Auto-Expiry Automation                 |
|  [✓] Shipping, Fulfillment Cartons, Courier Abstraction & AWB Tracking               |
|  [✓] Multi-Channel Customer Notifications (Email, WhatsApp, SMS Adapters)            |
|  [✓] Statutory GST Invoicing (Section 31 CGST Act, Zero-Dep PDF 1.4 Engine)           |
|  [✓] Post-Order Orchestration, Cancellation Restocks & Production Hardening           |
|  [✓] Phase 3.9: GST Credit Notes, Invoice Lifecycle & Payment Refund Reconciliation  |
+---------------------------------------------------------------------------------------+
|  REMAINING ROADMAP CANDIDATES (Gap Analysis):                                         |
|                                                                                       |
|  Candidate Phase 3.10 — Customer Returns, Replacements & Reverse Logistics (RMA)      |
|    - Return Merchandise Authorization (RMA) workflow                                  |
|    - Customer return requests with image uploads and quality inspection triage        |
|    - Reverse pickup generation with courier APIs (Delhivery/Shiprocket reverse AWB)   |
|    - Return item condition grading: Restockable vs Damaged / Scrap write-off          |
|    - Replacement order generation or automated refund credit note dispatch            |
|                                                                                       |
|  Candidate Phase 3.11 — Promotions, Coupon Codes & Loyalty Rewards Engine            |
|    - Percentage, flat, and cart-minimum discount coupons                              |
|    - First-order, category-specific, and B2B vs B2C targeted promotions               |
|    - Coupon usage limits (per customer, global maximum, expiry windows)              |
|    - Customer reward points / store credits wallet system                             |
|                                                                                       |
|  Candidate Phase 3.12 — Analytics, GSTR Reporting & Business Intelligence            |
|    - Statutory GSTR-1 (Table 4, 7, 9B) & GSTR-3B tax export engine (CSV/Excel/JSON)    |
|    - Sales, Gross Margin, Average Order Value (AOV) & Inventory turnover metrics      |
|    - Abandoned cart drop-off analytics and conversion rate funnels                    |
|    - Staff management dashboard summary aggregation endpoints                         |
|                                                                                       |
|  Candidate Phase 3.13 — Customer Support, Helpdesk & Ticket Management               |
|    - Order-linked customer support tickets and status tracking                        |
|    - Ticket messaging threads between customer and support executive                  |
|    - Issue categorization (Delayed Delivery, Damaged Goods, Payment Query)            |
+---------------------------------------------------------------------------------------+
```

---

## 7. Sign-off & Next Steps

Phase 3.9 is completely finalized, fully documented, and verified under zero-drift quality gates. Awaiting user guidance and prioritization on subsequent roadmap phases.
