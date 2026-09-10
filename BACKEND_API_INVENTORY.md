# Bharath Masala Products — Backend API Inventory

This document provides a comprehensive, exhaustive catalog of all **81 URL routes** and **98 HTTP operations** registered in the Bharath Masala Products backend as of Phase 3.11.

---

## 1. Executive Summary Table

| # | Method | Endpoint | App | Auth Required | Minimum Role | Frontend Consumer |
|---|---|---|---|---|---|---|
| 1 | `GET` | `/health/liveness/` | `apps.core` | None | Anyone | Infrastructure / Monitoring |
| 2 | `GET` | `/health/readiness/` | `apps.core` | None | Anyone | Infrastructure / Monitoring |
| 3 | `POST` | `/api/v1/auth/register/` | `apps.accounts` | None | Anyone | Public Storefront |
| 4 | `POST` | `/api/v1/auth/register/wholesale/` | `apps.accounts` | None | Anyone | Wholesale Portal |
| 5 | `POST` | `/api/v1/auth/login/` | `apps.accounts` | None | Anyone | Public Storefront / Customer |
| 6 | `POST` | `/api/v1/auth/token/refresh/` | `apps.accounts` | None (Cookie/Body) | Anyone | All Frontend Apps |
| 7 | `POST` | `/api/v1/auth/logout/` | `apps.accounts` | None (Cookie/Body) | Anyone | Customer / Staff Dashboard |
| 8 | `GET` | `/api/v1/auth/me/` | `apps.accounts` | JWT / Session | Customer | Customer Dashboard / Wholesale |
| 9 | `PATCH` | `/api/v1/auth/me/` | `apps.accounts` | JWT / Session | Customer | Customer Dashboard |
| 10 | `GET` | `/api/v1/auth/addresses/` | `apps.accounts` | JWT / Session | Customer | Customer Dashboard / Checkout |
| 11 | `POST` | `/api/v1/auth/addresses/` | `apps.accounts` | JWT / Session | Customer | Customer Dashboard / Checkout |
| 12 | `GET` | `/api/v1/auth/addresses/<uuid:pk>/` | `apps.accounts` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 13 | `PATCH` | `/api/v1/auth/addresses/<uuid:pk>/` | `apps.accounts` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 14 | `DELETE` | `/api/v1/auth/addresses/<uuid:pk>/` | `apps.accounts` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 15 | `POST` | `/api/v1/auth/addresses/<uuid:pk>/set-default/` | `apps.accounts` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 16 | `POST` | `/api/v1/staff/wholesale/<uuid:pk>/verify/` | `apps.accounts` | JWT / Session | Manager / Superadmin | Manager Dashboard |
| 17 | `GET` | `/api/v1/catalog/categories/` | `apps.catalog` | None | Anyone | Public Storefront |
| 18 | `GET` | `/api/v1/catalog/categories/<slug:slug>/` | `apps.catalog` | None | Anyone | Public Storefront |
| 19 | `GET` | `/api/v1/catalog/products/` | `apps.catalog` | None (Optional) | Anyone | Public Storefront / Wholesale |
| 20 | `GET` | `/api/v1/catalog/products/<slug:slug>/` | `apps.catalog` | None (Optional) | Anyone | Public Storefront / Wholesale |
| 21 | `GET` | `/api/v1/catalog/products/<slug:slug>/reviews/` | `apps.catalog` | None | Anyone | Public Storefront |
| 22 | `POST` | `/api/v1/catalog/products/<slug:slug>/reviews/` | `apps.catalog` | JWT / Session | Customer | Customer Dashboard |
| 23 | `POST` | `/api/v1/staff/catalog/reviews/<uuid:pk>/moderate/` | `apps.catalog` | JWT / Session | Staff / Manager | Staff Dashboard |
| 24 | `GET` | `/api/v1/inventory/` | `apps.inventory` | JWT / Session | Staff / Manager | Staff Dashboard |
| 25 | `POST` | `/api/v1/inventory/restock/` | `apps.inventory` | JWT / Session | Staff / Manager | Staff Dashboard |
| 26 | `GET` | `/api/v1/inventory/<uuid:pk>/` | `apps.inventory` | JWT / Session | Staff / Manager | Staff Dashboard |
| 27 | `POST` | `/api/v1/inventory/<uuid:pk>/adjust/` | `apps.inventory` | JWT / Session | Manager / Superadmin | Manager Dashboard |
| 28 | `GET` | `/api/v1/cart/` | `apps.cart` | None (Guest/Auth) | Anyone | Public Storefront / Checkout |
| 29 | `DELETE` | `/api/v1/cart/` | `apps.cart` | None (Guest/Auth) | Anyone | Public Storefront / Checkout |
| 30 | `POST` | `/api/v1/cart/items/` | `apps.cart` | None (Guest/Auth) | Anyone | Public Storefront / Checkout |
| 31 | `PATCH` | `/api/v1/cart/items/<uuid:pk>/` | `apps.cart` | None (Guest/Auth) | Anyone | Public Storefront / Checkout |
| 32 | `DELETE` | `/api/v1/cart/items/<uuid:pk>/` | `apps.cart` | None (Guest/Auth) | Anyone | Public Storefront / Checkout |
| 33 | `POST` | `/api/v1/cart/coupon/` | `apps.promotions` | None (Guest/Auth) | Anyone | Customer Checkout |
| 34 | `DELETE` | `/api/v1/cart/coupon/` | `apps.promotions` | None (Guest/Auth) | Anyone | Customer Checkout |
| 35 | `DELETE` | `/api/v1/cart/coupon/remove/` | `apps.promotions` | None (Guest/Auth) | Anyone | Customer Checkout |
| 36 | `POST` | `/api/v1/orders/checkout/` | `apps.orders` | JWT / Session | Customer | Customer Checkout |
| 37 | `GET` | `/api/v1/orders/` | `apps.orders` | JWT / Session | Customer | Customer Dashboard |
| 38 | `GET` | `/api/v1/orders/<uuid:pk>/` | `apps.orders` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 39 | `POST` | `/api/v1/orders/<uuid:pk>/cancel/` | `apps.orders` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 40 | `GET` | `/api/v1/staff/orders/` | `apps.orders` | JWT / Session | Staff / Manager | Staff Dashboard |
| 41 | `GET` | `/api/v1/staff/orders/<uuid:pk>/` | `apps.orders` | JWT / Session | Staff / Manager | Staff Dashboard |
| 42 | `POST` | `/api/v1/staff/orders/<uuid:pk>/status/` | `apps.orders` | JWT / Session | Staff / Manager | Staff Dashboard |
| 43 | `GET` | `/api/v1/payments/orders/<uuid:order_id>/` | `apps.payments` | JWT / Session | Customer (Owner) | Customer Checkout / Dashboard |
| 44 | `POST` | `/api/v1/payments/orders/<uuid:order_id>/initiate/` | `apps.payments` | JWT / Session | Customer (Owner) | Customer Checkout |
| 45 | `POST` | `/api/v1/payments/orders/<uuid:order_id>/verify/` | `apps.payments` | JWT / Session | Customer (Owner) | Customer Checkout |
| 46 | `POST` | `/api/v1/payments/webhooks/razorpay/` | `apps.payments` | Webhook Signature | Gateway Service | Webhook / Background |
| 47 | `GET` | `/api/v1/staff/payments/` | `apps.payments` | JWT / Session | Staff / Manager | Staff Dashboard |
| 48 | `GET` | `/api/v1/staff/payments/<uuid:payment_id>/` | `apps.payments` | JWT / Session | Staff / Manager | Staff Dashboard |
| 49 | `POST` | `/api/v1/staff/payments/<uuid:payment_id>/refund/` | `apps.payments` | JWT / Session | Manager / Superadmin | Manager Dashboard |
| 50 | `GET` | `/api/v1/shipping/track/` | `apps.shipping` | None | Anyone (Public AWB) | Public Storefront |
| 51 | `GET` | `/api/v1/shipping/orders/<uuid:order_id>/tracking/` | `apps.shipping` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 52 | `GET` | `/api/v1/shipping/<str:shipment_number>/` | `apps.shipping` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 53 | `GET` | `/api/v1/staff/shipping/` | `apps.shipping` | JWT / Session | Staff / Manager | Staff Dashboard |
| 54 | `GET` | `/api/v1/staff/shipping/<uuid:shipment_id>/` | `apps.shipping` | JWT / Session | Staff / Manager | Staff Dashboard |
| 55 | `POST` | `/api/v1/staff/shipping/<uuid:shipment_id>/status/` | `apps.shipping` | JWT / Session | Staff / Manager | Staff Dashboard |
| 56 | `POST` | `/api/v1/staff/shipping/<uuid:shipment_id>/label/` | `apps.shipping` | JWT / Session | Staff / Manager | Staff Dashboard |
| 57 | `POST` | `/api/v1/staff/shipping/<uuid:shipment_id>/cancel/` | `apps.shipping` | JWT / Session | Staff / Manager | Staff Dashboard |
| 58 | `POST` | `/api/v1/staff/shipping/orders/<uuid:order_id>/shipments/` | `apps.shipping` | JWT / Session | Staff / Manager | Staff Dashboard |
| 59 | `GET` | `/api/v1/staff/shipping/orders/<uuid:order_id>/fulfillment-summary/` | `apps.shipping` | JWT / Session | Staff / Manager | Staff Dashboard |
| 60 | `GET` | `/api/v1/orders/<uuid:order_id>/invoice/` | `apps.invoices` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 61 | `GET` | `/api/v1/orders/<uuid:order_id>/invoice/download/` | `apps.invoices` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 62 | `GET` | `/api/v1/orders/<uuid:order_id>/invoice/html/` | `apps.invoices` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 63 | `GET` | `/api/v1/orders/<uuid:order_id>/credit-notes/` | `apps.invoices` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 64 | `GET` | `/api/v1/orders/<uuid:order_id>/credit-notes/<uuid:id>/download/` | `apps.invoices` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 65 | `GET` | `/api/v1/staff/invoices/` | `apps.invoices` | JWT / Session | Staff / Manager | Staff Dashboard |
| 66 | `GET` | `/api/v1/staff/invoices/<uuid:id>/` | `apps.invoices` | JWT / Session | Staff / Manager | Staff Dashboard |
| 67 | `POST` | `/api/v1/staff/invoices/<uuid:id>/regenerate-pdf/` | `apps.invoices` | JWT / Session | Staff / Manager | Staff Dashboard |
| 68 | `GET` | `/api/v1/staff/invoices/credit-notes/` | `apps.invoices` | JWT / Session | Staff / Manager | Staff Dashboard |
| 69 | `GET` | `/api/v1/staff/invoices/credit-notes/<uuid:id>/` | `apps.invoices` | JWT / Session | Staff / Manager | Staff Dashboard |
| 70 | `POST` | `/api/v1/staff/invoices/credit-notes/<uuid:id>/regenerate-pdf/` | `apps.invoices` | JWT / Session | Staff / Manager | Staff Dashboard |
| 71 | `GET` | `/api/v1/staff/notifications/` | `apps.notifications` | JWT / Session | Staff / Manager | Staff Dashboard |
| 72 | `GET` | `/api/v1/staff/notifications/<uuid:id>/` | `apps.notifications` | JWT / Session | Staff / Manager | Staff Dashboard |
| 73 | `POST` | `/api/v1/staff/notifications/<uuid:id>/resend/` | `apps.notifications` | JWT / Session | Staff / Manager | Staff Dashboard |
| 74 | `GET` | `/api/v1/orders/<uuid:order_id>/returns/` | `apps.returns` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 75 | `POST` | `/api/v1/orders/<uuid:order_id>/returns/` | `apps.returns` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 76 | `GET` | `/api/v1/orders/<uuid:order_id>/returns/<uuid:id>/` | `apps.returns` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 77 | `POST` | `/api/v1/orders/<uuid:order_id>/returns/<uuid:id>/cancel/` | `apps.returns` | JWT / Session | Customer (Owner) | Customer Dashboard |
| 78 | `GET` | `/api/v1/staff/returns/` | `apps.returns` | JWT / Session | Staff / Manager | Staff Dashboard |
| 79 | `GET` | `/api/v1/staff/returns/<uuid:id>/` | `apps.returns` | JWT / Session | Staff / Manager | Staff Dashboard |
| 80 | `POST` | `/api/v1/staff/returns/<uuid:id>/review/` | `apps.returns` | JWT / Session | Staff / Manager | Staff Dashboard |
| 81 | `POST` | `/api/v1/staff/returns/<uuid:id>/shipment/schedule/` | `apps.returns` | JWT / Session | Staff / Manager | Staff Dashboard |
| 82 | `POST` | `/api/v1/staff/returns/<uuid:id>/shipment/status/` | `apps.returns` | JWT / Session | Staff / Manager | Staff Dashboard |
| 83 | `POST` | `/api/v1/staff/returns/<uuid:id>/inspection/` | `apps.returns` | JWT / Session | Staff / Manager | Staff Dashboard |
| 84 | `POST` | `/api/v1/staff/returns/<uuid:id>/complete/` | `apps.returns` | JWT / Session | Staff / Manager | Staff Dashboard |
| 85 | `GET` | `/api/v1/staff/promotions/coupons/` | `apps.promotions` | JWT / Session | Staff / Manager | Staff Dashboard |
| 86 | `POST` | `/api/v1/staff/promotions/coupons/` | `apps.promotions` | JWT / Session | Manager / Superadmin | Manager Dashboard |
| 87 | `GET` | `/api/v1/staff/promotions/coupons/<uuid:pk>/` | `apps.promotions` | JWT / Session | Staff / Manager | Staff Dashboard |
| 88 | `PUT` | `/api/v1/staff/promotions/coupons/<uuid:pk>/` | `apps.promotions` | JWT / Session | Manager / Superadmin | Manager Dashboard |
| 89 | `PATCH` | `/api/v1/staff/promotions/coupons/<uuid:pk>/` | `apps.promotions` | JWT / Session | Manager / Superadmin | Manager Dashboard |
| 90 | `DELETE` | `/api/v1/staff/promotions/coupons/<uuid:pk>/` | `apps.promotions` | JWT / Session | Manager / Superadmin | Manager Dashboard |
| 91 | `POST` | `/api/v1/staff/promotions/coupons/<uuid:pk>/toggle/` | `apps.promotions` | JWT / Session | Manager / Superadmin | Manager Dashboard |
| 92 | `GET` | `/api/v1/staff/promotions/promotions/` | `apps.promotions` | JWT / Session | Staff / Manager | Staff Dashboard |
| 93 | `POST` | `/api/v1/staff/promotions/promotions/` | `apps.promotions` | JWT / Session | Manager / Superadmin | Manager Dashboard |
| 94 | `GET` | `/api/v1/staff/promotions/promotions/<uuid:pk>/` | `apps.promotions` | JWT / Session | Staff / Manager | Staff Dashboard |
| 95 | `PUT` | `/api/v1/staff/promotions/promotions/<uuid:pk>/` | `apps.promotions` | JWT / Session | Manager / Superadmin | Manager Dashboard |
| 96 | `PATCH` | `/api/v1/staff/promotions/promotions/<uuid:pk>/` | `apps.promotions` | JWT / Session | Manager / Superadmin | Manager Dashboard |
| 97 | `DELETE` | `/api/v1/staff/promotions/promotions/<uuid:pk>/` | `apps.promotions` | JWT / Session | Manager / Superadmin | Manager Dashboard |

