# Codex Project Takeover Audit

**Project:** Bharath Masala Django REST Framework backend  
**Audit date:** 2026-09-06  
**Scope:** Read-only repository audit. No application code, migrations, tests, or project configuration were changed. This report is the sole audit artifact created.

## 1. Executive summary

The repository contains a working Phase 1 foundation (`apps.core`, `apps.accounts`) and a working Phase 2 catalog (`apps.catalog`). The current development database has all known migrations applied, `makemigrations --check --dry-run` reports no model drift, Django system checks pass, and all **83/83** discovered automated tests pass.

Phase 3 business modules - inventory, cart, orders, and payments - **do not exist** and are not registered or routed. Consequently, checkout, authoritative stock management, order/address/price snapshots, payment capture/webhook idempotency, and order authorization have not been implemented or tested. Phase 3 is **NOT STARTED**.

The repository does now include Celery, Redis, `django-celery-beat`, a Celery application factory, and Compose services. That infrastructure is configured but has no application tasks, so it is **implemented but unverified as runtime infrastructure** rather than a completed background-processing capability.

The most important current remedial findings before adding business functionality are:

1. **High - log redaction is ineffective for interpolated log arguments and does not apply its declared phone pattern.** The filter edits only `record.msg`, not `record.args`; a test run visibly logged `secret=ABCDE12345` inside an exception. Do not log request bodies, tokens, payment payloads, or KYC data until this is corrected and tested.
2. **Medium - no production deployment verification was performed.** The current audit used the development SQLite database. PostgreSQL locking behavior, Docker startup, Redis/Celery connectivity, worker/beat execution, and production settings were not exercised.
3. **Medium - catalog category serialization can create an N+1 pattern.** The category list prefetches `subcategories`, but `CategorySerializer.get_subcategories()` calls `.filter(is_active=True)`, which does not use Django's ordinary related-object prefetch cache.
4. **Low - Black reports one formatting deviation in `config/settings/base.py`; Ruff is clean.** No formatter was run, per audit constraints.

## 2. Evidence and baseline verification

| Check | Result |
|---|---|
| `python3 manage.py check` | PASS - no issues |
| `python3 manage.py showmigrations` | All listed migrations applied in the local SQLite database |
| `python3 manage.py makemigrations --check --dry-run` | PASS - `No changes detected` |
| `python3 manage.py test` | PASS - 83 tests in 19.472 seconds |
| `black --check .` | FAIL - would reformat `config/settings/base.py` only |
| `ruff check .` | PASS - all checks passed |
| Git history/status | Unavailable - the workspace has no `.git` directory |

Test result: **total 83, pass 83, fail 0, error 0, skipped 0**.

Expected negative-path HTTP logs (400/401/403/404/429/503) and the deliberate test 500 appeared during the test run; they are not test failures. The 500 log did reveal the PII/redaction issue described below.

## 3. Repository structure

```text
config/
  settings/{base,development,staging,production}.py
  celery.py, urls.py, asgi.py, wsgi.py
apps/
  core/       models, middleware, renderer, exceptions, pagination, health views, tests
  accounts/   user/address/wholesale models, auth service, API, admin, migration, tests
  catalog/    catalog/review models, services, API, admin, migration, tests
media/        product uploads (repository-local media)
staticfiles/  collected static assets
```

`README.md`, `PROJECT_CONTINUITY.md`, and `walkthrough.md` are absent. Present project documentation is `PHASE_1_COMPLETION_AUDIT.md`, `PHASE_2_PRE_IMPLEMENTATION_AUDIT.md`, `PHASE_2_COMPLETION_AUDIT.md`, and `PHASE_3_PRE_IMPLEMENTATION_AUDIT.md`.

| App | Exists | In `INSTALLED_APPS` | Models | Migrations | Serializers | Views / URLs | Services | Tests | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `apps.core` | Yes | Yes | Yes (abstract timestamp base) | No app migration needed | No | Yes | Empty package only | Yes | Implemented and tested |
| `apps.accounts` | Yes | Yes | Yes | `0001_initial` | Yes | Yes | Yes | Yes | Implemented and tested |
| `apps.catalog` | Yes | Yes | Yes | `0001_initial` | Yes | Yes | Yes | Yes | Implemented and tested |
| `apps.inventory` | No | No | No | No | No | No | No | No | NOT STARTED |
| `apps.cart` | No | No | No | No | No | No | No | No | NOT STARTED |
| `apps.orders` | No | No | No | No | No | No | No | No | NOT STARTED |
| `apps.payments` | No | No | No | No | No | No | No | No | NOT STARTED |

