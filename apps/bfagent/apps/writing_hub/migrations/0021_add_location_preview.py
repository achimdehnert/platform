# Generated manually for location preview fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('writing_hub', '0020_add_character_portrait'),
    ]

    operations = [
        migrations.AddField(
            model_name='promptlocation',
            name='preview_image',
            field=models.ImageField(blank=True, help_text='Generierte Ort-Vorschau', null=True, upload_to='prompt_system/location_previews/'),
        ),
        migrations.AddField(
            model_name='promptlocation',
            name='preview_generated_at',
            field=models.DateTimeField(blank=True, help_text='Zeitpunkt der Vorschau-Generierung', null=True),
        ),
    ]