*(Note: Endpoints with multiple HTTP methods are counted as separate operations, yielding 98 operations across 81 route entries.)*

---

## 2. Exhaustive Endpoint Specifications

### 2.1. Core & Infrastructure (`apps.core`)

#### 1. Liveness Probe
- **HTTP Method:** `GET`
- **URL:** `/health/liveness/`
- **Application:** `apps.core`
- **View:** `LivenessCheckView`
- **Auth Required:** No
- **Required Role:** Any
- **Request Serializer:** None
- **Request Fields:** None
- **Response Serializer:** Implicit dictionary
- **Expected Response (HTTP 200):**
  ```json
  {
    "success": true,
    "request_id": "req_...",
    "message": "Operation successful",
    "data": {
      "status": "alive",
      "timestamp": "2026-09-07T20:55:00.000000+05:30"
    },
    "error": null
  }
  ```
- **Error Responses:** N/A (process crash returns 502/504 at gateway)
- **Frontend Consumer:** Infrastructure / Kubernetes / Monitoring

#### 2. Readiness Probe
- **HTTP Method:** `GET`
- **URL:** `/health/readiness/`
- **Application:** `apps.core`
- **View:** `ReadinessCheckView`
- **Auth Required:** No
- **Required Role:** Any
- **Request Serializer:** None
- **Request Fields:** None
- **Response Serializer:** Implicit dictionary
- **Expected Response (HTTP 200):**
  ```json
  {
    "success": true,
    "request_id": "req_...",
    "message": "Operation successful",
    "data": {
      "status": "ready",
      "services": {
        "database": "healthy"
      },
      "timestamp": "2026-09-07T20:55:00.000000+05:30"
    },
    "error": null
  }
  ```
