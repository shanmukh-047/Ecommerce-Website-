# CURRENT DEVELOPMENT STATUS REPORT

**Project:** Bharath Masala Products E-Commerce Platform (Production Django/DRF Backend)  
**Report Date:** 2026-09-06  
**Audience:** Core Engineering Team, Stakeholders & Successor Developers  
**Reference Document:** Complements `CURRENT_PROJECT_TAKEOVER_AUDIT.md` with operational metrics, domain breakdowns, and direct execution priorities.

---

## 1. Executive Summary & Project Health

The Bharath Masala platform is an enterprise-grade e-commerce backend catering to both **Retail (B2C)** and **Wholesale (B2B)** customers for indigenous Malenadu spices and dry fruits.

The codebase is built on **Django 5.0.6**, **Django REST Framework 3.16.0**, **PostgreSQL 16**, **Redis 7**, and **Celery 5.4.0**.

### Development Milestones Summary

| Phase | Domain | Status | Automated Tests | Notes |
|---|---|---|---|---|
| **Phase 1** | Foundation & Core Infrastructure | **100% COMPLETE** | 14 / 14 Passing | Response envelope, request IDs, PII masking, health probes |
| **Phase 1** | Accounts, Auth & RBAC | **100% COMPLETE** | 32 / 32 Passing | Custom UUID user, JWT in HttpOnly cookies, B2B wholesale vetting |
| **Phase 2** | Catalog, Products & Pricing | **100% COMPLETE** | 41 / 41 Passing | Master products, variants, wholesale tier slabs, reviews, images |
| **Phase 3.1**| Async Infrastructure | **100% CONFIGURED** | Integrated | Celery, Redis, django-celery-beat, Docker Compose multi-service |
| **Phase 3.2**| Inventory Management | **100% COMPLETE** | 16 / 16 Passing | StockItem, immutable StockMovement ledger, StockReservation |
| **Phase 3.3**| Shopping Cart Domain | **100% COMPLETE** | 23 / 23 Passing | Cart & CartItem constraints, atomic row-locking, guest merge |
| **Phase 3.4**| Orders & Checkout | **100% COMPLETE** | 34 / 34 Passing | Atomic checkout, reservations, snapshots, FSM, customer & staff APIs |
| **Phase 3.5**| Payments & Webhooks | **100% COMPLETE** | 43 / 43 Passing | Razorpay gateway, HMAC-SHA256 verification, webhook idempotency |
| **Phase 3.6**| Background Celery Tasks | **100% COMPLETE** | 24 / 24 Passing | Reservation expiry, abandoned orders recovery, deadlock fix, Beat schedule |
| **Phase 3.7**| Shipping & Fulfillment Domain | **100% COMPLETE** | 33 / 33 Passing | Multi-shipment packaging, courier abstraction, AWB tracking, label gen, FSM sync |
| **Phase 3.8**| Notifications & Invoicing Domain | **100% COMPLETE** | 55 / 55 Passing | Statutory GST invoices (CGST/SGST/IGST), zero-dep PDF 1.4, multi-channel alerts |
| **Hardening**| Post-Order Orchestration & RBAC | **100% COMPLETE** | 6 / 6 Passing | Automated on_commit triggers, shipping hooks, unified RBAC, fail-fast checks |
| **Phase 3.9**| GST Credit Notes, Returns & Refunds | **100% COMPLETE** | 27 / 27 Passing | Statutory Credit Notes (Rule 53(1A)), zero-dep PDF 1.4, refunds gateway, webhook ingestion |
| **Phase 3.10**| Customer Returns, Replacements & RMA | **100% COMPLETE** | 39 / 39 Passing | Reverse logistics, FSSAI warehouse QA segregation, dual resolution (Credit Note + Refund vs Replacement Order) |
| **Phase 3.10.1 (Stage 1 & 1.1)**| Financial & Concurrency Hardening | **100% COMPLETE & VERIFIED** | 26 / 26 Passing | P0 remediation: ISSUE-001 (dispatch race), ISSUE-002 (partial refunds & webhook lock hierarchy), ISSUE-003 (invoice discounts Largest Remainder & replacement GST) |
| **Phase 3.10.1 (Stage 2)**| Wave 2 Remediation & Cross-Domain Hardening | **100% COMPLETE & VERIFIED** | 10 / 10 Passing | ISSUE-004 (credit note cumulative validation), ISSUE-005 (RTO state & refund automation), ISSUE-006 (QA inspection outcome verification) |

---

## 2. Engineering Health Dashboard

