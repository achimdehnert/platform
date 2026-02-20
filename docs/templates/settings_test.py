# config/settings/test.py — ADR-057 §2.3 standard test settings template
# Copy to config/settings/test.py in each service repo
# Adjust DATABASE NAME/USER/PASSWORD to match CI service container values

import os
from .base import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "test_db",
        "USER": "test_user",
        "PASSWORD": "test_pass",
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": "5432",
    }
}

# 10x faster password hashing in tests (never use in production)
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Capture emails in memory — access via django.core.mail.outbox
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Run Celery tasks synchronously — no worker needed in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# In-memory file storage — no disk writes during tests
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Disable throttling in tests
REST_FRAMEWORK = {
    **globals().get("REST_FRAMEWORK", {}),
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}

# Disable HTTPS redirect in tests
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