- **Error Responses:**
  - HTTP 503 Service Unavailable: `{"success": false, "request_id": "...", "message": "An error occurred", "data": null, "error": {"code": "ERROR", "details": {"status": "unhealthy", "services": {"database": "unreachable"}}}}`
- **Frontend Consumer:** Infrastructure / Load Balancer

---

### 2.2. Authentication & Accounts (`apps.accounts`)

#### 3. Retail Customer Registration
- **HTTP Method:** `POST`
- **URL:** `/api/v1/auth/register/`
- **Application:** `apps.accounts`
- **View:** `CustomerRegistrationView`
- **Auth Required:** No (Rate limited: 5 req/min)
- **Required Role:** Anyone
- **Request Serializer:** `CustomerRegistrationSerializer`
- **Request Fields:** `email` (string, required), `phone_number` (string, 10-digit Indian, required), `first_name` (string, optional), `last_name` (string, optional), `password` (string, min 8 chars, required), `confirm_password` (string, required)
- **Response Serializer:** `UserSerializer` + tokens
- **Expected Response (HTTP 201):**
  - Sets HttpOnly Cookie: `refresh_token` (`Path=/api/v1/auth/`, `Max-Age=7d`, `SameSite=Lax`, `Secure` in prod)
  ```json
  {
    "success": true,
    "request_id": "req_...",
    "message": "Registration successful. Welcome to Bharath Masala Products!",
    "data": {
      "access_token": "eyJhbG...",
      "token_type": "Bearer",
      "user": {
        "id": "uuid",
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
    },
    "error": null
  }
  ```
- **Error Responses:** HTTP 400 Validation Error (`VALIDATION_ERROR`), HTTP 429 Rate Limited (`RATE_LIMIT_EXCEEDED`)
- **Frontend Consumer:** Public Storefront

#### 4. B2B Wholesale Customer Application
- **HTTP Method:** `POST`
- **URL:** `/api/v1/auth/register/wholesale/`
- **Application:** `apps.accounts`
- **View:** `WholesaleRegistrationView`
- **Auth Required:** No (Rate limited: 5 req/min)
- **Required Role:** Anyone
- **Request Serializer:** `WholesaleRegistrationSerializer`
- **Request Fields:**
  - `user`: `{ email, phone_number, first_name, last_name, password, confirm_password }`
  - `company_name`: string (max 200)
  - `gstin`: string (valid 15-char Indian GSTIN)
  - `pan_number`: string (valid 10-char PAN)
  - `fssai_license`: string (optional 14-digit FSSAI)
  - `business_type`: choice (`PROPRIETORSHIP`, `PARTNERSHIP`, `LLP`, `PRIVATE_LIMITED`, `PUBLIC_LIMITED`, `RETAILER`, `DISTRIBUTOR`, `RESTAURANT_HOTEL`, `OTHER`)
- **Response Serializer:** `UserSerializer` + tokens
- **Expected Response (HTTP 201):**
  - Sets HttpOnly Cookie: `refresh_token`
  ```json
  {
    "success": true,
    "request_id": "req_...",
    "message": "Wholesale application submitted successfully. Account is pending verification.",
    "data": {
      "access_token": "eyJ...",
      "token_type": "Bearer",
      "user": {
        "id": "uuid",
        "email": "merchant@malenadugrocers.com",
        "role": "WHOLESALE",
        "is_wholesale_buyer": false,
        "wholesale_profile": {
          "id": "uuid",
          "company_name": "Malenadu Grocers",
          "masked_gstin": "29ABC******1Z5",
          "masked_pan": "ABC****F",
          "fssai_license": "11223344556677",
          "business_type": "RETAILER",
          "verification_status": "PENDING",
          "verified_at": null,
          "rejection_reason": "",
          "created_at": "2026-09-07T12:00:00Z"
        }
      }
    },
    "error": null
  }
  ```
