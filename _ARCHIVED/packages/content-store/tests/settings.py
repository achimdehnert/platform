"""Minimal Django settings for content_store tests."""

SECRET_KEY = "test-secret-key-not-for-production"

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
    "content_store",
]

DATABASE_ROUTERS = ["content_store.router.ContentStoreRouter"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
