# PHASE 3.5 — PAYMENTS & PAYMENT PROCESSING DOMAIN IMPLEMENTATION PLAN
## Pre-Implementation Compatibility Audit & Architecture Specification

**Project:** Bharath Masala Products E-Commerce Platform  
**Backend:** Django 5.0 + Django REST Framework + PostgreSQL 16 + Redis 7 + Celery 5.4  
**Date:** 2026-09-06  
**Status:** Audit & Architecture Design Complete — Ready for Review & Authorization  

---

## 1. Executive Summary & Verification Baseline

Phase 3.4 (Orders & Checkout Domain) is 100% complete and verified:
- **Test Baseline:** 160 / 160 passing automated tests across all apps (`apps.core`: 14, `apps.accounts`: 32, `apps.catalog`: 41, `apps.inventory`: 16, `apps.cart`: 23, `apps.orders`: 34).
- **Static Analysis:** `python3 manage.py check` (0 issues), `python3 manage.py makemigrations --check --dry-run` (No changes detected).
- **Code Hygiene:** `black --check .` (109 files clean), `ruff check .` (All checks passed).

This document presents the comprehensive **Compatibility Audit** and **Technical Architecture** for **Phase 3.5 — Payments & Payment Processing Domain (`apps.payments`)**.

---

## 2. Codebase Compatibility Audit

### 2.1 Order Domain Integration (`apps.orders`)
- **`Order.order_status`:** Concrete database column with choices: `PENDING_PAYMENT`, `CONFIRMED`, `PROCESSING`, `SHIPPED`, `DELIVERED`, `CANCELLED`, `FAILED`, `REFUNDED`.
- **Checkout State:** When an order is placed, it is in `PENDING_PAYMENT` with `paid_at=None`.
- **Order State Machine Transitions:**
  - `OrderStateMachine.ALLOWED_TRANSITIONS[OrderStatus.PENDING_PAYMENT] = [OrderStatus.CONFIRMED, OrderStatus.CANCELLED, OrderStatus.FAILED]`.
  - When `OrderStateMachine.transition_status(order, OrderStatus.CONFIRMED, actor=..., notes=...)` is invoked:
    1. Finds all `StockReservation.objects.filter(reference_type="ORDER", reference_id=order.id, status=ReservationStatus.ACTIVE)`.
    2. Calls `InventoryService.consume_reservation(res.id, actor=actor)` for each active reservation.
    3. Sets `order.paid_at = timezone.now()`.
    4. Sets `order.order_status = OrderStatus.CONFIRMED`.
    5. Creates an audit record in `OrderStatusHistory`.
- **Review Service Compatibility:** `ReviewService.verify_user_purchase()` requires `order__order_status=OrderStatus.DELIVERED` and `OrderItem.objects.filter(...)`. Transitioning from `PENDING_PAYMENT` to `CONFIRMED` via payments keeps this contract intact.

### 2.2 Inventory Domain Integration (`apps.inventory`)
- **Stock Reservation Contract:**
  - `reference_type="ORDER"`
  - `reference_id=order.id` (UUID)
  - `status=ReservationStatus.ACTIVE`
  - `expires_at = order.created_at + ORDER_RESERVATION_TIMEOUT_MINUTES` (30 minutes default).
- **`InventoryService.consume_reservation(reservation_id, actor=None)`:**
  - Idempotent: If already `ReservationStatus.CONSUMED`, returns cleanly without double-decrementing.
  - If `status != ReservationStatus.ACTIVE`: raises `InventoryConflict("Only an active reservation can be consumed.")`.
  - If `expires_at <= timezone.now()`: raises `InventoryConflict("An expired reservation cannot be consumed.")`.
  - Decrements `stock_item.quantity_on_hand` and `stock_item.quantity_reserved`.
  - Sets `reservation.status = ReservationStatus.CONSUMED` and `consumed_at = timezone.now()`.
  - Creates immutable `StockMovement` with `MovementType.SALE`.
- **`InventoryService.release_reservation(reservation_id, actor=None, expired=False)`:**
  - Decrements `stock_item.quantity_reserved` and restores `quantity_available`.
  - Sets `reservation.status = ReservationStatus.EXPIRED` (if `expired=True`) or `ReservationStatus.RELEASED` (if `expired=False`).
  - Cannot release a `CONSUMED` reservation (raises `InventoryConflict`).

