# Phase 3.13: Backend Finalization, OpenAPI/Swagger Implementation & API Contract Verification — Implementation Plan

**Document Version:** 1.0.0  
**Date:** September 7, 2026  
**Status:** PROPOSED (Stage 1 — Read-Only Baseline Complete)  
**Execution Objective:** Establish enterprise-grade OpenAPI 3.0 documentation, implement P0 production caching, deliver P1 frontend-critical endpoints, normalize API error contracts, and verify end-to-end runtime API behavior with zero regressions on the 468-test baseline.

---

## 1. Current Architecture Summary

The Bharath Masala Products platform is a production-grade Django 5.0.6 / DRF 3.16.0 backend organized into 12 domain applications:
- `apps.core`: Health probes (`/health/liveness/`, `/health/readiness/`), standard JSON response renderer (`StandardResponseRenderer`), custom exception handling (`custom_exception_handler`), `RequestIDMiddleware` (`X-Request-ID`), and log PII masking (`PIIMaskingFilter`).
- `apps.accounts`: Custom UUID `User` model, role-based access control (`CUSTOMER`, `WHOLESALE_PENDING`, `WHOLESALE_APPROVED`, `STAFF`, `MANAGER`, `SUPERADMIN`), JWT authentication with token rotation in `HttpOnly` cookies, address book with IDOR protection.
- `apps.catalog`: Hierarchical categories, multi-variant products (pack sizes), legal metrology, login-gated B2B wholesale slab pricing, approved customer reviews, and staff review moderation.
- `apps.inventory`: `StockItem`, immutable `StockMovement` ledger, transactional `StockReservation` with automatic 30-minute reservation expiry via Celery Beat, and atomic `select_for_update` row-locking.
- `apps.cart`: Guest and authenticated customer cart persistence, cookie-based guest cart merge on login, stock reservation checks, and coupon attachment.
- `apps.orders`: Atomic checkout with authoritative repricing, snapshotting, finite-state machine transitions (`OrderStateMachine`), customer order history, and cancellation.
- `apps.payments`: Razorpay integration, order initiation, cryptographic HMAC-SHA256 signature verification, idempotent webhook processing, and staff-managed gateway refunds.
- `apps.shipping`: Multi-shipment packaging, courier abstraction, AWB milestone tracking, carrier label generation, and customer parcel tracking.
- `apps.invoices`: Statutory Indian GST compliance (CGST/SGST/IGST), Section 15(3) commercial discount apportionment using the Hamilton-Hare Largest Remainder Method, zero-dependency PDF 1.4 generation, and Rule 53(1A) tax credit notes.
- `apps.notifications`: Multi-channel communication engine (SMS, Email, WhatsApp adapters), Celery task dispatch, and staff notification log inspection.
- `apps.returns`: Reverse logistics RMA workflows, FSSAI warehouse quality inspection restock segregation, and dual resolution (Credit Note + Refund vs Replacement Order).
- `apps.promotions`: Enterprise promotions engine (`Coupon`, `CouponUsage`, `Promotion`, `PromotionRule`, `OrderDiscountSnapshot`), deterministic concurrency locking order ($\text{Coupon} \to \text{StockItem}$), and lifecycle release hooks on order cancellation or abandonment.

**Baseline Verification State:**
- 468 / 468 tests passing (1 intentional SQLite concurrency skip)
- 0 Django check issues
- 0 migration drift
- 100% compliant Black and Ruff linters
- 81 registered URL routes / 98 HTTP operations cataloged in `BACKEND_API_INVENTORY.md`

---

## 2. Scope of Work by Execution Stage

### Stage 2 — OpenAPI / Swagger Implementation
1. **Dependency:** Add `drf-spectacular>=0.28.0,<0.29.0` to `requirements.txt`.
2. **Settings:**
   - Add `"drf_spectacular"` to `THIRD_PARTY_APPS` in `config/settings/base.py`.
   - Set `REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] = "drf_spectacular.openapi.AutoSchema"`.
   - Configure comprehensive `SPECTACULAR_SETTINGS` with 14 domain tags, JWT Bearer security scheme, and cookie authentication scheme.
