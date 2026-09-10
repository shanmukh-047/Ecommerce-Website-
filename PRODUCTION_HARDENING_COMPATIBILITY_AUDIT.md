# PRODUCTION HARDENING COMPATIBILITY AUDIT

**Target:** Automated Post-Order Orchestration, Shipping Hooks, RBAC Standardization & Fail-Fast Validation  
**Date:** September 2026  
**Status:** COMPLETED & APPROVED FOR IMPLEMENTATION  

---

### 1. Objective
Assess compatibility and safety before implementing:
1. Automatic post-order event orchestration on `OrderStateMachine.transition_status(CONFIRMED)`.
2. Automatic shipping dispatch & delivery notification hooks on `ShippingService.transition_shipment_status()`.
3. Cancellation notification hook on `OrderStateMachine.cancel_order()`.
4. RBAC standardization across `apps.invoices` and `apps.notifications` (`IsAuthenticated, IsStaffOrManager`).
5. Fail-fast production configuration assertions in `config/settings/production.py`.

---

### 2. Compatibility Audit Findings

#### 2.1 Circular Import Prevention
* **Risk:** `apps.invoices` and `apps.notifications` import from `apps.orders` and `apps.shipping`. If `apps.orders` or `apps.shipping` directly import models or services from `apps.invoices` or `apps.notifications` at the module level, Python circular import errors will occur on startup.
* **Resolution:** 
  - Never import invoice or notification tasks/models at module top-level in `apps.orders` or `apps.shipping`.
  - Perform all invocations lazily inside `transaction.on_commit(lambda: ...)` callbacks or internal helper methods.
  - This preserves clean unidirectional module loading at startup.

#### 2.2 Transaction Boundary & Race Condition Safety
* **Risk:** Enqueueing Celery tasks (`.delay()`) directly inside active database transactions can cause worker race conditions. The worker may execute before the outer database transaction commits, resulting in `Order.DoesNotExist` or reading uncommitted state.
* **Resolution:**
  - Wrap all asynchronous task dispatches strictly in `transaction.on_commit(...)`:
    ```python
    transaction.on_commit(lambda: generate_invoice_for_order_task.delay(str(order.id)))
    transaction.on_commit(lambda: send_order_notifications_task.delay(str(order.id), NotificationEvent.ORDER_CONFIRMED))
    ```
  - If the database transaction rolls back, `on_commit` hooks will not fire, preventing orphaned tasks from executing.

#### 2.3 Idempotency & Replay Resilience
* **Risk:** Razorpay webhooks, network retries, or manual staff actions can trigger state machine or notification dispatches multiple times for the same order.
* **Verification:**
  - `InvoiceService.generate_invoice(order)`: Strictly checks `Invoice.objects.filter(order=order).first()`. If an invoice already exists, it returns the existing invoice without re-incrementing `InvoiceSequence`.
  - `NotificationService.send_order_notifications(order, event, ...)`: Enforces `idempotency_key = f"{order.id}:{event}:{channel}"`. If an existing log is in `SENT` status, it logs an informational note and safely skips dispatch without re-sending emails, WhatsApp, or SMS messages.

#### 2.4 RBAC Consistency
* **Existing State:**
  - `apps.orders.staff_views`: `[IsAuthenticated, IsStaffOrManager]`
  - `apps.payments.staff_views`: `[IsAuthenticated, IsStaffOrManager]`
  - `apps.shipping.staff_views`: `[IsAuthenticated, IsStaffOrManager]`
  - `apps.invoices.staff_views`: `[IsAdminUser]` (inconsistent)
  - `apps.notifications.staff_views`: `[IsAdminUser]` (inconsistent)
* **Resolution:**
  - Standardize `apps.invoices.staff_views` and `apps.notifications.staff_views` to `[IsAuthenticated, IsStaffOrManager]`.
  - Update tests to verify that both `STAFF` and `MANAGER` roles are authorized, while regular customers and unauthenticated callers remain blocked.

#### 2.5 Fail-Fast Production Settings
* **Existing State:**
  - `config/settings/base.py` provides default placeholder values (`rzp_test_placeholder`, `test_secret_placeholder`, `test_webhook_secret`).
  - `config/settings/production.py` enforces `SECRET_KEY`, `ALLOWED_HOSTS`, and `DATABASE_URL`, but does not inspect gateway credentials.
* **Resolution:**
  - Add fail-fast validation in `config/settings/production.py` to assert that `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET` are present, non-empty, and do not contain `"placeholder"` when `DEBUG=False`.

---

### 3. Implementation Plan

1. **`apps/orders/services/checkout_service.py`**:
   - In `OrderStateMachine.transition_status(CONFIRMED)`: add `transaction.on_commit()` to trigger invoice generation and `ORDER_CONFIRMED` notifications.
   - In `OrderStateMachine.cancel_order()`: add `transaction.on_commit()` to trigger `ORDER_CANCELLED` notifications.
2. **`apps/shipping/services/shipping_service.py`**:
   - In `transition_shipment_status()` when order advances to `SHIPPED`: add `transaction.on_commit()` to trigger `ORDER_SHIPPED` notifications.
   - In `transition_shipment_status()` when order advances to `DELIVERED`: add `transaction.on_commit()` to trigger `ORDER_DELIVERED` notifications.
3. **`apps/invoices/staff_views.py` & `apps/notifications/staff_views.py`**:
   - Update `permission_classes` to `[IsAuthenticated, IsStaffOrManager]`.
4. **`config/settings/production.py`**:
   - Add fail-fast checks for Razorpay credentials.
5. **Update Test Suites**:
   - Add unit tests verifying `on_commit` task dispatch and standardized RBAC permissions.
6. **Execute Full Quality Verification**:
   - `python3 manage.py check`
   - `python3 manage.py makemigrations --check --dry-run`
   - `black --check .`
   - `ruff check .`
   - `python3 manage.py test` (all 311+ tests)
