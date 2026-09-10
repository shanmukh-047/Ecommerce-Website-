"""
Staging Settings for Bharath Masala Products Platform.
Mirrors production configuration with staging domain tolerances.
"""

from .production import *

# Staging specific overrides if needed
SECURE_HSTS_PRELOAD = False  # Avoid browser preload lists for staging domains
