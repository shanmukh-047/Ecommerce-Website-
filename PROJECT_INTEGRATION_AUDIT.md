# Bharat Masala — Project Integration Audit Report

**Audit Date:** 2026-09-08  
**Auditor:** Senior Full-Stack Engineer & Production QA Lead  
**Scope:** Complete Architecture, Backend APIs, Frontend Routes, Services, and Integrations  
**Status:** **PHASE 0 AUDIT COMPLETE — PROCEEDING TO IMPLEMENTATION**

---

## 1. Executive Summary

This comprehensive audit evaluates the integration status between the **Bharat Masala Django REST Framework backend** (`/api/v1`) and the **Next.js 14 App Router frontend** (`frontend/`).

The codebase represents a high-quality, production-ready foundation:
- The backend enforces strict relational integrity, atomic inventory stock reservations, HMAC-SHA256 cryptographic payment verification, and GST-compliant invoicing.
- The frontend features a robust centralized API client (`lib/apiClient.js`), cohesive design tokens, responsive App Router pages, and zero mock e-commerce data in active shopping flows.
- **Key issues identified during the audit:**
  1. **Frontend Routing Gaps (404s):** Links to `/wholesale`, `/about`, `/contact`, `/shipping-policy`, `/returns`, `/terms`, `/privacy`, and `/account/addresses` currently return 404 because the corresponding route files were not created.
  2. **Payment Checkout Flow Friction:** The checkout flow creates the pending order on the backend, but the payment modal displays developer simulation buttons instead of seamlessly launching Razorpay Checkout with native UPI, Card, and Netbanking options.
  3. **Backend Gap — Cash on Delivery (COD):** The backend does not implement COD in `Order`, `CheckoutRequestSerializer`, or `CheckoutService`. All orders require upfront payment settlement.
  4. **Abort Handling & Request Cancellation:** Component remounts under React 18 Strict Mode and fast search typing trigger `AbortController` cancellation, which must be handled silently without displaying error states or retry alerts to customers.

---

## 2. Backend URLs & OpenAPI Schema Audit

### 2.1 Backend URL Architecture
The Django backend exposes 80 distinct endpoint patterns structured under `/api/v1/`:
- **Authentication & Accounts (`/api/v1/auth/`):**
  - `POST /api/v1/auth/register/` (Retail customer registration)
  - `POST /api/v1/auth/register/wholesale/` (B2B Wholesale application with GSTIN/PAN)
  - `POST /api/v1/auth/login/` (JWT Access token + HttpOnly Refresh cookie)
  - `POST /api/v1/auth/token/refresh/` (Silent cookie-based token refresh)
  - `POST /api/v1/auth/logout/` (Blacklists refresh token and clears session)
  - `GET, PATCH /api/v1/auth/me/` (Current profile retrieval & update)
  - `GET, POST /api/v1/auth/addresses/` (Address book list and creation)
  - `GET, PATCH, DELETE /api/v1/auth/addresses/<id>/` (Address CRUD)
  - `POST /api/v1/auth/addresses/<id>/set-default/` (Default address designation)
- **Catalog & Merchandising (`/api/v1/catalog/`):**
  - `GET /api/v1/catalog/categories/` (Active categories with subcategories)
  - `GET /api/v1/catalog/categories/<slug>/` (Category detail)
  - `GET /api/v1/catalog/products/` (Paginated products with filters for category, tier, form, featured, bestseller, search)
  - `GET /api/v1/catalog/products/<slug>/` (Product details, multi-tier pack variants, FSSAI legal metrology, reviews summary)
  - `GET, POST /api/v1/catalog/products/<slug>/reviews/` (Approved customer reviews and review submission)
- **Shopping Cart & Promotions (`/api/v1/cart/`):**
  - `GET /api/v1/cart/` (Authoritative cart with line items, subtotals, and stock validation warnings)
  - `DELETE /api/v1/cart/` (Clear entire cart)
  - `POST /api/v1/cart/items/` (Add product variant with stock availability check)
  - `PATCH, DELETE /api/v1/cart/items/<id>/` (Update unit count or remove item)
  - `POST /api/v1/cart/coupon/` (Apply promotional coupon code)
  - `DELETE /api/v1/cart/coupon/` & `DELETE /api/v1/cart/coupon/remove/` (Remove coupon)
