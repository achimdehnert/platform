"""
Development settings for Django 5.2 LTS project
"""
import os
from decouple import config

from .base import *
from .database import get_postgres_config, get_sqlite_config

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "172.31.37.255", ".local"]

# Allow all WSL2 IPs (172.16.0.0 - 172.31.255.255)
import socket
try:
    hostname = socket.gethostname()
    ALLOWED_HOSTS.append(hostname)
    # Add WSL2 IP
    wsl_ip = socket.gethostbyname(hostname)
    if wsl_ip not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(wsl_ip)
except:
    pass

# Development-specific apps
INSTALLED_APPS += [
    "django.contrib.admindocs",
]

# Development middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    # 'django.contrib.auth.middleware.LoginRequiredMiddleware',  # Disabled for development
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.admindocs.middleware.XViewMiddleware",
]

# Optional WhiteNoise (static file serving) - don't hard-require it in every environment
try:
    import importlib.util

    if importlib.util.find_spec("whitenoise"):
        MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
except Exception:
    pass

# Database - Force PostgreSQL (book_projects is VIEW in SQLite)
# Use PostgreSQL to bypass SQLite VIEW limitation
# Note: USE_POSTGRES=true works on Linux/WSL2, not on Windows (psycopg2 UTF-8 issue)
USE_POSTGRES = config("USE_POSTGRES", default=False, cast=bool)

if USE_POSTGRES:
    # PostgreSQL via Docker (requires `make docker-up`)
    # Using centralized UTF-8 safe configuration
    DATABASES = get_postgres_config(config)
    print("📊 Using PostgreSQL Database (UTF-8 Safe)")
else:
    # SQLite - No setup required!
    DATABASES = get_sqlite_config(BASE_DIR)
    print("✅ Using SQLite Database (No Docker required!)")

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "django.log",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# Django Debug Toolbar (optional)
if DEBUG:
    try:
        import debug_toolbar

        INSTALLED_APPS += ["debug_toolbar"]
        MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
        INTERNAL_IPS = ["127.0.0.1"]
    except ImportError:
        pass

# =============================================================================
# CELERY CONFIGURATION (Redis Broker)
# =============================================================================
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Europe/Berlin"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Task routing
CELERY_TASK_ROUTES = {
    "apps.bfagent.tasks.process_requirement_task": {"queue": "celery"},
    "apps.bfagent.tasks.auto_illustrate_chapter_task": {"queue": "celery"},
}

# =============================================================================
# N8N CONFIGURATION
# =============================================================================
N8N_BASE_URL = config("N8N_BASE_URL", default="")
N8N_API_KEY = config("N8N_API_KEY", default="")
N8N_WEBHOOK_URL = config("N8N_WEBHOOK_URL", default="")
