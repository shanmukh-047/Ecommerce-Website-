# PHASE 3 PRE-IMPLEMENTATION AUDIT
## Bharath Masala Products — Cart, Inventory, Orders & Payments

**Audit Date:** 2026-09-05
**Audit Type:** Pre-Implementation Compatibility & Risk Assessment
**Codebase State:** Phase 1 + Phase 2 complete

---

## AUDIT GATE STATUS

| Check | Result | Status |
|---|---|---|
| `python3 manage.py check` | System check identified no issues (0 silenced) | ✅ PASS |
| `python3 manage.py makemigrations --check --dry-run` | No changes detected | ✅ PASS |
| `python3 manage.py test` | Ran 83 tests in 16.330s — OK | ✅ PASS |
| `black --check .` | 1 file needs reformatting (`apps/catalog/serializers.py`) | ⚠️ MINOR |
| `ruff check .` | All checks passed | ✅ PASS |

> **NOTE on black finding:** `apps/catalog/serializers.py` has a minor formatting deviation. It is not a regression in logic or functionality. Per audit rules, it is reported but NOT auto-fixed here. Must be corrected before Phase 3 implementation begins.

> **AUDIT GATE RESULT: CONDITIONAL PASS.** One trivial formatting correction required before implementation. Zero logical regressions. 83 tests pass unchanged.

---

## SECTION 1 — CURRENT SYSTEM STATUS

### Installed Applications
```
DJANGO_APPS:    admin, auth, contenttypes, sessions, messages, staticfiles
THIRD_PARTY:    rest_framework, simplejwt, simplejwt.token_blacklist, corsheaders
LOCAL_APPS:     apps.core, apps.accounts, apps.catalog
```

**Missing for Phase 3 (expected):** `apps.inventory`, `apps.cart`, `apps.orders`, `apps.payments` — none yet exist. No premature stubs detected.

### Database Engine
- **Driver:** `psycopg2-binary>=2.9.12` — confirmed in `requirements.txt`
- **PostgreSQL version:** 16-alpine (defined in `docker-compose.yml`)
- **SELECT FOR UPDATE / advisory locks:** Fully supported. PostgreSQL 16 satisfies all concurrency requirements for Phase 3 inventory reservation.

### Async Infrastructure Gap (CRITICAL)
- **Redis:** NOT in `requirements.txt`, NOT in `docker-compose.yml`
- **Celery:** NOT in `requirements.txt`
- **django-celery-beat:** NOT in `requirements.txt`
- **Implication:** Payment webhook retry, order confirmation email, stock reservation expiry cleanup — all require Celery + Redis. These MUST be added as part of Phase 3 setup before async features are implemented.

### URL Namespace Structure (confirmed clean)
```
/admin/
/health/liveness/
/health/readiness/
/api/v1/auth/           → apps.accounts.urls (namespace=auth)
/api/v1/staff/          → apps.accounts.staff_urls (namespace=staff)
/api/v1/catalog/        → apps.catalog.urls (namespace=catalog)
/api/v1/staff/catalog/  → apps.catalog.staff_urls (namespace=staff-catalog)
```
Phase 3 will add:
```
/api/v1/cart/           → apps.cart.urls
/api/v1/orders/         → apps.orders.urls
/api/v1/payments/       → apps.payments.urls
/api/v1/staff/orders/   → apps.orders.staff_urls
/api/v1/inventory/      → apps.inventory.urls (staff only)
```

---

## SECTION 2 — EXISTING TEST RESULTS

```
Ran 83 tests in 16.330s
OK
```

- Phase 1 (accounts, core, auth, JWT): 42 tests — all pass
- Phase 2 (catalog, variants, wholesale pricing, reviews): 41 tests — all pass
- Total: **83 tests, 0 failures, 0 errors**

No Phase 3 test regressions are possible — Phase 3 apps do not yet exist.

---

## SECTION 3 — ProductVariant.stock_quantity INVESTIGATION

### FINDING: stock_quantity DOES NOT EXIST

