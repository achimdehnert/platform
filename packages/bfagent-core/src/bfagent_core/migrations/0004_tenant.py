"""
Migration: Create core_tenant table.

Central tenant model with lifecycle management.
"""

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    
    dependencies = [
        ('bfagent_core', '0003_core_user'),
    ]
    
    operations = [
        migrations.CreateModel(
            name='Tenant',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    help_text='Unique tenant ID (UUID v4)',
                    primary_key=True,
                    serialize=False,
                )),
                ('slug', models.SlugField(
                    help_text='URL-friendly identifier for subdomains',
                    max_length=63,
                    unique=True,
                )),
                ('name', models.CharField(
                    help_text='Organization display name',
                    max_length=255,
                )),
                ('status', models.CharField(
                    choices=[
                        ('trial', 'Trial'),
                        ('active', 'Active'),
                        ('suspended', 'Suspended'),
                        ('deleted', 'Deleted'),
                    ],
                    db_index=True,
                    default='trial',
                    max_length=20,
                )),
                ('trial_ends_at', models.DateTimeField(
                    blank=True,
                    help_text='End of trial period',
                    null=True,
                )),
                ('suspended_at', models.DateTimeField(blank=True, null=True)),
                ('suspended_reason', models.TextField(blank=True, default='')),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('plan', models.ForeignKey(
                    default='free',
                    help_text='Subscription plan',
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='tenants',
                    to='bfagent_core.plan',
                )),
                ('settings', models.JSONField(
                    default=dict,
                    help_text="{'timezone': 'Europe/Berlin', 'locale': 'de-DE'}",
                )),
                ('stripe_customer_id', models.CharField(
                    blank=True,
                    max_length=255,
                    null=True,
                    unique=True,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'core_tenant',
                'ordering': ['name'],
                'verbose_name': 'Tenant',
                'verbose_name_plural': 'Tenants',
            },
        ),
        
        # Status constraint
        migrations.AddConstraint(
            model_name='tenant',
            constraint=models.CheckConstraint(
                check=models.Q(status__in=['trial', 'active', 'suspended', 'deleted']),
                name='tenant_status_chk',
            ),
        ),
        
        # Indexes
        migrations.AddIndex(
            model_name='tenant',
            index=models.Index(fields=['slug'], name='core_tenant_slug_idx'),
        ),
        migrations.AddIndex(
            model_name='tenant',
            index=models.Index(fields=['status'], name='core_tenant_status_idx'),
        ),
    ]
