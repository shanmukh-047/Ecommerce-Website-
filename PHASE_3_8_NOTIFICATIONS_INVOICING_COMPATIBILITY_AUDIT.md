# PHASE 3.8 — NOTIFICATIONS & GST INVOICING ARCHITECTURAL AUDIT
## DOMAIN SEPARATION & FINANCIAL INTEGRITY AUDIT

**Project:** Bharath Masala Products E-Commerce Platform  
**Backend:** Django 5.0.6, DRF 3.16.0, PostgreSQL 16, Redis 7, Celery 5.4.0, django-celery-beat 2.6.0  
**Audit Date:** 2026-09-06T18:55:00+05:30  
**Status:** ARCHITECTURE AUDITED & AUTHORIZED FOR IMPLEMENTATION  
**Current Baseline:** 260 / 260 tests passing (100% Green across all 8 applications)

---

## 1. Domain Separation Decision: `apps.notifications` vs `apps.invoices`

In accordance with architectural review requirements, **GST Invoicing** and **Multi-Channel Notifications** are separated into two distinct, single-responsibility domains:

### 1.1 `apps.invoices` (Statutory Financial Accounting Context)
* **Responsibilities:**
  - Authoritative Tax Invoice generation for B2C retail and B2B wholesale orders.
  - Concurrency-safe sequential invoice numbering per financial year (e.g. `BMP-INV-202627-00001`).
  - Statutory Place of Supply (POS) and GST tax regime determination (Intra-state CGST+SGST vs Inter-state IGST).
  - Immutable financial snapshotting (seller details, buyer GSTIN/PAN, line item HSN codes, unit prices, taxable subtotals, tax amounts).
  - Zero-dependency PDF generation and printable HTML generation.
  - Customer invoice retrieval APIs (strictly IDOR-protected).
  - Staff invoice management APIs (protected by `IsStaffOrManager`).
  - Asynchronous invoice PDF generation Celery tasks.

### 1.2 `apps.notifications` (Multi-Channel Communications Context)
* **Responsibilities:**
  - Customer order communication across **Email**, **WhatsApp**, and **SMS**.
  - Event-driven lifecycle messaging (`ORDER_CONFIRMED`, `ORDER_SHIPPED`, `ORDER_DELIVERED`, `ORDER_CANCELLED`).
  - Pluggable channel provider adapters with deterministic mock adapters for testing.
  - Asynchronous background dispatch via Celery.
  - Message deduplication to prevent duplicate messages on webhook retries or task replays.
  - Complete notification audit logging (`NotificationLog`).

---

## 2. Critical Financial Data Rule & Existing Snapshots Inspection

A forensic inspection of existing models was conducted before designing invoice models:

### 2.1 Inspection Findings
1. **`OrderLineItem` (`apps.orders.models.py`)**:
   - ALREADY stores: `product_name`, `variant_name`, `sku`, `weight_in_grams`, `mrp`, `unit_price`, `line_subtotal`, `pricing_tier_applied`.
   - Linked to `variant` -> `product`.
2. **`Product` (`apps.catalog.models.py`)**:
   - ALREADY stores statutory metadata:
     - `hsn_code`: Statutory GST Harmonized System of Nomenclature code (e.g. "0904", "0801").
     - `gst_rate`: Statutory GST rate (e.g. `Decimal("5.00")` or `Decimal("12.00")`).
     - `fssai_license`: "11223344556677".
     - `packer_name`: "Bharath Masala Products".
     - `packer_address`: "Main Road, Thirthahalli, Shimoga District, Karnataka 577432".
3. **`Order` (`apps.orders.models.py`)**:
   - ALREADY stores: `items_subtotal`, `shipping_fee`, `tax_amount`, `grand_total`, `is_wholesale_order`.
   - Immutable shipping address snapshot: `shipping_recipient_name`, `shipping_phone_number`, `shipping_address_line_1`, `shipping_address_line_2`, `shipping_landmark`, `shipping_city`, `shipping_state`, `shipping_pincode`.
