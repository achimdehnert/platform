"""
Cache Backend Implementations

Concrete implementations of cache backends:
- MemoryCacheBackend: In-memory dict (testing/single-process)
- DjangoCacheBackend: Django's cache framework wrapper
- FileCacheBackend: JSON file-based persistent cache
- RedisCacheBackend: Direct Redis connection

Part of the consolidated Core Cache Service.
"""

import fnmatch
import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    from .base import BaseCacheBackend
    from .exceptions import (
        CacheBackendNotAvailableError,
        CacheBackendNotConfiguredError,
        CacheConnectionError,
        CacheSerializationError,
    )
    from .models import CacheBackend, CacheConfig, CacheEntry
except ImportError:
    from base import BaseCacheBackend
    from exceptions import (
        CacheBackendNotAvailableError,
        CacheBackendNotConfiguredError,
        CacheConnectionError,
        CacheSerializationError,
    )
    from models import CacheBackend, CacheConfig, CacheEntry


logger = logging.getLogger(__name__)


# =============================================================================
# Memory Cache Backend
# =============================================================================


class MemoryCacheBackend(BaseCacheBackend):
    """
    In-memory cache backend using a Python dictionary.

    Features:
        - Thread-safe operations
        - TTL support with lazy expiration
        - LRU eviction when max_entries exceeded
        - Key pattern matching

    Best for:
        - Testing
        - Single-process applications
        - Development

    Limitations:
        - Not shared across processes
        - Lost on restart
        - Memory bound

    Example:
        cache = MemoryCacheBackend(CacheConfig(
            default_ttl=300,
            max_entries=10000
        ))
        cache.set("key", "value")
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        super().__init__(config)
        self._storage: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._access_order: List[str] = []  # For LRU

    def _get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._storage.get(key)

            if entry is None:
                return None

            # Check expiration
            if entry.is_expired:
                del self._storage[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                if self._stats:
                    self._stats.record_expiration()
                return None

            # Update access order for LRU
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            entry.hits += 1
            return entry.value

    def _set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        with self._lock:
            # Evict if at capacity
            if self.config.max_entries:
                while len(self._storage) >= self.config.max_entries:
                    self._evict_lru()

            expires_at = None
            if ttl and ttl > 0:
                expires_at = datetime.now() + timedelta(seconds=ttl)

            entry = CacheEntry(
                key=key,
                value=value,
                ttl=ttl,
                expires_at=expires_at,
            )

            self._storage[key] = entry

            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            if self._stats:
                self._stats.total_entries = len(self._storage)

            return True

    def _delete(self, key: str) -> bool:
        with self._lock:
            if key in self._storage:
                del self._storage[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                if self._stats:
                    self._stats.total_entries = len(self._storage)
                return True
            return False

    def _exists(self, key: str) -> bool:
        with self._lock:
            entry = self._storage.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                del self._storage[key]
                return False
            return True

    def _clear(self) -> bool:
        with self._lock:
            self._storage.clear()
            self._access_order.clear()
            if self._stats:
                self._stats.total_entries = 0
            return True

    def _keys(self, pattern: str = "*") -> List[str]:
        with self._lock:
            # Clean expired entries first
            self._cleanup_expired()

            # Match pattern
            matching = []
            for key in self._storage.keys():
                if fnmatch.fnmatch(key, pattern):
                    matching.append(key)
            return matching

    def _incr(self, key: str, delta: int = 1) -> Optional[int]:
        with self._lock:
            entry = self._storage.get(key)
            if entry is None or entry.is_expired:
                return None

            try:
                new_value = int(entry.value) + delta
                entry.value = new_value
                return new_value
            except (ValueError, TypeError):
                return None

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if self._access_order:
            oldest_key = self._access_order.pop(0)
            if oldest_key in self._storage:
                del self._storage[oldest_key]

    def _cleanup_expired(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        expired_keys = [key for key, entry in self._storage.items() if entry.is_expired]

        for key in expired_keys:
            del self._storage[key]
            if key in self._access_order:
                self._access_order.remove(key)

        if self._stats:
            self._stats.expirations += len(expired_keys)
            self._stats.total_entries = len(self._storage)

        return len(expired_keys)


# =============================================================================
# Django Cache Backend
# =============================================================================


class DjangoCacheBackend(BaseCacheBackend):
    """
    Cache backend wrapping Django's cache framework.

    Uses whatever cache backend is configured in Django settings
    (Redis, Memcached, database, file, locmem, etc.).

    Features:
        - Full Django cache compatibility
        - Multiple cache aliases support
        - Automatic fallback to default cache

    Best for:
        - Django applications
        - Shared cache (Redis/Memcached)
        - Production deployments

    Example:
        cache = DjangoCacheBackend(CacheConfig(
            default_ttl=300,
            key_prefix="myapp"
        ))

        # Use specific Django cache alias
        cache = DjangoCacheBackend(config, cache_alias="redis")
    """

    def __init__(self, config: Optional[CacheConfig] = None, cache_alias: str = "default"):
        super().__init__(config)
        self.cache_alias = cache_alias
        self._cache = None

    @property
    def cache(self):
        """Lazy load Django cache to avoid import errors."""
        if self._cache is None:
            try:
                from django.core.cache import caches

                self._cache = caches[self.cache_alias]
            except ImportError:
                raise CacheBackendNotAvailableError("django", reason="Django not installed")
            except Exception as e:
                raise CacheBackendNotConfiguredError(
                    "django", missing_config=f"cache alias '{self.cache_alias}'"
                )
        return self._cache

    def _get(self, key: str) -> Optional[Any]:
        return self.cache.get(key)

    def _set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            if ttl is None or ttl == 0:
                self.cache.set(key, value, None)  # No expiration
            else:
                self.cache.set(key, value, ttl)
            return True
        except Exception as e:
            logger.error(f"Django cache set error: {e}")
            return False

    def _delete(self, key: str) -> bool:
        try:
            self.cache.delete(key)
            return True
        except Exception:
            return False

    def _exists(self, key: str) -> bool:
        # Django doesn't have a native exists(), use get with sentinel
        sentinel = object()
        return self.cache.get(key, sentinel) is not sentinel

    def _clear(self) -> bool:
        try:
            self.cache.clear()
            return True
        except Exception:
            return False

    def _get_many(self, keys: List[str]) -> Dict[str, Any]:
        return self.cache.get_many(keys)

    def _set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        try:
            self.cache.set_many(mapping, ttl)
            return True
        except Exception:
            return False

    def _delete_many(self, keys: List[str]) -> int:
        try:
            self.cache.delete_many(keys)
            return len(keys)  # Django doesn't return count
        except Exception:
            return 0

    def _incr(self, key: str, delta: int = 1) -> Optional[int]:
        try:
            if delta >= 0:
                return self.cache.incr(key, delta)
            else:
                return self.cache.decr(key, -delta)
        except ValueError:
            return None

    def _touch(self, key: str, ttl: Optional[int] = None) -> bool:
        try:
            return self.cache.touch(key, ttl)
        except AttributeError:
            # Older Django versions don't have touch()
            return super()._touch(key, ttl)


# =============================================================================
# File Cache Backend
# =============================================================================


class FileCacheBackend(BaseCacheBackend):
    """
    JSON file-based cache backend.

    Stores cache entries in a JSON file for persistence across restarts.

    Features:
        - Persistent storage
        - No external dependencies
        - Human-readable cache file
        - Auto-save on changes

    Best for:
        - Development
        - Small datasets
        - Environments without Redis
        - Translation memory / document caches

    Limitations:
        - Not suitable for high-traffic
        - Single-process write (uses file locking)
        - Entire file loaded into memory

    Example:
        cache = FileCacheBackend(CacheConfig(
            cache_dir="/tmp/cache",
            cache_file="app_cache.json"
        ))
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        super().__init__(config)

        # Determine cache file path
        if config and config.cache_dir:
            self.cache_dir = Path(config.cache_dir)
        else:
            self.cache_dir = Path.cwd() / "cache"

        self.cache_file = self.cache_dir / (
            config.cache_file if config and config.cache_file else "cache.json"
        )

        # Ensure directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load existing cache
        self._storage: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from file."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._storage = data
                    logger.info(f"Loaded {len(self._storage)} cache entries from {self.cache_file}")
        except json.JSONDecodeError as e:
            logger.warning(f"Cache file corrupted, starting fresh: {e}")
            self._storage = {}
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")
            self._storage = {}

    def _save_cache(self) -> None:
        """Save cache to file."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._storage, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"Could not save cache: {e}")

    def _get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._storage.get(key)

            if entry is None:
                return None

            # Check expiration
            expires_at = entry.get("expires_at")
            if expires_at:
                if datetime.fromisoformat(expires_at) < datetime.now():
                    del self._storage[key]
                    self._save_cache()
                    if self._stats:
                        self._stats.record_expiration()
                    return None

            # Update hits
            entry["hits"] = entry.get("hits", 0) + 1

            return entry.get("value")

    def _set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        with self._lock:
            expires_at = None
            if ttl and ttl > 0:
                expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()

            self._storage[key] = {
                "value": value,
                "created_at": datetime.now().isoformat(),
                "expires_at": expires_at,
                "ttl": ttl,
                "hits": 0,
            }

            self._save_cache()

            if self._stats:
                self._stats.total_entries = len(self._storage)

            return True

    def _delete(self, key: str) -> bool:
        with self._lock:
            if key in self._storage:
                del self._storage[key]
                self._save_cache()
                if self._stats:
                    self._stats.total_entries = len(self._storage)
                return True
            return False

    def _exists(self, key: str) -> bool:
        with self._lock:
            entry = self._storage.get(key)
            if entry is None:
                return False

            expires_at = entry.get("expires_at")
            if expires_at:
                if datetime.fromisoformat(expires_at) < datetime.now():
                    del self._storage[key]
                    self._save_cache()
                    return False

            return True

    def _clear(self) -> bool:
        with self._lock:
            self._storage.clear()
            self._save_cache()
            if self._stats:
                self._stats.total_entries = 0
            return True

    def _keys(self, pattern: str = "*") -> List[str]:
        with self._lock:
            matching = []
            for key in self._storage.keys():
                if fnmatch.fnmatch(key, pattern):
                    # Skip expired
                    entry = self._storage[key]
                    expires_at = entry.get("expires_at")
                    if expires_at:
                        if datetime.fromisoformat(expires_at) < datetime.now():
                            continue
                    matching.append(key)
            return matching

    def get_file_stats(self) -> Dict[str, Any]:
        """Get file-specific statistics."""
        return {
            "cache_file": str(self.cache_file),
            "file_size_kb": (
                self.cache_file.stat().st_size // 1024 if self.cache_file.exists() else 0
            ),
            "total_entries": len(self._storage),
        }


# =============================================================================
# Redis Cache Backend
# =============================================================================


class RedisCacheBackend(BaseCacheBackend):
    """
    Direct Redis cache backend (bypasses Django).

    Uses redis-py for direct Redis connection with full feature support.

    Features:
        - Atomic operations
        - Key pattern scanning
        - Pub/sub support (future)
        - Connection pooling
        - Cluster support (with redis-py-cluster)

    Best for:
        - High-performance requirements
        - Distributed caching
        - When Django is not available
        - Full Redis feature access

    Example:
        cache = RedisCacheBackend(CacheConfig(
            redis_url="redis://localhost:6379/0",
            key_prefix="myapp"
        ))
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        super().__init__(config)
        self._client = None
        self._pool = None

    @property
    def client(self):
        """Lazy load Redis client."""
        if self._client is None:
            try:
                import redis
            except ImportError:
                raise CacheBackendNotAvailableError(
                    "redis", reason="redis-py not installed. Run: pip install redis"
                )

            redis_url = self.config.redis_url
            if not redis_url:
                # Try Django settings
                try:
                    from django.conf import settings

                    redis_url = getattr(settings, "REDIS_URL", None)
                except ImportError:
                    pass

            if not redis_url:
                redis_url = "redis://localhost:6379/0"

            try:
                self._pool = redis.ConnectionPool.from_url(redis_url)
                self._client = redis.Redis(connection_pool=self._pool)
                # Test connection
                self._client.ping()
            except redis.ConnectionError as e:
                raise CacheConnectionError(
                    message=f"Could not connect to Redis: {e}", backend="redis"
                )

        return self._client

    def _serialize(self, value: Any) -> bytes:
        """Serialize value to bytes."""
        try:
            return json.dumps(value, default=str).encode("utf-8")
        except (TypeError, ValueError) as e:
            raise CacheSerializationError(
                message=f"Could not serialize value: {e}", value_type=type(value).__name__
            )

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to value."""
        if data is None:
            return None
        try:
            return json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Return raw string if not JSON
            return data.decode("utf-8")

    def _get(self, key: str) -> Optional[Any]:
        data = self.client.get(key)
        return self._deserialize(data)

    def _set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            data = self._serialize(value)
            if ttl and ttl > 0:
                self.client.setex(key, ttl, data)
            else:
                self.client.set(key, data)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    def _delete(self, key: str) -> bool:
        return self.client.delete(key) > 0

    def _exists(self, key: str) -> bool:
        return self.client.exists(key) > 0

    def _clear(self) -> bool:
        try:
            # Only clear keys with our prefix
            pattern = f"{self.config.key_prefix}:*"
            cursor = 0
            while True:
                cursor, keys = self.client.scan(cursor, match=pattern, count=100)
                if keys:
                    self.client.delete(*keys)
                if cursor == 0:
                    break
            return True
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False

    def _get_many(self, keys: List[str]) -> Dict[str, Any]:
        if not keys:
            return {}

        values = self.client.mget(keys)
        result = {}
        for key, value in zip(keys, values):
            if value is not None:
                result[key] = self._deserialize(value)
        return result

    def _set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        try:
            pipe = self.client.pipeline()
            for key, value in mapping.items():
                data = self._serialize(value)
                if ttl and ttl > 0:
                    pipe.setex(key, ttl, data)
                else:
                    pipe.set(key, data)
            pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Redis set_many error: {e}")
            return False

    def _delete_many(self, keys: List[str]) -> int:
        if not keys:
            return 0
        return self.client.delete(*keys)

    def _keys(self, pattern: str = "*") -> List[str]:
        result = []
        cursor = 0
        while True:
            cursor, keys = self.client.scan(cursor, match=pattern, count=100)
            result.extend([k.decode("utf-8") if isinstance(k, bytes) else k for k in keys])
            if cursor == 0:
                break
        return result

    def _incr(self, key: str, delta: int = 1) -> Optional[int]:
        try:
            if delta >= 0:
                return self.client.incrby(key, delta)
            else:
                return self.client.decrby(key, -delta)
        except Exception:
            return None

    def _touch(self, key: str, ttl: Optional[int] = None) -> bool:
        if ttl:
            return self.client.expire(key, ttl)
        else:
            return self.client.persist(key)

    def close(self) -> None:
        """Close Redis connection."""
        if self._pool:
            self._pool.disconnect()
            self._pool = None
            self._client = None


# =============================================================================
# Backend Factory
# =============================================================================


def create_backend(
    backend_type: CacheBackend, config: Optional[CacheConfig] = None, **kwargs
) -> BaseCacheBackend:
    """
    Factory function to create cache backends.

    Args:
        backend_type: Type of backend to create
        config: Cache configuration
        **kwargs: Additional backend-specific arguments

    Returns:
        Cache backend instance

    Example:
        cache = create_backend(CacheBackend.REDIS, CacheConfig(
            redis_url="redis://localhost:6379"
        ))
    """
    backends = {
        CacheBackend.MEMORY: MemoryCacheBackend,
        CacheBackend.DJANGO: DjangoCacheBackend,
        CacheBackend.FILE: FileCacheBackend,
        CacheBackend.REDIS: RedisCacheBackend,
    }

    backend_class = backends.get(backend_type)
    if backend_class is None:
        raise ValueError(f"Unknown cache backend: {backend_type}")

    return backend_class(config, **kwargs)
