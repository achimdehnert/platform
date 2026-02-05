"""
Migration: Create core_permission_audit table.

Audit trail for permission changes.
"""

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    
    dependencies = [
        ('bfagent_core', '0006_permissions'),
    ]
    
    operations = [
        migrations.CreateModel(
            name='PermissionAudit',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False,
                )),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('membership_id', models.UUIDField(db_index=True)),
                ('user_id', models.UUIDField(db_index=True)),
                ('permission_code', models.CharField(max_length=100)),
                ('action', models.CharField(
                    help_text='grant, revoke, clear, role_change',
                    max_length=20,
                )),
                ('performed_by_id', models.UUIDField(blank=True, null=True)),
                ('performed_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('previous_value', models.JSONField(blank=True, null=True)),
                ('new_value', models.JSONField(blank=True, null=True)),
                ('reason', models.TextField(blank=True, default='')),
                ('request_id', models.CharField(blank=True, default='', max_length=64)),
            ],
            options={
                'db_table': 'core_permission_audit',
                'ordering': ['-performed_at'],
            },
        ),
        
        # Indexes
        migrations.AddIndex(
            model_name='permissionaudit',
            index=models.Index(
                fields=['tenant_id', 'performed_at'],
                name='core_perm_audit_tenant_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='permissionaudit',
            index=models.Index(
                fields=['membership_id'],
                name='core_perm_audit_membership_idx',
            ),
        ),
    ]
