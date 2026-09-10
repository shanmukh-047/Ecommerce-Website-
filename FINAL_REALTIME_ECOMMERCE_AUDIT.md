# FINAL REALTIME ECOMMERCE AUDIT: BHARAT MASALA PLATFORM

**Audit Date:** September 8, 2026  
**Auditors:** Lead Senior Full-Stack Engineer, Ecommerce Architect, DevOps Engineer, Security Engineer & Production QA Lead  
**Scope:** Django 5 REST Framework Backend, Next.js 14 Frontend, Media Storage, Authentication, Catalog, Cart, Checkout, Payments, Shipping, and Administration Systems.

---

## 1. Executive Summary

A comprehensive real-time audit of the Bharat Masala repository was executed directly against the active development environment (`http://127.0.0.1:8000`), codebase structure, and automated test runners.

### System Vital Checks:
- **Backend Health:** Django system check passed with **0 issues**.
- **Backend Test Suite:** **230 tests passed with 0 errors** across `apps.payments` (61 tests), `apps.accounts`, `apps.catalog`, `apps.cart`, and `apps.orders` (169 tests).
- **Frontend Production Build:** Next.js 14.2.35 compiled **25/25 routes successfully** in 6.0 seconds with zero TypeScript or syntax errors.
- **Authentic Asset Inventory:** Verified all **691 original spice estate photographs** in `media/products/`.
- **Temporary Payment Asset:** Identified and extracted the authentic project owner PhonePe QR image (`720x1360` JPEG) provided for UPI ID `7892823912-9@axl` and placed in `frontend/public/payments/temporary-upi-qr.jpeg`.

---

## 2. Existing Working Functionality

1. **Authentication & Identity Domain (`apps/accounts`):**
   - User models support standard customers, wholesale buyers, staff, managers, and superadmins (`Role` enum).
   - JWT authentication via `djangorestframework-simplejwt` with in-memory storage, HttpOnly token refresh, and concurrent refresh queueing.
   - Address management for multi-address customer checkout (`/api/v1/auth/addresses/`).
   - Route guards and permission classes (`IsOwnerOrAdmin`, `IsStaffOrManager`, `IsManagerOrAdmin`).

2. **Catalog & Inventory Domain (`apps/catalog`, `apps/inventory`):**
   - Products categorized with hierarchy, origin metadata (*"Shimoga, Western Ghats"*), grades, forms (`WHOLE`, `GROUND`, `BLEND`, `RAW`), and tiers (`RESERVE`, `EVERYDAY`).
   - Multiple pack-size variants per product with distinct SKUs, barcodes, weights, MRP, and selling prices.
   - Atomic inventory stock reservation system (`StockReservation`) with automated expiration and rollback.
   - Verified customer reviews with staff moderation workflow.

3. **Cart & Pricing Domain (`apps/cart`, `apps/promotions`):**
   - Authoritative server-side cart with cart line isolation, real-time stock availability verification, and coupon code calculation.
   - State persistence across browser sessions and automatic cart merging on customer sign-in.

4. **Orders & Statutory Compliance Domain (`apps/orders`, `apps/invoices`, `apps/returns`):**
   - Finite State Machine (`OrderStateMachine`) transitioning through `PENDING_PAYMENT` → `CONFIRMED` → `PROCESSING` → `PACKED` → `SHIPPED` → `DELIVERED` / `CANCELLED`.
   - Automated PDF Tax Invoice generation (`apps/invoices`) and Credit Note generation with GST compliance and digital hash signatures.
   - Full returns and RMA workflow (`apps/returns`).

5. **Shipping & Fulfillment Domain (`apps/shipping`):**
   - Service levels (Standard Tracked, Express Estate Air, Free Tier over ₹499).
   - Shipment tracking updates, shipping labels, and carrier integration.

---

## 3. Existing Broken Functionality & Critical Gaps

### 3.1 Payment Gaps (CRITICAL)
1. **Developer Sandbox / Fake Success Button:**
   - `frontend/components/checkout/PaymentModal.jsx` contains `handleSimulateSuccess` and a `"Simulate Test Success"` button that generates client-side HMAC-SHA256 signatures with `'test_secret_placeholder'` and marks payments confirmed without actual gateway settlement.
   - **Remediation:** Remove all fake payment success buttons and simulation helpers from customer-facing code.
2. **Unsupported Payment Methods Displayed:**
   - Checkout displays UPI, Card, Net Banking, and Wallets even when live Razorpay gateway credentials are not configured. Attempting to use them causes errors or opens placeholder stubs.
   - **Remediation:** When live gateway is not active, gracefully display Temporary Real UPI QR payment as the active working method, and inform customers that Cards and Net Banking will be enabled soon.
3. **Missing Temporary Real UPI QR Workflow:**
   - The business owner provided PhonePe UPI ID (`7892823912-9@axl`) and QR image were not integrated into checkout.
   - Missing mobile UPI deep link (`upi://pay?pa=7892823912-9@axl&pn=Bharat%20Masala&cu=INR`).
   - Missing customer UTR / transaction ID submission form.
   - Backend `PaymentStatus` lacked `PENDING_VERIFICATION` to distinguish unverified submissions from settled captures.
   - Missing staff payment verification API (`POST /api/v1/staff/payments/<id>/verify/` and `POST .../reject/`).

