# CURRENT PROJECT TAKEOVER AUDIT

**Project:** Bharath Masala Products E-Commerce Platform (Production Django/DRF Backend)  
**Audit Timestamp:** 2026-09-06T15:37:00+05:30  
**Scope:** Complete repository forensic audit across Phase 1, Phase 2, and Phase 3 (Infrastructure, Inventory, Cart, Orders, Payments).  
**Prior Reference:** Replaces and supersedes `CODEX_PROJECT_TAKEOVER_AUDIT.md` (which captured state at 00:09:00 before Inventory and Cart were implemented).

---

## 1. Executive Summary

A previous audit report (`CODEX_PROJECT_TAKEOVER_AUDIT.md`) was written on 2026-09-06 at 00:09:00. At that exact timestamp, `apps.inventory` and `apps.cart` did not exist. Between 00:14 and 00:38 on 2026-09-06, significant implementation took place:
1. **Core logging sanitization was repaired** at 00:14 in `apps/core/middleware.py`.
2. **`apps.inventory` was fully implemented** at 00:16 with 16 automated tests (all 16 passing).
3. **`apps.cart` was partially implemented** at 00:38 with 18 automated tests, but was abandoned with **10 test failures/errors, severe check constraint bugs, and lint/formatting violations**.
4. **`apps.orders` and `apps.payments` remain completely unstarted**.

### Current Baseline Health Matrix

| Verification Vector | Status | Detail |
|---|---|---|
| **System Check (`manage.py check`)** | **PASS** | 0 issues identified (0 silenced) |
| **Model Drift (`makemigrations --check --dry-run`)** | **PASS** | `No changes detected` — all models match migrations |
| **Migrations Applied (`showmigrations`)** | **PASS** | All migrations applied across accounts, catalog, inventory, cart, django_celery_beat |
| **Total Automated Tests** | **121 Tests** | **111 PASSING, 2 FAILING, 8 ERRORS** |
| `apps.core` Tests | **14 / 14 PASS** | Health probes, envelope renderer, exception handling, PII masking |
| `apps.accounts` Tests | **32 / 32 PASS** | Auth, RBAC, address book, wholesale onboarding/approval |
| `apps.catalog` Tests | **41 / 41 PASS** | Categories, products, variants, tier pricing, reviews, images |
| `apps.inventory` Tests | **16 / 16 PASS** | StockItem, StockMovement ledger, StockReservation, staff restock/adjust |
| `apps.cart` Tests | **8 / 18 PASS (10 FAIL)** | **CRITICAL: 8 CHECK constraint errors, 1 HTTP 500 failure, 1 constraint assertion failure** |
| **Code Formatting (`black --check .`)** | **FAIL** | 6 files would be reformatted (`apps/cart/*`, `apps/accounts/views.py`) |
| **Code Linting (`ruff check .`)** | **FAIL** | 36 lint errors in `apps/cart/tests/test_cart.py` (E702 multiple statements, E501 length) |
| **Async Infrastructure** | **CONFIGURED** | Celery 5.4.0, Redis 5.3.1, django-celery-beat 2.7.0, docker-compose services |
| **Orders Domain (`apps.orders`)** | **NOT STARTED** | 0 models, 0 migrations, 0 endpoints, 0 tests |
| **Payments Domain (`apps.payments`)** | **NOT STARTED** | 0 models, 0 migrations, 0 endpoints, 0 tests |

---

## 2. Forensic Timeline & Audit Reconciliation

To eliminate confusion between historical audit documents and the live codebase, the following forensic timeline documents exact repository events:

```
[2026-09-04 20:46] Phase 1 Completion Audit (accounts, core, auth, RBAC, addresses) -> 42 tests
[2026-09-04 23:30] Phase 2 Completion Audit (catalog, variants, wholesale pricing, reviews) -> 83 tests
[2026-09-05 15:32] Phase 3 Pre-Implementation Audit approved; stopping gate established
[2026-09-06 00:09] CODEX_PROJECT_TAKEOVER_AUDIT.md generated:
                   - Reported inventory and cart as NOT STARTED.
                   - Flagged PII filter bug in record.msg vs record.args.
                   - Flagged black formatting deviation in base.py.
[2026-09-06 00:14] Commit/Edit: apps/core/middleware.py updated.
                   - Redaction now evaluates record.getMessage(), clears record.args, applies phone regex.
[2026-09-06 00:16] Commit/Edit: apps/inventory created.
                   - StockItem, StockMovement, StockReservation, InventoryService, staff views created.
                   - Migration 0001_initial generated and applied. 16 tests written and passing.
[2026-09-06 00:32] Commit/Edit: apps/cart created.
                   - Cart, CartItem, CartService, views, serializers, migration 0001_initial generated.
                   - apps/accounts/views.py updated to merge guest cart on login.
                   - 18 tests written hurriedly in minified/semicolon format.
[2026-09-06 00:38] Execution halted with 10 cart test failures and lint violations.
[2026-09-06 15:37] CURRENT_PROJECT_TAKEOVER_AUDIT.md conducted (this report).
```

