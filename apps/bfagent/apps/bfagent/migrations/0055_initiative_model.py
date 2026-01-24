# Generated manually for Initiative model
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bfagent', '0054_add_delegated_task_models'),
    ]

    operations = [
        # Create Initiative model
        migrations.CreateModel(
            name='Initiative',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(help_text='Titel der Initiative/des Konzepts', max_length=200)),
                ('description', models.TextField(help_text='Ausführliche Beschreibung des Konzepts')),
                ('analysis', models.TextField(blank=True, help_text='Analyse-Ergebnisse und Erkenntnisse')),
                ('concept', models.TextField(blank=True, help_text='Ausgearbeitetes Konzept/Lösung')),
                ('domain', models.CharField(choices=[
                    ('writing_hub', 'Writing Hub'),
                    ('cad_hub', 'CAD Hub'),
                    ('mcp_hub', 'MCP Hub'),
                    ('medtrans', 'MedTrans'),
                    ('control_center', 'Control Center'),
                    ('genagent', 'GenAgent'),
                    ('core', 'Core/Shared'),
                    ('multi', 'Multi-Domain'),
                ], default='core', help_text='Hauptbereich der Initiative', max_length=50)),
                ('priority', models.CharField(choices=[
                    ('critical', 'Critical'),
                    ('high', 'High'),
                    ('medium', 'Medium'),
                    ('low', 'Low'),
                ], default='medium', max_length=20)),
                ('status', models.CharField(choices=[
                    ('analysis', 'In Analyse'),
                    ('concept', 'Konzept-Phase'),
                    ('planning', 'Task-Planung'),
                    ('in_progress', 'In Bearbeitung'),
                    ('review', 'Review'),
                    ('completed', 'Abgeschlossen'),
                    ('on_hold', 'Pausiert'),
                    ('cancelled', 'Abgebrochen'),
                ], default='analysis', max_length=20)),
                ('tags', models.JSONField(blank=True, default=list, help_text='Tags für Filterung')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('estimated_hours', models.IntegerField(blank=True, help_text='Geschätzte Stunden für die gesamte Initiative', null=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='initiatives_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'bfagent_initiative',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='initiative',
            index=models.Index(fields=['status', 'priority'], name='bfagent_ini_status_idx'),
        ),
        migrations.AddIndex(
            model_name='initiative',
            index=models.Index(fields=['domain'], name='bfagent_ini_domain_idx'),
        ),
        # Add initiative FK to TestRequirement
        migrations.AddField(
            model_name='testrequirement',
            name='initiative',
            field=models.ForeignKey(blank=True, help_text='Übergeordnete Initiative/Konzept', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='requirements', to='bfagent.initiative'),
        ),
        # Add missing domains to TestRequirement
        migrations.AlterField(
            model_name='testrequirement',
            name='domain',
            field=models.CharField(choices=[
                ('writing_hub', 'Writing Hub'),
                ('cad_hub', 'CAD Hub'),
                ('mcp_hub', 'MCP Hub'),
                ('medtrans', 'MedTrans'),
                ('control_center', 'Control Center'),
                ('genagent', 'GenAgent'),
                ('core', 'Core/Shared'),
            ], default='core', help_text='Which domain/app does this requirement belong to?', max_length=50),
        ),
    ]
