# Generated manually for Import Framework V2
# Migration creates new models for Smart Import and Outline Generation

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bfagent', '0072_import_framework_v2_fields'),
        ('writing_hub', '0035_book_series_models'),
    ]

    operations = [
        # ImportPromptTemplate
        migrations.CreateModel(
            name='ImportPromptTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('step_code', models.CharField(help_text='Unique step identifier (e.g., type_detection, metadata_extraction)', max_length=100, unique=True)),
                ('step_name', models.CharField(max_length=200)),
                ('step_name_de', models.CharField(blank=True, max_length=200, null=True)),
                ('description', models.TextField(blank=True)),
                ('step_order', models.PositiveIntegerField(default=10)),
                ('system_prompt', models.TextField(help_text='System prompt for the LLM')),
                ('user_prompt_template', models.TextField(help_text='User prompt template with {placeholders}')),
                ('output_schema', models.JSONField(blank=True, help_text='Expected JSON schema for validation', null=True)),
                ('example_input', models.TextField(blank=True, help_text='Example input for documentation', null=True)),
                ('example_output', models.TextField(blank=True, help_text='Example output for documentation', null=True)),
                ('temperature', models.FloatField(default=0.2)),
                ('max_tokens', models.PositiveIntegerField(default=4000)),
                ('preferred_model', models.CharField(blank=True, help_text="Preferred LLM model (e.g., 'gpt-4o', 'claude-3')", max_length=100, null=True)),
                ('fallback_model', models.CharField(blank=True, max_length=100, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('version', models.PositiveIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Import Prompt Template',
                'verbose_name_plural': 'Import Prompt Templates',
                'db_table': 'writing_hub_import_prompt_template',
                'ordering': ['step_order', 'step_code'],
            },
        ),
        
        # OutlineCategory
        migrations.CreateModel(
            name='OutlineCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('name_de', models.CharField(blank=True, max_length=100, null=True)),
                ('description', models.TextField(blank=True)),
                ('icon', models.CharField(blank=True, help_text='Icon class or emoji', max_length=50, null=True)),
                ('order', models.PositiveIntegerField(default=10)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Outline Category',
                'verbose_name_plural': 'Outline Categories',
                'db_table': 'writing_hub_outline_category',
                'ordering': ['order', 'name'],
            },
        ),
        
        # OutlineTemplate
        migrations.CreateModel(
            name='OutlineTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=100, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('name_de', models.CharField(blank=True, max_length=200, null=True)),
                ('description', models.TextField()),
                ('description_de', models.TextField(blank=True, null=True)),
                ('structure_json', models.JSONField(help_text='Full structure: acts, beats, chapters')),
                ('genre_tags', models.JSONField(default=list, help_text='Suitable genres')),
                ('theme_tags', models.JSONField(default=list, help_text='Suitable themes')),
                ('pov_tags', models.JSONField(default=list, help_text='Suitable POV styles')),
                ('word_count_min', models.PositiveIntegerField(default=60000)),
                ('word_count_max', models.PositiveIntegerField(default=100000)),
                ('difficulty_level', models.CharField(choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced')], default='intermediate', max_length=20)),
                ('example_books', models.TextField(blank=True, help_text='Famous books using this structure')),
                ('pros', models.TextField(blank=True)),
                ('cons', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('is_featured', models.BooleanField(default=False)),
                ('usage_count', models.PositiveIntegerField(default=0)),
                ('avg_rating', models.FloatField(default=0.0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='templates', to='writing_hub.outlinecategory')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Outline Template',
                'verbose_name_plural': 'Outline Templates',
                'db_table': 'writing_hub_outline_template',
                'ordering': ['-is_featured', '-usage_count', 'name'],
            },
        ),
        
        # ProjectOutline
        migrations.CreateModel(
            name='ProjectOutline',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.PositiveIntegerField(default=1)),
                ('outline_data', models.JSONField(help_text='Generated/edited outline')),
                ('is_active', models.BooleanField(default=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('in_progress', 'In Progress'), ('review', 'Under Review'), ('approved', 'Approved'), ('finalized', 'Finalized')], default='draft', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outlines', to='bfagent.bookprojects')),
                ('template', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='writing_hub.outlinetemplate')),
            ],
            options={
                'verbose_name': 'Project Outline',
                'verbose_name_plural': 'Project Outlines',
                'db_table': 'writing_hub_project_outline',
                'ordering': ['-version'],
            },
        ),
        
        # ImportSession
        migrations.CreateModel(
            name='ImportSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.CharField(max_length=100, unique=True)),
                ('source_filename', models.CharField(max_length=500)),
                ('source_type', models.CharField(choices=[('upload', 'File Upload'), ('paste', 'Pasted Text'), ('url', 'URL Import'), ('api', 'API Import')], default='upload', max_length=20)),
                ('document_type', models.CharField(blank=True, help_text='Detected document type', max_length=50, null=True)),
                ('status', models.CharField(choices=[('started', 'Started'), ('analyzing', 'Analyzing'), ('type_detected', 'Type Detected'), ('metadata_extracted', 'Metadata Extracted'), ('characters_extracted', 'Characters Extracted'), ('locations_extracted', 'Locations Extracted'), ('structure_extracted', 'Structure Extracted'), ('review', 'Ready for Review'), ('importing', 'Importing'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='started', max_length=30)),
                ('raw_content', models.TextField(blank=True, help_text='Original content')),
                ('extracted_data', models.JSONField(blank=True, help_text='Full extraction result', null=True)),
                ('selected_items', models.JSONField(blank=True, help_text='User selections', null=True)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('step_results', models.JSONField(blank=True, default=dict, help_text='Results per step')),
                ('total_tokens_used', models.PositiveIntegerField(default=0)),
                ('total_cost', models.DecimalField(decimal_places=4, default=0, max_digits=10)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='import_sessions', to='bfagent.bookprojects')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Import Session',
                'verbose_name_plural': 'Import Sessions',
                'db_table': 'writing_hub_import_session',
                'ordering': ['-started_at'],
            },
        ),
        
        # OutlineRecommendation
        migrations.CreateModel(
            name='OutlineRecommendation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rank', models.PositiveIntegerField()),
                ('match_score', models.FloatField()),
                ('match_reason', models.TextField()),
                ('llm_analysis', models.TextField(blank=True, help_text='Full LLM analysis')),
                ('was_selected', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('import_session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recommendations', to='writing_hub.importsession')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='writing_hub.outlinetemplate')),
            ],
            options={
                'verbose_name': 'Outline Recommendation',
                'verbose_name_plural': 'Outline Recommendations',
                'db_table': 'writing_hub_outline_recommendation',
                'ordering': ['import_session', 'rank'],
                'unique_together': {('import_session', 'template')},
            },
        ),
        
        # Add unique constraint
        migrations.AddConstraint(
            model_name='projectoutline',
            constraint=models.UniqueConstraint(condition=models.Q(('is_active', True)), fields=('project',), name='unique_active_outline_per_project'),
        ),
    ]
