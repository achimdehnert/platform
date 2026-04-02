"""
hub_template/settings/base.py

Platform-Standard-Settings für alle iil UI-Hubs.
Kopieren und hub-spezifisch anpassen.

Fixes ADR-110:
  B-4: LocaleMiddleware korrekte Reihenfolge (nach SessionMiddleware)
  B-6: compilemessages mit --locale Flags
  C-7: makemessages mit --ignore Flags
  M-4: LANGUAGE_COOKIE_NAME plattformweit einheitlich
  H-5: gettext_lazy / gettext Verwendung dokumentiert

Fixes ADR-109:
  B-1: TENANCY_MODE statt fest verkabeltem Subdomain-Routing
  C-3: TENANCY_FALLBACK_URL für unbekannte Subdomains
  C-4: TENANT_ISOLATION_MODE = "disabled" für billing-hub
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Core Django
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]  # Never hardcode, always env var

DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"  # Platform-Standard: BigAutoField

# ---------------------------------------------------------------------------
# i18n / l10n (ADR-110 Pflicht-Stack)
# ---------------------------------------------------------------------------

USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGE_CODE = "de"

LANGUAGES = [
    ("de", "Deutsch"),
    ("en", "English"),
    # ("fr", "Français"),  # Nur wenn Hub es unterstützt — nicht global
]

LOCALE_PATHS = [BASE_DIR / "locale"]

# Fix M-4: Einheitlicher Cookie-Name plattformweit (kein Konflikt bei mehreren Hubs auf Domain)
LANGUAGE_COOKIE_NAME = "iil_lang"
LANGUAGE_COOKIE_AGE = 60 * 60 * 24 * 365  # 1 Jahr
LANGUAGE_COOKIE_PATH = "/"
LANGUAGE_COOKIE_DOMAIN = None   # Wird in prod-settings auf ".domain.tld" gesetzt
LANGUAGE_COOKIE_SECURE = False  # Wird in prod-settings auf True gesetzt
LANGUAGE_COOKIE_SAMESITE = "Lax"

# ---------------------------------------------------------------------------
# Multi-Tenancy (ADR-109)
# ---------------------------------------------------------------------------

# Fix H-3: TenancyMode Strategy
# "subdomain" = Prod, "session" = Dev, "header" = API/CI, "disabled" = billing-hub
TENANCY_MODE = os.environ.get("TENANCY_MODE", "session")  # Dev-Default: session

# Fix C-3: Fallback für unbekannte Subdomains (kein 500)
TENANCY_FALLBACK_URL = "/onboarding/"

# Fix C-4: Explicit isolation mode for billing-hub
# billing-hub setzt: TENANT_ISOLATION_MODE = "disabled"
TENANT_ISOLATION_MODE = "enabled"  # "enabled" | "disabled"

# ---------------------------------------------------------------------------
# MIDDLEWARE — Reihenfolge ist kritisch (Fix B-4)
# ---------------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # direkt nach Security
    # ↓ Session MUSS vor Locale kommen (Django-Requirement)
    "django.contrib.sessions.middleware.SessionMiddleware",
    # ↓ Locale MUSS nach Session kommen (liest Session für Sprachpräferenz)
    "django.middleware.locale.LocaleMiddleware",
    # ↓ Tenancy nach Locale (setzt tenant_id + überschreibt LANGUAGE_CODE)
    "django_tenancy.middleware.SubdomainTenantMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Platform packages
    "django_tenancy",
    # Hub apps (hub-spezifisch hinzufügen)
]

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",  # Pflicht für {% trans %}
                "django_tenancy.context_processors.tenant",  # request.tenant im Template
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "hub_dev"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------

ROOT_URLCONF = "config.urls"

# ---------------------------------------------------------------------------
# Static / Media
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"
