# Generated manually for StyleLabSession LLM field

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bfagent', '0001_initial'),
        ('writing_hub', '0015_sentence_feedback'),
    ]

    operations = [
        migrations.AddField(
            model_name='stylelabsession',
            name='llm',
            field=models.ForeignKey(
                blank=True,
                help_text='LLM für Stil-Analyse und Generierung. Leer = System-Default (bevorzugt Ollama)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='style_lab_sessions',
                to='bfagent.llms',
            ),
        ),
    ]