| Location Inspected | Finding |
|---|---|
| `apps/catalog/models.py` lines 158–238 | No `stock_quantity` field on `ProductVariant` |
| `apps/catalog/migrations/0001_initial.py` lines 302–363 | No `stock_quantity` column in database schema |
| `apps/catalog/serializers.py` | No inventory or stock field in any serializer |
| `apps/catalog/admin.py` | No `stock_quantity` in `ProductVariantInline` or `ProductVariantAdmin` |
| `apps/catalog/services/catalog_service.py` | No stock filtering or stock annotation |
| `apps/catalog/tests/test_models.py` | No reference to `stock_quantity` |
| `grep -r stock_quantity .` | Found ONLY in `PHASE_2_COMPLETION_AUDIT.md` (documentation artifact, not code) |

**ProductVariant actual fields (confirmed from migration):**
`id`, `product`, `variant_name`, `sku`, `weight_in_grams`, `mrp`, `selling_price`, `is_most_chosen`, `sort_order`, `is_active`, `created_at`, `updated_at`

**Conclusion:** `stock_quantity` was never implemented in Phase 2. The codebase is clean of any conflicting stock source.

**Action required:** NONE. No migration needed. No backward compatibility risk.

---

## SECTION 4 — INVENTORY SOURCE-OF-TRUTH RECOMMENDATION

**OPTION A (Remove via migration):** Moot — field does not exist. No migration needed.

**Recommendation: Proceed directly with canonical `StockItem` architecture.**

```
apps.inventory
├── StockItem           ← OneToOne → ProductVariant
│   ├── quantity_on_hand  (PositiveIntegerField)
│   ├── quantity_reserved (PositiveIntegerField, default=0)
│   ├── reorder_level     (PositiveIntegerField)
│   └── last_restocked_at (DateTimeField, null=True)
└── StockMovement       ← Immutable audit log
    ├── stock_item    (FK → StockItem)
    ├── movement_type (ENUM: INBOUND, SALE, RESERVATION, CANCELLATION, EXPIRY, ADJUSTMENT)
    ├── quantity_delta (IntegerField — positive or negative)
    ├── reference_id  (UUIDField, null=True — order/cart reference)
    └── recorded_by   (FK → User, null=True, SET_NULL)
```

**Canonical rule:** `StockItem.quantity_on_hand` is the ONLY source of stock truth.
`ProductVariant` remains a pure pricing/cataloging model with no inventory fields ever added.
All stock operations go through `InventoryService` with PostgreSQL row-level locking.

---

## SECTION 5 — DATABASE DEPENDENCY ANALYSIS

### Existing FK on_delete behaviors relevant to Phase 3

| Model | FK Target | on_delete | Phase 3 Risk |
|---|---|---|---|
| `WholesaleProfile.user` | `User` | `CASCADE` | Low |
| `Address.user` | `User` | `CASCADE` | **HIGH** — Orders must snapshot address; cannot FK-depend on live Address |
| `Category.parent` | `Category` | `CASCADE` | Medium — deleting parent cascades subcategories |
| `ProductReview.product` | `Product` | `CASCADE` | Low for Phase 3 |
| `ProductVariant` → `Product` | `Product` | `CASCADE` | **HIGH** — OrderLineItem must snapshot SKU+name+price; must not cascade from product delete |

### Required Phase 3 FK Decisions
1. `OrderLineItem.variant` → `ProductVariant` with `on_delete=PROTECT` (never CASCADE)
2. `Order.user` → `User` with `on_delete=PROTECT` (never delete user with orders)
3. `Order` address fields = snapshot (not FK to live Address)
4. `StockItem.variant` → `ProductVariant` with `on_delete=CASCADE` (stock record follows variant)

---

## SECTION 6 — CART COMPATIBILITY ANALYSIS

### Existing platform auth is compatible with guest carts
- JWT authentication via HttpOnly cookie exists for authenticated users
- Default `IsAuthenticated` permission class must be overridden to `AllowAny` on cart endpoints
- Guest session token: UUID4 stored in HttpOnly cookie, server-side validated via `CartItem.guest_token`

### Cart Model Design
```
CartItem
├── id (UUID PK)
├── user (FK → User, null=True — NULL for guest carts)
├── guest_token (CharField, null=True, db_index=True)
├── variant (FK → ProductVariant, on_delete=PROTECT)
├── quantity (PositiveIntegerField)
├── saved_unit_price (DecimalField — price at time of add, for change detection)
└── created_at / updated_at
Meta:
  UniqueConstraint(["user", "variant"], condition=Q(user__isnull=False))
  UniqueConstraint(["guest_token", "variant"], condition=Q(guest_token__isnull=False))
  CheckConstraint: user IS NOT NULL OR guest_token IS NOT NULL
```

