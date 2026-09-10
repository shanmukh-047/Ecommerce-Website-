# scratch/test_phase5_customer_apis.py
import urllib.request
import urllib.error
import json
import http.cookiejar
import time

COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))

def req(url, method="GET", data=None, token=None):
    hdrs = {"Accept": "application/json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    req_body = None
    if data is not None:
        hdrs["Content-Type"] = "application/json"
        req_body = json.dumps(data).encode("utf-8")
    
    request = urllib.request.Request(url, data=req_body, headers=hdrs, method=method)
    try:
        with OPENER.open(request) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}
        return err.code, parsed

def run_customer_api_audit():
    print("======================================================================")
    print("PHASE 5: COMPREHENSIVE CUSTOMER API AUDIT MATRIX")
    print("======================================================================")
    
    BASE = "http://localhost:3000/api/v1"
    matrix = []

    def record(category, method, endpoint, auth_req, req_data, status, expected_status, note=""):
        passed = (status == expected_status)
        matrix.append({
            "category": category,
            "method": method,
            "url": f"/api/v1{endpoint}",
            "auth": auth_req,
            "status": status,
            "expected": expected_status,
            "pass": passed,
            "note": note
        })
        print(f"[{'PASS' if passed else 'FAIL'}] {method:6} {endpoint:45} | Got {status} (Expected {expected_status}) | {note}")
        return passed

    # 1. AUTH: Register
    ts = int(time.time())
    email = f"cust_api_test_{ts}@example.com"
    phone = f"+9198{ts % 100000000:08d}"
    status, res = req(f"{BASE}/auth/register/", "POST", {
        "email": email,
        "password": "CustomerPass@123",
        "confirm_password": "CustomerPass@123",
        "phone_number": phone,
        "first_name": "API",
        "last_name": "Tester"
    })
    token = res.get("data", {}).get("access_token")
    user_id = res.get("data", {}).get("user", {}).get("id")
    record("AUTH", "POST", "/auth/register/", False, "{...}", status, 201, "Created customer account")

    # 2. AUTH: Login
    status, res = req(f"{BASE}/auth/login/", "POST", {
        "email": email,
        "password": "CustomerPass@123"
    })
    token = res.get("data", {}).get("access_token") or token
    record("AUTH", "POST", "/auth/login/", False, "{email, password}", status, 200, "Issued access token")

    # 3. AUTH: Refresh
    status, res = req(f"{BASE}/auth/token/refresh/", "POST", {})
    new_token = res.get("data", {}).get("access_token")
    if new_token:
        token = new_token
    record("AUTH", "POST", "/auth/token/refresh/", False, "{}", status, 200, "Rotated access token")

    # 4. AUTH: Me
    status, res = req(f"{BASE}/auth/me/", "GET", token=token)
    record("AUTH", "GET", "/auth/me/", True, None, status, 200, f"Profile for {email}")

    # 5. ACCOUNT: Update Me
    status, res = req(f"{BASE}/auth/me/", "PATCH", {"first_name": "UpdatedAPI"}, token=token)
    record("ACCOUNT", "PATCH", "/auth/me/", True, "{first_name}", status, 200, "Updated customer name")

    # 6. ACCOUNT: Add Address
    addr_payload = {
        "recipient_name": "API Tester",
        "phone_number": "+919876543210",
        "address_line_1": "Flat 402, Nilgiri Heights",
        "address_line_2": "MG Road",
        "city": "Bengaluru",
        "state": "KA",
        "pincode": "560001",
        "address_type": "HOME",
        "is_default_shipping": True
    }
    status, res = req(f"{BASE}/auth/addresses/", "POST", addr_payload, token=token)
    addr_id = res.get("data", {}).get("id")
    record("ACCOUNT", "POST", "/auth/addresses/", True, "{address}", status, 201, "Added shipping address")

    # 7. ACCOUNT: List Addresses
    status, res = req(f"{BASE}/auth/addresses/", "GET", token=token)
    record("ACCOUNT", "GET", "/auth/addresses/", True, None, status, 200, f"Retrieved addresses (count: {len(res.get('data', []))})")

    # 8. ACCOUNT: Set Default Address
    if addr_id:
        status, res = req(f"{BASE}/auth/addresses/{addr_id}/set-default/", "POST", {}, token=token)
        record("ACCOUNT", "POST", f"/auth/addresses/:id/set-default/", True, "{}", status, 200, "Default address set")

    # 9. CATALOG: Categories
    status, res = req(f"{BASE}/catalog/categories/", "GET")
    categories = res.get("data", [])
    record("CATALOG", "GET", "/catalog/categories/", False, None, status, 200, f"Categories retrieved: {len(categories)}")

    # 10. CATALOG: Products
    status, res = req(f"{BASE}/catalog/products/", "GET")
    products = res.get("data", {}).get("results", []) if isinstance(res.get("data"), dict) else res.get("data", [])
    record("CATALOG", "GET", "/catalog/products/", False, None, status, 200, f"Products returned: {len(products)}")

    # 11. CATALOG: Product Detail
    first_slug = products[0]["slug"] if products else "salem-pure-turmeric-powder"
    status, res = req(f"{BASE}/catalog/products/{first_slug}/", "GET")
    product_detail = res.get("data", {})
    variants = product_detail.get("variants", [])
    variant_id = variants[0]["id"] if variants else None
    record("CATALOG", "GET", f"/catalog/products/:slug/", False, None, status, 200, f"Loaded detail for {first_slug}")

    # 12. CATALOG: Search
    status, res = req(f"{BASE}/catalog/products/?search=turmeric", "GET")
    record("CATALOG", "GET", "/catalog/products/?search=turmeric", False, None, status, 200, "Search query executed")

    # 13. CATALOG: Category Filter
    status, res = req(f"{BASE}/catalog/products/?category=pure-spices", "GET")
    record("CATALOG", "GET", "/catalog/products/?category=pure-spices", False, None, status, 200, "Category filter executed")

    # 14. CATALOG: Reviews
    status, res = req(f"{BASE}/catalog/products/{first_slug}/reviews/", "GET")
    record("CATALOG", "GET", f"/catalog/products/:slug/reviews/", False, None, status, 200, "Retrieved reviews")

    # 15. CART: Get Cart
    status, res = req(f"{BASE}/cart/", "GET", token=token)
    record("CART", "GET", "/cart/", False, None, status, 200, "User cart loaded")

    # 16. CART: Add Item
    cart_item_id = None
    if variant_id:
        status, res = req(f"{BASE}/cart/items/", "POST", {"variant_id": variant_id, "quantity": 2}, token=token)
        cart_data = res.get("data", {}).get("cart", {}) or res.get("data", {})
        items = cart_data.get("items", [])
        if items:
            cart_item_id = items[0]["id"]
        record("CART", "POST", "/cart/items/", False, "{variant_id, quantity}", status, 200, f"Item added to basket")

    # 17. CART: Update Quantity
    if cart_item_id:
        status, res = req(f"{BASE}/cart/items/{cart_item_id}/", "PATCH", {"quantity": 3}, token=token)
        record("CART", "PATCH", f"/cart/items/:id/", False, "{quantity: 3}", status, 200, "Quantity updated to 3")

    # 18. ORDERS: Checkout Order Creation
    order_id = None
    if addr_id:
        checkout_payload = {
            "shipping_address_id": addr_id,
            "billing_address_id": addr_id,
            "payment_method": "ONLINE",
            "customer_notes": "Handle with care, single origin spices"
        }
        status, res = req(f"{BASE}/orders/checkout/", "POST", checkout_payload, token=token)
        order_data = res.get("data", {}).get("order", {}) or res.get("data", {})
        order_id = order_data.get("id")
        record("ORDERS", "POST", "/orders/checkout/", True, "{checkout_payload}", status, 201, f"Order created: {order_id}")

    # 19. ORDERS: Orders List
    status, res = req(f"{BASE}/orders/", "GET", token=token)
    record("ORDERS", "GET", "/orders/", True, None, status, 200, "Customer order list retrieved")

    # 20. ORDERS: Order Detail
    if order_id:
        status, res = req(f"{BASE}/orders/{order_id}/", "GET", token=token)
        record("ORDERS", "GET", f"/orders/:id/", True, None, status, 200, f"Order detail loaded for {order_id}")

    # 21. PAYMENTS: Razorpay Order Initiation
    if order_id:
        status, res = req(f"{BASE}/payments/orders/{order_id}/initiate/", "POST", {}, token=token)
        record("PAYMENTS", "POST", f"/payments/orders/:id/initiate/", True, "{}", status, 201, "Razorpay gateway initiated (201 Created)")

    # 22. PAYMENTS: Payment Detail
    if order_id:
        status, res = req(f"{BASE}/payments/orders/{order_id}/", "GET", token=token)
        record("PAYMENTS", "GET", f"/payments/orders/:id/", True, None, status, 200, "Payment record loaded")

    # 23. PAYMENTS: COD Order Flow
    # Add another item to cart and create COD order
    if variant_id and addr_id:
        req(f"{BASE}/cart/items/", "POST", {"variant_id": variant_id, "quantity": 1}, token=token)
        status, res = req(f"{BASE}/orders/checkout/", "POST", {
            "shipping_address_id": addr_id,
            "billing_address_id": addr_id,
            "payment_method": "COD",
            "customer_notes": "Pay on delivery order"
        }, token=token)
        cod_order_id = (res.get("data", {}).get("order", {}) or res.get("data", {})).get("id")
        if cod_order_id:
            status, res = req(f"{BASE}/payments/orders/{cod_order_id}/cod/", "POST", {}, token=token)
            record("PAYMENTS", "POST", f"/payments/orders/:id/cod/", True, "{}", status, 201, f"COD payment confirmed for {cod_order_id} (201 Created)")

    # 24. SHIPPING: Public Tracking (404 expected for non-existent AWB)
    status, res = req(f"{BASE}/shipping/track/?awb=DELHIVERY12345", "GET")
    record("SHIPPING", "GET", "/shipping/track/?awb=...", False, None, status, 404, "Correct 404 Not Found for non-existent AWB")

    # 25. AUTH: Logout
    status, res = req(f"{BASE}/auth/logout/", "POST", {}, token=token)
    record("AUTH", "POST", "/auth/logout/", True, "{}", status, 200, "Session terminated cleanly")

    print("\n======================================================================")
    total = len(matrix)
    passed = sum(1 for m in matrix if m["pass"])
    print(f"CUSTOMER API AUDIT COMPLETE: {passed}/{total} PASSED ({(passed/total)*100:.1f}%)")
    print("======================================================================")

if __name__ == "__main__":
    run_customer_api_audit()