## 4. Infrastructure and configuration

### Settings and web stack

- `base.py` registers Django, DRF, SimpleJWT blacklist, CORS headers, `django_celery_beat`, and the three existing local apps. DRF defaults to JWT plus session authentication, authenticated permissions, a custom response renderer/exception handler, standard pagination, and anonymous/user throttles.
- Development uses SQLite when `DATABASE_URL` is absent and PostgreSQL when it begins with `postgres`. It has `DEBUG=True`, localhost hosts/origins, and non-secure cookies for local HTTP.
- Production sets `DEBUG=False`, requires a 50+ character secret, requires non-wildcard `DJANGO_ALLOWED_HOSTS`, requires `DATABASE_URL`, uses secure cookies/HTTPS redirect/HSTS/CSP-adjacent browser headers, and accepts configured CORS/CSRF origins. Staging inherits production and disables HSTS preload.
- `config/urls.py` exposes admin, public liveness/readiness probes, auth/staff routes, and public/staff catalog routes. There are no Phase 3 routes.
- `.env.example` supplies placeholders for database, Celery/Redis, Razorpay, email, and CORS. Email and Razorpay settings are not consumed by the current code.

### Redis, Celery, and Docker

Redis/Celery are present in `requirements.txt`, base settings, `config/celery.py`, `config/__init__.py`, `.env.example`, and `docker-compose.yml`. Compose defines `redis`, `celery`, and `celery-beat` in addition to `web` and PostgreSQL.

There are no `tasks.py` files, registered app tasks, payment retries, reservation expiry routines, or email dispatch operations. Runtime startup was not performed, so the correct classification is **configuration present, capability unverified**.

Docker Compose contains explicit local-development database credentials. They should remain demonstrably development-only and never be used for staging/production deployment.

## 5. Phase 1 verification

### Core

- `TimeStampedModel` is an abstract model with indexed `created_at` and `updated_at`.
- Request IDs are validated/generated and returned as `X-Request-ID` headers.
- JSON responses use the declared `{success, request_id, message, data, error}` envelope; 204 responses remain bodyless.
- The exception handler maps normal DRF/Django exceptions to sanitized envelopes; the health liveness/readiness views are public and readiness performs a database `SELECT 1`.
- `StandardResultsSetPagination` is configured globally. DRF anonymous/user throttles are configured; auth endpoints use the `auth` scope.

### Accounts and auth

- `User` has a UUID primary key, unique indexed email and phone fields, `USERNAME_FIELD = "email"`, normalized Indian phones, and the documented roles: CUSTOMER, WHOLESALE_PENDING, WHOLESALE_APPROVED, STAFF, MANAGER, and SUPERADMIN.
- Registration, login, refresh, logout, self profile, address CRUD/default setting, wholesale registration, and manager/admin wholesale verification are routed and tested.
- Refresh tokens use SimpleJWT rotation/blacklisting configuration and an HttpOnly, SameSite=Lax cookie scoped to `/api/v1/auth/`. Production enables `Secure`; development deliberately does not.
- Address requests are scoped to `user=request.user`, preventing ordinary address IDOR. The `IsOwnerOrAdmin` permission nominally permits staff, but the view's strict user-scoped lookup prevents staff from retrieving another user's address; this is stricter than the permission name/documentation, not an authorization bypass.
- Wholesale approval is wrapped in `transaction.atomic()` and locks the profile row with `select_for_update()`.

Phase 1 implementation has credible automated coverage but is not a full production claim: no live production stack or threat-model test was run in this audit.

## 6. Phase 2 verification

### Actual catalog schema

`apps.catalog` implements exactly these domain models: `Category`, `Product`, `ProductVariant`, `WholesaleTierPricing`, `ProductImage`, `ProductReview`, and `ReviewImage`.

- `Product.category` is `models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")`.
- `ProductVariant` has **no `stock_quantity` field**. Its actual business fields are `product`, `variant_name`, `sku`, `weight_in_grams`, `mrp`, `selling_price`, `is_most_chosen`, `sort_order`, and `is_active`, plus inherited timestamps. Neither its migration, serializers, services, admin, nor tests supply another catalog stock source. Inventory therefore has no catalog-level source of truth today.
- Variant MRP/selling-price checks, wholesale quantity/price checks, a unique variant/slab threshold, review rating checks, and a one-review-per-user/product constraint are present at database level.
- Product images have a conditional unique database constraint for one active hero image per product and a transactional save hook that clears an existing active hero. The database constraint prevents duplicate active heroes, but concurrent replacement can still surface an integrity error rather than a controlled conflict response.

