# Bharat Masala — Comprehensive Project Analysis & Pre-Implementation Audit

**Document:** `CURRENT_PROJECT_ANALYSIS.md`  
**Date:** September 8, 2026  
**Auditors:** Lead Senior Full-Stack Engineer, Ecommerce Architect, DevOps Engineer, Security Engineer & Production QA Lead  
**Scope:** Django 5 REST Framework Backend, Next.js 14 Frontend, Media Storage, Authentication, Catalog, Cart, Checkout, Payments, Shipping, and Administration Systems.

---

## 1. Existing Architecture

### Backend (Django 5 REST Framework)
- **Framework & Runtime:** Python 3.12, Django 5.0, Django REST Framework 3.15.
- **Database:** SQLite in development (`db.sqlite3`), configured to support PostgreSQL for staging/production via `DATABASE_URL`.
- **Authentication Domain (`apps/accounts`):**
  - Custom `User` model with roles: `CUSTOMER`, `WHOLESALE_BUYER`, `STAFF`, `MANAGER`, `SUPERADMIN`.
  - SimpleJWT token authentication with rotation and token blacklisting.
  - Multi-address book management at `/api/v1/auth/addresses/`.
- **Catalog & Merchandising Domain (`apps/catalog`):**
  - Hierarchical `Category` tree with slug navigation.
  - `Product` model with Western Ghats origin provenance, terroir stamps, FSSAI legal metrology, and Sharada narrative audio links.
  - `ProductVariant` pack-size models (e.g., 100g, 250g, 500g, 1kg) with SKU, MRP, and dynamic discount percentages.
  - `ProductImage` model supporting gallery images, `is_hero` flags, and automated unique hero constraint.
- **Cart & Promotions Domain (`apps/cart`, `apps/promotions`):**
  - Server-authoritative carts supporting authenticated customers and anonymous guest sessions.
  - Live stock availability checks and coupon engine (`DiscountEngine`) supporting fixed, percentage, and free shipping codes.
- **Orders & Inventory Domain (`apps/orders`, `apps/inventory`):**
  - Atomic checkout with pessimistic locking (`select_for_update`) and address snapshotting.
  - FSM order state machine (`OrderStateMachine`): `PENDING_PAYMENT` → `CONFIRMED` → `PROCESSING` → `SHIPPED` → `DELIVERED` / `CANCELLED`.
  - Stock reservation tracking (`StockReservation`) with expiration timeouts.
- **Payments Domain (`apps/payments`):**
  - Authoritative `Payment` and `PaymentAttempt` logging.
  - Pluggable gateway abstraction (`RazorpayGateway`).
  - Webhook ingestion with HMAC-SHA256 signature verification.

### Frontend (Next.js 14.2 App Router)
- **Framework & Tooling:** Next.js 14.2.35, React 18, Tailwind CSS, Lucide React icons.
- **API Client:** Axios instance (`frontend/lib/apiClient.js`) with request interceptor token injection, response envelope unwrapping, and cancellation handling.
- **State Architecture:** React Contexts: `AuthContext`, `CartContext`, `ToastContext`.
- **Media Configuration:** `next.config.js` with remote image patterns and reverse-proxy rewrites for `/media/:path*` to `http://127.0.0.1:8000/media/:path*`.

---

## 2. Existing Payment Flow

### Current Backend State
1. **Initiation (`POST /api/v1/payments/orders/<id>/initiate/`):**
   - Validates order state (`PENDING_PAYMENT`) and active stock reservations.
   - Invokes `RazorpayGateway.create_order()` returning `gateway_order_id`, key ID, amount in subunits, and currency.
2. **Signature Verification (`POST /api/v1/payments/orders/<id>/verify/`):**
   - Receives `razorpay_order_id`, `razorpay_payment_id`, and `razorpay_signature`.
   - Computes HMAC-SHA256 digest with `RAZORPAY_KEY_SECRET` using `hmac.compare_digest`.
   - Atomically marks `Payment` as `CAPTURED` and transitions `Order` to `CONFIRMED`, consuming stock reservations.
3. **Manual UPI / PhonePe Flow (Legacy / To be Deprecated):**
   - `PaymentSubmitUTRView` (`POST /api/v1/payments/orders/<id>/submit-utr/`) accepts 12-digit UTR numbers and receipt screenshots.
   - Sets payment status to `PENDING_VERIFICATION`.
   - Staff endpoints (`POST /api/v1/staff/payments/<id>/verify/` and `reject/`) allow manual approval.

