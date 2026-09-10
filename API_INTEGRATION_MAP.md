# Bharath Masala — Frontend API Integration Map

**Document Purpose:** Definitive, field-exact mapping between frontend UI workflows and the Django REST Framework backend APIs.  
**Source of Truth:** OpenAPI 3.0.3 specification (`schema.yml`) and verified backend implementation (`BACKEND_API_INVENTORY.md`).  
**Standard Response Envelope:** All successful JSON responses are encapsulated by the backend envelope:
```json
{
  "success": true,
  "request_id": "req_...",
  "message": "Operation successful",
  "data": { ... },
  "error": null
}
```
All errors are encapsulated as:
```json
{
  "success": false,
  "request_id": "req_...",
  "message": "Error description",
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "User-facing error message",
    "details": { ... }
  }
}
```

---

## 1. Domain: Authentication & Customer Accounts

### 1.1 Retail Customer Self-Registration
- **Endpoint:** `/api/v1/auth/register/`
- **HTTP Method:** `POST`
- **Authentication Required:** No (Public endpoint; rate-limited to 5 requests/minute).
- **Request Body (JSON):**
  ```json
  {
    "email": "customer@example.com",
    "phone_number": "+919876543210",
    "password": "SecurePassword123!",
    "confirm_password": "SecurePassword123!",
    "first_name": "Aarav",
    "last_name": "Sharma"
  }
  ```
  *(Required: `email`, `phone_number` [10-digit Indian], `password` [min 8 chars], `confirm_password`. Optional: `first_name`, `last_name`)*
- **Query Parameters:** None.
- **Response Structure (HTTP 201 Created):**
  - **Cookies Set:** `refresh_token` (`HttpOnly`, `SameSite=Lax`, `Path=/api/v1/auth/`, `Max-Age=7d`)
  - **Payload (`data`):**
    ```json
    {
      "access_token": "eyJhbGciOi...",
      "token_type": "Bearer",
      "user": {
        "id": "c3a887ef-3bc2-4f11-8bf8-d3b2bf4054a1",
        "email": "customer@example.com",
        "phone_number": "+919876543210",
        "first_name": "Aarav",
        "last_name": "Sharma",
        "full_name": "Aarav Sharma",
        "role": "CUSTOMER",
        "is_wholesale_buyer": false,
        "date_joined": "2026-09-07T12:00:00Z",
        "wholesale_profile": null
      }
    }
    ```
- **Frontend Page Using API:** `/register` (or Registration Modal).
- **Error Responses:**
  - `HTTP 400 Bad Request`: Validation failure (`VALIDATION_ERROR` — duplicate email, mismatched passwords, invalid phone format).
  - `HTTP 429 Too Many Requests`: `{"error": {"code": "RATE_LIMIT_EXCEEDED"}}`.
- **Loading Behavior:** Submit button shows spinner ("Creating Account..."), inputs disabled during submission.

---

### 1.2 B2B Wholesale Customer Registration
- **Endpoint:** `/api/v1/auth/register/wholesale/`
- **HTTP Method:** `POST`
- **Authentication Required:** No (Public; rate-limited to 5 requests/minute).
- **Request Body (JSON):**
  ```json
  {
    "user": {
      "email": "merchant@malenadugrocers.com",
      "phone_number": "+919876543211",
      "password": "MerchantPass123!",
      "confirm_password": "MerchantPass123!",
      "first_name": "Ramesh",
      "last_name": "Kannan"
    },
    "company_name": "Malenadu Grocers Pvt Ltd",
    "gstin": "29ABCDE1234F1Z5",
    "pan_number": "ABCDE1234F",
    "fssai_license": "11223344556677",
    "business_type": "RETAILER"
  }
  ```
  *(Business type choices: `PROPRIETORSHIP`, `PARTNERSHIP`, `LLP`, `PRIVATE_LIMITED`, `PUBLIC_LIMITED`, `RETAILER`, `DISTRIBUTOR`, `RESTAURANT_HOTEL`, `OTHER`)*
