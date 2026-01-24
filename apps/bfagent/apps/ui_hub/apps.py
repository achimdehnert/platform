"""UI Hub app configuration."""

from django.apps import AppConfig


class UiHubConfig(AppConfig):
    """UI Hub app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ui_hub"
    label = "ui_hub"
    verbose_name = "UI Hub - HTMX Guardrails"

    def ready(self):
        """Initialize app on startup."""
        # Import admin to ensure registration
        from . import admin
