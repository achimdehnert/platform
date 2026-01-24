"""Django App Configuration for BF Agent MCP."""

from django.apps import AppConfig


class BfagentMcpConfig(AppConfig):
    """Configuration for bfagent_mcp Django app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bfagent_mcp'
    verbose_name = 'BF Agent MCP'
    
    def ready(self):
        """Initialize the app when Django starts."""
        # Import models to ensure they're registered
        from . import models
        from . import models_mcp
        from . import models_naming
        from . import models_extension