- **Orders & Invoicing (`/api/v1/orders/`):**
  - `POST /api/v1/orders/checkout/` (Atomic checkout from cart, address snapshotting, inventory reservation)
  - `GET /api/v1/orders/` (Customer order history)
  - `GET /api/v1/orders/<id>/` (Full order details with line items and addresses)
  - `POST /api/v1/orders/<id>/cancel/` (Cancel order in PENDING_PAYMENT status and release stock reservations)
  - `GET /api/v1/orders/<order_id>/invoice/` & `/download/` (GST tax invoice PDF/HTML)
  - `GET, POST /api/v1/orders/<order_id>/returns/` (RMA return requests)
- **Payments (`/api/v1/payments/`):**
  - `POST /api/v1/payments/orders/<order_id>/initiate/` (Creates Razorpay order and returns gateway config)
  - `POST /api/v1/payments/orders/<order_id>/verify/` (Cryptographically verifies HMAC-SHA256 signature and captures payment)
  - `GET /api/v1/payments/orders/<order_id>/` (Payment attempt history and status)
  - `POST /api/v1/payments/webhooks/razorpay/` (Gateway webhook processing)
- **Shipping & Fulfillment (`/api/v1/shipping/`):**
  - `GET /api/v1/shipping/orders/<order_id>/tracking/` (All consignments, carriers, AWB numbers, and milestones)
  - `GET /api/v1/shipping/<shipment_number>/` (Consignment detail)
  - `GET /api/v1/shipping/track/?awb=...` (Public unauthenticated milestone tracking with PII redaction)

### 2.2 OpenAPI Schema Compliance
The backend repository contains a complete, 4,295-line OpenAPI 3.0.3 specification (`schema.yml`). All request bodies, path parameters, query filters, and response models in the frontend services match the OpenAPI contract.

---

## 3. Existing Frontend Routes & Services Audit

### 3.1 Implemented Customer Routes
| Route | Component File | API Connectivity | Status |
| :--- | :--- | :---: | :---: |
| `/` | `frontend/app/page.js` | Live (`/catalog/categories/`, `/catalog/products/`) | **WORKING** |
| `/products` | `frontend/app/products/page.js` | Live (`/catalog/products/`, `/catalog/categories/`) | **WORKING** |
| `/products/[slug]` | `frontend/app/products/[slug]/page.js` | Live (`/catalog/products/<slug>/`, `/cart/items/`) | **WORKING** |
| `/cart` | `frontend/app/cart/page.js` | Live (`/cart/`, `/cart/items/`, `/cart/coupon/`) | **WORKING** |
| `/checkout` | `frontend/app/checkout/page.js` | Live (`/auth/addresses/`, `/orders/checkout/`, `/payments/`) | **WORKING** |
| `/login` | `frontend/app/login/page.js` | Live (`/auth/login/`) | **WORKING** |
| `/register` | `frontend/app/register/page.js` | Live (`/auth/register/`) | **WORKING** |
| `/account` | `frontend/app/account/page.js` | Live (`/auth/me/`, `/auth/addresses/`) | **WORKING** |
| `/account/orders` | `frontend/app/account/orders/page.js` | Live (`/orders/`) | **WORKING** |
| `/account/orders/[id]` | `frontend/app/account/orders/[id]/page.js` | Live (`/orders/<id>/`, `/shipping/orders/<id>/tracking/`) | **WORKING** |
| `/track` | `frontend/app/track/page.js` | Live (`/shipping/track/?awb=...`) | **WORKING** |

