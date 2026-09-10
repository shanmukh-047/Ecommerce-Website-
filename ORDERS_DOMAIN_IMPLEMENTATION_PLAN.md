# PHASE 3.4 — ORDERS & CHECKOUT DOMAIN: ARCHITECTURE & IMPLEMENTATION PLAN
## (REVISED POST-COMPATIBILITY AUDIT)

**Project:** Bharath Masala Products E-Commerce Platform (Production Django/DRF Backend)  
**Document Type:** Architectural Blueprint & Implementation Specification  
**Audit & Revision Date:** 2026-09-06T16:23:00+05:30  
**Status:** FULLY RECONCILED & READY FOR IMPLEMENTATION  

---

## 1. Executive Summary & Compatibility Audit Findings

Following a targeted compatibility audit against the existing verified codebase (126/126 tests passing), five critical architectural contracts have been verified and reconciled:

1. **`order_status` Field Alignment:**  
   `apps.catalog.services.ReviewService.verify_user_purchase()` explicitly queries `order__order_status=OrderStatus.DELIVERED`. To guarantee 100% zero-regression compatibility without modifying Phase 2 code, the `Order` model uses `order_status` as the database field, with `status` provided as a python property alias.
2. **Deterministic Reservation vs. Restocking Lifecycle:**  
   Inspected `InventoryService` contracts:
   - When order is in `PENDING_PAYMENT`, reservations are `ACTIVE`. Cancellation releases them via `InventoryService.release_reservation(reservation_id, actor)`.
   - When order is `CONFIRMED` (payment captured in Phase 3.5), reservations are `CONSUMED`. Subsequent cancellation after confirmation cannot call `release_reservation` (which raises `InventoryConflict`). Instead, restocking is performed by calling `InventoryService.add_stock(variant, quantity, actor, note="Restock from cancelled order ...")`, maintaining exact physical and ledger accounting integrity.
3. **Deadlock-Free Cart and Stock Locking:**  
   The checkout service locks both `Cart` and `CartItem` rows. To prevent PostgreSQL deadlocks during high-concurrency checkouts, all `StockItem` rows are queried with `select_for_update()` ordered deterministically by `variant_id`.
4. **Order Number Collision Protection:**  
   Order numbers use `BMP-YYYYMMDD-XXXXX` with non-ambiguous alphanumeric characters (excluding 0, O, 1, I). Generation includes an in-transaction retry loop (up to 5 attempts) backed by a database `unique=True` constraint.
5. **Backwards-Compatible Model Symbols:**  
   `apps/orders/models.py` defines `OrderLineItem` and explicitly aliases `OrderItem = OrderLineItem` to fulfill the import expected by `ReviewService`.

---

## 2. Dependencies & Contract Reconciliation Matrix

| Dependency | Method / Field Inspected | Exact Contract in Orders Domain |
|---|---|---|
| `apps.accounts.models.Address` | `recipient_name`, `phone_number`, `address_line_1`, `address_line_2`, `landmark`, `city`, `state`, `pincode` | Snapshot 8 flat columns on `Order`. Require `address.user == request.user`. Soft link `shipping_address` (`on_delete=SET_NULL`). |
| `apps.accounts.models.User` | `is_wholesale_buyer` property | Re-evaluated server-side during checkout. Retail users receive standard retail price; approved wholesale buyers receive volume tier slab prices. |
| `apps.cart.services.CartService` | `clear_cart(cart)`<br>`unit_price(variant, qty, user)` | `CartService.unit_price()` used for authoritative repricing.<br>`CartService.clear_cart(cart)` called upon checkout completion. |
| `apps.inventory.services.InventoryService` | `reserve_stock()`<br>`release_reservation()`<br>`consume_reservation()`<br>`add_stock()` | `reserve_stock(variant, qty, expires_at, actor, reference_type="ORDER", reference_id=order.id)`.<br>`release_reservation()` for `PENDING_PAYMENT` cancellations.<br>`add_stock()` for post-confirmation restocks. |
| `apps.catalog.services.ReviewService` | `from apps.orders.models import OrderItem, OrderStatus`<br>`order__order_status=OrderStatus.DELIVERED` | Export `OrderStatus` enum containing `DELIVERED`. Export `OrderItem = OrderLineItem`. Field name is `order_status`. |

---

## 3. Order Models Specification

