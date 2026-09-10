# POST-ORDER COMMERCE WORKFLOW ARCHITECTURE & PRODUCTION-READINESS AUDIT

**Project:** Bharath Masala Products E-Commerce Platform  
**Audit Target:** End-to-End Post-Order Commerce Pipeline (Phases 3.4 through 3.8)  
**Date:** September 2026  
**Auditor:** Antigravity Advanced Agentic Engineering Team  
**Status:** COMPREHENSIVE ARCHITECTURAL AUDIT & PRODUCTION READINESS REVIEW  

---

## 1. Executive Summary & Verification Baseline

The Bharath Masala backend has completed its core commercial and operational domains:
- **Phase 3.4**: Orders, Checkout, and State Machine
- **Phase 3.5**: Payments, Razorpay Gateway, and HMAC Webhooks
- **Phase 3.6**: Background Celery Automation, Deadlock Prevention, and Reservation Expiry
- **Phase 3.7**: Multi-Package Shipping, Courier Abstraction, and AWB Tracking
- **Phase 3.8**: Statutory Indian GST Invoicing and Multi-Channel Communications

### Current Verified Technical Baseline
- **Total Test Suite**: **311 / 311 tests passing (100% green)**
  - `apps.core`: 14 tests
  - `apps.accounts`: 32 tests
  - `apps.catalog`: 41 tests
  - `apps.inventory`: 16 tests
  - `apps.cart`: 23 tests
  - `apps.orders`: 58 tests
  - `apps.payments`: 43 tests
  - `apps.shipping`: 33 tests
  - `apps.invoices`: 26 tests
  - `apps.notifications`: 25 tests
- **System Configuration**: `python3 manage.py check` → 0 issues.
- **Model Migration Drift**: `python3 manage.py makemigrations --check --dry-run` → No changes detected.
- **Code Formatting**: `black --check .` → 203 files verified and compliant.
- **Linting & Code Quality**: `ruff check .` → All checks passed cleanly.

This audit evaluates the system across five dimensions:
1. End-to-End Post-Order Pipeline Integration
2. Celery Asynchronous Infrastructure & Task Reliability
3. Security, Access Control (RBAC/IDOR), and Financial Data Integrity
4. API Consistency & Response Standardisation
5. Deployment & Production Operational Readiness

---

## 2. End-to-End Post-Order Pipeline Integration Audit

```
[Customer]
    │
    ▼
[Cart & Checkout] ──► [StockReservation (ACTIVE)]
    │
    ▼
[Order Created (PENDING_PAYMENT)]
    │
    ▼
[Payment Captured] ──► [Universal Lock: Order -> Payment -> Reservation -> StockItem]
    │
    ▼
[OrderStateMachine: CONFIRMED] ──► [Reservation CONSUMED]
    │
    ├───────────────────────────────┐
    ▼                               ▼
[apps.invoices]             [apps.notifications]
- Consecutive Numbering     - Multi-Channel: Email / WhatsApp / SMS
- CGST / SGST / IGST Splits - Deduplication: order:event:channel
- Zero-dep PDF 1.4          - Celery Async Dispatch
    │                               │
    ▼                               ▼
[apps.shipping]             [Lifecycle Events]
- Split Shipment Cartons    - ORDER_SHIPPED
- Courier Booking & AWB     - ORDER_DELIVERED
- IN_TRANSIT -> SHIPPED     - ORDER_CANCELLED
- DELIVERED -> DELIVERED
```

### 2.1 Payments → Order Confirmation
* **Implementation Status:** Verified & Robust.
* **Mechanism:**
  - Dual capture paths: Synchronous client signature verification (`/api/v1/payments/orders/{id}/verify/`) and asynchronous webhook ingestion (`/api/v1/payments/webhooks/razorpay/`).
  - Strict universal lock hierarchy: `Order` is locked before `Payment`, eliminating cross-transaction deadlocks.
  - Confirmation triggers `OrderStateMachine.transition_status(order, OrderStatus.CONFIRMED)`, which automatically executes `InventoryService.consume_reservation()`, converting virtual holds into hard stock deductions.
