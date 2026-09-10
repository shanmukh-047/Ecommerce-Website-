"""
Automated End-to-End Verification of Bharat Masala Cart APIs
Tests all 8 cart lifecycle operations against real Django backend.
"""

import os
import sys
from pathlib import Path
from decimal import Decimal
import django

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from apps.cart.views import CartView, CartItemListCreateView, CartItemDetailView
from apps.promotions.views import CartCouponApplyView, CartCouponRemoveView
from apps.catalog.models import ProductVariant
from apps.inventory.models import StockItem
from django.conf import settings

def run_tests():
    rf = RequestFactory()
    passed = 0
    total = 0
    guest_cookie = {}

    print("=" * 60)
    print("BHARAT MASALA SHOPPING CART BACKEND API VERIFICATION")
    print("=" * 60)

    # Pick a test variant with stock
    variant = ProductVariant.objects.filter(is_active=True, stock_item__quantity_on_hand__gt=10).first()
    assert variant is not None, "No active variant with stock found for testing"
    variant_id = str(variant.id)
    unit_selling_price = float(variant.selling_price)

    # Pick a second variant for multi-item testing
    variant2 = ProductVariant.objects.filter(is_active=True, stock_item__quantity_on_hand__gt=10).exclude(id=variant.id).first()
    variant2_id = str(variant2.id)

    # 1. VIEW CART (Initial State)
    total += 1
    req = rf.get('/api/v1/cart/')
    req.user = AnonymousUser()
    req.COOKIES = guest_cookie
    res = CartView.as_view()(req)
    assert res.status_code == 200, f"GET cart failed: {res.status_code}"
    # Capture guest_cart_token cookie from response if set
    if settings.GUEST_CART_COOKIE_NAME in res.cookies:
        guest_cookie[settings.GUEST_CART_COOKIE_NAME] = res.cookies[settings.GUEST_CART_COOKIE_NAME].value
    cart_data = res.data['cart']
    assert 'items' in cart_data and 'items_subtotal' in cart_data
    print(f"[{passed+1}/{total}] PASS: Initial GET /api/v1/cart/ succeeded (items={len(cart_data['items'])}, guest_token={'present' if guest_cookie else 'none'})")
    passed += 1

    # 2. ADD PRODUCT TO CART
    total += 1
    req = rf.post('/api/v1/cart/items/', {'variant_id': variant_id, 'quantity': 2}, content_type='application/json')
    req.user = AnonymousUser()
    req.COOKIES = guest_cookie
    res = CartItemListCreateView.as_view()(req)
    assert res.status_code in [200, 201], f"POST cart/items failed: {res.status_code} - {res.data}"
    if settings.GUEST_CART_COOKIE_NAME in res.cookies:
        guest_cookie[settings.GUEST_CART_COOKIE_NAME] = res.cookies[settings.GUEST_CART_COOKIE_NAME].value
    cart_data = res.data['cart']
    item = next((i for i in cart_data['items'] if str(i['variant_id']) == variant_id), None)
    assert item is not None, f"Variant {variant_id} not found in cart"
    item_id = str(item['id'])
    assert item['quantity'] >= 2
    expected_line_total = float(item['unit_price']) * item['quantity']
    assert float(item['line_total']) == expected_line_total
    print(f"[{passed+1}/{total}] PASS: POST /api/v1/cart/items/ added {variant.product.name} ({item['quantity']} units, line_total=₹{item['line_total']})")
    passed += 1

    # 3. ADD SECOND ITEM (To reach min_order_value for coupon)
    total += 1
    req = rf.post('/api/v1/cart/items/', {'variant_id': variant2_id, 'quantity': 2}, content_type='application/json')
    req.user = AnonymousUser()
    req.COOKIES = guest_cookie
    res = CartItemListCreateView.as_view()(req)
    assert res.status_code in [200, 201]
    cart_data = res.data['cart']
    assert len(cart_data['items']) >= 2
    item2 = next(i for i in cart_data['items'] if str(i['variant_id']) == variant2_id)
    item2_id = str(item2['id'])
    print(f"[{passed+1}/{total}] PASS: POST /api/v1/cart/items/ added second variant (total subtotal=₹{cart_data['items_subtotal']})")
    passed += 1

    # 4. UPDATE QUANTITY
    total += 1
    req = rf.patch(f'/api/v1/cart/items/{item_id}/', {'quantity': 3}, content_type='application/json')
    req.user = AnonymousUser()
    req.COOKIES = guest_cookie
    res = CartItemDetailView.as_view()(req, pk=item_id)
    assert res.status_code == 200, f"PATCH cart/items/{item_id}/ failed: {res.status_code} - {res.data}"
    cart_data = res.data['cart']
    updated_item = next(i for i in cart_data['items'] if str(i['id']) == item_id)
    assert updated_item['quantity'] == 3
    print(f"[{passed+1}/{total}] PASS: PATCH /api/v1/cart/items/{item_id}/ updated quantity to 3 (subtotal=₹{cart_data['items_subtotal']})")
    passed += 1

    # 5. APPLY PROMOTIONAL COUPON (WELCOME50)
    total += 1
    req = rf.post('/api/v1/cart/coupon/', {'code': 'WELCOME50'}, content_type='application/json')
    req.user = AnonymousUser()
    req.COOKIES = guest_cookie
    res = CartCouponApplyView.as_view()(req)
    assert res.status_code == 200, f"POST cart/coupon/ failed: {res.status_code} - {res.data}"
    cart_data = res.data['cart']
    assert cart_data['applied_coupon_code'] == 'WELCOME50'
    discount = float(cart_data['discount_amount'])
    assert discount == 50.0, f"Expected discount 50.0, got {discount}"
    net = float(cart_data['net_subtotal'])
    items_subtotal = float(cart_data['items_subtotal'])
    assert abs(net - (items_subtotal - discount)) < 0.01, f"Net {net} != Subtotal {items_subtotal} - Discount {discount}"
    print(f"[{passed+1}/{total}] PASS: POST /api/v1/cart/coupon/ applied 'WELCOME50' (discount=₹{discount}, net_subtotal=₹{net})")
    passed += 1

    # 6. REMOVE PROMOTIONAL COUPON
    total += 1
    req = rf.delete('/api/v1/cart/coupon/')
    req.user = AnonymousUser()
    req.COOKIES = guest_cookie
    res = CartCouponApplyView.as_view()(req)
    assert res.status_code == 200, f"DELETE cart/coupon/ failed: {res.status_code}"
    cart_data = res.data['cart']
    assert cart_data['applied_coupon_code'] is None
    assert float(cart_data['discount_amount']) == 0.0
    print(f"[{passed+1}/{total}] PASS: DELETE /api/v1/cart/coupon/ removed coupon (discount reverted to ₹0.00)")
    passed += 1

    # 7. REMOVE SINGLE ITEM LINE
    total += 1
    req = rf.delete(f'/api/v1/cart/items/{item2_id}/')
    req.user = AnonymousUser()
    req.COOKIES = guest_cookie
    res = CartItemDetailView.as_view()(req, pk=item2_id)
    assert res.status_code == 200, f"DELETE cart/items/{item2_id}/ failed: {res.status_code}"
    cart_data = res.data['cart']
    assert not any(str(i['id']) == item2_id for i in cart_data['items'])
    print(f"[{passed+1}/{total}] PASS: DELETE /api/v1/cart/items/{item2_id}/ removed item (remaining items={len(cart_data['items'])})")
    passed += 1

    # 8. CLEAR ENTIRE CART
    total += 1
    req = rf.delete('/api/v1/cart/')
    req.user = AnonymousUser()
    req.COOKIES = guest_cookie
    res = CartView.as_view()(req)
    assert res.status_code == 200, f"DELETE /api/v1/cart/ failed: {res.status_code}"
    cart_data = res.data['cart']
    assert len(cart_data['items']) == 0
    assert float(cart_data['items_subtotal']) == 0.0
    print(f"[{passed+1}/{total}] PASS: DELETE /api/v1/cart/ cleared basket (items=0, subtotal=₹0.00)")
    passed += 1

    # 9. INVENTORY STOCK CONFLICT TEST (Attempt to add quantity > stock_available)
    total += 1
    stock = StockItem.objects.get(variant=variant)
    excess_qty = stock.quantity_available + 100
    req = rf.post('/api/v1/cart/items/', {'variant_id': variant_id, 'quantity': excess_qty}, content_type='application/json')
    req.user = AnonymousUser()
    req.COOKIES = guest_cookie
    res = CartItemListCreateView.as_view()(req)
    assert res.status_code == 409, f"Expected 409 Conflict, got {res.status_code}"
    assert "Insufficient inventory" in str(res.data)
    print(f"[{passed+1}/{total}] PASS: Inventory limit enforced: adding {excess_qty} units returned 409 Conflict as expected")
    passed += 1

    print("=" * 60)
    print(f"ALL {passed}/{total} CART BACKEND INTEGRATION TESTS PASSED CLEANLY!")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