### Current Frontend Customer UI Problem
- Customer checkout currently opens `PaymentModal.jsx` which displays a static PhonePe QR image (`/payments/temporary-upi-qr.jpeg`), displays a raw personal UPI ID (`7892823912-9@axl`), and asks customers to input a 12-digit UTR and upload payment screenshots.
- This creates severe friction, exposes raw business UPI handles, looks unprofessional compared to standard Indian ecommerce platforms (Zepto, BigBasket), and fails to provide automated payment confirmation.

---

## 3. Existing Product Image Flow

### Root Cause Audit
1. **Database State:**
   - 12 active products exist in the database (`Product.objects.count() == 12`).
   - The `ProductImage` database table contains **0 rows** (`ProductImage.objects.count() == 0`).
   - When `seed_catalog.py` initialized products and pack variants, it omitted populating `ProductImage` records.
2. **Serializer Output:**
   - `ProductListSerializer.get_hero_image()` queries `obj.images.filter(is_active=True)`. Because no records exist, `hero_image` returns `None` for every single product across the catalog.
   - `ProductDetailSerializer.images` returns an empty array `[]`.
3. **Media Files on Disk:**
   - `media/products/` contains 715 subdirectories with 770 image files.
   - 8 primary products have historical UUID directories mapped in `IMAGE_ASSET_AUDIT.md`:
     - `02cc425f-d249-4706-98f7-fa88aaa625bd`: Malabar Black Pepper
     - `7fbb60eb-a975-435a-b9d1-d6b3eb01f54b`: Wayanad Green Cardamom
     - `dc27bcf7-e920-4bee-963b-e5460e6ee0e3`: Salem Golden Turmeric Powder
     - `72773c1e-3204-42f5-b6ae-0748e6072bb9`: Guntur Sannam Red Chilli Powder
     - `6653da74-78e6-42bf-8014-24921131144b`: Ceylon Cinnamon Quills / Potli
     - `44dc3620-223a-4522-9842-965e1483bf0a`: Zanzibar Clove Buds
     - `7ca685cd-25d0-44f2-92e2-9ede3fc89a8f`: Heritage Brass Masala Dabba / Garam Masala
     - `e1273a68-155a-427f-bc7b-0e69cf4a5afe`: Byadgi Wrinkled Red Chilli / Sambar Masala
   - The remaining 4 active products lack image associations.
4. **Frontend Rendering:**
   - `ProductCard.jsx` falls back to rendering a silhouette badge ("100% Pure Origin") because `hero_image` is `null`.
   - `cart/page.js` had a placeholder `<ShoppingBag />` icon div without an image tag.
   - `checkout/page.js` item list omitted image thumbnails.

---

## 4. Existing Admin Routes

The administrative suite is accessible under `/admin-*` and `/admin/*`:
- `/admin-login`: Role-guarded login restricting access to users with `is_staff=True` or `is_superuser=True`.
- `/admin-dashboard`: Real-time operational KPI tiles (Revenue, Orders Today, Low Stock SKUs, Recent Orders).
- `/admin/products`: Product listing, search, category filtering, stock & pricing overview, and add-spice modal.
- `/admin/orders`: Customer orders list, order status filter, recipient destination info, and status progression.
- `/admin/payments`: Real payment records, gateway references, and legacy UTR verification queue.
- `/admin/inventory`: Physical inventory tracking vs active customer reservations, reorder thresholds, and quick-adjust modal.

---

## 5. Existing Problems Identified

1. **Missing Product Images in Catalog APIs:** Zero `ProductImage` database rows mean all frontend catalog cards show generic fallback placeholders instead of authentic spice imagery.
2. **Missing Product Thumbnails in Cart & Checkout:** Cart and checkout line items do not receive or display product images.
3. **Manual QR / UPI Checkout Experience:** Unprofessional customer checkout forcing manual QR scans, UPI handle disclosure, UTR entry, and screenshot uploads.
4. **No Cash on Delivery (COD) Option:** Customers cannot choose COD as a payment method at checkout.
5. **Lack of COD Payment Collection Workflow in Admin:** Operations staff cannot record cash collected upon delivery with a strict confirmation modal.
6. **Raw Image Tag in Product Detail Page:** `frontend/app/products/[slug]/page.js` uses unoptimized `<img>` tags rather than `next/image`.