### 3.2 Missing Routes (Causing 404 Errors)
| Linked URL | Referenced In | Cause | Action Required |
| :--- | :--- | :--- | :--- |
| `/wholesale` | Header, Footer, MobileNav, AccountMenu, HomeCTA | Missing `app/wholesale/page.js` | Create full wholesale B2B page with registration form calling `/api/v1/auth/register/wholesale/`. |
| `/about` | Header (`Our Terroir`), Navbar | Missing `app/about/page.js` | Create authentic Malenadu origin, terroir, cold-milling, and farmer partnership page. |
| `/our-story` | Prompt Brief | Alias for `/about` | Create redirect or alias route to `/about`. |
| `/contact` | Footer (`Contact Support & Farm Visits`) | Missing `app/contact/page.js` | Create customer care contact page with Shimoga estate address, phone, email, hours. |
| `/shipping-policy` | Footer (`Shipping & Transit Timelines`) | Missing `app/shipping-policy/page.js` | Create shipping policy page detailing carrier partners, SLAs, tracking, and free shipping terms. |
| `/returns` | Footer (`Returns, Replacement & Refunds`) | Missing `app/returns/page.js` | Create return & replacement policy explaining 7-day food safety rules and RMA flow. |
| `/terms` | Footer (`Terms of Service & GST Invoicing`) | Missing `app/terms/page.js` | Create legal terms page covering pricing, taxation, GST invoices, and Indian jurisdiction. |
| `/privacy` | Footer (`Privacy & Data Protection`) | Missing `app/privacy/page.js` | Create privacy policy detailing data handling, PCI-DSS compliance, and zero PII sale guarantee. |
| `/offers` | Prompt Brief | Missing `app/offers/page.js` | Create active offers and discount coupon showcase (`FIRSTSPICE`, `ESTATE499`). |
| `/gifts` | Prompt Brief | Missing `app/gifts/page.js` | Create artisanal spice gift boxes and festive hampers showcase. |
| `/stories` | Prompt Brief | Missing `app/stories/page.js` | Create spice stories, harvest journals, and culinary folklore audio snippets. |
| `/account/addresses` | `components/layout/AccountMenu.jsx` | Missing dedicated route | Create `app/account/addresses/page.js` redirecting to `/account#addresses`. |

---

## 4. Centralized API Client (`apiClient.js`) Audit

`frontend/lib/apiClient.js` serves as the centralized communication bridge between Next.js and Django REST Framework:
1. **Base URL Resolution:** Reads `NEXT_PUBLIC_API_BASE_URL` (development: `http://127.0.0.1:8000`), falling back to relative URLs for production deployments behind reverse proxies.
2. **Prefix Normalization:** Ensures all endpoints are prefixed with `/api/v1/` without duplicating slashes.
3. **Request Interceptors:** Automatically attaches `Authorization: Bearer <access_token>` from memory/localStorage and sets `Content-Type: application/json` unless handling `FormData`.
4. **Response Normalization:** Seamlessly unpacks Django REST Framework standard envelopes:
   ```json
   {
     "success": true,
     "request_id": "...",
     "message": "...",
     "data": { ... },
     "error": null
   }
   ```
5. **Silent 401 Token Refresh:** Intercepts 401 Unauthorized errors on protected routes, queues concurrent requests in a `failedQueue`, triggers `POST /api/v1/auth/token/refresh/` via HttpOnly cookies, and retries pending requests.
6. **Request Cancellation:** Supports `AbortController` cancellation signals for autocomplete searches and tab navigations.

---

## 5. Domain Flows Audit

### 5.1 Authentication Flow
- **Registration:** Retail registration (`/auth/register/`) and Wholesale application (`/auth/register/wholesale/`) are supported by backend serializers.
- **Login:** Returns JWT access token and sets secure HttpOnly cookie with refresh token.
- **Session Persistence:** Access token is held in memory with localStorage backup; refresh token enables transparent sessions across browser reloads.
- **Logout:** Purges local storage, clears in-memory state, and calls backend to invalidate the refresh token.

### 5.2 Product Catalog Flow
- **Catalog:** Eager-loads variants, inventory availability, tier, and pricing.
- **Product Details:** Serializes multi-tier pack sizes (50g, 100g, 250g, 500g, 1kg), statutory FSSAI legal metrology, harvest/grinding dates, and verified customer reviews.
- **Search:** Performs server-side substring queries with debounced input and auto-aborting stale queries.

