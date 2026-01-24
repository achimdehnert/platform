"""
Cache Service Base Classes

Abstract base class and common functionality for cache backends.
Part of the consolidated Core Cache Service.
"""

import functools
import logging
import threading
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Generic,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)

try:
    from .exceptions import (
        CacheException,
        CacheKeyNotFoundError,
        CacheLockError,
        CacheLockTimeoutError,
        CacheSerializationError,
        CacheTimeoutError,
        wrap_backend_error,
    )
    from .models import (
        CacheBackend,
        CacheConfig,
        CacheEntry,
        CacheStats,
        deserialize_value,
        generate_cache_key,
        serialize_value,
    )
except ImportError:
    from exceptions import (
        CacheException,
        CacheKeyNotFoundError,
        CacheLockError,
        CacheLockTimeoutError,
        CacheSerializationError,
        CacheTimeoutError,
        wrap_backend_error,
    )
    from models import (
        CacheBackend,
        CacheConfig,
        CacheEntry,
        CacheStats,
        deserialize_value,
        generate_cache_key,
        serialize_value,
    )


# Type variable for cached values
T = TypeVar("T")

# Logger
logger = logging.getLogger(__name__)

# Try to use structlog if available
try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    pass


class BaseCacheBackend(ABC):
    """
    Abstract base class for cache backends.

    All cache backends must implement the abstract methods.
    Provides common functionality for key generation, stats tracking,
    and error handling.

    Abstract Methods (must implement):
        - _get(key) -> value or None
        - _set(key, value, ttl) -> bool
        - _delete(key) -> bool
        - _exists(key) -> bool
        - _clear() -> bool

    Optional Methods (can override):
        - _get_many(keys) -> dict
        - _set_many(mapping, ttl) -> bool
        - _delete_many(keys) -> int
        - _keys(pattern) -> list

    Example:
        class MyBackend(BaseCacheBackend):
            def _get(self, key: str) -> Optional[Any]:
                return self.storage.get(key)

            def _set(self, key: str, value: Any, ttl: Optional[int]) -> bool:
                self.storage[key] = value
                return True
            ...
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize cache backend.

        Args:
            config: Cache configuration (uses defaults if None)
        """
        self.config = config or CacheConfig()
        self._stats = CacheStats() if self.config.enable_stats else None
        self._locks: Dict[str, threading.Lock] = {}
        self._lock_manager = threading.Lock()

    @property
    def name(self) -> str:
        """Get backend name."""
        return self.__class__.__name__

    @property
    def stats(self) -> Optional[CacheStats]:
        """Get cache statistics."""
        return self._stats

    # =========================================================================
    # Abstract Methods (MUST implement)
    # =========================================================================

    @abstractmethod
    def _get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.

        Args:
            key: Cache key (already prefixed)

        Returns:
            Cached value or None if not found
        """
        pass

    @abstractmethod
    def _set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.

        Args:
            key: Cache key (already prefixed)
            value: Value to cache
            ttl: Time-to-live in seconds (None = use default)

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def _delete(self, key: str) -> bool:
        """
        Delete a key from the cache.

        Args:
            key: Cache key (already prefixed)

        Returns:
            True if key was deleted, False if not found
        """
        pass

    @abstractmethod
    def _exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: Cache key (already prefixed)

        Returns:
            True if key exists
        """
        pass

    @abstractmethod
    def _clear(self) -> bool:
        """
        Clear all keys from the cache.

        Returns:
            True if successful
        """
        pass

    # =========================================================================
    # Optional Methods (can override for efficiency)
    # =========================================================================

    def _get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values from the cache.

        Default implementation calls _get() for each key.
        Override for backends that support bulk operations.
        """
        result = {}
        for key in keys:
            value = self._get(key)
            if value is not None:
                result[key] = value
        return result

    def _set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Set multiple values in the cache.

        Default implementation calls _set() for each item.
        Override for backends that support bulk operations.
        """
        success = True
        for key, value in mapping.items():
            if not self._set(key, value, ttl):
                success = False
        return success

    def _delete_many(self, keys: List[str]) -> int:
        """
        Delete multiple keys from the cache.

        Default implementation calls _delete() for each key.
        Override for backends that support bulk operations.
        """
        count = 0
        for key in keys:
            if self._delete(key):
                count += 1
        return count

    def _keys(self, pattern: str = "*") -> List[str]:
        """
        Get keys matching a pattern.

        Default returns empty list (not all backends support this).
        Override for backends that support key iteration.
        """
        return []

    def _touch(self, key: str, ttl: Optional[int] = None) -> bool:
        """
        Update expiration time without changing value.

        Default implementation re-sets the value.
        Override for backends that support touch operations.
        """
        value = self._get(key)
        if value is not None:
            return self._set(key, value, ttl)
        return False

    def _incr(self, key: str, delta: int = 1) -> Optional[int]:
        """
        Increment a numeric value.

        Default implementation is not atomic.
        Override for backends that support atomic increment.
        """
        value = self._get(key)
        if value is not None:
            new_value = int(value) + delta
            self._set(key, new_value)
            return new_value
        return None

    # =========================================================================
    # Public API
    # =========================================================================

    def get(self, key: str, default: T = None, version: Optional[int] = None) -> Union[Any, T]:
        """
        Get a value from the cache.

        Args:
            key: Cache key
            default: Value to return if key not found
            version: Optional version number for versioned keys

        Returns:
            Cached value or default
        """
        full_key = self._make_key(key, version)

        try:
            value = self._get(full_key)

            if value is None:
                if self._stats:
                    self._stats.record_miss()
                return default

            if self._stats:
                self._stats.record_hit()

            return value

        except Exception as e:
            if self._stats:
                self._stats.record_error()
            logger.warning(f"Cache get error: {e}", exc_info=True)
            return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        version: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = use default)
            version: Optional version number for versioned keys
            tags: Optional tags for group invalidation

        Returns:
            True if successful
        """
        full_key = self._make_key(key, version)
        ttl = ttl if ttl is not None else self.config.default_ttl

        try:
            if tags:
                self._add_to_tags(full_key, tags)

            result = self._set(full_key, value, ttl)

            if self._stats and result:
                self._stats.record_set()

            return result

        except Exception as e:
            if self._stats:
                self._stats.record_error()
            logger.error(f"Cache set error: {e}", exc_info=True)
            return False

    def delete(self, key: str, version: Optional[int] = None) -> bool:
        """Delete a key from the cache."""
        full_key = self._make_key(key, version)

        try:
            result = self._delete(full_key)

            if self._stats and result:
                self._stats.record_delete()

            return result

        except Exception as e:
            if self._stats:
                self._stats.record_error()
            logger.error(f"Cache delete error: {e}", exc_info=True)
            return False

    def exists(self, key: str, version: Optional[int] = None) -> bool:
        """Check if a key exists in the cache."""
        full_key = self._make_key(key, version)

        try:
            return self._exists(full_key)
        except Exception as e:
            logger.error(f"Cache exists error: {e}", exc_info=True)
            return False

    def get_or_set(
        self,
        key: str,
        default: Union[T, Callable[[], T]],
        ttl: Optional[int] = None,
        version: Optional[int] = None,
    ) -> Union[Any, T]:
        """
        Get a value, or set it if not found.

        Args:
            key: Cache key
            default: Default value or callable to generate it
            ttl: Time-to-live in seconds
            version: Optional version number

        Returns:
            Cached or newly set value
        """
        value = self.get(key, version=version)

        if value is None:
            if callable(default):
                value = default()
            else:
                value = default

            self.set(key, value, ttl=ttl, version=version)

        return value

    def add(
        self, key: str, value: Any, ttl: Optional[int] = None, version: Optional[int] = None
    ) -> bool:
        """
        Add a value only if the key doesn't exist.

        Returns:
            True if value was added, False if key exists
        """
        if not self.exists(key, version=version):
            return self.set(key, value, ttl=ttl, version=version)
        return False

    def get_many(self, keys: List[str], version: Optional[int] = None) -> Dict[str, Any]:
        """Get multiple values from the cache."""
        full_keys = [self._make_key(k, version) for k in keys]
        key_map = dict(zip(full_keys, keys))

        try:
            results = self._get_many(full_keys)
            return {key_map[k]: v for k, v in results.items()}
        except Exception as e:
            logger.error(f"Cache get_many error: {e}", exc_info=True)
            return {}

    def set_many(
        self, mapping: Dict[str, Any], ttl: Optional[int] = None, version: Optional[int] = None
    ) -> bool:
        """Set multiple values in the cache."""
        full_mapping = {self._make_key(k, version): v for k, v in mapping.items()}

        try:
            return self._set_many(full_mapping, ttl or self.config.default_ttl)
        except Exception as e:
            logger.error(f"Cache set_many error: {e}", exc_info=True)
            return False

    def delete_many(self, keys: List[str], version: Optional[int] = None) -> int:
        """Delete multiple keys from the cache."""
        full_keys = [self._make_key(k, version) for k in keys]

        try:
            count = self._delete_many(full_keys)

            if self._stats:
                for _ in range(count):
                    self._stats.record_delete()

            return count

        except Exception as e:
            logger.error(f"Cache delete_many error: {e}", exc_info=True)
            return 0

    def clear(self) -> bool:
        """Clear all keys from the cache."""
        try:
            result = self._clear()

            if self._stats:
                self._stats.reset()

            return result

        except Exception as e:
            logger.error(f"Cache clear error: {e}", exc_info=True)
            return False

    def incr(self, key: str, delta: int = 1, version: Optional[int] = None) -> Optional[int]:
        """Increment a numeric value."""
        full_key = self._make_key(key, version)

        try:
            return self._incr(full_key, delta)
        except Exception as e:
            logger.error(f"Cache incr error: {e}", exc_info=True)
            return None

    def decr(self, key: str, delta: int = 1, version: Optional[int] = None) -> Optional[int]:
        """Decrement a numeric value."""
        return self.incr(key, -delta, version=version)

    def touch(self, key: str, ttl: Optional[int] = None, version: Optional[int] = None) -> bool:
        """Update expiration time without changing value."""
        full_key = self._make_key(key, version)

        try:
            return self._touch(full_key, ttl or self.config.default_ttl)
        except Exception as e:
            logger.error(f"Cache touch error: {e}", exc_info=True)
            return False

    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching a pattern."""
        full_pattern = f"{self.config.key_prefix}:{pattern}"

        try:
            full_keys = self._keys(full_pattern)
            prefix_len = len(self.config.key_prefix) + 1
            return [k[prefix_len:] for k in full_keys]
        except Exception as e:
            logger.error(f"Cache keys error: {e}", exc_info=True)
            return []

    # =========================================================================
    # Tag-Based Operations
    # =========================================================================

    def _add_to_tags(self, key: str, tags: List[str]) -> None:
        """Add a key to tag sets for later invalidation."""
        for tag in tags:
            tag_key = f"_tag:{tag}"
            tag_set = self._get(tag_key) or set()
            if isinstance(tag_set, list):
                tag_set = set(tag_set)
            tag_set.add(key)
            self._set(tag_key, list(tag_set), ttl=None)

    def invalidate_tags(self, *tags: str) -> int:
        """
        Invalidate all keys with given tags.

        Returns:
            Number of keys deleted
        """
        count = 0
        for tag in tags:
            tag_key = f"_tag:{tag}"
            full_tag_key = self._make_key(tag_key)

            tag_set = self._get(full_tag_key)
            if tag_set:
                if isinstance(tag_set, list):
                    tag_set = set(tag_set)

                for key in tag_set:
                    if self._delete(key):
                        count += 1

                self._delete(full_tag_key)

        return count

    # =========================================================================
    # Locking
    # =========================================================================

    @contextmanager
    def lock(
        self,
        name: str,
        timeout: float = 10.0,
        blocking: bool = True,
        blocking_timeout: Optional[float] = None,
    ) -> Generator[bool, None, None]:
        """
        Acquire a distributed lock.

        Args:
            name: Lock name
            timeout: Lock expiration in seconds
            blocking: Wait for lock if held
            blocking_timeout: Maximum time to wait for lock

        Yields:
            True if lock acquired
        """
        lock_key = f"_lock:{name}"
        acquired = False
        start_time = time.time()

        try:
            while True:
                if self.add(lock_key, "1", ttl=int(timeout)):
                    acquired = True
                    break

                if not blocking:
                    break

                if blocking_timeout is not None:
                    if time.time() - start_time >= blocking_timeout:
                        break

                time.sleep(0.1)

            yield acquired

        finally:
            if acquired:
                self.delete(lock_key)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _make_key(self, key: str, version: Optional[int] = None) -> str:
        """Create a full cache key with prefix and version."""
        parts = [self.config.key_prefix, key]
        if version is not None:
            parts.append(f"v{version}")
        return ":".join(parts)

    def get_stats_dict(self) -> Dict[str, Any]:
        """Get statistics as dictionary."""
        if self._stats:
            return self._stats.to_dict()
        return {}

    def reset_stats(self) -> None:
        """Reset statistics."""
        if self._stats:
            self._stats.reset()

    def health_check(self) -> bool:
        """Check if the cache backend is healthy."""
        try:
            test_key = "_health_check"
            test_value = "ok"

            self.set(test_key, test_value, ttl=10)
            result = self.get(test_key)
            self.delete(test_key)

            return result == test_value

        except Exception:
            return False


