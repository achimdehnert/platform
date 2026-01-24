from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bfagent', '0042_fix_worlds_technology_level'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookprojects',
            name='title',
            field=models.CharField(max_length=500),
        ),
        migrations.AlterField(
            model_name='bookprojects',
            name='genre',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='bookprojects',
            name='tagline',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='bookprojects',
            name='story_themes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='bookprojects',
            name='setting_time',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='bookprojects',
            name='setting_location',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='bookprojects',
            name='atmosphere_tone',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='bookprojects',
            name='stakes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='bookprojects',
            name='protagonist_concept',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='bookprojects',
            name='antagonist_concept',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='bookprojects',
            name='inspiration_sources',
            field=models.TextField(blank=True, null=True),
        ),
    ]
