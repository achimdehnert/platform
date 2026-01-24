# Generated manually for media_hub app
# Migration for: StylePreset, FormatPreset, QualityPreset, VoicePreset,
#                WorkflowDefinition, WorkflowBinding, RenderJob, RenderAttempt,
#                Asset, AssetFile, ParameterMapping

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # No external dependencies - using integer fields for cross-app references
    ]

    operations = [
        # StylePreset
        migrations.CreateModel(
            name='StylePreset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
                ('prompt_style', models.TextField(blank=True, help_text='Style prompt to append')),
                ('prompt_negative', models.TextField(blank=True, help_text='Negative prompt')),
                ('defaults', models.JSONField(default=dict, help_text='Default sampler settings')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.CharField(choices=[('illustration', 'Illustration'), ('comic', 'Comic'), ('cover', 'Cover Art'), ('food', 'Food Photography'), ('portrait', 'Portrait'), ('landscape', 'Landscape')], db_index=True, default='illustration', max_length=20)),
                ('color_palette', models.JSONField(blank=True, default=list, help_text='Suggested hex colors for this style')),
            ],
            options={
                'verbose_name': 'Style Preset',
                'verbose_name_plural': 'Style Presets',
                'db_table': 'media_hub_style_preset',
            },
        ),
        # FormatPreset
        migrations.CreateModel(
            name='FormatPreset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
                ('width', models.PositiveIntegerField(default=1024)),
                ('height', models.PositiveIntegerField(default=1024)),
                ('aspect_ratio', models.CharField(blank=True, help_text='e.g., 16:9, 1:1', max_length=10)),
                ('meta', models.JSONField(default=dict, help_text='Additional format metadata')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('use_case', models.CharField(choices=[('general', 'General'), ('comic_panel', 'Comic Panel'), ('book_cover', 'Book Cover'), ('audiobook', 'Audiobook Cover'), ('social', 'Social Media'), ('print', 'Print')], db_index=True, default='general', max_length=20)),
            ],
            options={
                'verbose_name': 'Format Preset',
                'verbose_name_plural': 'Format Presets',
                'db_table': 'media_hub_format_preset',
            },
        ),
        # QualityPreset
        migrations.CreateModel(
            name='QualityPreset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
                ('level', models.CharField(choices=[('draft', 'Draft'), ('standard', 'Standard'), ('high', 'High'), ('final', 'Final')], default='standard', max_length=20)),
                ('settings', models.JSONField(default=dict, help_text='Quality settings (steps, cfg, etc.)')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Quality Preset',
                'verbose_name_plural': 'Quality Presets',
                'db_table': 'media_hub_quality_preset',
            },
        ),
        # VoicePreset
        migrations.CreateModel(
            name='VoicePreset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
                ('engine', models.CharField(default='xtts', help_text='TTS engine identifier', max_length=50)),
                ('voice_id', models.CharField(help_text='Voice identifier for the engine', max_length=100)),
                ('defaults', models.JSONField(default=dict, help_text='Default TTS settings')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('language', models.CharField(choices=[('de', 'Deutsch'), ('en', 'English'), ('fr', 'Français'), ('es', 'Español')], db_index=True, default='de', max_length=5)),
                ('gender', models.CharField(choices=[('male', 'Male'), ('female', 'Female'), ('neutral', 'Neutral')], default='neutral', max_length=10)),
            ],
            options={
                'verbose_name': 'Voice Preset',
                'verbose_name_plural': 'Voice Presets',
                'db_table': 'media_hub_voice_preset',
            },
        ),
        # WorkflowDefinition
        migrations.CreateModel(
            name='WorkflowDefinition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(db_index=True, help_text='Workflow identifier', max_length=100)),
                ('version', models.PositiveIntegerField(default=1)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('workflow_json', models.JSONField(help_text='Full ComfyUI workflow graph')),
                ('sha256', models.CharField(blank=True, help_text='Hash of workflow_json for integrity', max_length=64)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('engine', models.CharField(choices=[('comfyui', 'ComfyUI'), ('xtts', 'XTTS (TTS)'), ('custom', 'Custom')], default='comfyui', max_length=20)),
                ('required_models', models.JSONField(default=list, help_text='List of required model files')),
            ],
            options={
                'verbose_name': 'Workflow Definition',
                'verbose_name_plural': 'Workflow Definitions',
                'db_table': 'media_hub_workflow_definition',
                'unique_together': {('key', 'version')},
            },
        ),
        # WorkflowBinding
        migrations.CreateModel(
            name='WorkflowBinding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job_type', models.CharField(choices=[('illustration', 'Illustration'), ('comic_panel', 'Comic Panel'), ('book_cover', 'Book Cover'), ('audio_chapter', 'Audio Chapter'), ('audio_full', 'Full Audio'), ('video_trailer', 'Video Trailer')], db_index=True, max_length=20, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='bindings', to='media_hub.workflowdefinition')),
                ('default_style_preset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='media_hub.stylepreset')),
                ('default_format_preset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='media_hub.formatpreset')),
                ('default_quality_preset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='media_hub.qualitypreset')),
            ],
            options={
                'verbose_name': 'Workflow Binding',
                'verbose_name_plural': 'Workflow Bindings',
                'db_table': 'media_hub_workflow_binding',
            },
        ),
        # RenderJob
        migrations.CreateModel(
            name='RenderJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('job_type', models.CharField(choices=[('illustration', 'Illustration'), ('comic_panel', 'Comic Panel'), ('book_cover', 'Book Cover'), ('audio_chapter', 'Audio Chapter'), ('audio_full', 'Full Audio'), ('video_trailer', 'Video Trailer')], db_index=True, max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('queued', 'Queued'), ('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], db_index=True, default='pending', max_length=20)),
                ('priority', models.PositiveSmallIntegerField(db_index=True, default=5)),
                ('ref_table', models.CharField(blank=True, help_text='Source table name', max_length=100)),
                ('ref_id', models.PositiveIntegerField(blank=True, help_text='Source record ID', null=True)),
                ('input_snapshot', models.JSONField(default=dict, help_text='Complete input parameters snapshot')),
                ('error_message', models.TextField(blank=True)),
                ('attempt_count', models.PositiveSmallIntegerField(default=0)),
                ('max_attempts', models.PositiveSmallIntegerField(default=3)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('org_id', models.PositiveIntegerField(blank=True, db_index=True, help_text='Organization ID (for future multi-tenancy)', null=True)),
                ('project_id', models.PositiveIntegerField(blank=True, null=True, db_index=True, help_text='BookProjects ID')),
                ('created_by_id', models.PositiveIntegerField(blank=True, null=True, help_text='User ID')),
                ('style_preset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='media_hub.stylepreset')),
                ('format_preset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='media_hub.formatpreset')),
                ('quality_preset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='media_hub.qualitypreset')),
                ('voice_preset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='media_hub.voicepreset')),
                ('workflow', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='media_hub.workflowdefinition')),
            ],
            options={
                'verbose_name': 'Render Job',
                'verbose_name_plural': 'Render Jobs',
                'db_table': 'media_hub_render_job',
            },
        ),
        migrations.AddIndex(
            model_name='renderjob',
            index=models.Index(fields=['status', 'created_at'], name='media_hub_r_status_idx'),
        ),
        migrations.AddIndex(
            model_name='renderjob',
            index=models.Index(fields=['project_id', 'job_type'], name='media_hub_r_project_idx'),
        ),
        migrations.AddIndex(
            model_name='renderjob',
            index=models.Index(fields=['org_id', 'status'], name='media_hub_r_org_idx'),
        ),
        # RenderAttempt
        migrations.CreateModel(
            name='RenderAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempt_no', models.PositiveSmallIntegerField(default=1)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('duration_ms', models.PositiveIntegerField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('error_traceback', models.TextField(blank=True)),
                ('output_data', models.JSONField(default=dict, help_text='Raw output from render engine')),
                ('comfy_prompt_id', models.CharField(blank=True, help_text='ComfyUI prompt_id for tracking', max_length=100)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attempts', to='media_hub.renderjob')),
            ],
            options={
                'verbose_name': 'Render Attempt',
                'verbose_name_plural': 'Render Attempts',
                'db_table': 'media_hub_render_attempt',
                'unique_together': {('job', 'attempt_no')},
            },
        ),
        # Asset
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('asset_type', models.CharField(choices=[('image', 'Image'), ('audio', 'Audio'), ('video', 'Video'), ('document', 'Document')], db_index=True, max_length=20)),
                ('title', models.CharField(blank=True, max_length=200)),
                ('description', models.TextField(blank=True)),
                ('tags', models.JSONField(default=list)),
                ('metadata', models.JSONField(default=dict, help_text='Asset metadata (dimensions, duration, etc.)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('org_id', models.PositiveIntegerField(blank=True, db_index=True, help_text='Organization ID (for future multi-tenancy)', null=True)),
                ('content_type', models.CharField(blank=True, help_text='Content type: scene, panel, chapter, etc.', max_length=100)),
                ('content_id', models.PositiveIntegerField(blank=True, help_text='Content record ID', null=True)),
                ('is_approved', models.BooleanField(default=False, help_text='Approved for use/publication')),
                ('is_featured', models.BooleanField(default=False, help_text='Featured/highlighted asset')),
                ('job', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assets', to='media_hub.renderjob')),
                ('project_id', models.PositiveIntegerField(blank=True, null=True, db_index=True, help_text='BookProjects ID')),
                ('created_by_id', models.PositiveIntegerField(blank=True, null=True, help_text='User ID')),
            ],
            options={
                'verbose_name': 'Asset',
                'verbose_name_plural': 'Assets',
                'db_table': 'media_hub_asset',
            },
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['project_id', 'asset_type'], name='media_hub_a_project_idx'),
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['content_type', 'content_id'], name='media_hub_a_content_idx'),
        ),
        # AssetFile
        migrations.CreateModel(
            name='AssetFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_type', models.CharField(choices=[('original', 'Original'), ('thumbnail', 'Thumbnail'), ('preview', 'Preview'), ('optimized', 'Optimized')], default='original', max_length=20)),
                ('storage_path', models.CharField(help_text='Path in storage backend', max_length=500)),
                ('storage_backend', models.CharField(default='local', max_length=50)),
                ('mime_type', models.CharField(blank=True, max_length=100)),
                ('file_size', models.PositiveBigIntegerField(blank=True, null=True)),
                ('checksum', models.CharField(blank=True, max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='media_hub.asset')),
            ],
            options={
                'verbose_name': 'Asset File',
                'verbose_name_plural': 'Asset Files',
                'db_table': 'media_hub_asset_file',
            },
        ),
        # ParameterMapping
        migrations.CreateModel(
            name='ParameterMapping',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job_type', models.CharField(choices=[('illustration', 'Illustration'), ('comic_panel', 'Comic Panel'), ('book_cover', 'Book Cover'), ('audio_chapter', 'Audio Chapter'), ('audio_full', 'Full Audio'), ('video_trailer', 'Video Trailer')], db_index=True, max_length=20)),
                ('source_field', models.CharField(help_text="Source field path (e.g., 'scene.location', 'panel.description')", max_length=200)),
                ('target_field', models.CharField(help_text="Target field path (e.g., 'prompt.positive', 'sampler.steps')", max_length=200)),
                ('transform', models.CharField(choices=[('passthrough', 'Passthrough (as-is)'), ('template', 'Template (Jinja2)'), ('int', 'Integer'), ('float', 'Float'), ('bool', 'Boolean'), ('json', 'JSON')], default='passthrough', max_length=20)),
                ('template', models.TextField(blank=True, help_text='Jinja2 template for TEMPLATE transform')),
                ('default_value', models.TextField(blank=True, help_text='Default value if source is empty')),
                ('is_required', models.BooleanField(default=False)),
                ('order', models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Parameter Mapping',
                'verbose_name_plural': 'Parameter Mappings',
                'db_table': 'media_hub_parameter_mapping',
                'ordering': ['job_type', 'order'],
                'unique_together': {('job_type', 'source_field', 'target_field')},
            },
        ),
    ]
