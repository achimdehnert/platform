# Generated manually for World Building V2

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('writing_hub', '0029_world_building_v2'),
        ('bfagent', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='World',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(blank=True, max_length=200)),
                ('description', models.TextField(blank=True)),
                ('cover_image', models.ImageField(blank=True, null=True, upload_to='worlds/')),
                ('setting_era', models.CharField(blank=True, help_text='Zeitepoche', max_length=200)),
                ('geography', models.TextField(blank=True, help_text='Landschaften, Klima, Orte')),
                ('climate', models.TextField(blank=True, help_text='Klimazonen, Wetter')),
                ('inhabitants', models.TextField(blank=True, help_text='Völker, Rassen, Bewohner')),
                ('culture', models.TextField(blank=True, help_text='Traditionen, Religion, Werte')),
                ('religion', models.TextField(blank=True, help_text='Glaubenssysteme')),
                ('technology_level', models.CharField(blank=True, help_text='Technologiestufe', max_length=200)),
                ('magic_system', models.TextField(blank=True, help_text='Magiesystem falls vorhanden')),
                ('politics', models.TextField(blank=True, help_text='Machtverhältnisse, Regierungsformen')),
                ('economy', models.TextField(blank=True, help_text='Wirtschaftssystem')),
                ('history', models.TextField(blank=True, help_text='Wichtige historische Ereignisse')),
                ('is_public', models.BooleanField(default=False, help_text='Kann von anderen Usern adoptiert werden')),
                ('is_template', models.BooleanField(default=False, help_text='Vorlage für neue Welten')),
                ('version', models.PositiveIntegerField(default=1)),
                ('tags', models.JSONField(blank=True, default=list, help_text='Tags für Suche und Filterung (Liste von Strings)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='worlds', to=settings.AUTH_USER_MODEL)),
                ('world_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='worlds', to='writing_hub.worldtype')),
            ],
            options={
                'verbose_name': 'World',
                'verbose_name_plural': 'Worlds',
                'db_table': 'writing_worlds',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ProjectWorld',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('role', models.CharField(choices=[('primary', 'Hauptwelt'), ('secondary', 'Nebenwelt'), ('mentioned', 'Erwähnt'), ('flashback', 'Rückblende')], default='primary', max_length=20)),
                ('custom_name', models.CharField(blank=True, help_text='Anderer Name im Projekt (optional)', max_length=200)),
                ('project_notes', models.TextField(blank=True, help_text='Projekt-spezifische Notizen')),
                ('timeline_offset', models.IntegerField(default=0, help_text='Jahre vor/nach Welt-Timeline')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='world_links', to='bfagent.bookprojects')),
                ('world', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_links', to='writing_hub.world')),
            ],
            options={
                'verbose_name': 'Project World',
                'verbose_name_plural': 'Project Worlds',
                'db_table': 'writing_project_worlds',
                'ordering': ['role', 'world__name'],
                'unique_together': {('project', 'world')},
            },
        ),
        migrations.CreateModel(
            name='WorldLocation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('location_type', models.CharField(choices=[('continent', 'Kontinent'), ('country', 'Land'), ('region', 'Region'), ('city', 'Stadt'), ('district', 'Stadtteil'), ('building', 'Gebäude'), ('landmark', 'Wahrzeichen'), ('natural', 'Naturmerkmal')], default='city', max_length=20)),
                ('description', models.TextField(blank=True)),
                ('significance', models.TextField(blank=True, help_text='Bedeutung für die Story')),
                ('coordinates', models.JSONField(blank=True, help_text="{'x': 0, 'y': 0} für Karten", null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='children', to='writing_hub.worldlocation')),
                ('world', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='locations', to='writing_hub.world')),
            ],
            options={
                'verbose_name': 'World Location',
                'verbose_name_plural': 'World Locations',
                'db_table': 'writing_world_locations',
                'ordering': ['location_type', 'name'],
            },
        ),
        migrations.CreateModel(
            name='WorldRule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('category', models.CharField(choices=[('physics', 'Physik'), ('magic', 'Magie'), ('social', 'Gesellschaft'), ('technology', 'Technologie'), ('biology', 'Biologie'), ('economy', 'Wirtschaft')], default='physics', max_length=20)),
                ('rule', models.CharField(help_text='Die Regel selbst', max_length=500)),
                ('explanation', models.TextField(blank=True, help_text='Erklärung/Begründung')),
                ('importance', models.CharField(choices=[('absolute', 'Absolut - Nie brechen'), ('strong', 'Stark - Nur mit gutem Grund'), ('guideline', 'Richtlinie - Flexibel')], default='strong', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('world', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rules', to='writing_hub.world')),
            ],
            options={
                'verbose_name': 'World Rule',
                'verbose_name_plural': 'World Rules',
                'db_table': 'writing_world_rules',
                'ordering': ['category', '-importance', 'rule'],
            },
        ),
    ]
