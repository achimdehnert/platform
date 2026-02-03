"""
Permission resolver with deterministic resolution algorithm.

Resolution order:
1. Override DENY → DENIED
2. Override ALLOW (not expired) → GRANTED
3. Role Permission → GRANTED/DENIED
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import FrozenSet, Optional
from uuid import UUID

from django.utils import timezone as django_timezone

from bfagent_core.permissions.enums import get_role_permissions

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PermissionResult:
    """Result of a permission check."""
    granted: bool
    permission: str
    source: str  # 'override', 'role', 'no_membership'
    
    def __bool__(self) -> bool:
        return self.granted


class PermissionResolver:
    """
    Resolves effective permissions for a membership.
    
    Algorithm:
    1. Check explicit DENY override → DENIED
    2. Check explicit ALLOW override (not expired) → GRANTED
    3. Check role-based permission → GRANTED/DENIED
    """
    
    def resolve(
        self,
        membership,  # TenantMembership
        permission_code: str,
    ) -> PermissionResult:
        """
        Resolve a single permission.
        
        Args:
            membership: TenantMembership instance
            permission_code: Permission code to check
        
        Returns:
            PermissionResult with granted status and source
        """
        # 1. Check overrides
        override = self._get_valid_override(membership, permission_code)
        if override is not None:
            return PermissionResult(
                granted=override.allowed,
                permission=permission_code,
                source="override",
            )
        
        # 2. Check role permissions
        role_perms = get_role_permissions(membership.role)
        granted = permission_code in role_perms
        
        return PermissionResult(
            granted=granted,
            permission=permission_code,
            source="role",
        )
    
    def resolve_all(self, membership) -> FrozenSet[str]:
        """
        Resolve all effective permissions for a membership.
        
        Returns:
            FrozenSet of granted permission codes
        """
        # Start with role permissions
        role_perms = set(get_role_permissions(membership.role))
        
        # Apply overrides
        overrides = self._get_all_valid_overrides(membership)
        for override in overrides:
            if override.allowed:
                role_perms.add(override.permission_id)
            else:
                role_perms.discard(override.permission_id)
        
        return frozenset(role_perms)
    
    def _get_valid_override(self, membership, permission_code: str):
        """Get valid (non-expired) override for a permission."""
        from bfagent_core.models import MembershipPermissionOverride
        
        now = django_timezone.now()
        
        override = MembershipPermissionOverride.objects.filter(
            membership=membership,
            permission_id=permission_code,
        ).first()
        
        if override is None:
            return None
        
        # Check expiration
        if override.expires_at and override.expires_at < now:
            return None
        
        return override
    
    def _get_all_valid_overrides(self, membership):
        """Get all valid (non-expired) overrides."""
        from bfagent_core.models import MembershipPermissionOverride
        from django.db.models import Q
        
        now = django_timezone.now()
        
        return MembershipPermissionOverride.objects.filter(
            membership=membership,
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gte=now)
        )


# Singleton instance
_resolver = PermissionResolver()


def get_permission_resolver() -> PermissionResolver:
    """Get the permission resolver singleton."""
    return _resolver
