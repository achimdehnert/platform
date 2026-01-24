"""
Central Handler Registry

Provides registration and discovery of handlers across all domains.

Usage:
    # Register a handler
    @register_handler("bookwriting.book.create", "1.0.0")
    class BookCreateHandler(BaseHandler):
        pass

    # Get a handler
    handler = get_handler("bookwriting.book.create")
    result = handler.execute(context)
"""

import logging
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class HandlerRegistry:
    """
    Central registry for all handlers

    Stores handlers by name with versioning support.
    Supports domain-based organization.
    """

    _handlers: Dict[str, Dict[str, Any]] = {}
    _initialized = False

    def __init__(self):
        self._handlers: Dict[str, Dict[str, Any]] = {}
        self._handlers_by_domain: Dict[str, List[str]] = {}
        self._handler_metadata: Dict[str, Dict[str, Any]] = {}

        # Auto-register domain handlers
        self._register_bookwriting_handlers()

    def _register_bookwriting_handlers(self) -> None:
        """
        Register all BookWriting domain handlers.

        Called automatically during initialization.
        """
        try:
            from apps.core.handlers.domains.bookwriting import (
                ChapterEnrichmentHandler,
                ChapterGenerateHandler,
                CharacterCastHandler,
                CharacterEnrichmentHandler,
                ProjectEnrichmentHandler,
            )

            # Register enrichment handlers
            self.register(
                "bookwriting.project.enrich",
                "1.0.0",
                ProjectEnrichmentHandler,
                domain="bookwriting",
                description="Enriches book projects using AI agents",
            )

            self.register(
                "bookwriting.chapter.enrich",
                "1.0.0",
                ChapterEnrichmentHandler,
                domain="bookwriting",
                description="Enriches book chapters using AI agents",
            )

            self.register(
                "bookwriting.character.enrich",
                "1.0.0",
                CharacterEnrichmentHandler,
                domain="bookwriting",
                description="Enriches characters using AI agents",
            )

            # Register generation handlers
            self.register(
                "bookwriting.chapter.generate",
                "1.0.0",
                ChapterGenerateHandler,
                domain="bookwriting",
                description="Generates new chapters for book projects",
            )

            self.register(
                "bookwriting.character.cast",
                "1.0.0",
                CharacterCastHandler,
                domain="bookwriting",
                description="Generates character cast for book projects",
            )

            logger.info("Registered 5 BookWriting domain handlers")

        except ImportError as e:
            logger.error(f"Failed to register BookWriting handlers: {e}")

    @classmethod
    def register(
        cls,
        name: str,
        version: str,
        handler_class: Type,
        domain: Optional[str] = None,
        description: Optional[str] = None,
        **metadata,
    ) -> None:
        """
        Register a handler

        Args:
            name: Handler identifier (e.g., "bookwriting.book.create")
            version: Handler version (e.g., "1.0.0")
            handler_class: Handler class to register
            domain: Domain name (extracted from name if not provided)
            description: Handler description
            **metadata: Additional metadata
        """
        # Extract domain from name if not provided
        if domain is None and "." in name:
            domain = name.split(".")[0]

        cls._handlers[name] = {
            "class": handler_class,
            "version": version,
            "domain": domain,
            "description": description or handler_class.__doc__,
            "name": name,
            **metadata,
        }

        logger.info(f"Registered handler '{name}' v{version} (domain: {domain})")

    @classmethod
    def get(cls, name: str) -> Optional[Any]:
        """
        Get handler instance by name

        Args:
            name: Handler name

        Returns:
            Handler instance or None if not found
        """
        handler_info = cls._handlers.get(name)
        if handler_info:
            handler_class = handler_info["class"]
            return handler_class()
        return None

    @classmethod
    def get_info(cls, name: str) -> Optional[Dict[str, Any]]:
        """
        Get handler metadata

        Args:
            name: Handler name

        Returns:
            Handler metadata dict or None
        """
        return cls._handlers.get(name)

    @classmethod
    def list_all(cls) -> Dict[str, Dict[str, Any]]:
        """
        List all registered handlers

        Returns:
            Dict of handler name -> metadata
        """
        return cls._handlers.copy()

    @classmethod
    def list_by_domain(cls, domain: str) -> Dict[str, Dict[str, Any]]:
        """
        List handlers by domain

        Args:
            domain: Domain name (e.g., "bookwriting", "medtrans")

        Returns:
            Dict of handler name -> metadata for the domain
        """
        return {name: info for name, info in cls._handlers.items() if info.get("domain") == domain}

    @classmethod
    def exists(cls, name: str) -> bool:
        """
        Check if handler exists

        Args:
            name: Handler name

        Returns:
            True if handler is registered
        """
        return name in cls._handlers

    @classmethod
    def get_domains(cls) -> list[str]:
        """
        Get list of all domains with registered handlers

        Returns:
            List of domain names
        """
        domains = set()
        for info in cls._handlers.values():
            domain = info.get("domain")
            if domain:
                domains.add(domain)
        return sorted(list(domains))

    def list_handlers(self, domain: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Instance method to list handlers (for convenience).

        Args:
            domain: Optional domain filter

        Returns:
            Dict of handler name -> metadata
        """
        if domain:
            return self.list_by_domain(domain)
        return self.list_all()

    def list_domains(self) -> list[str]:
        """
        Instance method to list domains (for convenience).

        Returns:
            List of domain names
        """
        return self.get_domains()

    @classmethod
    def clear(cls) -> None:
        """Clear all registered handlers (for testing)"""
        cls._handlers.clear()

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """
        Get registry statistics

        Returns:
            Dict with counts by domain and total
        """
        domains = {}
        for info in cls._handlers.values():
            domain = info.get("domain", "unknown")
            domains[domain] = domains.get(domain, 0) + 1

        return {
            "total": len(cls._handlers),
            "domains": domains,
            "handler_names": list(cls._handlers.keys()),
        }


def register_handler(name: str, version: str = "1.0.0", **metadata):
    """
    Decorator to register a handler

    Args:
        name: Handler identifier (e.g., "bookwriting.book.create")
        version: Handler version
        **metadata: Additional metadata

    Usage:
        @register_handler("bookwriting.book.create", "1.0.0")
        class BookCreateHandler(BaseHandler):
            def execute(self, context):
                return {'status': 'success'}
    """

    def decorator(handler_class):
        HandlerRegistry.register(
            name=name, version=version, handler_class=handler_class, **metadata
        )
        return handler_class

    return decorator


def get_handler(name: str) -> Optional[Any]:
    """
    Get handler instance by name

    Args:
        name: Handler name

    Returns:
        Handler instance or None

    Usage:
        handler = get_handler("bookwriting.book.create")
        result = handler.execute(context)
    """
    return HandlerRegistry.get(name)
