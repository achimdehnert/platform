"""
BF Agent App Configuration
"""

from django.apps import AppConfig


class BfagentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.bfagent'
    verbose_name = 'BF Agent'
    
    def ready(self):
        """
        Initialize handlers and signals when Django starts.
        """
        # Auto-register all handlers
        try:
            from .services.handlers.registries import auto_register_handlers
            auto_register_handlers()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to auto-register handlers: {e}")
        
        # Import signals to register them
        try:
            from . import signals  # noqa: F401
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to register signals: {e}")