### 2.3 Failed Payments & Inventory Reservation Decision (Audit Resolution)
- **Problem Statement:** Determine whether a failed payment leaves reservations `ACTIVE` or releases them immediately.
- **Audit Decision (Reconciled Behavior):**
  - **Individual Payment Attempt Failure (Non-Terminal):** When an individual transaction attempt fails (e.g. card declined, bank server timeout, insufficient funds, OTP expired), the customer should be allowed to retry using an alternate payment method (e.g. UPI, NetBanking) within their 30-minute reservation window. Releasing inventory on the first attempt failure would penalize customers for temporary bank network errors. Thus, for payment attempt failures, the reservation remains **`ACTIVE`** until the TTL expires or the customer cancels.
  - **Terminal Order Cancellation / Failure:** If the customer explicitly cancels the order, or if the order is transitioned to terminal `OrderStatus.CANCELLED` or `OrderStatus.FAILED`, `OrderStateMachine.cancel_order()` releases all active reservations immediately.
  - **Reservation Expiry:** If the 30-minute TTL expires, periodic Celery tasks and/or just-in-time expiry checks release the reservation with `expired=True` and transition abandoned orders to `OrderStatus.CANCELLED` or `OrderStatus.FAILED`.

### 2.4 Idempotency & Concurrency Audit
Payment capture may be triggered simultaneously through two distinct channels:
1. **Frontend callback:** Customer browser finishes Razorpay checkout and calls `POST /api/v1/payments/orders/<id>/verify/`.
2. **Gateway webhook:** Razorpay server-to-server webhook fires `payment.captured` at `POST /api/v1/payments/webhooks/razorpay/`.
- **Mitigation:**
  - Both endpoints lock the order and payment using `select_for_update()` inside `transaction.atomic()`.
  - If `payment.status == PaymentStatus.CAPTURED` and `order.order_status == OrderStatus.CONFIRMED`, the transaction immediately returns the captured payment and confirmed order without re-executing state machine transitions or inventory consumption.
  - Webhooks record unique `event_id` in `PaymentWebhookEvent`. Duplicate event deliveries are logged and acknowledged with HTTP 200 OK without re-execution.

---

## 3. Domain Architecture & Structure

```
apps/payments/
├── __init__.py
├── apps.py                     # AppConfig: "apps.payments", verbose_name="Payments"
├── models.py                   # Payment, PaymentAttempt, PaymentWebhookEvent
├── admin.py                    # Django Admin integration with read-only audit trails
├── urls.py                     # Customer endpoints: initiate, verify, detail, webhooks
├── staff_urls.py               # Staff endpoints: list payments, retrieve payment
├── exceptions.py               # PaymentConflict, PaymentVerificationError
├── gateways/
│   ├── __init__.py
│   ├── base.py                 # PaymentGatewayInterface ABC
│   ├── razorpay_gateway.py     # Concrete Razorpay gateway implementation & HMAC verification
│   └── factory.py              # Gateway factory resolver
├── serializers.py              # PaymentSerializer, PaymentAttemptSerializer, PaymentWebhookSerializer
├── services/
│   ├── __init__.py
│   ├── payment_service.py      # Authoritative payment initiation, verification, and retry orchestration
│   └── webhook_service.py      # Webhook ingestion, signature validation, and deduplication
├── views.py                    # Customer views: PaymentInitiateView, PaymentVerifyView, PaymentDetailView
├── staff_views.py              # Staff views: StaffPaymentListView, StaffPaymentDetailView
├── webhook_views.py            # Gateway webhook ingress view (CSRF-exempt, signature-validated)
├── migrations/
│   └── __init__.py
└── tests/
    ├── __init__.py
    ├── factories.py            # Test factories for payments and webhook payloads
    ├── test_models.py          # Model constraints, fields, string representations
    ├── test_gateways.py        # Gateway abstraction and HMAC-SHA256 signature verification
    ├── test_payment_service.py # Payment initiation, capture, retries, reservation consumption
    ├── test_webhooks.py        # Webhook signature validation, idempotency, duplicate events
    ├── test_payment_api.py     # Customer initiate, verify, detail, IDOR protection
    └── test_staff_payment_api.py # Staff list, filters, RBAC permissions
```

---

## 4. Models Specification

