"""
Permission cache with version-based invalidation.

Features:
- Version check for precise invalidation
- Fail-closed on errors
- Namespaced keys for collision prevention
"""

import logging
from datetime import datetime, timezone
from typing import FrozenSet, Optional
from uuid import UUID

from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_PREFIX = "bfagent:perms:v1"
CACHE_TTL = 60  # seconds


def _utc_now() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)


class PermissionCache:
    """
    Version-based permission cache.
    
    Uses membership.permission_version for precise invalidation.
    Fail-closed: returns None on any error (forces DB lookup).
    """
    
    def _key(self, tenant_id: UUID, user_id: UUID) -> str:
        return f"{CACHE_PREFIX}:{tenant_id}:{user_id}"
    
    def get(
        self,
        tenant_id: UUID,
        user_id: UUID,
        expected_version: int,
    ) -> Optional[FrozenSet[str]]:
        """
        Get cached permissions.
        
        Returns None if:
        - Cache miss
        - Version mismatch
        - Cache error (fail-closed)
        """
        key = self._key(tenant_id, user_id)
        try:
            cached = cache.get(key)
            if cached is None:
                return None
            
            if cached.get("version") != expected_version:
                logger.debug(
                    "Cache version mismatch",
                    extra={
                        "key": key,
                        "expected": expected_version,
                        "cached": cached.get("version"),
                    }
                )
                return None
            
            return frozenset(cached.get("permissions", []))
        
        except Exception as e:
            logger.warning(f"Cache read failed: {e}", extra={"key": key})
            return None  # Fail-closed: DB lookup
    
    def set(
        self,
        tenant_id: UUID,
        user_id: UUID,
        version: int,
        permissions: FrozenSet[str],
    ) -> None:
        """Set cached permissions with version."""
        key = self._key(tenant_id, user_id)
        try:
            cache.set(
                key,
                {
                    "version": version,
                    "permissions": list(permissions),
                    "cached_at": _utc_now().isoformat(),
                },
                timeout=CACHE_TTL,
            )
        except Exception as e:
            logger.warning(f"Cache write failed: {e}", extra={"key": key})
    
    def invalidate(self, tenant_id: UUID, user_id: UUID) -> None:
        """Explicit invalidation."""
        key = self._key(tenant_id, user_id)
        try:
            cache.delete(key)
            logger.debug("Cache invalidated", extra={"key": key})
        except Exception as e:
            logger.warning(f"Cache delete failed: {e}", extra={"key": key})
    
    def invalidate_tenant(self, tenant_id: UUID) -> None:
        """Invalidate all permissions for a tenant (expensive, use sparingly)."""
        pattern = f"{CACHE_PREFIX}:{tenant_id}:*"
        try:
            # Note: This requires cache backend that supports delete_pattern
            if hasattr(cache, 'delete_pattern'):
                cache.delete_pattern(pattern)
                logger.info("Tenant cache invalidated", extra={"tenant_id": str(tenant_id)})
            else:
                logger.warning("Cache backend doesn't support delete_pattern")
        except Exception as e:
            logger.warning(f"Tenant cache invalidation failed: {e}")


# Singleton instance
permission_cache = PermissionCache()


def get_permission_cache() -> PermissionCache:
    """Get the permission cache singleton."""
    return permission_cache