### Clarification of `CODEX_PROJECT_TAKEOVER_AUDIT.md` Discrepancies
1. **Inventory & Cart Status:** `CODEX_PROJECT_TAKEOVER_AUDIT.md` stated `apps.inventory` and `apps.cart` were "NOT STARTED". That was true at 00:09 on Sep 6. As of now, `inventory` is complete and green, while `cart` is partially implemented and failing.
2. **PII Masking Flaw:** `CODEX_PROJECT_TAKEOVER_AUDIT.md` correctly identified that `record.msg` alone was sanitized. This was fixed at 00:14 by calling `str(record.getMessage())` and clearing `record.args = ()`. Live test output confirmed secrets are now masked: `secret=********`.
3. **Black Formatting:** `base.py` formatting was resolved; current formatting failures are isolated to `apps/cart` and `apps/accounts/views.py`.

---

## 3. Comprehensive Domain-by-Domain Audit

### 3.1 `apps.core` (Phase 1 Foundation) — HEALTHY
- **Architecture:** Abstract base model `TimeStampedModel` providing indexed `created_at` and `updated_at`.
- **Envelope Renderer:** `StandardResponseRenderer` enforces `{success, request_id, message, data, error}` envelope. HTTP 204 remains bodyless.
- **Exception Handler:** Sanitizes unhandled exceptions into structured 500 responses with request correlation IDs.
- **Logging Sanitization (`PIIMaskingFilter`):**
  - Sanitizes PAN (`[A-Z]{5}[0-9]{4}[A-Z]{1}`), GSTIN, Phone numbers, passwords, Bearer tokens, and secrets.
  - Formatted string evaluation: Invokes `str(record.getMessage())` and clears `record.args = ()`, preventing format-string leaks.
  - Handles exception tracebacks via `record.exc_text`.
- **Health Probes:**
  - `/health/liveness/` -> `{"status": "live"}` (Public).
  - `/health/readiness/` -> Performs `SELECT 1` database query (Public).
- **Test Suite:** 14 tests, 100% passing in 0.23s.

### 3.2 `apps.accounts` (Phase 1 Authentication & RBAC) — HEALTHY
- **User Model:** Custom UUID primary key, unique email (`USERNAME_FIELD`), normalized phone number (`91XXXXXXXXXX`), role choices (`CUSTOMER`, `WHOLESALE_PENDING`, `WHOLESALE_APPROVED`, `STAFF`, `MANAGER`, `SUPERADMIN`).
- **Wholesale Verification:** Two-tier security gate. `is_wholesale_buyer` requires `role == WHOLESALE_APPROVED` AND `wholesale_profile.verification_status == APPROVED`.
- **Address Management:** Scoped to `user=request.user` to eliminate IDOR. Atomic `save()` ensures single default shipping and billing address invariants.
- **JWT & Cookie Architecture:** Short-lived access tokens (15 min) in JSON; refresh tokens (7 days) stored in `HttpOnly`, `SameSite=Lax` cookies scoped to `/api/v1/auth/`.
- **Login View Integration:** Modified at 00:32 to read `guest_cart_token` from cookies, trigger `CartService.merge_guest_cart_into_user_cart()`, and clear the guest cookie.
- **Test Suite:** 32 tests, 100% passing in 8.57s.

### 3.3 `apps.catalog` (Phase 2 Catalog Domain) — HEALTHY
- **Models:** `Category`, `Product`, `ProductVariant`, `WholesaleTierPricing`, `ProductImage`, `ProductReview`, `ReviewImage`.
- **`Product.category` FK On-Delete:** Explicitly verified as `on_delete=models.PROTECT` in `apps/catalog/models.py` (line 75) and `apps/catalog/migrations/0001_initial.py` (line 194). Categories with active products cannot be accidentally deleted.
- **Variant Stock Field Verification:** Confirmed that `ProductVariant` contains **NO `stock_quantity` field**. Stock authority is strictly decoupled into `apps.inventory.StockItem`.
- **Wholesale Pricing Security:**
  1. Queryset layer: `CatalogService.get_base_product_queryset()` prefetches `wholesale_slabs` only if `user.is_wholesale_buyer`.
  2. Serializer layer: `ProductVariantSerializer.get_wholesale_slabs()` redacts slabs if the caller is not an approved wholesale buyer.