3. **URL Routing (`config/urls.py`):**
   - `GET /api/v1/schema/`: OpenAPI 3.0 raw schema endpoint.
   - `GET /api/v1/docs/`: Interactive Swagger UI.
   - `GET /api/v1/redoc/`: ReDoc documentation reader.

### Stage 3 & 4 — Schema Validation & API Contract Audit
1. Execute `python3 manage.py spectacular --file schema.yml --validate`.
2. Inspect and resolve any schema warnings using `@extend_schema` and `@extend_schema_view` where DRF generic inference requires explicit typing.
3. Cross-reference `BACKEND_API_INVENTORY.md` against generated schema and produce `API_CONTRACT_VERIFICATION_REPORT.md`.

### Stage 5 — Runtime API Smoke Testing
1. Create `apps/core/tests/test_api_smoke_contracts.py`.
2. Validate public storefront endpoints, customer authenticated endpoints, staff operations endpoints, and RBAC barriers (anonymous $\to$ 401, customer $\to$ staff 403, staff $\to$ manager refund 403).
3. Validate presence of `request_id`, standard envelope fields, and absence of HTTP 500 errors.

### Stage 6 — P0 Production Centralized Cache Configuration
1. In `config/settings/base.py`, configure `CACHES` using Django's built-in `django.core.cache.backends.redis.RedisCache` when `REDIS_URL` or `DATABASE_URL` is set, falling back to `LocMemCache` for local development/testing without Redis.
2. In `config/settings/production.py`, assert Redis cache configuration is active so DRF rate limiting throttles (`auth: 5/min`, `anon: 20/min`, `user: 100/min`) are distributed across Gunicorn workers.
3. Ensure the test suite continues running cleanly without requiring a live Redis instance.

### Stage 7 — P1 Frontend-Critical APIs
1. **P1.1 Staff Wholesale Applications List:**
   - Endpoint: `GET /api/v1/staff/wholesale/`
   - Permissions: `[IsAuthenticated, IsStaffOrManager]`
   - Filtering: `status` (`PENDING`, `APPROVED`, `REJECTED`), `search` (`company_name`, `email`, `phone_number`)
   - Pagination: `StandardResultsSetPagination`
2. **P1.2 Public Active Promotions Display:**
   - Endpoint: `GET /api/v1/promotions/active/`
   - Permissions: `[AllowAny]`
   - Serializer: `PublicPromotionSerializer` (exposes only customer-safe promotional details: title, description, discount type/value, validity dates; no internal targeting rules or hidden codes)
3. **P1.3 Pre-Order Checkout Preview API:**
   - Endpoint: `POST /api/v1/orders/checkout/preview/`
   - Permissions: `[IsAuthenticated]`
   - DRY RUN calculation: Identical financial math to `CheckoutService.create_order_from_cart` without creating orders, decrementing stock, consuming coupon quotas, or initiating payments.
   - Returns items subtotal, coupon discount, qualifying promotions, shipping fee, taxable amount, GST breakdown (CGST/SGST/IGST), and estimated grand total.

### Stage 8 — API Error Contract Normalization (`apps.returns`)
1. Refactor `ReturnError` in `apps/returns/exceptions.py` to subclass DRF's `APIException` with appropriate HTTP status codes:
   - `ReturnPolicyViolation`: HTTP 400 Bad Request
   - `ReturnPermissionDenied`: HTTP 403 Forbidden
   - `ReturnConflict`: HTTP 409 Conflict
   - `ReturnNotFound`: HTTP 404 Not Found
2. Remove manual `try ... except` error responses in `apps/returns/views.py` and `apps/returns/staff_views.py` so exceptions are cleanly handled by `custom_exception_handler` and enveloped consistently.

