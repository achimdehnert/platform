"""
Membership handlers for invitation and management.

All handlers use @transaction.atomic for data consistency.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from django.db import transaction

from bfagent_core.exceptions import (
    MembershipNotFoundError,
    MembershipExistsError,
    InvitationExpiredError,
    InvitationNotPendingError,
    TenantNotFoundError,
    UserNotFoundError,
)


def _utc_now() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# MEMBERSHIP INVITE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MembershipInviteCommand:
    """Command for inviting a user to a tenant."""
    tenant_id: UUID
    user_id: UUID
    role: str
    invited_by_id: UUID
    expires_in_days: int = 7


@dataclass(frozen=True)
class MembershipInviteResult:
    """Result of membership invitation."""
    membership_id: UUID
    expires_at: datetime


class MembershipInviteHandler:
    """Handler for inviting users to a tenant."""
    
    @transaction.atomic
    def handle(self, cmd: MembershipInviteCommand) -> MembershipInviteResult:
        from bfagent_core.models import Tenant, TenantMembership, CoreUser, MembershipStatus
        
        # 1. Validate tenant exists
        tenant = Tenant.objects.filter(id=cmd.tenant_id).first()
        if not tenant:
            raise TenantNotFoundError(cmd.tenant_id)
        
        # 2. Validate user exists
        user = CoreUser.objects.filter(id=cmd.user_id).first()
        if not user:
            raise UserNotFoundError(cmd.user_id)
        
        # 3. Check for existing membership
        existing = TenantMembership.objects.filter(
            tenant_id=cmd.tenant_id,
            user_id=cmd.user_id,
        ).first()
        
        if existing:
            if existing.status == MembershipStatus.ACTIVE:
                raise MembershipExistsError(cmd.tenant_id, cmd.user_id)
            # Reactivate deactivated membership
            if existing.status == MembershipStatus.DEACTIVATED:
                existing.status = MembershipStatus.PENDING
                existing.role = cmd.role
                existing.invited_by_id = cmd.invited_by_id
                existing.invited_at = _utc_now()
                existing.invitation_expires_at = _utc_now() + timedelta(days=cmd.expires_in_days)
                existing.save()
                return MembershipInviteResult(
                    membership_id=existing.id,
                    expires_at=existing.invitation_expires_at,
                )
        
        # 4. Create pending invitation
        expires_at = _utc_now() + timedelta(days=cmd.expires_in_days)
        membership = TenantMembership.objects.create(
            tenant=tenant,
            user=user,
            role=cmd.role,
            status=MembershipStatus.PENDING,
            invited_by_id=cmd.invited_by_id,
            invited_at=_utc_now(),
            invitation_expires_at=expires_at,
        )
        
        return MembershipInviteResult(
            membership_id=membership.id,
            expires_at=expires_at,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# MEMBERSHIP ACCEPT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MembershipAcceptCommand:
    """Command for accepting an invitation."""
    membership_id: UUID


class MembershipAcceptHandler:
    """Handler for accepting invitations."""
    
    @transaction.atomic
    def handle(self, cmd: MembershipAcceptCommand) -> None:
        from bfagent_core.models import TenantMembership, MembershipStatus
        
        membership = TenantMembership.objects.filter(id=cmd.membership_id).first()
        if not membership:
            raise MembershipNotFoundError(membership_id=cmd.membership_id)
        
        if membership.status != MembershipStatus.PENDING:
            raise InvitationNotPendingError(cmd.membership_id, membership.status)
        
        if membership.is_invitation_expired:
            raise InvitationExpiredError(cmd.membership_id)
        
        membership.accept_invitation()


# ═══════════════════════════════════════════════════════════════════════════════
# MEMBERSHIP CHANGE ROLE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MembershipChangeRoleCommand:
    """Command for changing a member's role."""
    membership_id: UUID
    new_role: str


class MembershipChangeRoleHandler:
    """Handler for changing roles."""
    
    @transaction.atomic
    def handle(self, cmd: MembershipChangeRoleCommand) -> None:
        from bfagent_core.models import TenantMembership
        
        membership = TenantMembership.objects.filter(id=cmd.membership_id).first()
        if not membership:
            raise MembershipNotFoundError(membership_id=cmd.membership_id)
        
        membership.change_role(cmd.new_role)


# ═══════════════════════════════════════════════════════════════════════════════
# MEMBERSHIP REMOVE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MembershipRemoveCommand:
    """Command for removing a member (soft)."""
    membership_id: UUID


class MembershipRemoveHandler:
    """Handler for removing members."""
    
    @transaction.atomic
    def handle(self, cmd: MembershipRemoveCommand) -> None:
        from bfagent_core.models import TenantMembership
        
        membership = TenantMembership.objects.filter(id=cmd.membership_id).first()
        if not membership:
            raise MembershipNotFoundError(membership_id=cmd.membership_id)
        
        membership.deactivate()
