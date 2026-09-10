"""
Django Base Settings for Bharath Masala Products Platform.
All shared configuration across development, staging, and production.
"""

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_celery_beat",  # Phase 3+: periodic task scheduling via DatabaseScheduler
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.catalog",
    "apps.inventory",
    "apps.cart",
    "apps.orders",
    "apps.payments",
    "apps.shipping",
    "apps.invoices",
    "apps.notifications",
    "apps.returns",
    "apps.promotions",
]


INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "apps.core.middleware.RequestIDMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization & Timezone (India-centric UTC-safe)
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_RENDERER_CLASSES": ("apps.core.renderers.StandardResponseRenderer",),
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON_RATE", "20/min"),
        "user": os.getenv("THROTTLE_USER_RATE", "100/min"),
        "auth": os.getenv("THROTTLE_AUTH_RATE", "5/min"),
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# OpenAPI / Swagger Documentation Settings (Phase 3.13)
SPECTACULAR_SETTINGS = {
    "TITLE": "Bharath Masala API",
    "DESCRIPTION": "Production-ready API contract for e-commerce backend",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]",
    "TAGS": [
        {"name": "Core", "description": "Platform health checks and readiness probes"},
        {
            "name": "Authentication",
            "description": "Customer and staff authentication, registration, and token rotation",
        },
        {"name": "Accounts", "description": "User profile management and customer address book"},
        {
            "name": "Catalog",
            "description": "Categories, spice products, pack-size variants, and reviews",
        },
        {"name": "Cart", "description": "Guest and authenticated shopping cart management"},
        {
            "name": "Orders",
            "description": "Atomic checkout, order state machine, history, and cancellation",
        },
        {
            "name": "Payments",
            "description": "Razorpay order initiation, signature verification, and webhooks",
        },
        {
            "name": "Inventory",
            "description": "Stock item queries, restock operations, and warehouse adjustments",
        },
        {
            "name": "Shipping",
            "description": "Consignment fulfillment, carrier booking, and parcel tracking",
        },
        {
            "name": "Invoices",
            "description": "Statutory Indian GST tax invoices, credit notes, and PDF downloads",
        },
        {
            "name": "Returns",
            "description": "Customer returns, reverse logistics, QA inspection, and RMA resolutions",
        },
        {
            "name": "Notifications",
            "description": "Staff communication audit logs and message resend",
        },
        {
            "name": "Promotions",
            "description": "Discount coupons and automated promotional campaigns",
        },
        {
            "name": "Wholesale",
            "description": "B2B wholesale customer registration and KYC verification",
        },
        {
            "name": "Staff Operations",
            "description": "Staff and management administration workflows",
        },
    ],
}

# SimpleJWT Configuration
JWT_ACCESS_LIFETIME_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "15"))
JWT_REFRESH_LIFETIME_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "7"))

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=JWT_ACCESS_LIFETIME_MINUTES),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=JWT_REFRESH_LIFETIME_DAYS),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": os.getenv(
        "DJANGO_SECRET_KEY", "bmp-insecure-dev-key-change-in-production-12345"
    ),
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": "bharath-masala-products",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "JTI_CLAIM": "jti",
}

# Cookie Settings for Refresh Token
JWT_REFRESH_COOKIE_NAME = "refresh_token"
JWT_REFRESH_COOKIE_PATH = "/api/v1/auth/"
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", None) or None
COOKIE_SAMESITE = "Lax"
GUEST_CART_COOKIE_NAME = os.getenv("GUEST_CART_COOKIE_NAME", "guest_cart_token")
GUEST_CART_COOKIE_PATH = "/api/v1/cart/"
GUEST_CART_COOKIE_MAX_AGE = int(os.getenv("GUEST_CART_COOKIE_MAX_AGE", "2592000"))
ORDER_RESERVATION_TIMEOUT_MINUTES = int(os.getenv("ORDER_RESERVATION_TIMEOUT_MINUTES", "30"))

# Razorpay Gateway Configuration (Phase 3.5)
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_placeholder")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "test_secret_placeholder")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret")

# Transactional Email & Password Recovery Configuration
EMAIL_BACKEND = os.getenv(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "Bharat Masala <support@bharathmasala.com>",
)
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")
PASSWORD_RESET_TIMEOUT = int(os.getenv("PASSWORD_RESET_TIMEOUT", "3600"))  # 1 hour


# Logging configuration with PII masking and request ID binding
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "pii_masking": {
            "()": "apps.core.middleware.PIIMaskingFilter",
        },
    },
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "filters": ["pii_masking"],
            "formatter": "standard",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": True,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

# ---------------------------------------------------------------------------
# Celery Configuration (Phase 3+)
# All keys are prefixed with CELERY_ and loaded by:
#   app.config_from_object("django.conf:settings", namespace="CELERY")
# ---------------------------------------------------------------------------

# Broker: Redis (connection string from environment — never hardcoded)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

# Result backend: Redis (used by celery inspect, monitoring, chord callbacks)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# Timezone must match Django TIME_ZONE for accurate periodic scheduling
CELERY_TIMEZONE = TIME_ZONE  # "Asia/Kolkata"
CELERY_ENABLE_UTC = True

# Serialization — restrict to JSON only; never allow pickle (security)
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]

# Task behaviour
CELERY_TASK_ALWAYS_EAGER = False  # Never inline tasks — always use broker
CELERY_TASK_EAGER_PROPAGATES = True  # Propagate exceptions in eager mode (tests)
CELERY_TASK_ACKS_LATE = True  # Acknowledge task only after completion (safe retry)
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Re-queue if worker dies mid-task
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # One task at a time per worker slot (prevents starvation)

# Result TTL: results expire after 1 day
CELERY_RESULT_EXPIRES = 86400  # seconds

# django-celery-beat: store periodic task schedule in the database
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Celery Beat Periodic Task Schedule (Phase 3.6)
CELERY_BEAT_SCHEDULE = {
    "cleanup-expired-reservations-and-orders": {
        "task": "apps.orders.tasks.cleanup_expired_reservations_and_orders",
        "schedule": 60.0,  # Run every 60 seconds (1 minute)
    },
}

# ---------------------------------------------------------------------------
# Statutory Indian GST Invoicing Configuration (Phase 3.8)
# ---------------------------------------------------------------------------
INVOICE_SELLER_NAME = os.getenv("INVOICE_SELLER_NAME", "Bharath Masala Products")
INVOICE_SELLER_GSTIN = os.getenv("INVOICE_SELLER_GSTIN", "29AAAAA0000A1Z5")
INVOICE_SELLER_FSSAI = os.getenv("INVOICE_SELLER_FSSAI", "11223344556677")
INVOICE_SELLER_ADDRESS = os.getenv(
    "INVOICE_SELLER_ADDRESS",
    "Main Road, Thirthahalli, Shimoga District, Karnataka 577432",
)

# ---------------------------------------------------------------------------
# Returns & Reverse Logistics Configuration (Phase 3.10)
# ---------------------------------------------------------------------------
RETURN_POLICY_WINDOW_DAYS = int(os.getenv("RETURN_POLICY_WINDOW_DAYS", "7"))
