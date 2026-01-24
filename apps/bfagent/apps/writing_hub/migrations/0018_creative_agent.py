# Generated migration for Creative Agent System

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('writing_hub', '0017_style_issues'),
    ]

    operations = [
        migrations.CreateModel(
            name='CreativeSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text="Session-Name, z.B. 'Thriller-Ideen Januar 2026'", max_length=200)),
                ('initial_input', models.TextField(blank=True, help_text='Initiale Idee/Inspiration des Users')),
                ('preferred_genres', models.JSONField(default=list, help_text="Bevorzugte Genres, z.B. ['Thriller', 'SciFi']")),
                ('constraints', models.JSONField(default=dict, help_text='Einschränkungen: target_length, target_audience, etc.')),
                ('current_phase', models.CharField(choices=[('brainstorm', 'Brainstorming'), ('refining', 'Idee verfeinern'), ('premise', 'Premise erstellen'), ('completed', 'Abgeschlossen'), ('cancelled', 'Abgebrochen')], default='brainstorm', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='creative_sessions', to=settings.AUTH_USER_MODEL)),
                ('style_dna', models.ForeignKey(blank=True, help_text='Optional: Style DNA für passende Ideen', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creative_sessions', to='writing_hub.authorstyledna')),
            ],
            options={
                'verbose_name': 'Creative Session',
                'verbose_name_plural': 'Creative Sessions',
                'db_table': 'writing_creative_sessions',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BookIdea',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title_sketch', models.CharField(help_text='Arbeitstitel der Idee', max_length=200)),
                ('hook', models.TextField(help_text="Der 'Hook' - was macht die Idee spannend? (1-2 Sätze)")),
                ('genre', models.CharField(blank=True, help_text='Haupt-Genre', max_length=100)),
                ('setting_sketch', models.CharField(blank=True, help_text='Setting in einem Satz', max_length=300)),
                ('protagonist_sketch', models.CharField(blank=True, help_text='Protagonist in einem Satz', max_length=300)),
                ('conflict_sketch', models.CharField(blank=True, help_text='Zentraler Konflikt in einem Satz', max_length=300)),
                ('has_full_premise', models.BooleanField(default=False)),
                ('full_premise', models.TextField(blank=True, help_text='Ausführliche Premise (2-3 Absätze)')),
                ('themes', models.JSONField(default=list, help_text='Identifizierte Themen')),
                ('unique_selling_points', models.JSONField(default=list, help_text='Was macht diese Geschichte einzigartig?')),
                ('user_rating', models.CharField(choices=[('unrated', 'Nicht bewertet'), ('love', '❤️ Liebe es'), ('like', '👍 Gefällt mir'), ('maybe', '🤔 Vielleicht'), ('dislike', '👎 Nicht so')], default='unrated', max_length=20)),
                ('user_notes', models.TextField(blank=True, help_text='Notizen/Feedback des Users')),
                ('refinement_count', models.PositiveIntegerField(default=0)),
                ('refinement_history', models.JSONField(default=list, help_text='Historie der Verfeinerungen')),
                ('generation_order', models.PositiveIntegerField(default=0, help_text='Reihenfolge der Generierung')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ideas', to='writing_hub.creativesession')),
            ],
            options={
                'verbose_name': 'Book Idea',
                'verbose_name_plural': 'Book Ideas',
                'db_table': 'writing_book_ideas',
                'ordering': ['session', 'generation_order'],
            },
        ),
        migrations.CreateModel(
            name='CreativeMessage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('sender', models.CharField(choices=[('user', 'User'), ('agent', 'Kreativagent'), ('system', 'System')], max_length=20)),
                ('content', models.TextField(help_text='Nachrichteninhalt')),
                ('message_type', models.CharField(choices=[('text', 'Text'), ('ideas', 'Ideen-Liste'), ('premise', 'Premise'), ('question', 'Rückfrage'), ('action', 'Aktion')], default='text', max_length=20)),
                ('metadata', models.JSONField(default=dict, help_text='Zusätzliche Daten (LLM usage, etc.)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='writing_hub.creativesession')),
                ('linked_ideas', models.ManyToManyField(blank=True, help_text='Mit dieser Nachricht verknüpfte Ideen', related_name='messages', to='writing_hub.bookidea')),
            ],
            options={
                'verbose_name': 'Creative Message',
                'verbose_name_plural': 'Creative Messages',
                'db_table': 'writing_creative_messages',
                'ordering': ['session', 'created_at'],
            },
        ),
        # Add FK from CreativeSession to BookIdea (selected_idea) and BookProject (created_project)
        migrations.AddField(
            model_name='creativesession',
            name='selected_idea',
            field=models.ForeignKey(blank=True, help_text='Die ausgewählte Idee für Projekt-Erstellung', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='selected_in_sessions', to='writing_hub.bookidea'),
        ),
        migrations.AddField(
            model_name='creativesession',
            name='created_project',
            field=models.ForeignKey(blank=True, help_text='Das aus dieser Session erstellte Projekt', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creative_sessions', to='bfagent.bookprojects'),
        ),
    ]
