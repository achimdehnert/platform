"""
Migration: Create core_tenant_membership table.

User-Tenant relationship with role and permission_version.
"""

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    
    dependencies = [
        ('bfagent_core', '0004_tenant'),
    ]
    
    operations = [
        migrations.CreateModel(
            name='TenantMembership',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False,
                )),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='memberships',
                    to='bfagent_core.tenant',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='memberships',
                    to='bfagent_core.coreuser',
                )),
                ('role', models.CharField(
                    choices=[
                        ('owner', 'Owner'),
                        ('admin', 'Admin'),
                        ('member', 'Member'),
                        ('viewer', 'Viewer'),
                    ],
                    db_index=True,
                    default='member',
                    max_length=20,
                )),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('active', 'Active'),
                        ('deactivated', 'Deactivated'),
                    ],
                    db_index=True,
                    default='active',
                    max_length=20,
                )),
                ('invited_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='invitations_sent',
                    to='bfagent_core.coreuser',
                )),
                ('invited_at', models.DateTimeField(blank=True, null=True)),
                ('invitation_expires_at', models.DateTimeField(blank=True, null=True)),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('permission_version', models.IntegerField(
                    default=1,
                    help_text='Incremented on role/permission changes for cache invalidation',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'core_tenant_membership',
                'verbose_name': 'Tenant Membership',
                'verbose_name_plural': 'Tenant Memberships',
            },
        ),
        
        # Unique constraint
        migrations.AddConstraint(
            model_name='tenantmembership',
            constraint=models.UniqueConstraint(
                fields=['tenant', 'user'],
                name='membership_unique',
            ),
        ),
        
        # Role constraint
        migrations.AddConstraint(
            model_name='tenantmembership',
            constraint=models.CheckConstraint(
                check=models.Q(role__in=['owner', 'admin', 'member', 'viewer']),
                name='membership_role_chk',
            ),
        ),
        
        # Status constraint
        migrations.AddConstraint(
            model_name='tenantmembership',
            constraint=models.CheckConstraint(
                check=models.Q(status__in=['pending', 'active', 'deactivated']),
                name='membership_status_chk',
            ),
        ),
        
        # Indexes
        migrations.AddIndex(
            model_name='tenantmembership',
            index=models.Index(fields=['tenant', 'user'], name='core_membership_tenant_user_idx'),
        ),
        migrations.AddIndex(
            model_name='tenantmembership',
            index=models.Index(fields=['user', 'status'], name='core_membership_user_status_idx'),
        ),
        
        # Partial index for pending invitations
        migrations.RunSQL(
            sql="""
                CREATE INDEX core_membership_pending_idx 
                ON core_tenant_membership(invitation_expires_at) 
                WHERE status = 'pending';
            """,
            reverse_sql="DROP INDEX IF EXISTS core_membership_pending_idx;",
        ),
        
        # Trigger for permission_version increment on role change (PostgreSQL only)
        migrations.RunSQL(
            sql=[
                ("""
                    CREATE OR REPLACE FUNCTION trg_membership_permission_version()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        IF OLD.role <> NEW.role THEN
                            NEW.permission_version := OLD.permission_version + 1;
                        END IF;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """, None),
                ("DROP TRIGGER IF EXISTS membership_permission_version_trigger ON core_tenant_membership;", None),
                ("""
                    CREATE TRIGGER membership_permission_version_trigger
                        BEFORE UPDATE OF role ON core_tenant_membership
                        FOR EACH ROW
                        EXECUTE FUNCTION trg_membership_permission_version();
                """, None),
            ],
            reverse_sql=[
                ("DROP TRIGGER IF EXISTS membership_permission_version_trigger ON core_tenant_membership;", None),
                ("DROP FUNCTION IF EXISTS trg_membership_permission_version();", None),
            ],
            state_operations=[],
        ),
    ]
