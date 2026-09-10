# BHARATH MASALA — PASSWORD RECOVERY & AUTHENTICATION AUDIT
**Date:** 2026-09-10  
**Project:** Bharath Masala Products  
**Backend:** Django REST Framework (`apps/accounts`)  
**Frontend:** Next.js 14 (`masala-box`)  
**Audit File:** `PASSWORD_RECOVERY_AUDIT_2026_09_10.md`

---

## 1. Executive Summary

This audit evaluates the current state of authentication, credential management, session handling, and recovery mechanisms in the Bharath Masala application. While customer registration, login, JWT issuance, HttpOnly refresh cookie rotation, and role-based staff authentication are functioning and pass automated suites, **the application currently lacks password recovery and password change functionality**.

Specifically:
- No "Forgot Password" flow exists for customers or staff.
- No password reset endpoints exist in the Django backend.
- No authenticated "Change Password" endpoint or UI exists.
- No transactional email configuration or templates exist for credential recovery.
- No token-based recovery validation exists.

This audit details the existing architecture, identifies security risks, and establishes the production-ready implementation plan.

---

## 2. Current Authentication Architecture

### 2.1 User Model (`apps/accounts/models.py`)
- **Model:** `User(AbstractBaseUser, PermissionsMixin)` with UUID primary keys (`id = models.UUIDField(primary_key=True, default=uuid.uuid4)`).
- **Identifier:** `email = models.EmailField(unique=True, db_index=True)` (normalized to lowercase in `clean()`).
- **Phone:** `phone_number = models.CharField(max_length=15, unique=True, db_index=True)` (normalized to Indian E.164 format).
- **Roles:** Defined via `Role` TextChoices:
  - `CUSTOMER` (Retail Customer)
  - `WHOLESALE_PENDING` / `WHOLESALE_APPROVED` (B2B Wholesale)
  - `STAFF` (Operations Staff, `is_staff=True`)
  - `MANAGER` (Operations Manager, `is_staff=True`)
  - `SUPERADMIN` (Super Administrator, `is_staff=True`, `is_superuser=True`)
- **Security fields:** `password` (Django hashed format `pbkdf2_sha256$...`), `last_login`, `is_active`.

### 2.2 Password Hashing & Validation (`config/settings/base.py`)
- Standard Django password hashing (`pbkdf2_sha256` by default, cryptographically secure).
- `AUTH_PASSWORD_VALIDATORS` configured:
  1. `UserAttributeSimilarityValidator`
  2. `MinimumLengthValidator` (`min_length: 8`)
  3. `CommonPasswordValidator`
  4. `NumericPasswordValidator`
- Serializer validation invokes `django.contrib.auth.password_validation.validate_password(value)`.

### 2.3 Token & Session Architecture (`rest_framework_simplejwt`)
- **Access Token:** Short-lived JWT (15 minutes), passed via `Authorization: Bearer <token>` header. Custom claims include `role` and `email`.
- **Refresh Token:** Long-lived JWT (7 days), stored in an `HttpOnly`, `SameSite=Lax`, path-restricted (`/api/v1/auth/`) cookie.
- **Rotation:** `ROTATE_REFRESH_TOKENS = True`, `BLACKLIST_AFTER_ROTATION = True`. Refreshing an access token revokes the previous refresh token and issues a new pair.

### 2.4 Registration & Login Endpoints
- `POST /api/v1/auth/register/`: Registers a retail customer, validates unique email/phone and password strength, issues JWT access token, and sets refresh cookie.
- `POST /api/v1/auth/register/wholesale/`: Registers a B2B applicant and creates a pending KYC profile.
- `POST /api/v1/auth/login/`: Authenticates via email/password using Django's `authenticate()`, issues JWT access token, sets refresh cookie, and merges guest cart.
- `POST /api/v1/auth/token/refresh/`: Rotates refresh token from HttpOnly cookie and yields a new access token.
- `POST /api/v1/auth/logout/`: Blacklists current refresh token and deletes the refresh cookie.
- `GET/PATCH /api/v1/auth/me/`: Customer profile retrieval and name updates.

### 2.5 Admin / Staff Authentication
- Staff members authenticate through `POST /api/v1/auth/login/` (frontend: `/admin-login`).
- `AdminRouteGuard` on frontend checks `isStaff` (`is_staff`, `is_superuser`, or role in `['STAFF', 'MANAGER', 'SUPERADMIN']`).
- Backend views enforce `IsManagerOrAdmin` / `is_staff` permission checks.
- Currently, if an admin forgets their password, there is no self-service recovery mechanism.

### 2.6 Email Configuration
- **Current state:** `EMAIL_BACKEND` is not explicitly declared in `config/settings/base.py`, defaulting to standard SMTP on localhost:25.
- No password-reset email templates or mail generation logic currently exist in `apps/accounts`.

---

## 3. Gap Analysis & Missing Functionality

