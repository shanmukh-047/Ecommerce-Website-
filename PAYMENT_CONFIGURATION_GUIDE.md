# Bharat Masala — Payment Configuration & Operations Guide

**Comprehensive Dual-Mode Payment Architecture Manual**  
**Version:** 1.0 (Production Release)  
**Applicable For:** Finance Officers, Operations Staff, DevOps Engineers

---

## 1. Architecture Overview

Bharat Masala implements an enterprise dual-mode payment architecture tailored for the Indian retail landscape:

```
                          [Customer Cart Checkout]
                                     |
                                     v
                        [Order Created: PENDING_PAYMENT]
                                     |
              +----------------------+----------------------+
              |                                             |
   [Mode 1: PhonePe UPI QR]                      [Mode 2: Razorpay Gateway]
   • Direct UPI ID: 7892823912-9@axl             • Cards, Net Banking, Wallets
   • Zero Gateway Commission (0%)                • Instant Settlement
   • Mobile Deep Link Enabled                    • Automated HMAC-SHA256
              |                                             |
   [Customer Submits 12-Digit UTR]               [Customer Enters Card/Bank]
              |                                             |
   [Status: PENDING_VERIFICATION]                           v
              |                                  [Status: CAPTURED]
   [Staff Checks Bank / PhonePe App]                        |
              |                                             v
   +----------+----------+                         [Order: CONFIRMED]
   |                     |
[Verify]              [Reject]
   |                     |
   v                     v
[Status: CAPTURED]   [Status: FAILED]
   |                     |
[Order: CONFIRMED]   [Order: PENDING_PAYMENT]
```

---

## 2. Mode 1: Temporary Real UPI QR Settlement (Zero Fees)

### 2.1 Verified Account Credentials
- **Business UPI ID**: `7892823912-9@axl`
- **Payee Display Name**: `Bharat Masala`
- **Associated Banking Handle**: Axis Bank (`@axl`) / PhonePe Business
- **Static QR Code File**: `frontend/public/payments/temporary-upi-qr.jpeg` (720x1360 RGB)

### 2.2 Mobile Deep Link Specification
On mobile devices (Android / iOS), the customer is presented with an "Open in UPI App" link that launches any installed UPI application:
```text
upi://pay?pa=7892823912-9@axl&pn=Bharat%20Masala&am=540.00&cu=INR&tn=Order%20BMP-20260908-ABCDE
```
**Parameter Breakdown:**
- `pa`: Payee Address (`7892823912-9@axl`).
- `pn`: Payee Name (`Bharat Masala`).
- `am`: Exact payable amount calculated by the backend.
- `cu`: Currency (`INR`).
- `tn`: Transaction note containing the unique order reference.

### 2.3 Customer Submission API
- **Endpoint**: `POST /api/v1/payments/orders/<order_id>/submit-utr/`
- **Permissions**: Authenticated Customer (`IsAuthenticated`, owner of the order).
- **Request Format (JSON)**:
  ```json
  {
    "utr_number": "426812345678"
  }
  ```
- **Request Format (Multipart / FormData with Screenshot)**:
  - `utr_number`: `426812345678` (12-digit string).
  - `screenshot`: Binary image file (JPEG, PNG, WebP &le; 5MB).
- **Backend Response (`200 OK`)**:
  ```json
  {
    "payment": {
      "id": "c1f7535b-1793-4a6c-9411-9a99fc621516",
      "order_number": "BMP-20260908-ABCDE",
      "amount": "540.00",
      "gateway": "PHONEPE_QR",
      "payment_method": "UPI",
      "status": "PENDING_VERIFICATION",
      "utr_number": "426812345678",
      "created_at": "2026-09-08T20:30:00Z"
    },
    "_message": "UTR submitted successfully. Payment is under verification."
  }
  ```

### 2.4 Staff Verification Workflow
1. Staff logs into the management portal at `/admin-login` and navigates to `/admin/payments`.
2. The `Pending Verification` tab lists all submitted transactions with order amount, customer details, UTR reference, and optional screenshot.
3. The staff member opens their PhonePe Business App or Axis Bank statement to verify receipt of the exact credit matching the UTR and timestamp.
4. **Approval**:
   - Staff clicks **Verify**.
   - Endpoint called: `POST /api/v1/staff/payments/<payment_id>/verify/` with optional audit note.
   - Database actions executed in an atomic transaction:
     - `Payment.status` transitions from `PENDING_VERIFICATION` to `CAPTURED`.
     - `Payment.captured_at` is set to current timestamp.
     - `PaymentAudit` log entry is recorded with actor username.
     - `Order.order_status` transitions to `CONFIRMED`.
     - Reserved stock items are finalized for warehouse milling and dispatch.
5. **Rejection**:
   - If the funds were not credited or the UTR is fraudulent, staff clicks **Reject**.
   - Endpoint called: `POST /api/v1/staff/payments/<payment_id>/reject/` with required rejection reason.
   - `Payment.status` transitions to `FAILED`.
   - Customer's order remains open for payment re-attempt or cancellation.

---

## 3. Mode 2: Razorpay Secure Online Payment

### 3.1 Overview & Capabilities
For customers desiring credit/debit card settlement, Net Banking (50+ Indian banks), or digital wallets, the platform integrates Razorpay Standard Checkout SDK.

### 3.2 Environment Variables
Set the following keys in your environment (`.env` for backend, `.env.local` for frontend):
```bash
# Backend (.env)
RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=yyyyyyyyyyyyyyyyyyyyyy
RAZORPAY_WEBHOOK_SECRET=zzzzzzzzzzzzzzzzzzzz

# Frontend (.env.local / .env.production)
NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxxxxxx
```

### 3.3 Cryptographic Verification Protocol
- **Endpoint**: `POST /api/v1/payments/orders/<order_id>/verify/`
- **Algorithm**: HMAC-SHA256.
- **Verification Formula**:
  ```python
  expected_signature = hmac.new(
      key=settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
      msg=f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8"),
      digestmod=hashlib.sha256,
  ).hexdigest()
  ```
- Verification occurs authoritatively on the backend. No frontend client-side calculation is trusted for state changes.

### 3.4 Webhook Ingestion & Anti-Replay
- **Endpoint**: `POST /api/v1/payments/webhooks/razorpay/`
- **Header**: `X-Razorpay-Signature`.
- **Deduplication**: Incoming webhook IDs are checked against the `WebhookEvent` model; duplicate event deliveries are silently acknowledged with `200 OK` without triggering double processing.

---

## 4. Future PhonePe Business API Integration (Roadmap)

When the company's corporate merchant KYC is processed, the platform can be seamlessly switched to PhonePe's automated PG API:
1. Replace `PHONEPE_QR` manual service with `PhonePeGateway` adapter in `apps/payments/gateways/`.
2. Construct PhonePe standard request payload (`/pg/v1/pay`) with SHA256 base64 header.
3. Receive PhonePe S2S webhook callbacks on `/api/v1/payments/webhooks/phonepe/` to automatically transition transactions from `PENDING_VERIFICATION` to `CAPTURED`.

---

## 5. Security & Compliance Checklist

- [x] Zero mock or simulated payment buttons visible to customers.
- [x] Razorpay Key Secret is NEVER exposed to the frontend browser context.
- [x] All staff payment verification actions require authenticated staff permissions (`IsStaffOrManager`).
- [x] UTR inputs are sanitized and validated against length bounds (6–30 characters).
- [x] Complete audit logs are maintained for every manual payment verification and rejection.
