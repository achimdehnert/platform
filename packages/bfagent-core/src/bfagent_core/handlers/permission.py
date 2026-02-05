"""
Permission handlers for granting and revoking overrides.

All handlers use @transaction.atomic for data consistency.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from django.db import transaction

from bfagent_core.exceptions import (
    MembershipNotFoundError,
    PermissionNotFoundError,
    PermissionDeniedError,
)
from bfagent_core.permissions.cache import get_permission_cache


def _utc_now() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# PERMISSION GRANT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PermissionGrantCommand:
    """Command for granting a permission override."""
    membership_id: UUID
    permission_code: str
    granted_by_id: UUID
    reason: str = ""
    expires_in_days: Optional[int] = None


class PermissionGrantHandler:
    """Handler for granting permission overrides."""
    
    @transaction.atomic
    def handle(self, cmd: PermissionGrantCommand) -> None:
        from bfagent_core.models import (
            TenantMembership,
            CorePermission,
            MembershipPermissionOverride,
        )
        
        # 1. Validate membership exists
        membership = TenantMembership.objects.filter(id=cmd.membership_id).first()
        if not membership:
            raise MembershipNotFoundError(membership_id=cmd.membership_id)
        
        # 2. Validate permission exists
        if not CorePermission.objects.filter(code=cmd.permission_code).exists():
            raise PermissionNotFoundError(cmd.permission_code)
        
        # 3. Calculate expiration
        expires_at = None
        if cmd.expires_in_days:
            expires_at = _utc_now() + timedelta(days=cmd.expires_in_days)
        
        # 4. Create or update override
        MembershipPermissionOverride.objects.update_or_create(
            membership=membership,
            permission_id=cmd.permission_code,
            defaults={
                "allowed": True,
                "expires_at": expires_at,
                "reason": cmd.reason,
                "granted_by_id": cmd.granted_by_id,
            }
        )
        
        # 5. Increment permission version for cache invalidation
        membership.increment_permission_version()
        
        # 6. Invalidate cache
        cache = get_permission_cache()
        cache.invalidate(membership.tenant_id, membership.user_id)


# ═══════════════════════════════════════════════════════════════════════════════
# PERMISSION REVOKE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PermissionRevokeCommand:
    """Command for revoking a permission (explicit deny)."""
    membership_id: UUID
    permission_code: str
    granted_by_id: UUID
    reason: str = ""
    expires_in_days: Optional[int] = None


class PermissionRevokeHandler:
    """Handler for revoking permissions (explicit deny override)."""
    
    @transaction.atomic
    def handle(self, cmd: PermissionRevokeCommand) -> None:
        from bfagent_core.models import (
            TenantMembership,
            CorePermission,
            MembershipPermissionOverride,
        )
        
        # 1. Validate membership exists
        membership = TenantMembership.objects.filter(id=cmd.membership_id).first()
        if not membership:
            raise MembershipNotFoundError(membership_id=cmd.membership_id)
        
        # 2. Validate permission exists
        if not CorePermission.objects.filter(code=cmd.permission_code).exists():
            raise PermissionNotFoundError(cmd.permission_code)
        
        # 3. Calculate expiration
        expires_at = None
        if cmd.expires_in_days:
            expires_at = _utc_now() + timedelta(days=cmd.expires_in_days)
        
        # 4. Create or update override with allowed=False
        MembershipPermissionOverride.objects.update_or_create(
            membership=membership,
            permission_id=cmd.permission_code,
            defaults={
                "allowed": False,  # DENY
                "expires_at": expires_at,
                "reason": cmd.reason,
                "granted_by_id": cmd.granted_by_id,
            }
        )
        
        # 5. Increment permission version
        membership.increment_permission_version()
        
        # 6. Invalidate cache
        cache = get_permission_cache()
        cache.invalidate(membership.tenant_id, membership.user_id)


# ═══════════════════════════════════════════════════════════════════════════════
# PERMISSION CLEAR
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PermissionClearCommand:
    """Command for clearing a permission override (back to role default)."""
    membership_id: UUID
    permission_code: str


class PermissionClearHandler:
    """Handler for clearing permission overrides."""
    
    @transaction.atomic
    def handle(self, cmd: PermissionClearCommand) -> None:
        from bfagent_core.models import TenantMembership, MembershipPermissionOverride
        
        # 1. Validate membership exists
        membership = TenantMembership.objects.filter(id=cmd.membership_id).first()
        if not membership:
            raise MembershipNotFoundError(membership_id=cmd.membership_id)
        
        # 2. Delete override if exists
        deleted, _ = MembershipPermissionOverride.objects.filter(
            membership=membership,
            permission_id=cmd.permission_code,
        ).delete()
        
        if deleted:
            # 3. Increment permission version
            membership.increment_permission_version()
            
            # 4. Invalidate cache
            cache = get_permission_cache()
            cache.invalidate(membership.tenant_id, membership.user_id)
