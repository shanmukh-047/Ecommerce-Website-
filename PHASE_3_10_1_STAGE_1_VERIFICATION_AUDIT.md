# PHASE 3.10.1 — STAGE 1 POST-IMPLEMENTATION VERIFICATION AUDIT
## Strict Read-Only Concurrency, Financial & Mathematical Audit

**Auditor:** Antigravity Senior Backend & Concurrency Systems Auditor  
**Audit Mode:** READ-ONLY (Zero Code / Zero Migration Modifications)  
**Date:** 2026-09-06  
**Target Applications Audited:** `apps.orders`, `apps.payments`, `apps.shipping`, `apps.invoices`, `apps.returns`, `apps.inventory`  
**Test Suite Baseline:** 405 / 405 Passing (100.0% Green)  

---

## 1. Stage 1 Verification Results Summary

| Issue | Title | Result | Summary Justification |
|---|---|---|---|
| **ISSUE-001** | Order Cancellation vs. Shipment Dispatch Race Condition | **VERIFIED** | Strict row-locking on `Order` then `Shipment`s prevents cancellation once consignments enter transit. Cancellation and status transitions serialize cleanly on `Order`. |
| **ISSUE-002** | Partial Refund Accumulation & Payment State Integrity | **PARTIALLY VERIFIED** | Refund accumulation and balance checking are mathematically sound under lock in `PaymentService`. However, an unhandled lock order inversion exists in the fallback branch of `WebhookService.process_razorpay_webhook` (`Payment` locked before `Order`). |
| **ISSUE-003** | Invoice Discount Accounting & GST Integrity | **PARTIALLY VERIFIED** | Zero-cost replacement orders and standard single/two-line discounts behave as expected. However, an edge case in proportional discount allocation causes $\sum \text{line\_discount} > \text{invoice.total\_discount}$ when multiple lines round up, producing a 1-paisa discrepancy. |

---

## 2. Independent Findings Classification

### Finding 1 [HIGH]: Fallback Webhook Path Locks `Payment` Before `Order` (Lock Inversion Risk)
- **Location:** `apps/payments/services/webhook_service.py` (Lines 93–100)
- **Description:**  
  While the primary lookup path (`if target_ids:`) locks `Order` first then `Payment` second, the `else:` fallback block locks `Payment` first and then locks `Order`:
  ```python
  else:
      payment = (
          Payment.objects.select_for_update()
          .filter(gateway_order_id=gateway_order_id)
          .first()
      )
      if payment and payment.order_id:
          order = Order.objects.select_for_update().filter(pk=payment.order_id).first()
  ```
  If a webhook hits this fallback path concurrently with `OrderStateMachine.cancel_order` or `PaymentService.refund_payment` (which lock `Order` first, then `Payment`), a PostgreSQL deadlock (`deadlock detected`) can occur.
- **Root Cause:** Attempting to retrieve the `order_id` by locking `Payment` first rather than reading `order_id` in an uncommitted non-locking query.
- **Classification:** **HIGH**

---

### Finding 2 [MEDIUM]: Proportional Discount Allocation Overflow on Multiple Upward Roundings
- **Location:** `apps/invoices/services/invoice_service.py` (Lines 208–220)
- **Description:**  
  The proportional discount allocator loops through lines, quantizing each line's share to 2 decimal places with `ROUND_HALF_UP`, and assigns the remainder to the final line:
  ```python
  if idx == len(order_lines) - 1:
      line_disc = effective_discount - running_allocated
  else:
      line_disc = (
          effective_discount * (line.line_subtotal / order_items_gross)
      ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
      running_allocated += line_disc
  allocated_discounts.append(max(Decimal("0.00"), line_disc))
  ```
  **Concrete Edge Case:**  
  Consider an order with 4 lines: ₹10.00, ₹10.00, ₹10.00, ₹1.00 (Total ₹31.00) and an order discount of ₹0.02.
  - Line 0: $0.02 \times (10/31) = 0.00645 \to$ quantized to ₹0.01 (`running_allocated` = ₹0.01)
  - Line 1: $0.02 \times (10/31) = 0.00645 \to$ quantized to ₹0.01 (`running_allocated` = ₹0.02)
  - Line 2: $0.02 \times (10/31) = 0.00645 \to$ quantized to ₹0.01 (`running_allocated` = ₹0.03)
  - Line 3 (Last): $0.02 - 0.03 = -0.01 \to$ clamped by `max(0, -0.01)` to ₹0.00.
  - **Result:** Allocated discounts = `[0.01, 0.01, 0.01, 0.00]`.  
    $$\sum \text{allocated\_discounts} = \mathbf{0.03} \ne \mathbf{0.02} \text{ (Order Discount)}$$
  - Net lines sum to ₹30.97, while `order.items_subtotal - effective_discount` equals ₹30.98. This violates the strict statutory invariant:
    $$\sum \text{line.taxable\_amount} + \text{total\_tax} + \text{shipping} \ne \text{invoice.grand\_total}$$
