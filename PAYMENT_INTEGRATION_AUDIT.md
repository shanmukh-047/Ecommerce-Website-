# Bharat Masala — Payment Integration Audit Report

**Audit Date:** 2026-09-08  
**Auditor:** Senior Full-Stack Engineer & Production QA Lead  
**Scope:** Payment Initiation, Razorpay Checkout, HMAC Verification, Webhooks, and COD Analysis  
**Status:** **AUDITED — ENHANCEMENT REQUIRED FOR SEAMLESS CHECKOUT**

---

## Executive Answers to Critical Audit Questions

### 1. Does the backend create an order before payment?
**YES.**  
`POST /api/v1/orders/checkout/` atomically validates customer cart items, computes server-side line totals and taxes, snapshots the immutable flat shipping address, locks inventory stock through `StockReservation`, and creates the `Order` in status `PENDING_PAYMENT` with a unique order number (e.g. `BMP-20260908-XXXXX`).

### 2. Does the backend support Razorpay order creation?
**YES.**  
`POST /api/v1/payments/orders/<order_id>/initiate/` invokes `PaymentService.initiate_payment(order, user)`, which initializes the gateway adapter (`RazorpayGateway.create_order()`) and returns gateway metadata.

### 3. Does the backend return `razorpay_order_id`?
**YES.**  
The initiation endpoint returns the gateway order ID inside the response envelope:
```json
{
  "gateway": {
    "key_id": "rzp_test_placeholder",
    "gateway_order_id": "order_xxxx...",
    "amount": 49900,
    "currency": "INR",
    "name": "Bharath Masala Products",
    "description": "Payment for Order BMP-20260908-XXXXX"
  },
  "payment": {
    "id": "uuid...",
    "payment_number": "PAY-20260908-XXXXX",
    "status": "PENDING",
    "amount": "499.00"
  }
}
```

### 4. Does frontend load Razorpay Checkout?
**PARTIALLY.**  
The script `https://checkout.razorpay.com/v1/checkout.js` is dynamically injected by `frontend/components/checkout/PaymentModal.jsx`. However, in the current user flow:
- After order placement, instead of immediately or seamlessly triggering the Razorpay modal presenting customer payment options, an intermediate dialog with "Developer Sandbox Mode Active" is shown.
- The customer must manually click "Pay ₹..." or "Simulate Test Success".
- **Action Required:** When clicking "Pay Now" on checkout, the system should load the Razorpay SDK reliably and immediately open the Razorpay Checkout modal.

### 5. Is Razorpay script configured correctly?
**YES, but needs hardening.**  
The script tag loads asynchronously. It should be wrapped in a reusable promise-based loader (`loadRazorpayScript()`) to guarantee that `window.Razorpay` is fully instantiated before invoking the checkout instance.

### 6. Are UPI options available through Razorpay Checkout?
**YES.**  
Razorpay Checkout natively presents all enabled Indian UPI payment flows (Google Pay, PhonePe, Paytm, BHIM, UPI ID / VPA, and dynamic QR code generation) when initialized with a valid Razorpay Key.

### 7. Are cards enabled?
**YES.**  
Credit cards and Debit cards (Visa, MasterCard, RuPay, Diners, Amex) with 3D Secure OTP verification are standard across Razorpay Checkout.

### 8. Is netbanking enabled?
**YES.**  
Over 50 Indian commercial and retail banks (HDFC, ICICI, SBI, Axis, Kotak, etc.) are available natively within Razorpay Checkout.

### 9. Is COD supported?
**NO — BACKEND GAP: COD NOT IMPLEMENTED.**  
- `PaymentMethod.COD` exists only as an unused text choice constant in `apps/payments/models.py`.
- `apps/orders/models.py` defines no COD status (e.g. `COD_PENDING`).
- `CheckoutRequestSerializer` and `CheckoutService.create_order_from_cart()` only support atomic checkout transitioning to `PENDING_PAYMENT`.
- All orders must be cryptographically verified and captured via `PaymentService.verify_and_capture_payment()`.
- **Verdict:** Do NOT fake Cash on Delivery. This is an explicit backend gap documented in `BACKEND_GAPS.md`.

### 10. Does payment success update backend payment status?
**YES.**  
`POST /api/v1/payments/orders/<order_id>/verify/` executes `PaymentService.verify_and_capture_payment()`, which atomically:
1. Validates the HMAC-SHA256 signature.
2. Transitions `Order.order_status` from `PENDING_PAYMENT` to `CONFIRMED`.
3. Marks `Payment.status` as `CAPTURED`.
4. Sets `paid_at` timestamp.
5. Consumes the active `StockReservation` entries into permanently committed inventory deductions.

### 11. Is Razorpay signature verification implemented?
**YES.**  
`RazorpayGateway.verify_payment_signature()` computes:
$$\text{expected\_signature} = \text{HMAC-SHA256}(\text{order\_id} \mathbin{\Vert} \text{payment\_id},\, \text{key\_secret})$$
and verifies using `hmac.compare_digest()`.

### 12. Are webhooks implemented?
**YES.**  
`POST /api/v1/payments/webhooks/razorpay/` exists in `apps/payments/webhook_views.py`. `WebhookService` handles `payment.authorized`, `payment.captured`, `payment.failed`, and `refund.processed` with HMAC-SHA256 signature authentication (`X-Razorpay-Signature`).

### 13. Does the frontend incorrectly mark payment successful without backend verification?
**NO.**  
In the verified production code, `handleVerify` sends `{ razorpay_order_id, razorpay_payment_id, razorpay_signature }` to `paymentService.verifyPayment()`. The order is ONLY transitioned to confirmed after the backend returns HTTP 200 with captured status.

---

## Required Action Plan for Phase 3 & 4

1. **Seamless Razorpay Checkout Loader:** Implement a robust `loadRazorpayScript()` utility ensuring `window.Razorpay` is available.
2. **Direct Pay Now Execution:** In `frontend/app/checkout/page.js`, when customer clicks "Place Order & Pay":
   - Validate address selection.
   - Call `orderService.checkout()`.
   - Call `paymentService.initiatePayment()`.
   - Automatically open the Razorpay Checkout modal.
   - Support retry if the customer dismisses the gateway dialog.
3. **Environment Variable Configuration:** Ensure `NEXT_PUBLIC_RAZORPAY_KEY_ID` is documented in `.env.example`, `.env.development`, and `.env.production`.
4. **Backend Gateway Fallback:** In `apps/payments/gateways/razorpay_gateway.py`, ensure that when actual `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` are configured, the real Razorpay API (`https://api.razorpay.com/v1/orders`) is invoked via Python's standard `urllib.request`.
