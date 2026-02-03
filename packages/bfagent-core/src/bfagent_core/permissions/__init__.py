"""
Permission system for bfagent-core.

Public API:
    from bfagent_core.permissions import (
        Permission,
        has_permission,
        check_permission,
        require_permission,
        require_role,
        TenantPermissionMixin,
    )
"""

from bfagent_core.permissions.enums import (
    Permission,
    ROLE_PERMISSIONS,
    get_role_permissions,
    role_has_permission,
    sync_permissions_to_db,
)

from bfagent_core.permissions.checker import (
    PermissionChecker,
    get_permission_checker,
    has_permission,
    check_permission,
    get_user_permissions,
)

from bfagent_core.permissions.resolver import (
    PermissionResolver,
    PermissionResult,
    get_permission_resolver,
)

from bfagent_core.permissions.cache import (
    PermissionCache,
    get_permission_cache,
)

from bfagent_core.permissions.decorators import (
    require_permission,
    require_role,
    require_any_permission,
    require_all_permissions,
    require_tenant_access,
)

from bfagent_core.permissions.mixins import (
    TenantPermissionMixin,
    TenantAdminRequiredMixin,
    TenantOwnerRequiredMixin,
    TenantAPIPermissionMixin,
)

__all__ = [
    # Enums
    "Permission",
    "ROLE_PERMISSIONS",
    "get_role_permissions",
    "role_has_permission",
    "sync_permissions_to_db",
    # Checker
    "PermissionChecker",
    "get_permission_checker",
    "has_permission",
    "check_permission",
    "get_user_permissions",
    # Resolver
    "PermissionResolver",
    "PermissionResult",
    "get_permission_resolver",
    # Cache
    "PermissionCache",
    "get_permission_cache",
    # Decorators
    "require_permission",
    "require_role",
    "require_any_permission",
    "require_all_permissions",
    "require_tenant_access",
    # Mixins
    "TenantPermissionMixin",
    "TenantAdminRequiredMixin",
    "TenantOwnerRequiredMixin",
    "TenantAPIPermissionMixin",
]
