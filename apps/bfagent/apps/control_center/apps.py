from django.apps import AppConfig


class ControlCenterConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.control_center"
    verbose_name = "BF Agent Control Center"

    def ready(self):
        """Initialize the control center when Django starts"""
        from .registry import tool_registry

        tool_registry.discover_tools()
