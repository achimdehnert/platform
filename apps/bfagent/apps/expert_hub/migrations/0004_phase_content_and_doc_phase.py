from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('expert_hub', '0003_workflow_phases'),
    ]

    operations = [
        migrations.AddField(
            model_name='exsessionphasestatus',
            name='content',
            field=models.TextField(blank=True, help_text='Textinhalt dieser Phase'),
        ),
        migrations.AddField(
            model_name='exsessionphasestatus',
            name='ai_generated_content',
            field=models.TextField(blank=True, help_text='KI-generierter Inhalt'),
        ),
        migrations.AddField(
            model_name='exsessiondocument',
            name='phase',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='documents', to='expert_hub.exworkflowphase'),
        ),
    ]