### 4.1 Enums (`models.TextChoices`)
```python
class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    AUTHORIZED = "AUTHORIZED", "Authorized"
    CAPTURED = "CAPTURED", "Captured"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
    REFUNDED = "REFUNDED", "Refunded"

class PaymentMethod(models.TextChoices):
    RAZORPAY = "RAZORPAY", "Razorpay Standard"
    UPI = "UPI", "UPI"
    CARD = "CARD", "Credit/Debit Card"
    NETBANKING = "NETBANKING", "Net Banking"
    WALLET = "WALLET", "Wallet"
    COD = "COD", "Cash on Delivery"

class PaymentGateway(models.TextChoices):
    RAZORPAY = "RAZORPAY", "Razorpay"
    MANUAL = "MANUAL", "Manual / Offline"
```

### 4.2 `Payment` Model
- **`id`:** `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`
- **`payment_number`:** `CharField(max_length=32, unique=True, db_index=True)` (e.g. `PAY-YYYYMMDD-XXXXX`)
- **`order`:** `ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="payments")`
- **`user`:** `ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments")`
- **`status`:** `CharField(max_length=30, choices=PaymentStatus.choices, default=PaymentStatus.PENDING, db_index=True)`
- **`gateway`:** `CharField(max_length=30, choices=PaymentGateway.choices, default=PaymentGateway.RAZORPAY)`
- **`payment_method`:** `CharField(max_length=30, choices=PaymentMethod.choices, blank=True, default="")`
- **`gateway_order_id`:** `CharField(max_length=100, blank=True, default="", db_index=True)` (Razorpay order ID e.g. `order_M7...`)
- **`gateway_payment_id`:** `CharField(max_length=100, blank=True, default="", db_index=True)` (Razorpay payment ID e.g. `pay_N8...`)
- **`gateway_signature`:** `CharField(max_length=255, blank=True, default="")`
- **`amount`:** `DecimalField(max_digits=12, decimal_places=2)` (Matches `order.grand_total`)
- **`currency`:** `CharField(max_length=3, default="INR")`
- **`gateway_response`:** `JSONField(default=dict, blank=True)`
- **`failure_reason`:** `TextField(blank=True, default="")`
- **`initiated_at`:** `DateTimeField(auto_now_add=True)`
- **`authorized_at`:** `DateTimeField(null=True, blank=True)`
- **`captured_at`:** `DateTimeField(null=True, blank=True)`
- **`failed_at`:** `DateTimeField(null=True, blank=True)`
- **`refunded_at`:** `DateTimeField(null=True, blank=True)`
- **`idempotency_key`:** `CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)`
- **Constraints & Indexes:**
  - `CheckConstraint(check=Q(amount > 0), name="payment_amount_positive")`
  - Index on `["order", "-created_at"]`
  - Index on `["status", "-created_at"]`

### 4.3 `PaymentAttempt` Model
- **`id`:** `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`
- **`payment`:** `ForeignKey(Payment, on_delete=models.CASCADE, related_name="attempts")`
- **`attempt_number`:** `PositiveIntegerField(default=1)`
- **`gateway_payment_id`:** `CharField(max_length=100, blank=True, default="")`
- **`status`:** `CharField(max_length=30, choices=PaymentStatus.choices)`
- **`error_code`:** `CharField(max_length=100, blank=True, default="")`
- **`error_description`:** `TextField(blank=True, default="")`
- **`raw_response`:** `JSONField(default=dict, blank=True)`

### 4.4 `PaymentWebhookEvent` Model
- **`id`:** `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`
- **`provider`:** `CharField(max_length=50, default="RAZORPAY", db_index=True)`
- **`event_id`:** `CharField(max_length=128, unique=True, db_index=True)` (Razorpay `x-razorpay-event-id` or hashed payload)
- **`event_type`:** `CharField(max_length=100, db_index=True)` (e.g. `payment.captured`, `payment.failed`, `order.paid`)
- **`payment`:** `ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name="webhook_events")`
- **`payload`:** `JSONField(default=dict)`
- **`signature_verified`:** `BooleanField(default=False)`
- **`processed`:** `BooleanField(default=False, db_index=True)`
- **`processed_at`:** `DateTimeField(null=True, blank=True)`
- **`error_message`:** `TextField(blank=True, default="")`

---

## 5. Gateway Abstraction Layer