- **Classification:** **MEDIUM** (Statutory rounding accuracy defect under specific multi-item line price ratios).

---

### Finding 3 [LOW]: Stage 1 Concurrency Tests Run Sequentially (No Multi-Threaded DB Contention)
- **Location:** `apps/orders/tests/test_cancellation_concurrency.py`, `apps/payments/tests/test_partial_refunds.py`
- **Description:**  
  All Stage 1 automated tests inherit from `django.test.TestCase` and run inside a single Python thread on a single database connection.
  For example, `test_cancellation_racing_with_shipment_dispatch_blocked_under_lock` executes `ShippingService.transition_shipment_status` completely to commit, and then sequentially runs `OrderStateMachine.cancel_order`.
  While this successfully tests the state-machine transition guard (`IN_TRANSIT` status check), it does **not** simulate two operating system threads executing `select_for_update()` at the exact same physical millisecond to verify wait-queue blocking and deadlock freedom.
- **Classification:** **LOW** (Test methodology observation; does not affect production runtime correctness as long as lock orders match).

---

## 3. Lock Acquisition Matrix (Observed Source Code Analysis)

The table below documents the exact lock acquisition sequence across all transactional service methods touching `Order`, `Payment`, `Shipment`, `StockReservation`, and `StockItem`.

| Service / Method | First Lock | Second Lock | Third Lock | Fourth Lock | Potential Conflict / Deadlock Risk |
|---|---|---|---|---|---|
| `OrderStateMachine.cancel_order` | `Order` (P001) | `Shipment` (ordered by `id`) | `StockItem` (via `InventoryService`) | — | **NONE** with status update (both acquire `Order` first). |
| `ShippingService.transition_shipment_status` | `Order` | `Shipment` | `StockItem` (if RTO) | — | **NONE**. Matches `cancel_order`. |
| `ShippingService.create_shipment` | `Order` | — | — | — | **NONE**. |
| `ShippingService.book_carrier_and_generate_label` | `Shipment` | — | — | — | **SAFE**: Does not touch or lock `Order`. |
| `ShippingService.cancel_shipment` | `Shipment` | — | — | — | **SAFE**: Does not touch or lock `Order`. |
| `PaymentService.refund_payment` | `Order` | `Payment` | — | — | **NONE**. Matches global hierarchy. |
| `PaymentService.capture_payment` | `Order` | `Payment` | — | — | **NONE**. Matches global hierarchy. |
| `WebhookService.process_razorpay_webhook` (Primary) | `Order` | `Payment` | — | — | **NONE**. Matches `refund_payment` and `capture_payment`. |
| `WebhookService.process_razorpay_webhook` (**Fallback**) | **`Payment`** | **`Order`** | — | — | ⚠️ **DEADLOCK RISK** with `refund_payment` or `cancel_order` if fallback is entered. |
| `CreditNoteService.generate_credit_note` | `Order` | `Invoice` | `CreditNoteSequence` | — | **NONE**. |
| `ReturnResolutionService.resolve_return` (Refund) | `ReturnRequest` | `Order` | `Invoice` / `CreditNoteSequence` | `Payment` | **NONE**. `Order` is locked before `Payment`. |
| `ReturnResolutionService.resolve_return` (Replacement) | `ReturnRequest` | `Order` | `StockReservation` | `StockItem` | **NONE**. |
| `OrderService.expire_pending_reservations` | `Order` (`skip_locked`) | `StockReservation` (ordered by `id`) | `StockItem` | — | **NONE**. |
| `CheckoutService.create_order_from_cart` | `Cart` | `CartItem` | `StockItem` (ordered by `variant_id`) | `Order` (INSERT) | **NONE**. New `Order` created after stock checks. |

### Deadlock Conflict Analysis:
1. **`Shipment` $\to$ `Order` vs `Order` $\to$ `Shipment`:**
   - Both `OrderStateMachine.cancel_order` and `ShippingService.transition_shipment_status` acquire `Order` first and `Shipment` second.
   - `book_carrier_and_generate_label` and `cancel_shipment` only acquire `Shipment` and never acquire `Order`.
   - **Conclusion:** No `Shipment` $\to$ `Order` inversion exists in the shipping domain.
2. **`Payment` $\to$ `Order` vs `Order` $\to$ `Payment`:**
   - Identified exclusively in `WebhookService` lines 93–100 (Finding 1).

---

## 4. Financial Invariant Verification

### 4.1 Payment & Refund Invariants (`apps.payments`)

