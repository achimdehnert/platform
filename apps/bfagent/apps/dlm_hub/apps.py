"""DLM Hub app configuration."""

from django.apps import AppConfig


class DlmHubConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dlm_hub"
    label = "dlm_hub"
    verbose_name = "DLM Hub"
