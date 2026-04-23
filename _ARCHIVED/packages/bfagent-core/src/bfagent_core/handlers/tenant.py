"""
Tenant handlers for use case orchestration.

All handlers use @transaction.atomic for data consistency.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from django.db import transaction

from bfagent_core.exceptions import (
    TenantSlugExistsError,
    TenantNotFoundError,
    TenantInactiveError,
)


def _utc_now() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT CREATE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TenantCreateCommand:
    """Command for tenant creation."""
    slug: str
    name: str
    plan_code: str
    owner_user_id: UUID
    trial_days: int = 14


@dataclass(frozen=True)
class TenantCreateResult:
    """Result of tenant creation."""
    tenant_id: UUID
    membership_id: UUID
    trial_ends_at: datetime


class TenantCreateHandler:
    """
    Handler for tenant creation use case.
    
    Creates tenant and owner membership atomically.
    """
    
    @transaction.atomic
    def handle(self, cmd: TenantCreateCommand) -> TenantCreateResult:
        from bfagent_core.models import Tenant, TenantMembership, TenantStatus, TenantRole, CoreUser
        
        # 1. Validate slug uniqueness
        if Tenant.objects.filter(slug=cmd.slug).exists():
            raise TenantSlugExistsError(cmd.slug)
        
        # 2. Get owner user
        owner = CoreUser.objects.filter(id=cmd.owner_user_id).first()
        if not owner:
            from bfagent_core.exceptions import UserNotFoundError
            raise UserNotFoundError(cmd.owner_user_id)
        
        # 3. Create tenant
        trial_ends = _utc_now() + timedelta(days=cmd.trial_days)
        tenant = Tenant.objects.create(
            slug=cmd.slug,
            name=cmd.name,
            plan_id=cmd.plan_code,
            status=TenantStatus.TRIAL,
            trial_ends_at=trial_ends,
        )
        
        # 4. Create owner membership
        membership = TenantMembership.objects.create(
            tenant=tenant,
            user=owner,
            role=TenantRole.OWNER,
            status="active",
        )
        
        return TenantCreateResult(
            tenant_id=tenant.id,
            membership_id=membership.id,
            trial_ends_at=trial_ends,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT ACTIVATE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TenantActivateCommand:
    """Command for tenant activation."""
    tenant_id: UUID


class TenantActivateHandler:
    """Handler for tenant activation (trial → active)."""
    
    @transaction.atomic
    def handle(self, cmd: TenantActivateCommand) -> None:
        from bfagent_core.models import Tenant
        
        tenant = Tenant.objects.filter(id=cmd.tenant_id).first()
        if not tenant:
            raise TenantNotFoundError(cmd.tenant_id)
        
        tenant.activate()


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT SUSPEND
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TenantSuspendCommand:
    """Command for tenant suspension."""
    tenant_id: UUID
    reason: str = ""


class TenantSuspendHandler:
    """Handler for tenant suspension."""
    
    @transaction.atomic
    def handle(self, cmd: TenantSuspendCommand) -> None:
        from bfagent_core.models import Tenant
        
        tenant = Tenant.objects.filter(id=cmd.tenant_id).first()
        if not tenant:
            raise TenantNotFoundError(cmd.tenant_id)
        
        tenant.suspend(reason=cmd.reason)


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT DELETE (Soft)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TenantDeleteCommand:
    """Command for tenant soft-delete."""
    tenant_id: UUID


class TenantDeleteHandler:
    """Handler for tenant soft-delete."""
    
    @transaction.atomic
    def handle(self, cmd: TenantDeleteCommand) -> None:
        from bfagent_core.models import Tenant
        
        tenant = Tenant.objects.filter(id=cmd.tenant_id).first()
        if not tenant:
            raise TenantNotFoundError(cmd.tenant_id)
        
        tenant.soft_delete()