4. **`WholesaleProfile` (`apps.accounts.models.py`)**:
   - Stores B2B statutory data: `company_name`, `gstin`, `pan_number`.

### 2.2 Financial Integrity Directives for Invoicing
* **Rule 1: Never recalculate historical invoice values from live catalog prices.** Invoices strictly use the historical `OrderLineItem.unit_price`, `OrderLineItem.quantity`, and `OrderLineItem.line_subtotal`.
* **Rule 2: Never hardcode 5% GST.** The invoice reads the authoritative `gst_rate` from the product associated with each variant at the time of invoice creation.
* **Rule 3: Backward Tax Calculation.** In Indian consumer retail under Legal Metrology, product selling prices are inclusive of GST. The taxable value is derived backward:
  $$\text{Taxable Value} = \frac{\text{Line Subtotal}}{1 + (\text{GST Rate} / 100)}$$
  $$\text{Total Tax} = \text{Line Subtotal} - \text{Taxable Value}$$
* **Rule 4: State-based Tax Split.**
  - If `order.shipping_state == 'KA'` (Karnataka): **Intra-state supply** -> **CGST** ($\text{GST Rate} / 2$) + **SGST** ($\text{GST Rate} / 2$).
  - If `order.shipping_state != 'KA'`: **Inter-state supply** -> **IGST** ($\text{GST Rate}$).
* **Rule 5: B2B Wholesale Tax Invoicing.** When `order.is_wholesale_order` is True, buyer GSTIN, PAN, and Company Name are permanently snapshotted onto the `Invoice` so wholesale customers can claim statutory Input Tax Credit (ITC).

---

## 3. Database-Safe Concurrency & Idempotency Controls

### 3.1 Invoice Numbering Concurrency Protection
To prevent duplicate invoice numbers under concurrent Celery workers:
* A dedicated model `InvoiceSequence` holds the fiscal year counter:
  ```python
  class InvoiceSequence(models.Model):
      financial_year = models.CharField(max_length=10, primary_key=True)
      last_number = models.PositiveIntegerField(default=0)
  ```
* Number generation executes inside `@transaction.atomic` using:
  ```python
  seq = InvoiceSequence.objects.select_for_update().get_or_create(financial_year=fy)
  seq.last_number += 1
  seq.save(update_fields=["last_number"])
  invoice_number = f"BMP-INV-{fy_slug}-{seq.last_number:05d}"
  ```
* Unique database constraint on `Invoice.invoice_number` provides a second hard barrier.

### 3.2 Invoice Generation Idempotency
* `InvoiceService.generate_invoice(order)` first executes:
  ```python
  existing = Invoice.objects.filter(order=order).first()
  if existing:
      return existing
  ```
* Repeated calls for the same order are strictly idempotent and never generate duplicate invoices.

### 3.3 Notification Deduplication
* Key format: `f"{order.id}:{event_type}:{channel}"`.
* `NotificationLog` enforces a unique constraint on `deduplication_key`.
* If a notification with this key already has status `SENT`, further dispatches are skipped immediately.

---

## 4. Zero-Dependency PDF Generation Architecture

### 4.1 Dependency Audit
* Forensic check confirmed **no 3rd-party PDF library** (`reportlab`, `weasyprint`, `xhtml2pdf`) is installed.
* Per directive ("Confirm which PDF library is installed; do not introduce an unnecessary dependency"), we implement a pure-Python, zero-dependency `MinimalPDFWriter` in `apps/invoices/services/pdf_generator.py` conforming to standard PDF 1.4 specifications.
* In addition, `apps.invoices` provides a print-optimized, responsive HTML tax invoice template with Bharath Masala branding, suitable for browser viewing and printing.
* PDF generation is offloaded to a Celery task (`generate_invoice_pdf_task`), guaranteeing zero slowdown during checkout or payment processing.

---

