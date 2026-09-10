# PHASE 3.6 — BACKGROUND TASKS, RESERVATION EXPIRY & ABANDONED ORDER RECOVERY
## COMPLETION & VERIFICATION REPORT

**Project:** Bharath Masala Products E-Commerce Platform (Production Django 5.0 / DRF / PostgreSQL 16 Backend)  
**Completion Date:** 2026-09-06T18:07:00+05:30  
**Phase:** Phase 3.6 — Background Tasks, Reservation Expiry & Abandoned Order Recovery  
**Status:** **100% COMPLETE & VERIFIED**  
**Total Automated Tests:** **227 / 227 PASSING** (100% Green across all 7 applications)

---

## 1. Executive Summary

Phase 3.6 has been successfully implemented, verified, and integrated into the Bharath Masala platform. This phase resolves critical production concurrency risks, delivers automated background inventory reclamation, implements abandoned order transitions, and establishes scheduled periodic task automation.

### Key Milestones Achieved:
1. **Universal Lock Hierarchy Enforced:**
   - Corrected the concurrency inconsistency between customer payment verification and gateway webhooks.
   - Standardized universal database locking order across all services:
     $$\mathbf{Order} \longrightarrow \mathbf{Payment} \longrightarrow \mathbf{StockReservation} \longrightarrow \mathbf{StockItem}\text{ (ordered by variant ID)}$$
   - Eliminates potential PostgreSQL deadlock exceptions (`DeadlockDetected`) under high checkout concurrency.
2. **Post-Expiry Payment Reconciliation Guard:**
   - If a payment is captured on Razorpay for an order whose reservations have already expired (`order_status == FAILED`), the system:
     - Never consumes expired or non-existent inventory.
     - Never changes a `FAILED` order back to `CONFIRMED`.
     - Preserves the captured payment data for financial auditing.
     - Flags the payment record with `RECONCILIATION_REQUIRED` for refunding.
3. **Automated Abandoned Order Recovery Service (`OrderService.expire_abandoned_orders`):**
   - Automatically detects orders in `PENDING_PAYMENT` whose stock reservations have passed their TTL.
   - Employs per-order transaction isolation so that a lock or failure on Order A never prevents Order B from completing.
   - Atomically releases inventory reservations with `expired=True` via `InventoryService.release_reservation()`.
   - Decrements `quantity_reserved` and restores `quantity_available` without touching physical `quantity_on_hand`.
   - Writes immutable `StockMovement` ledger entries with `MovementType.EXPIRY`.
   - Transitions order to `OrderStatus.FAILED` and creates auditable `OrderStatusHistory`.
4. **Celery Shared Task & Beat Scheduling:**
   - Implemented `@shared_task` `cleanup_expired_reservations_and_orders` in `apps/orders/tasks.py`.
   - Configured `CELERY_BEAT_SCHEDULE` in `config/settings/base.py` to run every 60 seconds (1 minute).
   - Fully idempotent: multiple consecutive or concurrent executions never double-decrement stock or duplicate records.
5. **Quality Gates & Test Coverage:**
   - **227 / 227 automated tests passing** (25 new tests added in Phase 3.6).
   - Zero Django system check warnings.
   - Zero migration drift (`makemigrations --check --dry-run`).
   - 100% clean formatting (`black --check .`) and linting (`ruff check .`).

---

## 2. Inventory of Modified and Created Files

| File | Status | Purpose & Changes |
|---|---|---|
| `apps/payments/services/webhook_service.py` | **MODIFIED** | Enforced universal lock hierarchy (`Order` before `Payment`), prevented `FAILED` order confirmation, flagged post-expiry captures as `RECONCILIATION_REQUIRED`. |
| `apps/payments/tests/test_webhooks.py` | **MODIFIED** | Added `test_webhook_payment_captured_after_order_failed_reconciliation` verifying post-expiry guard. |
| `apps/orders/services/order_service.py` | **CREATED** | Implemented `OrderService.expire_abandoned_orders()` with per-order atomic isolation, safe locking, and audit trail generation. |
| `apps/orders/services/__init__.py` | **MODIFIED** | Exported `OrderService` alongside `CheckoutService` and `OrderStateMachine`. |
| `apps/orders/services/checkout_service.py` | **MODIFIED** | Re-exported `OrderService` for backwards compatibility. |
| `apps/orders/tasks.py` | **CREATED** | Created Celery `@shared_task` `cleanup_expired_reservations_and_orders()` invoking `OrderService.expire_abandoned_orders()`. |
| `apps/orders/tests/test_tasks.py` | **CREATED** | Added 24 exhaustive unit and integration tests covering reservation expiry, order recovery, idempotency, concurrency, and Celery execution. |
| `config/settings/base.py` | **MODIFIED** | Registered `CELERY_BEAT_SCHEDULE` with 60-second periodic schedule. |

