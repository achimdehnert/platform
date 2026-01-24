"""MCP Django App Configuration"""

from django.apps import AppConfig


class MCPConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bfagent.mcp'
    verbose_name = 'MCP SQLite Server'
    
    def ready(self):
        """Initialize MCP components when Django starts."""
        pass
