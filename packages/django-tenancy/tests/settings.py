SECRET_KEY = "test-secret-key-not-for-production"
DEBUG = True
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django_tenancy",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
TENANCY_MODE = "session"
TENANCY_FALLBACK_URL = "/onboarding/"
LANGUAGE_COOKIE_NAME = "iil_lang"
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django_tenancy.middleware.SubdomainTenantMiddleware",
]
SESSION_ENGINE = "django.contrib.sessions.backends.db"
ROOT_URLCONF = "tests.urls"
