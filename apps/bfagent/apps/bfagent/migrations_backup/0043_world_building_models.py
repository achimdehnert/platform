# Generated migration for World Building models

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('bfagent', '0042_actionhandler_traffic_weight'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorldSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Name of the world/setting", max_length=200)),
                ('description', models.TextField(blank=True, help_text='General description of the world', null=True)),
                ('time_period', models.CharField(blank=True, help_text='When does the story take place?', max_length=200, null=True)),
                ('geography', models.TextField(blank=True, help_text='Physical geography and climate', null=True)),
                ('culture', models.TextField(blank=True, help_text='Cultural aspects, society, customs', null=True)),
                ('technology_level', models.CharField(blank=True, help_text='Technology level', max_length=200, null=True)),
                ('magic_system', models.TextField(blank=True, help_text='Magic system rules (if applicable)', null=True)),
                ('political_system', models.TextField(blank=True, help_text='Government, politics, power structures', null=True)),
                ('economy', models.TextField(blank=True, help_text='Economic system, currency, trade', null=True)),
                ('history', models.TextField(blank=True, help_text='Important historical events', null=True)),
                ('atmosphere', models.CharField(blank=True, help_text='Overall atmosphere/tone', max_length=200, null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.OneToOneField(help_text='Book project this world belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='world', to='bfagent.bookprojects')),
            ],
            options={
                'verbose_name': 'World Setting',
                'verbose_name_plural': 'World Settings',
                'db_table': 'world_settings',
            },
        ),
        migrations.CreateModel(
            name='WorldRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('magic', 'Magic System'), ('technology', 'Technology'), ('society', 'Social Rules'), ('physics', 'Physical Laws'), ('other', 'Other')], default='other', help_text='What category does this rule fall into?', max_length=100)),
                ('title', models.CharField(help_text='Short title for this rule', max_length=200)),
                ('description', models.TextField(help_text='Detailed description of the rule')),
                ('importance', models.CharField(choices=[('critical', 'Critical - Must not be broken'), ('important', 'Important - Should be followed'), ('guideline', 'Guideline - Flexible')], default='important', max_length=50)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('world', models.ForeignKey(help_text='World this rule applies to', on_delete=django.db.models.deletion.CASCADE, related_name='rules', to='bfagent.worldsetting')),
            ],
            options={
                'verbose_name': 'World Rule',
                'verbose_name_plural': 'World Rules',
                'db_table': 'world_rules',
                'ordering': ['-importance', 'title'],
            },
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Location name', max_length=200)),
                ('location_type', models.CharField(blank=True, help_text='Type of location', max_length=100, null=True)),
                ('description', models.TextField(blank=True, help_text='Detailed description of the location', null=True)),
                ('atmosphere', models.CharField(blank=True, help_text='Mood/atmosphere of this location', max_length=200, null=True)),
                ('importance', models.CharField(choices=[('major', 'Major Location'), ('minor', 'Minor Location'), ('background', 'Background')], default='minor', help_text='How important is this location to the story?', max_length=50)),
                ('notes', models.TextField(blank=True, help_text='Internal notes about this location', null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('parent_location', models.ForeignKey(blank=True, help_text='Parent location', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sub_locations', to='bfagent.location')),
                ('world', models.ForeignKey(help_text='World this location belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='locations', to='bfagent.worldsetting')),
            ],
            options={
                'verbose_name': 'Location',
                'verbose_name_plural': 'Locations',
                'db_table': 'locations',
                'ordering': ['name'],
            },
        ),
    ]
