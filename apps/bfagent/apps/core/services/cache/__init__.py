"""
Core Cache Service

Unified caching system with multiple backend support.

Features:
    - Multiple backends: Memory, Django, File, Redis
    - Consistent API across all backends
    - TTL and tag-based invalidation
    - Statistics and monitoring
    - Thread-safe operations
    - Decorator for function caching

Quick Start:
    from apps.core.services.cache import cache, cached

    # Use default cache
    cache.set("key", "value", ttl=3600)
    value = cache.get("key")

    # Decorator
    @cached(ttl=300)
    def expensive_function(arg):
        return compute(arg)

Backends:
    - MEMORY: In-memory dict (testing/single-process)
    - DJANGO: Django's cache framework (Redis/Memcached)
    - FILE: JSON file-based (persistence without Redis)
    - REDIS: Direct Redis connection

Configuration:
    # Django settings
    CACHE_BACKEND = "django"  # or "memory", "file", "redis"
    CACHE_DEFAULT_TTL = 300
    CACHE_KEY_PREFIX = "myapp"
    REDIS_URL = "redis://localhost:6379/0"

Migration from existing code:
    # Old: from django.core.cache import cache
    # New: from apps.core.services.cache import cache

    # Old: @with_caching(cache_key_prefix="data", ttl=300)
    # New: @cached(ttl=300, key_prefix="data")
"""

from typing import Any, Dict, Optional

from .backends import (
    DjangoCacheBackend,
    FileCacheBackend,
    MemoryCacheBackend,
    RedisCacheBackend,
    create_backend,
)
from .base import BaseCacheBackend, cached
from .exceptions import (
    CacheBackendError,
    CacheBackendNotAvailableError,
    CacheBackendNotConfiguredError,
    CacheConfigurationError,
    CacheConnectionError,
    CacheDeserializationError,
    CacheException,
    CacheKeyError,
    CacheKeyExistsError,
    CacheKeyNotFoundError,
    CacheLockError,
    CacheLockTimeoutError,
    CacheOperationError,
    CacheSerializationError,
    CacheTimeoutError,
    CacheValueError,
    CacheValueTooLargeError,
    CacheVersionError,
    InvalidCacheKeyError,
    InvalidTTLError,
    is_cache_error,
    is_retriable_error,
)
from .models import (
    CacheBackend,
    CacheConfig,
    CacheEntry,
    CacheStats,
    CacheStrategy,
    generate_cache_key,
)

# =============================================================================
# Global Cache Instance
# =============================================================================

_default_cache: Optional[BaseCacheBackend] = None
_cache_lock = __import__("threading").Lock()


def get_cache(
    backend: Optional[str] = None, config: Optional[CacheConfig] = None, **kwargs
) -> BaseCacheBackend:
    """
    Get or create a cache backend instance.

    Args:
        backend: Backend type ("memory", "django", "file", "redis")
                 If None, auto-detects from settings
        config: Cache configuration
        **kwargs: Additional backend-specific arguments

    Returns:
        Cache backend instance

    Example:
        # Auto-detect (uses Django settings or defaults to memory)
        cache = get_cache()

        # Explicit backend
        cache = get_cache("redis", config=CacheConfig(
            redis_url="redis://localhost:6379"
        ))
    """
    global _default_cache

    # If requesting default cache, return cached instance
    if backend is None and config is None and not kwargs:
        if _default_cache is not None:
            return _default_cache

        with _cache_lock:
            if _default_cache is None:
                _default_cache = _create_default_cache()
            return _default_cache

    # Create new cache instance
    return _create_cache(backend, config, **kwargs)


def _detect_backend() -> CacheBackend:
    """Auto-detect best available cache backend."""
    # Try Django settings first
    try:
        from django.conf import settings

        backend_name = getattr(settings, "CACHE_BACKEND", None)

        if backend_name:
            return CacheBackend(backend_name)

        # Check if Django cache is configured
        caches = getattr(settings, "CACHES", {})
        if caches:
            return CacheBackend.DJANGO
    except ImportError:
        pass

    # Try Redis
    try:
        import redis

        return CacheBackend.REDIS
    except ImportError:
        pass

    # Default to memory
    return CacheBackend.MEMORY


def _create_default_cache() -> BaseCacheBackend:
    """Create default cache from settings or auto-detect."""
    backend_type = _detect_backend()
    config = CacheConfig.from_django_settings()

    return create_backend(backend_type, config)


def _create_cache(
    backend: Optional[str], config: Optional[CacheConfig], **kwargs
) -> BaseCacheBackend:
    """Create a cache backend instance."""
    if backend is None:
        backend_type = _detect_backend()
    else:
        backend_type = CacheBackend(backend)

    if config is None:
        config = CacheConfig.from_django_settings()

    return create_backend(backend_type, config, **kwargs)


def reset_cache() -> None:
    """Reset the global cache instance."""
    global _default_cache
    with _cache_lock:
        if _default_cache:
            _default_cache.clear()
        _default_cache = None


# =============================================================================
# Convenience Functions
# =============================================================================


def get(key: str, default: Any = None) -> Any:
    """Get a value from the default cache."""
    return get_cache().get(key, default)


def set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set a value in the default cache."""
    return get_cache().set(key, value, ttl=ttl)


def delete(key: str) -> bool:
    """Delete a key from the default cache."""
    return get_cache().delete(key)


def exists(key: str) -> bool:
    """Check if a key exists in the default cache."""
    return get_cache().exists(key)


def clear() -> bool:
    """Clear the default cache."""
    return get_cache().clear()


def get_or_set(key: str, default: Any, ttl: Optional[int] = None) -> Any:
    """Get a value or set it if not found."""
    return get_cache().get_or_set(key, default, ttl=ttl)


# =============================================================================
# Cache Property (for lazy access)
# =============================================================================


class _CacheProxy:
    """
    Proxy class for lazy cache access.

    Allows using `cache` as if it were a cache instance,
    while deferring actual creation until first use.
    """

    def __getattr__(self, name: str) -> Any:
        return getattr(get_cache(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(get_cache(), name, value)


# Global cache instance (lazy loaded)
cache = _CacheProxy()


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Main interface
    "cache",
    "get_cache",
    "reset_cache",
    "cached",
    # Convenience functions
    "get",
    "set",
    "delete",
    "exists",
    "clear",
    "get_or_set",
    # Models
    "CacheConfig",
    "CacheBackend",
    "CacheEntry",
    "CacheStats",
    "CacheStrategy",
    "generate_cache_key",
    # Backend classes
    "BaseCacheBackend",
    "MemoryCacheBackend",
    "DjangoCacheBackend",
    "FileCacheBackend",
    "RedisCacheBackend",
    "create_backend",
    # Exceptions
    "CacheException",
    "CacheConnectionError",
    "CacheTimeoutError",
    "CacheKeyError",
    "CacheKeyNotFoundError",
    "CacheKeyExistsError",
    "InvalidCacheKeyError",
    "CacheValueError",
    "CacheSerializationError",
    "CacheDeserializationError",
    "CacheValueTooLargeError",
    "CacheBackendError",
    "CacheBackendNotAvailableError",
    "CacheBackendNotConfiguredError",
    "CacheOperationError",
    "CacheLockError",
    "CacheLockTimeoutError",
    "CacheVersionError",
    "CacheConfigurationError",
    "InvalidTTLError",
    "is_cache_error",
    "is_retriable_error",
]
