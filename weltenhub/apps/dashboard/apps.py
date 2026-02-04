"""Dashboard app configuration."""

from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """Dashboard app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboard"
    verbose_name = "Dashboard"
