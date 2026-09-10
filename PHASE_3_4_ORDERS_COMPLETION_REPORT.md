# PHASE 3.4 — ORDERS & CHECKOUT DOMAIN COMPLETION REPORT

**Project:** Bharath Masala Products E-Commerce Platform (Production-Grade Django 5.0 / DRF / PostgreSQL 16 Backend)  
**Completion Date:** 2026-09-06T16:35:00+05:30  
**Phase:** Phase 3.4 — Orders & Checkout Domain  
**Target:** 100% Orders App Implementation, Inventory Reservation Integration, Snapshots, State Machine, REST APIs, and Zero Regressions  

---

## 1. Executive Summary

Phase 3.4 (Orders & Checkout Domain) has been fully implemented, integrated, and verified to production standards. The domain bridges customer intent from `apps.cart` into authoritative purchase contracts (`Order`, `OrderLineItem`), reserving real physical inventory via `apps.inventory`, and safeguarding against concurrency anomalies, IDOR attacks, and price tampering.

Key Accomplishments:
1. **Reconciliation & Architecture Compatibility:**
   - Named the status field `order_status` on `Order` to preserve backwards compatibility with `ReviewService.verify_user_purchase()`.
   - Exported `OrderItem = OrderLineItem` alias in `apps.orders.models`.
   - Implemented database-level deterministic row locking with `.order_by("variant_id")` to eliminate deadlocks.
   - Designed dual cancellation logic: `PENDING_PAYMENT` releases active reservations via `InventoryService.release_reservation()`, whereas `CONFIRMED`/`PROCESSING` cancels physically restock inventory via `InventoryService.add_stock()`.
2. **Authoritative Checkout Engine (`CheckoutService`):**
   - Atomically locks user cart and cart items (`select_for_update()`).
   - Re-evaluates pricing server-side through `CartService.unit_price()` (honoring B2B wholesale volume tier slabs vs retail selling price).
   - Generates collision-resistant order numbers (`BMP-YYYYMMDD-XXXXX`).
   - Freezes immutable flat shipping address and line item snapshots.
   - Creates active stock reservations with configurable TTL (`ORDER_RESERVATION_TIMEOUT_MINUTES = 30`).
   - Empties cart and records initial audit log entry.
3. **Finite State Machine (`OrderStateMachine`):**
   - Enforces strict unidirectional status transitions: `PENDING_PAYMENT` -> `CONFIRMED` -> `PROCESSING` -> `SHIPPED` -> `DELIVERED`.
   - Blocks illegal transitions and records every transition in `OrderStatusHistory`.
4. **Complete REST APIs:**
   - Customer Endpoints: Checkout (`POST /api/v1/orders/checkout/`), Order List (`GET /api/v1/orders/`), Order Detail (`GET /api/v1/orders/<pk>/`), and Cancellation (`POST /api/v1/orders/<pk>/cancel/`).
   - Staff Endpoints: Staff Order List with filtering/search (`GET /api/v1/staff/orders/`), Staff Detail (`GET /api/v1/staff/orders/<pk>/`), and Status Transition (`POST /api/v1/staff/orders/<pk>/status/`).
5. **Quality & Verification:**
   - **160 / 160 automated tests** passing (126 existing + 34 new orders tests, 100% pass rate).
   - Zero Django system check issues.
   - Zero unapplied migration drift.
   - 100% clean formatting (`black --check .`) and linting (`ruff check .`).

---

## 2. Inventory of Implemented Files

| Component / File | Purpose & Responsibilities |
|---|---|
| `apps/orders/models.py` | `OrderStatus` TextChoices, `Order` model, `OrderLineItem` (aliased as `OrderItem`), and `OrderStatusHistory` model. |
| `apps/orders/migrations/0001_initial.py` | Initial database migration creating tables, foreign keys, indexes, and check constraints. |
| `apps/orders/services/checkout_service.py` | `CheckoutService` (atomic checkout, deterministic locking, repricing, snapshots) & `OrderStateMachine` (transition validation, reservation consumption, restock). |
| `apps/orders/services/__init__.py` | Clean exports for service layer. |
| `apps/orders/serializers.py` | DRF serializers: `OrderSerializer`, `OrderLineItemSerializer`, `OrderStatusHistorySerializer`, `CheckoutRequestSerializer`, `OrderStatusUpdateSerializer`, `OrderCancelSerializer`. |
| `apps/orders/views.py` | Customer API views with IDOR protection: `CheckoutView`, `OrderListView`, `OrderDetailView`, `OrderCancelView`. |
| `apps/orders/staff_views.py` | Staff management views with RBAC: `StaffOrderListView`, `StaffOrderDetailView`, `StaffOrderStatusUpdateView`. |
| `apps/orders/urls.py` | URL routing for `/api/v1/orders/`. |
| `apps/orders/staff_urls.py` | URL routing for `/api/v1/staff/orders/`. |
| `apps/orders/admin.py` | Django admin configuration with inline line items and read-only status history. |
| `apps/orders/exceptions.py` | `OrderConflict` domain exception mapped to HTTP 409 Conflict. |
| `apps/orders/tests/factories.py` | Test fixtures (`create_order_user`, `create_wholesale_user`, `create_staff_user`, `create_order_address`, `add_to_cart`). |
| `apps/orders/tests/test_checkout_service.py` | 9 unit tests for checkout, retail/wholesale pricing, validation, and reservations. |
| `apps/orders/tests/test_snapshots.py` | 4 unit tests verifying address and pricing immutability and deletion safety. |
| `apps/orders/tests/test_state_machine.py` | 6 unit tests verifying lifecycle transitions, reservation release, physical restock, and ReviewService integration. |
| `apps/orders/tests/test_order_api.py` | 9 integration tests for customer checkout, listing, detail, cancellation, and IDOR defense. |
| `apps/orders/tests/test_staff_order_api.py` | 6 integration tests for staff order listing, filtering, search, RBAC, and status transitions. |
| `config/settings/base.py` | Registered `"apps.orders"` in `LOCAL_APPS` and added `ORDER_RESERVATION_TIMEOUT_MINUTES = 30`. |
| `config/urls.py` | Mounted `orders` and `staff-orders` namespaces under `api/v1/`. |

