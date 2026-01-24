"""
Core Handler Registry
=====================

Centralized registry for handler discovery and management.
Consolidates registry implementations from:
- apps/core/handlers/registry.py
- apps/bfagent/services/handlers/registries.py
- apps/genagent/handlers/__init__.py

Features:
- Decorator-based registration
- Domain-based organization
- Version tracking
- Metadata support
- Type-specific registries (input, processing, output)

Usage:
    from apps.core.handlers import register_handler, get_handler

    @register_handler("book.create", "1.0.0", domain="writing")
    class BookCreateHandler(ProcessingHandler):
        def process(self, data, context):
            return {'book_id': 123}

    # Later...
    handler = get_handler("book.create")
    result = handler.execute(context)
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Type

from .exceptions import RegistryError

logger = logging.getLogger(__name__)


class HandlerRegistry:
    """
    Central registry for all handlers.

    Provides:
    - Registration of handlers with metadata
    - Lookup by name, domain, or type
    - Version tracking
    - Statistics and reporting

    This is a class-level registry - all instances share the same data.

    Example:
        # Register a handler
        HandlerRegistry.register(
            name="book.create",
            version="1.0.0",
            handler_class=BookCreateHandler,
            domain="writing",
            handler_type="processing"
        )

        # Get a handler
        handler = HandlerRegistry.get("book.create")

        # List handlers
        handlers = HandlerRegistry.list_by_domain("writing")
    """

    # Class-level storage
    _handlers: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(
        cls,
        name: str,
        handler_class: Type,
        version: str = "1.0.0",
        domain: str = "core",
        handler_type: str = None,
        description: str = None,
        **metadata,
    ) -> None:
        """
        Register a handler in the registry.

        Args:
            name: Unique handler identifier (e.g., "book.create")
            handler_class: The handler class to register
            version: Semantic version string
            domain: Domain this handler belongs to
            handler_type: Type classification (input/processing/output)
            description: Human-readable description
            **metadata: Additional metadata

        Raises:
            RegistryError: If handler name already registered
        """
        if name in cls._handlers:
            existing = cls._handlers[name]
            logger.warning(
                f"Handler '{name}' already registered (v{existing.get('version')}). "
                f"Overwriting with v{version}"
            )

        # Auto-detect handler_type from class if not provided
        if handler_type is None:
            handler_type = getattr(handler_class, "handler_type", "unknown")

        # Auto-detect description from class if not provided
        if description is None:
            description = getattr(handler_class, "description", None) or handler_class.__doc__ or ""

        cls._handlers[name] = {
            "name": name,
            "class": handler_class,
            "version": version,
            "domain": domain,
            "handler_type": handler_type,
            "description": description,
            "module": handler_class.__module__,
            "class_name": handler_class.__name__,
            **metadata,
        }

        logger.debug(f"Registered handler: {name} v{version} ({handler_type}) in domain '{domain}'")

    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        Remove a handler from the registry.

        Args:
            name: Handler name to remove

        Returns:
            True if removed, False if not found
        """
        if name in cls._handlers:
            del cls._handlers[name]
            logger.debug(f"Unregistered handler: {name}")
            return True
        return False

    @classmethod
    def get(cls, name: str, instantiate: bool = True, config: Dict = None) -> Optional[Any]:
        """
        Get a handler by name.

        Args:
            name: Handler identifier
            instantiate: If True, return instance; if False, return class
            config: Configuration to pass to handler constructor

        Returns:
            Handler instance/class or None if not found
        """
        if name not in cls._handlers:
            logger.warning(f"Handler not found: {name}")
            return None

        handler_info = cls._handlers[name]
        handler_class = handler_info["class"]

        if instantiate:
            try:
                return handler_class(config=config or {})
            except TypeError:
                # Handler doesn't accept config
                return handler_class()

        return handler_class

    @classmethod
    def get_info(cls, name: str) -> Optional[Dict[str, Any]]:
        """
        Get handler metadata without instantiating.

        Args:
            name: Handler identifier

        Returns:
            Handler metadata dict or None
        """
        return cls._handlers.get(name)

    @classmethod
    def exists(cls, name: str) -> bool:
        """Check if a handler is registered."""
        return name in cls._handlers

    @classmethod
    def list_all(cls) -> Dict[str, Dict[str, Any]]:
        """Get all registered handlers."""
        return cls._handlers.copy()

    @classmethod
    def list_by_domain(cls, domain: str) -> Dict[str, Dict[str, Any]]:
        """
        Get handlers for a specific domain.

        Args:
            domain: Domain name to filter by

        Returns:
            Dict of handler name -> metadata
        """
        return {name: info for name, info in cls._handlers.items() if info.get("domain") == domain}

    @classmethod
    def list_by_type(cls, handler_type: str) -> Dict[str, Dict[str, Any]]:
        """
        Get handlers of a specific type.

        Args:
            handler_type: Type to filter by (input/processing/output)

        Returns:
            Dict of handler name -> metadata
        """
        return {
            name: info
            for name, info in cls._handlers.items()
            if info.get("handler_type") == handler_type
        }

    @classmethod
    def get_domains(cls) -> List[str]:
        """Get list of all registered domains."""
        domains = set()
        for info in cls._handlers.values():
            domains.add(info.get("domain", "unknown"))
        return sorted(domains)

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dict with counts by domain, type, and total
        """
        domains = {}
        types = {}

        for info in cls._handlers.values():
            domain = info.get("domain", "unknown")
            handler_type = info.get("handler_type", "unknown")

            domains[domain] = domains.get(domain, 0) + 1
            types[handler_type] = types.get(handler_type, 0) + 1

        return {
            "total": len(cls._handlers),
            "by_domain": domains,
            "by_type": types,
            "domains": sorted(domains.keys()),
            "types": sorted(types.keys()),
        }

    @classmethod
    def clear(cls) -> None:
        """Clear all registered handlers (for testing)."""
        cls._handlers.clear()
        logger.debug("Handler registry cleared")

    # ==================== Instance Methods (for convenience) ====================

    def __init__(self):
        """Initialize registry instance (shares class-level data)."""
        pass

    def register_handler(self, name: str, handler_class: Type, **kwargs) -> None:
        """Instance method wrapper for register()."""
        self.register(name, handler_class, **kwargs)

    def get_handler(self, name: str, **kwargs) -> Optional[Any]:
        """Instance method wrapper for get()."""
        return self.get(name, **kwargs)

    def list_handlers(self, domain: str = None, handler_type: str = None) -> Dict[str, Dict]:
        """
        List handlers with optional filters.

        Args:
            domain: Filter by domain
            handler_type: Filter by type

        Returns:
            Dict of matching handlers
        """
        result = self.list_all()

        if domain:
            result = {k: v for k, v in result.items() if v.get("domain") == domain}

        if handler_type:
            result = {k: v for k, v in result.items() if v.get("handler_type") == handler_type}

        return result


# ==================== Type-Specific Registries ====================


class InputHandlerRegistry(HandlerRegistry):
    """Registry specifically for input handlers."""

    _handlers: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, name: str, handler_class: Type, **kwargs) -> None:
        kwargs["handler_type"] = "input"
        super().register(name, handler_class, **kwargs)


class ProcessingHandlerRegistry(HandlerRegistry):
    """Registry specifically for processing handlers."""

    _handlers: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, name: str, handler_class: Type, **kwargs) -> None:
        kwargs["handler_type"] = "processing"
        super().register(name, handler_class, **kwargs)


class OutputHandlerRegistry(HandlerRegistry):
    """Registry specifically for output handlers."""

    _handlers: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, name: str, handler_class: Type, **kwargs) -> None:
        kwargs["handler_type"] = "output"
        super().register(name, handler_class, **kwargs)


# ==================== Convenience Instances ====================

# Global registry instances
input_registry = InputHandlerRegistry()
processing_registry = ProcessingHandlerRegistry()
output_registry = OutputHandlerRegistry()


def get_all_handlers() -> Dict[str, List[str]]:
    """
    Get all handlers organized by type.

    Returns:
        Dict with 'input', 'processing', 'output' keys
    """
    return {
        "input": list(InputHandlerRegistry.list_all().keys()),
        "processing": list(ProcessingHandlerRegistry.list_all().keys()),
        "output": list(OutputHandlerRegistry.list_all().keys()),
        "all": list(HandlerRegistry.list_all().keys()),
    }


# ==================== Decorator ====================


def register_handler(
    name: str, version: str = "1.0.0", domain: str = "core", handler_type: str = None, **metadata
) -> Callable:
    """
    Decorator to register a handler class.

    Args:
        name: Unique handler identifier
        version: Semantic version string
        domain: Domain this handler belongs to
        handler_type: Type classification (auto-detected if not provided)
        **metadata: Additional metadata

    Usage:
        @register_handler("book.create", "1.0.0", domain="writing")
        class BookCreateHandler(ProcessingHandler):
            def process(self, data, context):
                return {'book_id': 123}

    Returns:
        Decorator function
    """

    def decorator(handler_class: Type) -> Type:
        # Determine handler type
        actual_type = handler_type
        if actual_type is None:
            actual_type = getattr(handler_class, "handler_type", "processing")

        # Register in main registry
        HandlerRegistry.register(
            name=name,
            handler_class=handler_class,
            version=version,
            domain=domain,
            handler_type=actual_type,
            **metadata,
        )

        # Also register in type-specific registry
        if actual_type == "input":
            InputHandlerRegistry.register(
                name, handler_class, version=version, domain=domain, **metadata
            )
        elif actual_type == "processing":
            ProcessingHandlerRegistry.register(
                name, handler_class, version=version, domain=domain, **metadata
            )
        elif actual_type == "output":
            OutputHandlerRegistry.register(
                name, handler_class, version=version, domain=domain, **metadata
            )

        # Store registration info on class
        handler_class._registry_name = name
        handler_class._registry_version = version
        handler_class._registry_domain = domain

        return handler_class

    return decorator


# ==================== Shortcut Functions ====================


def get_handler(name: str, config: Dict = None) -> Optional[Any]:
    """
    Get handler instance by name.

    Shortcut for HandlerRegistry.get()

    Args:
        name: Handler identifier
        config: Configuration for handler

    Returns:
        Handler instance or None
    """
    return HandlerRegistry.get(name, instantiate=True, config=config)


def get_handler_class(name: str) -> Optional[Type]:
    """
    Get handler class by name (without instantiating).

    Args:
        name: Handler identifier

    Returns:
        Handler class or None
    """
    return HandlerRegistry.get(name, instantiate=False)


def list_handlers(domain: str = None, handler_type: str = None) -> Dict[str, Dict]:
    """
    List registered handlers with optional filters.

    Args:
        domain: Filter by domain
        handler_type: Filter by type

    Returns:
        Dict of handler name -> metadata
    """
    result = HandlerRegistry.list_all()

    if domain:
        result = {k: v for k, v in result.items() if v.get("domain") == domain}

    if handler_type:
        result = {k: v for k, v in result.items() if v.get("handler_type") == handler_type}

    return result