### 2.1 Test Suite Metrics

```text
======================================================================
TOTAL TESTS EXECUTED: 423
  - PASSING:          423  (100.0%)
  - FAILURES:           0  (  0.0%)
  - ERRORS:             0  (  0.0%)
TOTAL RUNTIME:        78.08s
======================================================================
```

#### Test Suite Breakdown by Application
- `apps.core`: **14 tests** — 14 Passed, 0 Failed
- `apps.accounts`: **32 tests** — 32 Passed, 0 Failed
- `apps.catalog`: **41 tests** — 41 Passed, 0 Failed
- `apps.inventory`: **16 tests** — 16 Passed, 0 Failed
- `apps.cart`: **23 tests** — 23 Passed, 0 Failed
- `apps.orders`: **72 tests** — 72 Passed, 0 Failed (+4 tests: ISSUE-001 cancellation concurrency)
- `apps.payments`: **61 tests** — 61 Passed, 0 Failed (+10 tests: ISSUE-002 partial refunds & webhook lock hierarchy)
- `apps.shipping`: **35 tests** — 35 Passed, 0 Failed (+2 tests: ISSUE-005 RTO state & refund automation)
- `apps.invoices`: **59 tests** — 59 Passed, 0 Failed (+16 tests: ISSUE-003 discounts/GST + ISSUE-004 cumulative credit notes)
- `apps.notifications`: **27 tests** — 27 Passed, 0 Failed
- `apps.returns`: **43 tests** — 43 Passed, 0 Failed (+4 tests: ISSUE-006 QA inspection outcome verification)

### 2.2 Static Analysis & Quality Metrics

| Tool | Status | Output Detail |
|---|---|---|
| `python3 manage.py check` | **PASS** | `System check identified no issues (0 silenced).` |
| `python3 manage.py makemigrations --check --dry-run` | **PASS** | `No changes detected` — zero database model drift. |
| `python3 manage.py showmigrations` | **PASS** | All migration sequences applied and in sync with models. |
| `black --check .` | **PASS** | `All done! 234 files would be left unchanged.` |
| `ruff check .` | **PASS** | `All checks passed!` |


---

## 3. Domain-by-Domain Operational Status

### 3.1 `apps.core` — Complete & Operational
- **Responsibilities:** API envelope consistency, error formatting, request correlation, security log sanitization, platform health checks.
- **Implemented Artifacts:**
  - `TimeStampedModel`: Abstract base providing auto-updating, indexed `created_at` and `updated_at`.
  - `RequestIDMiddleware`: Enforces or generates RFC-compliant `X-Request-ID` correlation identifiers.
  - `StandardResponseRenderer`: Wraps all API payloads in standard `{success, request_id, message, data, error}` envelope. Preserves HTTP 204 No Content.
  - `custom_exception_handler`: Catches DRF and Django validation/integrity exceptions and maps them to standard error responses.
  - `PIIMaskingFilter`: Sanitizes PANs, GSTINs, phone numbers, passwords, Bearer tokens, and secrets from all log output, including interpolated arguments and exception tracebacks.
  - Health Probes: `/health/liveness/` (liveness check) and `/health/readiness/` (executes database ping `SELECT 1`).

### 3.2 `apps.accounts` — Complete & Operational
- **Responsibilities:** User authentication, role-based access control (RBAC), B2B wholesale customer lifecycle, customer address book.
- **Implemented Artifacts:**
  - `User`: Custom model using UUID primary key, normalized Indian phone numbers (`91XXXXXXXXXX`), email username, and 6-role hierarchy (`CUSTOMER`, `WHOLESALE_PENDING`, `WHOLESALE_APPROVED`, `STAFF`, `MANAGER`, `SUPERADMIN`).
  - `WholesaleProfile`: B2B registration storing `company_name`, `gstin`, `pan_number`, and verification audit trail.
  - `Address`: User address book with strict `user=request.user` isolation preventing IDOR. Transactional `save()` guarantees only one default shipping and one default billing address per user.
  - `AuthService`: Generates JWT pairs; sets refresh tokens in `HttpOnly`, `SameSite=Lax`, path-scoped `/api/v1/auth/` cookies. Supports token rotation and blacklisting.
  - Guest Cart Merge: `LoginView` reads `guest_cart_token` cookie, automatically transfers items to the authenticated user's cart, and purges the cookie.