---

## 3. Architecture & Technical Decision Log

### 3.1 `order_status` Model Field Name
- **Decision:** The concrete DB column on `Order` is named `order_status`.
- **Rationale:** `apps.catalog.services.ReviewService.verify_user_purchase()` specifically queries:
  ```python
  OrderItem.objects.filter(
      order__user=user,
      order__order_status=OrderStatus.DELIVERED,
      variant__product=product,
  ).exists()
  ```
  Using `order_status` avoided breaking existing Phase 2 catalog code while maintaining full consistency. A convenience `@property def status(self)` was also provided.

### 3.2 `OrderItem` Backwards-Compatible Symbol
- **Decision:** Exported `OrderItem = OrderLineItem` at the module level in `apps/orders/models.py`.
- **Rationale:** Satisfies the import requirement `from apps.orders.models import OrderItem, OrderStatus` in `apps.catalog.services.review_service`.

### 3.3 Deterministic Database-Level Row Locking
- **Decision:** Ordered the query for variant stock items explicitly at the SQL level:
  ```python
  StockItem.objects.select_for_update().filter(variant_id__in=variant_ids).order_by("variant_id")
  ```
- **Rationale:** Sorting IDs in Python alone does not guarantee the database engine will acquire locks in ascending order. Adding `.order_by("variant_id")` ensures deterministic ascending lock acquisition in PostgreSQL and SQLite, eliminating deadlock hazards.

### 3.4 Dual Cancellation Strategy
- **`PENDING_PAYMENT` Cancellation:**
  - Reservations in `StockReservation` are `ACTIVE`.
  - Calling `InventoryService.release_reservation()` decrements `StockItem.quantity_reserved` and restores `quantity_available`.
- **`CONFIRMED` / `PROCESSING` Cancellation:**
  - Reservations were already consumed upon confirmation (`quantity_on_hand` and `quantity_reserved` decremented, reservation marked `CONSUMED`).
  - Attempting to release a consumed reservation raises `InventoryConflict`.
  - Instead, the state machine invokes `InventoryService.add_stock(line.variant, line.quantity, actor=actor, note=...)` to physically restock the warehouse, keeping stock accounting accurate.

---

## 4. Verification Suite Results

### 4.1 Django System Check
```bash
python3 manage.py check
System check identified no issues (0 silenced).
```

### 4.2 Migration Drift Check
```bash
python3 manage.py makemigrations --check --dry-run
No changes detected
```

### 4.3 Automated Test Suite
```bash
python3 manage.py test
Ran 160 tests in 35.454s

OK
```
**Test Distribution by Application:**
- `apps.core`: 14 tests
- `apps.accounts`: 32 tests
- `apps.catalog`: 41 tests
- `apps.inventory`: 16 tests
- `apps.cart`: 23 tests
- `apps.orders`: 34 tests
- **Total: 160 tests (100% passing, 0 errors, 0 failures)**

### 4.4 Code Formatting & Linting
```bash
black --check .
All done! ✨ 🍰 ✨
109 files would be left unchanged.

ruff check .
All checks passed!
```

---

## 5. Current Project Status & Readiness

- **Current State:** Phase 3.4 (Orders & Checkout) is **COMPLETE**.
- **Next Authorized Phase:** Phase 3.5 — Payments Domain (`apps.payments` - Razorpay integration, webhook processing, idempotent payment capture).
- **Stopping Rule:** Implementation stopped cleanly. No code for `apps.payments` has been written, awaiting explicit authorization.
