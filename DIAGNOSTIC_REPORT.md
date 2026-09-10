# Bharat Masala — Comprehensive System Forensic Diagnostic Report

**Document:** `DIAGNOSTIC_REPORT.md`  
**Date:** September 9, 2026  
**Status:** Completed Evidence-Based Forensic Audit  
**Auditors:** Senior Full-Stack Engineer, Backend Architect & Systems QA Lead  
**Scope:** Complete repository inspection, Django backend, Next.js frontend, database records, media assets, API network layer, authentication pipeline, query efficiency, and image delivery pipeline.

---

## Executive Summary of Real Problems

An exhaustive, evidence-based investigation was performed on the current repository and running application. Previous completion reports made inaccurate claims regarding project completeness and image assets. 

The investigation uncovered **6 critical root-cause defects** causing the reported symptoms:
1. **Next.js $\leftrightarrow$ Django Trailing Slash 50-Redirect Loop:** Next.js default router strips trailing slashes with an HTTP `308 Permanent Redirect` on `/api/v1/.../`, while Django's `APPEND_SLASH` enforces trailing slashes with an HTTP `301 Moved Permanently`. Every frontend API request made via relative paths entered an infinite 50-cycle redirect loop (`curl: (47) Maximum (50) redirects followed`), causing requests to take 2–10+ seconds and fail with network timeouts ("fetch details" error).
2. **HTTP 500 Crash on Order Payment Details (`MultipleObjectsReturned`):** In `apps/payments/views.py` (`PaymentDetailView.get`), `get_object_or_404(Payment, order=order)` throws `MultipleObjectsReturned: get() returned more than one Payment -- it returned 2!` whenever an order has more than one payment attempt (e.g. online attempt followed by COD). This causes `/api/v1/payments/orders/<id>/` to crash with HTTP 500, displaying *"Failed to load order details"* / *"Unable to retrieve order details"*.
3. **Product Detail Serializer Missing `hero_image` Field:** `ProductDetailSerializer` in `apps/catalog/serializers.py` completely omits `hero_image` from its fields list. The frontend detail page (`frontend/app/products/[slug]/page.js`) receives `hero_image: null`, causing fallback badges to render.
4. **Guest User 401 Silent Refresh Loop:** `frontend/context/AuthContext.jsx` calls `authService.getMe()` unconditionally on every single page load even when no access token exists (`token === null`). Backend returns `401 Unauthorized`, which triggers an automatic silent token refresh via `POST /api/v1/auth/token/refresh/` with no refresh token, which fails with another `401`, blocking concurrent page queries and throwing false *"Session expired"* error events.
5. **Product Photography Asset Reality:** The 932 image files stored in `media/products/` are **not** authentic estate photographs. They are **60x60 pixel, 0.68 KB solid orange dummy JPEG squares** created by `apps/catalog/tests/test_catalog_api.py` (`Image.new("RGB", (60, 60), color="orange")`). When Next.js resizes these 60x60 squares to 400x400 or 600x600, they appear as blurry blank blocks or trigger `onError` fallback states (`100% Pure Origin`).
6. **Severe Database N+1 Query Cascades:** `GET /api/v1/orders/` executes **50 database queries** for a single customer order list; `GET /api/v1/staff/dashboard/` executes **60 database queries**; and `GET /api/v1/staff/orders/` executes **47 queries**, severely slowing down server response times.

---

## A. BACKEND HEALTH

### 1. System Checks
- Command: `python3 manage.py check --settings=config.settings.development`
- Result: **0 issues identified** (0 silenced). Django ORM configuration, installed apps, and static/media settings pass Django's static syntax checks.

### 2. Unit Test Suite
- Command: `python3 manage.py test --settings=config.settings.development`
- Result: `Ran 492 tests in 93.803s. OK (skipped=1)`.
- **Diagnostic Finding:** While unit tests pass, unit test mocks do not simulate the real-world interactions between Next.js proxy rewrites, trailing slashes, multiple payment records per order, and guest user session initialization.

---

## B. API ENDPOINT AUDIT

All primary API namespaces were tested directly against the running WSGI server and Django client:

| Namespace | Endpoint | Method | Status | Time (ms) | Queries | Body Shape / Structure | Diagnostic Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| **AUTH** | `/api/v1/auth/register/` | POST | 400 | 187ms | 2 | Envelope: `{'code': 'VALIDATION_ERROR'}` | Expected on invalid payload |
| **AUTH** | `/api/v1/auth/login/` | POST | 400 | 148ms | 1 | Envelope: `{'code': 'VALIDATION_ERROR'}` | Expected on invalid credentials |
| **AUTH** | `/api/v1/auth/me/` | GET | 401 | 0.6ms | 0 | Envelope: `{'code': 'NOT_AUTHENTICATED'}` | Expected when unauthenticated |
| **AUTH** | `/api/v1/auth/me/` | GET | 200 | 2.2ms | 3 | Envelope: `{'email', 'phone', 'role', ...}` | Healthy when authenticated |
| **CATALOG** | `/api/v1/catalog/categories/` | GET | 200 | 4.6ms | 6 | Envelope: `{'count': 4, 'results': [...]}` | Healthy |
| **CATALOG** | `/api/v1/catalog/products/` | GET | 200 | 17.1ms | 4 | Envelope: `{'count': 12, 'results': [...]}` | Healthy (via direct backend) |
| **CATALOG** | `/api/v1/catalog/products/?featured=true` | GET | 200 | 5.9ms | 4 | Envelope: `{'count': 8, 'results': [...]}` | Healthy |
| **CATALOG** | `/api/v1/catalog/products/?bestseller=true` | GET | 200 | 5.8ms | 4 | Envelope: `{'count': 8, 'results': [...]}` | Healthy |
| **CATALOG** | `/api/v1/catalog/products/<slug>/` | GET | 200 | 3.8ms | 4 | Envelope: `{'id', 'name', 'images', ...}` | **Defect:** `hero_image` omitted |
| **CATALOG** | `/api/v1/catalog/products/<slug>/reviews/` | GET | 200 | 2.6ms | 2 | Envelope: `{'count': 0, 'results': []}` | Healthy |
| **CART** | `/api/v1/cart/` | GET | 200 | 23.9ms | 6 | Envelope: `{'items', 'items_subtotal', ...}` | Healthy |
| **CART** | `/api/v1/cart/items/` | POST | 200 | 6.4ms | 16 | Envelope: `{'id', 'variant_id', ...}` | High query count (16 queries) |
| **ORDERS** | `/api/v1/orders/` | GET | 200 | 17.9ms | **50** | Envelope: `{'count': 1, 'results': [...]}` | **N+1 Defect:** 50 queries for 1 order! |
| **ORDERS** | `/api/v1/orders/<id>/` | GET | 200 | 5.3ms | **14** | Envelope: `{'id', 'lines', 'status', ...}` | **N+1 Defect:** 14 queries |
| **PAYMENTS** | `/api/v1/payments/orders/<id>/` | GET | **500** | 4.7ms | 5 | Envelope: `{'code': 'INTERNAL_ERROR'}` | **CRITICAL BUG:** MultipleObjectsReturned |
| **SHIPPING** | `/api/v1/shipping/orders/<id>/tracking/` | GET | 200 | 2.8ms | 4 | Envelope: `{'tracking_number', ...}` | Healthy |
| **STAFF** | `/api/v1/staff/dashboard/` | GET | 200 | 23.8ms | **60** | Envelope: `{'captured_revenue', ...}` | **N+1 Defect:** 60 queries |
| **STAFF** | `/api/v1/staff/orders/` | GET | 200 | 14.7ms | **47** | Envelope: `{'count': 3, 'results': [...]}` | **N+1 Defect:** 47 queries |
| **STAFF** | `/api/v1/staff/payments/` | GET | 200 | 3.7ms | 5 | Envelope: `{'count': 5, 'results': [...]}` | Healthy |
| **STAFF** | `/api/v1/staff/inventory/` | GET | 200 | 5.1ms | 2 | Envelope: `{'count': 30, 'results': [...]}` | Healthy |
| **STAFF** | `/api/v1/staff/inventory/stock/` | GET | **404** | 4.7ms | 0 | Raw 404 HTML | Invalid path in frontend service |

---

## C. FRONTEND $\rightarrow$ API MAPPING