- **Error Responses:** HTTP 400 Validation Error, HTTP 429 Rate Limited
- **Frontend Consumer:** Wholesale Portal

#### 5. User Login
- **HTTP Method:** `POST`
- **URL:** `/api/v1/auth/login/`
- **Application:** `apps.accounts`
- **View:** `LoginView`
- **Auth Required:** No (Rate limited: 5 req/min)
- **Required Role:** Anyone
- **Request Serializer:** `LoginSerializer`
- **Request Fields:** `email` (string, required), `password` (string, required)
- **Response Serializer:** `UserSerializer` + tokens + cart merge report
- **Expected Response (HTTP 200):**
  - Sets HttpOnly Cookie: `refresh_token`
  - Clears Cookie: `guest_cart_token` (if merged)
  ```json
  {
    "success": true,
    "request_id": "req_...",
    "message": "Login successful.",
    "data": {
      "access_token": "eyJ...",
      "token_type": "Bearer",
      "user": { ... },
      "cart_merge_adjustments": []
    },
    "error": null
  }
  ```
- **Error Responses:** HTTP 400 Bad Request (`Invalid email or password.`), HTTP 429 Rate Limited
- **Frontend Consumer:** Public Storefront / Customer / Wholesale / Staff

#### 6. Token Refresh
- **HTTP Method:** `POST`
- **URL:** `/api/v1/auth/token/refresh/`
- **Application:** `apps.accounts`
- **View:** `TokenRefreshView`
- **Auth Required:** No (Reads `refresh_token` from HttpOnly cookie, fallback to body `refresh`)
- **Required Role:** Anyone
- **Request Serializer:** Implicit / `{"refresh": "..."}`
- **Response Serializer:** Implicit
- **Expected Response (HTTP 200):**
  - Rotates and sets new HttpOnly Cookie: `refresh_token`
  ```json
  {
    "success": true,
    "request_id": "req_...",
    "message": "Token refreshed successfully.",
    "data": {
      "access_token": "eyJ...",
      "token_type": "Bearer"
    },
    "error": null
  }
  ```
- **Error Responses:** HTTP 401 Unauthorized (`AUTHENTICATION_FAILED`)
- **Frontend Consumer:** All Frontend Apps (Axios/Fetch interceptors)

#### 7. User Logout
- **HTTP Method:** `POST`
- **URL:** `/api/v1/auth/logout/`
- **Application:** `apps.accounts`
- **View:** `LogoutView`
- **Auth Required:** No
- **Required Role:** Anyone
- **Request Serializer:** Implicit / reads cookie or body `refresh`
- **Response Serializer:** Implicit
- **Expected Response (HTTP 200):**
  - Deletes Cookie: `refresh_token`
  ```json
  {
    "success": true,
    "request_id": "req_...",
    "message": "Successfully logged out.",
    "data": null,
    "error": null
  }
  ```
- **Frontend Consumer:** Customer Dashboard / Staff Dashboard

#### 8. User Profile (Retrieve)
- **HTTP Method:** `GET`
- **URL:** `/api/v1/auth/me/`
- **Application:** `apps.accounts`
- **View:** `UserProfileView`
- **Auth Required:** Yes
- **Required Role:** Any Authenticated User
- **Response Serializer:** `UserSerializer`
- **Expected Response (HTTP 200):**
  ```json
  {
    "success": true,
    "request_id": "req_...",
    "message": "Operation successful",
    "data": {
      "id": "uuid",
      "email": "user@example.com",
      "phone_number": "+919876543210",
      "first_name": "Aarav",
      "last_name": "Sharma",
      "full_name": "Aarav Sharma",
      "role": "CUSTOMER",
      "is_wholesale_buyer": false,
      "date_joined": "2026-09-07T12:00:00Z",
      "wholesale_profile": null
    },
    "error": null
  }
  ```
- **Frontend Consumer:** Customer Dashboard / Wholesale Portal

#### 9. User Profile (Update)
- **HTTP Method:** `PATCH`
- **URL:** `/api/v1/auth/me/`
- **Application:** `apps.accounts`
- **View:** `UserProfileView`
- **Auth Required:** Yes
- **Required Role:** Any Authenticated User
- **Request Serializer:** `UserUpdateSerializer`
- **Request Fields:** `first_name` (string, optional), `last_name` (string, optional)
- **Response Serializer:** `UserSerializer`
- **Expected Response (HTTP 200):** Full updated user data + `message: "Profile updated successfully."`
- **Frontend Consumer:** Customer Dashboard

#### 10 & 11. Address Book (List & Create)
- **HTTP Method:** `GET`, `POST`
- **URL:** `/api/v1/auth/addresses/`
- **Application:** `apps.accounts`
- **View:** `AddressListCreateView`
- **Auth Required:** Yes
- **Required Role:** Customer / Authenticated User
- **Request Serializer (POST):** `AddressSerializer`
- **Request Fields:** `recipient_name` (string), `phone_number` (string), `address_line_1` (string), `address_line_2` (string, optional), `landmark` (string, optional), `city` (string), `state` (string), `pincode` (string, 6 digits), `address_type` (`HOME`/`OFFICE`/`WAREHOUSE`/`OTHER`), `is_default_shipping` (bool), `is_default_billing` (bool)
- **Response Serializer:** `AddressSerializer` (list on GET, object on POST)
- **Expected Response (GET 200):** `data: [ AddressSerializer, ... ]`
- **Expected Response (POST 201):** `data: { AddressSerializer, ... }`
- **Frontend Consumer:** Customer Dashboard / Checkout

#### 12, 13 & 14. Address Detail (Retrieve, Update, Delete)
- **HTTP Method:** `GET`, `PATCH`, `DELETE`
- **URL:** `/api/v1/auth/addresses/<uuid:pk>/`
- **Application:** `apps.accounts`
- **View:** `AddressDetailView`
- **Auth Required:** Yes
- **Required Role:** Resource Owner or Admin
- **Request Serializer (PATCH):** `AddressSerializer` (partial)
- **Expected Response (GET 200, PATCH 200):** `data: { AddressSerializer }`
- **Expected Response (DELETE 204):** Empty body (RFC compliant)
- **Frontend Consumer:** Customer Dashboard

#### 15. Address Set Default
- **HTTP Method:** `POST`
- **URL:** `/api/v1/auth/addresses/<uuid:pk>/set-default/`
- **Application:** `apps.accounts`
- **View:** `AddressSetDefaultView`
- **Auth Required:** Yes
- **Required Role:** Resource Owner
- **Request Fields:** `type`: `"shipping"` or `"billing"`
- **Response Serializer:** `AddressSerializer`
- **Expected Response (HTTP 200):** Updated address object
- **Frontend Consumer:** Customer Dashboard