| Capability | Current State | Required State |
| :--- | :--- | :--- |
| **Customer Forgot Password** | Missing | `POST /api/v1/auth/password-reset/` with enumeration protection & email dispatch |
| **Customer Password Reset** | Missing | `POST /api/v1/auth/password-reset/confirm/` with token validation & password update |
| **Customer Change Password** | Missing | `POST /api/v1/auth/change-password/` requiring current password & re-authentication |
| **Admin Forgot Password** | Missing | Accessible via `/admin-login` with same cryptographically secure token & email dispatch |
| **Admin Change Password** | Missing | Accessible in `/admin-dashboard` or admin settings requiring current password |
| **Password Reset Page** | Missing | Dedicated frontend route `/reset-password?uid=...&token=...` with validation & feedback |
| **Email Service & Template** | Missing | Formatted HTML + text email with token link, expiration notice, and security warning |
| **Token Invalidation on Reset** | Missing | Old sessions/tokens revoked; Django `default_token_generator` automatically invalidates upon password hash change |
| **Rate Limiting on Reset** | Missing | Auth throttle (`AuthRateThrottle`, 5/min) applied to recovery endpoints |

---

## 4. Security Risks & Mitigations

1. **Account Enumeration via Forgot Password:**
   - *Risk:* Attacker submits emails to discover which users exist in the system.
   - *Mitigation:* The endpoint returns an identical generic 200 response: `"If an account exists for this email, password reset instructions have been sent."` regardless of whether the email exists.
2. **Token Guessing / Brute-force:**
   - *Risk:* Attacker attempts to forge or brute-force reset tokens.
   - *Mitigation:* Uses Django's `default_token_generator` (cryptographically salted SHA-256 HMAC incorporating user PK, password hash, and timestamp) with a 1-hour expiration window.
3. **Token Reuse:**
   - *Risk:* Attacker intercepts an old reset link.
   - *Mitigation:* Because `default_token_generator` embeds the user's password hash in the HMAC, changing the password instantly invalidates the token. Re-submitting the same token fails immediately.
4. **Plaintext Password Exposure:**
   - *Risk:* Passwords sent via email, logged, or serialized.
   - *Mitigation:* Never send or log passwords. Write-only serializer fields. Passwords only exist in memory during hashing.
5. **Privilege Escalation / IDOR:**
   - *Risk:* Customer uses reset mechanism to modify admin accounts without authorization.
   - *Mitigation:* Reset tokens are tied to specific user IDs decoded from secure base64. Staff routes remain isolated behind RBAC.

---

## 5. Implementation Plan

### Step 1: Backend Settings & Email Setup
- Configure `EMAIL_BACKEND` in `config/settings/base.py` (default to `django.core.mail.backends.console.EmailBackend` in development).
- Add `FRONTEND_BASE_URL` (default `http://localhost:3000`).
- Add `PASSWORD_RESET_TIMEOUT = 3600` (1 hour).

### Step 2: Backend Serializers & Services (`apps/accounts`)
- `PasswordResetRequestSerializer`: Validates email format.
- `PasswordResetConfirmSerializer`: Validates `uid`, `token`, `new_password`, `confirm_password` with `validate_password()`.
- `ChangePasswordSerializer`: Validates `current_password`, `new_password`, `confirm_password` against `request.user`.
- `AuthService.send_password_reset_email(email)`: Uses `default_token_generator` and `urlsafe_base64_encode`.
- `AuthService.confirm_password_reset(uidb64, token, new_password)`: Decodes UID, verifies token, sets new password, rotates tokens.
- `AuthService.change_password(user, current_password, new_password)`: Verifies old password, sets new password, blacklists existing tokens.

### Step 3: Backend Views & URLs
- `PasswordResetRequestView` (`POST /api/v1/auth/password-reset/`)
- `PasswordResetConfirmView` (`POST /api/v1/auth/password-reset/confirm/`)
- `ChangePasswordView` (`POST /api/v1/auth/change-password/`)

### Step 4: Frontend API Client & Auth Service
- Add `requestPasswordReset(email)` to `frontend/services/authService.js`.
- Add `confirmPasswordReset(uid, token, newPassword, confirmPassword)` to `frontend/services/authService.js`.
- Add `changePassword(currentPassword, newPassword, confirmPassword)` to `frontend/services/authService.js`.

### Step 5: Frontend UI
- Add "Forgot Password?" modal / flow to `StorefrontAuth.jsx`.
- Add "Forgot Password?" modal / flow to `/admin-login`.
- Create `/reset-password` page (`frontend/app/reset-password/page.js`).
- Add "Security & Password" tab to `/account` page (`frontend/app/account/page.js`).
- Add "Change Password" modal / action to Admin Deck (`AdminLayout.jsx`).

### Step 6: Automated Verification & Audit
- Unit tests in `apps/accounts/tests/test_password_recovery.py`.
- Browser CDP end-to-end tests for customer and staff password reset flows.
- Multi-viewport responsive verification.
- Final report: `PASSWORD_RECOVERY_FINAL_AUDIT_2026_09_10.md`.
