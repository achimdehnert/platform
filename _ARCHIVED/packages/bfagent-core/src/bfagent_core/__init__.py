"""
bfagent-core: Shared core components for BFAgent Hub ecosystem.

As of v0.2.0, the framework-agnostic foundation (context, middleware, db,
audit, outbox, exceptions) has been extracted to `platform-context`
(see ADR-028). This package re-exports everything for backward compatibility.

New projects should depend on `platform-context` directly.

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

# Re-export from platform-context (ADR-028 compatibility shim)
from platform_context.context import (
    RequestContext,
    clear_context,
    get_context,
    set_request_id,
    set_tenant,
    set_user_id,
)
from platform_context.audit import emit_audit_event
from platform_context.outbox import emit_outbox_event
from platform_context.db import set_db_tenant, get_db_tenant


def _get_models():
    """Lazy import to avoid circular deps."""
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
    # Context (from platform-context)
    "RequestContext",
    "clear_context",
    "get_context",
    "set_request_id",
    "set_tenant",
    "set_user_id",
    # Audit (from platform-context)
    "emit_audit_event",
    # Outbox (from platform-context)
    "emit_outbox_event",
    # DB (from platform-context)
    "set_db_tenant",
    "get_db_tenant",
]
