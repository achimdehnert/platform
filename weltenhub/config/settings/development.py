"""
Development Settings
====================

Local development settings for Weltenhub.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

# SQLite for local development + Platform DB for governance
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
    "platform": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "platform",
        "USER": "bfagent",
        "PASSWORD": "bfagent_dev_2024",
        "HOST": "localhost",
        "PORT": "5432",
        "OPTIONS": {
            "options": "-c search_path=platform,public"
        },
    }
}

# Simplified password validation for development
AUTH_PASSWORD_VALIDATORS = []

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CORS for local development
CORS_ALLOW_ALL_ORIGINS = True

# Database routers
DATABASE_ROUTERS = ["apps.governance.db_router.GovernanceRouter"]
