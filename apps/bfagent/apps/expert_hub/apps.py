"""
App configuration for Expert Hub
"""

from django.apps import AppConfig


class ExpertHubConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.expert_hub"
    verbose_name = "Expert Hub"
