# Generated manually for MCPUsageLog model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bfagent', '0057_initiative_workflow_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='MCPUsageLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tool_name', models.CharField(db_index=True, max_length=100)),
                ('tool_category', models.CharField(blank=True, help_text='Category: domain, handler, refactor, initiative, task, rules', max_length=50)),
                ('arguments', models.JSONField(blank=True, default=dict)),
                ('result_summary', models.TextField(blank=True, help_text='First 500 chars of result')),
                ('status', models.CharField(choices=[('success', 'Erfolgreich'), ('error', 'Fehler'), ('timeout', 'Timeout'), ('cancelled', 'Abgebrochen')], default='success', max_length=20)),
                ('error_message', models.TextField(blank=True)),
                ('session_id', models.CharField(blank=True, db_index=True, max_length=100)),
                ('llm_model', models.CharField(blank=True, max_length=100)),
                ('tokens_input', models.IntegerField(default=0)),
                ('tokens_output', models.IntegerField(default=0)),
                ('tokens_total', models.IntegerField(default=0)),
                ('estimated_cost', models.DecimalField(decimal_places=6, default=0, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('duration_ms', models.IntegerField(default=0)),
                ('initiative', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mcp_usage_logs', to='bfagent.initiative')),
                ('requirement', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mcp_usage_logs', to='bfagent.testrequirement')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mcp_usage_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'MCP Usage Log',
                'verbose_name_plural': 'MCP Usage Logs',
                'db_table': 'bfagent_mcp_usage_log',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='mcpusagelog',
            index=models.Index(fields=['tool_name', '-created_at'], name='bfagent_mcp_tool_na_8e9f4a_idx'),
        ),
        migrations.AddIndex(
            model_name='mcpusagelog',
            index=models.Index(fields=['tool_category'], name='bfagent_mcp_tool_ca_b2c3d4_idx'),
        ),
        migrations.AddIndex(
            model_name='mcpusagelog',
            index=models.Index(fields=['status'], name='bfagent_mcp_status_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='mcpusagelog',
            index=models.Index(fields=['session_id'], name='bfagent_mcp_session_d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='mcpusagelog',
            index=models.Index(fields=['-created_at'], name='bfagent_mcp_created_g7h8i9_idx'),
        ),
    ]
