"""
Settings package initialization
Automatically loads development or production settings based on DJANGO_ENV
"""

import os
from pathlib import Path

# Determine environment
DJANGO_ENV = os.environ.get("DJANGO_ENV", "development")

# Load environment-specific settings
if DJANGO_ENV == "production":
    from .production import *  # noqa

    print(" Loaded PRODUCTION settings")
else:
    from .development import *  # noqa

    print(" Loaded DEVELOPMENT settings")