- **Query Parameters:** None.
- **Response Structure (HTTP 201 Created):**
  - **Cookies Set:** `refresh_token` (`HttpOnly`, `Path=/api/v1/auth/`)
  - **Payload (`data`):**
    ```json
    {
      "access_token": "eyJhbGciOi...",
      "token_type": "Bearer",
      "user": {
        "id": "f8a12b3c-...",
        "email": "merchant@malenadugrocers.com",
        "role": "WHOLESALE",
        "is_wholesale_buyer": false,
        "wholesale_profile": {
          "id": "e4b2...",
          "company_name": "Malenadu Grocers Pvt Ltd",
          "masked_gstin": "29ABC******1Z5",
          "masked_pan": "ABC****F",
          "fssai_license": "11223344556677",
          "business_type": "RETAILER",
          "verification_status": "PENDING",
          "verified_at": null,
          "rejection_reason": ""
        }
      }
    }
    ```
- **Frontend Page Using API:** `/wholesale/register` (B2B Onboarding Page).
- **Error Responses:**
  - `HTTP 400 Bad Request`: Invalid GSTIN format (must be 15 chars matching Indian state prefix), invalid PAN, or existing company name.
- **Loading Behavior:** Multi-step wizard spinner; upon success, redirects to `/account` with "Pending Verification" banner.

---

### 1.3 User Login
- **Endpoint:** `/api/v1/auth/login/`
- **HTTP Method:** `POST`
- **Authentication Required:** No (Rate-limited: 5 requests/minute).
- **Request Body (JSON):**
  ```json
  {
    "email": "customer@example.com",
    "password": "SecurePassword123!"
  }
  ```
- **Query Parameters:** None.
- **Response Structure (HTTP 200 OK):**
  - **Cookies Set:** `refresh_token` (`HttpOnly`, `Path=/api/v1/auth/`, `Max-Age=7d`, `SameSite=Lax`)
  - **Cookies Cleared:** `guest_cart_token` (cleared automatically if guest cart was merged into customer cart)
  - **Payload (`data`):**
    ```json
    {
      "access_token": "eyJhbGciOi...",
      "token_type": "Bearer",
      "user": {
        "id": "c3a887ef-3bc2-4f11-8bf8-d3b2bf4054a1",
        "email": "customer@example.com",
        "phone_number": "+919876543210",
        "first_name": "Aarav",
        "last_name": "Sharma",
        "full_name": "Aarav Sharma",
        "role": "CUSTOMER",
        "is_wholesale_buyer": false,
        "wholesale_profile": null
      },
      "cart_merge_adjustments": []
    }
    ```
- **Frontend Page Using API:** `/login` (or Login Slide-over Modal).
- **Error Responses:**
  - `HTTP 400 Bad Request`: `{"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}}`.
  - `HTTP 429 Too Many Requests`: IP lock after consecutive failures.
- **Loading Behavior:** Button spinner ("Signing in..."), instant store update (`authStore.setAuth`), cart drawer re-fetch trigger.

---

### 1.4 Silent Token Refresh
- **Endpoint:** `/api/v1/auth/token/refresh/`
- **HTTP Method:** `POST`
- **Authentication Required:** No header required; browser sends `refresh_token` HttpOnly cookie.
- **Request Body:** Optional empty body `{}` (accepts cookie as primary source; body `{"refresh": "..."}` supported as fallback).
- **Query Parameters:** None.
- **Response Structure (HTTP 200 OK):**
  - **Cookies Rotated:** New `refresh_token` cookie set.
  - **Payload (`data`):**
    ```json
    {
      "access_token": "eyJhbGciOi...NEW_TOKEN...",
      "token_type": "Bearer"
    }
    ```
- **Frontend Page Using API:** Background API Interceptor (`src/api/client/interceptors.ts`).
- **Error Responses:**
  - `HTTP 401 Unauthorized`: Token expired or blacklisted $\to$ clears local session and redirects to `/login?next=...`.
- **Loading Behavior:** Silent; transparent to user. Pending requests queued until refresh completes.

---

### 1.5 User Logout
- **Endpoint:** `/api/v1/auth/logout/`
- **HTTP Method:** `POST`
- **Authentication Required:** Optional (reads `refresh_token` cookie or Bearer header).
- **Request Body:** `{}`
- **Query Parameters:** None.
- **Response Structure (HTTP 200 OK):**
  - **Cookies Cleared:** Deletes `refresh_token` cookie.
  - **Payload (`data`):** `null`
- **Frontend Page Using API:** Header Account Menu / `/account` Logout button.
- **Loading Behavior:** Instant UI teardown; redirects user to `/`.

---

### 1.6 Current User Profile (Retrieve & Update)
- **Endpoint:** `/api/v1/auth/me/`
- **HTTP Method:** `GET` (Retrieve), `PATCH` (Update)
- **Authentication Required:** Yes (`Authorization: Bearer <token>`).
- **Request Body (for PATCH):**
  ```json
  {
    "first_name": "Aarav",
    "last_name": "Sharma"
  }
  ```
