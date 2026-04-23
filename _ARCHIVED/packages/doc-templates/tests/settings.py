"""Minimal Django settings for testing doc_templates."""

SECRET_KEY = "test-secret-key-for-doc-templates"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "doc_templates",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
