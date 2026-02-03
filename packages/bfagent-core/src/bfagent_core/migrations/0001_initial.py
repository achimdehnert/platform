"""
Initial migration for bfagent-core.

Creates the legacy AuditEvent and OutboxMessage tables.
"""

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    
    initial = True
    
    dependencies = []
    
    operations = [
        # AuditEvent
        migrations.CreateModel(
            name='AuditEvent',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False,
                )),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('actor_user_id', models.UUIDField(
                    blank=True,
                    db_index=True,
                    null=True,
                )),
                ('category', models.CharField(db_index=True, max_length=80)),
                ('action', models.CharField(db_index=True, max_length=80)),
                ('entity_type', models.CharField(db_index=True, max_length=120)),
                ('entity_id', models.UUIDField(db_index=True)),
                ('payload', models.JSONField(default=dict)),
                ('request_id', models.CharField(
                    blank=True,
                    db_index=True,
                    max_length=64,
                    null=True,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'db_table': 'bfagent_core_audit_event',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='auditevent',
            index=models.Index(
                fields=['tenant_id', 'created_at'],
                name='bfagent_cor_tenant__7b4d4e_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='auditevent',
            index=models.Index(
                fields=['entity_type', 'entity_id'],
                name='bfagent_cor_entity__3c4f5a_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='auditevent',
            index=models.Index(
                fields=['tenant_id', 'category', 'action'],
                name='bfagent_cor_tenant__8d5e6f_idx',
            ),
        ),
        
        # OutboxMessage
        migrations.CreateModel(
            name='OutboxMessage',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False,
                )),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('topic', models.CharField(db_index=True, max_length=120)),
                ('payload', models.JSONField(default=dict)),
                ('published_at', models.DateTimeField(
                    blank=True,
                    db_index=True,
                    null=True,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'db_table': 'bfagent_core_outbox_message',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='outboxmessage',
            index=models.Index(
                fields=['tenant_id', 'published_at', 'created_at'],
                name='bfagent_cor_tenant__9f6a7b_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='outboxmessage',
            index=models.Index(
                fields=['topic', 'created_at'],
                name='bfagent_cor_topic_c_1a2b3c_idx',
            ),
        ),
    ]