- **Known Optimization Debt:** `CategorySerializer.get_subcategories()` invokes `.filter(is_active=True)` on prefetched subcategories, bypassing Django’s in-memory prefetch cache (minor N+1 query pattern).
- **Test Suite:** 41 tests, 100% passing in 8.08s.

### 3.4 `apps.inventory` (Phase 3 Step 2) — HEALTHY & VERIFIED
- **Architecture:**
  - `StockItem`: OneToOne with `ProductVariant` (`on_delete=models.PROTECT`). Fields: `quantity_on_hand`, `quantity_reserved`, `reorder_level`.
  - Database Constraints:
    - `inventory_on_hand_non_negative`: `quantity_on_hand >= 0`.
    - `inventory_reserved_non_negative`: `quantity_reserved >= 0`.
    - `inventory_reserved_not_above_on_hand`: `quantity_on_hand >= quantity_reserved`.
  - Computed Property: `quantity_available` = `quantity_on_hand - quantity_reserved`.
- **Audit Ledger (`StockMovement`):**
  - Append-only event store: `INBOUND`, `SALE`, `RESERVATION`, `CANCELLATION`, `EXPIRY`, `ADJUSTMENT`.
  - Enforced immutability: `save()` raises `ValidationError` on updates; `delete()` raises `ValidationError`.
  - Captures `stock_item`, `quantity_delta`, `reserved_quantity_delta`, `actor`, `reference_type`, `reference_id`, and `note`.
- **Reservation Lifecycle (`StockReservation`):**
  - Statuses: `ACTIVE`, `RELEASED`, `CONSUMED`, `EXPIRED`.
  - Uncoupled reference: `reference_type` (`CART`, `ORDER`) and `reference_id` (UUID), avoiding circular FKs.
- **Concurrency & Locking:**
  - `InventoryService` wraps all mutations in `@transaction.atomic`.
  - `_locked_stock_item()` employs `StockItem.objects.select_for_update()`.
  - Concurrency conflict handling: `InventoryConflict` exception mapped to HTTP 409.
- **REST Endpoints:**
  - `GET /api/v1/inventory/` -> Paginated stock items (Staff/Manager only).
  - `GET /api/v1/inventory/<pk>/` -> Stock item detail (Staff/Manager only).
  - `POST /api/v1/inventory/restock/` -> Inbound physical restock (Staff/Manager only).
  - `POST /api/v1/inventory/<pk>/adjust/` -> Stock adjustment (Manager/Admin only).
- **Test Suite:** 16 tests, 100% passing in 2.40s.

### 3.5 `apps.cart` (Phase 3 Step 3) — DEFECTIVE & FAILING
- **Architecture:**
  - `Cart`: Linked to `user` (OneToOne, null=True, cascade) or `guest_token` (CharField 64, unique, null=True).
  - `CartItem`: Linked to `cart` (CASCADE) and `variant` (PROTECT). Unique constraint on `(cart, variant)`.
  - Check constraint on `CartItem`: `cart_item_quantity_positive` (`quantity > 0`).
  - Check constraint on `Cart`: `cart_has_exactly_one_owner` (`(user IS NOT NULL AND guest_token IS NULL) OR (user IS NULL AND guest_token > "")`).
