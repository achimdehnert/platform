"""
bfagent_core models package.

Exports all models for easy importing:
    from bfagent_core.models import Tenant, TenantMembership, CoreUser
"""

from bfagent_core.models.plan import Plan
from bfagent_core.models.user import CoreUser, CoreUserManager
from bfagent_core.models.tenant import (
    Tenant,
    TenantStatus,
    TenantManager,
    TenantQuerySet,
)
from bfagent_core.models.membership import (
    TenantMembership,
    TenantRole,
    MembershipStatus,
    TenantMembershipManager,
    TenantMembershipQuerySet,
)
from bfagent_core.models.permission import (
    CorePermission,
    CoreRolePermission,
    MembershipPermissionOverride,
    PermissionAudit,
)

# Legacy models from original bfagent-core (audit & outbox)
from bfagent_core.models.legacy import AuditEvent, OutboxMessage

__all__ = [
    # Plan
    "Plan",
    # User
    "CoreUser",
    "CoreUserManager",
    # Tenant
    "Tenant",
    "TenantStatus",
    "TenantManager",
    "TenantQuerySet",
    # Membership
    "TenantMembership",
    "TenantRole",
    "MembershipStatus",
    "TenantMembershipManager",
    "TenantMembershipQuerySet",
    # Permissions
    "CorePermission",
    "CoreRolePermission",
    "MembershipPermissionOverride",
    "PermissionAudit",
    # Legacy (Audit & Outbox)
    "AuditEvent",
    "OutboxMessage",
]
