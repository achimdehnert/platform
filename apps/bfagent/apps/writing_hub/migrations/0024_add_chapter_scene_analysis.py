from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bfagent', '0001_initial'),
        ('writing_hub', '0023_add_correction_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChapterSceneAnalysis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scenes', models.JSONField(default=list)),
                ('best_scene_index', models.IntegerField(default=0)),
                ('best_scene_reason', models.TextField(blank=True)),
                ('overall_color_mood', models.CharField(blank=True, max_length=200)),
                ('chapter_atmosphere', models.CharField(blank=True, max_length=200)),
                ('analysis_model', models.CharField(default='gpt-4o', help_text='LLM verwendet für Analyse', max_length=50)),
                ('analysis_version', models.IntegerField(default=1)),
                ('analysis_tokens_used', models.IntegerField(default=0)),
                ('content_hash', models.CharField(blank=True, help_text='SHA256 des Kapitelinhalts', max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('chapter', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='scene_analysis', to='bfagent.bookchapters')),
            ],
            options={
                'verbose_name': 'Kapitel-Szenenanalyse',
                'verbose_name_plural': 'Kapitel-Szenenanalysen',
                'db_table': 'writing_chapter_scene_analysis',
            },
        ),
    ]
