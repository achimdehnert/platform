# Generated manually for task delegation system
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bfagent', '0053_add_documentation_system'),
    ]

    operations = [
        migrations.CreateModel(
            name='DelegatedTask',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('task_type', models.CharField(
                    choices=[
                        ('coding', 'Coding'),
                        ('writing', 'Writing'),
                        ('analysis', 'Analysis'),
                        ('translation', 'Translation'),
                        ('illustration', 'Illustration'),
                        ('other', 'Other')
                    ],
                    default='coding',
                    max_length=20
                )),
                ('complexity', models.CharField(
                    choices=[
                        ('auto', 'Auto (Heuristik)'),
                        ('low', 'Low - Einfach'),
                        ('medium', 'Medium - Moderat'),
                        ('high', 'High - Komplex')
                    ],
                    default='auto',
                    max_length=20
                )),
                ('complexity_estimated', models.CharField(blank=True, help_text='Auto-estimated complexity (if complexity=auto)', max_length=20)),
                ('routing_reason', models.CharField(blank=True, max_length=200)),
                ('requires_cascade', models.BooleanField(default=False, help_text='True if task was too complex for local LLMs')),
                ('prompt', models.TextField(help_text='The prompt sent to LLM')),
                ('system_prompt', models.TextField(blank=True)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('queued', 'Queued'),
                        ('running', 'Running'),
                        ('completed', 'Completed'),
                        ('failed', 'Failed'),
                        ('cancelled', 'Cancelled')
                    ],
                    default='pending',
                    max_length=20
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('result_text', models.TextField(blank=True)),
                ('result_data', models.JSONField(blank=True, default=dict)),
                ('error_message', models.TextField(blank=True)),
                ('tokens_used', models.IntegerField(default=0)),
                ('latency_ms', models.IntegerField(default=0)),
                ('estimated_cost', models.DecimalField(decimal_places=6, default=0, max_digits=10)),
                ('celery_task_id', models.CharField(blank=True, max_length=255)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='delegated_tasks_created', to=settings.AUTH_USER_MODEL)),
                ('llm_selected', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='delegated_tasks', to='bfagent.llms')),
                ('requirement', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='delegated_tasks', to='bfagent.testrequirement')),
            ],
            options={
                'db_table': 'bfagent_delegated_tasks',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TaskExecutionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('event', models.CharField(max_length=50)),
                ('details', models.JSONField(default=dict)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='execution_logs', to='bfagent.delegatedtask')),
            ],
            options={
                'db_table': 'bfagent_task_execution_logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='delegatedtask',
            index=models.Index(fields=['status', 'created_at'], name='bfagent_del_status_idx'),
        ),
        migrations.AddIndex(
            model_name='delegatedtask',
            index=models.Index(fields=['task_type', 'complexity'], name='bfagent_del_type_cmplx_idx'),
        ),
        migrations.AddIndex(
            model_name='delegatedtask',
            index=models.Index(fields=['requirement'], name='bfagent_del_req_idx'),
        ),
        migrations.CreateModel(
            name='TaskFeedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('result_quality', models.CharField(
                    choices=[
                        ('excellent', '⭐⭐⭐ Excellent'),
                        ('good', '⭐⭐ Good'),
                        ('acceptable', '⭐ Acceptable'),
                        ('poor', '👎 Poor'),
                        ('wrong_routing', '❌ Wrong Routing')
                    ],
                    help_text='Quality of the LLM result',
                    max_length=20
                )),
                ('routing_correct', models.BooleanField(default=True, help_text='Was the complexity estimation correct?')),
                ('should_have_been', models.CharField(
                    choices=[
                        ('low', 'Should have been LOW'),
                        ('medium', 'Should have been MEDIUM'),
                        ('high', 'Should have been HIGH (Cascade)'),
                        ('correct', 'Routing was correct')
                    ],
                    default='correct',
                    max_length=20
                )),
                ('comment', models.TextField(blank=True, help_text='Optional feedback comment')),
                ('result_used', models.BooleanField(default=True, help_text='Was the result actually used?')),
                ('manual_correction_needed', models.BooleanField(default=False, help_text='Did Cascade need to fix the result?')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('task', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='feedback', to='bfagent.delegatedtask')),
            ],
            options={
                'db_table': 'bfagent_task_feedback',
                'verbose_name': 'Task Feedback',
                'verbose_name_plural': 'Task Feedbacks',
            },
        ),
        migrations.CreateModel(
            name='RoutingAnalytics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(unique=True)),
                ('total_tasks', models.IntegerField(default=0)),
                ('low_complexity_tasks', models.IntegerField(default=0)),
                ('medium_complexity_tasks', models.IntegerField(default=0)),
                ('high_complexity_tasks', models.IntegerField(default=0)),
                ('cascade_required_tasks', models.IntegerField(default=0)),
                ('successful_delegations', models.IntegerField(default=0)),
                ('failed_delegations', models.IntegerField(default=0)),
                ('excellent_ratings', models.IntegerField(default=0)),
                ('good_ratings', models.IntegerField(default=0)),
                ('acceptable_ratings', models.IntegerField(default=0)),
                ('poor_ratings', models.IntegerField(default=0)),
                ('wrong_routing_count', models.IntegerField(default=0)),
                ('estimated_tokens_saved', models.IntegerField(default=0)),
                ('estimated_cost_saved_usd', models.DecimalField(decimal_places=4, default=0, max_digits=10)),
                ('avg_latency_ms', models.IntegerField(default=0)),
                ('total_tokens_used', models.IntegerField(default=0)),
            ],
            options={
                'db_table': 'bfagent_routing_analytics',
                'ordering': ['-date'],
            },
        ),
    ]
