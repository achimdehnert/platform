"""Django app configuration for content_store (ADR-130)."""

from django.apps import AppConfig


class ContentStoreConfig(AppConfig):
    """Shared content persistence app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "content_store"
    verbose_name = "Content Store"
