"""
Core Handlers - Unified Handler System for BF Agent
====================================================

This module provides the centralized handler system used by all domain
applications (writing, medtrans, genagent, expert, etc.).

Architecture:
    BaseHandler (ABC)
    ├── InputHandler     - Data collection from sources
    ├── ProcessingHandler - Business logic & transformations
    └── OutputHandler    - Persistence & output formatting

Quick Start:
    from apps.core.handlers import (
        ProcessingHandler,
        register_handler,
        get_handler
    )

    @register_handler("book.create", "1.0.0", domain="writing")
    class BookCreateHandler(ProcessingHandler):
        handler_name = "book.create"

        def process(self, data, context):
            return {'book_id': 123}

    # Later, use the handler:
    handler = get_handler("book.create")
    result = handler.execute({'title': 'My Book'})

Components:
    - base.py: Base handler classes
    - registry.py: Handler registration and lookup
    - decorators.py: Logging, performance, caching decorators
    - exceptions.py: Handler exception hierarchy

Migration Notes:
    This module consolidates handlers from:
    - apps/core/handlers/ (original)
    - apps/bfagent/handlers/
    - apps/bfagent/services/handlers/
    - apps/genagent/handlers/

    Backward compatibility aliases are provided for existing imports.
"""

# ==================== Base Classes ====================
from .base import (  # Backward compatibility aliases
    BaseHandler,
    BaseInputHandler,
    BaseOutputHandler,
    BaseProcessingHandler,
    GenAgentBaseHandler,
    InputHandler,
    OutputHandler,
    ProcessingHandler,
)

# ==================== Decorators ====================
from .decorators import (
    deprecated,
    measure_tokens,
    retry_on_failure,
    validate_context,
    with_caching,
    with_logging,
    with_performance_monitoring,
)

# ==================== Exceptions ====================
from .exceptions import (
    ConfigurationException,
    HandlerException,
    InputHandlerException,
    OutputHandlerException,
    ProcessingError,
    RegistryError,
    RetryableError,
    TimeoutError,
    ValidationError,
)

# ==================== Registry ====================
from .registry import (  # Convenience instances; Functions
    HandlerRegistry,
    InputHandlerRegistry,
    OutputHandlerRegistry,
    ProcessingHandlerRegistry,
    get_all_handlers,
    get_handler,
    get_handler_class,
    input_registry,
    list_handlers,
    output_registry,
    processing_registry,
    register_handler,
)

# ==================== Public API ====================
__all__ = [
    # Base Classes
    "BaseHandler",
    "InputHandler",
    "ProcessingHandler",
    "OutputHandler",
    # Backward Compatibility
    "BaseInputHandler",
    "BaseProcessingHandler",
    "BaseOutputHandler",
    "GenAgentBaseHandler",
    # Registry
    "HandlerRegistry",
    "InputHandlerRegistry",
    "ProcessingHandlerRegistry",
    "OutputHandlerRegistry",
    "input_registry",
    "processing_registry",
    "output_registry",
    "register_handler",
    "get_handler",
    "get_handler_class",
    "list_handlers",
    "get_all_handlers",
    # Decorators
    "with_logging",
    "with_performance_monitoring",
    "retry_on_failure",
    "with_caching",
    "validate_context",
    "measure_tokens",
    "deprecated",
    # Exceptions
    "HandlerException",
    "ValidationError",
    "ProcessingError",
    "ConfigurationException",
    "InputHandlerException",
    "OutputHandlerException",
    "RegistryError",
    "TimeoutError",
    "RetryableError",
]


# ==================== Version ====================
__version__ = "2.0.0"
__author__ = "BF Agent Team"


# ==================== Module Info ====================
def get_module_info() -> dict:
    """
    Get information about the handlers module.

    Returns:
        Dict with version, registered handlers, and statistics
    """
    return {
        "version": __version__,
        "registry_stats": HandlerRegistry.get_stats(),
        "available_decorators": [
            "with_logging",
            "with_performance_monitoring",
            "retry_on_failure",
            "with_caching",
            "validate_context",
            "measure_tokens",
            "deprecated",
        ],
        "handler_types": ["input", "processing", "output"],
        "base_classes": ["BaseHandler", "InputHandler", "ProcessingHandler", "OutputHandler"],
    }
