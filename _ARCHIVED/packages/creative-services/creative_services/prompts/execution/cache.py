"""
Caching for prompt executions.

Provides a protocol for cache implementations and an in-memory cache.
"""

import hashlib
import json
import time
from typing import Protocol, runtime_checkable, Any


@runtime_checkable
class PromptCache(Protocol):
    """
    Protocol for prompt execution caching.

    Implementations can use Redis, Memcached, or any other cache backend.
    """

    def get(self, key: str) -> str | None:
        """
        Get a cached response.

        Args:
            key: Cache key

        Returns:
            Cached response or None if not found/expired
        """
        ...

    def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        """
        Set a cached response.

        Args:
            key: Cache key
            value: Response to cache
            ttl_seconds: Time-to-live in seconds (None = no expiry)
        """
        ...

    def delete(self, key: str) -> bool:
        """
        Delete a cached entry.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        ...

    def clear(self) -> None:
        """Clear all cached entries."""
        ...


class InMemoryCache:
    """
    Simple in-memory cache implementation.

    Suitable for development and testing. Not shared across processes.
    """

    def __init__(self, default_ttl: int = 3600):
        """
        Initialize the cache.

        Args:
            default_ttl: Default TTL in seconds (1 hour)
        """
        self._cache: dict[str, tuple[str, float | None]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> str | None:
        """Get a cached value, checking expiry."""
        if key not in self._cache:
            return None

        value, expires_at = self._cache[key]

        # Check expiry
        if expires_at is not None and time.time() > expires_at:
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        """Set a cached value with optional TTL."""
        if ttl_seconds is None:
            ttl_seconds = self._default_ttl

        expires_at = time.time() + ttl_seconds if ttl_seconds else None
        self._cache[key] = (value, expires_at)

    def delete(self, key: str) -> bool:
        """Delete a cached entry."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def size(self) -> int:
        """Get number of cached entries."""
        return len(self._cache)

    def cleanup_expired(self) -> int:
        """
        Remove expired entries.

        Returns:
            Number of entries removed
        """
        now = time.time()
        expired_keys = [
            key for key, (_, expires_at) in self._cache.items()
            if expires_at is not None and now > expires_at
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)


def build_cache_key(
    template_key: str,
    variables: dict[str, Any],
    llm_config_hash: str | None = None,
) -> str:
    """
    Build a deterministic cache key for a prompt execution.

    The key is based on:
    - Template key
    - Sorted, serialized variables
    - Optional LLM config hash

    Args:
        template_key: Template identifier
        variables: Variables used in the prompt
        llm_config_hash: Optional hash of LLM config

    Returns:
        SHA256 hash as cache key
    """
    # Sort variables for deterministic ordering
    sorted_vars = json.dumps(variables, sort_keys=True, default=str)

    # Build key components
    components = [template_key, sorted_vars]
    if llm_config_hash:
        components.append(llm_config_hash)

    # Create hash
    key_string = "|".join(components)
    return hashlib.sha256(key_string.encode()).hexdigest()


def hash_llm_config(
    provider: str,
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """
    Create a hash of LLM configuration for cache key.

    Only includes parameters that affect output.

    Args:
        provider: LLM provider
        model: Model name
        temperature: Temperature setting
        max_tokens: Max tokens setting

    Returns:
        Short hash string
    """
    config_str = f"{provider}|{model}|{temperature}|{max_tokens}"
    return hashlib.md5(config_str.encode()).hexdigest()[:8]
