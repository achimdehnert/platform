# Generated manually on 2026-01-06
# Migration for StyleIssue and StyleIssueType models

import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('writing_hub', '0016_add_llm_to_stylelabsession'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StyleIssueType',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(db_index=True, max_length=50, unique=True)),
                ('name_de', models.CharField(max_length=100)),
                ('name_en', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('severity', models.IntegerField(
                    default=2,
                    help_text='1=info, 2=warning, 3=error, 4=blocker',
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(4)
                    ]
                )),
                ('auto_fixable', models.BooleanField(default=False, help_text='Kann automatisch korrigiert werden')),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Style Issue Type',
                'verbose_name_plural': 'Style Issue Types',
                'db_table': 'writing_style_issue_types',
                'ordering': ['sort_order', 'severity', 'code'],
            },
        ),
        migrations.CreateModel(
            name='StyleIssue',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('text_excerpt', models.TextField(help_text='Original-Text mit dem Problem')),
                ('line_number', models.IntegerField(blank=True, help_text='Zeile im Kapiteltext', null=True)),
                ('char_position', models.IntegerField(blank=True, help_text='Zeichenposition im Text', null=True)),
                ('suggestion', models.TextField(blank=True, help_text='Vorgeschlagene Korrektur')),
                ('explanation', models.TextField(blank=True, help_text='Erklärung warum es ein Problem ist')),
                ('is_fixed', models.BooleanField(default=False)),
                ('fixed_at', models.DateTimeField(blank=True, null=True)),
                ('is_ignored', models.BooleanField(default=False, help_text='Bewusst ignoriert (false positive)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('fixed_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='fixed_style_issues',
                    to=settings.AUTH_USER_MODEL
                )),
                ('issue_type', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='issues',
                    to='writing_hub.styleissuetype'
                )),
                ('quality_score', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='style_issues',
                    to='writing_hub.chapterqualityscore'
                )),
            ],
            options={
                'verbose_name': 'Style Issue',
                'verbose_name_plural': 'Style Issues',
                'db_table': 'writing_style_issues',
                'ordering': ['-issue_type__severity', 'line_number'],
            },
        ),
    ]
