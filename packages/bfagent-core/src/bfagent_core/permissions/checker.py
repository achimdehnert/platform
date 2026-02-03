"""
Permission checker - main entry point for permission checks.

Combines cache, resolver, and membership lookup.
"""

import logging
from dataclasses import dataclass
from typing import FrozenSet, Optional
from uuid import UUID

from bfagent_core.context import get_context
from bfagent_core.permissions.cache import get_permission_cache
from bfagent_core.permissions.resolver import PermissionResolver, PermissionResult

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result of a permission check with metadata."""
    granted: bool
    permission: str
    source: str
    cached: bool = False
    membership_id: Optional[UUID] = None
    
    def __bool__(self) -> bool:
        return self.granted


class PermissionChecker:
    """
    Main permission checker.
    
    Usage:
        checker = get_permission_checker()
        
        # Single check
        if checker.has_permission(user_id, "stories.create"):
            ...
        
        # Check with raise
        checker.check_permission(user_id, "stories.delete")  # raises PermissionDenied
        
        # Get all permissions
        perms = checker.get_permissions(user_id)
    """
    
    def __init__(self):
        self.cache = get_permission_cache()
        self.resolver = PermissionResolver()
    
    def has_permission(
        self,
        user_id: UUID,
        permission: str,
        tenant_id: Optional[UUID] = None,
    ) -> CheckResult:
        """
        Check if user has permission.
        
        Args:
            user_id: CoreUser ID
            permission: Permission code or Permission enum
            tenant_id: Optional tenant ID (uses context if not provided)
        
        Returns:
            CheckResult with granted status
        """
        from bfagent_core.permissions.enums import Permission
        
        # Normalize permission to string
        if isinstance(permission, Permission):
            permission = permission.value
        
        # Get tenant from context if not provided
        if tenant_id is None:
            ctx = get_context()
            tenant_id = ctx.tenant_id
        
        if tenant_id is None:
            logger.warning("No tenant context for permission check")
            return CheckResult(
                granted=False,
                permission=permission,
                source="no_tenant",
            )
        
        # Get membership
        membership = self._get_membership(tenant_id, user_id)
        if membership is None:
            return CheckResult(
                granted=False,
                permission=permission,
                source="no_membership",
            )
        
        # Try cache first
        cached_perms = self.cache.get(
            tenant_id,
            user_id,
            membership.permission_version,
        )
        
        if cached_perms is not None:
            granted = permission in cached_perms
            return CheckResult(
                granted=granted,
                permission=permission,
                source="cache",
                cached=True,
                membership_id=membership.id,
            )
        
        # Resolve from DB
        result = self.resolver.resolve(membership, permission)
        
        # Update cache with all permissions
        all_perms = self.resolver.resolve_all(membership)
        self.cache.set(
            tenant_id,
            user_id,
            membership.permission_version,
            all_perms,
        )
        
        return CheckResult(
            granted=result.granted,
            permission=permission,
            source=result.source,
            cached=False,
            membership_id=membership.id,
        )
    
    def check_permission(
        self,
        user_id: UUID,
        permission: str,
        tenant_id: Optional[UUID] = None,
    ) -> None:
        """
        Check permission and raise if denied.
        
        Raises:
            PermissionDeniedError: If permission not granted
        """
        from bfagent_core.exceptions import PermissionDeniedError
        
        result = self.has_permission(user_id, permission, tenant_id)
        if not result.granted:
            raise PermissionDeniedError(permission)
    
    def get_permissions(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
    ) -> FrozenSet[str]:
        """
        Get all effective permissions for user.
        
        Returns:
            FrozenSet of permission codes
        """
        if tenant_id is None:
            ctx = get_context()
            tenant_id = ctx.tenant_id
        
        if tenant_id is None:
            return frozenset()
        
        membership = self._get_membership(tenant_id, user_id)
        if membership is None:
            return frozenset()
        
        # Try cache
        cached = self.cache.get(
            tenant_id,
            user_id,
            membership.permission_version,
        )
        if cached is not None:
            return cached
        
        # Resolve all
        perms = self.resolver.resolve_all(membership)
        
        # Cache
        self.cache.set(
            tenant_id,
            user_id,
            membership.permission_version,
            perms,
        )
        
        return perms
    
    def _get_membership(self, tenant_id: UUID, user_id: UUID):
        """Get active membership."""
        from bfagent_core.models import TenantMembership
        return TenantMembership.objects.get_membership(tenant_id, user_id)


# Singleton
_checker = PermissionChecker()


def get_permission_checker() -> PermissionChecker:
    """Get the permission checker singleton."""
    return _checker


# Convenience functions
def has_permission(
    user_id: UUID,
    permission: str,
    tenant_id: Optional[UUID] = None,
) -> bool:
    """Check if user has permission."""
    return _checker.has_permission(user_id, permission, tenant_id).granted


def check_permission(
    user_id: UUID,
    permission: str,
    tenant_id: Optional[UUID] = None,
) -> None:
    """Check permission and raise if denied."""
    _checker.check_permission(user_id, permission, tenant_id)


def get_user_permissions(
    user_id: UUID,
    tenant_id: Optional[UUID] = None,
) -> FrozenSet[str]:
    """Get all effective permissions for user."""
    return _checker.get_permissions(user_id, tenant_id)
