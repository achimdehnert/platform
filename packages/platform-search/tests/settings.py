"""Minimal Django settings for platform-search tests."""

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
    "content_store": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "platform_search",
]

SECRET_KEY = "test-secret-key"
OPENAI_API_KEY = "test-key"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