#### 16. Staff Wholesale Verification
- **HTTP Method:** `POST`
- **URL:** `/api/v1/staff/wholesale/<uuid:pk>/verify/`
- **Application:** `apps.accounts`
- **View:** `WholesaleVerificationView`
- **Auth Required:** Yes
- **Required Role:** Manager or Superadmin (`IsManagerOrAdmin`)
- **Request Serializer:** `WholesaleVerificationSerializer`
- **Request Fields:** `action` (`APPROVE` / `REJECT`), `rejection_reason` (string, mandatory if REJECT)
- **Response Serializer:** `WholesaleProfileSerializer`
- **Expected Response (HTTP 200):** Updated wholesale profile
- **Frontend Consumer:** Manager Dashboard

---

### 2.3. Catalog & Reviews (`apps.catalog`)

#### 17. Category List
- **HTTP Method:** `GET`
- **URL:** `/api/v1/catalog/categories/`
- **Application:** `apps.catalog`
- **View:** `CategoryListView`
- **Auth Required:** No
- **Response Serializer:** `CategorySerializer` (many=True)
- **Response Structure:** Hierarchical list of root categories with nested `subcategories`.
- **Frontend Consumer:** Public Storefront (Header Navigation / Mega Menu)

#### 18. Category Detail
- **HTTP Method:** `GET`
- **URL:** `/api/v1/catalog/categories/<slug:slug>/`
- **Application:** `apps.catalog`
- **View:** `CategoryDetailView`
- **Auth Required:** No
- **Response Serializer:** `CategorySerializer`
- **Frontend Consumer:** Public Storefront

#### 19. Product Catalog List
- **HTTP Method:** `GET`
- **URL:** `/api/v1/catalog/products/`
- **Application:** `apps.catalog`
- **View:** `ProductListView`
- **Auth Required:** No (Optional JWT provides wholesale tier pricing if approved)
- **Query Parameters:** `category`, `tier`, `form`, `origin`, `featured`, `bestseller`, `search`, `ordering`, `page`, `page_size`
- **Response Serializer:** `ProductListSerializer` (paginated)
- **Expected Response (HTTP 200):**
  ```json
  {
    "success": true,
    "request_id": "req_...",
    "message": "Operation successful",
    "data": {
      "count": 42,
      "page": 1,
      "total_pages": 3,
      "next": "http://.../?page=2",
      "previous": null,
      "results": [
        {
          "id": "uuid",
          "slug": "byadgi-chilli-stemless",
          "name": "Byadgi Chilli - Stemless",
          "tier": "PREMIUM",
          "form": "WHOLE",
          "origin": "Byadgi, Haveri, Karnataka",
          "category": { "id": "uuid", "name": "Pure Spices", "slug": "pure-spices" },
          "primary_image_url": "http://.../media/products/byadgi.jpg",
          "min_price": "220.00",
          "max_price": "850.00",
          "average_rating": "4.8",
          "total_reviews": 12,
          "is_featured": true,
          "is_bestseller": true
        }
      ]
    },
    "error": null
  }
  ```
- **Frontend Consumer:** Public Storefront / Search / Filter

#### 20. Product Detail
- **HTTP Method:** `GET`
- **URL:** `/api/v1/catalog/products/<slug:slug>/`
- **Application:** `apps.catalog`
- **View:** `ProductDetailView`
- **Auth Required:** No (Optional JWT unlocks wholesale slabs if user is verified wholesale buyer)
- **Response Serializer:** `ProductDetailSerializer`
- **Response Structure:** Includes variants with SKU, pack size, stock status, everyday retail price, and `wholesale_pricing` slabs when authorized.
- **Frontend Consumer:** Public Storefront (Product Detail Page)

#### 21 & 22. Product Reviews (List & Submit)
- **HTTP Method:** `GET`, `POST`
- **URL:** `/api/v1/catalog/products/<slug:slug>/reviews/`
- **Application:** `apps.catalog`
- **View:** `ProductReviewListCreateView`
- **Auth Required:** `GET`: No (Public); `POST`: Yes (`IsAuthenticated`)
- **Request Fields (POST):** `rating` (int, 1-5, required), `title` (string, required), `review_body` (string, required), `images` (multipart file list, optional)
- **Response Serializer:** `ProductReviewSerializer` (paginated on GET; single object on POST with message pending moderation)
- **Frontend Consumer:** Public Storefront (Product Detail Page)

#### 23. Staff Review Moderation
- **HTTP Method:** `POST`
- **URL:** `/api/v1/staff/catalog/reviews/<uuid:pk>/moderate/`
- **Application:** `apps.catalog`
- **View:** `StaffReviewModerationView`
- **Auth Required:** Yes
- **Required Role:** Staff or Manager (`IsStaffOrManager`)
- **Request Serializer:** `ReviewModerationSerializer`
- **Request Fields:** `action` (`APPROVE` / `REJECT`)
- **Expected Response (HTTP 200):** Moderation confirmation
- **Frontend Consumer:** Staff Dashboard

---

### 2.4. Inventory Management (`apps.inventory`)

#### 24. Stock Items List
- **HTTP Method:** `GET`
- **URL:** `/api/v1/inventory/`
- **Application:** `apps.inventory`
- **View:** `StockItemListView`
- **Auth Required:** Yes
- **Required Role:** Staff or Manager
- **Response Serializer:** `StockItemSerializer` (paginated)
- **Response Fields:** SKU, variant name, pack size, quantity on hand, quantity reserved, quantity available, batch number, location.
- **Frontend Consumer:** Staff Dashboard

#### 25. Stock Inbound Restock
- **HTTP Method:** `POST`
- **URL:** `/api/v1/inventory/restock/`
- **Application:** `apps.inventory`
- **View:** `StockRestockView`
- **Auth Required:** Yes
- **Required Role:** Staff or Manager
- **Request Serializer:** `StockRestockSerializer`
- **Request Fields:** `variant_id` (UUID), `quantity` (int > 0), `note` (string)
- **Response Serializer:** `StockItemSerializer`
- **Frontend Consumer:** Staff Dashboard

#### 26. Stock Item Detail
- **HTTP Method:** `GET`
- **URL:** `/api/v1/inventory/<uuid:pk>/`
- **Application:** `apps.inventory`
- **View:** `StockItemDetailView`
- **Auth Required:** Yes
- **Required Role:** Staff or Manager
- **Response Serializer:** `StockItemSerializer`
- **Frontend Consumer:** Staff Dashboard

#### 27. Stock Adjustment (Manager Override)
- **HTTP Method:** `POST`
- **URL:** `/api/v1/inventory/<uuid:pk>/adjust/`
- **Application:** `apps.inventory`
- **View:** `StockAdjustmentView`
- **Auth Required:** Yes
- **Required Role:** Manager or Superadmin (`IsManagerOrAdmin`)
- **Request Serializer:** `StockAdjustmentSerializer`
- **Request Fields:** `quantity_delta` (int, positive or negative), `note` (string, required)
- **Response Serializer:** `StockItemSerializer`
- **Frontend Consumer:** Manager Dashboard

