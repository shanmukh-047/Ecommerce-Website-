"""Config package for Bharath Masala Products platform."""

# Expose the Celery application instance here so that Django's autoreload
# and management commands can discover it automatically.
# The try/except guard allows the package to import cleanly in environments
# where Celery has not been installed yet (e.g., during initial pip install).
try:
    from .celery import app as celery_app

    __all__ = ("celery_app",)
except ImportError:
    pass
