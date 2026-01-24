from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('expert_hub', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExSessionDocument',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file', models.FileField(upload_to='expert_hub/documents/%Y/%m/')),
                ('original_filename', models.CharField(default='', max_length=255)),
                ('file_size', models.IntegerField(default=0, help_text='Dateigröße in Bytes')),
                ('file_type', models.CharField(blank=True, help_text='MIME-Type', max_length=100)),
                ('document_type', models.CharField(choices=[('plan', 'Lageplan/Grundriss'), ('piid', 'P&ID / R&I-Schema'), ('datasheet', 'Datenblatt'), ('certificate', 'Zertifikat/Prüfbericht'), ('report', 'Gutachten/Bericht'), ('photo', 'Foto'), ('cad', 'CAD-Datei'), ('other', 'Sonstiges')], default='other', max_length=20)),
                ('description', models.TextField(blank=True)),
                ('analysis_status', models.CharField(choices=[('pending', 'Ausstehend'), ('processing', 'Wird analysiert'), ('completed', 'Analysiert'), ('failed', 'Fehler'), ('skipped', 'Übersprungen')], default='pending', max_length=20)),
                ('analysis_result', models.JSONField(blank=True, default=dict, help_text='Extrahierte Daten')),
                ('analysis_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('analyzed_at', models.DateTimeField(blank=True, null=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='expert_hub.exanalysissession')),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ex_uploaded_documents', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Session-Dokument',
                'verbose_name_plural': 'Session-Dokumente',
                'db_table': 'expert_hub_session_document',
                'ordering': ['-created_at'],
            },
        ),
    ]
