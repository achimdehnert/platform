"""
Migration: Sync permissions from Python Enum to DB.

This data migration populates:
- core_permission with all permission codes
- core_role_permission with role-permission mappings
"""

from django.db import migrations


def sync_permissions_forward(apps, schema_editor):
    """Sync Permission Enum → DB."""
    CorePermission = apps.get_model('bfagent_core', 'CorePermission')
    CoreRolePermission = apps.get_model('bfagent_core', 'CoreRolePermission')
    
    # All permissions with categories
    PERMISSIONS = [
        # Tenant
        ('tenant.view', 'tenant', 'View tenant details'),
        ('tenant.edit', 'tenant', 'Edit tenant settings'),
        ('tenant.manage', 'tenant', 'Manage tenant configuration'),
        ('tenant.delete', 'tenant', 'Delete tenant'),
        
        # Members
        ('members.view', 'members', 'View team members'),
        ('members.invite', 'members', 'Invite new members'),
        ('members.edit', 'members', 'Edit member roles'),
        ('members.remove', 'members', 'Remove members'),
        
        # Stories
        ('stories.view', 'stories', 'View stories'),
        ('stories.create', 'stories', 'Create new stories'),
        ('stories.edit', 'stories', 'Edit stories'),
        ('stories.delete', 'stories', 'Delete stories'),
        ('stories.publish', 'stories', 'Publish stories'),
        ('stories.export', 'stories', 'Export stories'),
        
        # Projects
        ('projects.view', 'projects', 'View projects'),
        ('projects.create', 'projects', 'Create projects'),
        ('projects.edit', 'projects', 'Edit projects'),
        ('projects.delete', 'projects', 'Delete projects'),
        
        # AI
        ('ai.generate', 'ai', 'Use AI generation'),
        ('ai.use_premium', 'ai', 'Use premium AI models'),
        
        # Settings
        ('settings.view', 'settings', 'View settings'),
        ('settings.edit', 'settings', 'Edit settings'),
        ('audit.view', 'settings', 'View audit log'),
        ('api_keys.manage', 'settings', 'Manage API keys'),
    ]
    
    # Role → Permission mappings
    ROLE_PERMISSIONS = {
        'owner': [p[0] for p in PERMISSIONS],  # All
        'admin': [p[0] for p in PERMISSIONS if p[0] != 'tenant.delete'],
        'member': [
            'tenant.view', 'members.view',
            'stories.view', 'stories.create', 'stories.edit', 'stories.export',
            'projects.view', 'projects.create', 'projects.edit',
            'ai.generate', 'settings.view',
        ],
        'viewer': [
            'tenant.view', 'members.view',
            'stories.view', 'projects.view', 'settings.view',
        ],
    }
    
    # Create permissions
    for code, category, description in PERMISSIONS:
        CorePermission.objects.update_or_create(
            code=code,
            defaults={
                'category': category,
                'description': description,
            }
        )
    
    # Create role-permission mappings
    for role, perms in ROLE_PERMISSIONS.items():
        for perm_code in perms:
            CoreRolePermission.objects.get_or_create(
                role=role,
                permission_id=perm_code,
            )
    
    print(f"Synced {len(PERMISSIONS)} permissions and {len(ROLE_PERMISSIONS)} roles")


def sync_permissions_reverse(apps, schema_editor):
    """Clear synced permissions (for rollback)."""
    CoreRolePermission = apps.get_model('bfagent_core', 'CoreRolePermission')
    CorePermission = apps.get_model('bfagent_core', 'CorePermission')
    
    CoreRolePermission.objects.all().delete()
    CorePermission.objects.all().delete()


class Migration(migrations.Migration):
    
    dependencies = [
        ('bfagent_core', '0007_permission_audit'),
    ]
    
    operations = [
        migrations.RunPython(
            sync_permissions_forward,
            sync_permissions_reverse,
        ),
    ]