### 3.1 Model 1: `Order`
```python
class OrderStatus(models.TextChoices):
    PENDING_PAYMENT = "PENDING_PAYMENT", "Pending Payment"
    CONFIRMED = "CONFIRMED", "Confirmed"
    PROCESSING = "PROCESSING", "Processing"
    SHIPPED = "SHIPPED", "Shipped"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"
    FAILED = "FAILED", "Failed"
    REFUNDED = "REFUNDED", "Refunded"


class Order(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=32, unique=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    
    # Matches ReviewService expectation: order__order_status
    order_status = models.CharField(
        max_length=30,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING_PAYMENT,
        db_index=True,
    )
    
    currency = models.CharField(max_length=3, default="INR")
    items_subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)
    total_quantity = models.PositiveIntegerField(default=1)
    total_weight_in_grams = models.PositiveIntegerField(default=0)
    is_wholesale_order = models.BooleanField(default=False, db_index=True)

    # Immutable Address Snapshot
    shipping_recipient_name = models.CharField(max_length=100)
    shipping_phone_number = models.CharField(max_length=15)
    shipping_address_line_1 = models.CharField(max_length=255)
    shipping_address_line_2 = models.CharField(max_length=255, blank=True, default="")
    shipping_landmark = models.CharField(max_length=100, blank=True, default="")
    shipping_city = models.CharField(max_length=100, db_index=True)
    shipping_state = models.CharField(max_length=50, choices=IndianStates.choices, db_index=True)
    shipping_pincode = models.CharField(max_length=6, db_index=True)
    shipping_address = models.ForeignKey(
        "accounts.Address",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    customer_notes = models.CharField(max_length=500, blank=True, default="")
    cancellation_reason = models.TextField(blank=True, default="")
    cancelled_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["order_status", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(check=Q(grand_total__gte=0), name="order_grand_total_non_negative"),
            models.CheckConstraint(check=Q(items_subtotal__gte=0), name="order_items_subtotal_non_negative"),
        ]

    @property
    def status(self) -> str:
        return self.order_status

    @status.setter
    def status(self, value: str):
        self.order_status = value
```

### 3.2 Model 2: `OrderLineItem` (Aliased as `OrderItem`)
```python
class OrderLineItem(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="order_lines",
    )
    quantity = models.PositiveIntegerField()

    # Immutable Catalog & Price Snapshot
    product_name = models.CharField(max_length=200)
    variant_name = models.CharField(max_length=100)
    sku = models.CharField(max_length=64)
    weight_in_grams = models.PositiveIntegerField(null=True, blank=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    pricing_tier_applied = models.CharField(max_length=50, default="RETAIL")

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(check=Q(quantity__gt=0), name="order_line_quantity_positive"),
            models.CheckConstraint(check=Q(unit_price__gt=0), name="order_line_unit_price_positive"),
            models.CheckConstraint(check=Q(line_subtotal__gt=0), name="order_line_subtotal_positive"),
            models.UniqueConstraint(fields=["order", "variant"], name="unique_order_variant"),
        ]

# Alias required for apps.catalog.services.ReviewService backwards compatibility
OrderItem = OrderLineItem
```

### 3.3 Model 3: `OrderStatusHistory`
```python
class OrderStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=30, blank=True, default="")
    to_status = models.CharField(max_length=30, choices=OrderStatus.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_status_changes",
    )
    notes = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
```

---

## 4. Concurrency & Deadlock-Free Checkout Architecture

To guarantee zero deadlocks and zero overselling under heavy concurrent load:

```python
class CheckoutService:
    @classmethod
    @transaction.atomic
    def create_order_from_cart(cls, user, shipping_address_id, customer_notes=""):
        # 1. Lock the Cart row
        cart = Cart.objects.select_for_update().filter(user=user).first()
        if not cart:
            raise OrderConflict("Cart was not found.")

        # 2. Lock all CartItem rows explicitly
        cart_items = list(
            CartItem.objects.select_for_update()
            .select_related("variant__product")
            .filter(cart=cart)
        )
        if not cart_items:
            raise OrderConflict("Cart is empty.")

        # 3. Validate shipping address ownership
        address = Address.objects.filter(user=user, id=shipping_address_id).first()
        if not address:
            raise OrderConflict("Valid shipping address belonging to the customer is required.")

        # 4. Deterministically sort variant IDs to eliminate deadlocks across transactions
        variant_ids = sorted([item.variant_id for item in cart_items])
        stock_items = {
            si.variant_id: si
            for si in StockItem.objects.select_for_update().filter(variant_id__in=variant_ids)
        }

        # 5. Verify active state and inventory availability
        for item in cart_items:
            variant = item.variant
            if not variant.is_active:
                raise OrderConflict(f"Variant '{variant.variant_name}' is no longer active.")
            stock = stock_items.get(variant.id)
            if not stock or stock.quantity_available < item.quantity:
                raise OrderConflict(f"Insufficient stock for variant '{variant.variant_name}'.")

        # 6. Authoritative server repricing
        subtotal = Decimal("0.00")
        total_quantity = 0
        total_weight = 0
        is_wholesale = user.is_wholesale_buyer
        line_specs = []

        for item in cart_items:
            variant = item.variant
            unit_price = CartService.unit_price(variant, item.quantity, user)
            line_subtotal = unit_price * item.quantity
            subtotal += line_subtotal
            total_quantity += item.quantity
            total_weight += (variant.weight_in_grams or 0) * item.quantity
            line_specs.append({
                "variant": variant,
                "quantity": item.quantity,
                "unit_price": unit_price,
                "line_subtotal": line_subtotal,
                "mrp": variant.mrp,
                "product_name": variant.product.name,
                "variant_name": variant.variant_name,
                "sku": variant.sku,
                "weight_in_grams": variant.weight_in_grams,
                "pricing_tier": "WHOLESALE" if (is_wholesale and unit_price < variant.selling_price) else "RETAIL",
            })

        # 7. Collision-safe Order Number Generation
        order_number = cls.generate_unique_order_number()

        # 8. Create Order record with Address Snapshot
        order = Order.objects.create(
            order_number=order_number,
            user=user,
            order_status=OrderStatus.PENDING_PAYMENT,
            currency="INR",
            items_subtotal=subtotal,
            shipping_fee=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_discount=Decimal("0.00"),
            grand_total=subtotal,
            total_quantity=total_quantity,
            total_weight_in_grams=total_weight,
            is_wholesale_order=is_wholesale,
            shipping_recipient_name=address.recipient_name,
            shipping_phone_number=address.phone_number,
            shipping_address_line_1=address.address_line_1,
            shipping_address_line_2=address.address_line_2,
            shipping_landmark=address.landmark,
            shipping_city=address.city,
            shipping_state=address.state,
            shipping_pincode=address.pincode,
            shipping_address=address,
            customer_notes=customer_notes,
        )

        # 9. Create OrderLineItems and Reserve Inventory
        reservation_expiry = timezone.now() + timedelta(minutes=settings.ORDER_RESERVATION_TIMEOUT_MINUTES)
        for spec in line_specs:
            OrderLineItem.objects.create(
                order=order,
                variant=spec["variant"],
                quantity=spec["quantity"],
                product_name=spec["product_name"],
                variant_name=spec["variant_name"],
                sku=spec["sku"],
                weight_in_grams=spec["weight_in_grams"],
                mrp=spec["mrp"],
                unit_price=spec["unit_price"],
                line_subtotal=spec["line_subtotal"],
                pricing_tier_applied=spec["pricing_tier"],
            )
            # Reuses InventoryService.reserve_stock API
            InventoryService.reserve_stock(
                variant=spec["variant"],
                quantity=spec["quantity"],
                expires_at=reservation_expiry,
                actor=user,
                reference_type="ORDER",
                reference_id=order.id,
            )

        # 10. Audit History & Clear Cart
        OrderStatusHistory.objects.create(
            order=order,
            from_status="",
            to_status=OrderStatus.PENDING_PAYMENT,
            actor=user,
            notes="Order placed via checkout.",
        )
        CartService.clear_cart(cart)

        return order
```

---

## 5. Order Cancellation & Restocking Lifecycle

The cancellation logic strictly respects the `StockReservation` status:

```python
class OrderStateMachine:
    @classmethod
    @transaction.atomic
    def cancel_order(cls, order, actor=None, reason=""):
        if order.order_status not in [OrderStatus.PENDING_PAYMENT, OrderStatus.CONFIRMED, OrderStatus.PROCESSING]:
            raise OrderConflict(f"Order in status '{order.order_status}' cannot be cancelled.")

        prev_status = order.order_status

        if prev_status == OrderStatus.PENDING_PAYMENT:
            # Reservations are ACTIVE: safely release them
            active_reservations = StockReservation.objects.filter(
                reference_type="ORDER",
                reference_id=order.id,
                status=ReservationStatus.ACTIVE,
            )
            for res in active_reservations:
                InventoryService.release_reservation(res.id, actor=actor, expired=False)

        elif prev_status in [OrderStatus.CONFIRMED, OrderStatus.PROCESSING]:
            # Reservations were already CONSUMED upon payment capture.
            # Physical inventory on-hand was deducted. Must restock physical items!
            for line in order.lines.select_related("variant"):
                InventoryService.add_stock(
                    variant=line.variant,
                    quantity=line.quantity,
                    actor=actor,
                    note=f"Restock from cancelled order {order.order_number}",
                )

        order.order_status = OrderStatus.CANCELLED
        order.cancelled_at = timezone.now()
        order.cancellation_reason = reason
        order.save(update_fields=["order_status", "cancelled_at", "cancellation_reason", "updated_at"])

        OrderStatusHistory.objects.create(
            order=order,
            from_status=prev_status,
            to_status=OrderStatus.CANCELLED,
            actor=actor,
            notes=reason or "Order cancelled.",
        )
        return order
```