---

### 2.5. Cart & Promotions (`apps.cart`, `apps.promotions`)

#### 28 & 29. Cart Retrieve & Clear
- **HTTP Method:** `GET`, `DELETE`
- **URL:** `/api/v1/cart/`
- **Application:** `apps.cart`
- **View:** `CartView`
- **Auth Required:** No (Guest cookie `guest_cart_token` or Authenticated User)
- **Response Serializer:** `CartSerializer`
- **Expected Response (HTTP 200):**
  ```json
  {
    "success": true,
    "request_id": "req_...",
    "message": "Cart retrieved successfully.",
    "data": {
      "cart": {
        "id": "uuid",
        "items_subtotal": "550.00",
        "applied_coupon_code": "SPICE10",
        "discount_amount": "55.00",
        "net_subtotal": "495.00",
        "items": [
          {
            "id": "uuid",
            "variant_id": "uuid",
            "sku": "BYADGI-250G",
            "product_name": "Byadgi Chilli",
            "unit_price": "275.00",
            "quantity": 2,
            "line_subtotal": "550.00"
          }
        ]
      }
    },
    "error": null
  }
  ```
- **Frontend Consumer:** Public Storefront / Cart Drawer / Checkout

#### 30. Add Cart Item
- **HTTP Method:** `POST`
- **URL:** `/api/v1/cart/items/`
- **Application:** `apps.cart`
- **View:** `CartItemListCreateView`
- **Auth Required:** No
- **Request Serializer:** `AddCartItemSerializer`
- **Request Fields:** `variant_id` (UUID), `quantity` (int >= 1)
- **Response Serializer:** `CartSerializer`
- **Frontend Consumer:** Product Detail / Storefront

#### 31 & 32. Update & Remove Cart Item
- **HTTP Method:** `PATCH`, `DELETE`
- **URL:** `/api/v1/cart/items/<uuid:pk>/`
- **Application:** `apps.cart`
- **View:** `CartItemDetailView`
- **Auth Required:** No
- **Request Fields (PATCH):** `quantity` (int >= 1)
- **Response Serializer:** `CartSerializer`
- **Frontend Consumer:** Cart Page / Cart Drawer

#### 33 & 34. Apply & Remove Coupon
- **HTTP Method:** `POST`, `DELETE`
- **URL:** `/api/v1/cart/coupon/`
- **Application:** `apps.promotions`
- **View:** `CartCouponApplyView`
- **Auth Required:** No (Guest or Customer)
- **Request Serializer (POST):** `ApplyCouponSerializer` (`code`: string, uppercase)
- **Response Serializer:** `CartSerializer` (with updated `discount_amount` and `net_subtotal`)
- **Frontend Consumer:** Cart / Customer Checkout

#### 35. Dedicated Coupon Remove Endpoint
- **HTTP Method:** `DELETE`
- **URL:** `/api/v1/cart/coupon/remove/`
- **Application:** `apps.promotions`
- **View:** `CartCouponRemoveView`
- **Auth Required:** No
- **Response Serializer:** `CartSerializer`
- **Frontend Consumer:** Cart / Customer Checkout

---

### 2.6. Orders & Checkout (`apps.orders`)

#### 36. Checkout (Create Order from Cart)
- **HTTP Method:** `POST`
- **URL:** `/api/v1/orders/checkout/`
- **Application:** `apps.orders`
- **View:** `CheckoutView`
- **Auth Required:** Yes (`IsAuthenticated`)
- **Required Role:** Customer
- **Request Serializer:** `CheckoutRequestSerializer`
- **Request Fields:** `shipping_address_id` (UUID, required), `customer_notes` (string, optional)
- **Response Serializer:** `OrderSerializer`
- **Expected Response (HTTP 201):**
  ```json
  {
    "success": true,
    "request_id": "req_...",
    "message": "Order placed successfully.",
    "data": {
      "order": {
        "id": "uuid",
        "order_number": "BMP-20260907-XXXXX",
        "order_status": "PENDING_PAYMENT",
        "items_subtotal": "550.00",
        "discount_amount": "55.00",
        "taxable_amount": "471.43",
        "tax_amount": "23.57",
        "shipping_fee": "0.00",
        "total_amount": "495.00",
        "lines": [ ... ],
        "created_at": "2026-09-07T12:00:00Z"
      }
    },
    "error": null
  }
  ```
- **Error Responses:** HTTP 400 Validation Error, HTTP 409 Conflict (`OrderConflict` / `CartConflict` / Stock Exhausted)
- **Frontend Consumer:** Customer Checkout

#### 37 & 38. Customer Orders (List & Detail)
- **HTTP Method:** `GET`
- **URL:** `/api/v1/orders/` & `/api/v1/orders/<uuid:pk>/`
- **Application:** `apps.orders`
- **View:** `OrderListView` & `OrderDetailView`
- **Auth Required:** Yes
- **Required Role:** Resource Owner (Strict User IDOR isolation)
- **Response Serializer:** `OrderSerializer` (paginated on list)
- **Frontend Consumer:** Customer Dashboard

#### 39. Customer Cancel Order
- **HTTP Method:** `POST`
- **URL:** `/api/v1/orders/<uuid:pk>/cancel/`
- **Application:** `apps.orders`
- **View:** `OrderCancelView`
- **Auth Required:** Yes
- **Required Role:** Resource Owner
- **Conditions:** Order must be in `PENDING_PAYMENT` state.
- **Request Serializer:** `OrderCancelSerializer` (`reason`: string, optional)
- **Response Serializer:** `OrderSerializer`
- **Frontend Consumer:** Customer Dashboard

#### 40, 41 & 42. Staff Orders Management
- **HTTP Method:** `GET` (List), `GET` (Detail), `POST` (Status Transition)
- **URL:** `/api/v1/staff/orders/`, `/api/v1/staff/orders/<uuid:pk>/`, `/api/v1/staff/orders/<uuid:pk>/status/`
- **Application:** `apps.orders`
- **Views:** `StaffOrderListView`, `StaffOrderDetailView`, `StaffOrderStatusUpdateView`
- **Auth Required:** Yes
- **Required Role:** Staff or Manager
- **Query Params (List):** `status`, `is_wholesale`, `search`, `page`, `page_size`
- **Request Fields (Status Update):** `status` (string choice), `notes` (string)
- **Response Serializer:** `OrderSerializer`
- **Frontend Consumer:** Staff Dashboard

---

### 2.7. Payments & Webhooks (`apps.payments`)

#### 43. Payment Detail
- **HTTP Method:** `GET`
- **URL:** `/api/v1/payments/orders/<uuid:order_id>/`
- **Application:** `apps.payments`
- **View:** `PaymentDetailView`
- **Auth Required:** Yes
- **Required Role:** Resource Owner
- **Response Serializer:** `PaymentSerializer`
- **Frontend Consumer:** Customer Checkout / Order Details