- **Response Structure (HTTP 200 OK):**
  ```json
  {
    "id": "c3a887ef-3bc2-4f11-8bf8-d3b2bf4054a1",
    "email": "customer@example.com",
    "phone_number": "+919876543210",
    "first_name": "Aarav",
    "last_name": "Sharma",
    "full_name": "Aarav Sharma",
    "role": "CUSTOMER",
    "is_wholesale_buyer": false,
    "wholesale_profile": null
  }
  ```
- **Frontend Page Using API:** `/account`, Header user avatar.
- **Loading Behavior:** Skeleton placeholder in account dashboard while fetching.

---

### 1.7 Customer Address Book
- **Endpoints:**
  - `GET /api/v1/auth/addresses/` (List customer addresses)
  - `POST /api/v1/auth/addresses/` (Add new address)
  - `PATCH /api/v1/auth/addresses/{id}/` (Update address)
  - `DELETE /api/v1/auth/addresses/{id}/` (Remove address)
  - `POST /api/v1/auth/addresses/{id}/set-default/` (Set default shipping/billing)
- **Authentication Required:** Yes (`Authorization: Bearer <token>`).
- **Request Body (POST / PATCH):**
  ```json
  {
    "recipient_name": "Aarav Sharma",
    "phone_number": "+919876543210",
    "address_line_1": "Flat 402, Malenadu Heights",
    "address_line_2": "Main Road",
    "landmark": "Near Sharada Temple",
    "city": "Thirthahalli",
    "state": "KARNATAKA",
    "pincode": "577432",
    "address_type": "HOME",
    "is_default_shipping": true,
    "is_default_billing": false
  }
  ```
  *(Choices for `address_type`: `HOME`, `OFFICE`, `WAREHOUSE`, `OTHER`. `state` must match statutory Indian state choices).*
- **Request Body (`set-default`):** `{"type": "shipping"}` or `{"type": "billing"}`.
- **Frontend Pages Using API:** `/checkout` (Address selector) and `/account/addresses`.

---

## 2. Domain: Product Catalog & Reviews

### 2.1 Category Navigation Hierarchy
- **Endpoint:** `/api/v1/catalog/categories/`
- **HTTP Method:** `GET`
- **Authentication Required:** No (Public).
- **Query Parameters:** None.
- **Response Structure (HTTP 200 OK):**
  ```json
  [
    {
      "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "name": "Pure Spices",
      "slug": "pure-spices",
      "description": "Single-origin whole spices harvested from the Western Ghats.",
      "image": "http://127.0.0.1:8000/media/categories/pure-spices.jpg",
      "sort_order": 1,
      "parent": null,
      "subcategories": [
        {
          "id": "e4b2c1d0-...",
          "name": "Whole Spices",
          "slug": "whole-spices",
          "description": "Cardamom, Pepper, Clove, Cinnamon",
          "image": null,
          "sort_order": 1
        }
      ]
    }
  ]
  ```
- **Frontend Page Using API:** Header Navigation, Catalog Category Filter Pills, Footer Quick Links.
- **Loading Behavior:** Cached using SWR/TanStack Query with 1-hour stale time.

---

### 2.2 Product Catalog Listing & Faceted Filter
- **Endpoint:** `/api/v1/catalog/products/`
- **HTTP Method:** `GET`
- **Authentication Required:** Optional (Public; if authenticated as wholesale buyer, returns wholesale tier pricing).
- **Query Parameters:**
  | Parameter | Type | Description |
  | :--- | :--- | :--- |
  | `category` | string (slug) | Filter by category slug (e.g. `pure-spices`, `signature-blends`). |
  | `tier` | string | `RESERVE` (Reserve Tier) or `EVERYDAY` (Everyday Fresh). |
  | `form` | string | `WHOLE` (Whole Spice), `GROUND` (Powdered), `BLEND` (Blends), `RAW` (Raw nut). |
  | `search` | string | Search keyword matched against product name and story. |
  | `ordering` | string | `price_asc`, `price_desc`, `rating`, `newest`, `bestseller`. |
  | `page` | integer | Page number (default: 1). |
  | `page_size` | integer | Number of items per page (default: 12). |
