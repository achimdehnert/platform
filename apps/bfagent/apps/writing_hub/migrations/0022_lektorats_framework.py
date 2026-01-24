"""
Migration for Lektorats-Framework Models
=========================================
Creates tables for the systematic quality assurance system.
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('writing_hub', '0021_bookidea_characters_world'),
        ('bfagent', '0001_initial'),
    ]

    operations = [
        # LektoratsSession
        migrations.CreateModel(
            name='LektoratsSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('nicht_gestartet', 'Nicht gestartet'), ('in_bearbeitung', 'In Bearbeitung'), ('abgeschlossen', 'Abgeschlossen')], default='nicht_gestartet', max_length=20)),
                ('version_name', models.CharField(blank=True, help_text="z.B. 'Erster Durchgang', 'Finale Prüfung'", max_length=100)),
                ('modul_status', models.JSONField(default=dict, help_text="Status pro Modul: {'figuren': 'completed', 'zeitlinien': 'in_progress', ...}")),
                ('total_fehler', models.PositiveIntegerField(default=0)),
                ('fehler_kritisch', models.PositiveIntegerField(default=0)),
                ('fehler_schwer', models.PositiveIntegerField(default=0)),
                ('fehler_mittel', models.PositiveIntegerField(default=0)),
                ('fehler_leicht', models.PositiveIntegerField(default=0)),
                ('fehler_marginal', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lektorats_sessions', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lektorats_sessions', to='bfagent.bookprojects')),
            ],
            options={
                'verbose_name': 'Lektorats-Session',
                'verbose_name_plural': 'Lektorats-Sessions',
                'db_table': 'writing_lektorats_sessions',
                'ordering': ['-created_at'],
            },
        ),
        
        # LektoratsFehler
        migrations.CreateModel(
            name='LektoratsFehler',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('modul', models.CharField(choices=[('figuren', '👤 Figurenkonsistenz'), ('zeitlinien', '📅 Zeitlinien'), ('logik', '🧠 Handlungslogik'), ('stil', '✍️ Stilkonsistenz'), ('wiederholungen', '🔄 Wiederholungen')], help_text='Lektorats-Modul', max_length=20)),
                ('severity', models.CharField(choices=[('A', '🔴 Kritisch (zerstört Glaubwürdigkeit)'), ('B', '🟠 Schwer (verwirrt Leser)'), ('C', '🟡 Mittel (aufmerksamer Leser bemerkt es)'), ('D', '🟢 Leicht (stilistische Inkonsistenz)'), ('E', '⚪ Marginal (nur für Perfektionisten)')], default='C', help_text='Schweregrad A-E', max_length=1)),
                ('fehler_typ', models.CharField(blank=True, help_text="Spezifischer Fehlertyp (z.B. 'Namensvariation', 'Tempus-Wechsel')", max_length=100)),
                ('beschreibung', models.TextField(help_text='Kurze Beschreibung des Problems')),
                ('originaltext', models.TextField(blank=True, help_text='Zitat aus dem Manuskript')),
                ('korrekturvorschlag', models.TextField(blank=True, help_text='Korrigierter Text')),
                ('erklaerung', models.TextField(blank=True, help_text='Warum ist das ein Problem?')),
                ('querverweis_text', models.TextField(blank=True, help_text='Widersprüchlicher Text aus anderem Kapitel')),
                ('position_zeile', models.PositiveIntegerField(blank=True, help_text='Zeilennummer', null=True)),
                ('position_start', models.PositiveIntegerField(blank=True, help_text='Startposition im Text', null=True)),
                ('position_end', models.PositiveIntegerField(blank=True, help_text='Endposition im Text', null=True)),
                ('status', models.CharField(choices=[('offen', 'Offen'), ('in_bearbeitung', 'In Bearbeitung'), ('korrigiert', 'Korrigiert'), ('ignoriert', 'Ignoriert')], default='offen', max_length=20)),
                ('korrektur_notiz', models.TextField(blank=True, help_text='Notiz zur Korrektur')),
                ('ai_erkannt', models.BooleanField(default=False, help_text='Wurde dieser Fehler von AI erkannt?')),
                ('ai_konfidenz', models.FloatField(blank=True, help_text='AI-Konfidenz (0-1)', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('korrigiert_at', models.DateTimeField(blank=True, null=True)),
                ('chapter', models.ForeignKey(blank=True, help_text='Betroffenes Kapitel (optional bei projektweiten Fehlern)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='lektorats_fehler', to='bfagent.bookchapters')),
                ('querverweis_kapitel', models.ForeignKey(blank=True, help_text='Widersprechendes Kapitel', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lektorats_querverweise', to='bfagent.bookchapters')),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fehler', to='writing_hub.lektoratssession')),
            ],
            options={
                'verbose_name': 'Lektorats-Fehler',
                'verbose_name_plural': 'Lektorats-Fehler',
                'db_table': 'writing_lektorats_fehler',
                'ordering': ['severity', '-created_at'],
            },
        ),
        
        # FigurenRegister
        migrations.CreateModel(
            name='FigurenRegister',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Hauptname der Figur', max_length=200)),
                ('name_varianten', models.JSONField(default=list, help_text='Alle Namensvarianten: ["Max", "Maximilian", "Herr Müller"]')),
                ('rolle', models.CharField(choices=[('protagonist', '⭐ Protagonist'), ('antagonist', '👿 Antagonist'), ('hauptfigur', '👤 Hauptfigur'), ('nebenfigur', '👥 Nebenfigur'), ('erwaehnt', '💭 Erwähnt')], default='nebenfigur', max_length=20)),
                ('erste_erwaehnung_kapitel', models.PositiveIntegerField(blank=True, help_text='Kapitelnummer der ersten Erwähnung', null=True)),
                ('letzte_erwaehnung_kapitel', models.PositiveIntegerField(blank=True, help_text='Kapitelnummer der letzten Erwähnung', null=True)),
                ('alter', models.CharField(blank=True, max_length=50)),
                ('geschlecht', models.CharField(blank=True, max_length=50)),
                ('haarfarbe', models.CharField(blank=True, max_length=50)),
                ('augenfarbe', models.CharField(blank=True, max_length=50)),
                ('groesse', models.CharField(blank=True, max_length=50)),
                ('besondere_merkmale', models.TextField(blank=True)),
                ('herkunft', models.CharField(blank=True, max_length=200)),
                ('beruf', models.CharField(blank=True, max_length=200)),
                ('familie', models.TextField(blank=True)),
                ('charakterzuege', models.TextField(blank=True)),
                ('sprechweise', models.TextField(blank=True)),
                ('gewohnheiten', models.TextField(blank=True)),
                ('motivation', models.TextField(blank=True)),
                ('beziehungen', models.JSONField(default=list, help_text='Beziehungen: [{"figur": "Anna", "art": "Schwester"}, ...]')),
                ('kapitel_referenzen', models.JSONField(default=list, help_text='Referenzen: [{"kapitel": 5, "attribut": "Augenfarbe", "wert": "blau", "zitat": "..."}]')),
                ('ai_extrahiert', models.BooleanField(default=False, help_text='Wurde diese Figur von AI extrahiert?')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='figuren', to='writing_hub.lektoratssession')),
            ],
            options={
                'verbose_name': 'Figuren-Eintrag',
                'verbose_name_plural': 'Figuren-Register',
                'db_table': 'writing_lektorats_figuren',
                'ordering': ['rolle', 'name'],
                'unique_together': {('session', 'name')},
            },
        ),
        
        # ZeitlinienEintrag
        migrations.CreateModel(
            name='ZeitlinienEintrag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('zeit_typ', models.CharField(choices=[('explizit', '📅 Explizites Datum'), ('relativ', '⏱️ Relative Angabe'), ('implizit', '🌤️ Implizit (Jahreszeit, etc.)'), ('berechnet', '🔢 Berechnet')], default='explizit', max_length=20)),
                ('beschreibung', models.CharField(help_text='Die Zeitangabe aus dem Text', max_length=500)),
                ('tag_nummer', models.IntegerField(blank=True, help_text='Berechneter Tag relativ zu Tag 0', null=True)),
                ('datum', models.DateField(blank=True, help_text='Konkretes Datum (falls bekannt)', null=True)),
                ('originaltext', models.TextField(blank=True, help_text='Zitat aus dem Manuskript')),
                ('reihenfolge', models.PositiveIntegerField(default=0, help_text='Reihenfolge in der Timeline')),
                ('ai_extrahiert', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('chapter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='zeitlinien_eintraege', to='bfagent.bookchapters')),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='zeitlinien', to='writing_hub.lektoratssession')),
            ],
            options={
                'verbose_name': 'Zeitlinien-Eintrag',
                'verbose_name_plural': 'Zeitlinien-Einträge',
                'db_table': 'writing_lektorats_zeitlinien',
                'ordering': ['reihenfolge', 'tag_nummer'],
            },
        ),
        
        # StilProfil
        migrations.CreateModel(
            name='StilProfil',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('perspektive', models.CharField(choices=[('ich', 'Ich-Erzähler'), ('er_sie', 'Er/Sie-Erzähler'), ('auktorial', 'Auktorialer Erzähler'), ('wechselnd', 'Wechselnde Perspektive')], default='er_sie', max_length=20)),
                ('tempus', models.CharField(choices=[('praesens', 'Präsens'), ('praeteritum', 'Präteritum'), ('wechselnd', 'Wechselnd')], default='praeteritum', max_length=20)),
                ('durchschn_satzlaenge', models.PositiveIntegerField(blank=True, help_text='Durchschnittliche Wörter pro Satz', null=True)),
                ('fragmentsaetze_erlaubt', models.BooleanField(default=False, help_text='Sind Fragmentsätze erlaubt?')),
                ('grundton', models.CharField(blank=True, help_text="z.B. 'Ernst', 'Humorvoll', 'Ironisch'", max_length=100)),
                ('dialog_anteil', models.PositiveIntegerField(blank=True, help_text='Prozent Dialog', null=True)),
                ('metaphern_dichte', models.CharField(blank=True, help_text='Hoch/Mittel/Niedrig', max_length=20)),
                ('fachsprache', models.BooleanField(default=False)),
                ('umgangssprache', models.BooleanField(default=False)),
                ('besondere_stilmittel', models.TextField(blank=True)),
                ('ai_analysiert', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('session', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='stil_profil', to='writing_hub.lektoratssession')),
            ],
            options={
                'verbose_name': 'Stil-Profil',
                'verbose_name_plural': 'Stil-Profile',
                'db_table': 'writing_lektorats_stil_profil',
            },
        ),
        
        # WiederholungsAnalyse
        migrations.CreateModel(
            name='WiederholungsAnalyse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('typ', models.CharField(choices=[('wort', '📝 Wort-Wiederholung'), ('phrase', '💬 Phrasen-Wiederholung'), ('backstory', '📖 Backstory-Wiederholung'), ('struktur', '🏗️ Struktur-Wiederholung')], max_length=20)),
                ('text', models.TextField(help_text='Der wiederholte Text/Phrase')),
                ('anzahl', models.PositiveIntegerField(help_text='Anzahl der Vorkommen')),
                ('vorkommen', models.JSONField(default=list, help_text='Vorkommen: [{"kapitel": 5, "position": 123, "kontext": "..."}]')),
                ('bewertung', models.CharField(choices=[('intentional', '✅ Intentional (Leitmotiv)'), ('akzeptabel', '🔵 Akzeptabel'), ('pruefen', '🟡 Prüfen'), ('korrigieren', '🔴 Korrigieren')], default='pruefen', max_length=20)),
                ('bewertung_notiz', models.TextField(blank=True, help_text='Notiz zur Bewertung')),
                ('ai_erkannt', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wiederholungen', to='writing_hub.lektoratssession')),
            ],
            options={
                'verbose_name': 'Wiederholungs-Analyse',
                'verbose_name_plural': 'Wiederholungs-Analysen',
                'db_table': 'writing_lektorats_wiederholungen',
                'ordering': ['-anzahl'],
            },
        ),
    ]