#### 44. Initiate Payment
- **HTTP Method:** `POST`
- **URL:** `/api/v1/payments/orders/<uuid:order_id>/initiate/`
- **Application:** `apps.payments`
- **View:** `PaymentInitiateView`
- **Auth Required:** Yes
- **Required Role:** Resource Owner
- **Response Structure (HTTP 201):**
  ```json
  {
    "success": true,
    "request_id": "req_...",
    "message": "Payment initiated successfully.",
    "data": {
      "payment": { "id": "uuid", "amount": "495.00", "currency": "INR", "status": "INITIATED" },
      "gateway": {
        "key_id": "rzp_live_...",
        "gateway_order_id": "order_H768...",
        "amount": 49500,
        "currency": "INR",
        "name": "Bharath Masala Products",
        "description": "Payment for Order BMP-20260907-XXXXX"
      }
    },
    "error": null
  }
  ```
- **Frontend Consumer:** Customer Checkout (feeds Razorpay checkout.js modal)

#### 45. Verify Payment
- **HTTP Method:** `POST`
- **URL:** `/api/v1/payments/orders/<uuid:order_id>/verify/`
- **Application:** `apps.payments`
- **View:** `PaymentVerifyView`
- **Auth Required:** Yes
- **Required Role:** Resource Owner
- **Request Serializer:** `PaymentVerifyRequestSerializer`
- **Request Fields:** `razorpay_order_id`, `razorpay_payment_id`, `razorpay_signature`, `payment_method` (optional)
- **Response Serializer:** `PaymentSerializer`
- **Expected Response (HTTP 200):** Captured payment object
- **Frontend Consumer:** Customer Checkout (modal completion handler)

#### 46. Razorpay Webhook Ingress
- **HTTP Method:** `POST`
- **URL:** `/api/v1/payments/webhooks/razorpay/`
- **Application:** `apps.payments`
- **View:** `RazorpayWebhookView`
- **Auth Required:** None (Cryptographic `X-Razorpay-Signature` HMAC verification)
- **Request Body:** Raw Razorpay event payload
- **Expected Response (HTTP 200):** `{"event_id": "...", "status": "processed"}`
- **Frontend Consumer:** Background Gateway Webhook Service

#### 47, 48 & 49. Staff Payments & Gateway Refund
- **HTTP Method:** `GET` (List), `GET` (Detail), `POST` (Refund)
- **URL:** `/api/v1/staff/payments/`, `/api/v1/staff/payments/<uuid:payment_id>/`, `/api/v1/staff/payments/<uuid:payment_id>/refund/`
- **Application:** `apps.payments`
- **Views:** `StaffPaymentListView`, `StaffPaymentDetailView`, `StaffPaymentRefundView`
- **Auth Required:** Yes
- **Required Role:** List/Detail: `IsStaffOrManager`; Refund: `IsManagerOrAdmin`
- **Request Fields (Refund):** `amount` (Decimal, optional for partial refund; defaults to full), `reason` (string)
- **Response Serializer:** `PaymentSerializer`
- **Frontend Consumer:** Staff Dashboard (List/Detail); Manager Dashboard (Refund)

---

### 2.8. Shipping & Logistics (`apps.shipping`)

#### 50. Public AWB Tracking
- **HTTP Method:** `GET`
- **URL:** `/api/v1/shipping/track/`
- **Application:** `apps.shipping`
- **View:** `PublicAwbTrackingView`
- **Auth Required:** No
- **Query Params:** `awb` or `shipment`
- **Response Serializer:** `PublicTrackingSerializer` (strictly redacts customer PII and financials)
- **Frontend Consumer:** Public Storefront / SMS Tracking Links

#### 51 & 52. Customer Order Tracking & Shipment Detail
- **HTTP Method:** `GET`
- **URL:** `/api/v1/shipping/orders/<uuid:order_id>/tracking/` & `/api/v1/shipping/<str:shipment_number>/`
- **Application:** `apps.shipping`
- **Views:** `CustomerOrderTrackingView`, `CustomerShipmentDetailView`
- **Auth Required:** Yes
- **Required Role:** Resource Owner
- **Response Serializer:** `ShipmentSerializer`
- **Frontend Consumer:** Customer Dashboard

#### 53 through 59. Staff Shipping Operations
- **HTTP Method:** `GET` (List, Detail, Summary), `POST` (Create, Status, Label, Cancel)
- **Endpoints:**
  - `GET /api/v1/staff/shipping/`
  - `GET /api/v1/staff/shipping/<uuid:shipment_id>/`
  - `POST /api/v1/staff/shipping/<uuid:shipment_id>/status/`
  - `POST /api/v1/staff/shipping/<uuid:shipment_id>/label/`
  - `POST /api/v1/staff/shipping/<uuid:shipment_id>/cancel/`
  - `POST /api/v1/staff/shipping/orders/<uuid:order_id>/shipments/`
  - `GET /api/v1/staff/shipping/orders/<uuid:order_id>/fulfillment-summary/`
- **Application:** `apps.shipping`
- **Auth Required:** Yes
- **Required Role:** Staff or Manager
- **Frontend Consumer:** Staff Warehouse Dashboard

---

### 2.9. Statutory Invoices & Credit Notes (`apps.invoices`)

#### 60. Customer Order Invoice (JSON)
- **HTTP Method:** `GET`
- **URL:** `/api/v1/orders/<uuid:order_id>/invoice/`
- **Application:** `apps.invoices`
- **View:** `CustomerOrderInvoiceView`
- **Auth Required:** Yes
- **Required Role:** Resource Owner
- **Response Serializer:** `InvoiceSerializer`
- **Frontend Consumer:** Customer Dashboard

#### 61. Customer Order Invoice (PDF Download)
- **HTTP Method:** `GET`
- **URL:** `/api/v1/orders/<uuid:order_id>/invoice/download/`
- **Application:** `apps.invoices`
- **View:** `CustomerOrderInvoiceDownloadView`
- **Auth Required:** Yes
- **Required Role:** Resource Owner
- **Response Content-Type:** `application/pdf` (Binary stream with `Content-Disposition: attachment; filename="Invoice_BMP_2026-27_00001.pdf"`)
- **Frontend Consumer:** Customer Dashboard (Browser Download)

#### 62. Customer Order Invoice (Printable HTML)
- **HTTP Method:** `GET`
- **URL:** `/api/v1/orders/<uuid:order_id>/invoice/html/`
- **Application:** `apps.invoices`
- **View:** `CustomerOrderInvoiceHtmlView`
- **Auth Required:** Yes
- **Required Role:** Resource Owner
- **Response Content-Type:** `text/html` (Print-optimized CSS template)
- **Frontend Consumer:** Customer Dashboard (Print Dialog)