- **Response Structure (HTTP 200 OK):**
  ```json
  {
    "count": 18,
    "page": 1,
    "total_pages": 2,
    "next": "http://127.0.0.1:8000/api/v1/catalog/products/?page=2",
    "previous": null,
    "results": [
      {
        "id": "d1c2b3a4-...",
        "name": "Thirthahalli Black Pepper",
        "slug": "thirthahalli-black-pepper",
        "category": {
          "id": "9b1d...",
          "name": "Pure Spices",
          "slug": "pure-spices"
        },
        "tier": "RESERVE",
        "form": "WHOLE",
        "short_description": "High-piperine Malenadu black pepper, hand-harvested.",
        "origin_region": "Thirthahalli, Shimoga",
        "origin_stamp": "Western Ghats Certified Terroir",
        "grade": "Bold 550GL+",
        "is_bestseller": true,
        "is_featured_from_home": true,
        "hero_image": {
          "id": "img_01",
          "image": "http://127.0.0.1:8000/media/products/pepper_hero.jpg",
          "alt_text": "Thirthahalli Black Pepper Pods"
        },
        "starting_price": "240.00",
        "starting_price_label": "From ₹240.00",
        "variant_count": 4,
        "variants": [
          {
            "id": "var_100g",
            "variant_name": "100g Aroma-Lock Pouch",
            "sku": "BMP-PEP-100G",
            "weight_in_grams": 100,
            "mrp": "270.00",
            "selling_price": "240.00",
            "savings_amount": "30.00",
            "discount_percentage": 11,
            "savings_label": "Save 11%",
            "is_most_chosen": false,
            "sort_order": 1
          },
          {
            "id": "var_250g",
            "variant_name": "250g Aroma-Lock Pouch",
            "sku": "BMP-PEP-250G",
            "weight_in_grams": 250,
            "mrp": "650.00",
            "selling_price": "560.00",
            "savings_amount": "90.00",
            "discount_percentage": 14,
            "savings_label": "Save 14%",
            "is_most_chosen": true,
            "sort_order": 2
          }
        ]
      }
    ]
  }
  ```
- **Frontend Pages Using API:** Homepage (`FeaturedSpices`), Catalog Page (`/products`), Category Landing Pages (`/products?category=...`).
- **Loading Behavior:** 4-column `ProductCardSkeleton` during pagination and filter switching. Search input debounced by 350ms.

---

### 2.3 Product Master Detail
- **Endpoint:** `/api/v1/catalog/products/{slug}/`
- **HTTP Method:** `GET`
- **Authentication Required:** Optional (Public; if wholesale user authenticated, `wholesale_slabs` array is conditionally populated).
- **Response Structure (HTTP 200 OK):**
  ```json
  {
    "id": "d1c2b3a4-...",
    "name": "Thirthahalli Black Pepper",
    "slug": "thirthahalli-black-pepper",
    "category": {
      "id": "9b1d...",
      "name": "Pure Spices",
      "slug": "pure-spices",
      "description": "...",
      "image": "..."
    },
    "tier": "RESERVE",
    "form": "WHOLE",
    "short_description": "High-piperine Malenadu black pepper, hand-harvested.",
    "detailed_description": "Grown in the high-rainfall slopes of Thirthahalli...",
    "origin_region": "Thirthahalli, Shimoga, Karnataka",
    "plantation_provenance": "Sharada Estate, Agumbe Foothills",
    "origin_stamp": "Western Ghats Certified Terroir",
    "grade": "Bold 550GL+",
    "harvest_date": "2026-02-15",
    "grinding_date": null,
    "sharada_note": "A pinch into hot rasam cures cold monsoon nights.",
    "qr_audio_url": "https://cdn.bharathmasala.com/audio/stories/pepper.mp3",
    "legal_metrology": {
      "fssai_license": "11223344556677",
      "hsn_code": "090411",
      "gst_rate": "5.00",
      "packer_name": "Bharath Masala Products",
      "packer_address": "Main Road, Thirthahalli, Shimoga District, Karnataka 577432",
      "best_before_guidance": "12 months from packing"
    },
    "is_bestseller": true,
    "images": [
      {
        "id": "img_01",
        "image": "http://127.0.0.1:8000/media/products/pepper_hero.jpg",
        "alt_text": "Pepper Main",
        "is_hero": true,
        "sort_order": 1
      }
    ],
    "variants": [
      {
        "id": "var_250g",
        "variant_name": "250g Pouch",
        "sku": "BMP-PEP-250G",
        "weight_in_grams": 250,
        "mrp": "650.00",
        "selling_price": "560.00",
        "savings_amount": "90.00",
        "discount_percentage": 14,
        "savings_label": "Save 14%",
        "is_most_chosen": true,
        "wholesale_slabs": [
          {
            "id": "slab_01",
            "min_quantity": 10,
            "wholesale_price_per_unit": "480.00"
          }
        ]
      }
    ],
    "reviews_summary": {
      "total_reviews": 24,
      "average_rating": 4.9
    },
    "recent_reviews": [ ... ]
  }
  ```
