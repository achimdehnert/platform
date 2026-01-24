"""Django App Configuration für Sphinx Export."""

from django.apps import AppConfig


class SphinxExportConfig(AppConfig):
    """App-Konfiguration für Sphinx Markdown Export."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sphinx_export'
    verbose_name = 'Sphinx Markdown Export'
    
    def ready(self):
        """App ist bereit - MCP Tools registrieren."""
        pass
