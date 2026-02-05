"""
Django app configuration for PPTX-Hub.
"""

from django.apps import AppConfig


class PptxHubConfig(AppConfig):
    """Django app configuration."""
    
    name = "pptx_hub.django"
    label = "pptx_hub"
    verbose_name = "PPTX Hub"
    default_auto_field = "django.db.models.BigAutoField"
    
    def ready(self) -> None:
        """Initialize app when Django starts."""
        # Import signals if any
        pass