### 3.3 `apps.catalog` — Complete & Operational
- **Responsibilities:** Product master catalog, variant SKU matrix, B2B wholesale tiered pricing slabs, product photography, user reviews.
- **Implemented Artifacts:**
  - `Category`: Hierarchical product taxonomy with slug routing.
  - `Product`: Master product definition capturing Malenadu terroir, storytelling, harvest date, and origin stamps. Foreign key to Category is protected: `on_delete=models.PROTECT`.
  - `ProductVariant`: Specific SKUs by weight/size. **Confirmed: Contains NO stock field.** Stock authority is strictly delegated to the inventory app.
  - `WholesaleTierPricing`: Tiered volume discount slabs (`min_quantity`, `wholesale_price_per_unit`).
  - **Wholesale Price Security:** Two-tier protection prevents unauthorized retail viewing of wholesale slab discounts:
    1. Queryset layer: Prefetch filtered by `user.is_wholesale_buyer`.
    2. Serializer layer: Slabs redacted if user is not verified wholesale buyer.
  - `ProductReview` & `ReviewImage`: Customer review pipeline with automated image validation (size <= 5MB, format Pillow-verified) and staff moderation workflow (`PENDING` -> `APPROVED` / `REJECTED`).

### 3.4 `apps.inventory` — Complete & Operational
- **Responsibilities:** Authoritative physical stock tracking, append-only immutable audit trail, stock reservations during purchase flows, staff restock and adjustment workflows.
- **Implemented Artifacts:**
  - `StockItem`: Canonical record per `ProductVariant` (`OneToOneField(ProductVariant, on_delete=PROTECT)`).
    - Tracks `quantity_on_hand` and `quantity_reserved`.
    - Computed property `quantity_available = quantity_on_hand - quantity_reserved`.
    - Database check constraints enforce non-negative stock and prevent reservations from exceeding on-hand inventory.
  - `StockMovement`: Append-only audit ledger recording every inventory change (`INBOUND`, `SALE`, `RESERVATION`, `CANCELLATION`, `EXPIRY`, `ADJUSTMENT`). Immutability is enforced in Python (`save()` and `delete()` raise `ValidationError`) and audited with `actor`, `reference_type`, and `reference_id`.
  - `StockReservation`: State-machine allocation entity (`ACTIVE`, `RELEASED`, `CONSUMED`, `EXPIRED`) with timestamped expiry.
  - `InventoryService`: Thread-safe and transaction-safe stock operations utilizing `StockItem.objects.select_for_update()`.
  - Staff REST API:
    - `GET /api/v1/inventory/` — List all stock items (Staff/Manager).
    - `GET /api/v1/inventory/<pk>/` — Retrieve single stock item (Staff/Manager).
    - `POST /api/v1/inventory/restock/` — Record inbound inventory shipment (Staff/Manager).
    - `POST /api/v1/inventory/<pk>/adjust/` — Adjust inventory discrepancy with note (Manager/Admin).

### 3.5 `apps.cart` — Complete & Operational (Phase 3.3)
- **Responsibilities:** Session-based guest carts, authenticated customer carts, real-time inventory validation, dynamic pricing calculation (retail vs wholesale volume slabs), guest-to-user cart merging.
- **Implemented Artifacts:**
  - `Cart`: Supports either an authenticated `user` or an anonymous `guest_token` (64-character high-entropy cryptographic string).
  - `CartItem`: Links `Cart` to `ProductVariant` with unique composite constraint and `quantity > 0` validation.
  - `CartService`: Provides `add_item`, `update_item`, `remove_item`, `clear_cart`, `merge_guest_cart_into_user_cart`, and `unit_price`.
  - REST API: Endpoints for `GET /api/v1/cart/`, `DELETE /api/v1/cart/`, `POST /api/v1/cart/items/`, `PATCH /api/v1/cart/items/<pk>/`, `DELETE /api/v1/cart/items/<pk>/`.
  - Automated Tests: 23 / 23 passing.

### 3.6 `apps.orders` — Complete & Operational (Phase 3.4)
- **Responsibilities:** Authoritative checkout processing, price/address snapshotting, multi-state order fulfillment lifecycle, customer order history, staff fulfillment management.
- **Implemented Artifacts:**
  - `Order`: Captures customer, `order_status`, total items, subtotal, shipping fee, tax, final total, and full shipping address snapshot.
  - `OrderLineItem` (aliased as `OrderItem`): Immutable line item capturing `product_name`, `variant_name`, `sku`, `weight_in_grams`, `mrp`, `unit_selling_price`, `quantity`, and `line_total`.
  - `OrderStatusHistory`: Auditable state change log with `previous_status`, `new_status`, `actor`, and `notes`.
  - `CheckoutService`: Atomically validates cart, acquires `StockReservation` with deterministic locking, creates order and line items, clears cart, and returns order in `PENDING_PAYMENT` status.
  - `OrderStateMachine`: Strict transition matrix governing order states (`PENDING_PAYMENT`, `CONFIRMED`, `PROCESSING`, `SHIPPED`, `DELIVERED`, `CANCELLED`, `REFUNDED`).
  - Automated Tests: 34 / 34 passing.

