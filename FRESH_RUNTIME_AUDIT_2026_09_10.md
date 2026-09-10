# FRESH RUNTIME AUDIT (10/09/2026)
**Bharath Masala Full-Stack E-Commerce Platform**
*Diagnostic Baseline Prior to Fixes*

---

## 1. EXECUTIVE SUMMARY

An independent audit of the running application was performed on September 10, 2026, investigating the critical failure reported during manual user testing:
> **Observed User Failure:** When attempting to create a new customer account, the website displayed `"Check your network connection"` (or `"Unable to connect to the backend server. Please verify your connection."`).

### Identified Root Causes of Authentication Failure:
1. **Missing `confirm_password` Field in `StorefrontAuth.jsx` Submission:**
   - The backend `CustomerRegistrationSerializer` defines `confirm_password` as `required=True`.
   - The frontend registration handler in `StorefrontAuth.jsx` submitted only `{ email, password, phone_number, first_name, last_name }` without `confirm_password`.
   - Django REST Framework rejected the payload with HTTP 400: `{"confirm_password": ["This field is required."]}`.
2. **Cross-Origin Host Binding (`NEXT_PUBLIC_API_BASE_URL` vs Mobile/Localhost):**
   - `frontend/.env.local` and `.env.development` had `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000` set.
   - `frontend/lib/apiClient.js` resolved `getBaseUrl()` to `http://127.0.0.1:8000` in the browser instead of using relative `/api/v1/` URLs.
   - **On Mobile Devices / LAN Clients:** Mobile browsers navigating to `http://192.168.x.x:3000` attempted to contact `127.0.0.1:8000` (the phone's own local loopback), resulting in immediate TCP connection failure (`ECONNREFUSED` / `TypeError: Failed to fetch`).
   - **On Laptop/Desktop Browsers:** Requests from `localhost:3000` to `127.0.0.1:8000` constitute cross-origin requests, subject to CORS preflight headers and third-party cookie restrictions for `refresh_token`.
3. **Overly Restrictive Development Auth Rate Limit (`5/min`):**
   - `base.py` defined `"auth": "5/min"` in `DEFAULT_THROTTLE_RATES`, which applied to both `CustomerRegistrationView` and `LoginView`.
   - When a user or tester attempts registration or login more than 5 times in 60 seconds, Django returns HTTP 429 Too Many Requests, which surfaced as a connection or validation failure.
4. **Generic Error Message Fallbacks in Frontend Catch Blocks:**
   - In several UI components, any error where `status === 0` or `isNetworkError === true` triggered a generic `"Unable to connect to the server. Please check your network connection."` message.
   - When real API validation errors occurred, error formatting did not properly bind field errors back to the form inputs.

---

## 2. POTENTIAL FAILURE POINTS IDENTIFIED ACROSS SUBSYSTEMS

| Subsystem | Potential Failure Point | Severity | Analysis / Root Cause |
| :--- | :--- | :---: | :--- |
| **Authentication** | Missing `confirm_password` in payload | **HIGH** | `CustomerRegistrationSerializer` strictly requires `confirm_password`. Must make it optional/default to `password` on backend, and pass it from frontend. |
| **Network / Mobile**| `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000` in browser | **CRITICAL** | Hardcoding `127.0.0.1` breaks all mobile and LAN access. Browser must use relative URL `""` to route via Next.js proxy. |
| **Next.js Proxy** | Rewrites destination trailing slash | **MEDIUM** | Standardized `${cleanBackend}/api/v1/:path*/` tested OK; ensure queries and paths don't double-slash. |
| **Throttling** | `auth` throttle set to `5/min` in development | **HIGH** | Exhausts in 5 attempts during testing, causing HTTP 429 errors. Need dev override to `100/min`. |
| **Form UX** | Field-level error propagation in `StorefrontAuth` | **MEDIUM** | API validation errors (e.g. duplicate email/phone) should highlight corresponding input fields directly. |
| **Catalog / Images**| Test fixtures vs authentic photography | **INFO** | Authentic high-res photography is missing (asset blocker); SVG badge fallbacks are active. |
| **Payments** | Gateway credentials in development | **INFO** | Requires valid Razorpay credentials in production; development handles test signatures. |
| **Admin / RBAC** | Direct access to admin login & dashboard | **LOW** | Customer access gate must continue to exempt `/admin*` routes. |

---

## 3. REMEDIATION PLAN

1. **Fix `apiClient.js` URL Resolution for Multi-Device Support:**
   - In browser environment (`typeof window !== 'undefined'`), default `getBaseUrl()` to `""` (relative path) unless explicitly overridden. This guarantees that requests from laptops, desktops, and mobile phones over Wi-Fi all hit the same host `/api/v1/...` and are proxied by Next.js cleanly.
2. **Fix `CustomerRegistrationSerializer` Contract:**
   - Update `apps/accounts/serializers.py` so `confirm_password` is optional on the backend serializer (`required=False`, defaulting to `password`), while still verifying match if provided.
   - Update `StorefrontAuth.jsx` to pass `confirm_password: regPassword`.
3. **Update Rate Throttling in `config/settings/development.py`:**
   - Increase development `"auth"` throttle rate to `"100/min"` so manual and automated testing does not hit artificial rate limits.
4. **Improve Form Validation Error Mapping in `StorefrontAuth.jsx`:**
   - Bind backend field errors (`err.details`) directly to form fields (`regErrors.email`, `regErrors.phone_number`, etc.) so the user sees exact inline validation feedback.
5. **Comprehensive Verification:**
   - Direct API calls (curl) for register, login, refresh, me, logout.
   - Mobile and desktop responsive layouts (390px to 1920px).
   - E2E journey: Intro → Register → Login → Catalog → Cart → Checkout → COD → Admin.
