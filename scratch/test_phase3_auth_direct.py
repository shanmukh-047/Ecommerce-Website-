# scratch/test_phase3_auth_direct.py
import urllib.request
import urllib.error
import json
import http.cookiejar

COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))

def make_request(url, method="GET", data=None, headers=None):
    hdrs = {"Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    req_body = None
    if data is not None:
        hdrs["Content-Type"] = "application/json"
        req_body = json.dumps(data).encode("utf-8")
    
    req = urllib.request.Request(url, data=req_body, headers=hdrs, method=method)
    try:
        with OPENER.open(req) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
            return status, json.loads(body) if body else {}, resp.headers
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}
        return err.code, parsed, err.headers

def run_tests():
    print("==================================================")
    print("PHASE 3 — DIRECT AUTHENTICATION VERIFICATION")
    print("==================================================")
    
    base_url = "http://localhost:3000/api/v1"
    
    # 1. Register
    reg_email = f"phase3_customer_{urllib.request.time.time():.0f}@example.com"
    reg_phone = f"+91987654{int(urllib.request.time.time()) % 10000:04d}"
    print(f"\n[TEST 1] POST {base_url}/auth/register/ (without explicit confirm_password)")
    status, body, headers = make_request(
        f"{base_url}/auth/register/",
        method="POST",
        data={
            "email": reg_email,
            "password": "Phase3Password@123",
            "phone_number": reg_phone,
            "first_name": "Phase3",
            "last_name": "Customer",
        }
    )
    print(f"Status: {status} (Expected: 201)")
    print(f"Success: {body.get('success')}")
    print(f"Has Access Token: {bool(body.get('data', {}).get('access_token'))}")
    assert status == 201, f"Expected 201, got {status}: {body}"
    access_token = body["data"]["access_token"]
    
    # Verify refresh token cookie
    cookies = {c.name: c.value for c in COOKIE_JAR}
    print(f"Refresh Token Cookie set: {'refresh_token' in cookies}")
    assert 'refresh_token' in cookies, "Missing refresh_token cookie"
    
    # 2. Get Me
    print(f"\n[TEST 2] GET {base_url}/auth/me/ (with access token)")
    status, body, _ = make_request(
        f"{base_url}/auth/me/",
        method="GET",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    print(f"Status: {status} (Expected: 200)")
    print(f"Email: {body.get('data', {}).get('email')}")
    assert status == 200, f"Expected 200, got {status}: {body}"
    assert body["data"]["email"] == reg_email
    
    # 3. Token Refresh
    print(f"\n[TEST 3] POST {base_url}/auth/token/refresh/ (using cookie)")
    status, body, _ = make_request(
        f"{base_url}/auth/token/refresh/",
        method="POST",
        data={}
    )
    print(f"Status: {status} (Expected: 200)")
    print(f"New Access Token: {bool(body.get('data', {}).get('access_token'))}")
    assert status == 200, f"Expected 200, got {status}: {body}"
    new_access_token = body["data"]["access_token"]
    
    # 4. Login
    print(f"\n[TEST 4] POST {base_url}/auth/login/")
    status, body, _ = make_request(
        f"{base_url}/auth/login/",
        method="POST",
        data={
            "email": reg_email,
            "password": "Phase3Password@123"
        }
    )
    print(f"Status: {status} (Expected: 200)")
    print(f"Login Access Token: {bool(body.get('data', {}).get('access_token'))}")
    assert status == 200, f"Expected 200, got {status}: {body}"
    
    # 5. Invalid Login
    print(f"\n[TEST 5] POST {base_url}/auth/login/ (Invalid Password)")
    status, body, _ = make_request(
        f"{base_url}/auth/login/",
        method="POST",
        data={
            "email": reg_email,
            "password": "WrongPassword@123"
        }
    )
    print(f"Status: {status} (Expected: 401)")
    print(f"Error Code: {body.get('error', {}).get('code')}")
    assert status == 401, f"Expected 401, got {status}: {body}"
    
    # 6. Duplicate Registration
    print(f"\n[TEST 6] POST {base_url}/auth/register/ (Duplicate Email)")
    status, body, _ = make_request(
        f"{base_url}/auth/register/",
        method="POST",
        data={
            "email": reg_email,
            "password": "Phase3Password@123",
            "phone_number": "+919999999999",
            "first_name": "Dup",
            "last_name": "User",
        }
    )
    print(f"Status: {status} (Expected: 400)")
    print(f"Validation Details: {body.get('error', {}).get('details')}")
    assert status == 400, f"Expected 400, got {status}: {body}"
    assert "email" in body["error"]["details"]
    
    # 7. Logout
    print(f"\n[TEST 7] POST {base_url}/auth/logout/")
    status, body, _ = make_request(
        f"{base_url}/auth/logout/",
        method="POST",
        headers={"Authorization": f"Bearer {new_access_token}"},
        data={}
    )
    print(f"Status: {status} (Expected: 200)")
    assert status == 200, f"Expected 200, got {status}: {body}"
    
    print("\n==================================================")
    print("ALL PHASE 3 AUTHENTICATION TESTS PASSED (7/7)!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