- **Frontend Page Using API:** Product Detail Page (`/products/[slug]`).
- **Loading Behavior:** Next.js App Router streaming SSR with layout skeleton.

---

### 2.4 Product Reviews (List & Submit)
- **Endpoints:**
  - `GET /api/v1/catalog/products/{slug}/reviews/` (List approved reviews)
  - `POST /api/v1/catalog/products/{slug}/reviews/` (Submit review)
- **Authentication Required:** `GET`: No; `POST`: Yes (`Authorization: Bearer <token>`).
- **Request Body (POST):**
  ```json
  {
    "rating": 5,
    "title": "Aroma fills the entire kitchen!",
    "review_body": "Genuine whole black pepper. The piperine punch is far stronger than grocery brands."
  }
  ```
- **Frontend Page Using API:** `/products/[slug]#reviews`.
- **Loading Behavior:** Submit button enters loading state; on success, notifies customer: *"Review submitted for staff verification."*

---

## 3. Domain: Shopping Cart & Promotions

### 3.1 Cart Retrieval & Guest Synchronization
- **Endpoint:** `/api/v1/cart/`
- **HTTP Method:** `GET` (Fetch active cart), `DELETE` (Clear all items)
- **Authentication Required:** No (Works seamlessly for anonymous visitors with `guest_cart_token` cookie and authenticated customers).
- **Query Parameters:** None.
- **Response Structure (HTTP 200 OK):**
  ```json
  {
    "id": "cart_uuid_1234",
    "items": [
      {
        "id": "item_uuid_5678",
        "variant_id": "var_250g",
        "product_name": "Thirthahalli Black Pepper",
        "variant_name": "250g Pouch",
        "sku": "BMP-PEP-250G",
        "weight_in_grams": 250,
        "quantity": 2,
        "mrp": "650.00",
        "unit_price": "560.00",
        "line_total": "1120.00",
        "stock_available": true
      }
    ],
    "validation_issues": [],
    "applied_coupon_code": "SPICE10",
    "items_subtotal": "1120.00",
    "discount_amount": "112.00",
    "net_subtotal": "1008.00",
    "created_at": "2026-09-07T14:30:00Z",
    "updated_at": "2026-09-07T14:35:00Z"
  }
  ```
- **Frontend Pages Using API:** `<Navbar />` (cart counter badge), `<CartDrawer />`, Full Cart Page (`/cart`), Checkout Page (`/checkout`).
- **Loading Behavior:** Optimistic quantity increment in UI with background server sync.

---

### 3.2 Cart Item Modifications
- **Add Item:** `POST /api/v1/cart/items/`
  - Body: `{"variant_id": "uuid", "quantity": 1}`
- **Update Quantity:** `PATCH /api/v1/cart/items/{id}/`
  - Body: `{"quantity": 3}`
- **Remove Item:** `DELETE /api/v1/cart/items/{id}/`
- **Response Structure:** Returns full updated `CartSerializer` object.
- **Frontend Components Using API:** Product Card "Add to Cart" button, Cart Drawer quantity steppers, Cart Page item remove button.
- **Error Responses:**
  - `HTTP 409 Conflict`: Insufficient stock available (`{"error": {"code": "INSUFFICIENT_STOCK", "message": "Only 2 units remaining."}}`).
- **Loading Behavior:** Action button shows loading spinner; drawer slides open automatically on add.

---

### 3.3 Promotional Coupon Application
- **Apply Coupon:** `POST /api/v1/cart/coupon/`
  - Request Body: `{"code": "WELCOME10"}`
- **Remove Coupon:** `DELETE /api/v1/cart/coupon/` (or `DELETE /api/v1/cart/coupon/remove/`)
- **Response Structure:** Returns updated `CartSerializer` with recalculated `applied_coupon_code`, `discount_amount`, and `net_subtotal`.
- **Frontend Components Using API:** `<CouponInput />` in Cart Drawer and Checkout Order Summary.
- **Error Responses:**
  - `HTTP 400 Bad Request`: `{"error": {"code": "INVALID_COUPON", "message": "Coupon code 'SUMMER20' has expired or minimum spend of ₹500 is not met."}}`.

