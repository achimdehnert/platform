"""
GenAgent App Configuration
"""

from django.apps import AppConfig


class GenagentConfig(AppConfig):
    """GenAgent - General Agent Framework"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.genagent'
    verbose_name = "GenAgent Framework"
    
    def ready(self):
        """Initialize GenAgent components on startup"""
        # Import handlers to register them
        try:
            from apps.genagent.handlers import demo_handlers  # noqa: F401
            print(" GenAgent handlers registered")
            
            # Initialize new HandlerRegistry system
            from apps.genagent import initialize_handler_registry
            initialize_handler_registry()
        except ImportError as e:
            print(f" GenAgent handlers not yet available: {e}")