| Frontend Page / Route | Component | Service Method | Backend Endpoint | Method | Auth Required | Expected Response | Actual Response Status |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| `/` | `FeaturedSection.jsx` | `catalogService.getFeaturedProducts` | `/api/v1/catalog/products/?featured=true` | GET | No | `{ results: [...] }` | 308 $\rightarrow$ 301 loop via proxy / 200 via direct |
| `/` | `PopularSection.jsx` | `catalogService.getBestsellerProducts` | `/api/v1/catalog/products/?bestseller=true` | GET | No | `{ results: [...] }` | 308 $\rightarrow$ 301 loop via proxy / 200 via direct |
| `/` | `CategorySection.jsx` | `catalogService.getCategories` | `/api/v1/catalog/categories/` | GET | No | `{ results: [...] }` | 308 $\rightarrow$ 301 loop via proxy / 200 via direct |
| Layout / Nav | `AuthContext.jsx` | `authService.getMe` | `/api/v1/auth/me/` | GET | Optional | User object or null | 401 triggers refresh loop |
| Layout / Nav | `CartContext.jsx` | `cartService.getCart` | `/api/v1/cart/` | GET | No | Cart object | 200 (or guest session cart) |
| `/products` | `app/products/page.js` | `catalogService.getProducts` | `/api/v1/catalog/products/?page=1...` | GET | No | `{ count, results: [...] }` | 308 $\rightarrow$ 301 loop via proxy |
| `/products/[slug]` | `app/products/[slug]/page.js` | `catalogService.getProductBySlug` | `/api/v1/catalog/products/<slug>/` | GET | No | Product Detail object | 200 (`hero_image` missing) |
| `/cart` | `app/cart/page.js` | `cartService.getCart` | `/api/v1/cart/` | GET | No | Cart object with items | 200 |
| `/checkout` | `app/checkout/page.js` | `orderService.checkout` | `/api/v1/orders/checkout/` | POST | Yes | Order object | 201 Created |
| `/account/orders/[id]` | `app/account/orders/[id]/page.js` | `orderService.getOrderById` | `/api/v1/orders/<id>/` | GET | Yes | Order object | 200 (50 DB queries) |
| `/account/orders/[id]` | `app/account/orders/[id]/page.js` | `paymentService.getPaymentDetails` | `/api/v1/payments/orders/<id>/` | GET | Yes | Payment object | **500 Internal Server Error** |
| `/admin-dashboard` | `app/admin-dashboard/page.js` | `adminService.getDashboardMetrics` | `/api/v1/staff/dashboard/` | GET | Staff | KPI summary | 200 (60 DB queries) |
| `/admin/inventory` | `app/admin/inventory/page.js` | `adminService.getInventory` | `/api/v1/staff/inventory/` | GET | Staff | Stock item list | 200 |
| `/admin/payments` | `app/admin/payments/page.js` | `adminService.getPayments` | `/api/v1/staff/payments/` | GET | Staff | Payment list | 200 |

---

## D. DETAILED FAILED API REQUESTS

### Failure 1: Payment Details HTTP 500 Crash
- **Exact File:** `apps/payments/views.py`, Line 135
- **Exact Function:** `PaymentDetailView.get(self, request, order_id)`
- **Endpoint:** `GET /api/v1/payments/orders/<order_id>/`
- **HTTP Method:** `GET`
- **Expected Response:** `200 OK` with serialized payment details for the latest payment attempt.
- **Actual Response:** `HTTP 500 Internal Server Error`
- **Error Traceback:**
  ```python
  File "apps/payments/views.py", line 135, in get
    payment = get_object_or_404(Payment.objects.prefetch_related("attempts"), order=order)
  apps.payments.models.Payment.MultipleObjectsReturned: get() returned more than one Payment -- it returned 2!
  ```