### Pricing and data exposure

`CatalogService.get_base_product_queryset()` conditionally prefetches active wholesale slabs only for an authenticated `user.is_wholesale_buyer`. `ProductVariantSerializer` independently checks the same property and removes the `wholesale_slabs` key for everyone else. Public, retail, and pending-wholesale users therefore do not receive slab prices or quantity thresholds through catalog responses. The existing wholesale-security tests pass.

This is appropriately defensive for display. It is not checkout authorization: Phase 3 must recalculate the eligible retail/wholesale price server-side while holding the checkout transaction.

### Reviews and image validation

- Ratings are validated in both model and serializer/service logic; the model enforces 1-5.
- The service rejects an existing review and the database unique constraint is the final duplicate backstop. Concurrent duplicate submissions may raise uncaught `IntegrityError`; future code should translate this to a validation/conflict response.
- Submitted reviews begin pending; public reads only return approved reviews; moderation requires authenticated staff/manager permissions.
- `verified_purchase` is read-only to clients and calculated in the service. Since orders do not exist, it always resolves to `False`; its future import expects `OrderItem`/`OrderStatus`, names that should be reconciled with the eventual order design.
- Product/review image validators check extension, size (5 MB), and Pillow-detected content format.

### Catalog performance

Product list/detail queries select the category and prefetch active variants/images, with conditional slab prefetches; product detail additionally prefetches approved reviews, review users, and review images. This meaningfully limits the major product/variant/image N+1 risks.

The category-list path remains a medium issue: its prefetched subcategories are subsequently filtered in the serializer, generating a related query for each parent category. Use a filtered `Prefetch`/`to_attr` or serialize the prefetched list directly when implementation is authorized.

## 7. Actual Phase 3 status

| Module | Classification | Evidence | Missing functionality / risks |
|---|---|---|---|
| Inventory | NOT STARTED | No directory, models, migrations, APIs, services, admin, tasks, or tests | No canonical stock, reservation, movement log, locking, negative-stock protections, or staff operations |
| Cart | NOT STARTED | No directory, models, migrations, APIs, services, admin, tasks, or tests | No authenticated/guest cart, guest token, ownership controls, merge behavior, or price-change handling |
| Orders | NOT STARTED | No directory, models, migrations, APIs, services, admin, tasks, or tests | No shipping-address snapshot, order-line price snapshot, state machine, customer ownership filter, or audit history |
| Payments | NOT STARTED | No directory, models, migrations, APIs, services, admin, tasks, or tests | No Razorpay integration, signature check, server-side price capture, payment record, webhook event store, or idempotency |

There are no Phase 3 application APIs to audit for payment spoofing, order IDOR, guest-cart enumeration, stock races, or historical data mutation. Their absence is the principal release blocker.

## 8. Database and migration audit

The local SQLite database reports applied migrations for `accounts.0001_initial`, `catalog.0001_initial`, Django contrib applications, `token_blacklist`, and all installed `django_celery_beat` migrations. `makemigrations --check --dry-run` found no model changes without a migration and no conflicts.

Only initial application migrations exist for accounts and catalog. In the absence of Git history, the audit cannot determine whether a historical migration was ever edited after being applied elsewhere. The current source/model state is internally consistent.

The audit did not apply migrations. PostgreSQL-specific behavior - particularly conditional-constraint and future row-lock behavior - was not exercised because the active audit database is SQLite.

## 9. Targeted security audit

| Severity | Finding | Evidence / impact | Recommendation |
|---|---|---|---|
| High | Log PII/secret masking is ineffective for formatted arguments | `PIIMaskingFilter` changes `record.msg` only. Python logging later interpolates `record.args`; the test output disclosed `secret=ABCDE12345`. `PHONE_PATTERN` is declared but never applied. | Redact message and arguments before formatting; include phone handling; add tests for positional and mapping args, tracebacks, PAN/GSTIN/tokens/passwords, webhook bodies. |
| Medium | Production deployment controls unverified | Production settings are strict, but no production check with real required environment, Docker build, PostgreSQL, proxy, Redis, or worker was run. | Run a separate staging/deploy audit before release. |
| Medium | No Phase 3 transactional security domain | No inventory, checkout, order, or payment code exists. | Implement atomic, locked inventory and server-authoritative checkout before exposing purchase endpoints. |
| Low | Development secrets are embedded in Compose and fallback settings | Clearly development-scoped values exist in `docker-compose.yml` and `base.py`. | Keep them out of deployed config, use real secret injection, and scan built images/CI logs. |
| Low | Token refresh accepts a body fallback | The endpoint accepts cookie or `request.data["refresh"]`, which increases accidental token logging/client-storage risk if frontend consumers choose the body path. | Prefer cookie-only refresh for browser clients or document and tightly control non-browser clients. |

