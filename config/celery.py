"""
Celery application factory for Bharath Masala Products platform.

Integrates with Django settings via django-celery-beat for
scheduled periodic tasks (reservation expiry, email dispatch, etc.).
"""

import os

from celery import Celery

# Set the default Django settings module for the celery command-line program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("bharath_masala")

# Load configuration from Django settings, using the CELERY_ namespace.
# All Celery config keys in settings.py must be prefixed with CELERY_.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all INSTALLED_APPS.
# Each app can define tasks in its own tasks.py module.
app.autodiscover_tasks()
