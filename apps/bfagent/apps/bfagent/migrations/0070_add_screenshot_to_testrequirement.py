# Generated manually for screenshot field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bfagent', '0069_add_session_tracking'),
    ]

    operations = [
        migrations.AddField(
            model_name='testrequirement',
            name='screenshot',
            field=models.ImageField(
                blank=True,
                help_text='Screenshot des Bugs (Ctrl+V zum Einfügen)',
                null=True,
                upload_to='bug_screenshots/%Y/%m/%d/'
            ),
        ),
    ]
