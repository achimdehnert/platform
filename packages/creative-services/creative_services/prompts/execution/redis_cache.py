"""
Redis-based cache implementation for prompt executions.

Provides distributed caching with TTL support.
Requires redis package: pip install redis
"""

from typing import Any

from .cache import PromptCache

# Try to import redis
try:
    import redis
    from redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = Any  # type: ignore


class RedisCache:
    """
    Redis-based cache for prompt executions.
    
    Provides distributed caching suitable for production deployments.
    Supports TTL, connection pooling, and cluster mode.
    
    Example:
        cache = RedisCache(host="localhost", port=6379, db=0)
        cache.set("key", "value", ttl_seconds=3600)
        value = cache.get("key")
        
        # With connection URL
        cache = RedisCache.from_url("redis://localhost:6379/0")
        
        # With prefix for namespacing
        cache = RedisCache(host="localhost", prefix="prompts:")
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        prefix: str = "prompt_cache:",
        default_ttl: int = 3600,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        decode_responses: bool = True,
        client: "Redis | None" = None,
    ):
        """
        Initialize Redis cache.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            prefix: Key prefix for namespacing
            default_ttl: Default TTL in seconds
            socket_timeout: Socket timeout
            socket_connect_timeout: Connection timeout
            decode_responses: Whether to decode responses to strings
            client: Optional pre-configured Redis client
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis package is required for RedisCache. "
                "Install with: pip install redis"
            )
        
        self._prefix = prefix
        self._default_ttl = default_ttl
        
        if client is not None:
            self._client = client
        else:
            self._client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                decode_responses=decode_responses,
            )

    @classmethod
    def from_url(
        cls,
        url: str,
        prefix: str = "prompt_cache:",
        default_ttl: int = 3600,
    ) -> "RedisCache":
        """
        Create RedisCache from connection URL.
        
        Args:
            url: Redis connection URL (e.g., "redis://localhost:6379/0")
            prefix: Key prefix
            default_ttl: Default TTL
            
        Returns:
            Configured RedisCache
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis package is required for RedisCache. "
                "Install with: pip install redis"
            )
        
        client = redis.from_url(url, decode_responses=True)
        instance = cls.__new__(cls)
        instance._client = client
        instance._prefix = prefix
        instance._default_ttl = default_ttl
        return instance

    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self._prefix}{key}"

    def get(self, key: str) -> str | None:
        """
        Get a cached value.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        try:
            return self._client.get(self._make_key(key))
        except redis.RedisError:
            # Log error but don't fail - cache is optional
            return None

    def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> None:
        """
        Set a cached value.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL in seconds (uses default if not provided)
        """
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        
        try:
            if ttl:
                self._client.setex(self._make_key(key), ttl, value)
            else:
                self._client.set(self._make_key(key))
        except redis.RedisError:
            # Log error but don't fail - cache is optional
            pass

    def delete(self, key: str) -> bool:
        """
        Delete a cached entry.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        try:
            return bool(self._client.delete(self._make_key(key)))
        except redis.RedisError:
            return False

    def clear(self, pattern: str = "*") -> int:
        """
        Clear cached entries matching pattern.
        
        Args:
            pattern: Glob pattern to match (default: all keys with prefix)
            
        Returns:
            Number of keys deleted
        """
        try:
            full_pattern = f"{self._prefix}{pattern}"
            keys = self._client.keys(full_pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except redis.RedisError:
            return 0

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return bool(self._client.exists(self._make_key(key)))
        except redis.RedisError:
            return False

    def ttl(self, key: str) -> int:
        """
        Get remaining TTL for a key.
        
        Returns:
            TTL in seconds, -1 if no TTL, -2 if key doesn't exist
        """
        try:
            return self._client.ttl(self._make_key(key))
        except redis.RedisError:
            return -2

    def ping(self) -> bool:
        """Check if Redis is available."""
        try:
            return self._client.ping()
        except redis.RedisError:
            return False

    def info(self) -> dict[str, Any]:
        """Get Redis server info."""
        try:
            return self._client.info()
        except redis.RedisError:
            return {}

    def size(self) -> int:
        """Get approximate number of cached entries with prefix."""
        try:
            keys = self._client.keys(f"{self._prefix}*")
            return len(keys)
        except redis.RedisError:
            return 0


class AsyncRedisCache:
    """
    Async Redis cache for use with asyncio.
    
    Requires redis[hiredis] for best performance.
    
    Example:
        cache = await AsyncRedisCache.create(host="localhost")
        await cache.set("key", "value")
        value = await cache.get("key")
    """

    def __init__(
        self,
        client: Any,
        prefix: str = "prompt_cache:",
        default_ttl: int = 3600,
    ):
        """Initialize with async Redis client."""
        self._client = client
        self._prefix = prefix
        self._default_ttl = default_ttl

    @classmethod
    async def create(
        cls,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        prefix: str = "prompt_cache:",
        default_ttl: int = 3600,
    ) -> "AsyncRedisCache":
        """
        Create async Redis cache.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database
            password: Redis password
            prefix: Key prefix
            default_ttl: Default TTL
            
        Returns:
            Configured AsyncRedisCache
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis package is required for AsyncRedisCache. "
                "Install with: pip install redis"
            )
        
        client = redis.asyncio.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
        )
        return cls(client, prefix, default_ttl)

    @classmethod
    async def from_url(
        cls,
        url: str,
        prefix: str = "prompt_cache:",
        default_ttl: int = 3600,
    ) -> "AsyncRedisCache":
        """Create from connection URL."""
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis package is required for AsyncRedisCache. "
                "Install with: pip install redis"
            )
        
        client = redis.asyncio.from_url(url, decode_responses=True)
        return cls(client, prefix, default_ttl)

    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self._prefix}{key}"

    async def get(self, key: str) -> str | None:
        """Get cached value."""
        try:
            return await self._client.get(self._make_key(key))
        except redis.RedisError:
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> None:
        """Set cached value."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        
        try:
            if ttl:
                await self._client.setex(self._make_key(key), ttl, value)
            else:
                await self._client.set(self._make_key(key), value)
        except redis.RedisError:
            pass

    async def delete(self, key: str) -> bool:
        """Delete cached entry."""
        try:
            return bool(await self._client.delete(self._make_key(key)))
        except redis.RedisError:
            return False

    async def clear(self, pattern: str = "*") -> int:
        """Clear entries matching pattern."""
        try:
            full_pattern = f"{self._prefix}{pattern}"
            keys = await self._client.keys(full_pattern)
            if keys:
                return await self._client.delete(*keys)
            return 0
        except redis.RedisError:
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return bool(await self._client.exists(self._make_key(key)))
        except redis.RedisError:
            return False

    async def ping(self) -> bool:
        """Check if Redis is available."""
        try:
            return await self._client.ping()
        except redis.RedisError:
            return False

    async def close(self) -> None:
        """Close the connection."""
        await self._client.close()


def is_redis_available() -> bool:
    """Check if redis package is available."""
    return REDIS_AVAILABLE