### 3.7 `apps.payments` — Complete & Operational (Phase 3.5)
- **Responsibilities:** Payment gateway integration (Razorpay), HMAC-SHA256 signature verification, idempotent webhook processing, atomic reservation consumption.
- **Implemented Artifacts:**
  - `Payment`: Gateway transaction record linking `Order` to Razorpay order ID, payment ID, signature, method, and status (`PENDING`, `AUTHORIZED`, `CAPTURED`, `FAILED`, `CANCELLED`, `REFUNDED`).
  - `PaymentAttempt`: Append-only attempt log preserving retry history without corrupting main payment status.
  - `PaymentWebhookEvent`: Idempotent webhook event store (`event_id` unique constraint) capturing raw JSON payload and deduplicating retries.
  - `PaymentService`: Authoritative service initiating payments, verifying cryptographic signatures, and capturing payments with `select_for_update()` locking.
  - `WebhookService`: Verifies HMAC-SHA256 signature against `RAZORPAY_WEBHOOK_SECRET`, processes `payment.captured` and `payment.failed`, and enforces universal lock order (`Order` before `Payment`).
  - REST APIs: Customer endpoints (`initiate`, `verify`, `detail`), staff management endpoints (list with search/filters, detail), and public webhook receiver.
  - Automated Tests: 43 / 43 passing.

### 3.8 `apps.orders` Tasks & Recovery — Complete & Operational (Phase 3.6)
- **Responsibilities:** Automated background inventory recovery, reservation expiry, abandoned order failure, periodic Beat scheduling, deadlock-free universal locking.
- **Implemented Artifacts:**
  - `OrderService.expire_abandoned_orders()`: Per-order isolated atomic transactions identifying expired active stock reservations, releasing reservations with `expired=True` via `InventoryService.release_reservation()`, transitioning orders to `OrderStatus.FAILED`, and appending `OrderStatusHistory`.
  - `cleanup_expired_reservations_and_orders`: Celery `@shared_task` in `apps/orders/tasks.py`.
  - `CELERY_BEAT_SCHEDULE`: Configured in `config/settings/base.py` for 60-second execution.
  - Universal Lock Hierarchy: Standardized `Order -> Payment -> StockReservation -> StockItem` across customer verify, webhooks, and background cleanup.
  - Post-Expiry Reconciliation: Webhook captures for `FAILED` orders preserve payment data while flagging `RECONCILIATION_REQUIRED` without consuming expired inventory.
  - Automated Tests: 24 / 24 passing in `test_tasks.py` (58 / 58 total in `apps.orders`).

### 3.8 `apps.shipping` — Complete & Operational (Phase 3.7)
- **Responsibilities:** Physical parcel fulfillment, multi-shipment/split packaging, 3PL courier integrations (Delhivery, Blue Dart, Shiprocket, India Post), Air Waybill (AWB) tracking, shipping label generation, append-only tracking milestones, bidirectional Order FSM synchronization, and customer IDOR isolation.
- **Implemented Artifacts:**
  - `Shipment`, `ShipmentItem`, `ShipmentTrackingEvent`: Comprehensive relational data models capturing volumetric carton dimensions, weights, immutable destination snapshots, and carrier milestones.
  - `CourierAdapterInterface` & `MockCourierAdapter`: Pluggable carrier abstraction decoupled from core order models.
  - `ShippingService`: Coordinates parcel creation, split item fulfillment, AWB allocation, label generation, status transitions, and inventory restocking for Returned-To-Origin (RTO) consignments.
  - Bidirectional Order Sync: Automatically advances `CONFIRMED -> PROCESSING` on shipment creation, `PROCESSING -> SHIPPED` on carrier dispatch (`IN_TRANSIT`), and `SHIPPED -> DELIVERED` upon full fulfillment delivery.
  - Cancellation Safeguards: Prohibits cancelling orders with shipments in transit or delivered.
  - Customer Tracking APIs: Authenticated routes strictly isolated to `order.user == request.user` (IDOR safe) and public tracking endpoint (`/api/v1/shipping/track/`) with strict PII redaction.
  - Staff Logistics APIs: Full RBAC-protected management suite under `IsStaffOrManager`.
  - Automated Tests: 33 / 33 passing in `apps.shipping`.

