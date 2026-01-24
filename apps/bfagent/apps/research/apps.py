"""
Research Hub - App Configuration
"""

from django.apps import AppConfig


class ResearchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.research'
    label = 'research'
    verbose_name = 'Research Hub'
    
    def ready(self):
        # Import handlers for auto-registration
        try:
            from . import handlers  # noqa
        except ImportError:
            pass
