from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('writing_hub', '0030_world_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='promptmasterstyle',
            name='preview_image',
            field=models.ImageField(blank=True, null=True, upload_to='master_style_previews/', verbose_name='Vorschaubild'),
        ),
        migrations.AddField(
            model_name='promptmasterstyle',
            name='preview_generated_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Vorschau generiert am'),
        ),
    ]
