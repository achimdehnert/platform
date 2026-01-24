"""
GenAgent Application

Phase 1 - Handler Registry System
"""

default_app_config = 'apps.genagent.apps.GenagentConfig'


def initialize_handler_registry():
    """
    Initialize HandlerRegistry with demo handlers
    Called automatically on app startup
    """
    from apps.genagent.core.handler_registry import HandlerRegistry
    from apps.genagent.handlers import list_handlers
    
    # Register all handlers from old system to new system
    for handler_path, handler_class in list_handlers().items():
        # Extract domain from module path
        module_parts = handler_path.split('.')
        if 'demo_handlers' in module_parts:
            domain = 'demo'
        elif 'book' in module_parts:
            domain = 'book_writing'
        else:
            domain = 'general'
        
        # Register with new system
        HandlerRegistry.register(
            name=handler_path,
            handler_class=handler_class,
            version='1.0.0',
            domains=[domain],
            status='active',
            description=handler_class.get_description()
        )
    
    HandlerRegistry._initialized = True
    print(f"[OK] Initialized HandlerRegistry with {len(list_handlers())} handlers")
