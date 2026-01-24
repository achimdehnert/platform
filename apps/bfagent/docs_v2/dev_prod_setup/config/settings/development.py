"""
Django Development Settings
============================

Development-specific settings for local development with Docker PostgreSQL.

Usage:
    # Default (automatically loaded)
    python manage.py runserver

    # Explicit
    DJANGO_ENV=development python manage.py runserver
"""

import os

from .base import *  # noqa: F401, F403

# =============================================================================
# Debug Settings
# =============================================================================

DEBUG = True

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "[::1]",
]

# =============================================================================
# Database - PostgreSQL via Docker
# =============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "bfagent_dev"),
        "USER": os.environ.get("POSTGRES_USER", "bfagent"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "bfagent_dev_2024"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# =============================================================================
# Cache - Redis via Docker (fallback to local memory)
# =============================================================================

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

try:
    import redis

    r = redis.from_url(REDIS_URL)
    r.ping()
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
except Exception:
    # Fallback to local memory cache if Redis not available
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

# =============================================================================
# Email - Console Backend for Development
# =============================================================================

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# =============================================================================
# Static & Media Files
# =============================================================================

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =============================================================================
# Debug Toolbar (optional)
# =============================================================================

if os.environ.get("ENABLE_DEBUG_TOOLBAR", "False").lower() == "true":
    try:
        import debug_toolbar  # noqa: F401

        INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
        MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
        INTERNAL_IPS = ["127.0.0.1"]
    except ImportError:
        pass

# =============================================================================
# Logging - Verbose for Development
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# =============================================================================
# Security - Relaxed for Development
# =============================================================================

# CSRF
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# CORS (if using django-cors-headers)
CORS_ALLOW_ALL_ORIGINS = True

# =============================================================================
# Development-specific Settings
# =============================================================================

# Show detailed error pages
DEBUG_PROPAGATE_EXCEPTIONS = True

# Disable password validation in development
AUTH_PASSWORD_VALIDATORS = []

# =============================================================================
# Print Database Info on Startup
# =============================================================================

print(
    f"""
╔══════════════════════════════════════════════════════════════════╗
║  BF Agent - Development Environment                              ║
╠══════════════════════════════════════════════════════════════════╣
║  Database: PostgreSQL                                            ║
║  Host: {DATABASES['default']['HOST']}:{DATABASES['default']['PORT']}                                           ║
║  Name: {DATABASES['default']['NAME']}                                          ║
║  Debug: {DEBUG}                                                      ║
╚══════════════════════════════════════════════════════════════════╝
"""
)