- **Defects Identified:**

  #### Defect 1: Critical `IntegrityError` in `CartService.add_item` and `merge_guest_cart_into_user_cart`
  - **Root Cause:** In `apps/cart/services/cart_service.py` (lines 58 and 104):
    ```python
    item, created = CartItem.objects.select_for_update().get_or_create(
        cart=cart, variant=variant, defaults={"quantity": 0}
    )
    ```
    `get_or_create` inserts a new `CartItem` row with `quantity=0`. The database `CheckConstraint(quantity > 0)` immediately aborts the transaction with `IntegrityError: CHECK constraint failed: cart_item_quantity_positive`.
  - **Impact:** Any attempt by an authenticated user or guest to add a new item to an empty cart results in an HTTP 500 crash.
  - **Test Casualties:** Causes 8 test errors across `test_update`, `test_duplicate_items_blocked`, `test_add_and_accumulate`, `test_remove`, `test_clear`, `test_cart_does_not_reserve_inventory`, `test_api_idor`, and `test_api_guest_add_and_cookie`.

  #### Defect 2: SQL Check Constraint Logic Error in `Cart`
  - **Root Cause:** In `apps/cart/models.py` (line 21):
    ```python
    check=(Q(user__isnull=False, guest_token__isnull=True) | Q(user__isnull=True, guest_token__gt=""))
    ```
    In SQL three-valued logic, when both `user` and `guest_token` are `NULL`, the expression `guest_token > ""` evaluates to `NULL` (unknown). In SQL `CHECK` constraints, a constraint fails ONLY if the expression evaluates to `FALSE`; `NULL` passes!
  - **Impact:** An orphaned cart with `user=None` and `guest_token=None` can be inserted into the database without triggering an `IntegrityError`.
  - **Test Casualty:** `test_owner_constraint` fails: `AssertionError: IntegrityError not raised`.

  #### Defect 3: Code Style and Quality Collapse
  - **Root Cause:** `apps/cart/tests/test_cart.py` was written using minified syntax with multiple statements separated by semicolons on single lines.
  - **Impact:** 36 `ruff` lint violations (`E702`, `E501`) and 6 files violating `black` formatting standards.

- **Test Suite:** 18 tests, 8 PASS, 2 FAILURES, 8 ERRORS.

---

## 4. Unstarted Phase 3 Domains

### 4.1 `apps.orders` — NOT STARTED
- **Status:** No models, no migrations, no services, no views, no serializers, no tests exist.
- **Architectural Imperatives Required for Implementation:**
  1. **Address Snapshotting:** Must snapshot shipping address fields (`full_name`, `address_line1`, `city`, `pincode`, etc.) directly onto the `Order` model. Never rely solely on a foreign key to `apps.accounts.Address`, as customers may edit or delete addresses.
  2. **Price & Product Snapshotting:** Must snapshot `product_name`, `variant_name`, `sku`, `weight_in_grams`, `mrp`, `unit_selling_price`, and `line_total` onto `OrderLineItem`. Prices must never be recalculated from current catalog values after order placement.
  3. **Order State Machine:** `PENDING_PAYMENT` -> `CONFIRMED` -> `PROCESSING` -> `SHIPPED` -> `DELIVERED` / `CANCELLED` / `REFUNDED`. State transitions must be auditable via `OrderStatusHistory`.
  4. **Stock Reservation to Consumption:** During checkout, the active `StockReservation` created during checkout initiation must transition to `CONSUMED` upon payment confirmation, or `RELEASED` upon cancellation/abandonment.
  5. **Review Service Integration:** `apps/catalog/services/review_service.py` currently attempts to import `OrderItem` and `OrderStatus` from `apps.orders.models`. The model design must provide these symbols.

### 4.2 `apps.payments` — NOT STARTED
- **Status:** No models, no migrations, no services, no views, no serializers, no tests exist.
- **Architectural Imperatives Required for Implementation:**
  1. **Razorpay Integration:** Server-side order creation (`client.order.create`) with currency `INR`, amount in paise (integer).
  2. **Signature Verification:** Razorpay signature verification (`razorpay_order_id|razorpay_payment_id` against `RAZORPAY_KEY_SECRET`) using HMAC-SHA256.
  3. **Webhook Idempotency:** Must persist raw webhook events in an append-only `PaymentWebhookEvent` table with unique constraint on `event_id`. Duplicate webhook deliveries must be acknowledged with HTTP 200 without reprocessing.
  4. **Zero Client Trust:** Never trust client-supplied amounts, status strings, or payment IDs. Payment capture and order confirmation must be driven entirely by cryptographic signature verification and server-to-server webhooks.

---

## 5. Security & Data Protection Audit

