# Bharat Masala — Frontend & Backend Compatibility Matrix

**Audit Date:** 2026-09-08  
**Specification Reference:** OpenAPI 3.0.3 (`schema.yml`) & Next.js 14 (`frontend/`)  
**Legend:**
- **WORKING:** Feature implemented and verified end-to-end against live backend.
- **MISSING:** Feature or route absent from current codebase.
- **BACKEND GAP:** Functionality required by full commerce experience but unsupported by backend models/APIs.
- **ACTION REQUIRED:** Concrete technical step to achieve full production readiness.

---

## Compatibility Matrix

| Feature | Frontend Status | Backend Status | API Available | Working | Missing | Action Required |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Retail User Registration** | Implemented (`/register`) | Implemented (`/api/v1/auth/register/`) | Yes (`POST`) | **YES** | None | Maintain existing validated registration flow. |
| **Wholesale User Registration** | Service Ready (`authService.registerWholesale`) | Implemented (`/api/v1/auth/register/wholesale/`) | Yes (`POST`) | **NO** | Frontend page (`/wholesale`) 404 | Create `frontend/app/wholesale/page.js` with GSTIN/PAN business registration form. |
| **User Login (JWT Auth)** | Implemented (`/login`) | Implemented (`/api/v1/auth/login/`) | Yes (`POST`) | **YES** | None | Maintain existing secure session handling. |
| **Silent Token Refresh** | Implemented (`apiClient.js`) | Implemented (`/api/v1/auth/token/refresh/`) | Yes (`POST`) | **YES** | None | Transparent cookie-based background renewal working cleanly. |
| **Current User Profile** | Implemented (`AuthContext`) | Implemented (`/api/v1/auth/me/`) | Yes (`GET`, `PATCH`) | **YES** | None | Profile details update working cleanly. |
| **User Logout** | Implemented (`AuthContext`) | Implemented (`/api/v1/auth/logout/`) | Yes (`POST`) | **YES** | None | Clears token storage and invalidates refresh session. |
| **Customer Address Book** | Implemented (`/account`) | Implemented (`/api/v1/auth/addresses/`) | Yes (`GET`, `POST`, `PATCH`, `DELETE`) | **YES** | Route `/account/addresses` 404 | Add redirect route `/account/addresses` pointing to `/account#addresses`. |
| **Catalog Listing & Filtering** | Implemented (`/products`) | Implemented (`/api/v1/catalog/products/`) | Yes (`GET`) | **YES** | None | Category, tier, and price filters working with live data. |
| **Product Substring Search** | Implemented (`SearchInterface`) | Implemented (`/api/v1/catalog/products/?search=...`) | Yes (`GET`) | **YES** | None | Debounced search with auto-aborting stale queries working cleanly. |
| **Product Detail & Variants** | Implemented (`/products/[slug]`) | Implemented (`/api/v1/catalog/products/<slug>/`) | Yes (`GET`) | **YES** | None | Multi-tier pack size switcher, live pricing, and stock badges working. |
| **FSSAI & Statutory Metrology** | Implemented (`/products/[slug]`) | Implemented (Product model fields) | Yes (`GET`) | **YES** | None | Legal Metrology block displays FSSAI license, HSN, and packer info. |
| **Verified Customer Reviews** | Implemented (`/products/[slug]`) | Implemented (`/catalog/products/<slug>/reviews/`) | Yes (`GET`, `POST`) | **YES** | None | Displays approved reviews with masked customer names (e.g. "Ramesh K."). |
| **Shopping Cart View** | Implemented (`/cart` & Drawer) | Implemented (`/api/v1/cart/`) | Yes (`GET`, `DELETE`) | **YES** | None | Backend serves as authoritative source of truth. |
| **Add Variant to Cart** | Implemented (`CartContext`) | Implemented (`/api/v1/cart/items/`) | Yes (`POST`) | **YES** | None | Enforces backend inventory availability checks. |
| **Update Cart Line Quantity** | Implemented (`CartContext`) | Implemented (`/api/v1/cart/items/<id>/`) | Yes (`PATCH`) | **YES** | None | Dynamically updates unit count and subtotal. |
| **Remove Line Item** | Implemented (`CartContext`) | Implemented (`/api/v1/cart/items/<id>/`) | Yes (`DELETE`) | **YES** | None | Line item deletion working. |
| **Coupon Code Redemption** | Implemented (`CartContext`) | Implemented (`/api/v1/cart/coupon/`) | Yes (`POST`, `DELETE`) | **YES** | None | Validates coupon rules, minimum spend, and discounts. |
| **Order Checkout** | Implemented (`/checkout`) | Implemented (`/api/v1/orders/checkout/`) | Yes (`POST`) | **YES** | None | Creates order, locks inventory reservations, snapshots delivery address. |
| **Customer Order History** | Implemented (`/account/orders`) | Implemented (`/api/v1/orders/`) | Yes (`GET`) | **YES** | None | Itemized order cards with live statuses and tracking links. |
| **Customer Order Detail** | Implemented (`/account/orders/[id]`) | Implemented (`/api/v1/orders/<id>/`) | Yes (`GET`) | **YES** | None | Order progress steppers, tax breakdown, and shipment info. |
| **Order Cancellation** | Implemented (`orderService.cancelOrder`) | Implemented (`/api/v1/orders/<id>/cancel/`) | Yes (`POST`) | **YES** | None | Customer can cancel orders in `PENDING_PAYMENT` state. |
| **Payment Initiation** | Implemented (`paymentService.initiatePayment`) | Implemented (`/api/v1/payments/orders/<id>/initiate/`) | Yes (`POST`) | **YES** | None | Returns gateway order ID and key ID for checkout. |
| **Razorpay Checkout Modal** | Partially Implemented (`PaymentModal.jsx`) | Gateway Adapter in backend | Yes (`POST`) | **PARTIAL** | Seamless direct invocation | Enhance modal to directly invoke Razorpay Checkout presenting UPI, Card, Netbanking. |
| **Payment Signature Verification** | Implemented (`paymentService.verifyPayment`) | Implemented (`/api/v1/payments/orders/<id>/verify/`) | Yes (`POST`) | **YES** | None | Cryptographic HMAC-SHA256 signature verification working. |
| **Payment Webhooks** | Not on frontend | Implemented (`/api/v1/payments/webhooks/razorpay/`) | Yes (`POST`) | **YES** | None | Backend handles asynchronous captured/failed webhook events. |
| **Cash on Delivery (COD)** | Unsupported | Not implemented in `Order` or `Checkout` | **NO** | **NO** | **BACKEND GAP** | Document backend gap in `BACKEND_GAPS.md`. Do not fake COD. |
| **Order Shipment Tracking** | Implemented (`/account/orders/[id]`) | Implemented (`/shipping/orders/<id>/tracking/`) | Yes (`GET`) | **YES** | None | Carrier consignment cards, AWB numbers, and milestone timelines working. |
| **Public AWB Tracking** | Implemented (`/track`) | Implemented (`/api/v1/shipping/track/`) | Yes (`GET`) | **YES** | None | Public unauthenticated milestone tracking with PII masking working. |
| **Brand Story / Terroir Page** | Missing (`/about`) | Marketing Content Available | N/A (Static) | **NO** | Route `/about` 404 | Create `frontend/app/about/page.js` showcasing Western Ghats heritage. |
| **Wholesale Portal Page** | Missing (`/wholesale`) | B2B API available | Yes (`POST`) | **NO** | Route `/wholesale` 404 | Create `frontend/app/wholesale/page.js` with registration & benefit cards. |
| **Active Offers Page** | Missing (`/offers`) | Promotion data available | N/A (Static) | **NO** | Route `/offers` 404 | Create `frontend/app/offers/page.js` with coupon copy actions. |
| **Gift Boxes Page** | Missing (`/gifts`) | Catalog filtering available | Yes (`GET`) | **NO** | Route `/gifts` 404 | Create `frontend/app/gifts/page.js` showcasing festive hampers and dabbas. |
| **Culinary Stories Page** | Missing (`/stories`) | Folklore content available | N/A (Static) | **NO** | Route `/stories` 404 | Create `frontend/app/stories/page.js` with recipe & harvest journals. |
| **Customer Support Page** | Missing (`/contact`) | Office details available | N/A (Static) | **NO** | Route `/contact` 404 | Create `frontend/app/contact/page.js` with Shimoga address and support hours. |
| **Shipping Policy Page** | Missing (`/shipping-policy`) | SLA details available | N/A (Static) | **NO** | Route `/shipping-policy` 404 | Create `frontend/app/shipping-policy/page.js` with courier SLAs. |
| **Returns & RMA Policy Page** | Missing (`/returns`) | RMA endpoints available | N/A (Static) | **NO** | Route `/returns` 404 | Create `frontend/app/returns/page.js` with food safety return guidelines. |
| **Terms of Service Page** | Missing (`/terms`) | GST policy available | N/A (Static) | **NO** | Route `/terms` 404 | Create `frontend/app/terms/page.js` with invoicing and legal terms. |
| **Privacy Policy Page** | Missing (`/privacy`) | Data security standards | N/A (Static) | **NO** | Route `/privacy` 404 | Create `frontend/app/privacy/page.js` with PCI-DSS & data protection details. |
