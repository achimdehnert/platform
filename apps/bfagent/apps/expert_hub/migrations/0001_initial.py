# Generated manually for Expert Hub models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ExAnalysisSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Name der Analyse', max_length=200)),
                ('description', models.TextField(blank=True)),
                ('project_name', models.CharField(blank=True, max_length=200)),
                ('project_location', models.CharField(blank=True, max_length=300)),
                ('status', models.CharField(choices=[('draft', 'Entwurf'), ('in_progress', 'In Bearbeitung'), ('review', 'In Prüfung'), ('completed', 'Abgeschlossen'), ('archived', 'Archiviert')], default='draft', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ex_analysis_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Ex-Analyse Session',
                'verbose_name_plural': 'Ex-Analyse Sessions',
                'db_table': 'expert_hub_analysis_session',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ExSubstance',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200, unique=True)),
                ('name_en', models.CharField(blank=True, max_length=200)),
                ('cas_number', models.CharField(blank=True, db_index=True, max_length=20)),
                ('lower_explosion_limit', models.FloatField(help_text='UEG in Vol-%')),
                ('upper_explosion_limit', models.FloatField(help_text='OEG in Vol-%')),
                ('flash_point_c', models.FloatField(blank=True, help_text='Flammpunkt in °C', null=True)),
                ('ignition_temperature_c', models.FloatField(blank=True, help_text='Zündtemperatur in °C', null=True)),
                ('vapor_density', models.FloatField(blank=True, help_text='Dampfdichte rel. zu Luft', null=True)),
                ('molar_mass', models.FloatField(blank=True, help_text='Molare Masse in g/mol', null=True)),
                ('temperature_class', models.CharField(blank=True, choices=[('T1', 'T1 (>450°C)'), ('T2', 'T2 (300-450°C)'), ('T3', 'T3 (200-300°C)'), ('T4', 'T4 (135-200°C)'), ('T5', 'T5 (100-135°C)'), ('T6', 'T6 (85-100°C)')], max_length=5)),
                ('explosion_group', models.CharField(blank=True, choices=[('IIA', 'IIA'), ('IIB', 'IIB'), ('IIC', 'IIC')], max_length=5)),
                ('data_source', models.CharField(default='GESTIS', max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Gefahrstoff',
                'verbose_name_plural': 'Gefahrstoffe',
                'db_table': 'expert_hub_substance',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ExZoneResult',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('room_name', models.CharField(max_length=200)),
                ('room_volume_m3', models.FloatField(blank=True, null=True)),
                ('zone_type', models.CharField(choices=[('zone_0', 'Zone 0'), ('zone_1', 'Zone 1'), ('zone_2', 'Zone 2'), ('zone_20', 'Zone 20'), ('zone_21', 'Zone 21'), ('zone_22', 'Zone 22'), ('none', 'Keine Ex-Zone')], max_length=20)),
                ('zone_category', models.CharField(choices=[('gas', 'Gas'), ('dust', 'Staub')], max_length=10)),
                ('zone_extent_m', models.FloatField(blank=True, help_text='Zonenausdehnung in m', null=True)),
                ('zone_volume_m3', models.FloatField(blank=True, help_text='Zonenvolumen in m³', null=True)),
                ('risk_level', models.CharField(choices=[('low', 'Gering'), ('medium', 'Mittel'), ('high', 'Hoch'), ('critical', 'Kritisch')], default='medium', max_length=20)),
                ('justification', models.TextField(help_text='Begründung mit Normbezug')),
                ('recommendations', models.JSONField(blank=True, default=list)),
                ('input_parameters', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='zone_results', to='expert_hub.exanalysissession')),
            ],
            options={
                'verbose_name': 'Zonen-Ergebnis',
                'verbose_name_plural': 'Zonen-Ergebnisse',
                'db_table': 'expert_hub_zone_result',
                'ordering': ['room_name'],
            },
        ),
        migrations.CreateModel(
            name='ExEquipmentCheck',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('equipment_name', models.CharField(max_length=200)),
                ('equipment_type', models.CharField(blank=True, max_length=100)),
                ('location', models.CharField(blank=True, max_length=200)),
                ('ex_marking', models.CharField(blank=True, max_length=100)),
                ('detected_category', models.CharField(blank=True, max_length=10)),
                ('detected_temp_class', models.CharField(blank=True, max_length=5)),
                ('detected_exp_group', models.CharField(blank=True, max_length=5)),
                ('target_zone', models.CharField(max_length=20)),
                ('required_category', models.CharField(max_length=10)),
                ('is_suitable', models.BooleanField(default=False)),
                ('issues', models.JSONField(blank=True, default=list)),
                ('recommendations', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='equipment_checks', to='expert_hub.exanalysissession')),
            ],
            options={
                'verbose_name': 'Equipment-Prüfung',
                'verbose_name_plural': 'Equipment-Prüfungen',
                'db_table': 'expert_hub_equipment_check',
                'ordering': ['equipment_name'],
            },
        ),
    ]