| Finding | Severity | Component | Description & Remediation |
|---|---|---|---|
| **Cart CHECK Constraint SQL NULL Leak** | **Medium** | `apps.cart.models.Cart` | When `user` and `guest_token` are both NULL, SQL evaluates `guest_token > ""` to NULL, bypassing the check constraint. **Remediation:** Add `guest_token__isnull=False` to the second Q object or enforce explicit constraints. |
| **Guest Cart Token Enumeration** | **Low** | `apps.cart.services.CartService` | Uses `secrets.token_urlsafe(32)` providing 256 bits of cryptographic entropy. Guessing or enumerating guest carts is cryptographically infeasible. |
| **Catalog Wholesale Price Leakage** | **Protected** | `apps.catalog.serializers` | Two-layer defense ensures non-wholesale users never see wholesale slabs or volume pricing tiers. |
| **PII & Secret Logging Exposure** | **Remediated** | `apps.core.middleware` | Log arguments are pre-rendered into `record.msg` and `record.args` is cleared. Passwords, tokens, PAN, and phone numbers are verified masked in live test outputs. |
| **Address IDOR Protection** | **Protected** | `apps.accounts.views` | Address lookups explicitly filter on `user=request.user`. Users cannot view or modify addresses belonging to other customers. |
| **Row-Level Concurrency Locks** | **Protected** | `apps.inventory.services` | All inventory movements and reservations use `select_for_update()` inside atomic transactions. Over-allocation is prevented at the database level. |

---

## 6. Asynchronous Infrastructure (Celery / Redis)

- **Dependencies:** `celery==5.4.0`, `redis==5.3.1`, `django-celery-beat==2.7.0` installed in the Python 3.12 environment.
- **Celery Application:** Configured in `config/celery.py` with `autodiscover_tasks()` and `DJANGO_SETTINGS_MODULE=config.settings.development`.
- **Django Settings:**
  - `CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")`
  - `CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")`
  - `CELERY_TIMEZONE = "Asia/Kolkata"`
  - `CELERY_TASK_SERIALIZER = "json"` (Security: pickle is forbidden)
  - `CELERY_TASK_ACKS_LATE = True` (Reliability: re-queued on unhandled worker termination)
  - `CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"`
- **Docker Compose:** Configured with `redis` (Redis 7 alpine with healthcheck), `celery` worker, and `celery-beat`.
- **Current Deficit:** No background task modules (`tasks.py`) have been written yet. Specifically, the automated periodic cleanup of expired inventory reservations (`StockReservation.objects.filter(status="ACTIVE", expires_at__lte=now)`) has not yet been registered as a Celery task.

---

## 7. Master Remediation Roadmap

To bring the project to 100% production readiness and complete Phase 3, the following sequence must be executed:

```
[STEP 1: REPAIR CART DOMAIN]
  ├── Fix CartService.add_item defaults={"quantity": quantity}
  ├── Fix CartService.merge_guest_cart_into_user_cart defaults={"quantity": allowed}
  ├── Correct Cart.Meta check constraint to prevent orphaned NULL/NULL carts
  ├── Refactor apps/cart/tests/test_cart.py into PEP-8 / Black compliant structure
  ├── Run black . and ruff check . to ensure clean formatting
  └── Verify 121 / 121 tests PASSING

[STEP 2: INVENTORY CELERY PERIODIC TASKS]
  ├── Create apps/inventory/tasks.py with expire_stale_reservations task
  └── Register periodic schedule via django-celery-beat

[STEP 3: IMPLEMENT APPS.ORDERS]
  ├── Models: Order, OrderLineItem, OrderStatusHistory
  ├── Address and pricing immutable snapshot logic
  ├── CheckoutService: Atomically reserve stock, calculate authoritative price, create order
  ├── Order customer and staff APIs with strict RBAC
  └── Unit and integration tests (target >= 25 tests)

[STEP 4: IMPLEMENT APPS.PAYMENTS]
  ├── Models: Payment, PaymentWebhookEvent
  ├── Razorpay client integration and HMAC-SHA256 signature verification
  ├── Webhook handler with deduplication and idempotency
  ├── Transition orders from PENDING_PAYMENT to CONFIRMED
  ├── Transition inventory reservations from ACTIVE to CONSUMED
  └── Payment test suite with mocked gateways (target >= 20 tests)

[STEP 5: FULL SUITE VERIFICATION & PRODUCTION STACK AUDIT]
  ├── Run full test suite across all 6 applications
  ├── Verify clean migrations and zero lint/format issues
  └── Perform live containerized verification on PostgreSQL 16 + Redis
```

---

## 8. Conclusion

The Bharath Masala backend is structurally sound across Phase 1, Phase 2, and Phase 3 Inventory. The inventory architecture (immutable ledger, explicit reservation state machine, and row locking) represents best-in-class financial/commerce design. 

The immediate blocker is **isolated to `apps.cart`** due to a straightforward `defaults={"quantity": 0}` insert bug that conflicts with a strict database check constraint, alongside minified test code. Once these cart defects are corrected, the codebase will be fully green at 121 tests, clearing the path to implement Orders and Payments with full confidence.
