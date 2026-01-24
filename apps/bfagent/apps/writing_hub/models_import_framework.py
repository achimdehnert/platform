"""
Import Framework V2 - Models for Smart Import and Outline Generation

This module provides:
- ImportPromptTemplate: DB-driven prompt templates for LLM extraction steps
- OutlineCategory: Categories for organizing outline templates
- OutlineTemplate: Template library for story structures
- ProjectOutline: Generated outline per project
- ImportSession: Tracking import sessions and their results

Author: BF Agent Team
Date: 2026-01-22
"""

from django.db import models
from django.utils import timezone


class ImportPromptTemplate(models.Model):
    """
    DB-gesteuerte Prompt-Templates für Import-Schritte.
    
    Ermöglicht:
    - Prompt-Änderungen ohne Code-Deploy
    - A/B-Testing von Prompts
    - Versionierung und Rollback
    """
    
    step_code = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Unique step identifier (e.g., type_detection, metadata_extraction)"
    )
    step_name = models.CharField(
        max_length=200,
        help_text="Human-readable step name"
    )
    step_name_de = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="German step name"
    )
    description = models.TextField(
        blank=True,
        help_text="Beschreibung des Templates"
    )
    step_order = models.PositiveIntegerField(
        default=10,
        help_text="Order of execution"
    )
    
    # Prompt Content
    system_prompt = models.TextField(
        help_text="System-Prompt für LLM"
    )
    user_prompt_template = models.TextField(
        help_text="User-Prompt mit Platzhaltern: {content}, {context}, {metadata_context}"
    )
    
    # Output Schema (JSON Schema für Validierung)
    output_schema = models.JSONField(
        blank=True,
        null=True,
        help_text="Expected JSON schema for validation"
    )
    example_input = models.TextField(
        blank=True,
        null=True,
        help_text="Example input for documentation"
    )
    example_output = models.TextField(
        blank=True,
        null=True,
        help_text="Example output for documentation"
    )
    
    # LLM Settings
    temperature = models.FloatField(
        default=0.2,
        help_text="LLM Temperature (0.0-1.0)"
    )
    max_tokens = models.PositiveIntegerField(
        default=4000,
        help_text="Max Output Tokens"
    )
    preferred_model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Preferred LLM model (e.g., 'gpt-4o', 'claude-3')"
    )
    fallback_model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Fallback LLM model"
    )
    
    # Versionierung
    version = models.PositiveIntegerField(
        default=1,
        help_text="Version des Templates"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Ist dieses Template aktiv?"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = 'writing_hub_import_prompt_template'
        ordering = ['step_order', 'step_code']
        verbose_name = 'Import Prompt Template'
        verbose_name_plural = 'Import Prompt Templates'
    
    def __str__(self):
        return f"{self.step_name} (v{self.version})"
    
    @classmethod
    def get_active_for_step(cls, step_code: str) -> 'ImportPromptTemplate':
        """Hole das aktive Template für einen Schritt"""
        return cls.objects.filter(
            step_code=step_code, 
            is_active=True
        ).order_by('-version').first()


class OutlineCategory(models.Model):
    """
    Kategorien für Outline-Templates.
    
    Beispiele:
    - Classic Structures (3-Act, 5-Act, Hero's Journey)
    - Genre-Specific (Romance, Thriller, Fantasy)
    - Author Methods (Save the Cat, Story Grid)
    """
    
    code = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Eindeutiger Code (z.B. 'classic', 'genre_specific')"
    )
    name = models.CharField(
        max_length=200,
        help_text="Anzeigename"
    )
    name_de = models.CharField(
        max_length=200,
        blank=True,
        help_text="Deutscher Name"
    )
    description = models.TextField(
        blank=True,
        help_text="Beschreibung der Kategorie"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        default='bi-diagram-3',
        help_text="Bootstrap Icon Class"
    )
    order = models.IntegerField(
        default=10,
        help_text="Sortierreihenfolge"
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'writing_hub_outline_category'
        ordering = ['order', 'name']
        verbose_name_plural = 'Outline Categories'
    
    def __str__(self):
        return self.name


class OutlineTemplate(models.Model):
    """
    Outline-Template-Library.
    
    Definiert vorgefertigte Story-Strukturen die auf Projekte angewendet werden können.
    """
    
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    code = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Eindeutiger Code (z.B. 'three_act', 'save_the_cat')"
    )
    name = models.CharField(
        max_length=200,
        help_text="Anzeigename"
    )
    name_de = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Deutscher Name"
    )
    
    category = models.ForeignKey(
        OutlineCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='templates',
        help_text="Kategorie des Templates"
    )
    
    description = models.TextField(
        help_text="Ausführliche Beschreibung des Templates"
    )
    description_de = models.TextField(
        blank=True,
        null=True,
        help_text="Deutsche Beschreibung"
    )
    
    # Structure Definition (JSON)
    structure_json = models.JSONField(
        help_text="Full structure: acts, beats, chapters"
    )
    
    # Matching Criteria
    genre_tags = models.JSONField(
        default=list,
        help_text="Suitable genres"
    )
    theme_tags = models.JSONField(
        default=list,
        help_text="Suitable themes"
    )
    pov_tags = models.JSONField(
        default=list,
        help_text="Suitable POV styles"
    )
    
    # Word Count Range
    word_count_min = models.PositiveIntegerField(
        default=60000,
        help_text="Minimale Wortanzahl für Empfehlung"
    )
    word_count_max = models.PositiveIntegerField(
        default=100000,
        help_text="Maximale Wortanzahl für Empfehlung"
    )
    
    # Metadata
    difficulty_level = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default='intermediate',
        help_text="Difficulty level for authors"
    )
    example_books = models.TextField(
        blank=True,
        help_text="Famous books using this structure"
    )
    pros = models.TextField(
        blank=True,
        help_text="Advantages of this structure"
    )
    cons = models.TextField(
        blank=True,
        help_text="Disadvantages of this structure"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(
        default=False,
        help_text="Wird prominent angezeigt"
    )
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this template was used"
    )
    avg_rating = models.FloatField(
        default=0.0,
        help_text="Average user rating"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = 'writing_hub_outline_template'
        ordering = ['-is_featured', '-usage_count', 'name']
        verbose_name = 'Outline Template'
        verbose_name_plural = 'Outline Templates'
    
    def __str__(self):
        return f"{self.name} ({self.category})"
    
    def get_total_beats(self) -> int:
        """Zähle alle Beats in der Struktur"""
        total = 0
        structure = self.structure_json or {}
        for act in structure.get('acts', []):
            total += len(act.get('beats', []))
        return total
    
    def get_acts_count(self) -> int:
        """Anzahl der Akte"""
        structure = self.structure_json or {}
        return len(structure.get('acts', []))


class ProjectOutline(models.Model):
    """
    Generiertes Outline für ein spezifisches Projekt.
    
    Entsteht durch Anwendung eines OutlineTemplates auf ein BookProject,
    kann aber vom User angepasst werden.
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('finalized', 'Finalized'),
    ]
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='outlines'
    )
    template = models.ForeignKey(
        OutlineTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Verwendetes Template (null wenn custom)"
    )
    
    version = models.PositiveIntegerField(
        default=1,
        help_text="Version number of this outline"
    )
    
    # Finales Outline (kann vom Template abweichen)
    outline_data = models.JSONField(
        help_text="Generated/edited outline"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Is this the active outline for the project"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    notes = models.TextField(
        blank=True,
        help_text="Notes about this outline version"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_hub_project_outline'
        ordering = ['-version']
        verbose_name = 'Project Outline'
        verbose_name_plural = 'Project Outlines'
        constraints = [
            models.UniqueConstraint(
                fields=['project'],
                condition=models.Q(is_active=True),
                name='unique_active_outline_per_project'
            )
        ]
    
    def __str__(self):
        template_name = self.template.name if self.template else 'Custom'
        return f"Outline für {self.project.title} v{self.version} ({template_name})"


class ImportSession(models.Model):
    """
    Tracking von Import-Sessions.
    
    Speichert den Verlauf und die Ergebnisse eines Import-Vorgangs.
    """
    
    STATUS_CHOICES = [
        ('started', 'Gestartet'),
        ('analyzing', 'Analysiert'),
        ('review', 'User Review'),
        ('completed', 'Abgeschlossen'),
        ('failed', 'Fehlgeschlagen'),
        ('cancelled', 'Abgebrochen'),
    ]
    
    SOURCE_TYPE_CHOICES = [
        ('upload', 'File Upload'),
        ('paste', 'Pasted Content'),
        ('url', 'URL Import'),
    ]
    
    # Session ID for URL-safe reference
    session_id = models.CharField(
        max_length=36,
        unique=True,
        help_text="UUID für URL-Referenz"
    )
    
    # User
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='import_sessions'
    )
    
    # Source
    source_filename = models.CharField(
        max_length=500,
        help_text="Original-Dateiname"
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
        default='upload',
        help_text="Art der Quelle"
    )
    source_content_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA256 Hash des Contents"
    )
    
    # Raw Content (for reprocessing)
    raw_content = models.TextField(
        blank=True,
        help_text="Original-Inhalt des Dokuments"
    )
    
    # Document Type (detected by AI)
    document_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Erkannter Dokumenttyp (expose, manuscript, outline, etc.)"
    )
    
    # Result
    created_project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='import_sessions',
        help_text="Erstelltes Projekt (nach Abschluss)"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='started'
    )
    
    # Extracted Data (full AI analysis result)
    extracted_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Vollständiges AI-Extraktionsergebnis"
    )
    
    # Selected Items (user selections for import)
    selected_items = models.JSONField(
        null=True,
        blank=True,
        help_text="Vom User ausgewählte Items für Import"
    )
    
    # Legacy fields for compatibility
    analysis_result = models.JSONField(
        null=True,
        blank=True,
        help_text="Legacy: Vollständiges Analyse-Ergebnis"
    )
    selected_characters = models.JSONField(
        default=list,
        help_text="Legacy: Ausgewählte Charakter-Namen"
    )
    selected_locations = models.JSONField(
        default=list,
        help_text="Legacy: Ausgewählte Locations"
    )
    selected_chapters = models.JSONField(
        default=list,
        help_text="Legacy: Ausgewählte Kapitel-Indizes"
    )
    
    # Outline Selection
    selected_outline_template = models.ForeignKey(
        OutlineTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='import_sessions'
    )
    
    # Errors
    error_message = models.TextField(
        blank=True,
        help_text="Fehlermeldung falls failed"
    )
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # LLM Usage
    total_tokens_used = models.IntegerField(default=0)
    total_llm_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        default=0
    )
    
    class Meta:
        db_table = 'writing_hub_import_session'
        ordering = ['-started_at']
        verbose_name = 'Import Session'
        verbose_name_plural = 'Import Sessions'
    
    def __str__(self):
        return f"Import: {self.source_filename} ({self.status})"
    
    def mark_completed(self, project):
        """Markiere Session als abgeschlossen"""
        self.status = 'completed'
        self.created_project = project
        self.completed_at = timezone.now()
        self.save()
    
    def mark_failed(self, error: str):
        """Markiere Session als fehlgeschlagen"""
        self.status = 'failed'
        self.error_message = error
        self.completed_at = timezone.now()
        self.save()


class OutlineRecommendation(models.Model):
    """
    Speichert LLM-Empfehlungen für Outline-Templates.
    
    Ermöglicht Analyse welche Empfehlungen akzeptiert werden.
    """
    
    import_session = models.ForeignKey(
        ImportSession,
        on_delete=models.CASCADE,
        related_name='outline_recommendations'
    )
    template = models.ForeignKey(
        OutlineTemplate,
        on_delete=models.CASCADE
    )
    
    # Matching
    match_score = models.FloatField(
        help_text="Match-Score 0.0-1.0"
    )
    match_reason = models.TextField(
        help_text="Begründung für die Empfehlung"
    )
    
    # User Decision
    was_selected = models.BooleanField(
        default=False,
        help_text="Wurde vom User ausgewählt"
    )
    
    # Order
    rank = models.IntegerField(
        default=1,
        help_text="Rang der Empfehlung (1 = beste)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'writing_hub_outline_recommendation'
        ordering = ['import_session', 'rank']
        unique_together = ['import_session', 'template']
    
    def __str__(self):
        return f"Empfehlung: {self.template.name} ({self.match_score:.0%})"