---

## 4. Domain: Orders, Checkout & Invoices

### 4.1 Execute Order Checkout
- **Endpoint:** `/api/v1/orders/checkout/`
- **HTTP Method:** `POST`
- **Authentication Required:** Yes (`Authorization: Bearer <token>`).
- **Request Body (JSON):**
  ```json
  {
    "shipping_address_id": "address_uuid_9999",
    "customer_notes": "Please ring bell on delivery."
  }
  ```
- **Response Structure (HTTP 201 Created):**
  ```json
  {
    "order": {
      "id": "order_uuid_0001",
      "order_number": "BMP-20260907-9A6PP",
      "order_status": "PENDING_PAYMENT",
      "status": "PENDING_PAYMENT",
      "currency": "INR",
      "items_subtotal": "1120.00",
      "shipping_fee": "0.00",
      "tax_amount": "48.00",
      "total_discount": "112.00",
      "grand_total": "1008.00",
      "total_quantity": 2,
      "total_weight_in_grams": 500,
      "is_wholesale_order": false,
      "shipping_recipient_name": "Aarav Sharma",
      "shipping_phone_number": "+919876543210",
      "shipping_address_line_1": "Flat 402, Malenadu Heights",
      "shipping_city": "Thirthahalli",
      "shipping_state": "KARNATAKA",
      "shipping_pincode": "577432",
      "customer_notes": "Please ring bell on delivery.",
      "lines": [
        {
          "id": "line_01",
          "variant_id": "var_250g",
          "product_name": "Thirthahalli Black Pepper",
          "variant_name": "250g Pouch",
          "sku": "BMP-PEP-250G",
          "weight_in_grams": 250,
          "mrp": "650.00",
          "unit_price": "560.00",
          "quantity": 2,
          "line_subtotal": "1120.00"
        }
      ],
      "created_at": "2026-09-07T14:40:00Z"
    }
  }
  ```
- **Frontend Page Using API:** `/checkout` (Place Order button).
- **Error Responses:**
  - `HTTP 409 Conflict`: `CART_EMPTY`, `STOCK_UNAVAILABLE`, or `INVALID_ADDRESS`.
- **Loading Behavior:** Full-screen overlay spinner: *"Reserving stock and creating your order..."*. Upon return, triggers `PaymentInitiateView`.

---

### 4.2 Customer Order History & Detail
- **Endpoints:**
  - `GET /api/v1/orders/` (Paginated list of customer orders)
  - `GET /api/v1/orders/{id}/` (Detailed order snapshot with tracking and line items)
- **Authentication Required:** Yes (Owner only).
- **Response Structure (HTTP 200 OK):** `OrderSerializer` (includes `lines`, `status_history`, and timestamps `paid_at`, `shipped_at`, `delivered_at`).
- **Frontend Pages Using API:** `/account/orders` and `/account/orders/[id]`.

---

### 4.3 Customer Order Cancellation
- **Endpoint:** `/api/v1/orders/{id}/cancel/`
- **HTTP Method:** `POST`
- **Authentication Required:** Yes (Owner only; allowed only while order is in `PENDING_PAYMENT`).
- **Request Body:** `{"reason": "Customer placed order by mistake."}`
- **Response Structure (HTTP 200 OK):** Updated `OrderSerializer` with `order_status: "CANCELLED"`.
- **Frontend Component Using API:** `<CancelOrderModal />` on `/account/orders/[id]`.

---

### 4.4 Statutory GST Tax Invoice (PDF Download & HTML View)
- **Endpoints:**
  - `GET /api/v1/orders/{order_id}/invoice/download/` (Binary PDF Download)
  - `GET /api/v1/orders/{order_id}/invoice/html/` (Printable HTML Invoice)
- **Authentication Required:** Yes (Owner only).
- **Response:**
  - For `/download/`: Binary stream with header `Content-Type: application/pdf` and `Content-Disposition: attachment; filename="Invoice_BMP_2026-27_00001.pdf"`.
  - For `/html/`: Clean HTML template formatted for A4 printing with statutory GSTIN, CGST, SGST, IGST splits.
- **Frontend Component Using API:** "Download Tax Invoice" button on `/account/orders/[id]` and Order Confirmation screen.

---

## 5. Domain: Payments (Razorpay Standard Checkout)

