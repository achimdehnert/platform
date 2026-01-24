"""
Book Series / Universe Models
=============================

Ermöglicht die Verwaltung von Buchreihen mit gemeinsamen:
- Charakteren (SharedCharacter)
- Welten (SharedWorld)
- Illustrations-Stil
- Schreibstil

Naming Convention: writing_* Präfix für alle Tabellen.
"""

import uuid
from django.conf import settings
from django.db import models


# =============================================================================
# BOOK SERIES (Universe / Buchreihe)
# =============================================================================

class BookSeries(models.Model):
    """
    Buchreihe / Universe - gruppiert mehrere Bücher mit gemeinsamen Elementen.
    
    Beispiele:
    - "Herr der Ringe" Trilogie
    - "Harry Potter" Serie
    - "Die Macht-Trilogie"
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(
        max_length=200,
        help_text="Name der Buchreihe, z.B. 'Die Macht-Trilogie'"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Beschreibung der Reihe und ihres Universums"
    )
    
    genre = models.CharField(
        max_length=100,
        blank=True,
        help_text="Hauptgenre der Reihe"
    )
    
    # Einheitlicher Illustrations-Stil für die gesamte Reihe (optional)
    illustration_style_template = models.ForeignKey(
        'writing_hub.IllustrationStyleTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='series_using',
        help_text="Einheitlicher visueller Stil für alle Bücher der Reihe"
    )
    
    # Einheitlicher Schreibstil für die Reihe (optional)
    writing_style = models.ForeignKey(
        'writing_hub.WritingStyle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='series_using',
        help_text="Einheitlicher Schreibstil für die Reihe"
    )
    
    # Cover-Bild für die Reihe
    cover_image = models.ImageField(
        upload_to='series_covers/',
        blank=True,
        null=True,
        help_text="Cover-Bild für die Buchreihe"
    )
    
    # =========================================================================
    # KONSISTENZ-ATTRIBUTE für die gesamte Reihe
    # =========================================================================
    
    # Zeitliche Einordnung
    series_timeline = models.TextField(
        blank=True,
        help_text="Zeitlicher Rahmen der Reihe (z.B. '1920-1945' oder 'Mittelalter')"
    )
    
    # Erzählperspektive
    narrative_voice = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('first_person', 'Ich-Erzähler'),
            ('third_limited', '3. Person (begrenzt)'),
            ('third_omniscient', '3. Person (allwissend)'),
            ('multiple_pov', 'Wechselnde POVs'),
            ('mixed', 'Gemischt'),
        ],
        help_text="Einheitliche Erzählperspektive für alle Bücher"
    )
    
    # Ton und Stimmung
    tone_guidelines = models.TextField(
        blank=True,
        help_text="Ton/Stimmung der Reihe (z.B. 'düster, melancholisch' oder 'humorvoll, leicht')"
    )
    
    # Zielgruppe
    target_audience = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('children', 'Kinder (6-10)'),
            ('middle_grade', 'Middle Grade (10-14)'),
            ('young_adult', 'Young Adult (14-18)'),
            ('new_adult', 'New Adult (18-25)'),
            ('adult', 'Erwachsene'),
            ('all_ages', 'Alle Altersgruppen'),
        ],
        help_text="Zielgruppe der Reihe"
    )
    
    # Konsistenz-Regeln
    consistency_rules = models.TextField(
        blank=True,
        help_text="Regeln für Konsistenz (z.B. 'Magie hat immer einen Preis', 'Keine modernen Begriffe')"
    )
    
    # Verbotene Elemente
    forbidden_elements = models.TextField(
        blank=True,
        help_text="Elemente, die NICHT vorkommen sollen (z.B. 'Zeitreisen', 'Deus ex machina')"
    )
    
    # Pflicht-Elemente
    required_elements = models.TextField(
        blank=True,
        help_text="Elemente, die in jedem Buch vorkommen müssen (z.B. 'Rückkehr zum Heimatort')"
    )
    
    # Spice Level (für Romance)
    spice_level = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('clean', 'Clean (keine expliziten Szenen)'),
            ('mild', 'Mild (closed door)'),
            ('medium', 'Medium (fade to black)'),
            ('spicy', 'Spicy (explizit)'),
            ('very_spicy', 'Sehr Spicy (sehr explizit)'),
        ],
        help_text="Erotik-Level für die gesamte Reihe"
    )
    
    # Content Warnings
    content_warnings = models.TextField(
        blank=True,
        help_text="Content Warnings für die Reihe (z.B. 'Gewalt, Verlust, PTSD')"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='book_series'
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_book_series'
        verbose_name = 'Buchreihe'
        verbose_name_plural = 'Buchreihen'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def projects_count(self):
        """Anzahl der Bücher in dieser Reihe"""
        return self.projects.count()
    
    @property
    def characters_count(self):
        """Anzahl der gemeinsamen Charaktere"""
        return self.characters.count()
    
    @property
    def worlds_count(self):
        """Anzahl der gemeinsamen Welten"""
        return self.worlds.count()


# =============================================================================
# SHARED CHARACTER (Reihen-übergreifende Charaktere)
# =============================================================================

class SharedCharacter(models.Model):
    """
    Charakter auf Reihen-Ebene - erscheint in mehreren Büchern der Reihe.
    
    Zentrale Verwaltung von Charakteren, die über mehrere Bücher hinweg
    konsistent bleiben sollen (z.B. Frodo in allen HdR-Büchern).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    series = models.ForeignKey(
        BookSeries,
        on_delete=models.CASCADE,
        related_name='characters'
    )
    
    name = models.CharField(max_length=200)
    
    class Role(models.TextChoices):
        PROTAGONIST = 'protagonist', 'Protagonist'
        ANTAGONIST = 'antagonist', 'Antagonist'
        DEUTERAGONIST = 'deuteragonist', 'Deuteragonist'
        SUPPORTING = 'supporting', 'Nebenrolle'
        MINOR = 'minor', 'Kleinere Rolle'
        MENTOR = 'mentor', 'Mentor'
        LOVE_INTEREST = 'love_interest', 'Love Interest'
    
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SUPPORTING
    )
    
    description = models.TextField(
        blank=True,
        help_text="Allgemeine Beschreibung des Charakters"
    )
    
    # Detaillierte Informationen
    age_at_series_start = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Alter zu Beginn der Reihe"
    )
    
    background = models.TextField(
        blank=True,
        help_text="Hintergrundgeschichte"
    )
    
    personality = models.TextField(
        blank=True,
        help_text="Persönlichkeitsmerkmale"
    )
    
    appearance = models.TextField(
        blank=True,
        help_text="Physische Beschreibung"
    )
    
    motivation = models.TextField(
        blank=True,
        help_text="Was treibt diesen Charakter an?"
    )
    
    arc = models.TextField(
        blank=True,
        help_text="Charakterentwicklung über die Reihe"
    )
    
    # Portrait-Bild
    portrait_image = models.ImageField(
        upload_to='character_portraits/',
        blank=True,
        null=True
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_shared_characters'
        verbose_name = 'Gemeinsamer Charakter'
        verbose_name_plural = 'Gemeinsame Charaktere'
        ordering = ['series', 'role', 'name']
        unique_together = ['series', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"


# =============================================================================
# SHARED WORLD (Reihen-übergreifende Welten)
# =============================================================================

class SharedWorld(models.Model):
    """
    Welt auf Reihen-Ebene - Setting das in mehreren Büchern vorkommt.
    
    Zentrale Verwaltung von Welten/Settings für konsistentes Worldbuilding
    über die gesamte Reihe (z.B. Mittelerde, Auenland, Mordor).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    series = models.ForeignKey(
        BookSeries,
        on_delete=models.CASCADE,
        related_name='worlds'
    )
    
    name = models.CharField(max_length=200)
    
    class WorldType(models.TextChoices):
        PRIMARY = 'primary', 'Hauptwelt'
        SECONDARY = 'secondary', 'Nebenwelt'
        REALM = 'realm', 'Reich/Königreich'
        CITY = 'city', 'Stadt'
        REGION = 'region', 'Region'
        DIMENSION = 'dimension', 'Dimension/Parallelwelt'
    
    world_type = models.CharField(
        max_length=20,
        choices=WorldType.choices,
        default=WorldType.PRIMARY
    )
    
    description = models.TextField(
        blank=True,
        help_text="Allgemeine Beschreibung der Welt"
    )
    
    # Worldbuilding Details
    geography = models.TextField(
        blank=True,
        help_text="Geografie und Landschaft"
    )
    
    culture = models.TextField(
        blank=True,
        help_text="Kultur und Gesellschaft"
    )
    
    technology_level = models.TextField(
        blank=True,
        help_text="Technologisches Niveau"
    )
    
    magic_system = models.TextField(
        blank=True,
        help_text="Magiesystem (falls vorhanden)"
    )
    
    politics = models.TextField(
        blank=True,
        help_text="Politische Strukturen"
    )
    
    history = models.TextField(
        blank=True,
        help_text="Geschichte der Welt"
    )
    
    # Preview-Bild
    preview_image = models.ImageField(
        upload_to='world_previews/',
        blank=True,
        null=True
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_shared_worlds'
        verbose_name = 'Gemeinsame Welt'
        verbose_name_plural = 'Gemeinsame Welten'
        ordering = ['series', 'world_type', 'name']
        unique_together = ['series', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_world_type_display()})"


# =============================================================================
# JUNCTION TABLES (Projekt-spezifische Verknüpfungen)
# =============================================================================

class ProjectCharacterLink(models.Model):
    """
    Verknüpfung: Welcher SharedCharacter erscheint in welchem Buch?
    
    Ermöglicht projekt-spezifische Anpassungen wie:
    - Alter des Charakters in diesem Buch
    - Rolle in diesem spezifischen Buch
    - Notizen zur Erscheinung
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='character_links'
    )
    
    shared_character = models.ForeignKey(
        SharedCharacter,
        on_delete=models.CASCADE,
        related_name='project_links'
    )
    
    # Projekt-spezifische Anpassungen
    age_in_book = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Alter des Charakters in diesem Buch"
    )
    
    role_in_book = models.CharField(
        max_length=100,
        blank=True,
        help_text="Spezifische Rolle in diesem Buch (falls abweichend)"
    )
    
    appearance_notes = models.TextField(
        blank=True,
        help_text="Anmerkungen zur Erscheinung in diesem Buch"
    )
    
    first_appearance_chapter = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Erstes Kapitel, in dem der Charakter erscheint"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Erscheint dieser Charakter in diesem Buch?"
    )
    
    class Meta:
        db_table = 'writing_project_character_links'
        verbose_name = 'Projekt-Charakter-Verknüpfung'
        verbose_name_plural = 'Projekt-Charakter-Verknüpfungen'
        unique_together = ['project', 'shared_character']
    
    def __str__(self):
        return f"{self.shared_character.name} in {self.project.title}"


