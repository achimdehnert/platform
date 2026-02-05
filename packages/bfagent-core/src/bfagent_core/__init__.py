"""
bfagent-core: Shared core components for BFAgent Hub ecosystem.

Provides:
- Request context management (tenant, user, request_id)
- Multi-tenancy with Tenant, Membership, and RBAC
- Permission system with decorators and mixins
- Handlers for use case orchestration
- Audit event logging
- Outbox pattern for reliable events
- Postgres RLS helpers
- Django middleware for multi-tenancy

Usage:
    from bfagent_core import get_context, Tenant, TenantMembership
    from bfagent_core.permissions import Permission, require_permission
    from bfagent_core.handlers import TenantCreateHandler
"""

from bfagent_core.context import (
    RequestContext,
    get_context,
    set_request_id,
    set_tenant,
    set_user_id,
)
from bfagent_core.audit import emit_audit_event
from bfagent_core.outbox import emit_outbox_event
from bfagent_core.db import set_db_tenant, get_db_tenant

# Models (lazy import to avoid circular deps)
def _get_models():
    from bfagent_core.models import (
        Plan,
        CoreUser,
        Tenant,
        TenantStatus,
        TenantMembership,
        TenantRole,
        MembershipStatus,
        CorePermission,
        CoreRolePermission,
        MembershipPermissionOverride,
    )
    return {
        "Plan": Plan,
        "CoreUser": CoreUser,
        "Tenant": Tenant,
        "TenantStatus": TenantStatus,
        "TenantMembership": TenantMembership,
        "TenantRole": TenantRole,
        "MembershipStatus": MembershipStatus,
        "CorePermission": CorePermission,
        "CoreRolePermission": CoreRolePermission,
        "MembershipPermissionOverride": MembershipPermissionOverride,
    }

__version__ = "0.2.0"

__all__ = [
    # Context
    "RequestContext",
    "get_context",
    "set_request_id",
    "set_tenant",
    "set_user_id",
    # Audit
    "emit_audit_event",
    # Outbox
    "emit_outbox_event",
    # DB
    "set_db_tenant",
    "get_db_tenant",
]