### Stage 9 — Response Envelope Consistency Audit (`apps.notifications`)
1. In `StaffResendNotificationView` (`apps/notifications/staff_views.py`), eliminate the redundant `"success": success` key inside the response body that causes nested `{"success": true, "data": {"success": true}}`.
2. Standardize response on `{"_message": "...", "dispatched": success, "notification": ...}`.

### Stage 10 — URL Parameter Consistency Review
1. Review all URL routes and document parameter naming conventions (`<uuid:pk>` vs `<uuid:id>`).
2. Maintain backward-compatible route URLs to avoid breaking any existing integrations.

### Stage 11 — Environment Configuration Template
1. Create `.env.example` documenting all configuration keys for Django, PostgreSQL, Redis, Celery, SimpleJWT, Razorpay, WhiteNoise, and statutory GST seller details.

### Stage 12 — Production Storage Readiness Analysis
1. Produce `PRODUCTION_STORAGE_READINESS.md` detailing current filesystem storage versus cloud object storage (`django-storages` with AWS S3 or GCP Cloud Storage) for persistent PDF and media management.

### Stage 13 to 16 — Testing, Verification & Final Documentation
1. Run full test suite: Verify 468+ tests passing.
2. Run quality gates: `manage.py check`, `makemigrations --check --dry-run`, `black --check .`, `ruff check .`, `spectacular --validate`.
3. Provide manual Swagger verification instructions for `/api/v1/docs/`, `/api/v1/redoc/`, and `/api/v1/schema/`.
4. Produce `PHASE_3_13_BACKEND_FINALIZATION_REPORT.md` and append status to `CURRENT_DEVELOPMENT_STATUS_REPORT.md`.

---

## 3. Exact Files Expected to Change

### New Files
- `apps/core/tests/test_api_smoke_contracts.py` (Stage 5 Smoke tests)
- `apps/accounts/tests/test_staff_wholesale_api.py` (Stage 7 Wholesale list tests)
- `apps/promotions/tests/test_public_promotions_api.py` (Stage 7 Public promotions tests)
- `apps/orders/tests/test_checkout_preview_api.py` (Stage 7 Checkout preview tests)
- `.env.example` (Stage 11 Environment template)
- `PRODUCTION_STORAGE_READINESS.md` (Stage 12 Cloud storage assessment)
- `API_CONTRACT_VERIFICATION_REPORT.md` (Stage 4 Contract verification)
- `PHASE_3_13_BACKEND_FINALIZATION_REPORT.md` (Stage 16 Final report)

### Modified Files
- `requirements.txt`: Add `drf-spectacular`
- `config/settings/base.py`: Register `drf_spectacular`, configure `SPECTACULAR_SETTINGS`, configure `CACHES`
- `config/settings/production.py`: Add production Redis cache assertions
- `config/urls.py`: Wire `/api/v1/schema/`, `/api/v1/docs/`, `/api/v1/redoc/`
- `apps/accounts/staff_urls.py`: Register `GET /api/v1/staff/wholesale/`
- `apps/accounts/views.py`: Add `StaffWholesaleListView`
- `apps/promotions/urls.py`: Register `GET /api/v1/promotions/active/`
- `apps/promotions/views.py`: Add `PublicActivePromotionsView`
- `apps/promotions/serializers.py`: Add `PublicPromotionSerializer`
- `apps/orders/urls.py`: Register `POST /api/v1/orders/checkout/preview/`
- `apps/orders/views.py`: Add `CheckoutPreviewView`
- `apps/orders/serializers.py`: Add `CheckoutPreviewRequestSerializer`, `CheckoutPreviewResponseSerializer`
- `apps/returns/exceptions.py`: Subclass DRF `APIException`
- `apps/returns/views.py`: Remove manual exception catches that bypass `custom_exception_handler`
- `apps/returns/staff_views.py`: Remove manual exception catches that bypass `custom_exception_handler`
- `apps/returns/tests/test_return_requests.py`: Adjust test assertions if error envelope code is normalized
- `apps/notifications/staff_views.py`: Fix double envelope in `StaffResendNotificationView`
- `CURRENT_DEVELOPMENT_STATUS_REPORT.md`: Append Phase 3.13 completion section