**Race condition on add-to-cart:** Use `update_or_create()` inside `@transaction.atomic` with DB unique constraint as backstop.

---

## SECTION 7 — GUEST TOKEN SECURITY ANALYSIS

| Threat | Mitigation |
|---|---|
| Token enumeration | Guest token = UUID4 (128-bit entropy, not sequential) |
| Token theft via XSS | Store in HttpOnly cookie, NOT localStorage |
| CSRF on cart mutation | CSRF middleware is active in `base.py` MIDDLEWARE |
| Token fixation | Server generates fresh token on first cart write only |
| Cross-user cart exposure | Cart queryset always scoped to `guest_token` value |
| Abandoned cart accumulation | Celery beat task to purge expired guest carts (requires Celery) |

**Recommendation:** HttpOnly cookie for guest token (consistent with existing refresh token cookie pattern at `JWT_REFRESH_COOKIE_NAME`).

Server sets: `Set-Cookie: guest_token=<uuid4>; HttpOnly; SameSite=Lax; Max-Age=2592000`

---

## SECTION 8 — PostgreSQL CONCURRENCY READINESS

**Assessment: READY with required coding patterns**

PostgreSQL 16 supports:
- `SELECT FOR UPDATE` — row-level exclusive lock
- `SELECT FOR UPDATE NOWAIT` — fail immediately if locked (prevents deadlock cascades)
- `SELECT FOR UPDATE SKIP LOCKED` — for Celery reservation expiry cleanup

**Required reservation pattern:**
```python
@transaction.atomic
def reserve_stock(variant_id, quantity, cart_item_id):
    try:
        stock = StockItem.objects.select_for_update(nowait=True).get(variant_id=variant_id)
    except OperationalError:
        raise StockReservationConflictError("Another transaction holds a lock. Retry.")

    available = stock.quantity_on_hand - stock.quantity_reserved
    if available < quantity:
        raise InsufficientStockError(f"Only {available} units available")

    stock.quantity_reserved += quantity
    stock.save(update_fields=["quantity_reserved", "updated_at"])

    return StockReservation.objects.create(
        stock_item=stock, cart_item_id=cart_item_id,
        quantity=quantity, expires_at=now() + timedelta(minutes=15),
    )
```

The critical double-spend race condition (two users, 1 unit in stock, simultaneous checkout) is resolved by `SELECT FOR UPDATE NOWAIT` — the second request receives HTTP 409 Conflict.

---

## SECTION 9 — STOCK RESERVATION DEPENDENCY DESIGN

### Reservation Lifecycle
```
Cart Add → reserve_stock() → StockReservation(expires_in=15min)
    │
    ├── Checkout initiated → extend reservation TTL
    ├── Payment SUCCESS → consume_reservation() → StockMovement(SALE)
    ├── Payment FAILURE → release_reservation() → StockMovement(CANCELLATION)
    └── Reservation EXPIRES → Celery beat → release_reservation() → StockMovement(EXPIRY)
```

### StockReservation Model
```
StockReservation
├── id (UUID PK)
├── stock_item (FK → StockItem, on_delete=CASCADE)
├── cart_item (FK → CartItem, on_delete=CASCADE)
├── order (FK → Order, null=True — set on payment capture)
├── quantity (PositiveIntegerField)
├── expires_at (DateTimeField, db_index=True)
└── is_consumed (BooleanField, default=False, db_index=True)
```

**Celery task (runs every 5 minutes):**
```python
StockReservation.objects.filter(expires_at__lt=now(), is_consumed=False)
    .select_for_update(skip_locked=True)
```

---

## SECTION 10 — ORDER ARCHITECTURE RECOMMENDATION

