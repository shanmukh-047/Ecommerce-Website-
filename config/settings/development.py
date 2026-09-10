"""
Development Settings for Bharath Masala Products.
Optimized for local developer experience and testing.
"""

import os

import dj_database_url

from .base import *

DEBUG = True

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "bmp-dev-insecure-secret-key-32894723894723894723894723894723",
)

allowed_hosts_env = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(",") if h.strip()]

# Database Strategy:
# If DATABASE_URL is set, connect to PostgreSQL.
# Otherwise fallback to local SQLite for frictionless development/testing.
database_url = os.getenv("DATABASE_URL")
if database_url and database_url.startswith("postgres"):
    DATABASES = {
        "default": dj_database_url.config(
            default=database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# CORS & CSRF for local frontend development
CORS_ALLOW_CREDENTIALS = True
cors_origins_env = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000",
)
CORS_ALLOWED_ORIGINS = [o.strip() for o in cors_origins_env.split(",") if o.strip()]

csrf_origins_env = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000",
)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_origins_env.split(",") if o.strip()]

# Cookie Security (relaxed for HTTP localhost)
SECURE_COOKIE = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

import sys
# Rate Throttling: Relaxed limits for local development and automated testing
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        **REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}),
        "anon": os.getenv("THROTTLE_ANON_RATE", "1000/min"),
        "user": os.getenv("THROTTLE_USER_RATE", "1000/min"),
        "auth": os.getenv(
            "THROTTLE_AUTH_RATE",
            "5/min" if any("test" in arg for arg in sys.argv) else "200/min",
        ),
    },
}

# Celery: In local development, execute tasks synchronously to avoid requiring Redis broker
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = False
