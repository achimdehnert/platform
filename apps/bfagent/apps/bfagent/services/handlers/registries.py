"""
Handler Registries

Centralized registries for all handler types.
Handlers auto-register themselves using decorators.
"""

from typing import Any, Dict, List, Type


class HandlerRegistry:
    """
    Base registry class for handlers.
    """

    _handlers = {}  # Will be overridden by subclasses
    _expected_handler_type = None  # Will be set by subclasses

    @classmethod
    def register(cls, handler_class: Type) -> Type:
        """
        Register a handler class.

        Can be used as decorator:
            @InputHandlerRegistry.register
            class MyHandler(BaseInputHandler):
                ...

        Or directly:
            InputHandlerRegistry.register(MyHandler)

        Args:
            handler_class: Handler class to register

        Returns:
            The handler class (for decorator usage)

        Raises:
            ValueError: If handler_name not defined or already registered
        """
        if handler_class.handler_name is None:
            raise ValueError(f"{handler_class.__name__} must define handler_name")

        # Check handler_type instead of inheritance (avoids circular import)
        expected_type = getattr(cls, "_expected_handler_type", None)
        if expected_type and getattr(handler_class, "handler_type", None) != expected_type:
            raise TypeError(f"{handler_class.__name__} must have handler_type='{expected_type}'")

        handler_name = handler_class.handler_name

        if handler_name in cls._handlers:
            existing = cls._handlers[handler_name]
            raise ValueError(
                f"Handler '{handler_name}' already registered " f"by {existing.__name__}"
            )

        cls._handlers[handler_name] = handler_class
        print(f"✅ Registered {cls.__name__}: {handler_name} ({handler_class.__name__})")

        return handler_class

    @classmethod
    def get(cls, handler_name: str) -> Type:
        """
        Get handler class by name.

        Args:
            handler_name: Name of the handler

        Returns:
            Handler class

        Raises:
            ValueError: If handler not found
        """
        if handler_name not in cls._handlers:
            available = ", ".join(cls._handlers.keys())
            raise ValueError(f"Unknown handler: '{handler_name}'. " f"Available: {available}")
        return cls._handlers[handler_name]

    @classmethod
    def get_all(cls) -> Dict[str, Type]:
        """
        Get all registered handlers.

        Returns:
            Dictionary of {handler_name: handler_class}
        """
        return cls._handlers.copy()

    @classmethod
    def get_handler_info(cls) -> List[Dict[str, Any]]:
        """
        Get info about all handlers for UI/API.

        Returns:
            List of handler info dictionaries
        """
        info_list = []

        for handler_name, handler_class in cls._handlers.items():
            info = {
                "name": handler_name,
                "class_name": handler_class.__name__,
                "description": handler_class.description,
                "version": handler_class.handler_version,
                "type": handler_class.handler_type,
            }

            # Add capability flags for output handlers
            if hasattr(handler_class, "supports_multiple_objects"):
                info["supports_multiple_objects"] = handler_class.supports_multiple_objects
                info["supports_nested_data"] = handler_class.supports_nested_data
                info["supports_validation"] = handler_class.supports_validation
                info["supports_preview"] = handler_class.supports_preview
                info["supports_rollback"] = handler_class.supports_rollback

            info_list.append(info)

        return info_list

    @classmethod
    def list_handlers(cls) -> List[str]:
        """
        Get list of all registered handler names.

        Returns:
            List of handler names
        """
        return list(cls._handlers.keys())


class InputHandlerRegistry(HandlerRegistry):
    """Registry for input handlers"""

    _handlers = {}  # Each subclass needs its own dict
    _expected_handler_type = "input"


class ProcessingHandlerRegistry(HandlerRegistry):
    """Registry for processing handlers"""

    _handlers = {}  # Each subclass needs its own dict
    _expected_handler_type = "processing"


class OutputHandlerRegistry(HandlerRegistry):
    """Registry for output handlers"""

    _handlers = {}  # Each subclass needs its own dict
    _expected_handler_type = "output"


def get_all_handlers() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get info about all handlers across all registries.

    Useful for admin UI and API endpoints.

    Returns:
        Dictionary with:
        {
            "input": [...handler info...],
            "processing": [...handler info...],
            "output": [...handler info...]
        }
    """
    return {
        "input": InputHandlerRegistry.get_handler_info(),
        "processing": ProcessingHandlerRegistry.get_handler_info(),
        "output": OutputHandlerRegistry.get_handler_info(),
    }


def auto_register_handlers():
    """
    Auto-register all handlers from standard locations.
    Called automatically by Django AppConfig.ready()
    """
    import logging

    logger = logging.getLogger(__name__)

    # Import and register input handlers
    try:
        from .input import (
            ChapterDataHandler,
            CharacterDataHandler,
            ProjectFieldsInputHandler,
            UserInputHandler,
            WorldDataHandler,
        )

        InputHandlerRegistry.register(ProjectFieldsInputHandler)
        InputHandlerRegistry.register(ChapterDataHandler)
        InputHandlerRegistry.register(CharacterDataHandler)
        InputHandlerRegistry.register(UserInputHandler)
        InputHandlerRegistry.register(WorldDataHandler)

        logger.info("Input handlers registered: 5")
    except ImportError as e:
        logger.warning(f"Failed to register input handlers: {e}")

    # Import and register processing handlers
    try:
        from .processing import (
            FrameworkGeneratorHandler,
            LLMProcessingHandler,
            TemplateRendererHandler,
        )

        ProcessingHandlerRegistry.register(TemplateRendererHandler)
        ProcessingHandlerRegistry.register(LLMProcessingHandler)
        ProcessingHandlerRegistry.register(FrameworkGeneratorHandler)

        logger.info("Processing handlers registered: 3")
    except ImportError as e:
        logger.warning(f"Failed to register processing handlers: {e}")

    # Import and register output handlers
    try:
        from .output import ChapterCreatorHandler, MarkdownExporter, SimpleTextFieldHandler

        OutputHandlerRegistry.register(SimpleTextFieldHandler)
        OutputHandlerRegistry.register(ChapterCreatorHandler)
        OutputHandlerRegistry.register(MarkdownExporter)

        logger.info("Output handlers registered: 3")
    except ImportError as e:
        logger.warning(f"Failed to register output handlers: {e}")


# Convenience aliases for common usage
input_registry = InputHandlerRegistry
processing_registry = ProcessingHandlerRegistry
output_registry = OutputHandlerRegistry
