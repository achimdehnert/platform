"""Django app configuration for platform-search."""

from django.apps import AppConfig


class PlatformSearchConfig(AppConfig):
    """Platform Search app config."""

    name = "platform_search"
    verbose_name = "Platform Search"
    default_auto_field = "django.db.models.BigAutoField"
