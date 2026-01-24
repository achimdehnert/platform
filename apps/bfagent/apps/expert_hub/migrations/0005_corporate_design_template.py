from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expert_hub', '0004_phase_content_and_doc_phase'),
    ]

    operations = [
        migrations.AddField(
            model_name='exanalysissession',
            name='template_file',
            field=models.FileField(
                blank=True,
                help_text='Word-Vorlage (.docx) für Corporate Design',
                null=True,
                upload_to='expert_hub/templates/'
            ),
        ),
        migrations.AddField(
            model_name='exanalysissession',
            name='company_logo',
            field=models.ImageField(
                blank=True,
                help_text='Firmenlogo für Deckblatt',
                null=True,
                upload_to='expert_hub/logos/'
            ),
        ),
    ]