| Invariant | Specification | Observed Code State | Status |
|---|---|---|---|
| **Invariant 1** | $0 \le \text{amount\_refunded} \le \text{payment.amount}$ | Enforced at lines 302–318 of `payment_service.py` under row-lock: `max_refundable = payment.amount - existing_refunded`. If `requested > max_refundable`, `PaymentConflict` is raised. | **VERIFIED** |
| **Invariant 2** | $\text{new\_total} = \text{existing} + \text{requested}$ | Line 349 adds requested refund to existing accumulated total; never overwrites. | **VERIFIED** |
| **Invariant 3** | $\text{CAPTURED} \to \text{PARTIALLY\_REFUNDED} \to \text{REFUNDED}$ | Verified. Payment transitions to `REFUNDED` only when `new_total_refunded >= payment.amount`. `Order.order_status` transitions to `REFUNDED` only on 100% refund balance. | **VERIFIED** |
| **Invariant 4** | Webhook Deduplication | `PaymentAttempt` logs `gateway_payment_id=refund_id`. Duplicate webhooks with same `refund_id` are skipped (`is_duplicate=True`). Legitimate second/third refunds with distinct IDs are permitted. | **VERIFIED** |

### 4.2 Invoice Mathematical Invariants (`apps.invoices`)

| Invariant | Specification | Observed Code State | Status |
|---|---|---|---|
| **Invoice Subtotals** | $\text{Items Subtotal} - \text{Total Discount} = \text{Taxable Subtotal} + \text{Total Tax}$ | Holds true in 1-item and 2-item orders. Subject to 1-paisa drift when proportional allocation rounds up across multiple items (Finding 2). | **PARTIALLY VERIFIED** |
| **Grand Total** | $\text{Taxable Subtotal} + \text{Total Tax} + \text{Shipping Fee} \equiv \text{Grand Total}$ | Lines 254, 274, 301 guarantee that within each line item, `taxable + tax = net_total`. If net totals sum to grand total, invariant holds. | **PARTIALLY VERIFIED** |
| **Replacement Invariant** | $\text{Grand Total} = 0 \implies \text{Taxable} = 0 \land \text{Tax} = 0$ | Lines 234–247 explicitly assign ₹0.00 to taxable, CGST, SGST, IGST, and total tax when net line consideration is zero. | **VERIFIED** |

---

## 5. Test Strength Evaluation

| Test Suite | Total Tests | Classification | Real Concurrency? | Notes |
|---|---|---|---|---|
| `test_cancellation_concurrency.py` | 4 | **STATE MACHINE & TRANSACTION TEST** | ❌ No | Tests sequential execution and state invariants. Does not run parallel threads with active DB lock contention. |
| `test_partial_refunds.py` | 6 | **STATE MACHINE & MOCK INTEGRATION TEST** | ❌ No | Tests financial accumulation, balance boundaries, and mock webhook idempotency sequentially. |
| `test_invoice_discounts.py` | 8 | **MATHEMATICAL & STATE MACHINE TEST** | ❌ N/A (Unit Math) | Thorough mathematical verification of GST percentages, B2B wholesale snapshots, and replacement orders. |

**Observation on Concurrency Testing:**  
Antigravity's test suite proves that **state machine transitions, exception guards, and accumulated balances behave correctly given specific database states**. However, it does not provide true concurrent load testing (e.g. `multiprocessing` or `threading` connecting to a live PostgreSQL cluster). The claim "Zero deadlock risks remain" must be qualified: deadlock freedom is derived from **static lock ordering inspection**, not runtime contention testing.

---

## 6. Migration Safety Verification

1. **`apps/payments/migrations/0003_alter_payment_status_alter_paymentattempt_status.py`:**
   - **Operations:** `AlterField` on `Payment.status` and `PaymentAttempt.status`.
   - **Data Risk:** Zero. Adds `"PARTIALLY_REFUNDED"` choice. Underlying database column is `VARCHAR(30)`. No data loss, no table lock.
2. **`apps/invoices/migrations/0003_invoice_total_discount_and_more.py`:**
   - **Operations:** `AddField` on `Invoice.total_discount` (`default=Decimal('0.00')`) and `InvoiceLineItem.discount_amount` (`default=Decimal('0.00')`).
   - **Data Risk:** Zero. Non-null defaults ensure all existing historical records retain valid numeric zeros without NULL pointer exceptions.
   - **Schema Drift:** `python3 manage.py makemigrations --check --dry-run` reports `No changes detected`.

---

## 7. Final Decision

**B. STAGE 1 PARTIALLY VERIFIED — FIX SPECIFIC FINDINGS FIRST**

### Justification:
While the core architecture for Stage 1 is robust and 405/405 tests pass:
1. **Finding 1 (HIGH):** The fallback branch in `WebhookService.process_razorpay_webhook` has an inverted lock order (`Payment` $\to$ `Order`), which creates an actual deadlock vulnerability under high webhook concurrency.
2. **Finding 2 (MEDIUM):** The proportional discount allocation algorithm in `InvoiceService.generate_invoice` allows $\sum \text{line\_discount} > \text{invoice.total\_discount}$ when multiple items round up, introducing a 1-paisa statutory tax distortion.

---

## 8. Stopping Boundary

In strict compliance with instructions:
- **No code was modified.**
- **No migrations were generated.**
- **No auto-fixers or formatters were executed.**
- Work is stopped here awaiting user instructions.