class ProjectWorldLink(models.Model):
    """
    Verknüpfung: Welche SharedWorld wird in welchem Buch verwendet?
    
    Ermöglicht projekt-spezifische Anpassungen wie:
    - Zeitpunkt/Epoche in diesem Buch
    - Relevanz für die Handlung
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='series_world_links'
    )
    
    shared_world = models.ForeignKey(
        SharedWorld,
        on_delete=models.CASCADE,
        related_name='project_links'
    )
    
    # Projekt-spezifische Anpassungen
    time_period = models.CharField(
        max_length=200,
        blank=True,
        help_text="Zeitraum/Epoche in diesem Buch"
    )
    
    relevance = models.CharField(
        max_length=20,
        choices=[
            ('primary', 'Hauptschauplatz'),
            ('secondary', 'Nebenschauplatz'),
            ('mentioned', 'Nur erwähnt'),
        ],
        default='primary'
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Anmerkungen zur Verwendung in diesem Buch"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Wird diese Welt in diesem Buch verwendet?"
    )
    
    class Meta:
        db_table = 'writing_project_world_links'
        verbose_name = 'Projekt-Welt-Verknüpfung'
        verbose_name_plural = 'Projekt-Welt-Verknüpfungen'
        unique_together = ['project', 'shared_world']
    
    def __str__(self):
        return f"{self.shared_world.name} in {self.project.title}"
