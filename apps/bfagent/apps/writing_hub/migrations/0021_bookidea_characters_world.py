from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('writing_hub', '0020_add_llm_to_creative_session'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookidea',
            name='characters_data',
            field=models.JSONField(default=list, help_text='Extrahierte Charaktere [{name, role, description, motivation}]'),
        ),
        migrations.AddField(
            model_name='bookidea',
            name='world_data',
            field=models.JSONField(default=dict, help_text='Extrahierte Welt {name, description, key_features, atmosphere}'),
        ),
    ]
