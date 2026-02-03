"""
Migration: Create core_user table.

SSO-ready user table with bridge to Django auth_user.
"""

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    
    dependencies = [
        ('bfagent_core', '0002_plan'),
    ]
    
    operations = [
        migrations.CreateModel(
            name='CoreUser',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False,
                )),
                ('external_id', models.CharField(
                    blank=True,
                    help_text='External provider ID (e.g., Auth0 sub, Okta uid)',
                    max_length=255,
                    null=True,
                    unique=True,
                )),
                ('provider', models.CharField(
                    blank=True,
                    default='local',
                    help_text='Identity provider: local, auth0, okta, saml',
                    max_length=50,
                )),
                ('legacy_user_id', models.IntegerField(
                    blank=True,
                    help_text='Django auth_user.id for backwards compatibility',
                    null=True,
                    unique=True,
                )),
                ('email', models.EmailField(
                    blank=True,
                    db_index=True,
                    default='',
                    help_text='Email (may be synced from provider)',
                    max_length=254,
                )),
                ('display_name', models.CharField(
                    blank=True,
                    default='',
                    help_text='Display name for UI',
                    max_length=255,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_login_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'core_user',
            },
        ),
        
        # Indexes
        migrations.AddIndex(
            model_name='coreuser',
            index=models.Index(fields=['provider', 'external_id'], name='core_user_provider_external_idx'),
        ),
        migrations.AddIndex(
            model_name='coreuser',
            index=models.Index(fields=['legacy_user_id'], name='core_user_legacy_idx'),
        ),
        
        # Constraint: At least one identity
        migrations.AddConstraint(
            model_name='coreuser',
            constraint=models.CheckConstraint(
                check=models.Q(legacy_user_id__isnull=False) | models.Q(external_id__isnull=False),
                name='user_identity_chk',
            ),
        ),
    ]