## 5. Proposed Application Architecture & Structure

```
apps/
├── invoices/
│   ├── __init__.py
│   ├── apps.py
│   ├── exceptions.py
│   ├── models.py
│   ├── serializers.py
│   ├── admin.py
│   ├── tasks.py
│   ├── urls.py
│   ├── staff_urls.py
│   ├── views.py
│   ├── staff_views.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── invoice_service.py
│   │   └── pdf_generator.py
│   ├── templates/
│   │   └── invoices/
│   │       └── tax_invoice.html
│   └── tests/
│       ├── __init__.py
│       ├── factories.py
│       ├── test_models.py
│       ├── test_invoice_service.py
│       ├── test_pdf_generation.py
│       ├── test_customer_api.py
│       └── test_staff_api.py
└── notifications/
    ├── __init__.py
    ├── apps.py
    ├── exceptions.py
    ├── models.py
    ├── serializers.py
    ├── admin.py
    ├── tasks.py
    ├── staff_urls.py
    ├── staff_views.py
    ├── channels/
    │   ├── __init__.py
    │   ├── base.py
    │   ├── email_adapter.py
    │   ├── whatsapp_adapter.py
    │   ├── sms_adapter.py
    │   └── factory.py
    ├── services/
    │   ├── __init__.py
    │   └── notification_service.py
    ├── templates/
    │   └── notifications/
    │       ├── email/
    │       │   ├── order_confirmed.html
    │       │   ├── order_shipped.html
    │       │   ├── order_delivered.html
    │       │   └── order_cancelled.html
    │       └── text/
    │           ├── order_confirmed.txt
    │           ├── order_shipped.txt
    │           ├── order_delivered.txt
    │           └── order_cancelled.txt
    └── tests/
        ├── __init__.py
        ├── factories.py
        ├── test_models.py
        ├── test_channels.py
        ├── test_notification_service.py
        ├── test_tasks.py
        └── test_staff_api.py
```

---

## 6. Implementation Sequence

1. **Step 1: Invoicing Domain (`apps.invoices`)**:
   - Create app structure, models (`Invoice`, `InvoiceLineItem`, `InvoiceSequence`), and exceptions.
   - Implement `InvoiceService` with database-safe concurrency locking and statutory GST calculations.
   - Implement zero-dependency `MinimalPDFWriter` and print-ready HTML invoice template.
   - Implement asynchronous Celery task `generate_invoice_pdf_task`.
   - Implement customer IDOR-protected invoice views and staff management views.
2. **Step 2: Notifications Domain (`apps.notifications`)**:
   - Create app structure, models (`NotificationLog`), and channel adapters (`EmailChannelAdapter`, `WhatsAppChannelAdapter`, `SMSChannelAdapter`).
   - Implement `NotificationService` with deduplication and Celery async dispatch.
   - Implement notification templates (HTML + Text for Email, structured text for WhatsApp/SMS).
   - Implement staff notification log and resend APIs.
3. **Step 3: Configuration & URLs Registration**:
   - Add `"apps.invoices"` and `"apps.notifications"` to `LOCAL_APPS` in `config/settings/base.py`.
   - Register route namespaces in `config/urls.py`.
4. **Step 4: Migrations & Database Sync**:
   - Run `python3 manage.py makemigrations invoices notifications`.
   - Run `python3 manage.py migrate`.
5. **Step 5: Automated Testing**:
   - Write unit and integration tests across both domains.
   - Run `python3 manage.py test apps.invoices` and `python3 manage.py test apps.notifications`.
   - Run full test suite: `python3 manage.py test`.
6. **Step 6: Quality Gates & Completion Deliverables**:
   - Verify `check`, `makemigrations --check --dry-run`, `black`, and `ruff`.
   - Produce `PHASE_3_8_NOTIFICATIONS_INVOICING_COMPLETION_REPORT.md` and update `CURRENT_DEVELOPMENT_STATUS_REPORT.md`.
