# Generated manually for CodeRefactorSession model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bfagent', '0059_add_depends_on_to_testrequirement'),
    ]

    operations = [
        migrations.CreateModel(
            name='CodeRefactorSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file_path', models.CharField(db_index=True, help_text="Relativer Pfad zur Datei (z.B. 'apps/bfagent/services/llm_client.py')", max_length=500)),
                ('instruction', models.TextField(help_text='Was soll refactored/optimiert werden?')),
                ('original_content', models.TextField(blank=True, help_text='Originaler Datei-Inhalt (für Rollback und Diff)')),
                ('original_hash', models.CharField(blank=True, help_text='SHA-256 Hash des Originals (für Konflikt-Erkennung)', max_length=64)),
                ('proposed_content', models.TextField(blank=True, help_text='Vom LLM vorgeschlagener neuer Inhalt')),
                ('unified_diff', models.TextField(blank=True, help_text='Diff zwischen Original und Vorschlag (für Review-UI)')),
                ('status', models.CharField(choices=[('draft', 'Entwurf'), ('generating', 'LLM generiert...'), ('pending_review', 'Wartet auf Review'), ('approved', 'Genehmigt'), ('applied', 'Angewendet'), ('rejected', 'Abgelehnt'), ('reverted', 'Zurückgesetzt'), ('error', 'Fehler')], db_index=True, default='draft', max_length=20)),
                ('error_message', models.TextField(blank=True, help_text='Fehlermeldung falls Status=ERROR')),
                ('llm_model', models.CharField(blank=True, help_text="Verwendetes LLM (z.B. 'gpt-4o-mini')", max_length=100)),
                ('llm_tokens_input', models.IntegerField(default=0)),
                ('llm_tokens_output', models.IntegerField(default=0)),
                ('llm_duration_ms', models.IntegerField(default=0)),
                ('backup_content', models.TextField(blank=True, help_text='Backup vor Apply (für Revert)')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('review_notes', models.TextField(blank=True)),
                ('applied_at', models.DateTimeField(blank=True, null=True)),
                ('reverted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('applied_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='applied_refactor_sessions', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_refactor_sessions', to=settings.AUTH_USER_MODEL)),
                ('requirement', models.ForeignKey(help_text='Das Requirement, das dieses Refactoring auslöste', on_delete=django.db.models.deletion.CASCADE, related_name='refactor_sessions', to='bfagent.testrequirement')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_refactor_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'bfagent_code_refactor_session',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='coderefactorsession',
            index=models.Index(fields=['requirement', 'status'], name='bfagent_cod_require_idx'),
        ),
        migrations.AddIndex(
            model_name='coderefactorsession',
            index=models.Index(fields=['file_path'], name='bfagent_cod_file_pa_idx'),
        ),
        migrations.AddIndex(
            model_name='coderefactorsession',
            index=models.Index(fields=['status', 'created_at'], name='bfagent_cod_status_idx'),
        ),
    ]