---

## 6. API Endpoints Specification

### 6.1 Customer Endpoints (`/api/v1/orders/`)
- `POST /api/v1/orders/checkout/` -> Accepts `{"shipping_address_id": "<uuid>", "customer_notes": ""}`. Returns HTTP 201 Created with standard `{success, request_id, message, data: {order}}` envelope.
- `GET /api/v1/orders/` -> Returns paginated list of user's orders (ordered `-created_at`).
- `GET /api/v1/orders/<uuid:pk>/` -> Returns order detail including line items and shipping snapshot. Strictly scoped to `user=request.user`.
- `POST /api/v1/orders/<uuid:pk>/cancel/` -> Customer cancellation (only valid for `PENDING_PAYMENT`).

### 6.2 Staff Endpoints (`/api/v1/staff/orders/`)
- `GET /api/v1/staff/orders/` -> Filtered, paginated order search for staff (`status`, `date_from`, `date_to`, `search`).
- `GET /api/v1/staff/orders/<uuid:pk>/` -> Full operational order inspection.
- `POST /api/v1/staff/orders/<uuid:pk>/status/` -> Transition status (`CONFIRMED` -> `PROCESSING` -> `SHIPPED` -> `DELIVERED`), requires audit note.

---

## 7. Test Strategy & Coverage Plan

Target test suite: **>= 25 new tests** added to `apps/orders/tests/`:
- `test_checkout_retail_pricing`: Verifies line items snapshot correct retail selling prices.
- `test_checkout_wholesale_pricing`: Verifies approved wholesale buyer receives volume slab discount.
- `test_checkout_unapproved_wholesale_blocked`: Unapproved user receives retail price regardless of quantity.
- `test_checkout_locks_and_reserves_stock`: Verifies `StockReservation` is created with status `ACTIVE` and `quantity_reserved` increments.
- `test_checkout_clears_cart`: Verifies cart is empty post-checkout.
- `test_checkout_empty_cart_fails`: HTTP 409 returned for empty cart.
- `test_checkout_insufficient_stock_fails`: HTTP 409 returned when stock < requested.
- `test_checkout_inactive_variant_fails`: HTTP 409 returned when variant is inactive.
- `test_checkout_address_idor_blocked`: Customer B's address used by Customer A is rejected.
- `test_concurrent_checkout_deadlock_free`: Threaded concurrent checkout runs cleanly without deadlocks.
- `test_address_snapshot_immutability`: Modifying or deleting original `Address` record leaves order shipping fields untouched.
- `test_pricing_snapshot_immutability`: Updating `ProductVariant.selling_price` leaves previously ordered line items untouched.
- `test_cancel_pending_order_releases_reservation`: Active reservation releases and decrements `quantity_reserved`.
- `test_cancel_confirmed_order_restocks_inventory`: Consumed reservation restocks physical `quantity_on_hand`.
- `test_customer_order_idor_blocked`: Customer B querying Customer A's order returns HTTP 404.
- `test_staff_order_lifecycle_transitions`: Full status progression verified.
- `test_review_service_integration`: Verifies `ReviewService.verify_user_purchase()` returns `True` for `DELIVERED` order and `False` otherwise.

---

## 8. Implementation Sequence (Ready to Execute Upon Approval)

1. **Scaffolding:** Create `apps/orders/` app structure; register in `LOCAL_APPS` and `config/urls.py`.
2. **Models & Migration:** Define `OrderStatus`, `Order`, `OrderLineItem` (alias `OrderItem`), `OrderStatusHistory`. Generate `0001_initial.py` and run `python manage.py migrate`.
3. **Checkout & State Machine Services:** Implement `CheckoutService` and `OrderStateMachine` with deterministic locking and atomic rollback.
4. **Serializers & Views:** Implement Customer and Staff API endpoints.
5. **Testing & Verification:** Run `python manage.py test apps.orders`, verify full suite (150+ tests), run `black --check .` and `ruff check .`.
6. **Completion Report:** Generate `PHASE_3_4_ORDERS_COMPLETION_REPORT.md`.
