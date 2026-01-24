# Generated manually for Initiative workflow fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bfagent', '0056_initiative_activity'),
    ]

    operations = [
        migrations.AddField(
            model_name='initiative',
            name='workflow_phase',
            field=models.CharField(
                choices=[
                    ('kickoff', 'Kickoff'),
                    ('research', 'Recherche'),
                    ('analysis', 'Analyse'),
                    ('design', 'Design'),
                    ('implementation', 'Implementierung'),
                    ('testing', 'Testing'),
                    ('documentation', 'Dokumentation'),
                    ('review', 'Review'),
                    ('deployment', 'Deployment'),
                ],
                default='kickoff',
                help_text='Aktuelle Workflow-Phase',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='initiative',
            name='lessons_learned',
            field=models.TextField(blank=True, help_text='Was wurde gelernt? Best Practices, Probleme, Lösungen'),
        ),
        migrations.AddField(
            model_name='initiative',
            name='next_steps',
            field=models.TextField(blank=True, help_text='Nächste geplante Schritte'),
        ),
        migrations.AddField(
            model_name='initiative',
            name='blockers',
            field=models.TextField(blank=True, help_text='Aktuelle Blocker/Hindernisse'),
        ),
        migrations.AddField(
            model_name='initiative',
            name='related_files',
            field=models.JSONField(blank=True, default=list, help_text='Liste relevanter Dateipfade'),
        ),
        migrations.AddField(
            model_name='initiative',
            name='related_urls',
            field=models.JSONField(blank=True, default=list, help_text='Externe Links, Docs, Issues'),
        ),
    ]
