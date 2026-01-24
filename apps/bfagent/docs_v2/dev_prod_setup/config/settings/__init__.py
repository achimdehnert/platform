"""
Django Settings Module Loader

Automatically loads the appropriate settings based on environment.

Priority:
1. DJANGO_SETTINGS_MODULE environment variable
2. Fallback to development settings

Usage:
    # Development (default)
    python manage.py runserver

    # Production
    DJANGO_SETTINGS_MODULE=config.settings.production python manage.py runserver

    # Or set in .env file
"""

import os

# Determine which settings to use
environment = os.environ.get("DJANGO_ENV", "development")

if environment == "production":
    from .production import *
else:
    from .development import *
