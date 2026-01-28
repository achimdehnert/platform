"""Django settings for testing bfagent-core."""

SECRET_KEY = "test-secret-key-not-for-production"
DEBUG = True

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "bfagent_core",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Tenancy settings
TENANT_BASE_DOMAIN = "localhost"
TENANT_ALLOW_LOCALHOST = True