### 5.1 Payment Initiation
- **Endpoint:** `/api/v1/payments/orders/{order_id}/initiate/`
- **HTTP Method:** `POST`
- **Authentication Required:** Yes (`Authorization: Bearer <token>`).
- **Request Body:** `{}`
- **Response Structure (HTTP 201 Created):**
  ```json
  {
    "payment": {
      "id": "pay_uuid_7777",
      "payment_number": "PAY-BMP-20260907-XXXXX",
      "status": "INITIATED",
      "amount": "1008.00",
      "currency": "INR",
      "gateway": "RAZORPAY"
    },
    "gateway": {
      "key_id": "rzp_test_YourKeyId",
      "gateway_order_id": "order_ND82hsj29Hs",
      "amount": 100800,
      "currency": "INR",
      "name": "Bharath Masala Products",
      "description": "Payment for Order BMP-20260907-9A6PP"
    }
  }
  ```
- **Frontend Integration Flow:**
  1. Frontend receives `gateway.gateway_order_id`, `gateway.key_id`, and `gateway.amount`.
  2. Frontend passes these options to the Razorpay Standard Modal (`new window.Razorpay(options)`).
  3. Modal opens allowing customer to pay via UPI (GPay, PhonePe), Cards, Net Banking, or Wallets.

---

### 5.2 Payment Verification
- **Endpoint:** `/api/v1/payments/orders/{order_id}/verify/`
- **HTTP Method:** `POST`
- **Authentication Required:** Yes.
- **Request Body (JSON):**
  ```json
  {
    "razorpay_order_id": "order_ND82hsj29Hs",
    "razorpay_payment_id": "pay_ND83ks831Ks",
    "razorpay_signature": "9a8b7c6d5e4f3a2b1c0d...",
    "payment_method": "RAZORPAY"
  }
  ```
- **Response Structure (HTTP 200 OK):**
  ```json
  {
    "id": "pay_uuid_7777",
    "status": "CAPTURED",
    "captured_at": "2026-09-07T14:42:15Z"
  }
  ```
- **Frontend Action on Success:** Clear local cart state; redirect customer to `/orders/[id]/confirmation?status=success`.

---

## 6. Domain: Shipping & Consignment Tracking

### 6.1 Customer Order Tracking
- **Endpoint:** `/api/v1/shipping/orders/{order_id}/tracking/`
- **HTTP Method:** `GET`
- **Authentication Required:** Yes (Owner only).
- **Response Structure (HTTP 200 OK):**
  ```json
  {
    "order_id": "order_uuid_0001",
    "order_number": "BMP-20260907-9A6PP",
    "order_status": "SHIPPED",
    "shipped_at": "2026-09-07T16:00:00Z",
    "delivered_at": null,
    "shipments": [
      {
        "id": "shipment_uuid_01",
        "shipment_number": "SHP-BMP-20260907-0001",
        "status": "IN_TRANSIT",
        "courier_name": "DELHIVERY",
        "awb_number": "DEL1234567890",
        "shipping_label_url": "...",
        "estimated_delivery_date": "2026-09-10",
        "items": [
          {
            "id": "s_item_01",
            "sku": "BMP-PEP-250G",
            "product_name": "Thirthahalli Black Pepper",
            "quantity": 2
          }
        ],
        "tracking_events": [
          {
            "id": "ev_01",
            "status": "PICKED_UP",
            "location": "Thirthahalli Hub",
            "description": "Consignment received from warehouse.",
            "event_timestamp": "2026-09-07T16:30:00Z"
          },
          {
            "id": "ev_02",
            "status": "IN_TRANSIT",
            "location": "Shimoga Sorting Facility",
            "description": "Departed sorting hub towards destination.",
            "event_timestamp": "2026-09-07T21:00:00Z"
          }
        ]
      }
    ]
  }
  ```
- **Frontend Page Using API:** `/account/orders/[id]` (Tracking tab / tracking stepper).

---

### 6.2 Public AWB Tracking
- **Endpoint:** `/api/v1/shipping/track/`
- **HTTP Method:** `GET`
- **Authentication Required:** No (Zero auth required; PII and financial values redacted).
- **Query Parameters:** `awb` (string) or `shipment` (string).
- **Response Structure (HTTP 200 OK):**
  ```json
  {
    "tracking": {
      "shipment_number": "SHP-BMP-20260907-0001",
      "courier_name": "DELHIVERY",
      "awb_number": "DEL1234567890",
      "status": "IN_TRANSIT",
      "estimated_delivery_date": "2026-09-10",
      "shipped_at": "2026-09-07T16:00:00Z",
      "destination_city": "Thirthahalli",
      "destination_state": "KARNATAKA",
      "tracking_events": [
        {
          "status": "IN_TRANSIT",
          "location": "Shimoga Sorting Facility",
          "description": "Departed sorting hub.",
          "event_timestamp": "2026-09-07T21:00:00Z"
        }
      ]
    }
  }
  ```