---

## 4. Risk Analysis & Mitigation

| Identified Risk | Severity | Probability | Mitigation Strategy |
|---|---|---|---|
| **Schema Generation Breaking on Complex Serializers:** Dynamic serializers (`ProductDetailSerializer` with login-dependent wholesale slabs) or custom view methods failing in `drf-spectacular` inspection. | Medium | Medium | Use targeted `@extend_schema` decorators with explicit request/response serializer declarations. Run `spectacular --validate` continuously. |
| **Redis Cache Breaking Test Suite:** If `CACHES` requires a running Redis daemon during `manage.py test`. | High | Low | Configure default cache to use `LocMemCache` in local/test settings unless `REDIS_URL` is explicitly supplied in production. Tests remain 100% self-contained. |
| **Checkout Preview Diverging from Actual Checkout:** Risk of calculating different GST or shipping charges in preview versus checkout. | High | Low | Both `CheckoutPreviewView` and `CheckoutService.create_order_from_cart` will invoke the identical calculation helper methods in `apps.invoices.services.tax_engine` and `apps.promotions.services.discount_engine`. Comprehensive integration test will assert equality. |
| **Return Exception Refactor Breaking Existing Tests:** Modifying `ReturnError` hierarchy could alter error status codes or messages expected by existing tests. | Medium | Low | Status codes (`400`, `403`, `404`, `409`) and messages are preserved exactly as defined. Any change will be verified against the 43 returns domain tests. |

---

## 5. Migration Impact
- **Database Schema Changes:** **NONE.** All proposed changes utilize existing models (`WholesaleProfile`, `Promotion`, `Cart`, `Order`, `ReturnRequest`).
- `python3 manage.py makemigrations --check --dry-run` will report `No changes detected`.

---

## 6. Backward Compatibility Analysis
- All 81 existing routes retain their exact URL patterns, HTTP methods, and payload interfaces.
- The 3 new endpoints (`GET /staff/wholesale/`, `GET /promotions/active/`, `POST /orders/checkout/preview/`) are strictly additive.
- The error normalization in `apps.returns` standardizes error codes (`VALIDATION_ERROR`, `CONFLICT`) while preserving HTTP status codes (`400`, `409`).
- Response envelope format `{success, request_id, message, data, error}` remains strictly invariant.

---

## 7. Test Strategy

```
Phase 3.13 Test Plan:
├── 1. Baseline Preservation: All 468 existing tests must pass untouched.
├── 2. Swagger / OpenAPI Validation: python3 manage.py spectacular --file schema.yml --validate
├── 3. Unit & Integration Tests for New Features:
│   ├── Wholesale Applications List (Filtering, search, pagination, RBAC)
│   ├── Public Active Promotions (Active filtering, date window, customer-safe fields)
│   ├── Checkout Preview (Cart subtotal, discount, GST tax calculation, zero state mutations)
│   └── Parity Test: Checkout Preview vs Actual Checkout equality
├── 4. Error Normalization Regression Tests: apps.returns exception hierarchy
├── 5. Runtime Smoke Tests: apps/core/tests/test_api_smoke_contracts.py (Representative endpoints across all 12 domains)
└── 6. Static Analysis Quality Gates: Django check, migration drift, Black, Ruff
```

---

## 8. Rollback Considerations
- If any stage encounters unresolvable blockers, the work is cleanly modular:
  - OpenAPI changes can be isolated to `config/settings/base.py` and `config/urls.py`.
  - Cache changes can fall back to Django's default `LocMemCache`.
  - New endpoints are self-contained views with zero database schema mutations.
- The baseline test suite (468 tests) acts as an automated safety harness at every step.