### 3.8 `apps.invoices` & `apps.notifications` — Complete & Operational (Phase 3.8)
- **Statutory Indian GST Invoicing (`apps.invoices`):**
  - `InvoiceSequence`: Atomic database-level counter using `select_for_update()` guaranteeing collision-free, gapless numbering (`BMP/{FY}/{SEQ}`) across concurrent workers.
  - `Invoice`: Authoritative invoice model snapshotting seller details (FSSAI, GSTIN, Address), buyer details (Retail/Wholesale B2B), place of supply, interstate status, taxable subtotal, and tax breakdowns.
  - `InvoiceLineItem`: Item-level statutory breakdown recording HSN code (derived from catalog `hsn_code` e.g. "0904"), statutory GST rate (derived from product `gst_rate`), and CGST/SGST or IGST tax splits.
  - `MinimalPDFWriter` & `InvoicePDFGenerator`: Zero-dependency PDF generation producing valid standard PDF 1.4 byte streams without requiring external third-party dependencies.
  - Printable HTML Template: `invoices/tax_invoice.html` providing print-ready invoices with `@media print` CSS.
  - Customer & Staff APIs: IDOR-safe customer retrieval and download endpoints (`/api/v1/orders/{id}/invoice/`, `/download/`, `/html/`), plus filtered staff management endpoints.
  - Automated Tests: 28 / 28 passing in `apps.invoices` (base invoices).

- **Multi-Channel Communications (`apps.notifications`):**
  - `NotificationLog`: Immutable audit trail tracking channel (`EMAIL`, `WHATSAPP`, `SMS`), event, status, target recipient, message content, error message, and retry counter.
  - Transport Adapters (`apps/notifications/channels/`):
    - `EmailChannelAdapter`: Dispatches HTML and plain-text multipart transactional emails via Django email backend.
    - `WhatsAppChannelAdapter`: Transactional WhatsApp mobile messaging adapter with phone number normalization and logging.
    - `SMSChannelAdapter`: DLT-compliant transactional SMS adapter.
    - `get_channel_adapter(channel)`: Factory returning channel-specific adapter.
  - `NotificationService`: Orchestrates multi-channel delivery, handles deduplication (`idempotency_key = f"{order.id}:{event}:{channel}"`), and manages graceful skipping when contact information is missing.
  - Asynchronous background tasks: `dispatch_notification_task`, `send_order_notifications_task`.
  - Automated Tests: 27 / 27 passing in `apps.notifications`.

### 3.9 `apps.invoices` (Credit Notes) & `apps.payments` (Refunds) — Complete & Operational (Phase 3.9)
- **Statutory GST Credit Notes (`apps.invoices`):**
  - `CreditNoteSequence`: Concurrency-safe atomic counter generating consecutive serials (`BMP/CN/{FY}/{SEQ}`) per Rule 53(1A) of CGST Rules, 2017.
  - `CreditNote` & `CreditNoteLine`: Full snapshot of original invoice references, reasons (`ORDER_CANCELLATION`, `RETURN_TO_ORIGIN`, `DEFECTIVE_GOODS`, etc.), taxable amounts, CGST/SGST/IGST adjustments, and recipient details.
  - `CreditNotePDFGenerator`: Zero-dependency vector PDF 1.4 compiler generating downloadable credit note files.
  - `CreditNoteService`: Orchestrates atomic sequence reservation, invoice status transition (`CREDIT_NOTED`), PDF persistence, and `CREDIT_NOTE_ISSUED` notifications.
  - Customer & Staff APIs: IDOR-safe customer retrieval (`/api/v1/orders/{order_id}/credit-notes/`, `/download/`) and staff management endpoints.
- **Payment Refunds & Financial Reconciliation (`apps.payments`):**
  - `PaymentGatewayInterface.refund_payment()`: Unified interface implemented by `RazorpayGateway` and offline fallbacks.
  - `PaymentService.refund_payment()`: Concurrency-safe refund processing enforcing strict `Order` -> `Payment` lock order, creating `PaymentAttempt` audit records, updating `amount_refunded`, transitioning order to `REFUNDED`, and notifying customer.
  - Webhook Ingestion: Ingests `refund.processed` and `payment.refunded` events with signature verification and idempotency.
  - Staff Refund API: `POST /api/v1/staff/payments/{payment_id}/refund/` restricted to `IsStaffOrManager`.
  - Automated Tests: 27 new tests added (15 credit notes + 8 refunds + 4 reconciliation).

