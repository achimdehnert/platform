"""
Handlers package for use case orchestration.

All handlers use Command/Result pattern and @transaction.atomic.

Usage:
    from bfagent_core.handlers import TenantCreateHandler, TenantCreateCommand
    
    handler = TenantCreateHandler()
    result = handler.handle(TenantCreateCommand(
        slug="acme",
        name="ACME Corp",
        plan_code="professional",
        owner_user_id=user_id,
    ))
"""

from bfagent_core.handlers.tenant import (
    TenantCreateCommand,
    TenantCreateResult,
    TenantCreateHandler,
    TenantActivateCommand,
    TenantActivateHandler,
    TenantSuspendCommand,
    TenantSuspendHandler,
    TenantDeleteCommand,
    TenantDeleteHandler,
)

from bfagent_core.handlers.membership import (
    MembershipInviteCommand,
    MembershipInviteResult,
    MembershipInviteHandler,
    MembershipAcceptCommand,
    MembershipAcceptHandler,
    MembershipChangeRoleCommand,
    MembershipChangeRoleHandler,
    MembershipRemoveCommand,
    MembershipRemoveHandler,
)

from bfagent_core.handlers.permission import (
    PermissionGrantCommand,
    PermissionGrantHandler,
    PermissionRevokeCommand,
    PermissionRevokeHandler,
    PermissionClearCommand,
    PermissionClearHandler,
)

__all__ = [
    # Tenant
    "TenantCreateCommand",
    "TenantCreateResult",
    "TenantCreateHandler",
    "TenantActivateCommand",
    "TenantActivateHandler",
    "TenantSuspendCommand",
    "TenantSuspendHandler",
    "TenantDeleteCommand",
    "TenantDeleteHandler",
    # Membership
    "MembershipInviteCommand",
    "MembershipInviteResult",
    "MembershipInviteHandler",
    "MembershipAcceptCommand",
    "MembershipAcceptHandler",
    "MembershipChangeRoleCommand",
    "MembershipChangeRoleHandler",
    "MembershipRemoveCommand",
    "MembershipRemoveHandler",
    # Permission
    "PermissionGrantCommand",
    "PermissionGrantHandler",
    "PermissionRevokeCommand",
    "PermissionRevokeHandler",
    "PermissionClearCommand",
    "PermissionClearHandler",
]
