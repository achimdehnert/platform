"""
Django test settings for bfagent-llm.

Uses PostgreSQL via Docker (docker-compose.test.yml).
Run: bash scripts/test.sh -v
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
        "USER": os.environ.get("TEST_DB_USER", "test"),
        "PASSWORD": os.environ.get("TEST_DB_PASSWORD", "test"),
        "HOST": os.environ.get("TEST_DB_HOST", "localhost"),
        "PORT": os.environ.get("TEST_DB_PORT", "5433"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"
