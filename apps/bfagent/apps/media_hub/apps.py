"""
Media Hub App Configuration
"""

from django.apps import AppConfig


class MediaHubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.media_hub'
    label = 'media_hub'
    verbose_name = 'Media Hub'
    
    def ready(self):
        # Import signal handlers if needed
        pass
