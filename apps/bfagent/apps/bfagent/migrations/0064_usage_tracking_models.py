# Generated migration for Usage Tracking Models

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bfagent', '0063_add_agentskills_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='DjangoGenerationError',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('error_type', models.CharField(choices=[
                    ('template', 'Template Error'),
                    ('view', 'View Error'),
                    ('url', 'URL Configuration Error'),
                    ('model', 'Model Error'),
                    ('form', 'Form Error'),
                    ('import', 'Import Error'),
                    ('syntax', 'Syntax Error'),
                    ('migration', 'Migration Error'),
                    ('admin', 'Admin Error'),
                    ('serializer', 'Serializer Error'),
                    ('handler', 'Handler Error'),
                    ('other', 'Other Error'),
                ], db_index=True, help_text='Type of Django error', max_length=20)),
                ('severity', models.CharField(choices=[
                    ('info', 'Info'),
                    ('warning', 'Warning'),
                    ('error', 'Error'),
                    ('critical', 'Critical'),
                ], default='error', max_length=20)),
                ('error_message', models.TextField(help_text='Full error message')),
                ('error_code', models.CharField(blank=True, db_index=True, help_text='Error code/rule (e.g., E001, W001)', max_length=50, null=True)),
                ('file_path', models.CharField(blank=True, help_text='File where error occurred', max_length=500, null=True)),
                ('line_number', models.IntegerField(blank=True, help_text='Line number of error', null=True)),
                ('function_name', models.CharField(blank=True, help_text='Function/class where error occurred', max_length=100, null=True)),
                ('code_snippet', models.TextField(blank=True, help_text='Relevant code snippet', null=True)),
                ('stack_trace', models.TextField(blank=True, help_text='Full stack trace', null=True)),
                ('source', models.CharField(choices=[
                    ('cascade', 'Cascade/AI Agent'),
                    ('user', 'User Manual'),
                    ('system', 'System/Automated'),
                    ('mcp', 'MCP Tool'),
                ], db_index=True, default='cascade', max_length=20)),
                ('session_id', models.CharField(blank=True, help_text='Cascade session ID', max_length=100, null=True)),
                ('resolved', models.BooleanField(default=False)),
                ('resolution', models.TextField(blank=True, help_text='How the error was resolved', null=True)),
                ('auto_fixable', models.BooleanField(default=False, help_text='Can this error be automatically fixed?')),
                ('fix_suggestion', models.TextField(blank=True, help_text='Suggested fix for this error', null=True)),
                ('error_hash', models.CharField(blank=True, db_index=True, help_text='Hash for deduplication/pattern matching', max_length=64, null=True)),
                ('occurrence_count', models.IntegerField(default=1, help_text='Number of times this error occurred')),
            ],
            options={
                'verbose_name': 'Django Generation Error',
                'verbose_name_plural': 'Django Generation Errors',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='ToolUsageLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('tool_name', models.CharField(db_index=True, help_text='Name of the tool/agent', max_length=100)),
                ('tool_version', models.CharField(blank=True, help_text='Tool version', max_length=20, null=True)),
                ('tool_category', models.CharField(blank=True, db_index=True, help_text='Tool category (e.g., code_quality, generation)', max_length=50, null=True)),
                ('caller_type', models.CharField(choices=[
                    ('user', 'User (Manual)'),
                    ('cascade', 'Cascade/AI'),
                    ('mcp', 'MCP Client'),
                    ('api', 'API Call'),
                    ('scheduled', 'Scheduled Task'),
                    ('system', 'System'),
                ], db_index=True, default='cascade', max_length=20)),
                ('caller_id', models.CharField(blank=True, db_index=True, help_text='User ID, session ID, or system identifier', max_length=100, null=True)),
                ('app_label', models.CharField(blank=True, db_index=True, help_text='Django app label if applicable', max_length=100, null=True)),
                ('request_url', models.CharField(blank=True, help_text='URL that triggered the tool call', max_length=500, null=True)),
                ('input_params', models.JSONField(blank=True, help_text='Input parameters (sanitized)', null=True)),
                ('execution_time_ms', models.FloatField(default=0.0, help_text='Execution time in milliseconds')),
                ('success', models.BooleanField(default=True)),
                ('result_summary', models.CharField(blank=True, help_text='Brief summary of result', max_length=500, null=True)),
                ('error_message', models.TextField(blank=True, help_text='Error message if failed', null=True)),
                ('session_id', models.CharField(blank=True, db_index=True, help_text='Session ID for grouping', max_length=100, null=True)),
            ],
            options={
                'verbose_name': 'Tool Usage Log',
                'verbose_name_plural': 'Tool Usage Logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='ErrorFixPattern',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Pattern name/identifier', max_length=100, unique=True)),
                ('description', models.TextField(help_text='Description of what this pattern fixes')),
                ('error_type', models.CharField(choices=[
                    ('template', 'Template Error'),
                    ('view', 'View Error'),
                    ('url', 'URL Configuration Error'),
                    ('model', 'Model Error'),
                    ('form', 'Form Error'),
                    ('import', 'Import Error'),
                    ('syntax', 'Syntax Error'),
                    ('migration', 'Migration Error'),
                    ('admin', 'Admin Error'),
                    ('serializer', 'Serializer Error'),
                    ('handler', 'Handler Error'),
                    ('other', 'Other Error'),
                ], db_index=True, max_length=20)),
                ('error_pattern', models.TextField(help_text='Regex pattern to match error message')),
                ('file_pattern', models.CharField(blank=True, help_text='Glob pattern for file matching', max_length=200, null=True)),
                ('fix_type', models.CharField(choices=[
                    ('replace', 'Find and Replace'),
                    ('insert', 'Insert Code'),
                    ('delete', 'Delete Code'),
                    ('refactor', 'Refactor'),
                    ('command', 'Run Command'),
                ], default='replace', max_length=20)),
                ('fix_template', models.TextField(help_text='Template for the fix (supports placeholders)')),
                ('times_applied', models.IntegerField(default=0)),
                ('success_rate', models.FloatField(default=100.0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Error Fix Pattern',
                'verbose_name_plural': 'Error Fix Patterns',
                'ordering': ['-times_applied'],
            },
        ),
        migrations.AddIndex(
            model_name='djangogenerationerror',
            index=models.Index(fields=['timestamp', 'error_type'], name='bfagent_dja_timesta_idx01'),
        ),
        migrations.AddIndex(
            model_name='djangogenerationerror',
            index=models.Index(fields=['error_type', 'error_code'], name='bfagent_dja_error_t_idx02'),
        ),
        migrations.AddIndex(
            model_name='djangogenerationerror',
            index=models.Index(fields=['source', 'timestamp'], name='bfagent_dja_source_idx03'),
        ),
        migrations.AddIndex(
            model_name='toolusagelog',
            index=models.Index(fields=['timestamp', 'tool_name'], name='bfagent_too_timesta_idx01'),
        ),
        migrations.AddIndex(
            model_name='toolusagelog',
            index=models.Index(fields=['caller_type', 'timestamp'], name='bfagent_too_caller__idx02'),
        ),
        migrations.AddIndex(
            model_name='toolusagelog',
            index=models.Index(fields=['tool_name', 'caller_type'], name='bfagent_too_tool_na_idx03'),
        ),
        migrations.AddIndex(
            model_name='toolusagelog',
            index=models.Index(fields=['app_label', 'timestamp'], name='bfagent_too_app_lab_idx04'),
        ),
    ]