#### 63 & 64. Customer Credit Notes (List & PDF Download)
- **HTTP Method:** `GET`
- **URL:** `/api/v1/orders/<uuid:order_id>/credit-notes/` & `.../<uuid:id>/download/`
- **Application:** `apps.invoices`
- **Views:** `CustomerOrderCreditNoteListView`, `CustomerOrderCreditNoteDownloadView`
- **Auth Required:** Yes
- **Required Role:** Resource Owner
- **Response:** JSON list or binary PDF attachment
- **Frontend Consumer:** Customer Dashboard

#### 65 through 70. Staff Invoices & Credit Notes Management
- **HTTP Method:** `GET` (List, Detail), `POST` (Regenerate PDF)
- **Endpoints:**
  - `GET /api/v1/staff/invoices/`
  - `GET /api/v1/staff/invoices/<uuid:id>/`
  - `POST /api/v1/staff/invoices/<uuid:id>/regenerate-pdf/`
  - `GET /api/v1/staff/invoices/credit-notes/`
  - `GET /api/v1/staff/invoices/credit-notes/<uuid:id>/`
  - `POST /api/v1/staff/invoices/credit-notes/<uuid:id>/regenerate-pdf/`
- **Application:** `apps.invoices`
- **Auth Required:** Yes
- **Required Role:** Staff or Manager
- **Frontend Consumer:** Staff Dashboard

---

### 2.10. Notifications Log (`apps.notifications`)

#### 71, 72 & 73. Staff Notification Logs & Resend
- **HTTP Method:** `GET` (List, Detail), `POST` (Resend)
- **URL:** `/api/v1/staff/notifications/`, `/api/v1/staff/notifications/<uuid:id>/`, `/api/v1/staff/notifications/<uuid:id>/resend/`
- **Application:** `apps.notifications`
- **Views:** `StaffNotificationLogListView`, `StaffNotificationLogDetailView`, `StaffResendNotificationView`
- **Auth Required:** Yes
- **Required Role:** Staff or Manager
- **Response Serializer:** `NotificationLogSerializer`
- **Frontend Consumer:** Staff Operations Dashboard

---

### 2.11. Returns & Reverse Logistics (`apps.returns`)

#### 74 & 75. Customer Return Requests (List & Create)
- **HTTP Method:** `GET`, `POST`
- **URL:** `/api/v1/orders/<uuid:order_id>/returns/`
- **Application:** `apps.returns`
- **View:** `CustomerOrderReturnListCreateView`
- **Auth Required:** Yes
- **Required Role:** Resource Owner
- **Request Serializer (POST):** `ReturnRequestCreateSerializer`
- **Request Fields:** `items`: `[ { order_line_item_id, quantity, reason } ]`, `reason`, `requested_resolution` (`REFUND`/`REPLACEMENT`), `customer_notes`, `evidence_urls`
- **Response Serializer:** `ReturnRequestDetailSerializer`
- **Frontend Consumer:** Customer Dashboard

#### 76 & 77. Customer Return Detail & Cancel
- **HTTP Method:** `GET`, `POST`
- **URL:** `/api/v1/orders/<uuid:order_id>/returns/<uuid:id>/` & `.../cancel/`
- **Application:** `apps.returns`
- **Views:** `CustomerOrderReturnDetailView`, `CustomerOrderReturnCancelView`
- **Auth Required:** Yes
- **Required Role:** Resource Owner
- **Response Serializer:** `ReturnRequestDetailSerializer`
- **Frontend Consumer:** Customer Dashboard

#### 78 through 84. Staff Returns Workflow
- **HTTP Method:** `GET` (List, Detail), `POST` (Review, Schedule Pickup, Update Transit, QA Inspection, Complete Resolution)
- **Endpoints:**
  - `GET /api/v1/staff/returns/`
  - `GET /api/v1/staff/returns/<uuid:id>/`
  - `POST /api/v1/staff/returns/<uuid:id>/review/` (`APPROVE` / `REJECT`)
  - `POST /api/v1/staff/returns/<uuid:id>/shipment/schedule/` (Reverse courier booking)
  - `POST /api/v1/staff/returns/<uuid:id>/shipment/status/` (Reverse transit update)
  - `POST /api/v1/staff/returns/<uuid:id>/inspection/` (Record QA & FSSAI restock vs discard)
  - `POST /api/v1/staff/returns/<uuid:id>/complete/` (Execute credit note / refund / replacement)
- **Application:** `apps.returns`
- **Auth Required:** Yes
- **Required Role:** Staff or Manager
- **Frontend Consumer:** Staff Operations Dashboard

---

### 2.12. Staff Promotions & Coupons Management (`apps.promotions`)

#### 85 through 91. Staff Coupons Management
- **HTTP Method:** `GET` (List, Detail), `POST` (Create, Toggle), `PUT`/`PATCH` (Update), `DELETE` (Delete)
- **Endpoints:**
  - `GET /api/v1/staff/promotions/coupons/`
  - `POST /api/v1/staff/promotions/coupons/` (Manager/Admin)
  - `GET /api/v1/staff/promotions/coupons/<uuid:pk>/`
  - `PUT`, `PATCH` `/api/v1/staff/promotions/coupons/<uuid:pk>/` (Manager/Admin)
  - `DELETE /api/v1/staff/promotions/coupons/<uuid:pk>/` (Manager/Admin)
  - `POST /api/v1/staff/promotions/coupons/<uuid:pk>/toggle/` (Manager/Admin)
- **Application:** `apps.promotions`
- **Views:** `StaffCouponListCreateView`, `StaffCouponDetailView`, `StaffCouponToggleView`
- **Auth Required:** Yes
- **Required Role:** List/Detail: `IsStaffOrManager`; Create/Update/Delete/Toggle: `IsManagerOrAdmin`
- **Request/Response Serializer:** `StaffCouponSerializer`
- **Frontend Consumer:** Staff Dashboard / Manager Dashboard

#### 92 through 97. Staff Automated Promotions Management
- **HTTP Method:** `GET` (List, Detail), `POST` (Create), `PUT`/`PATCH` (Update), `DELETE` (Delete)
- **Endpoints:**
  - `GET /api/v1/staff/promotions/promotions/`
  - `POST /api/v1/staff/promotions/promotions/` (Manager/Admin)
  - `GET /api/v1/staff/promotions/promotions/<uuid:pk>/`
  - `PUT`, `PATCH` `/api/v1/staff/promotions/promotions/<uuid:pk>/` (Manager/Admin)
  - `DELETE /api/v1/staff/promotions/promotions/<uuid:pk>/` (Manager/Admin)
- **Application:** `apps.promotions`
- **Views:** `StaffPromotionListCreateView`, `StaffPromotionDetailView`
- **Auth Required:** Yes
- **Required Role:** List/Detail: `IsStaffOrManager`; Create/Update/Delete: `IsManagerOrAdmin`
- **Request/Response Serializer:** `StaffPromotionSerializer`
- **Frontend Consumer:** Staff Dashboard / Manager Dashboard
