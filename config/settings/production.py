"""
Production Settings for Bharath Masala Products Platform.
Strict security enforcement, SSL headers, HSTS, secure cookies, and fail-fast assertions.
"""

import os

import dj_database_url

from .base import *

# Production must NEVER run in debug mode
DEBUG = False

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 50:
    raise RuntimeError(
        "CRITICAL SECURITY CONFIGURATION ERROR: DJANGO_SECRET_KEY must be set to "
        "a cryptographically secure string (minimum 50 characters) in production."
    )

allowed_hosts_env = os.getenv(
    "DJANGO_ALLOWED_HOSTS",
    "bharathmasala.com,www.bharathmasala.com,.onrender.com,.koyeb.app,.vercel.app,localhost,127.0.0.1",
)
ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(",") if h.strip()]
if "*" in ALLOWED_HOSTS:
    raise RuntimeError(
        "CRITICAL SECURITY CONFIGURATION ERROR: Wildcard '*' ALLOWED_HOSTS is forbidden in production."
    )

# Database Configuration (PostgreSQL 15+ mandatory)
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("CRITICAL CONFIGURATION ERROR: DATABASE_URL is required in production.")

DATABASES = {
    "default": dj_database_url.config(
        default=database_url,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Strict CORS & CSRF
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

cors_origins_env = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "https://bharathmasala.com,https://www.bharathmasala.com",
)
CORS_ALLOWED_ORIGINS = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.vercel\.app$",
    r"^https://.*\.onrender\.com$",
    r"^https://.*\.koyeb\.app$",
]

csrf_origins_env = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "https://bharathmasala.com,https://www.bharathmasala.com,https://*.vercel.app,https://*.onrender.com,https://*.koyeb.app",
)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_origins_env.split(",") if o.strip()]

# HTTPS & Cookie Security
SECURE_COOKIE = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # Frontend needs to read CSRF token for cookie-bearing endpoints

SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() == "true"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Payment Gateway Configuration Validation (Phase 3.5 & Production Hardening)
ENABLE_RAZORPAY = os.getenv("ENABLE_RAZORPAY", "False").lower() in ("true", "1", "yes")

razorpay_key_id = os.getenv("RAZORPAY_KEY_ID", RAZORPAY_KEY_ID)
razorpay_key_secret = os.getenv("RAZORPAY_KEY_SECRET", RAZORPAY_KEY_SECRET)
razorpay_webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", RAZORPAY_WEBHOOK_SECRET)

if ENABLE_RAZORPAY:
    if not razorpay_key_id or "placeholder" in razorpay_key_id.lower():
        raise RuntimeError(
            "CRITICAL CONFIGURATION ERROR: RAZORPAY_KEY_ID must be configured with a valid "
            "production key and cannot be empty or a placeholder when ENABLE_RAZORPAY=True."
        )
    if not razorpay_key_secret or "placeholder" in razorpay_key_secret.lower():
        raise RuntimeError(
            "CRITICAL CONFIGURATION ERROR: RAZORPAY_KEY_SECRET must be configured with a valid "
            "production secret and cannot be empty or a placeholder when ENABLE_RAZORPAY=True."
        )
    if (
        not razorpay_webhook_secret
        or "placeholder" in razorpay_webhook_secret.lower()
        or razorpay_webhook_secret == "test_webhook_secret"
    ):
        raise RuntimeError(
            "CRITICAL CONFIGURATION ERROR: RAZORPAY_WEBHOOK_SECRET must be configured with a valid "
            "production webhook secret when ENABLE_RAZORPAY=True."
        )