### 5.3 Shopping Cart Flow
- **Source of Truth:** Django backend is the absolute authority for prices, discounts, and inventory validation.
- **Cart Operations:** Adding variants (`POST /cart/items/`), adjusting quantities (`PATCH /cart/items/<id>/`), item deletion (`DELETE /cart/items/<id>/`), and coupon redemption (`POST /cart/coupon/`) are fully implemented.
- **Validation Issues:** Out-of-stock and price changes return clear warning banners in the cart drawer.

### 5.4 Checkout & Orders Flow
- **Address Book:** CRUD management with validation of 6-digit Indian PIN codes, mobile numbers, and state selections.
- **Atomic Checkout:** `POST /orders/checkout/` creates order in `PENDING_PAYMENT` state, locks inventory with `StockReservation`, snapshots addresses, and empties the active cart.
- **Order History & Detail:** Displays order status steppers, itemized line items, GST breakdown, shipping addresses, and direct payment retry for unpaid orders.

### 5.5 Payment Flow
- **Initiation:** `POST /payments/orders/<id>/initiate/` creates a gateway payment record and returns `key_id`, `gateway_order_id`, and `amount`.
- **Verification:** `POST /payments/orders/<id>/verify/` validates `razorpay_signature` via HMAC-SHA256, transitions order to `CONFIRMED`, marks payment `CAPTURED`, and consumes stock reservations.
- **Critical Action Required:** Replace the developer simulation modal with a direct, seamless Razorpay Checkout integration presenting UPI, Cards, and Netbanking.

### 5.6 Shipping & Tracking Flow
- **Order Tracking:** `GET /shipping/orders/<id>/tracking/` lists carrier names, AWB numbers, and chronological milestone timelines.
- **Public Tracking:** `GET /shipping/track/?awb=...` enables unauthenticated consignment tracking with customer PII strictly masked.

---

## 6. Environment Files & Configuration Audit

- `frontend/.env.development`: Configured with `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000` and `NEXT_PUBLIC_API_PREFIX=/api/v1`.
- `frontend/.env.local`: Configured for active local development with rewrites support.
- `frontend/.env.production`: Template configured for production domain hosting with secure HTTPS endpoints.
- `frontend/.env.example`: Thoroughly documented template listing all public and internal environment variables.
- **Secret Safety:** Static code scan verified zero private keys, database credentials, or payment gateway secrets in frontend code.

---

## 7. Mock & Dead Data Audit

- **Active Customer Experience:** 100% connected to live Django APIs. Zero mock products, prices, or fake orders exist in customer paths.
- **Acceptable Static Content:** Brand history, Western Ghats terroir descriptions, quality assurance badges, and Indian states dropdown choices.
- **Dead / Unused Prototype Code:**
  - `frontend/data/menu.json` (824 lines of Chinese restaurant items: Fried Rice, Momos)
  - `frontend/data/menuHelpers.js` (helpers for `menu.json`)
  - Legacy components: `components/Menu.jsx`, `components/Reservation.jsx`, `components/SpecialDishes.jsx`, `components/Offers.jsx`, `components/Contact.jsx`, `components/Gallery.jsx`, `components/Navbar.jsx`, `components/CartDrawer.jsx` (root version).
  - *None of these files are imported in the App Router tree. They can be safely deleted or archived in Phase 21.*

---

## 8. Summary of Action Items

1. **Phase 1:** Implement missing pages to eliminate all 404s (`/wholesale`, `/about`, `/contact`, `/shipping-policy`, `/returns`, `/terms`, `/privacy`, `/offers`, `/gifts`, `/stories`, `/account/addresses`).
2. **Phase 2 & 3 & 4:** Re-architect the payment modal to directly trigger the Razorpay Checkout SDK with native UPI, Card, and Netbanking options upon clicking "Pay Now", followed by backend HMAC verification.
3. **Phase 5:** Document the Cash on Delivery (COD) backend gap clearly in `BACKEND_GAPS.md`.
4. **Phase 9:** Document spice photography assets in `IMAGE_ASSET_AUDIT.md`.
5. **Phase 14:** Handle fetch aborts silently without user alerts or retry storms.
6. **Phase 21:** Safely remove confirmed dead prototype files and document in `DEAD_CODE_AUDIT.md`.