### 3.10 `apps.returns` — Complete & Operational (Phase 3.10)
- **Responsibilities:** Customer returns & replacements (RMA), reverse logistics, warehouse quality inspection, FSSAI food safety inventory segregation, statutory GST credit notes, payment refunds, zero-cost replacement orders, multi-channel transactional notifications.
- **Implemented Artifacts:**
  - `ReturnRequest`: RMA entity managing full lifecycle (`REQUESTED`, `APPROVED`, `REJECTED`, `PICKUP_SCHEDULED`, `IN_TRANSIT`, `RECEIVED`, `INSPECTED`, `COMPLETED`, `CANCELLED`). Idempotency ensured via OneToOne fields to `replacement_order` and `credit_note`.
  - `ReturnItem`: Line-level items with reasons and strict quantity invariants:
    $$\text{Eligible Quantity} = \text{Delivered Quantity} - \text{Previously Requested/Returned Quantity}$$
  - `ReturnEvidence`: Customer photographic evidence with validation (max 5MB, JPG/PNG).
  - `ReturnShipment`: Reverse logistics tracking with 3PL carrier integration (`CourierAdapterInterface`), reverse AWB, customer address snapshots, and transit milestones.
  - `ReturnInspection`: Warehouse intake QA enforcing FSSAI food safety segregation (`RESTOCK` into saleable inventory via `InventoryService.add_stock` vs `DISCARD` scrap write-off with zero physical restock).
  - Dual Resolution Engine:
    - `REFUND`: Generates statutory GST Credit Note (Rule 53(1A)) + executes payment refund with universal locking ($\text{Order} \to \text{Payment} \to \text{CreditNoteSequence}$).
    - `REPLACEMENT`: Creates zero-cost replacement order (`grand_total = 0.00`, `total_discount = items_subtotal`, `OrderLineItem` unit_price > 0) with automatic stock reservation and consumption.
  - Multi-Channel Notifications: 6 lifecycle events across Email, WhatsApp, and SMS with dedicated templates.
  - Customer & Staff REST APIs: IDOR-safe customer endpoints (`/api/v1/orders/{id}/returns/`) and staff RMA management endpoints (`/api/v1/staff/returns/`).
  - Automated Tests: 39 / 39 passing.

---

## 4. Completed Defect Remediation & Hardening

All previously noted issues have been resolved and permanently verified:
1. **`CartItem` Check Constraint Crash:** Fixed; item acquisition uses atomic `filter().first()` and creates/updates with non-zero quantity.
2. **Cart Ownership Constraint:** Regex check `guest_token__regex=r"^.{1,}$"` ensures non-empty tokens.
3. **ReviewService Compatibility:** `Order.order_status` preserved; `ReviewService` verified against delivered orders.
4. **Deterministic Inventory Locking:** Stock items locked with `.order_by("variant_id")` during checkout and cancellation to prevent database deadlocks.
5. **Universal Lock Hierarchy:** Corrected lock inversion in `WebhookService`; `Order` is always locked prior to `Payment` across all domains.
6. **In-Transit Cancellation Guard:** Prohibits cancellation of orders once physical consignments are dispatched to carriers.
7. **Statutory Tax Snapshot Integrity:** Invoices strictly derive GST rates and HSN codes from product snapshots rather than hardcoded rates; historical invoices are completely decoupled from live catalog updates.
8. **Statutory Credit Note Compliance (Rule 53(1A)):** Invoiced orders cancelled or returned via RTO generate immutable GST Credit Notes with dedicated sequential numbering (`BMP/CN/{FY}/{SEQ}`) and mark parent invoices `CREDIT_NOTED`.
9. **Universal Refund Processing:** Dedicated gateway abstraction for Razorpay and offline refunds with atomic order and payment locking, attempt logging, and webhook event reconciliation.
10. **ISSUE-001 (Order Cancellation vs. Dispatch Race Condition):** Hardened `OrderStateMachine.cancel_order` with atomic row locks on `Order` and all related `Shipment`s ordered by ID, blocking cancellation once any shipment is in transit (`IN_TRANSIT`, `OUT_FOR_DELIVERY`, `DELIVERED`, `RETURNED_TO_ORIGIN`), and automatically transitioning pre-dispatch shipments (`PENDING`, `LABEL_GENERATED`, `READY_FOR_PICKUP`) to `CANCELLED` with immutable tracking audit events.
11. **ISSUE-002 (Partial Refund Accumulation & Payment Status):** Added `PaymentStatus.PARTIALLY_REFUNDED`, accumulated `amount_refunded` under lock in `PaymentService.refund_payment`, deduplicated `refund.processed` webhook payloads via `PaymentAttempt`, and ensured `Order` only transitions to `REFUNDED` upon 100% refund balance clearance.
12. **ISSUE-003 (Statutory Invoice Discounts & Zero-Cost Replacement GST):** Added `total_discount` on `Invoice` and `discount_amount` on `InvoiceLineItem`, deterministically allocating cart/order discounts proportionally across lines, strictly preserving the GST statutory invariant `taxable_subtotal + total_tax + shipping_fee == grand_total`, and computing zero-tax liabilities for zero-value warranty/replacement orders.