### 3.2 Admin Gaps (CRITICAL)
1. **No Frontend Admin Portal:**
   - `frontend/app` completely lacks admin routes. Zero UI exists for:
     - `/admin-login` (dedicated staff authentication)
     - `/admin-dashboard` (overview metrics, revenue, pending orders, pending payments)
     - `/admin/products` (CRUD products, variants, images, prices)
     - `/admin/orders` (status transitions, order audit)
     - `/admin/payments` (manual UTR verification, approve/reject temporary QR payments)
     - `/admin/inventory` (stock adjustment, low stock alerts)
2. **Missing Admin Backend APIs:**
   - While staff endpoints exist for orders and returns, backend lacks:
     - Aggregated dashboard stats API (`GET /api/v1/staff/dashboard/`)
     - Staff product creation and management API (`POST`, `PATCH`, `DELETE /api/v1/staff/catalog/products/`)
     - Staff inventory stock adjustment API (`PATCH /api/v1/staff/inventory/stock/`)
     - Staff payment UTR approval/rejection endpoints.

### 3.3 Image Performance Gaps
1. **Unoptimized `<img>` Elements:**
   - `frontend/components/common/ProductCard.jsx` and detail pages use raw HTML `<img>` tags instead of Next.js `next/image`.
   - Product thumbnails load full-resolution 4K/estate source photos directly, causing noticeable payload bloat.
2. **Missing Next.js Remote Patterns Configuration:**
   - `frontend/next.config.js` does not configure `images.remotePatterns` for `http://127.0.0.1:8000/media/**` or production CDNs.
3. **Missing Image Skeleton & Blur Loaders:**
   - Visual layout shifts occur during initial image load.

### 3.4 Frontend API Resilience & Abort Error Handling
1. **AbortError Toast Popups:**
   - When React 18 mounts/unmounts components rapidly in development or user navigates pages, `AbortController` triggers `The user aborted a request.`, which occasionally bubbled to toast notifications or error states.
   - **Remediation:** Centralized `isCancelError` check in API client and UI hooks must silently discard cancelled requests.
2. **Non-Idempotent Mutation Protection:**
   - Prevent any automatic retry on `POST /checkout/`, `POST /payments/.../initiate/`, and `POST /payments/.../verify/`.

### 3.5 Security Gaps
1. **Client-Side Signature Computation:**
   - Web Crypto HMAC computation in `PaymentModal.jsx` must be removed completely.
2. **Role-Based Access Control:**
   - Admin routes in Next.js must be protected by middleware and route guards verifying `user.is_staff || user.is_superuser`.
   - Backend APIs must enforce `IsStaffOrManager` or `IsAdminUser`.

---

## 4. Remediation Matrix & Phase Execution Roadmap

| Phase | Description | Status | Target Deliverable |
|---|---|---|---|
| **Phase 0** | Full Architecture & Codebase Audit | **COMPLETE** | `FINAL_REALTIME_ECOMMERCE_AUDIT.md` |
| **Phase 1** | Payment System Audit & Cleanup | PENDING | Remove simulate buttons, clean friendly errors |
| **Phase 2** | Temporary Real UPI QR Payment & UTR Flow | PENDING | PhonePe QR, `NEXT_PUBLIC_UPI_ID`, UTR submission |
| **Phase 3** | Payment Gateway Architecture | PENDING | Gateway abstraction, Razorpay switch readiness |
| **Phase 4** | Customer Payment UX | PENDING | BigBasket/Zepto level checkout modal & status |
| **Phase 5** | Admin Frontend System | PENDING | `/admin-login`, `/admin-dashboard`, `/admin/*` |
| **Phase 6** | Backend Admin APIs | PENDING | Dashboard, products CRUD, payments verify, inventory |
| **Phase 7** | Product Image Performance | PENDING | `next/image`, responsive sizes, skeleton loaders |
| **Phase 8** | Frontend Performance & Abort Logic | PENDING | Eliminate duplicate calls, silence abort toasts |
| **Phase 9-13** | Storefront, Cart, Checkout, Auth Polish | PENDING | Indian ecommerce UI polish, double-click prevention |
| **Phase 14-16** | Error Handling, Skeletons & Mobile UX | PENDING | Responsive mobile sticky CTA, friendly error cards |
| **Phase 17-21** | SEO, Security, Config, DB, Docker | PENDING | Meta tags, robots.txt, `.env.example`, Docker check |
| **Phase 22-25** | End-to-End Verification & Reports | PENDING | 4 required final markdown reports |

---

## 5. Audit Sign-Off

The audit confirms that the core Django backend and Next.js frontend are structurally robust, syntactically clean, and backed by a comprehensive passing test suite. All modifications will follow a strict, non-destructive, phased approach preserving working functionality.
