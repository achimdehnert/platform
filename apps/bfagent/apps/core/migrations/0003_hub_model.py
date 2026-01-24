# Generated manually for Hub model

from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_unified_work_items'),
        ('control_center', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Hub',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hub_id', models.CharField(
                    help_text="Eindeutige Hub-ID (z.B. 'writing_hub')",
                    max_length=50,
                    unique=True,
                    validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9_]*$', 'Lowercase letters, numbers, underscores')]
                )),
                ('name', models.CharField(help_text='Anzeigename des Hubs', max_length=100)),
                ('version', models.CharField(default='1.0.0', max_length=20)),
                ('description', models.TextField(blank=True, default='')),
                ('author', models.CharField(default='BF Agent Team', max_length=100)),
                ('status', models.CharField(
                    choices=[
                        ('production', 'Production'),
                        ('beta', 'Beta'),
                        ('development', 'Development'),
                        ('deprecated', 'Deprecated'),
                        ('disabled', 'Disabled')
                    ],
                    default='production',
                    max_length=20
                )),
                ('category', models.CharField(
                    choices=[
                        ('content', 'Content'),
                        ('engineering', 'Engineering'),
                        ('system', 'System'),
                        ('research', 'Research'),
                        ('other', 'Other')
                    ],
                    default='other',
                    max_length=20
                )),
                ('icon', models.CharField(default='bi-puzzle', help_text='Bootstrap Icon class', max_length=50)),
                ('navigation_section', models.OneToOneField(
                    blank=True,
                    help_text='Verknüpfte NavigationSection für Sidebar',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='hub',
                    to='control_center.navigationsection'
                )),
                ('entry_point', models.CharField(blank=True, help_text="Python module path (z.B. 'apps.writing_hub')", max_length=100)),
                ('dependencies', models.JSONField(blank=True, default=list, help_text='Liste der Hub-IDs von denen dieser Hub abhängt')),
                ('provides', models.JSONField(blank=True, default=list, help_text='Was der Hub bereitstellt: views, models, handlers, api')),
                ('config', models.JSONField(blank=True, default=dict, help_text='Hub-spezifische Konfiguration als JSON')),
                ('config_schema', models.JSONField(blank=True, default=dict, help_text='JSON Schema für config Validierung')),
                ('is_active', models.BooleanField(default=True, help_text='Hub ist aktiviert')),
                ('is_installed', models.BooleanField(default=True, help_text='Hub-Code ist vorhanden')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Hub',
                'verbose_name_plural': 'Hubs',
                'db_table': 'core_hubs',
                'ordering': ['category', 'name'],
            },
        ),
    ]
