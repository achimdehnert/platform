"""
Permission enums and role-permission mapping.

Single source of truth for permission definitions.
Sync to DB via sync_permissions_to_db().
"""

from enum import Enum
from typing import Dict, FrozenSet


class Permission(str, Enum):
    """
    Permission codes.
    
    Naming convention: <resource>.<action>
    Actions: view, create, edit, delete, manage, export, publish, invite
    """
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TENANT
    # ═══════════════════════════════════════════════════════════════════════════
    TENANT_VIEW = "tenant.view"
    TENANT_EDIT = "tenant.edit"
    TENANT_MANAGE = "tenant.manage"
    TENANT_DELETE = "tenant.delete"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MEMBERS
    # ═══════════════════════════════════════════════════════════════════════════
    MEMBERS_VIEW = "members.view"
    MEMBERS_INVITE = "members.invite"
    MEMBERS_EDIT = "members.edit"
    MEMBERS_REMOVE = "members.remove"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STORIES
    # ═══════════════════════════════════════════════════════════════════════════
    STORIES_VIEW = "stories.view"
    STORIES_CREATE = "stories.create"
    STORIES_EDIT = "stories.edit"
    STORIES_DELETE = "stories.delete"
    STORIES_PUBLISH = "stories.publish"
    STORIES_EXPORT = "stories.export"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PROJECTS
    # ═══════════════════════════════════════════════════════════════════════════
    PROJECTS_VIEW = "projects.view"
    PROJECTS_CREATE = "projects.create"
    PROJECTS_EDIT = "projects.edit"
    PROJECTS_DELETE = "projects.delete"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # AI FEATURES
    # ═══════════════════════════════════════════════════════════════════════════
    AI_GENERATE = "ai.generate"
    AI_USE_PREMIUM = "ai.use_premium"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SETTINGS & AUDIT
    # ═══════════════════════════════════════════════════════════════════════════
    SETTINGS_VIEW = "settings.view"
    SETTINGS_EDIT = "settings.edit"
    AUDIT_VIEW = "audit.view"
    API_KEYS_MANAGE = "api_keys.manage"


# Role → Permissions mapping
ROLE_PERMISSIONS: Dict[str, FrozenSet[Permission]] = {
    "owner": frozenset(Permission),  # All permissions
    
    "admin": frozenset(Permission) - frozenset([
        Permission.TENANT_DELETE,
    ]),
    
    "member": frozenset([
        Permission.TENANT_VIEW,
        Permission.MEMBERS_VIEW,
        Permission.STORIES_VIEW,
        Permission.STORIES_CREATE,
        Permission.STORIES_EDIT,
        Permission.STORIES_EXPORT,
        Permission.PROJECTS_VIEW,
        Permission.PROJECTS_CREATE,
        Permission.PROJECTS_EDIT,
        Permission.AI_GENERATE,
        Permission.SETTINGS_VIEW,
    ]),
    
    "viewer": frozenset([
        Permission.TENANT_VIEW,
        Permission.MEMBERS_VIEW,
        Permission.STORIES_VIEW,
        Permission.PROJECTS_VIEW,
        Permission.SETTINGS_VIEW,
    ]),
}


def get_role_permissions(role: str) -> FrozenSet[str]:
    """Get permission codes for a role."""
    perms = ROLE_PERMISSIONS.get(role, frozenset())
    return frozenset(p.value for p in perms)


def role_has_permission(role: str, permission: str | Permission) -> bool:
    """Check if role has permission."""
    if isinstance(permission, Permission):
        permission = permission.value
    
    role_perms = ROLE_PERMISSIONS.get(role, frozenset())
    return any(p.value == permission for p in role_perms)


def sync_permissions_to_db() -> None:
    """
    Sync Python Enum → DB.
    
    Call in migration or management command:
        python manage.py shell -c "from bfagent_core.permissions import sync_permissions_to_db; sync_permissions_to_db()"
    """
    from bfagent_core.models import CorePermission, CoreRolePermission
    
    # Sync permissions
    for perm in Permission:
        category = perm.value.split('.')[0]
        CorePermission.objects.update_or_create(
            code=perm.value,
            defaults={
                "description": f"Permission: {perm.value}",
                "category": category,
            }
        )
    
    # Sync role-permissions
    for role, perms in ROLE_PERMISSIONS.items():
        # Remove old assignments not in current set
        current_codes = [p.value for p in perms]
        CoreRolePermission.objects.filter(role=role).exclude(
            permission_id__in=current_codes
        ).delete()
        
        # Add new assignments
        for perm in perms:
            CoreRolePermission.objects.get_or_create(
                role=role,
                permission_id=perm.value,
            )
    
    print(f"Synced {len(Permission)} permissions and {len(ROLE_PERMISSIONS)} roles")