Current positive controls include password hashing/validators, short JWT access lifetime, rotation/blacklisting, secure production refresh cookies, role-based wholesale gating, address ownership scoping, generic 500 API responses, validation, throttling, and conditional database constraints.

## 10. Performance audit

| Severity | Finding |
|---|---|
| Medium | Category list serializer filters an already-prefetched relation, risking one subcategory query per parent category. |
| Low | Public search uses several `icontains` predicates over text fields; it will not scale like PostgreSQL full-text/trigram search. |
| Low | `ProductImage.save()` bulk-clears a hero and then saves without product-row locking. The constraint protects integrity, but contention needs a user-facing conflict strategy. |
| Future-critical | There are no cart/inventory/order queries yet. Design these with row locks, constrained indexes, and eager-loading before implementation rather than retrofitting later. |

## 11. Documentation contradictions

| Documentation claim | Actual code / audit result | Status |
|---|---|---|
| Phase 2 completion audit lists `ProductVariant.stock_quantity` | No such field exists in model, migration, serializers, services, admin, or tests | CONTRADICTION |
| Phase 3 pre-audit says Celery, Redis, and `django-celery-beat` are absent | All are in requirements/settings/Compose; `config/celery.py` and app exposure exist | CONTRADICTION (documentation stale) |
| Phase 3 pre-audit says Black would reformat `apps/catalog/serializers.py` | Current Black reports only `config/settings/base.py` | CONTRADICTION (documentation stale) |
| Phase 1 audit says PII masking scrubs phone numbers and effectively protects log output | The phone regex is not used; format arguments escape redaction, demonstrated by test output | CONTRADICTION |
| Phase 1 audit claims zero hardcoded credentials | Development fallback keys and Compose development database credentials are present | CONTRADICTION if read literally; acceptable only as explicitly non-production defaults |
| Phase 1/2 test counts of 42/83 | Current suite finds and passes 83 tests | MATCH for current Phase 2 total |
| Phase 3 pre-audit says the four business apps are absent | All four remain absent | MATCH |

## 12. Bugs, technical debt, and unresolved issues

### Bugs / defects

- Logging filter must be fixed before collecting sensitive production traffic.
- Category list's subcategory filtering defeats prefetch caching.
- Concurrent review creation and hero-image replacement can yield unhandled database integrity errors instead of a controlled client response.
- `ReviewService.verify_user_purchase()` imports future symbols `OrderItem` and `OrderStatus`; planned order naming must either honor that contract or update the review integration in the same release.

### Technical debt / unresolved verification

- No Git metadata is present; provenance, branch state, and migration-edit history cannot be audited.
- No README or consolidated current architecture/runbook exists.
- No PostgreSQL, Docker, Redis, Celery worker, beat, email, payment gateway, or production-environment integration check was performed.
- There is no test coverage for the identified log-redaction flaw or category-list query count.
- Phase 3 security requirements are still design requirements, not delivered controls.

## 13. Recommended continuation plan

Do not recreate existing Phase 1/2 functionality. Start from the audited stopping point after deciding whether the log-redaction fix is an immediate pre-flight change.

### Phase 3A - Pre-flight and inventory

- **Scope:** Repair/cover logging redaction; validate PostgreSQL/Compose runtime; create `apps.inventory` with `StockItem` as the sole stock authority, immutable movements, and reservations.
- **Likely files:** New `apps/inventory/*`, settings/URLs/admin/tests; possibly core logging tests and the logging filter. Add only new migrations.
- **Models/APIs/services:** Stock item per variant, movement ledger, reservation lifecycle, staff-only adjustment/reconciliation endpoints, atomic reserve/release/consume services.
- **Security:** `transaction.atomic()` plus PostgreSQL `select_for_update()`; never let quantities become negative; idempotent reservation transitions; staff RBAC; audit actor/reference.
- **Completion:** PostgreSQL concurrency tests cover simultaneous reservation/consumption, negative stock, expiry, and repeated calls; migration clean; no direct stock field added to `ProductVariant`.