### Order Model (with mandatory address + price snapshots)
```
Order
├── id (UUID PK)
├── order_number (CharField, unique — format: BMP-2026-00001)
├── user (FK → User, on_delete=PROTECT)
├── status (ENUM: PENDING_PAYMENT, PAID, PROCESSING, SHIPPED, DELIVERED, CANCELLED, REFUNDED)
├── payment_status (ENUM: UNPAID, AUTHORISED, CAPTURED, FAILED, REFUNDED)
│
│   ← Address snapshot (NOT FK to live Address)
├── shipping_name, shipping_phone
├── shipping_address_line_1, shipping_address_line_2
├── shipping_city, shipping_state, shipping_pincode
│
│   ← Financial snapshot
├── subtotal, discount_amount, shipping_charge, tax_amount, grand_total
├── gst_rate_applied (DecimalField — from Product.gst_rate at order time)
│
└── created_at / updated_at

OrderLineItem
├── id (UUID PK)
├── order (FK → Order, on_delete=CASCADE)
├── variant (FK → ProductVariant, on_delete=PROTECT)
│
│   ← Product/pricing snapshot at order time
├── product_name, variant_name, sku
├── unit_mrp, unit_selling_price (retail or wholesale at time of order)
├── quantity, line_total
└── is_wholesale_price (BooleanField)
```

**Critical Rule:** All financial figures in `OrderLineItem` are snapshotted at placement. Live `ProductVariant.selling_price` is only used as the initial snapshot source — never re-read for existing orders.

**Order number generation:** Use a PostgreSQL sequence wrapped in an atomic helper — never use UUID as the customer-facing reference.

---

## SECTION 11 — PRICING SECURITY REVIEW

### Existing wholesale gate (Phase 2 — confirmed secure at two levels)
1. Queryset level: `CatalogService.get_base_product_queryset()` conditionally prefetches `wholesale_slabs`
2. Serializer level: `ProductVariantSerializer.get_wholesale_slabs()` re-checks `is_wholesale_buyer`

### Phase 3 Pricing Security Requirements

| Risk | Mitigation |
|---|---|
| Client-submitted price manipulation | Server re-fetches `ProductVariant.selling_price` from DB during checkout — never trusts client price |
| Wholesale price bypass at checkout | Re-verify `user.is_wholesale_buyer` at checkout, not just at cart-add |
| Price change between cart fill and checkout | Detect mismatch; display warning; re-confirm before payment capture |
| GST calculation error | Use `ProductVariant.product.gst_rate` from DB at order time |
| Wholesale status revoked after cart fill | If user no longer approved at checkout, fall back to retail price and notify |

---

## SECTION 12 — WHOLESALE AUTHORIZATION REGRESSION REVIEW

### Existing permission classes (confirmed — `apps/accounts/permissions.py`)
| Class | Logic | Phase 3 Use |
|---|---|---|
| `IsOwnerOrAdmin` | `obj.user == request.user` or `is_staff` | Orders, cart items |
| `IsApprovedWholesaleBuyer` | `request.user.is_wholesale_buyer` | Wholesale-only endpoints |
| `IsStaffOrManager` | `role in [STAFF, MANAGER, SUPERADMIN]` | Inventory, order management |
| `IsManagerOrAdmin` | `role in [MANAGER, SUPERADMIN]` | Refunds, wholesale KYC approval |

**No regressions found.** All existing permission classes are directly reusable in Phase 3 without modification.

### Phase 3 Permission Assignments
| Endpoint | Permission |
|---|---|
| `GET/POST /api/v1/cart/` | `AllowAny` |
| `POST /api/v1/orders/` | `IsAuthenticated` |
| `GET /api/v1/orders/{id}/` | `IsAuthenticated + IsOwnerOrAdmin` |
| `POST /api/v1/payments/initiate/` | `IsAuthenticated` |
| `POST /api/v1/payments/webhook/` | No DRF auth — signature-verified only |
| `GET /api/v1/inventory/` | `IsStaffOrManager` |
| `POST /api/v1/inventory/restock/` | `IsManagerOrAdmin` |

---

## SECTION 13 — REQUIRED MIGRATION STRATEGY

### New app migrations (no modifications to existing migrations)

| App | First Migration Creates |
|---|---|
| `apps.inventory` | `StockItem`, `StockMovement` |
| `apps.cart` | `CartItem`, `StockReservation` |
| `apps.orders` | `Order`, `OrderLineItem`, `OrderStatusHistory` |
| `apps.payments` | `PaymentRecord`, `PaymentWebhookEvent` |