---

## 3. Test Suite Verification Metrics

```text
======================================================================
TOTAL TESTS EXECUTED: 227
  - PASSING:          227  (100.0%)
  - FAILURES:           0  (  0.0%)
  - ERRORS:             0  (  0.0%)
  - SKIPPED:            0  (  0.0%)
TOTAL RUNTIME:        46.95s
STATUS:               OK
======================================================================
```

### Breakdown by Application Domain:
- `apps.core`: **14 tests** (100% passing)
- `apps.accounts`: **32 tests** (100% passing)
- `apps.catalog`: **41 tests** (100% passing)
- `apps.inventory`: **16 tests** (100% passing)
- `apps.cart`: **23 tests** (100% passing)
- `apps.orders`: **58 tests** (100% passing — 34 existing + 24 new task tests)
- `apps.payments`: **43 tests** (100% passing — 42 existing + 1 new reconciliation test)

---

## 4. Phase 3.6 Test Scenario Coverage Matrix (`test_tasks.py`)

| # | Test Name | Invariant Verified |
|---|---|---|
| 1 | `test_active_expired_reservation_becomes_expired` | Reservation transitions `ACTIVE -> EXPIRED` and `released_at` is set. |
| 2 | `test_quantity_reserved_decreases_correctly` | `stock_item.quantity_reserved` decrements by reservation quantity. |
| 3 | `test_quantity_available_becomes_available_again` | Available stock pool restored from 48 back to 50. |
| 4 | `test_stock_movement_expiry_ledger_created` | Ledger record with `MovementType.EXPIRY` and negative reserved delta created. |
| 5 | `test_non_expired_active_reservation_remains_untouched` | Active reservations within 30-min TTL are preserved. |
| 6 | `test_expired_pending_payment_order_becomes_failed` | Abandoned order transitions `PENDING_PAYMENT -> FAILED`. |
| 7 | `test_order_status_history_created` | `OrderStatusHistory` created with `from=PENDING_PAYMENT, to=FAILED`. |
| 8 | `test_expiry_note_is_recorded` | History note explicitly documents reservation expiration. |
| 9 | `test_confirmed_order_is_never_changed` | Paid/confirmed orders are never failed by expiry task. |
| 10 | `test_processing_order_is_never_changed` | Fulfillment-stage orders remain untouched. |
| 11 | `test_cancelled_order_is_never_changed` | Cancelled orders are never re-processed. |
| 12 | `test_consumed_reservation_is_never_released` | Consumed reservations are protected from release. |
| 13 | `test_released_reservation_is_ignored` | Manually cancelled reservations are ignored by task. |
| 14 | `test_already_expired_reservation_is_ignored` | Previously expired reservations safely no-op. |
| 15 | `test_multiline_order_reservations_expire_correctly` | Multi-item orders have all reservations released atomically. |
| 16 | `test_cleanup_twice_does_not_double_decrement_stock` | Multiple cleanup calls never reduce reserved stock below zero. |
| 17 | `test_cleanup_twice_does_not_duplicate_stock_movements` | Idempotency: ledger count remains exactly 1. |
| 18 | `test_cleanup_twice_does_not_duplicate_order_history` | Idempotency: history count remains exactly 1. |
| 19 | `test_already_failed_order_remains_unchanged` | Re-running against a failed order returns 0 changes. |
| 20 | `test_multiple_workers_do_not_process_same_order_twice` | Concurrency isolation skips already processed orders. |
| 21 | `test_payment_verification_racing_with_expiry_behaves_safely` | If verify captures first, expiry task safely skips order. |
| 22 | `test_webhook_capture_racing_with_expiry_behaves_safely` | If webhook confirms first, expiry task safely skips order. |
| 23 | `test_celery_task_execution_eager` | Task executes cleanly via `cleanup_expired_reservations_and_orders.delay()`. |
| 24 | `test_celery_task_rerun_remains_idempotent` | Re-running Celery task produces 0 expired orders on second run. |

---

## 5. Static Analysis & Verification Quality Gates

```bash
# 1. System Check
python3 manage.py check
System check identified no issues (0 silenced).

# 2. Migration Drift Check
python3 manage.py makemigrations --check --dry-run
No changes detected

# 3. Formatting
black --check .
All done! ✨ 🍰 ✨
138 files would be left unchanged.

# 4. Linter
ruff check .
All checks passed!
```

---

## 6. Phase 3.6 Sign-off & Current Status

* **Current Status:** Phase 3.6 (Background Tasks, Reservation Expiry & Abandoned Order Recovery) is **100% COMPLETE**.
* **Stopping Rule:** Implementation stopped cleanly. No further code or phases are being modified without authorization.