### 5.1 `PaymentGatewayInterface` (`apps/payments/gateways/base.py`)
```python
class PaymentGatewayInterface(ABC):
    @abstractmethod
    def create_order(self, amount: Decimal, currency: str, receipt: str, notes: dict = None) -> dict:
        """Creates an order at the gateway provider and returns gateway order payload."""
        pass

    @abstractmethod
    def verify_payment_signature(self, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
        """Verifies HMAC-SHA256 signature returned by the client-side checkout modal."""
        pass

    @abstractmethod
    def verify_webhook_signature(self, raw_body: bytes, signature: str) -> bool:
        """Verifies cryptographic signature on incoming webhook payload."""
        pass

    @abstractmethod
    def fetch_payment(self, gateway_payment_id: str) -> dict:
        """Fetches authoritative payment details directly from gateway API."""
        pass
```

### 5.2 Environment Variables & Secrets
No hardcoded gateway secrets. Loaded via `os.getenv` with sensible test fallbacks:
- `RAZORPAY_KEY_ID`: `os.getenv("RAZORPAY_KEY_ID", "rzp_test_placeholder")`
- `RAZORPAY_KEY_SECRET`: `os.getenv("RAZORPAY_KEY_SECRET", "test_secret_placeholder")`
- `RAZORPAY_WEBHOOK_SECRET`: `os.getenv("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret")`

---

## 6. End-to-End Payment Processing Flow

```
Customer              Frontend                  Django API                   Razorpay Gateway
   |                     |                          |                               |
   |--- Click "Pay" ---->|                          |                               |
   |                     |-- POST .../initiate/ --->|                               |
   |                     |                          |-- Check order status          |
   |                     |                          |   (must be PENDING_PAYMENT)   |
   |                     |                          |-- Check reservation TTL       |
   |                     |                          |-- create_order() ------------>|
   |                     |                          |<-- return gateway order ID ---|
   |                     |                          |-- Create Payment (PENDING)    |
   |                     |<- 201 Created (keys) ----|                               |
   |                     |                          |                               |
   |<- Open Razorpay ----|                          |                               |
   |   Checkout Modal    |                          |                               |
   |                     |                          |                               |
   |--- Pay via UPI/Card-|--------------------------------------------------------->|
   |<-- Payment Success -|----------------------------------------------------------|
   |                     |                                                          |
   |                     |-- POST .../verify/ ----->|                               |
   |                     |   (order_id, pay_id,     |                               |
   |                     |    signature)            |-- Verify HMAC-SHA256          |
   |                     |                          |-- Lock Payment & Order (DB)   |
   |                     |                          |-- Verify Amount & Currency    |
   |                     |                          |-- OrderStateMachine:          |
   |                     |                          |   * Consume reservations      |
   |                     |                          |   * Status -> CONFIRMED       |
   |                     |                          |   * paid_at = now             |
   |                     |                          |   * StatusHistory logged      |
   |                     |                          |-- Payment -> CAPTURED         |
   |                     |<- 200 OK (Confirmed) ----|                               |
   |                     |                          |                               |
   |                     |                          |<- POST .../webhooks/razorpay/-|
   |                     |                          |   (Identical verification;    |
   |                     |                          |    Idempotent no-op if already|
   |                     |                          |    captured!)                 |
   |                     |                          |-- 200 OK -------------------->|
```

---

## 7. REST API Endpoints Specification

### 7.1 Customer Endpoints (`/api/v1/payments/`)
1. `POST /api/v1/payments/orders/<order_id>/initiate/`:
   - Auth: Required (`IsAuthenticated`)
   - Ownership: Validates `order.user == request.user`
   - Validation: `order.order_status == OrderStatus.PENDING_PAYMENT`, reservations have not expired
   - Response: `201 Created` with `payment` details and gateway options (Key ID, amount, currency, `gateway_order_id`).
2. `POST /api/v1/payments/orders/<order_id>/verify/`:
   - Auth: Required (`IsAuthenticated`)
   - Payload: `{"razorpay_order_id": "...", "razorpay_payment_id": "...", "razorpay_signature": "..."}`
   - Action: Validates signature, locks order/payment, transitions order to `CONFIRMED`, consumes reservations, updates payment to `CAPTURED`.
   - Response: `200 OK` with captured payment and confirmed order.
