"""
Migration for Correction System Models
======================================
Adds GenreStyleProfile and CorrectionSuggestion models,
plus correction_status and is_intentional fields to LektoratsFehler.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('writing_hub', '0022_lektorats_framework'),
    ]

    operations = [
        # Add correction fields to LektoratsFehler
        migrations.AddField(
            model_name='lektoratsfehler',
            name='correction_status',
            field=models.CharField(
                choices=[
                    ('new', 'Neu'),
                    ('reviewing', 'In Prüfung'),
                    ('corrected', 'Korrigiert'),
                    ('ignored', 'Ignoriert'),
                    ('accepted', 'Als OK markiert'),
                ],
                db_index=True,
                default='new',
                help_text='Status im Korrektur-Workflow',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='lektoratsfehler',
            name='is_intentional',
            field=models.BooleanField(
                default=False,
                help_text='Als bewusstes Stilmittel markiert',
            ),
        ),
        
        # Create GenreStyleProfile
        migrations.CreateModel(
            name='GenreStyleProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('genre', models.CharField(help_text="Genre-Schlüssel (z.B. 'fantasy', 'thriller', 'romance')", max_length=100, unique=True)),
                ('display_name', models.CharField(help_text='Anzeigename', max_length=200)),
                ('repetition_tolerance', models.CharField(
                    choices=[
                        ('strict', 'Streng - Minimale Wiederholungen'),
                        ('normal', 'Normal - Ausgewogen'),
                        ('relaxed', 'Locker - Stilmittel erlaubt'),
                    ],
                    default='normal',
                    help_text='Wie streng sollen Wiederholungen bewertet werden?',
                    max_length=20,
                )),
                ('acceptable_phrases', models.JSONField(blank=True, default=list, help_text='Phrasen die im Genre akzeptabel sind: ["sagte er", "fragte sie"]')),
                ('avoid_phrases', models.JSONField(blank=True, default=list, help_text='Phrasen die vermieden werden sollten')),
                ('synonym_preferences', models.JSONField(blank=True, default=dict, help_text='Genre-typische Synonyme: {"sagte": ["flüsterte", "rief"]}')),
                ('style_instructions', models.TextField(blank=True, help_text='Zusätzliche Anweisungen für Korrektur-Prompts')),
                ('preferred_sentence_length', models.CharField(
                    choices=[
                        ('short', 'Kurz (5-15 Wörter)'),
                        ('medium', 'Mittel (10-25 Wörter)'),
                        ('long', 'Lang (20+ Wörter)'),
                        ('varied', 'Variiert'),
                    ],
                    default='varied',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Genre-Stil-Profil',
                'verbose_name_plural': 'Genre-Stil-Profile',
                'db_table': 'writing_genre_style_profiles',
                'ordering': ['display_name'],
            },
        ),
        
        # Create CorrectionSuggestion
        migrations.CreateModel(
            name='CorrectionSuggestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('strategy', models.CharField(
                    choices=[
                        ('synonym', 'Synonym-Ersetzung'),
                        ('reformulate', 'Umformulierung'),
                        ('delete', 'Streichung'),
                        ('merge', 'Zusammenführung'),
                        ('vary', 'Struktur-Variation'),
                        ('keep', 'Beibehalten (Stilmittel)'),
                    ],
                    help_text='Angewandte Korrektur-Strategie',
                    max_length=20,
                )),
                ('original_text', models.TextField(help_text='Original-Text der korrigiert werden soll')),
                ('suggested_text', models.TextField(help_text='Vorgeschlagene Korrektur')),
                ('alternatives', models.JSONField(blank=True, default=list, help_text='Alternative Vorschläge')),
                ('confidence', models.FloatField(default=0.0, help_text='Konfidenz-Score (0-1)')),
                ('context_before', models.TextField(blank=True, help_text='Text vor der Stelle')),
                ('context_after', models.TextField(blank=True, help_text='Text nach der Stelle')),
                ('chapter_id', models.IntegerField(blank=True, null=True)),
                ('position_start', models.IntegerField(blank=True, null=True)),
                ('position_end', models.IntegerField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Ausstehend'),
                        ('accepted', 'Akzeptiert'),
                        ('rejected', 'Abgelehnt'),
                        ('modified', 'Modifiziert übernommen'),
                        ('auto', 'Automatisch angewendet'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('user_note', models.TextField(blank=True, help_text='Notiz des Users zur Entscheidung')),
                ('final_text', models.TextField(blank=True, help_text='Tatsächlich verwendeter Text (bei MODIFIED)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('fehler', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='corrections',
                    to='writing_hub.lektoratsfehler',
                )),
            ],
            options={
                'verbose_name': 'Korrektur-Vorschlag',
                'verbose_name_plural': 'Korrektur-Vorschläge',
                'db_table': 'writing_correction_suggestions',
                'ordering': ['-confidence', 'created_at'],
            },
        ),
    ]
