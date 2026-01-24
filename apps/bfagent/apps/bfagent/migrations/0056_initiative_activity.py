# Generated manually for InitiativeActivity model
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('bfagent', '0055_initiative_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='InitiativeActivity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action', models.CharField(choices=[
                    ('created', 'Initiative erstellt'),
                    ('status_change', 'Status geändert'),
                    ('analysis_started', 'Analyse gestartet'),
                    ('analysis_completed', 'Analyse abgeschlossen'),
                    ('concept_added', 'Konzept hinzugefügt'),
                    ('requirement_added', 'Requirement hinzugefügt'),
                    ('requirement_completed', 'Requirement abgeschlossen'),
                    ('mcp_tool_called', 'MCP Tool aufgerufen'),
                    ('llm_invoked', 'LLM aufgerufen'),
                    ('comment', 'Kommentar'),
                    ('error', 'Fehler'),
                ], max_length=50)),
                ('details', models.TextField(blank=True)),
                ('actor', models.CharField(default='system', help_text='cascade, user, system', max_length=100)),
                ('mcp_tool_used', models.CharField(blank=True, max_length=100)),
                ('llm_model', models.CharField(blank=True, max_length=100)),
                ('tokens_used', models.IntegerField(default=0)),
                ('estimated_cost', models.DecimalField(decimal_places=6, default=0, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('duration_ms', models.IntegerField(default=0, help_text='Duration in milliseconds')),
                ('initiative', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to='bfagent.initiative')),
            ],
            options={
                'db_table': 'bfagent_initiative_activity',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='initiativeactivity',
            index=models.Index(fields=['initiative', '-created_at'], name='bfagent_ini_init_created_idx'),
        ),
        migrations.AddIndex(
            model_name='initiativeactivity',
            index=models.Index(fields=['action'], name='bfagent_ini_action_idx'),
        ),
        migrations.AddIndex(
            model_name='initiativeactivity',
            index=models.Index(fields=['mcp_tool_used'], name='bfagent_ini_mcp_tool_idx'),
        ),
    ]