3. `GET /api/v1/payments/orders/<order_id>/`:
   - Auth: Required (`IsAuthenticated`)
   - Ownership: Validates `order.user == request.user`
   - Response: `200 OK` with payment summary and attempt history.

### 7.2 Webhook Ingress (`/api/v1/payments/webhooks/<provider>/`)
- `POST /api/v1/payments/webhooks/razorpay/`:
  - Auth: None (CSRF exempt, signature-validated via `X-Razorpay-Signature` header).
  - Deduplication: Ingests `event_id`. If already processed, returns `200 OK` immediately.
  - Event `payment.captured` or `order.paid`: Executes idempotent capture & order confirmation.
  - Event `payment.failed`: Records failed `PaymentAttempt`, marks payment `FAILED` (leaving order reservations active for retries within TTL).

### 7.3 Staff Endpoints (`/api/v1/staff/payments/`)
1. `GET /api/v1/staff/payments/`:
   - Auth: Required (`IsAuthenticated`, `IsStaffOrManager`)
   - Filtering: `?status=`, `?gateway=`, `?order_id=`, `?search=`
   - Response: Paginated list of all customer payments.
2. `GET /api/v1/staff/payments/<payment_id>/`:
   - Auth: Required (`IsAuthenticated`, `IsStaffOrManager`)
   - Response: Detailed audit view with raw gateway response, attempt logs, and webhook history.

---

## 8. Security & Idempotency Controls

1. **No Client-Controlled Financial Data:** Amount, currency, and line items are read strictly from the server-side `Order` record, never accepted from request body.
2. **Cryptographic Validation:** Signature verification uses `hmac.compare_digest` to prevent timing attacks.
3. **Database-Level Concurrency:** `select_for_update()` on both `Order` and `Payment` prevents race conditions between customer frontend callbacks and asynchronous gateway webhooks.
4. **IDOR Defense:** All customer endpoints filter by `request.user`. Attempting to access or pay another customer's order returns HTTP 404 or 409.
5. **No Double-Consumption:** `InventoryService.consume_reservation()` is called only during transition to `CONFIRMED`. If the order is already `CONFIRMED`, subsequent calls return immediately.

---

## 9. Testing Strategy (Target: +25 Tests, Reaching 185+ Total)

1. `test_models.py` (5 tests):
   - Model creation, UUID primary keys, check constraints (`amount > 0`), foreign keys, status choices.
2. `test_gateways.py` (5 tests):
   - Gateway interface, valid HMAC signature, invalid HMAC signature, webhook signature validation, tampered signature detection.
3. `test_payment_service.py` (8 tests):
   - Successful payment initiation, signature verification & capture, reservation consumption, order confirmation & `paid_at`, expired reservation rejection, cancelled order rejection, payment attempt recording.
4. `test_webhooks.py` (6 tests):
   - Valid `payment.captured` webhook, duplicate webhook idempotency (processed once), invalid signature rejection, `payment.failed` records attempt, unknown event handled gracefully.
5. `test_payment_api.py` (6 tests):
   - Customer initiate API, verify API, order detail API, unauthenticated access blocked (401), IDOR blocked (404/409), amount mismatch blocked.
6. `test_staff_payment_api.py` (5 tests):
   - Regular customer forbidden (403), staff allowed (200), payment list filters, search, payment detail view.

---

## 10. Execution Plan & Stopping Gates

1. Scaffolding `apps/payments/` and register in `LOCAL_APPS` & `config/urls.py`.
2. Implement Models (`Payment`, `PaymentAttempt`, `PaymentWebhookEvent`) & migration `0001_initial.py`.
3. Implement Gateway abstraction (`PaymentGatewayInterface`, `RazorpayGateway`).
4. Implement `PaymentService` & `WebhookService`.
5. Implement Serializers, Customer Views, Webhook Views, and Staff Views.
6. Write test suites (`test_models.py`, `test_gateways.py`, `test_payment_service.py`, `test_webhooks.py`, `test_api.py`, `test_staff_api.py`).
7. Run verification quality gates:
   ```bash
   python3 manage.py check
   python3 manage.py makemigrations --check --dry-run
   python3 manage.py test apps.payments
   python3 manage.py test
   black --check .
   ruff check .
   ```
8. Generate `PHASE_3_5_PAYMENTS_COMPLETION_REPORT.md`.