* **Audit Finding [INTEGRATION-01] — Post-Confirmation Orchestration:**
  - Currently, when `verify_and_capture_payment` succeeds, `OrderStateMachine.transition_status` transitions the order, but does not automatically enqueue `generate_invoice_for_order_task` or `send_order_notifications_task`.
  - Invoices are currently generated on-demand when a customer/staff member requests them, or when tasks are manually triggered.
  - **Recommendation:** Connect an asynchronous post-transition hook or signal utilizing `transaction.on_commit(lambda: generate_invoice_for_order_task.delay(str(order.id)))` and `transaction.on_commit(lambda: send_order_notifications_task.delay(str(order.id), NotificationEvent.ORDER_CONFIRMED))` to achieve 100% automated straight-through processing.

### 2.2 Order Confirmation → Statutory GST Invoicing
* **Implementation Status:** Verified & Compliant.
* **Mechanism:**
  - `InvoiceSequence` uses database-level row locking (`select_for_update()`) to ensure collision-free, gapless sequential numbering (`BMP/{FY}/{SEQ}`) across concurrent Celery workers.
  - Accurate Place of Supply (POS) rules:
    - Intra-state (`KA` → `KA`): Equal split between CGST (`rate / 2`) and SGST (`rate / 2`).
    - Inter-state (`KA` → other state): 100% IGST (`rate`).
  - HSN codes (e.g. `0904` for spices) and statutory GST rates are derived dynamically from catalog items rather than being hardcoded.
  - Immutable B2B snapshot: Captures buyer company name, verified GSTIN, and PAN from `WholesaleProfile`.
* **Audit Finding [FINANCIAL-01] — Post-Confirmation Order Cancellation & Credit Notes:**
  - When a confirmed order is cancelled prior to dispatch, physical stock is cleanly returned to inventory via `InventoryService.add_stock`.
  - However, if an official GST Tax Invoice was already generated for that order, Indian GST law requires issuing a **GST Credit Note** (or marking the invoice as cancelled/voided with an explicit reversal reference).
  - **Recommendation:** Add an `is_cancelled` or `status` field (`ACTIVE`, `CANCELLED`, `CREDIT_NOTED`) to `Invoice`, and generate a statutory Credit Note reference if a confirmed order with an existing invoice is cancelled.

### 2.3 Shipping & Fulfillment → Lifecycle Notifications
* **Implementation Status:** Verified & Robust.
* **Mechanism:**
  - `ShipmentItem` tracks partial or split shipments against `OrderLineItem`.
  - `ShippingService.transition_shipment_status()` automatically transitions parent `Order` status:
    - First shipment entering `IN_TRANSIT` → Order advances to `SHIPPED` (`order.shipped_at` populated).
    - Final shipment entering `DELIVERED` → Order advances to `DELIVERED` (`order.delivered_at` populated).
  - Returned-To-Origin (RTO) consignments automatically restock physical inventory.
* **Audit Finding [INTEGRATION-02] — Automated Dispatch & Delivery Alerts:**
  - While `ShippingService` updates `Order` state, it does not currently dispatch `send_order_notifications_task(order.id, NotificationEvent.ORDER_SHIPPED)` or `ORDER_DELIVERED`.
  - **Recommendation:** Hook `send_order_notifications_task` to fire on shipment dispatch (`IN_TRANSIT`) with tracking metadata (`courier_name`, `awb_number`, `tracking_url`), and upon final delivery.

---

## 3. Celery Asynchronous Infrastructure & Task Reliability Audit