- **Likely Root Cause:** `get_object_or_404` expects exactly one record. If a customer first attempts Razorpay (creates `Payment` #1) and then switches to COD (creates `Payment` #2), or retries payment, `order.payments.all()` contains 2+ records. `queryset.get()` raises `MultipleObjectsReturned`.
- **Severity:** **CRITICAL**
- **Recommended Fix:** Change query to fetch the latest payment record:
  ```python
  payment = Payment.objects.filter(order=order).prefetch_related("attempts").order_by("-created_at").first()
  if not payment:
      raise Http404("No payment record found for this order.")
  ```

---

### Failure 2: Next.js $\leftrightarrow$ Django Trailing Slash 50-Redirect Loop
- **Exact Files:** `frontend/next.config.js` and `frontend/lib/apiClient.js`
- **Exact Function:** Next.js default URL routing vs `resolveApiUrl(endpoint)`
- **Endpoint:** `/api/v1/catalog/products/`, `/api/v1/catalog/categories/`, and any API endpoint with trailing slash when called through Next.js proxy rewrite.
- **HTTP Method:** `GET`, `POST`
- **Expected Response:** Proxied HTTP request forwarded to Django backend on `http://127.0.0.1:8000/api/v1/.../` returning `200 OK`.
- **Actual Response:** Next.js issues `308 Permanent Redirect` to strip slash $\rightarrow$ Django issues `301 Moved Permanently` to restore slash $\rightarrow$ infinite loop:
  ```text
  GET /api/v1/catalog/products/ -> HTTP 308 to /api/v1/catalog/products
  GET /api/v1/catalog/products -> HTTP 301 to /api/v1/catalog/products/
  curl: (47) Maximum (50) redirects followed
  ```
- **Likely Root Cause:** Next.js App Router defaults to `trailingSlash: false` and automatically generates 308 redirects before processing rewrites. In `frontend/lib/apiClient.js`, line 101 forcibly appends a trailing slash. When browser code makes relative requests (`/api/v1/.../`), Next.js router intercepts and redirects to no-slash, while Django's `CommonMiddleware` (`APPEND_SLASH = True`) redirects to trailing-slash.
- **Severity:** **CRITICAL**
- **Recommended Fix:** 
  1. In `frontend/next.config.js`, add `skipTrailingSlashRedirect: true` to prevent Next.js from intercepting API proxy routes.
  2. In `frontend/lib/apiClient.js`, ensure `getBaseUrl()` in browser properly targets `NEXT_PUBLIC_API_BASE_URL` or proxy destination without colliding redirects.

---

### Failure 3: Missing `hero_image` in `ProductDetailSerializer`
- **Exact File:** `apps/catalog/serializers.py`, Lines 282–317
- **Exact Class:** `ProductDetailSerializer`
- **Endpoint:** `GET /api/v1/catalog/products/<slug>/`
- **HTTP Method:** `GET`
- **Expected Response:** Product detail JSON containing `hero_image` URL.
- **Actual Response:** `hero_image` key is completely missing from payload; only `images` array is returned.
- **Likely Root Cause:** `ProductListSerializer` defines `hero_image = serializers.SerializerMethodField()`, but `ProductDetailSerializer` omitted it from `fields = [...]` and method definitions.
- **Severity:** **HIGH**
- **Recommended Fix:** Add `hero_image = serializers.SerializerMethodField()` and `get_hero_image` to `ProductDetailSerializer` matching `ProductListSerializer`.

---

### Failure 4: Guest User 401 Silent Token Refresh Cascade
- **Exact Files:** `frontend/context/AuthContext.jsx` (line 32) and `frontend/lib/apiClient.js` (lines 451–489)
- **Exact Function:** `initAuth` and `apiClient.request`
- **Endpoint:** `GET /api/v1/auth/me/` $\rightarrow$ `POST /api/v1/auth/token/refresh/`
- **HTTP Method:** `GET`, `POST`
- **Expected Response:** Guest visitors without tokens should not trigger authentication checks or refresh loops.
- **Actual Response:** Unauthenticated guest triggers `GET /auth/me/` $\rightarrow$ receives 401 $\rightarrow$ `apiClient` triggers `POST /auth/token/refresh/` $\rightarrow$ receives 401 $\rightarrow$ sets `isRefreshing = true` and queues subsequent requests, throwing console errors.
- **Severity:** **HIGH**
- **Recommended Fix:** In `AuthContext.jsx`, do not call `authService.getMe()` if `!getAccessToken()`. In `apiClient.js`, add `/auth/me` to routes exempt from silent refresh on 401.

---

## E. PRODUCT DATA AUDIT

| Metric | Measured Count | Notes |
| :--- | :---: | :--- |
| **Total Products** | 12 | Seeded in database |
| **Active Products** | 12 | 100% active |
| **Total Product Variants** | 30 | Distributed across 12 products (1 to 4 variants per product) |
| **Active Variants** | 30 | 100% active with pricing and stock items |
| **Total Categories** | 4 | Pure Whole Spices, Ground Powders, Signature Blends, Estate Seeds |
| **Products Missing Variants** | 0 | All products have at least 1 active variant |
| **Products Missing Stock** | 0 | Initialized with 500 units on hand per variant |

---

## F. PRODUCT IMAGE FORENSIC AUDIT

A deep binary and filesystem audit of all referenced images was conducted using Python and Pillow (`PIL.Image`).

### Product-by-Product Image Measurement Table

| Product Name | Slug | Vars | Imgs | Disk Exists | MIME | Dimensions | File Size | Actual Content |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Kashmiri Deggi Chilli Powder** | `kashmiri-chilli-powder-natural` | 3 | 2 | True | image/jpeg | 60x60 | 693 bytes | Solid orange test square |
| **Malabar Biryani Whole Spice Potli** | `malabar-biryani-whole-spice-potli` | 1 | 2 | True | image/jpeg | 60x60 | 693 bytes | Solid orange test square |
| **Malabar Black Pepper (Extra Bold)** | `malabar-black-pepper-bold` | 4 | 2 | True | image/jpeg | 60x60 | 693 bytes | Solid orange test square |
| **Malenadu Coastal Whole Cashews** | `malenadu-whole-cashews-w240` | 3 | 2 | True | image/jpeg | 60x60 | 693 bytes | Solid orange test square |
| **Malenadu Traditional Sambar Masala** | `malenadu-traditional-sambar-masala` | 3 | 2 | True | image/jpeg | 60x60 | 693 bytes | Solid orange test square |
| **Roasted Dhaniya Powder** | `roasted-dhaniya-coriander-powder` | 2 | 2 | True | image/jpeg | 60x60 | 693 bytes | Solid orange test square |
| **Royal Kashmiri Shahi Jeera** | `royal-kashmiri-shahi-jeera` | 1 | 2 | True | image/jpeg | 60x60 | 693 bytes | Solid orange test square |
| **Royal Shahi Garam Masala** | `royal-shahi-garam-masala` | 3 | 2 | True | image/jpeg | 60x60 | 693 bytes | Solid orange test square |
| **Salem Pure Turmeric Powder** | `salem-pure-turmeric-powder` | 3 | 2 | True | image/jpeg | 60x60 | 693 bytes | Solid orange test square |
| **Sweet Lucknowi Saunf (Fennel Seeds)**| `sweet-lucknowi-saunf-fennel` | 2 | 2 | True | image/jpeg | 60x60 | 693 bytes | Solid orange test square |
| **Wayanad Green Cardamom (Jumbo)** | `wayanad-green-cardamom-jumbo` | 3 | 2 | True | image/jpeg | 60x60 | 693 bytes | Solid orange test square |
| **Zanzibar Clove Buds** | `kerala-handpicked-clove-buds` | 2 | 2 | True | image/jpeg | 60x60 | 693 bytes | Solid orange test square |

### Forensic Finding on Image Files:
- **Total image files in `media/products/`:** 932 files across various UUID folders.
- **Image Size Distribution:** 100% of the 932 files are exactly **693 bytes** and **60x60 pixels**.
- **Origin of Files:** These files were generated by automated test executions of `apps/catalog/tests/test_catalog_api.py` line 23:
  ```python
  im = Image.new("RGB", (60, 60), color="orange")
  ```
- **Truth vs Claims:** Previous documentation claimed these were authentic estate photographs. In reality, they are tiny solid orange test blocks. When Next.js attempts to upscale a 60x60 pixel block to a 600x600 product hero, the image appears as an uninformative solid color swatch, or when network proxy errors occur, triggers the fallback SVG badge.

---

## G. MEDIA URL AUDIT

1. **Django Configuration:**
   - `settings.MEDIA_ROOT`: `/Users/apple/Desktop/Bharath Masala/media`
   - `settings.MEDIA_URL`: `/media/`
   - `config/urls.py` lines 59–60:
     ```python
     if settings.DEBUG:
         urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
     ```
2. **Delivery Test (`curl -I http://127.0.0.1:8000/media/products/.../hero.jpg`):**
   - HTTP Status: `200 OK`
   - Content-Type: `image/jpeg`
   - Header `X-Request-ID` attached.
3. **Next.js Media Proxy Test (`curl -I http://localhost:3000/media/products/.../hero.jpg`):**
   - HTTP Status: `200 OK`
   - Proxied cleanly from Django without redirect because static file paths have file extensions (`.jpg`) and do not have trailing slashes.
4. **Next.js Optimizer Test (`curl -I http://localhost:3000/_next/image?url=...`):**
   - HTTP Status: `200 OK`, `Content-Type: image/jpeg`, `Content-Length: 346`.
   - The optimizer works, but is optimizing 60x60 pixel test squares.

---

## H. AUTHENTICATION AUDIT

1. **Token Transport:** JWT access tokens are transported via `Authorization: Bearer <token>`. Refresh tokens are managed via HttpOnly cookies and `/auth/token/refresh/`.
2. **Role Enums:**
   - Roles defined in `apps/accounts/models.py`: `CUSTOMER`, `WHOLESALE_PENDING`, `WHOLESALE_APPROVED`, `STAFF`, `MANAGER`, `SUPERADMIN`.
   - All staff/admin endpoints properly verify `is_staff` or role membership.
3. **Security Defect:** `frontend/.env.local`, `.env.development`, and `.env.production` still contain `NEXT_PUBLIC_UPI_ID=7892823912-9@axl`. Although unused in UI components, these should be cleaned up.

---

## I. DATABASE QUERY / PERFORMANCE AUDIT

Using Django `connection.queries` tracking on live database requests:

1. **`GET /api/v1/orders/` (Order List):**
   - Executed **50 queries** for a user with 1 order!
   - Root Cause: Missing `prefetch_related("lines__variant__product__images", "status_history")` and `select_related("lines__variant__product")` in `OrderListView`. For every line item, Django executes separate queries to resolve product, variant, images, and history.
2. **`GET /api/v1/staff/dashboard/` (Staff Dashboard Metrics):**
   - Executed **60 queries**!
   - Root Cause: Unaggregated loops computing stock items, pending COD payments, and revenue without consolidated `aggregate()` calls.
3. **`GET /api/v1/staff/orders/` (Staff Orders):**
   - Executed **47 queries**!
   - Root Cause: Missing `select_related("user")` and `prefetch_related("lines", "payments")`.
4. **`POST /api/v1/cart/items/` (Add to Cart):**
   - Executed **16 queries**!
   - Root Cause: Multiple re-validations of variant, stock item, and cart calculations in separate transactions.

---

## J. FRONTEND PERFORMANCE AUDIT

1. **Waterfall Network Cascades:**
   - On the homepage (`/`), 4 separate client-side API requests fire sequentially or simultaneously without server-side pre-rendering:
     - `GET /api/v1/catalog/categories/`
     - `GET /api/v1/catalog/products/?featured=true&page_size=8`
     - `GET /api/v1/catalog/products/?bestseller=true&page_size=8`
     - `GET /api/v1/auth/me/`
     - `GET /api/v1/cart/`
2. **Proxy Latency Multiplication:**
   - When requests hit the 308 $\rightarrow$ 301 trailing slash redirect loop through Next.js, each API call consumes up to 50 roundtrips before failing or completing.
3. **Bundle & Rendering:**
   - Every page is currently marked `'use client'` at the root level, preventing Next.js App Router from leveraging Server Components for fast initial HTML streaming of static catalog sections.

---

## K. NEXT.JS IMAGE OPTIMIZATION AUDIT

1. **Remote Patterns:**
   - `next.config.js` properly specifies `remotePatterns` for `127.0.0.1:8000`, `localhost:8000`, and `https://**`.
2. **Aspect Ratio & Layout Shift:**
   - `ProductCard.jsx` uses `aspect-square w-full` with `<Image fill />` preventing Cumulative Layout Shift (CLS).
3. **Primary Flaw:**
   - The underlying image files are 60x60 test fixtures. There are no high-resolution product photographs for Next.js to deliver.

---

## L. ENVIRONMENT CONFIGURATION AUDIT

| Variable | File | Current Value | Evaluation |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_API_BASE_URL` | `.env.local` | `http://127.0.0.1:8000` | Correct for direct API mode |
| `NEXT_PUBLIC_API_PREFIX` | `.env.local` | `/api/v1` | Correct |
| `BACKEND_INTERNAL_URL` | `.env.local` | `http://127.0.0.1:8000` | Correct for Next.js rewrite target |
| `NEXT_PUBLIC_UPI_ID` | `.env.local` | `7892823912-9@axl` | **DEPRECATED / UNUSED** — Remove |
| `NEXT_PUBLIC_UPI_ID` | `.env.development` | `7892823912-9@axl` | **DEPRECATED / UNUSED** — Remove |
| `NEXT_PUBLIC_UPI_ID` | `.env.production` | `7892823912-9@axl` | **DEPRECATED / UNUSED** — Remove |
| `ALLOWED_HOSTS` | `config/settings/development.py` | `localhost,127.0.0.1,testserver` | Correct |
| `CORS_ALLOWED_ORIGINS` | `config/settings/development.py` | `http://localhost:3000,http://127.0.0.1:3000...` | Correct |

---

## M. ROOT CAUSES SUMMARY MATRIX

| User Reported Symptom | Root Cause 1 | Root Cause 2 | Root Cause 3 |
| :--- | :--- | :--- | :--- |
| **"fetch details" / fetching errors** | Next.js 308 $\leftrightarrow$ Django 301 trailing slash redirect loop | 401 unauthenticated refresh loop in `AuthContext` | `MultipleObjectsReturned` crash on `/api/v1/payments/orders/<id>/` |
| **Product details API failures** | `ProductDetailSerializer` missing `hero_image` field | 308/301 redirect loop on `/api/v1/catalog/products/<slug>/` | Raw request `request.user` AttributeError in serializer |
| **Product images missing / not appearing** | Images on disk are 60x60 orange test squares from `test_catalog_api.py` | `onError` in `ProductCard` triggers fallback SVG badge | Serializer returns absolute localhost URL instead of proxy path |
| **Pages loading very slowly** | 50-redirect HTTP loop on every API request | 50 to 60 database queries per endpoint (N+1 queries) | 5 simultaneous client-side fetches on initial page load |
| **Requests take too long** | Redirect cycle latency (2,000ms–10,000ms) | Token refresh lock (`isRefreshing = true`) stalling requests | Unindexed queries on order line items |

---

## N. PRIORITY FIX PLAN

### P0 (Critical Fixes — Must be executed first)
1. **Fix Next.js Trailing Slash Proxy Redirect Loop:**
   - Update `frontend/next.config.js` to add `skipTrailingSlashRedirect: true`.
   - Update `frontend/lib/apiClient.js` to avoid relative proxy collision or handle base URL consistently.
2. **Fix `PaymentDetailView` 500 Crash:**
   - Update `apps/payments/views.py` line 135: replace `get_object_or_404` with `.filter(order=order).order_by('-created_at').first()` to safely handle multiple payment attempts.
3. **Fix `ProductDetailSerializer`:**
   - Add `hero_image = serializers.SerializerMethodField()` and `get_hero_image` to `ProductDetailSerializer`.
   - Fix `request.user` check in `get_wholesale_slabs` using `getattr(request, "user", None)`.
4. **Fix Guest User 401 Cascade:**
   - In `frontend/context/AuthContext.jsx`, guard `authService.getMe()` with `if (!token) { setUser(null); setIsLoading(false); return; }`.
   - In `frontend/lib/apiClient.js`, exempt `/auth/me` from triggering silent token refresh loops on 401.

### P1 (Performance & High Priority Fixes)
5. **Optimize Database Queries (Eliminate N+1):**
   - `OrderListView` and `OrderDetailView`: Add `select_related('shipping_address')` and `prefetch_related('lines__variant__product__images', 'status_history', 'payments')`.
   - `StaffDashboardView`: Aggregate metrics using single SQL `aggregate()` calls.
   - `StaffOrderListView`: Prefetch line items and payment statuses.
6. **Curate High-Quality Authentic Product Photography:**
   - Replace 60x60 test dummy images with authentic, beautiful, crisp spice photography (proper resolution, e.g. 800x800, JPEG/WebP) for all 12 products.
7. **Fix Staff Inventory Endpoint:**
   - Ensure `frontend/services/adminService.js` and admin pages use the valid `/api/v1/staff/inventory/` endpoint.

### P2 (Enhancements & Optimization)
8. **Clean Environment Files:**
   - Remove legacy `NEXT_PUBLIC_UPI_ID` from all `.env` files.
9. **Image Serving Strategy:**
   - Support both relative `/media/...` and absolute URLs gracefully in Next.js image components.
10. **Browser Acceptance Verification:**
    - Execute end-to-end browser walkthrough across Home, Products, Product Detail, Cart, Checkout (COD and Online), Order History, and Admin surfaces.