- **Frontend Page Using API:** `/track` (Public AWB Search Portal) and SMS/WhatsApp tracking deep-links.

---

## 7. Domain: Customer Returns & RMA Portal

### 7.1 Customer Return Request Initiation
- **Endpoint:** `/api/v1/orders/{order_id}/returns/`
- **HTTP Method:** `POST`
- **Authentication Required:** Yes (Owner only; validated against 7-day delivery policy window).
- **Request Body (JSON):**
  ```json
  {
    "items": [
      {
        "order_line_item_id": "line_01",
        "quantity": 1,
        "reason": "DEFECTIVE_OR_DAMAGED"
      }
    ],
    "reason": "DEFECTIVE_OR_DAMAGED",
    "requested_resolution": "REFUND",
    "customer_notes": "Aroma seal was broken in transit.",
    "evidence_urls": [
      { "url": "https://images.example.com/damage1.jpg", "description": "Broken seal" }
    ]
  }
  ```
  *(Resolution options: `REFUND` to original payment method or `REPLACEMENT` shipment).*
- **Response Structure (HTTP 201 Created):** Full `ReturnRequestDetailSerializer` object with initial status `REQUESTED`.
- **Frontend Page Using API:** `<ReturnRequestModal />` on `/account/orders/[id]`.
- **Error Responses:**
  - `HTTP 400 Bad Request`: Return window expired (> 7 days from delivery), or return quantity exceeds eligible balance.

---

## 8. Summary of Frontend Route to API Map

| Frontend Page | User Persona | Primary APIs Consumed |
| :--- | :--- | :--- |
| **`/` (Homepage)** | All | `GET /api/v1/catalog/categories/`<br>`GET /api/v1/catalog/products/?featured=true`<br>`GET /api/v1/catalog/products/?bestseller=true` |
| **`/products` (Catalog)** | All | `GET /api/v1/catalog/categories/`<br>`GET /api/v1/catalog/products/?category=&search=&tier=&ordering=` |
| **`/products/[slug]` (PDP)** | All | `GET /api/v1/catalog/products/{slug}/`<br>`GET /api/v1/catalog/products/{slug}/reviews/`<br>`POST /api/v1/catalog/products/{slug}/reviews/`<br>`POST /api/v1/cart/items/` |
| **`<CartDrawer />` & `/cart`** | All | `GET /api/v1/cart/`<br>`POST /api/v1/cart/items/`<br>`PATCH /api/v1/cart/items/{id}/`<br>`DELETE /api/v1/cart/items/{id}/`<br>`POST /api/v1/cart/coupon/`<br>`DELETE /api/v1/cart/coupon/` |
| **`/checkout`** | Customer | `GET /api/v1/cart/`<br>`GET /api/v1/auth/addresses/`<br>`POST /api/v1/auth/addresses/`<br>`POST /api/v1/orders/checkout/`<br>`POST /api/v1/payments/orders/{id}/initiate/`<br>`POST /api/v1/payments/orders/{id}/verify/` |
| **`/track` (Public AWB)** | All | `GET /api/v1/shipping/track/?awb={awb}` |
| **`/account` (Dashboard)** | Customer | `GET /api/v1/auth/me/`<br>`PATCH /api/v1/auth/me/`<br>`GET /api/v1/orders/` |
| **`/account/orders/[id]`** | Customer | `GET /api/v1/orders/{id}/`<br>`GET /api/v1/shipping/orders/{id}/tracking/`<br>`GET /api/v1/orders/{id}/invoice/download/`<br>`POST /api/v1/orders/{id}/cancel/`<br>`POST /api/v1/orders/{id}/returns/` |
| **`/wholesale/register`** | Merchant | `POST /api/v1/auth/register/wholesale/` |
| **`/login` & `/register`** | Guest | `POST /api/v1/auth/login/`<br>`POST /api/v1/auth/register/` |

---

**Map Status:** Complete, field-verified, and grounded strictly in the backend OpenAPI schema.
