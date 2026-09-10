# Bharat Masala — Backend Architecture Gaps & Limitations Report

**Audit Date:** 2026-09-08  
**Auditor:** Senior Full-Stack Engineer & Production QA Lead  
**Scope:** Backend APIs (`/api/v1`), Data Models, Serializers, and Third-Party Dependencies  
**Rule:** **DO NOT INVENT MISSING BACKEND FUNCTIONALITY. DOCUMENT AS AN EXPLICIT GAP.**

---

## 1. Identified Backend Gaps

### Gap 1: Cash on Delivery (COD) Not Implemented
- **Status:** **CONFIRMED BACKEND GAP — COD NOT IMPLEMENTED**
- **Details:**
  - In `apps/payments/models.py`, `PaymentMethod.COD = "COD"` exists as an enum choice, but no operational logic exists.
  - In `apps/orders/models.py`, `OrderStatus` has no `COD_PENDING` status.
  - In `apps/orders/serializers.py`, `CheckoutRequestSerializer` accepts only `shipping_address_id` and `customer_notes`. It does not accept `payment_method: "COD"`.
  - In `apps/orders/services/checkout_service.py`, `CheckoutService.create_order_from_cart()` always marks the order as `PENDING_PAYMENT` with active inventory reservations that require confirmation via payment capture.
  - If a COD order were created in `PENDING_PAYMENT` without a gateway capture call, stock reservations would expire after the timeout threshold and cancel the order.
- **Frontend Action:** Do NOT fake COD on the frontend. The checkout page clearly communicates that only secure digital prepaid methods (UPI, Cards, Netbanking via Razorpay) are supported in this phase.

---

### Gap 2: Razorpay Live Order Creation in Gateway Adapter
- **Status:** **REMEDIATION IMPLEMENTED**
- **Details:**
  - In `apps/payments/gateways/razorpay_gateway.py`, `create_order()` previously returned an internally generated `order_<uuid>` string without attempting an HTTP call to the Razorpay API endpoint (`https://api.razorpay.com/v1/orders`).
  - When the frontend loads Razorpay Checkout JS (`https://checkout.razorpay.com/v1/checkout.js`) with an order ID not recognized by Razorpay servers, the checkout modal produces an error: `"Order ID not found"`.
- **Remediation:** When `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` are supplied in the environment (test or live mode), the gateway adapter makes an authenticated HTTP call using Python's standard `urllib.request` to obtain an authentic Razorpay order ID. When placeholder keys are used in development, fallback simulation is maintained safely.

---

### Gap 3: Third-Party Carrier Milestone Webhooks
- **Status:** **EXTERNAL CONFIGURATION REQUIRED**
- **Details:**
  - The backend provides public and customer order tracking endpoints (`/api/v1/shipping/orders/<id>/tracking/` and `/api/v1/shipping/track/`).
  - Automated carrier milestone updates (e.g. from Delhivery, Blue Dart, or Shiprocket webhooks) require active external courier accounts with webhook endpoints configured to point to `/api/v1/shipping/webhooks/`.
  - In local development, seed shipment milestones and admin tracking updates serve as the operational mechanism.

---

### Gap 4: Asynchronous Celery Worker Infrastructure
- **Status:** **EXTERNAL CONFIGURATION REQUIRED**
- **Details:**
  - The backend includes tasks for asynchronous PDF tax invoice generation (`apps.invoices.tasks`) and transactional SMS/Email notifications (`apps.notifications.tasks`).
  - For local development with SQLite, tasks can run synchronously if configured, but production deployment requires running Redis and Celery worker daemons (`celery -A config worker`).

---

## 2. Integrity Guarantee

The Bharat Masala frontend strictly adheres to these boundaries. No missing backend capabilities are simulated with fake success screens or hardcoded flags.
