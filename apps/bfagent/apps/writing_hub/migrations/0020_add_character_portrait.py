from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('writing_hub', '0019_change_idea_fields_to_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='promptcharacter',
            name='portrait_image',
            field=models.ImageField(blank=True, help_text='Generiertes Charakter-Portrait', null=True, upload_to='prompt_system/portraits/'),
        ),
        migrations.AddField(
            model_name='promptcharacter',
            name='portrait_generated_at',
            field=models.DateTimeField(blank=True, help_text='Zeitpunkt der Portrait-Generierung', null=True),
        ),
    ]
