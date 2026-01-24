from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('expert_hub', '0002_exsessiondocument'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExWorkflowPhase',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('number', models.CharField(help_text="z.B. '1', '6.2.1'", max_length=10)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('order', models.IntegerField(default=0)),
                ('phase_type', models.CharField(choices=[('info', 'Informationssammlung'), ('analysis', 'Analyse'), ('calculation', 'Berechnung'), ('assessment', 'Bewertung'), ('documentation', 'Dokumentation'), ('approval', 'Freigabe')], default='info', max_length=20)),
                ('tool_name', models.CharField(blank=True, help_text="z.B. 'zone_analysis'", max_length=100)),
                ('help_text', models.TextField(blank=True, help_text='Hilfetext für diese Phase')),
                ('is_required', models.BooleanField(default=True)),
                ('is_active', models.BooleanField(default=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='expert_hub.exworkflowphase')),
            ],
            options={
                'verbose_name': 'Workflow-Phase',
                'verbose_name_plural': 'Workflow-Phasen',
                'db_table': 'expert_hub_workflow_phase',
                'ordering': ['order', 'number'],
            },
        ),
        migrations.CreateModel(
            name='ExSessionPhaseStatus',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('not_started', 'Nicht begonnen'), ('in_progress', 'In Bearbeitung'), ('completed', 'Abgeschlossen'), ('skipped', 'Übersprungen'), ('not_applicable', 'Nicht zutreffend')], default='not_started', max_length=20)),
                ('progress_percent', models.IntegerField(default=0)),
                ('notes', models.TextField(blank=True)),
                ('data', models.JSONField(blank=True, default=dict, help_text='Phasen-spezifische Daten')),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('phase', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='session_statuses', to='expert_hub.exworkflowphase')),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='phase_statuses', to='expert_hub.exanalysissession')),
            ],
            options={
                'verbose_name': 'Session-Phasenstatus',
                'verbose_name_plural': 'Session-Phasenstatus',
                'db_table': 'expert_hub_session_phase_status',
                'ordering': ['phase__order'],
                'unique_together': {('session', 'phase')},
            },
        ),
    ]
