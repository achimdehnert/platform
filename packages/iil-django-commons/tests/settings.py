SECRET_KEY = "test-secret-key-iil-django-commons"
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "iil_commons",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
IIL_COMMONS = {
    "LOG_FORMAT": "human",
    "LOG_LEVEL": "WARNING",
    "HEALTH_CHECKS": ["db"],
}
