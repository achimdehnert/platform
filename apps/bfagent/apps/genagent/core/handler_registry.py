"""
GenAgent Handler Registry - Production-Ready Version
Implements handler discovery, validation, and versioning.
"""

from dataclasses import dataclass
from typing import Dict, Type, List, Any, Optional
import warnings
import logging

logger = logging.getLogger(__name__)


class HandlerNotFoundError(Exception):
    """Raised when a handler is not found in the registry."""
    pass


class VersionMismatchError(Exception):
    """Raised when handler version is incompatible."""
    pass


@dataclass
class HandlerMetadata:
    """Metadata for a registered handler."""
    handler_class: Type
    version: str
    domains: List[str]
    status: str  # active, deprecated, experimental
    dependencies: List[str]
    schema_version: str
    description: Optional[str] = None


class HandlerRegistry:
    """
    Central registry for GenAgent handlers with validation and versioning.
    
    Features:
    - Handler registration with metadata
    - Runtime availability validation
    - Version compatibility checking
    - Domain-based handler discovery
    - Status tracking (active/deprecated/experimental)
    """
    
    _handlers: Dict[str, HandlerMetadata] = {}
    _initialized: bool = False
    
    @classmethod
    def register(
        cls,
        name: str,
        handler_class: Type,
        version: str,
        domains: List[str],
        status: str = "active",
        description: Optional[str] = None
    ) -> None:
        """
        Register a handler with the registry.
        
        Args:
            name: Unique handler identifier
            handler_class: Handler class to register
            version: Semantic version (e.g., "1.0.0")
            domains: List of domains this handler supports
            status: Handler status (active/deprecated/experimental)
            description: Optional description
            
        Raises:
            ValueError: If handler name already exists
        """
        if name in cls._handlers:
            existing = cls._handlers[name]
            if existing.version != version:
                # Log and warn about version overwrite
                msg = f"Overwriting handler '{name}' v{existing.version} with v{version}"
                logger.warning(msg)
                warnings.warn(msg, UserWarning)
            else:
                raise ValueError(f"Handler '{name}' already registered")
        
        # Extract metadata from handler class
        dependencies = getattr(handler_class, 'dependencies', [])
        schema_version = getattr(handler_class, 'schema_version', '1.0.0')
        
        # Validate version format
        if not cls._is_valid_semver(version):
            raise ValueError(f"Invalid semantic version: {version}")
        
        cls._handlers[name] = HandlerMetadata(
            handler_class=handler_class,
            version=version,
            domains=domains,
            status=status,
            dependencies=dependencies,
            schema_version=schema_version,
            description=description
        )
        
        logger.info(
            f"Registered handler '{name}' v{version} for domains: {domains}"
        )
    
    @classmethod
    def validate_availability(cls, handler_name: str) -> bool:
        """
        Validate that a handler is available.
        
        Args:
            handler_name: Name of handler to validate
            
        Returns:
            True if handler is available
            
        Raises:
            HandlerNotFoundError: If handler not registered
        """
        if handler_name not in cls._handlers:
            available = list(cls._handlers.keys())
            raise HandlerNotFoundError(
                f"Handler '{handler_name}' not registered.\n"
                f"Available handlers: {available}"
            )
        
        metadata = cls._handlers[handler_name]
        
        # Warn if deprecated
        if metadata.status == "deprecated":
            warnings.warn(
                f"Handler '{handler_name}' is deprecated. "
                f"Consider using alternatives: {metadata.dependencies}",
                DeprecationWarning
            )
        
        # Warn if experimental
        elif metadata.status == "experimental":
            warnings.warn(
                f"Handler '{handler_name}' is experimental. "
                f"Use with caution in production.",
                UserWarning
            )
        
        return True
    
    @classmethod
    def get_handler_info(cls, handler_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a handler.
        
        Args:
            handler_name: Name of handler
            
        Returns:
            Dictionary with handler metadata
            
        Raises:
            HandlerNotFoundError: If handler not found
        """
        cls.validate_availability(handler_name)
        metadata = cls._handlers[handler_name]
        
        return {
            "name": handler_name,
            "class": metadata.handler_class.__name__,
            "version": metadata.version,
            "domains": metadata.domains,
            "status": metadata.status,
            "dependencies": metadata.dependencies,
            "schema_version": metadata.schema_version,
            "description": metadata.description,
            "module": metadata.handler_class.__module__
        }
    
    @classmethod
    def get_handlers_for_domain(cls, domain: str) -> List[str]:
        """
        Get all active handlers for a specific domain.
        
        Args:
            domain: Domain name (e.g., "book_writing")
            
        Returns:
            List of handler names supporting this domain
        """
        return [
            name for name, meta in cls._handlers.items()
            if domain in meta.domains and meta.status == "active"
        ]
    
    @classmethod
    def get_all_handlers(cls) -> Dict[str, HandlerMetadata]:
        """
        Get all registered handlers.
        
        Returns:
            Dictionary of all handlers with metadata
        """
        return cls._handlers.copy()
    
    @classmethod
    def get_handler_class(cls, handler_name: str) -> Type:
        """
        Get the handler class for instantiation.
        
        Args:
            handler_name: Name of handler
            
        Returns:
            Handler class
            
        Raises:
            HandlerNotFoundError: If handler not found
        """
        cls.validate_availability(handler_name)
        return cls._handlers[handler_name].handler_class
    
    @classmethod
    def check_version_compatibility(
        cls,
        handler_name: str,
        required_version: str
    ) -> bool:
        """
        Check if handler version is compatible with required version.
        
        Args:
            handler_name: Name of handler
            required_version: Required version string
            
        Returns:
            True if compatible
            
        Raises:
            HandlerNotFoundError: If handler not found
            VersionMismatchError: If versions incompatible
        """
        cls.validate_availability(handler_name)
        metadata = cls._handlers[handler_name]
        
        handler_major, handler_minor, _ = cls._parse_semver(metadata.version)
        required_major, required_minor, _ = cls._parse_semver(required_version)
        
        # MAJOR version must match
        if handler_major != required_major:
            raise VersionMismatchError(
                f"Handler '{handler_name}' version {metadata.version} "
                f"incompatible with required version {required_version}. "
                f"Major version mismatch."
            )
        
        # MINOR version must be >= required
        if handler_minor < required_minor:
            raise VersionMismatchError(
                f"Handler '{handler_name}' version {metadata.version} "
                f"incompatible with required version {required_version}. "
                f"Minor version too old."
            )
        
        return True
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered handlers (for testing)."""
        cls._handlers.clear()
        cls._initialized = False
        logger.debug("Handler registry cleared")
    
    @classmethod
    def _is_valid_semver(cls, version: str) -> bool:
        """Validate semantic version format."""
        try:
            parts = version.split(".")
            if len(parts) != 3:
                return False
            major, minor, patch = parts
            int(major), int(minor), int(patch)
            return True
        except (ValueError, AttributeError):
            return False
    
    @classmethod
    def _parse_semver(cls, version: str) -> tuple:
        """Parse semantic version into (major, minor, patch)."""
        parts = version.split(".")
        return int(parts[0]), int(parts[1]), int(parts[2])
    
    @classmethod
    def get_registry_stats(cls) -> Dict[str, Any]:
        """
        Get statistics about the handler registry.
        
        Returns:
            Dictionary with registry statistics
        """
        total = len(cls._handlers)
        by_status = {}
        by_domain = {}
        
        for name, meta in cls._handlers.items():
            # Count by status
            by_status[meta.status] = by_status.get(meta.status, 0) + 1
            
            # Count by domain
            for domain in meta.domains:
                by_domain[domain] = by_domain.get(domain, 0) + 1
        
        return {
            "total_handlers": total,
            "by_status": by_status,
            "by_domain": by_domain,
            "initialized": cls._initialized
        }