### 3.1 Worker Configuration & Broker Reliability
* **Broker & Backend:** Redis 7 (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`).
* **Settings Analysis (`config/settings/base.py`):**
  ```python
  CELERY_TASK_ALWAYS_EAGER = False
  CELERY_TASK_EAGER_PROPAGATES = True
  CELERY_TASK_ACKS_LATE = True
  CELERY_TASK_REJECT_ON_WORKER_LOST = True
  CELERY_WORKER_PREFETCH_MULTIPLIER = 1
  ```
  - `CELERY_TASK_ACKS_LATE = True` and `CELERY_TASK_REJECT_ON_WORKER_LOST = True` guarantee that if a worker pod/container terminates unexpectedly mid-task, the task is safely re-queued rather than dropped.
  - `CELERY_WORKER_PREFETCH_MULTIPLIER = 1` prevents fast workers from starving and ensures fair distribution of computationally heavy tasks (such as PDF generation).

### 3.2 Transaction Boundary & Race Condition Audit
* **Audit Finding [CELERY-01] — DB Transaction vs Asynchronous Worker Race Condition:**
  - When a task is queued from inside an active `with transaction.atomic():` block using `my_task.delay(entity_id)`, there is a known race condition: the background worker may pick up the task from Redis and query the database *before* the Django database transaction has completed its `COMMIT`.
  - If the worker executes before commit, it will encounter `Entity.DoesNotExist`.
  - **Current Codebase Protection:** In `apps.orders.tasks`, tasks use per-order transaction isolation. However, any new code enqueuing tasks from inside atomic blocks MUST use `transaction.on_commit()`:
    ```python
    transaction.on_commit(lambda: generate_invoice_for_order_task.delay(str(order.id)))
    ```

### 3.3 Periodic Task Scheduling (Celery Beat)
* **Scheduler:** `django_celery_beat.schedulers.DatabaseScheduler`.
* **Configured Schedule:**
  - `cleanup-expired-reservations-and-orders`: Runs every 60 seconds (`apps.orders.tasks.cleanup_expired_reservations_and_orders`).
  - Verified in Phase 3.6: Releases abandoned stock reservations, transitions expired orders to `FAILED`, and records stock restoration entries in `StockMovement` ledger.

---

## 4. Security, Access Control (RBAC/IDOR) & Data Integrity Audit

### 4.1 IDOR (Insecure Direct Object References) Verification
* **Customer Endpoints:**
  - `GET /api/v1/orders/{id}/`: Protected by `Order.objects.filter(id=id, user=request.user)`.
  - `POST /api/v1/orders/{id}/cancel/`: Protected; non-owners receive HTTP 404.
  - `GET /api/v1/orders/{id}/invoice/`: Enforces `order.user == request.user`; non-owners receive HTTP 404.
  - `GET /api/v1/orders/{id}/invoice/download/`: Enforces `order.user == request.user`.
  - `GET /api/v1/shipping/orders/{id}/tracking/`: Strictly filtered by `order.user == request.user`.
* **Verdict:** ✅ IDOR protection is consistently implemented across all customer-facing endpoints. Non-owners receive 404 rather than 403, preventing resource enumeration.

### 4.2 PII Protection & Logging Sanitization
* **Filter:** `apps.core.logging.PIIMaskingFilter` registered in `LOGGING`.
* **Sanitization:** Masks phone numbers, passwords, Bearer tokens, credit cards, GSTINs, and PANs across all log output, including exception tracebacks and Celery worker logs.
* **Public Tracking:** `/api/v1/shipping/track/` redacts all customer names, phone numbers, delivery street addresses, line items, and invoice amounts. Only courier milestone history, timestamp, and destination city/state are visible.

### 4.3 Staff RBAC Consistency Audit
* **Audit Finding [SECURITY-01] — Staff Permission Class Discrepancy:**
  - In `apps.orders.staff_views`, `apps.payments.staff_views`, and `apps.shipping.staff_views`, endpoints enforce:
    ```python
    permission_classes = [IsAuthenticated, IsStaffOrManager]
    ```
    This properly admits users with role `STAFF`, `MANAGER`, or `SUPERADMIN`, or users with `is_staff=True`.
  - In `apps.invoices.staff_views` and `apps.notifications.staff_views`, endpoints currently use:
    ```python
    permission_classes = [IsAdminUser]
    ```
    `IsAdminUser` only checks `request.user.is_staff`. If a management user has `role=Role.MANAGER` but `is_staff=False`, they would have access to shipping/orders, but would be blocked from viewing invoices or notifications.
  - **Recommendation:** Standardize all staff views across `apps.invoices` and `apps.notifications` to use `[IsAuthenticated, IsStaffOrManager]`.

### 4.4 Payment Gateway & Webhook Security
* **Razorpay HMAC Signature Verification:**
  - Verified with `hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()`.
  - `PaymentWebhookEvent` records event IDs with unique constraints, guaranteeing idempotency and preventing replay attacks.
* **Audit Finding [SECURITY-02] — Production Settings Secret Validation:**
  - In `config/settings/base.py`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET` provide test fallback values (`rzp_test_placeholder`, etc.).
  - While `config/settings/production.py` strictly validates `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and `DATABASE_URL`, it does not currently raise a `RuntimeError` if Razorpay placeholder keys are present when `DEBUG=False`.
  - **Recommendation:** Add fail-fast assertions in `config/settings/production.py` ensuring `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` do not contain `"placeholder"`.

---

## 5. API Consistency & Design Audit

| Domain | Base Route | Envelope Wrapped? | Authentication | IDOR Safe? |
|---|---|---|---|---|
| **Auth** | `/api/v1/auth/` | Yes (`StandardResponseRenderer`) | AllowAny / IsAuthenticated | N/A |
| **Catalog** | `/api/v1/catalog/` | Yes | AllowAny (Slabs hidden for retail) | N/A |
| **Cart** | `/api/v1/cart/` | Yes | Guest Token / IsAuthenticated | Yes |
| **Orders** | `/api/v1/orders/` | Yes | IsAuthenticated | Yes |
| **Payments** | `/api/v1/payments/` | Yes | IsAuthenticated | Yes |
| **Shipping** | `/api/v1/shipping/` | Yes | IsAuthenticated / AllowAny (public track) | Yes |
| **Invoices** | `/api/v1/orders/{id}/invoice/` | Yes (JSON) / Raw (PDF/HTML) | IsAuthenticated | Yes |
| **Staff APIs** | `/api/v1/staff/{domain}/` | Yes | Staff / Manager | RBAC Enforced |

* **API Envelope:** `StandardResponseRenderer` ensures uniform `{success, request_id, message, data, error}` format. Endpoints returning direct binary files (PDF downloads) or rendered HTML bypass the JSON envelope appropriately via standard `HttpResponse`.
* **Correlation:** `X-Request-ID` is extracted or generated on every request and propagated to logs and responses.

---

## 6. Deployment & Operational Readiness Audit

### 6.1 Database & Connection Management
* **Engine:** PostgreSQL 16 (in Docker / Production) with `dj-database-url`.
* **Pooling:** `conn_max_age=600`, `conn_health_checks=True`.
* **Migrations:** All 10 apps have clean migration histories without pending drift.

### 6.2 Media & Document Storage
* **Current Storage:** Default Django `FileSystemStorage` under `media/invoices/`.
* **Audit Finding [DEPLOY-01] — Ephemeral Container Media Durability:**
  - In containerized deployments (AWS ECS, GCP Cloud Run, Kubernetes), local container storage is ephemeral.
  - If a container restarts or autoscales, local media files (`media/invoices/*.pdf`) will be lost unless persistent volumes are attached or object storage is configured.
  - **Recommendation:** For production deployment, integrate `django-storages` with AWS S3, Google Cloud Storage, or MinIO to persist invoice PDFs and product photography.

### 6.3 Docker Compose Multi-Service Topology
* **Services Defined:**
  - `web`: Django application server (port 8000)
  - `db`: PostgreSQL 16 with automated healthcheck
  - `redis`: Redis 7 with automated healthcheck
  - `celery`: Celery asynchronous worker (concurrency 2)
  - `celery-beat`: Periodic task scheduler
* **Verdict:** ✅ Complete local and staging containerized stack ready for execution.

### 6.4 Environment Variables Checklist

| Variable | Required In Prod? | Purpose | Current Status |
|---|---|---|---|
| `DJANGO_SETTINGS_MODULE` | Yes | Selects configuration module | `config.settings.production` |
| `DJANGO_SECRET_KEY` | Yes (min 50 chars) | Cryptographic signing | Enforced in `production.py` |
| `DJANGO_ALLOWED_HOSTS` | Yes | Host header attack protection | Enforced (no wildcard) |
| `DATABASE_URL` | Yes | PostgreSQL connection URI | Enforced in `production.py` |
| `CELERY_BROKER_URL` | Yes | Redis broker connection | Configured in `base.py` |
| `CELERY_RESULT_BACKEND` | Yes | Redis result connection | Configured in `base.py` |
| `RAZORPAY_KEY_ID` | Yes | Gateway API Key | Fallback present in `base.py` |
| `RAZORPAY_KEY_SECRET` | Yes | Gateway API Secret | Fallback present in `base.py` |
| `RAZORPAY_WEBHOOK_SECRET` | Yes | Webhook HMAC verification | Fallback present in `base.py` |
| `INVOICE_SELLER_NAME` | Optional (has default)| Statutory seller legal name | Defaults to "Bharath Masala Products" |
| `INVOICE_SELLER_GSTIN` | Optional (has default)| Statutory 15-digit GSTIN | Defaults to Karnataka GSTIN |
| `INVOICE_SELLER_FSSAI` | Optional (has default)| 14-digit FSSAI license | Defaults to Thirthahalli license |
| `INVOICE_SELLER_ADDRESS`| Optional (has default)| Registered manufacturing address| Defaults to Thirthahalli address |

---

## 7. Actionable Production Hardening Plan

Before proceeding to Phase 3.9 (or frontend integration), the following production hardening tasks are recommended in order of priority:

### Priority 1: High (Integrity & Straight-Through Processing)
1. **Automate Post-Confirmation Workflow**: Connect `OrderStateMachine.transition_status(CONFIRMED)` to enqueue `generate_invoice_for_order_task` and `send_order_notifications_task` via `transaction.on_commit()`.
2. **Automate Shipping Dispatch & Delivery Notifications**: Connect `ShippingService` transitions to trigger `ORDER_SHIPPED` (with AWB tracking details) and `ORDER_DELIVERED` notifications.
3. **Harmonize Staff Permission Classes**: Update `apps.invoices.staff_views` and `apps.notifications.staff_views` to use `[IsAuthenticated, IsStaffOrManager]`.

### Priority 2: Medium (Financial & Settings Hardening)
4. **GST Credit Note Workflow**: Implement statutory credit note tracking or status updating on `Invoice` when a confirmed order with an invoice is cancelled.
5. **Production Settings Validation**: Add fail-fast checks in `config/settings/production.py` ensuring Razorpay credentials are not placeholder values.
6. **Environment Template Alignment**: Add `INVOICE_SELLER_*` variables to `.env.example`.

### Priority 3: Low (Infrastructure Scalability)
7. **Cloud Media Storage Hook**: Configure `django-storages` (S3/GCS) in `config/settings/production.py` for persistent invoice PDF and product image storage.

---

## 8. Audit Conclusion

The Bharath Masala backend architecture is **fundamentally sound, secure, and rigorously tested** (311/311 tests passing, 0 lint/format issues, 0 migration drift). The domain separation between Invoices and Notifications is clean, concurrency controls and row locks protect financial data and inventory, and IDOR protection is uniformly enforced.

Addressing the Priority 1 & 2 integration and hardening recommendations will ensure complete end-to-end automation across the entire post-order customer lifecycle.