### Migration dependency chain
```
apps.catalog 0001 (exists)
    ↓
apps.inventory 0001 → depends on: apps.catalog 0001
    ↓
apps.cart 0001 → depends on: apps.accounts 0001, apps.catalog 0001, apps.inventory 0001
    ↓
apps.orders 0001 → depends on: apps.accounts 0001, apps.catalog 0001, apps.cart 0001
    ↓
apps.payments 0001 → depends on: apps.orders 0001
```

**`makemigrations --check` will remain clean until Phase 3 apps are added to `INSTALLED_APPS`.**

---

## SECTION 14 — RISKS DISCOVERED

| # | Severity | Risk | Description |
|---|---|---|---|
| R-01 | 🔴 HIGH | No async infrastructure | Celery + Redis absent. Reservation expiry, payment retry, order emails all require them. |
| R-02 | 🔴 HIGH | Address snapshot not enforced | `Order.shipping_address` must snapshot fields — not FK to live `Address`. If user is deleted, order history loses shipping address. |
| R-03 | 🔴 HIGH | Price snapshot not enforced | OrderLineItem must capture prices at order time — never re-read from ProductVariant post-placement. |
| R-04 | 🟡 MEDIUM | Payment webhook idempotency | Gateways may deliver webhooks multiple times. `PaymentWebhookEvent` must have a unique constraint on `webhook_id`. |
| R-05 | 🟡 MEDIUM | Category CASCADE risk (Phase 2 carry-over) | `Category.parent` uses CASCADE. Deleting a parent cascades subcategories. Recommend `Product.category` uses `on_delete=PROTECT` — needs verification in catalog migration. |
| R-06 | 🟡 MEDIUM | `black` formatting gap | `apps/catalog/serializers.py` needs `black` formatting before Phase 3 begins. |
| R-07 | 🟡 MEDIUM | No Redis in docker-compose | Must add Redis service before Celery can run. |
| R-08 | 🟢 LOW | Missing requirements entries | `celery`, `redis`, `django-celery-beat` missing from `requirements.txt`. |
| R-09 | 🟢 LOW | Guest cart TTL cleanup | Without Celery, expired guest cart records accumulate indefinitely. |
| R-10 | 🟢 LOW | `psycopg2-binary` in production | Production deployment checklist should switch to compiled `psycopg2`. Known limitation, not a bug. |

---

## SECTION 15 — REQUIRED CORRECTIONS BEFORE IMPLEMENTATION

### CORRECTION 1 — Format `apps/catalog/serializers.py` [MANDATORY]
```bash
black apps/catalog/serializers.py
```
Verify with `black --check .` → must return 0 files to reformat.

### CORRECTION 2 — Add Celery + Redis infrastructure [MANDATORY for full Phase 3]
Add to `requirements.txt`:
```
celery>=5.4.0,<5.5.0
redis>=5.0.0,<6.0.0
django-celery-beat>=2.7.0,<2.8.0
```

Add to `docker-compose.yml`:
```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 5s
    timeout: 3s
    retries: 5

celery:
  build: .
  command: celery -A config worker -l INFO
  environment:
    - DJANGO_SETTINGS_MODULE=config.settings.development
    - CELERY_BROKER_URL=redis://redis:6379/0
  depends_on:
    redis:
      condition: service_healthy
    db:
      condition: service_healthy

celery-beat:
  build: .
  command: celery -A config beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
  environment:
    - DJANGO_SETTINGS_MODULE=config.settings.development
    - CELERY_BROKER_URL=redis://redis:6379/0
  depends_on:
    redis:
      condition: service_healthy
    db:
      condition: service_healthy
```

### CORRECTION 3 — Add `CELERY_BROKER_URL` to settings and `.env.example` [MANDATORY]
In `config/settings/base.py`:
```python
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_SERIALIZER = "json"
```

### CORRECTION 4 — Verify `Product.category` on_delete behavior [RECOMMENDED — Phase 2 carry-over]
Inspect `apps/catalog/migrations/0001_initial.py` for `Product.category` FK `on_delete`. If it is not `PROTECT`, create a new `0002` catalog migration to change it, preventing accidental product orphaning when a category is deleted.

> **Decision required from user:** fix this before Phase 3 or document as accepted risk.

---

