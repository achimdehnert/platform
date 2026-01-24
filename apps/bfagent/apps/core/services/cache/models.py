"""
Cache Service Models

Typed dataclasses for cache entries, statistics, and configuration.
Part of the consolidated Core Cache Service.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class CacheBackend(str, Enum):
    """Supported cache backends."""

    DJANGO = "django"  # Django's cache framework (Redis/Memcached/DB)
    MEMORY = "memory"  # In-memory dict (for testing/single process)
    FILE = "file"  # JSON file-based (for persistence without Redis)
    REDIS = "redis"  # Direct Redis (bypassing Django)


class CacheStrategy(str, Enum):
    """Cache invalidation strategies."""

    TTL = "ttl"  # Time-to-live based
    LRU = "lru"  # Least Recently Used
    VERSION = "version"  # Version-based invalidation
    MANUAL = "manual"  # Manual invalidation only


@dataclass
class CacheConfig:
    """
    Cache configuration settings.

    Attributes:
        backend: Cache backend to use
        default_ttl: Default time-to-live in seconds
        key_prefix: Prefix for all cache keys
        max_entries: Maximum entries (for memory/LRU backends)
        enable_stats: Enable statistics tracking
        enable_compression: Compress large values
        compression_threshold: Minimum size for compression (bytes)
        serializer: Serialization method ('json', 'pickle')
    """

    backend: CacheBackend = CacheBackend.DJANGO
    default_ttl: int = 300  # 5 minutes
    key_prefix: str = "core"
    max_entries: Optional[int] = None
    enable_stats: bool = True
    enable_compression: bool = False
    compression_threshold: int = 1024  # 1KB
    serializer: str = "json"

    # File backend settings
    cache_dir: Optional[str] = None
    cache_file: Optional[str] = None

    # Redis settings (direct connection)
    redis_url: Optional[str] = None
    redis_db: int = 0

    @classmethod
    def from_django_settings(cls) -> "CacheConfig":
        """Create config from Django settings."""
        try:
            from django.conf import settings

            return cls(
                backend=CacheBackend(getattr(settings, "CACHE_BACKEND", "django")),
                default_ttl=getattr(settings, "CACHE_DEFAULT_TTL", 300),
                key_prefix=getattr(settings, "CACHE_KEY_PREFIX", "core"),
                enable_stats=getattr(settings, "CACHE_ENABLE_STATS", True),
                enable_compression=getattr(settings, "CACHE_ENABLE_COMPRESSION", False),
                redis_url=getattr(settings, "REDIS_URL", None),
            )
        except ImportError:
            return cls()


@dataclass
class CacheEntry:
    """
    Represents a cached value with metadata.

    Attributes:
        key: Cache key
        value: Cached value
        created_at: When entry was created
        expires_at: When entry expires (None = never)
        ttl: Original TTL in seconds
        hits: Number of times accessed
        version: Entry version (for versioned invalidation)
        tags: Tags for group invalidation
        metadata: Additional metadata
    """

    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    ttl: Optional[int] = None
    hits: int = 0
    version: int = 1
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def age_seconds(self) -> float:
        """Get entry age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()

    @property
    def ttl_remaining(self) -> Optional[float]:
        """Get remaining TTL in seconds."""
        if self.expires_at is None:
            return None
        remaining = (self.expires_at - datetime.now()).total_seconds()
        return max(0, remaining)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entry to dict."""
        return {
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "ttl": self.ttl,
            "hits": self.hits,
            "version": self.version,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Deserialize entry from dict."""
        return cls(
            key=data["key"],
            value=data["value"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=(
                datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
            ),
            ttl=data.get("ttl"),
            hits=data.get("hits", 0),
            version=data.get("version", 1),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CacheStats:
    """
    Cache statistics for monitoring.

    Attributes:
        hits: Number of cache hits
        misses: Number of cache misses
        sets: Number of cache sets
        deletes: Number of cache deletes
        expirations: Number of expired entries
        errors: Number of errors
        total_entries: Current number of entries
        memory_bytes: Approximate memory usage
        start_time: When stats collection started
    """

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    expirations: int = 0
    errors: int = 0
    total_entries: int = 0
    memory_bytes: int = 0
    start_time: datetime = field(default_factory=datetime.now)

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate (0.0 - 1.0)."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    @property
    def hit_rate_percent(self) -> str:
        """Get hit rate as percentage string."""
        return f"{self.hit_rate * 100:.1f}%"

    @property
    def total_operations(self) -> int:
        """Total number of cache operations."""
        return self.hits + self.misses + self.sets + self.deletes

    @property
    def uptime_seconds(self) -> float:
        """Get stats collection uptime in seconds."""
        return (datetime.now() - self.start_time).total_seconds()

    def record_hit(self) -> None:
        """Record a cache hit."""
        self.hits += 1

    def record_miss(self) -> None:
        """Record a cache miss."""
        self.misses += 1

    def record_set(self) -> None:
        """Record a cache set."""
        self.sets += 1

    def record_delete(self) -> None:
        """Record a cache delete."""
        self.deletes += 1

    def record_expiration(self) -> None:
        """Record an expiration."""
        self.expirations += 1

    def record_error(self) -> None:
        """Record an error."""
        self.errors += 1

    def reset(self) -> None:
        """Reset all statistics."""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.expirations = 0
        self.errors = 0
        self.total_entries = 0
        self.memory_bytes = 0
        self.start_time = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "expirations": self.expirations,
            "errors": self.errors,
            "total_entries": self.total_entries,
            "memory_bytes": self.memory_bytes,
            "hit_rate": self.hit_rate_percent,
            "total_operations": self.total_operations,
            "uptime_seconds": self.uptime_seconds,
            "start_time": self.start_time.isoformat(),
        }


def generate_cache_key(
    *parts: Any,
    prefix: Optional[str] = None,
    hash_long_keys: bool = True,
    max_key_length: int = 250,
) -> str:
    """
    Generate a cache key from parts.

    Args:
        *parts: Key components to join
        prefix: Optional key prefix
        hash_long_keys: Hash keys that exceed max length
        max_key_length: Maximum key length before hashing

    Returns:
        Generated cache key

    Example:
        key = generate_cache_key("user", 123, "profile", prefix="myapp")
        # Returns: "myapp:user:123:profile"
    """
    # Convert parts to strings
    str_parts = []
    for part in parts:
        if isinstance(part, dict):
            # Sort dict for consistent keys
            sorted_items = sorted(part.items())
            str_parts.append("_".join(f"{k}={v}" for k, v in sorted_items))
        elif isinstance(part, (list, tuple)):
            str_parts.append("_".join(str(p) for p in part))
        else:
            str_parts.append(str(part))

    # Build key
    if prefix:
        key = f"{prefix}:{':'.join(str_parts)}"
    else:
        key = ":".join(str_parts)

    # Hash if too long
    if hash_long_keys and len(key) > max_key_length:
        key_hash = hashlib.md5(key.encode()).hexdigest()
        if prefix:
            key = f"{prefix}:hashed:{key_hash}"
        else:
            key = f"hashed:{key_hash}"

    return key


def serialize_value(value: Any, method: str = "json") -> bytes:
    """
    Serialize a value for caching.

    Args:
        value: Value to serialize
        method: Serialization method ('json' or 'pickle')

    Returns:
        Serialized bytes
    """
    if method == "json":
        return json.dumps(value, default=str).encode()
    elif method == "pickle":
        import pickle

        return pickle.dumps(value)
    else:
        raise ValueError(f"Unknown serialization method: {method}")


def deserialize_value(data: bytes, method: str = "json") -> Any:
    """
    Deserialize a cached value.

    Args:
        data: Serialized bytes
        method: Serialization method ('json' or 'pickle')

    Returns:
        Deserialized value
    """
    if method == "json":
        return json.loads(data.decode())
    elif method == "pickle":
        import pickle

        return pickle.loads(data)
    else:
        raise ValueError(f"Unknown serialization method: {method}")
