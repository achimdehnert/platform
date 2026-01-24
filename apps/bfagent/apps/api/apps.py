"""
API App Configuration
"""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api"
    verbose_name = "MCP Orchestration API"

    def ready(self):
        """Import signals and setup when app is ready"""
        pass
