import logging

logger = logging.getLogger(__name__)


def invalidate_pattern(pattern: str, cache_alias: str = "default") -> int:
    """Delete all cache keys matching a glob pattern. Returns count of deleted keys.

    Requires django-redis backend (uses iter_keys).
    Falls back to a warning if backend doesn't support pattern operations.
    """
    try:
        from django.core.cache import caches

        cache = caches[cache_alias]
        if not hasattr(cache, "iter_keys"):
            logger.warning(
                "invalidate_pattern requires django-redis backend. "
                "Cache alias '%s' does not support iter_keys.",
                cache_alias,
            )
            return 0

        keys = list(cache.iter_keys(pattern))
        if keys:
            cache.delete_many(keys)
        logger.debug("invalidated %d keys matching '%s'", len(keys), pattern)
        return len(keys)
    except Exception as exc:
        logger.error("cache invalidation failed for pattern '%s': %s", pattern, exc)
        return 0
