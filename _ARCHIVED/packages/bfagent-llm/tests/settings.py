"""
Django test settings for bfagent-llm.

Uses the existing bfagent_db Docker container (port 5432).
Django test runner auto-creates a 'test_<NAME>' database.
Override via TEST_DB_* env vars for CI.
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
        "NAME": os.environ.get("TEST_DB_NAME", "bfagent_llm_test"),
        "USER": os.environ.get("TEST_DB_USER", "bfagent"),
        "PASSWORD": os.environ.get("TEST_DB_PASSWORD", "bfagent_dev_2024"),
        "HOST": os.environ.get("TEST_DB_HOST", "localhost"),
        "PORT": os.environ.get("TEST_DB_PORT", "5432"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"
