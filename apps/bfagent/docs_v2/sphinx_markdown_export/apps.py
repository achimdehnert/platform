"""
Django App Configuration für Sphinx Markdown Export.
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SphinxMarkdownExportConfig(AppConfig):
    """App-Konfiguration für Sphinx Markdown Export."""
    
    name = 'sphinx_markdown_export'
    verbose_name = _('Sphinx Markdown Export')
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        """Wird aufgerufen wenn die App geladen ist."""
        # Hier könnten Signals registriert werden
        pass
