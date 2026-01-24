# Generated manually for Test Studio Quick Win
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bfagent', '0044_add_figure_caption_settings'),  # Latest existing migration
    ]

    operations = [
        migrations.AddField(
            model_name='testrequirement',
            name='domain',
            field=models.CharField(
                choices=[
                    ('writing_hub', 'Writing Hub'),
                    ('medtrans', 'MedTrans'),
                    ('control_center', 'Control Center'),
                    ('genagent', 'GenAgent'),
                    ('core', 'Core/Shared'),
                ],
                default='core',
                help_text='Which domain/app does this requirement belong to?',
                max_length=50,
            ),
        ),
        migrations.AddIndex(
            model_name='testrequirement',
            index=models.Index(fields=['domain', 'status'], name='bfagent_tes_domain_idx'),
        ),
    ]