### Phase 3B - Cart

- **Scope:** Add authenticated and guest carts, opaque server-generated guest token handling, merge-on-login, and server-side recalculation.
- **Likely files:** New `apps/cart/*`, URLs, tests, and possibly settings for cookie lifetime.
- **Models/APIs/services:** Cart/cart-item (or a deliberately selected equivalent), quantity mutation/removal/read endpoints, merge service.
- **Security:** Scope every query to user or high-entropy guest token, store guest token HttpOnly, enforce CSRF strategy for cookie-bearing mutations, protect variant deletion with `PROTECT`, and never treat saved cart price as checkout truth.
- **Completion:** Tests cover guest isolation/fixation, IDOR, merge collisions, invalid variants, quantity races, and retail vs approved-wholesale repricing.

### Phase 3C - Orders and checkout

- **Scope:** Add a stateful order domain and a server-side checkout service.
- **Likely files:** New `apps/orders/*`, inventory/cart integration, URLs/admin/tests, new migrations.
- **Models/APIs/services:** Order, line items, status history; snapshot shipping fields (not only a live Address FK); snapshot product/variant/SKU/MRP/unit selling price/quantity/line total/price context.
- **Security:** Lock inventory while calculating authoritative price; re-evaluate wholesale eligibility; customer-scoped order reads; `PROTECT` historical catalog/user references as appropriate; record an auditable status transition actor.
- **Completion:** Tests prove address and price mutation do not alter historical orders, client prices are ignored, duplicate checkout does not double-consume stock, and customer IDOR fails.

### Phase 3D - Payments

- **Scope:** Add Razorpay order initiation and a durable payment/webhook domain.
- **Likely files:** New `apps/payments/*`, order/inventory integrations, settings, URLs, admin, tests, migrations.
- **Models/APIs/services:** Payment record, webhook event/deduplication key, gateway order reference, signature-verification service, idempotent capture/failure transition logic.
- **Security:** Verify raw-body webhook signature before state changes; never accept client payment status or amount; constrain and lock duplicate event/order processing; capture enough audit evidence without logging secrets.
- **Completion:** Gateway fixture tests cover invalid signatures, replayed events, out-of-order events, concurrent deliveries, and exactly-once inventory/order changes.

### Phase 3E - Background tasks and integration

- **Scope:** Implement reservation-expiry cleanup, payment retry/reconciliation where appropriate, and notifications using the already configured Celery/Redis stack.
- **Likely files:** `tasks.py` in the relevant apps, beat schedule registration, integration tests and operational documentation.
- **Security/reliability:** Make tasks idempotent, use retry-safe correlation keys, lock rows when mutating stock/order state, and avoid secrets/PII in task logs.
- **Completion:** Worker/beat/Redis are verified in Compose and staging; tasks are tested for retry and duplicate delivery; all tests, migration check, formatting, and lint pass.

## 14. Phase status matrix

| Phase | Module | Actual Status | Tests | Problems |
|---|---|---|---:|---|
| 1 | `apps.core` | IMPLEMENTED BUT NOT production-environment verified | Included in 83 passing suite | Logging redaction defect; no Git/prod deployment evidence |
| 1 | `apps.accounts` | IMPLEMENTED BUT NOT production-environment verified | Included in 83 passing suite | Refresh body fallback; no staging verification |
| 2 | `apps.catalog` | IMPLEMENTED BUT NOT production-environment verified | Included in 83 passing suite | Category N+1 risk; concurrency conflict handling; stale documentation |
| 3 | `apps.inventory` | NOT STARTED | 0 | No stock source, locking, reservation, movement, admin, or API |
| 3 | `apps.cart` | NOT STARTED | 0 | No cart, guest handling, merge, ownership, or API |
| 3 | `apps.orders` | NOT STARTED | 0 | No checkout, snapshots, status history, or access control |
| 3 | `apps.payments` | NOT STARTED | 0 | No gateway, signature verification, payment records, or idempotency |

**Final status:** The existing Phase 1/2 code is test-green and internally migration-consistent. It is not an end-to-end production e-commerce backend; Phase 3 commerce and payment capabilities remain entirely to be built and must be introduced through new migrations with PostgreSQL-aware transactional tests.