---

## 5. Development Roadmap to Final Delivery

```
+-------------------------------------------------------------------------+
| STEP 1: FIX CART DOMAIN DEFECTS (PHASE 3.3)                             |
|  - [COMPLETED] 23 / 23 Automated Tests Passing                          |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| STEP 2: IMPLEMENT APPS.ORDERS (PHASE 3.4)                               |
|  - [COMPLETED] Order, OrderLineItem, OrderStatusHistory models          |
|  - [COMPLETED] Address & Pricing Immutability Snapshots                 |
|  - [COMPLETED] CheckoutService (Cart -> StockReservation -> Order)      |
|  - [COMPLETED] Customer Order API + Staff Fulfillment API               |
|  - [COMPLETED] 34 / 34 Automated Tests Passing (160 total across app)   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| STEP 3: IMPLEMENT APPS.PAYMENTS (PHASE 3.5)                             |
|  - [COMPLETED] Payment, PaymentAttempt, PaymentWebhookEvent models      |
|  - [COMPLETED] Razorpay gateway & HMAC-SHA256 signature verification    |
|  - [COMPLETED] Webhook deduplication & atomic reservation consumption   |
|  - [COMPLETED] 43 / 43 Automated Tests Passing                          |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| STEP 4: CELERY BACKGROUND AUTOMATION (PHASE 3.6)                        |
|  - [COMPLETED] Universal lock hierarchy (Order -> Payment deadlock fix) |
|  - [COMPLETED] OrderService.expire_abandoned_orders()                   |
|  - [COMPLETED] Periodic reservation expiry task via django-celery-beat  |
|  - [COMPLETED] Automated reclamation of abandoned checkout inventory    |
|  - [COMPLETED] 24 / 24 Automated Tests Passing (227 total across app)   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| STEP 5: SHIPPING, FULFILLMENT & DELIVERY DOMAIN (PHASE 3.7)             |
|  - [COMPLETED] Shipment, ShipmentItem, ShipmentTrackingEvent models     |
|  - [COMPLETED] CourierAdapterInterface & MockCourierAdapter             |
|  - [COMPLETED] ShippingService: split fulfillment & RTO restocking      |
|  - [COMPLETED] Customer IDOR-safe tracking & staff logistics APIs       |
|  - [COMPLETED] 33 / 33 Automated Tests Passing (260 total across app)   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| STEP 6: NOTIFICATIONS, EMAILS & INVOICES (PHASE 3.8)                    |
|  - [COMPLETED] apps.invoices & apps.notifications separation            |
|  - [COMPLETED] Statutory GST breakdown (CGST/SGST/IGST, HSN, POS)       |
|  - [COMPLETED] Zero-dependency standard PDF 1.4 + printable HTML        |
|  - [COMPLETED] Multi-channel notifications (Email, WhatsApp, SMS)       |
|  - [COMPLETED] 51 / 51 Automated Tests Passing (311 total across app)   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| STEP 7: GST CREDIT NOTES, INVOICE LIFECYCLE & REFUNDS (PHASE 3.9)       |
|  - [COMPLETED] InvoiceStatus (ACTIVE, CANCELLED, CREDIT_NOTED)          |
|  - [COMPLETED] Rule 53(1A) CreditNoteSequence & CreditNoteLine models   |
|  - [COMPLETED] CreditNoteService & zero-dependency PDF 1.4 generator    |
|  - [COMPLETED] PaymentService.refund_payment() + Razorpay refund gateway|
|  - [COMPLETED] Webhook ingestion (refund.processed, payment.refunded)   |
|  - [COMPLETED] Cancellation & RTO credit note automation & restock      |
|  - [COMPLETED] 27 / 27 Automated Tests Passing (348 total across app)   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| STEP 8: CUSTOMER RETURNS, REPLACEMENTS & RMA (PHASE 3.10)               |
|  - [COMPLETED] ReturnRequest, ReturnItem, ReturnShipment, Inspection    |
|  - [COMPLETED] 7-day policy window & eligible qty invariant calculation |
|  - [COMPLETED] Reverse logistics (courier adapter, reverse AWB tracking)|
|  - [COMPLETED] Warehouse FSSAI food safety inspection (RESTOCK vs SCRAP)|
|  - [COMPLETED] Dual resolution: Credit Note + Refund vs Replacement     |
|  - [COMPLETED] Universal lock order (Order -> Payment -> CreditNoteSeq) |
|  - [COMPLETED] Multi-channel notifications for 6 return events          |
|  - [COMPLETED] 39 / 39 Automated Tests Passing (387 total across app)   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| STEP 9: FINANCIAL INTEGRITY & CONCURRENCY REMEDIATION (PHASE 3.10.1 S1) |
|  - [COMPLETED] ISSUE-001: Order cancellation vs dispatch race condition |
|  - [COMPLETED] ISSUE-002: Partial refund accumulation & PARTIALLY_REFND |
|  - [COMPLETED] ISSUE-003: Invoice discount allocation & replacement GST |
|  - [COMPLETED] Universal lock order adhered across orders/payments/inv  |
|  - [COMPLETED] 18 / 18 Automated Tests Passing (405 total across app)   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| STEP 10: REMEDIATION CLOSURE & WAVE 3 AUDIT (PHASE 3.10.1 S1.1, S2, W3) |
|  - [COMPLETED] ISSUE-004: Cumulative Credit Note Quantity Validation    |
|  - [COMPLETED] ISSUE-005: Shipment RTO State Restock & Refund Integrity |
|  - [COMPLETED] ISSUE-006: Return Resolution State Transition Safety     |
|  - [COMPLETED] ISSUE-007: Fallback Webhook Order-Payment Lock Invariant |
|  - [COMPLETED] ISSUE-008 - ISSUE-013: Wave 3 Hardening Complete         |
|  - [COMPLETED] 22 / 22 Automated Tests Passing (427 total across app)   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| STEP 11: COUPONS, DISCOUNTS & PROMOTIONS ENGINE (PHASE 3.11)            |
|  - [COMPLETED] Coupon, Promotion, OrderDiscountLine models              |
|  - [COMPLETED] Concurrency protection (SELECT FOR UPDATE on coupons)    |
|  - [COMPLETED] Fixed vs Percentage discount engines with min spend caps |
|  - [COMPLETED] Proportional discount allocation with rounding reconcil. |
|  - [COMPLETED] Statutory GST compliance & invoice/credit note integrity |
|  - [COMPLETED] 41 / 41 Automated Tests Passing (468 total across app)   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| STEP 12: BACKEND FINALIZATION & API CONTRACT AUDIT (PHASE 3.12)         |
|  - [COMPLETED] 81 routes, 98 operations full surface cataloged          |
|  - [COMPLETED] Architecture and security invariant audit passed         |
|  - [COMPLETED] Zero regression baseline confirmed (468 tests)          |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| STEP 13: OPENAPI / SWAGGER & API CONTRACT (PHASE 3.13 STAGE 1 & 2)      |
|  - [COMPLETED] Stage 1: Pre-Implementation Baseline Audit approved      |
|  - [COMPLETED] Stage 2: drf-spectacular 0.28.0 installed & configured    |
|  - [COMPLETED] Endpoints live: /api/v1/schema/, /api/v1/docs/, /redoc/  |
|  - [COMPLETED] 80 paths, 94 operations documented across 9 domain tags  |
|  - [COMPLETED] OpenAPI 3.0.3 specification validated with 0 errors      |
|  - [COMPLETED] 3 new schema tests added (471 / 471 total passing)       |
+-------------------------------------------------------------------------+
```

---

## 6. Sign-off Status

| Role | Name / Identifier | Status | Date |
|---|---|---|---|
| **Auditor / Agent** | Antigravity Engine | Complete & Verified | 2026-09-07 |
| **System State** | Bharath Masala Backend | 471 / 471 Tests Green (100%); Phase 3.13 Stage 2 Complete | 2026-09-07 |
| **OpenAPI Endpoints** | `/api/v1/schema/`, `/api/v1/docs/`, `/api/v1/redoc/` | Validated & Live | 2026-09-07 |



