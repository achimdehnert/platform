"""
Migration: Create permission tables.

- core_permission: Permission registry
- core_role_permission: Role → Permission mapping
- core_membership_permission_override: Per-user overrides
"""

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    
    dependencies = [
        ('bfagent_core', '0005_membership'),
    ]
    
    operations = [
        # ═══════════════════════════════════════════════════════════════════════
        # CORE PERMISSION
        # ═══════════════════════════════════════════════════════════════════════
        migrations.CreateModel(
            name='CorePermission',
            fields=[
                ('code', models.CharField(
                    help_text="Permission code (e.g., 'stories.create')",
                    max_length=100,
                    primary_key=True,
                    serialize=False,
                )),
                ('description', models.TextField(
                    blank=True,
                    default='',
                    help_text='Human-readable description',
                )),
                ('category', models.CharField(
                    db_index=True,
                    default='general',
                    help_text='Permission category for grouping',
                    max_length=50,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'core_permission',
                'ordering': ['category', 'code'],
            },
        ),
        
        # ═══════════════════════════════════════════════════════════════════════
        # CORE ROLE PERMISSION
        # ═══════════════════════════════════════════════════════════════════════
        migrations.CreateModel(
            name='CoreRolePermission',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID',
                )),
                ('role', models.CharField(
                    db_index=True,
                    help_text='Role name (owner, admin, member, viewer)',
                    max_length=20,
                )),
                ('permission', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='role_assignments',
                    to='bfagent_core.corepermission',
                )),
            ],
            options={
                'db_table': 'core_role_permission',
                'unique_together': {('role', 'permission')},
            },
        ),
        
        # Role constraint
        migrations.AddConstraint(
            model_name='corerolepermission',
            constraint=models.CheckConstraint(
                check=models.Q(role__in=['owner', 'admin', 'member', 'viewer']),
                name='role_permission_role_chk',
            ),
        ),
        
        # ═══════════════════════════════════════════════════════════════════════
        # MEMBERSHIP PERMISSION OVERRIDE
        # ═══════════════════════════════════════════════════════════════════════
        migrations.CreateModel(
            name='MembershipPermissionOverride',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID',
                )),
                ('membership', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='permission_overrides',
                    to='bfagent_core.tenantmembership',
                )),
                ('permission', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='membership_overrides',
                    to='bfagent_core.corepermission',
                )),
                ('allowed', models.BooleanField(
                    help_text='True = grant, False = deny',
                )),
                ('expires_at', models.DateTimeField(
                    blank=True,
                    help_text='Override expires at this time (NULL = permanent)',
                    null=True,
                )),
                ('reason', models.TextField(
                    blank=True,
                    default='',
                    help_text='Reason for override',
                )),
                ('granted_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='permission_grants',
                    to='bfagent_core.coreuser',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'core_membership_permission_override',
                'unique_together': {('membership', 'permission')},
            },
        ),
        
        # Partial index for expiring overrides
        migrations.RunSQL(
            sql="""
                CREATE INDEX core_override_expires_idx 
                ON core_membership_permission_override(expires_at) 
                WHERE expires_at IS NOT NULL;
            """,
            reverse_sql="DROP INDEX IF EXISTS core_override_expires_idx;",
        ),
        
        # Trigger to increment membership.permission_version on override changes
        migrations.RunSQL(
            sql="""
                CREATE OR REPLACE FUNCTION trg_override_permission_version()
                RETURNS TRIGGER AS $$
                BEGIN
                    UPDATE core_tenant_membership 
                    SET permission_version = permission_version + 1,
                        updated_at = NOW()
                    WHERE id = COALESCE(NEW.membership_id, OLD.membership_id);
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                
                DROP TRIGGER IF EXISTS override_permission_version_trigger ON core_membership_permission_override;
                
                CREATE TRIGGER override_permission_version_trigger
                    AFTER INSERT OR UPDATE OR DELETE ON core_membership_permission_override
                    FOR EACH ROW
                    EXECUTE FUNCTION trg_override_permission_version();
            """,
            reverse_sql="""
                DROP TRIGGER IF EXISTS override_permission_version_trigger ON core_membership_permission_override;
                DROP FUNCTION IF EXISTS trg_override_permission_version();
            """,
        ),
    ]
