# Generated manually for publishing models
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('writing_hub', '0021_add_location_preview'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('bfagent', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PublishingMetadata',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('isbn', models.CharField(blank=True, help_text='ISBN-10 oder ISBN-13', max_length=17, validators=[django.core.validators.RegexValidator(message='Ungültige ISBN (10 oder 13 Ziffern)', regex='^(?:\\d{10}|\\d{13}|978-\\d-\\d{2}-\\d{6}-\\d)$')])),
                ('asin', models.CharField(blank=True, help_text='Amazon Standard Identification Number', max_length=10)),
                ('publisher_name', models.CharField(blank=True, default='Selbstverlag', help_text='Verlagsname', max_length=200)),
                ('imprint', models.CharField(blank=True, help_text='Impressum/Imprint', max_length=200)),
                ('copyright_year', models.PositiveIntegerField(blank=True, help_text='Copyright-Jahr', null=True)),
                ('copyright_holder', models.CharField(blank=True, help_text='Copyright-Inhaber (Name des Autors)', max_length=200)),
                ('all_rights_reserved', models.BooleanField(default=True, help_text='Alle Rechte vorbehalten')),
                ('language', models.CharField(default='de', help_text="Sprache (ISO 639-1, z.B. 'de', 'en')", max_length=5)),
                ('primary_bisac', models.CharField(blank=True, help_text="Primäre BISAC-Kategorie (z.B. 'FIC009000')", max_length=100)),
                ('secondary_bisac', models.CharField(blank=True, help_text='Sekundäre BISAC-Kategorie', max_length=100)),
                ('keywords', models.TextField(blank=True, help_text='Komma-getrennte Keywords für Suchmaschinen (max. 7)')),
                ('content_rating', models.CharField(choices=[('general', '👨\u200d👩\u200d👧 Allgemein (ab 0)'), ('teen', '🧒 Jugendliche (ab 12)'), ('young_adult', '👤 Junge Erwachsene (ab 16)'), ('adult', '🔞 Erwachsene (ab 18)')], default='general', max_length=20)),
                ('first_published', models.DateField(blank=True, help_text='Erstveröffentlichung', null=True)),
                ('this_edition', models.DateField(blank=True, help_text='Diese Ausgabe', null=True)),
                ('status', models.CharField(choices=[('draft', '📝 Entwurf'), ('ready', '✅ Bereit zur Publikation'), ('published', '📚 Veröffentlicht'), ('archived', '📦 Archiviert')], default='draft', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='publishing_metadata', to='bfagent.bookprojects')),
            ],
            options={
                'verbose_name': 'Publishing-Metadaten',
                'verbose_name_plural': 'Publishing-Metadaten',
                'db_table': 'writing_publishing_metadata',
            },
        ),
        migrations.CreateModel(
            name='BookCover',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cover_type', models.CharField(choices=[('ebook', '📱 E-Book Cover'), ('print', '📖 Print Cover'), ('audiobook', '🎧 Hörbuch Cover'), ('social', '📣 Social Media')], default='ebook', max_length=20)),
                ('image', models.ImageField(help_text='Cover-Bild (min. 1600x2560 für E-Book)', upload_to='book_covers/')),
                ('prompt_used', models.TextField(blank=True, help_text='KI-Prompt für Generierung')),
                ('is_ai_generated', models.BooleanField(default=False)),
                ('width', models.PositiveIntegerField(blank=True, null=True)),
                ('height', models.PositiveIntegerField(blank=True, null=True)),
                ('is_primary', models.BooleanField(default=False, help_text='Haupt-Cover für diese Art')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='covers', to='bfagent.bookprojects')),
            ],
            options={
                'verbose_name': 'Buchcover',
                'verbose_name_plural': 'Buchcover',
                'db_table': 'writing_book_covers',
                'ordering': ['-is_primary', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='FrontMatter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page_type', models.CharField(choices=[('half_title', '📄 Schmutztitel'), ('title', '📖 Titelseite'), ('copyright', '©️ Impressum'), ('dedication', '💝 Widmung'), ('epigraph', '✨ Motto/Zitat'), ('toc', '📑 Inhaltsverzeichnis'), ('foreword', '📝 Vorwort'), ('preface', '📋 Einleitung'), ('acknowledgments', '🙏 Danksagung'), ('prologue', '🎬 Prolog')], max_length=20)),
                ('title', models.CharField(blank=True, help_text='Seitentitel (optional)', max_length=200)),
                ('content', models.TextField(blank=True, help_text='Seiteninhalt (Markdown)')),
                ('auto_generate', models.BooleanField(default=True, help_text='Automatisch aus Metadaten generieren')),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='front_matter', to='bfagent.bookprojects')),
            ],
            options={
                'verbose_name': 'Frontmatter',
                'verbose_name_plural': 'Frontmatter',
                'db_table': 'writing_front_matter',
                'ordering': ['sort_order'],
                'unique_together': {('project', 'page_type')},
            },
        ),
        migrations.CreateModel(
            name='BackMatter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page_type', models.CharField(choices=[('epilogue', '🎭 Epilog'), ('afterword', '📝 Nachwort'), ('appendix', '📎 Anhang'), ('glossary', '📖 Glossar'), ('bibliography', '📚 Literaturverzeichnis'), ('index', '🔍 Index'), ('about_author', '👤 Über den Autor'), ('also_by', '📚 Weitere Bücher'), ('acknowledgments', '🙏 Danksagung'), ('colophon', '🖨️ Kolophon')], max_length=20)),
                ('title', models.CharField(blank=True, help_text='Seitentitel (optional)', max_length=200)),
                ('content', models.TextField(blank=True, help_text='Seiteninhalt (Markdown)')),
                ('auto_generate', models.BooleanField(default=False, help_text='Automatisch generieren')),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='back_matter', to='bfagent.bookprojects')),
            ],
            options={
                'verbose_name': 'Backmatter',
                'verbose_name_plural': 'Backmatter',
                'db_table': 'writing_back_matter',
                'ordering': ['sort_order'],
                'unique_together': {('project', 'page_type')},
            },
        ),
        migrations.CreateModel(
            name='AuthorProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pen_name', models.CharField(blank=True, help_text='Pseudonym / Künstlername', max_length=200)),
                ('bio_short', models.TextField(blank=True, help_text='Kurze Bio (1-2 Sätze)')),
                ('bio_long', models.TextField(blank=True, help_text='Ausführliche Bio')),
                ('photo', models.ImageField(blank=True, null=True, upload_to='author_photos/')),
                ('website', models.URLField(blank=True)),
                ('email_public', models.EmailField(blank=True, max_length=254)),
                ('twitter', models.CharField(blank=True, max_length=50)),
                ('instagram', models.CharField(blank=True, max_length=50)),
                ('facebook', models.CharField(blank=True, max_length=100)),
                ('goodreads', models.URLField(blank=True)),
                ('amazon_author_page', models.URLField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='author_profile', to='auth.user')),
            ],
            options={
                'verbose_name': 'Autorenprofil',
                'verbose_name_plural': 'Autorenprofile',
                'db_table': 'writing_author_profiles',
            },
        ),
    ]
