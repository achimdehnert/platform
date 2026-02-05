"""
Migration: Create core_plan table.

This is the first table in the tenant RBAC system, required as FK for tenants.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    
    dependencies = [
        ('bfagent_core', '0001_initial'),
    ]
    
    operations = [
        migrations.CreateModel(
            name='Plan',
            fields=[
                ('code', models.CharField(
                    help_text="Unique plan identifier (e.g., 'free', 'professional')",
                    max_length=50,
                    primary_key=True,
                    serialize=False,
                )),
                ('name', models.CharField(
                    help_text='Display name (English)',
                    max_length=100,
                )),
                ('name_de', models.CharField(
                    blank=True,
                    default='',
                    help_text='Display name (German)',
                    max_length=100,
                )),
                ('description', models.TextField(
                    blank=True,
                    default='',
                    help_text='Plan description',
                )),
                ('is_public', models.BooleanField(
                    default=True,
                    help_text='Show in pricing page',
                )),
                ('sort_order', models.IntegerField(
                    default=0,
                    help_text='Display order in UI',
                )),
                ('monthly_price_cents', models.IntegerField(
                    blank=True,
                    help_text='Monthly price in cents',
                    null=True,
                )),
                ('yearly_price_cents', models.IntegerField(
                    blank=True,
                    help_text='Yearly price in cents',
                    null=True,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'core_plan',
                'ordering': ['sort_order', 'code'],
            },
        ),
        
        # Insert default plans (use Python for DB compatibility)
        migrations.RunPython(
            code=lambda apps, schema_editor: apps.get_model('bfagent_core', 'Plan').objects.bulk_create([
                apps.get_model('bfagent_core', 'Plan')(code='free', name='Free', name_de='Kostenlos', description='Basic features for individuals', is_public=True, sort_order=0),
                apps.get_model('bfagent_core', 'Plan')(code='professional', name='Professional', name_de='Professional', description='Advanced features for teams', is_public=True, sort_order=10),
                apps.get_model('bfagent_core', 'Plan')(code='enterprise', name='Enterprise', name_de='Enterprise', description='Full features for organizations', is_public=True, sort_order=20),
            ], ignore_conflicts=True),
            reverse_code=lambda apps, schema_editor: apps.get_model('bfagent_core', 'Plan').objects.filter(code__in=['free', 'professional', 'enterprise']).delete(),
        ),
    ]
