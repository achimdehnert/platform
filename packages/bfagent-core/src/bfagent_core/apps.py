"""Django app configuration for bfagent_core."""

from django.apps import AppConfig


class BfagentCoreConfig(AppConfig):
    """Django app config for bfagent-core."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "bfagent_core"
    verbose_name = "BFAgent Core"