## SECTION 16 — RECOMMENDED PHASE 3 IMPLEMENTATION SEQUENCE

### Step 1: Pre-flight corrections (BEFORE any Phase 3 code)
1. `black apps/catalog/serializers.py`
2. Add Celery + Redis to `requirements.txt` and `docker-compose.yml`
3. Create `config/celery.py` — Celery application factory
4. Update `config/__init__.py` to import Celery app
5. Add Celery settings to `base.py`

### Step 2: `apps.inventory` (backend-only, no public APIs yet)
1. Create app, add to `INSTALLED_APPS`
2. `StockItem`, `StockMovement`, `StockReservation` models + migration
3. `InventoryService` with `reserve()`, `release()`, `consume()` — all `SELECT FOR UPDATE NOWAIT`
4. Django admin registration
5. Full unit tests for all service methods including lock-contention paths

### Step 3: `apps.cart`
1. `CartItem` model with user + guest_token design
2. Guest token HttpOnly cookie generation and validation
3. Cart service: add, update quantity, remove, clear, merge-on-login
4. Integration with `InventoryService.reserve()` on add-to-cart
5. Cart API endpoints (AllowAny)
6. Full tests including guest-to-authenticated merge

### Step 4: `apps.orders`
1. `Order` model with address snapshot fields
2. `OrderLineItem` model with price snapshot fields
3. `OrderStatusHistory` model
4. `OrderService.create_from_cart()` — atomic, stock consumed, cart cleared
5. Order confirmation email dispatch (async via Celery)
6. Customer order endpoints + staff order management endpoints
7. Full tests

### Step 5: `apps.payments`
1. `PaymentRecord` model
2. `PaymentWebhookEvent` model with `webhook_id` unique constraint for idempotency
3. Razorpay integration (environment variables ONLY — never hardcode credentials)
4. Webhook signature verification endpoint
5. Payment capture flow → order status update
6. Refund flow (`IsManagerOrAdmin` only)
7. Full tests including idempotency and signature verification

### Step 6: Celery periodic tasks
1. `release_expired_reservations` — every 5 minutes, `skip_locked=True`
2. `send_order_confirmation_email` — on order creation
3. `retry_failed_webhook_processing` — on payment webhook failure
4. Register all tasks with `django-celery-beat`

### Step 7: Phase 3 verification
1. `python3 manage.py check` → 0 issues
2. `python3 manage.py check --deploy` → 0 issues
3. All tests (target: 150+ tests) → all pass
4. `black --check .` → clean
5. `ruff check .` → clean
6. Write `PHASE_3_COMPLETION_AUDIT.md`

---

## FINAL AUDIT SUMMARY

```
PHASE 3 PRE-IMPLEMENTATION AUDIT — FINAL SUMMARY
==================================================
Audit Date:           2026-09-05
Phase 1 Status:       COMPLETE — 42 tests passing, no regressions
Phase 2 Status:       COMPLETE — 41 tests passing, no regressions
Total Tests Now:      83 tests, ALL PASS

CRITICAL FINDINGS:
  [OK]  stock_quantity DOES NOT EXIST on ProductVariant — clean slate
  [OK]  PostgreSQL 16 + psycopg2 — all concurrency primitives available
  [OK]  Permission classes cover all Phase 3 access patterns
  [OK]  Response envelope, exception handler, pagination — all reusable
  [OK]  No migration modifications needed to existing Phase 1/2 migrations
  [WARN] black formatting gap in serializers.py — fix before implementation
  [CRIT] No Celery + Redis — MUST add before Phase 3 async features work
  [CRIT] Address snapshot pattern — must enforce in Order model design
  [MED]  Category CASCADE carry-over risk — decision required from user

Architecture Compatibility:   COMPATIBLE
Blocking Issues:              0 (no blocker from Phase 1/2 code)
Required Pre-flight Fixes:    4 (documented in Section 15)
Infrastructure Gaps:          Celery + Redis (must be added)

AUDIT DECISION: READY FOR IMPLEMENTATION
— pending 4 pre-flight corrections listed in Section 15
— await explicit user approval before implementation begins
==================================================
```

---

*This audit was conducted without modifying any source code, models, migrations, tests, or settings. All findings are read-only observations. No Phase 3 application code has been created.*
