"""
Migration: Content Type Framework System
Creates tables for DB-driven content types and structure frameworks
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('writing_hub', '0002_outline_versioning'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(help_text="e.g. 'novel', 'essay', 'scientific'", unique=True)),
                ('name', models.CharField(help_text='Display name', max_length=100)),
                ('name_de', models.CharField(blank=True, help_text='German name', max_length=100)),
                ('description', models.TextField(blank=True)),
                ('icon', models.CharField(default='bi-file-text', help_text='Bootstrap icon class', max_length=50)),
                ('section_label', models.CharField(default='Kapitel', help_text='Label for sections: Kapitel, Abschnitt', max_length=50)),
                ('section_label_plural', models.CharField(default='Kapitel', help_text='Plural label', max_length=50)),
                ('default_word_count', models.PositiveIntegerField(default=50000)),
                ('default_section_count', models.PositiveIntegerField(default=15)),
                ('has_characters', models.BooleanField(default=True, help_text='Enable character management')),
                ('has_world_building', models.BooleanField(default=True, help_text='Enable world building')),
                ('has_citations', models.BooleanField(default=False, help_text='Enable citation management')),
                ('has_abstract', models.BooleanField(default=False, help_text='Enable abstract/summary')),
                ('llm_system_prompt', models.TextField(blank=True, help_text='System prompt for LLM calls')),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Content Type',
                'verbose_name_plural': 'Content Types',
                'db_table': 'writing_content_types',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='StructureFramework',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(help_text="e.g. 'save_the_cat', 'imrad'")),
                ('name', models.CharField(max_length=100)),
                ('name_de', models.CharField(blank=True, max_length=100)),
                ('description', models.TextField(blank=True)),
                ('icon', models.CharField(default='bi-diagram-3', max_length=50)),
                ('default_section_count', models.PositiveIntegerField(default=15)),
                ('llm_system_prompt', models.TextField(blank=True, help_text='System prompt for outline generation')),
                ('llm_user_template', models.TextField(blank=True, help_text='User prompt template with {placeholders}')),
                ('is_default', models.BooleanField(default=False, help_text='Default framework for content type')),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='frameworks', to='writing_hub.contenttype')),
            ],
            options={
                'verbose_name': 'Structure Framework',
                'verbose_name_plural': 'Structure Frameworks',
                'db_table': 'writing_structure_frameworks',
                'ordering': ['content_type', 'sort_order', 'name'],
                'unique_together': {('content_type', 'slug')},
            },
        ),
        migrations.CreateModel(
            name='FrameworkBeat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Beat name in English', max_length=100)),
                ('name_de', models.CharField(blank=True, help_text='German name', max_length=100)),
                ('description', models.TextField(blank=True, help_text='What should happen in this beat')),
                ('description_de', models.TextField(blank=True, help_text='German description')),
                ('position', models.CharField(default='0%', help_text="Position in story: '0-10%', '50%'", max_length=20)),
                ('part', models.IntegerField(choices=[(1, 'Teil 1 / Einleitung'), (2, 'Teil 2 / Hauptteil'), (3, 'Teil 3 / Schluss')], default=1, help_text='Which act/part')),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('llm_prompt_template', models.TextField(blank=True, help_text='Prompt template for generating this beat')),
                ('suggested_word_percentage', models.FloatField(default=0.0, help_text='Percentage of total words')),
                ('is_required', models.BooleanField(default=True, help_text='Required beat or optional')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('framework', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='beats', to='writing_hub.structureframework')),
            ],
            options={
                'verbose_name': 'Framework Beat',
                'verbose_name_plural': 'Framework Beats',
                'db_table': 'writing_framework_beats',
                'ordering': ['framework', 'sort_order'],
            },
        ),
    ]
