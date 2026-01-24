"""
Writing Hub App Configuration
"""

from django.apps import AppConfig


class WritingHubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.writing_hub'
    verbose_name = 'Writing Hub'
    label = 'writing_hub'
