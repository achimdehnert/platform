"""
Lektorats-Framework Models
==========================

Systematische Qualitätssicherung für Romanmanuskripte.
Basierend auf dem Lektorats-Pass Framework mit 5 Kernmodulen:
1. Figurenkonsistenz
2. Zeitlinien-Analyse
3. Handlungslogik
4. Stilkonsistenz
5. Wiederholungen & Redundanzen
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


# =============================================================================
# Lektorats-Session & Konfiguration
# =============================================================================

class LektoratsSession(models.Model):
    """
    Eine Lektorats-Session für ein Projekt.
    Verfolgt den Fortschritt über alle 5 Module.
    """
    
    class Status(models.TextChoices):
        NICHT_GESTARTET = 'nicht_gestartet', 'Nicht gestartet'
        IN_BEARBEITUNG = 'in_bearbeitung', 'In Bearbeitung'
        ABGESCHLOSSEN = 'abgeschlossen', 'Abgeschlossen'
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='lektorats_sessions'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lektorats_sessions'
    )
    
    # Session Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NICHT_GESTARTET
    )
    version_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="z.B. 'Erster Durchgang', 'Finale Prüfung'"
    )
    
    # Modul-Status (JSON für Flexibilität)
    modul_status = models.JSONField(
        default=dict,
        help_text="Status pro Modul: {'figuren': 'completed', 'zeitlinien': 'in_progress', ...}"
    )
    
    # Statistiken
    total_fehler = models.PositiveIntegerField(default=0)
    fehler_kritisch = models.PositiveIntegerField(default=0)
    fehler_schwer = models.PositiveIntegerField(default=0)
    fehler_mittel = models.PositiveIntegerField(default=0)
    fehler_leicht = models.PositiveIntegerField(default=0)
    fehler_marginal = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'writing_lektorats_sessions'
        ordering = ['-created_at']
        verbose_name = 'Lektorats-Session'
        verbose_name_plural = 'Lektorats-Sessions'
    
    def __str__(self):
        return f"{self.project.title} - {self.version_name or 'Session'} ({self.get_status_display()})"
    
    def update_statistics(self):
        """Aktualisiert Fehler-Statistiken basierend auf LektoratsFehler"""
        fehler = self.fehler.all()
        self.total_fehler = fehler.count()
        self.fehler_kritisch = fehler.filter(severity='A').count()
        self.fehler_schwer = fehler.filter(severity='B').count()
        self.fehler_mittel = fehler.filter(severity='C').count()
        self.fehler_leicht = fehler.filter(severity='D').count()
        self.fehler_marginal = fehler.filter(severity='E').count()
        self.save()
    
    def get_modul_progress(self):
        """Gibt Fortschritt pro Modul zurück"""
        module = ['figuren', 'zeitlinien', 'logik', 'stil', 'wiederholungen']
        progress = {}
        for modul in module:
            status = self.modul_status.get(modul, 'pending')
            progress[modul] = {
                'status': status,
                'fehler_count': self.fehler.filter(modul=modul).count()
            }
        return progress


# =============================================================================
# Lektorats-Fehler (Zentrale Fehler-Datenbank)
# =============================================================================

class LektoratsFehler(models.Model):
    """
    Ein gefundener Fehler/Inkonsistenz im Manuskript.
    Kategorisiert nach Modul und Schweregrad.
    """
    
    class Modul(models.TextChoices):
        FIGUREN = 'figuren', '👤 Figurenkonsistenz'
        ZEITLINIEN = 'zeitlinien', '📅 Zeitlinien'
        LOGIK = 'logik', '🧠 Handlungslogik'
        STIL = 'stil', '✍️ Stilkonsistenz'
        WIEDERHOLUNGEN = 'wiederholungen', '🔄 Wiederholungen'
    
    class Severity(models.TextChoices):
        A = 'A', '🔴 Kritisch (zerstört Glaubwürdigkeit)'
        B = 'B', '🟠 Schwer (verwirrt Leser)'
        C = 'C', '🟡 Mittel (aufmerksamer Leser bemerkt es)'
        D = 'D', '🟢 Leicht (stilistische Inkonsistenz)'
        E = 'E', '⚪ Marginal (nur für Perfektionisten)'
    
    class Status(models.TextChoices):
        OFFEN = 'offen', 'Offen'
        IN_BEARBEITUNG = 'in_bearbeitung', 'In Bearbeitung'
        KORRIGIERT = 'korrigiert', 'Korrigiert'
        IGNORIERT = 'ignoriert', 'Ignoriert'
    
    # Relations
    session = models.ForeignKey(
        LektoratsSession,
        on_delete=models.CASCADE,
        related_name='fehler'
    )
    chapter = models.ForeignKey(
        'bfagent.BookChapters',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='lektorats_fehler',
        help_text="Betroffenes Kapitel (optional bei projektweiten Fehlern)"
    )
    
    # Kategorisierung
    modul = models.CharField(
        max_length=20,
        choices=Modul.choices,
        help_text="Lektorats-Modul"
    )
    severity = models.CharField(
        max_length=1,
        choices=Severity.choices,
        default='C',
        help_text="Schweregrad A-E"
    )
    fehler_typ = models.CharField(
        max_length=100,
        blank=True,
        help_text="Spezifischer Fehlertyp (z.B. 'Namensvariation', 'Tempus-Wechsel')"
    )
    
    # Details
    beschreibung = models.TextField(
        help_text="Kurze Beschreibung des Problems"
    )
    originaltext = models.TextField(
        blank=True,
        help_text="Zitat aus dem Manuskript"
    )
    korrekturvorschlag = models.TextField(
        blank=True,
        help_text="Korrigierter Text"
    )
    erklaerung = models.TextField(
        blank=True,
        help_text="Warum ist das ein Problem?"
    )
    
    # Querverweis
    querverweis_kapitel = models.ForeignKey(
        'bfagent.BookChapters',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lektorats_querverweise',
        help_text="Widersprechendes Kapitel"
    )
    querverweis_text = models.TextField(
        blank=True,
        help_text="Widersprüchlicher Text aus anderem Kapitel"
    )
    
    # Position im Text
    position_zeile = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Zeilennummer"
    )
    position_start = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Startposition im Text"
    )
    position_end = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Endposition im Text"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OFFEN
    )
    korrektur_notiz = models.TextField(
        blank=True,
        help_text="Notiz zur Korrektur"
    )
    
    # AI-Erkennung
    ai_erkannt = models.BooleanField(
        default=False,
        help_text="Wurde dieser Fehler von AI erkannt?"
    )
    ai_konfidenz = models.FloatField(
        null=True,
        blank=True,
        help_text="AI-Konfidenz (0-1)"
    )
    
    # Korrektur-Workflow (NEU für Correction System)
    correction_status = models.CharField(
        max_length=20,
        choices=[
            ('new', 'Neu'),
            ('reviewing', 'In Prüfung'),
            ('corrected', 'Korrigiert'),
            ('ignored', 'Ignoriert'),
            ('accepted', 'Als OK markiert'),
        ],
        default='new',
        db_index=True,
        help_text="Status im Korrektur-Workflow"
    )
    is_intentional = models.BooleanField(
        default=False,
        help_text="Als bewusstes Stilmittel markiert"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    korrigiert_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'writing_lektorats_fehler'
        ordering = ['severity', '-created_at']
        verbose_name = 'Lektorats-Fehler'
        verbose_name_plural = 'Lektorats-Fehler'
    
    def __str__(self):
        return f"[{self.severity}] {self.get_modul_display()}: {self.beschreibung[:50]}..."


# =============================================================================
# Figuren-Register (Modul 1)
# =============================================================================

class FigurenRegister(models.Model):
    """
    Zentrale Figuren-Datenbank für ein Projekt.
    Speichert alle Attribute einer Figur mit Kapitel-Referenzen.
    """
    
    class Rolle(models.TextChoices):
        PROTAGONIST = 'protagonist', '⭐ Protagonist'
        ANTAGONIST = 'antagonist', '👿 Antagonist'
        HAUPTFIGUR = 'hauptfigur', '👤 Hauptfigur'
        NEBENFIGUR = 'nebenfigur', '👥 Nebenfigur'
        ERWAEHNT = 'erwaehnt', '💭 Erwähnt'
    
    session = models.ForeignKey(
        LektoratsSession,
        on_delete=models.CASCADE,
        related_name='figuren'
    )
    
    # Identifikation
    name = models.CharField(
        max_length=200,
        help_text="Hauptname der Figur"
    )
    name_varianten = models.JSONField(
        default=list,
        help_text='Alle Namensvarianten: ["Max", "Maximilian", "Herr Müller"]'
    )
    rolle = models.CharField(
        max_length=20,
        choices=Rolle.choices,
        default=Rolle.NEBENFIGUR
    )
    
    # Erste/Letzte Erwähnung
    erste_erwaehnung_kapitel = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Kapitelnummer der ersten Erwähnung"
    )
    letzte_erwaehnung_kapitel = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Kapitelnummer der letzten Erwähnung"
    )
    
    # Physische Merkmale
    alter = models.CharField(max_length=50, blank=True)
    geschlecht = models.CharField(max_length=50, blank=True)
    haarfarbe = models.CharField(max_length=50, blank=True)
    augenfarbe = models.CharField(max_length=50, blank=True)
    groesse = models.CharField(max_length=50, blank=True)
    besondere_merkmale = models.TextField(blank=True)
    
    # Hintergrund
    herkunft = models.CharField(max_length=200, blank=True)
    beruf = models.CharField(max_length=200, blank=True)
    familie = models.TextField(blank=True)
    
    # Persönlichkeit
    charakterzuege = models.TextField(blank=True)
    sprechweise = models.TextField(blank=True)
    gewohnheiten = models.TextField(blank=True)
    motivation = models.TextField(blank=True)
    
    # Beziehungen (JSON für Flexibilität)
    beziehungen = models.JSONField(
        default=list,
        help_text='Beziehungen: [{"figur": "Anna", "art": "Schwester"}, ...]'
    )
    
    # Kapitel-Referenzen (alle Erwähnungen mit Attributen)
    kapitel_referenzen = models.JSONField(
        default=list,
        help_text='Referenzen: [{"kapitel": 5, "attribut": "Augenfarbe", "wert": "blau", "zitat": "..."}]'
    )
    
    # AI-extrahiert
    ai_extrahiert = models.BooleanField(
        default=False,
        help_text="Wurde diese Figur von AI extrahiert?"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_lektorats_figuren'
        ordering = ['rolle', 'name']
        verbose_name = 'Figuren-Eintrag'
        verbose_name_plural = 'Figuren-Register'
        unique_together = ['session', 'name']
    
    def __str__(self):
        return f"{self.get_rolle_display()}: {self.name}"
    
    def get_inkonsistenzen(self):
        """Findet Inkonsistenzen in den Kapitel-Referenzen"""
        inkonsistenzen = []
        attribute = {}
        
        for ref in self.kapitel_referenzen:
            attr = ref.get('attribut')
            wert = ref.get('wert')
            kapitel = ref.get('kapitel')
            
            if attr not in attribute:
                attribute[attr] = {'wert': wert, 'kapitel': kapitel}
            elif attribute[attr]['wert'] != wert:
                inkonsistenzen.append({
                    'attribut': attr,
                    'wert1': attribute[attr]['wert'],
                    'kapitel1': attribute[attr]['kapitel'],
                    'wert2': wert,
                    'kapitel2': kapitel
                })
        
        return inkonsistenzen


# =============================================================================
# Zeitlinien-Eintrag (Modul 2)
# =============================================================================

class ZeitlinienEintrag(models.Model):
    """
    Ein Eintrag in der Projekt-Timeline.
    Speichert Zeitmarker und deren Kapitel-Referenzen.
    """
    
    class ZeitTyp(models.TextChoices):
        EXPLIZIT = 'explizit', '📅 Explizites Datum'
        RELATIV = 'relativ', '⏱️ Relative Angabe'
        IMPLIZIT = 'implizit', '🌤️ Implizit (Jahreszeit, etc.)'
        BERECHNET = 'berechnet', '🔢 Berechnet'
    
    session = models.ForeignKey(
        LektoratsSession,
        on_delete=models.CASCADE,
        related_name='zeitlinien'
    )
    chapter = models.ForeignKey(
        'bfagent.BookChapters',
        on_delete=models.CASCADE,
        related_name='zeitlinien_eintraege'
    )
    
    # Zeitangabe
    zeit_typ = models.CharField(
        max_length=20,
        choices=ZeitTyp.choices,
        default=ZeitTyp.EXPLIZIT
    )
    beschreibung = models.CharField(
        max_length=500,
        help_text="Die Zeitangabe aus dem Text"
    )
    
    # Berechnete Werte
    tag_nummer = models.IntegerField(
        null=True,
        blank=True,
        help_text="Berechneter Tag relativ zu Tag 0"
    )
    datum = models.DateField(
        null=True,
        blank=True,
        help_text="Konkretes Datum (falls bekannt)"
    )
    
    # Originaltext
    originaltext = models.TextField(
        blank=True,
        help_text="Zitat aus dem Manuskript"
    )
    
    # Sortierung
    reihenfolge = models.PositiveIntegerField(
        default=0,
        help_text="Reihenfolge in der Timeline"
    )
    
    # AI-extrahiert
    ai_extrahiert = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_lektorats_zeitlinien'
        ordering = ['reihenfolge', 'tag_nummer']
        verbose_name = 'Zeitlinien-Eintrag'
        verbose_name_plural = 'Zeitlinien-Einträge'
    
    def __str__(self):
        return f"Tag {self.tag_nummer or '?'}: {self.beschreibung[:50]}..."


# =============================================================================
# Stil-Profil (Modul 4)
# =============================================================================

class StilProfil(models.Model):
    """
    Stil-Profil für ein Projekt.
    Definiert den erwarteten Stil für Konsistenzprüfungen.
    """
    
    class Perspektive(models.TextChoices):
        ICH = 'ich', 'Ich-Erzähler'
        ER_SIE = 'er_sie', 'Er/Sie-Erzähler'
        AUKTORIAL = 'auktorial', 'Auktorialer Erzähler'
        WECHSELND = 'wechselnd', 'Wechselnde Perspektive'
    
    class Tempus(models.TextChoices):
        PRAESENS = 'praesens', 'Präsens'
        PRAETERITUM = 'praeteritum', 'Präteritum'
        WECHSELND = 'wechselnd', 'Wechselnd'
    
    session = models.OneToOneField(
        LektoratsSession,
        on_delete=models.CASCADE,
        related_name='stil_profil'
    )
    
    # Erzählperspektive
    perspektive = models.CharField(
        max_length=20,
        choices=Perspektive.choices,
        default=Perspektive.ER_SIE
    )
    tempus = models.CharField(
        max_length=20,
        choices=Tempus.choices,
        default=Tempus.PRAETERITUM
    )
    
    # Satzstruktur
    durchschn_satzlaenge = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Durchschnittliche Wörter pro Satz"
    )
    fragmentsaetze_erlaubt = models.BooleanField(
        default=False,
        help_text="Sind Fragmentsätze erlaubt?"
    )
    
    # Tonalität
    grundton = models.CharField(
        max_length=100,
        blank=True,
        help_text="z.B. 'Ernst', 'Humorvoll', 'Ironisch'"
    )
    dialog_anteil = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Prozent Dialog"
    )
    
    # Sprachliche Merkmale
    metaphern_dichte = models.CharField(
        max_length=20,
        blank=True,
        help_text="Hoch/Mittel/Niedrig"
    )
    fachsprache = models.BooleanField(default=False)
    umgangssprache = models.BooleanField(default=False)
    besondere_stilmittel = models.TextField(blank=True)
    
    # AI-analysiert
    ai_analysiert = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_lektorats_stil_profil'
        verbose_name = 'Stil-Profil'
        verbose_name_plural = 'Stil-Profile'
    
    def __str__(self):
        return f"Stil-Profil: {self.session.project.title}"


# =============================================================================
# Wiederholungs-Analyse (Modul 5)
# =============================================================================

class WiederholungsAnalyse(models.Model):
    """
    Ergebnis einer Wiederholungs-Analyse.
    Speichert gefundene Wiederholungen mit Kontext.
    """
    
    class WiederholungsTyp(models.TextChoices):
        WORT = 'wort', '📝 Wort-Wiederholung'
        PHRASE = 'phrase', '💬 Phrasen-Wiederholung'
        BACKSTORY = 'backstory', '📖 Backstory-Wiederholung'
        STRUKTUR = 'struktur', '🏗️ Struktur-Wiederholung'
    
    class Bewertung(models.TextChoices):
        INTENTIONAL = 'intentional', '✅ Intentional (Leitmotiv)'
        AKZEPTABEL = 'akzeptabel', '🔵 Akzeptabel'
        PRUEFEN = 'pruefen', '🟡 Prüfen'
        KORRIGIEREN = 'korrigieren', '🔴 Korrigieren'
    
    session = models.ForeignKey(
        LektoratsSession,
        on_delete=models.CASCADE,
        related_name='wiederholungen'
    )
    
    # Wiederholung
    typ = models.CharField(
        max_length=20,
        choices=WiederholungsTyp.choices
    )
    text = models.TextField(
        help_text="Der wiederholte Text/Phrase"
    )
    anzahl = models.PositiveIntegerField(
        help_text="Anzahl der Vorkommen"
    )
    
    # Vorkommen (JSON)
    vorkommen = models.JSONField(
        default=list,
        help_text='Vorkommen: [{"kapitel": 5, "position": 123, "kontext": "..."}]'
    )
    
    # Bewertung
    bewertung = models.CharField(
        max_length=20,
        choices=Bewertung.choices,
        default=Bewertung.PRUEFEN
    )
    bewertung_notiz = models.TextField(
        blank=True,
        help_text="Notiz zur Bewertung"
    )
    
    # AI-erkannt
    ai_erkannt = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_lektorats_wiederholungen'
        ordering = ['-anzahl']
        verbose_name = 'Wiederholungs-Analyse'
        verbose_name_plural = 'Wiederholungs-Analysen'
    
    def __str__(self):
        return f"{self.get_typ_display()}: '{self.text[:30]}...' ({self.anzahl}x)"


# =============================================================================
# Genre-Style-Profile (für Korrektur-System)
# =============================================================================

class GenreStyleProfile(models.Model):
    """
    Stil-Richtlinien pro Genre für Korrekturvorschläge.
    Bestimmt wie streng/locker Wiederholungen behandelt werden.
    """
    
    class Tolerance(models.TextChoices):
        STRICT = 'strict', 'Streng - Minimale Wiederholungen'
        NORMAL = 'normal', 'Normal - Ausgewogen'
        RELAXED = 'relaxed', 'Locker - Stilmittel erlaubt'
    
    class SentenceLength(models.TextChoices):
        SHORT = 'short', 'Kurz (5-15 Wörter)'
        MEDIUM = 'medium', 'Mittel (10-25 Wörter)'
        LONG = 'long', 'Lang (20+ Wörter)'
        VARIED = 'varied', 'Variiert'
    
    genre = models.CharField(
        max_length=100,
        unique=True,
        help_text="Genre-Schlüssel (z.B. 'fantasy', 'thriller', 'romance')"
    )
    display_name = models.CharField(
        max_length=200,
        help_text="Anzeigename"
    )
    
    # Toleranz-Level
    repetition_tolerance = models.CharField(
        max_length=20,
        choices=Tolerance.choices,
        default=Tolerance.NORMAL,
        help_text="Wie streng sollen Wiederholungen bewertet werden?"
    )
    
    # Akzeptable Phrasen (werden nicht als Fehler markiert)
    acceptable_phrases = models.JSONField(
        default=list,
        blank=True,
        help_text='Phrasen die im Genre akzeptabel sind: ["sagte er", "fragte sie"]'
    )
    
    # Zu vermeidende Phrasen (werden strenger bewertet)
    avoid_phrases = models.JSONField(
        default=list,
        blank=True,
        help_text='Phrasen die vermieden werden sollten'
    )
    
    # Synonym-Präferenzen
    synonym_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text='Genre-typische Synonyme: {"sagte": ["flüsterte", "rief"]}'
    )
    
    # Stil-Anweisungen für LLM
    style_instructions = models.TextField(
        blank=True,
        help_text='Zusätzliche Anweisungen für Korrektur-Prompts'
    )
    
    # Satzlängen-Präferenz
    preferred_sentence_length = models.CharField(
        max_length=20,
        choices=SentenceLength.choices,
        default=SentenceLength.VARIED
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_genre_style_profiles'
        verbose_name = 'Genre-Stil-Profil'
        verbose_name_plural = 'Genre-Stil-Profile'
        ordering = ['display_name']
    
    def __str__(self):
        return f"{self.display_name} ({self.get_repetition_tolerance_display()})"


# =============================================================================
# Korrektur-Vorschlag (für Korrektur-System)
# =============================================================================

class CorrectionSuggestion(models.Model):
    """
    Speichert Korrekturvorschläge für erkannte Fehler.
    Verknüpft mit LektoratsFehler.
    """
    
    class Strategy(models.TextChoices):
        SYNONYM = 'synonym', 'Synonym-Ersetzung'
        REFORMULATE = 'reformulate', 'Umformulierung'
        DELETE = 'delete', 'Streichung'
        MERGE = 'merge', 'Zusammenführung'
        VARY = 'vary', 'Struktur-Variation'
        KEEP = 'keep', 'Beibehalten (Stilmittel)'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ausstehend'
        ACCEPTED = 'accepted', 'Akzeptiert'
        REJECTED = 'rejected', 'Abgelehnt'
        MODIFIED = 'modified', 'Modifiziert übernommen'
        AUTO_APPLIED = 'auto', 'Automatisch angewendet'
    
    # Verknüpfung zum Fehler
    fehler = models.ForeignKey(
        LektoratsFehler,
        on_delete=models.CASCADE,
        related_name='corrections'
    )
    
    # Korrektur-Details
    strategy = models.CharField(
        max_length=20,
        choices=Strategy.choices,
        help_text="Angewandte Korrektur-Strategie"
    )
    
    original_text = models.TextField(
        help_text="Original-Text der korrigiert werden soll"
    )
    
    suggested_text = models.TextField(
        help_text="Vorgeschlagene Korrektur"
    )
    
    alternatives = models.JSONField(
        default=list,
        blank=True,
        help_text="Alternative Vorschläge"
    )
    
    # Bewertung
    confidence = models.FloatField(
        default=0.0,
        help_text="Konfidenz-Score (0-1)"
    )
    
    # Kontext
    context_before = models.TextField(
        blank=True,
        help_text="Text vor der Stelle"
    )
    
    context_after = models.TextField(
        blank=True,
        help_text="Text nach der Stelle"
    )
    
    # Position im Text
    chapter_id = models.IntegerField(null=True, blank=True)
    position_start = models.IntegerField(null=True, blank=True)
    position_end = models.IntegerField(null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # User-Feedback
    user_note = models.TextField(
        blank=True,
        help_text="Notiz des Users zur Entscheidung"
    )
    
    final_text = models.TextField(
        blank=True,
        help_text="Tatsächlich verwendeter Text (bei MODIFIED)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'writing_correction_suggestions'
        verbose_name = 'Korrektur-Vorschlag'
        verbose_name_plural = 'Korrektur-Vorschläge'
        ordering = ['-confidence', 'created_at']
    
    def __str__(self):
        return f"{self.get_strategy_display()}: {self.original_text[:30]}..."


# =============================================================================
# Export der Models
# =============================================================================

__all__ = [
    'LektoratsSession',
    'LektoratsFehler',
    'FigurenRegister',
    'ZeitlinienEintrag',
    'StilProfil',
    'WiederholungsAnalyse',
    'GenreStyleProfile',
    'CorrectionSuggestion',
]
