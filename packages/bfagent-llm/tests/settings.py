"""
Django test settings for bfagent-llm.

Uses PostgreSQL (matching production). Override via environment variables.

Local WSL: peer auth over Unix socket (HOST="").
CI/Docker: TCP with password (HOST="localhost").
"""

import os

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

SECRET_KEY = "test-secret-key-not-for-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "bfagent_llm.django_app",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("TEST_DB_NAME", "test_bfagent_llm"),
        "USER": os.environ.get("TEST_DB_USER", os.environ.get("USER", "dehnert")),
        "PASSWORD": os.environ.get("TEST_DB_PASSWORD", ""),
        "HOST": os.environ.get("TEST_DB_HOST", ""),
        "PORT": os.environ.get("TEST_DB_PORT", ""),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"