# =============================================================================
# Cache Decorator
# =============================================================================


def cached(
    ttl: int = 300,
    key_prefix: Optional[str] = None,
    key_func: Optional[Callable[..., str]] = None,
    cache_backend: Optional[BaseCacheBackend] = None,
    skip_if: Optional[Callable[..., bool]] = None,
    tags: Optional[List[str]] = None,
):
    """
    Decorator to cache function results.

    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache key (defaults to function name)
        key_func: Custom function to generate cache key
        cache_backend: Cache backend to use (uses default if None)
        skip_if: Callable that returns True to skip caching
        tags: Tags for group invalidation

    Example:
        @cached(ttl=3600)
        def get_user(user_id: int):
            return db.query(User).get(user_id)

        @cached(key_func=lambda x: f"data:{x}")
        def fetch_data(data_id: str):
            return api.fetch(data_id)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get cache backend
            backend = cache_backend
            if backend is None:
                from . import get_cache

                backend = get_cache()

            # Check skip condition
            if skip_if and skip_if(*args, **kwargs):
                return func(*args, **kwargs)

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                prefix = key_prefix or func.__name__
                cache_key = generate_cache_key(prefix, *args, kwargs, prefix=None)

            # Try to get from cache
            cached_value = backend.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            backend.set(cache_key, result, ttl=ttl, tags=tags)

            return result

        wrapper.cache_clear = lambda: None
        wrapper.cache_info = lambda: None

        return wrapper

    return decorator