---

## 6. Planned Changes

### Phase 1: Fix and Display All Product Images (Priority 1)
- Create and execute a database population script (`populate_product_images.py`) that attaches active `ProductImage` records with `is_hero=True` (and secondary gallery images) to all 12 products.
- Ensure Django serves media via `MEDIA_URL` / `MEDIA_ROOT`.
- Update `CartItemSerializer` to include `product_image` and `product_slug`.
- Update `frontend/app/cart/page.js`, `frontend/app/checkout/page.js`, and `frontend/app/products/[slug]/page.js` to render authentic images using `next/image` with graceful fallbacks.
- Write automated backend tests in `apps/catalog/tests/test_product_images.py`.
- Produce `PRODUCT_IMAGE_AUDIT.md`.

### Phase 2: Remove Manual QR / UPI Customer Checkout Flow (Priority 2)
- Remove QR display, UPI ID, copy buttons, UTR input, and screenshot upload inputs from customer-facing checkout UI (`PaymentModal.jsx`, `checkout/page.js`).
- Deprecate customer manual UPI submission while preserving existing database columns and historical records.

### Phase 3: Professional Payment Gateway Integration (Razorpay) (Priority 3)
- Integrate standard Razorpay Checkout modal via client SDK.
- Connect to backend order creation (`POST /api/v1/payments/orders/<id>/initiate/`) and signature verification (`POST /api/v1/payments/orders/<id>/verify/`).
- Zero fake simulation buttons; zero collection of card PIN/OTP on merchant site.
- Support asynchronous webhook reconciliation (`POST /api/v1/payments/webhooks/razorpay/`).

### Phase 4: Cash on Delivery (COD) Implementation (Priority 4)
- Add `PaymentGateway.COD` and ensure `PaymentMethod.COD` is fully supported in serializers.
- Add backend endpoint: `POST /api/v1/payments/orders/<id>/cod/` that confirms the order and sets payment status to `PENDING`.
- Add staff endpoint: `POST /api/v1/staff/payments/<id>/mark-cod-collected/` to record cash collection.

### Phase 5: Clean Checkout UX
- Streamlined checkout flow:
  1. Delivery Address Selection & Validation.
  2. Order Summary with Product Thumbnails.
  3. Payment Selection: Pay Online (Razorpay) vs Cash on Delivery (COD).

### Phase 6: Admin Improvements
- Update `/admin/payments` to display gateway orders, payments, and COD pending collection queue.
- Add "Mark COD Collected" button with explicit confirmation modal: *"Confirm that payment has been collected for this COD order?"*.

---

## 7. Potential Breaking Changes & Safeguards

| Component | Potential Risk | Mitigation / Safeguard |
| :--- | :--- | :--- |
| **Database Schema** | Adding `PaymentGateway.COD` | Use safe Django migrations (`payments.0005_...`); do not drop any existing columns (`utr_number`, `payment_screenshot`). |
| **Historical Data** | Existing payment records with `PHONEPE_QR` or `PENDING_VERIFICATION` | Models and serializers keep historical fields accessible in staff views; only customer checkout UI deprecates the manual flow. |
| **Cart Serializer** | Adding `product_image` to `CartItemSerializer` | Additive change only; preserves all existing fields (`variant_id`, `product_name`, `unit_price`, etc.). |
| **Payment Verification** | Disabling fake test signatures in production | Strict backend HMAC verification using `RAZORPAY_KEY_SECRET`. |

---

## 8. Migration Strategy

1. **Step 1 (Catalog Images):** Populate `ProductImage` records for all 12 products. Verify API response `hero_image != null`.
2. **Step 2 (Frontend Image UI):** Enhance `ProductCard.jsx`, `ProductDetail`, `cart/page.js`, and `checkout/page.js` with `next/image`.
3. **Step 3 (Payments Migration):** Create migration for `PaymentGateway.COD` if needed. Add COD backend logic in `PaymentService`.
4. **Step 4 (Frontend Checkout UX):** Replace manual QR UI with Pay Online vs COD selector in `PaymentModal.jsx` and `checkout/page.js`.
5. **Step 5 (Admin Enhancement):** Add COD collection action in admin payments screen with confirmation dialog.
6. **Step 6 (Verification & Reports):** Run backend test suite, run Next.js build, and generate all required documentation.
