"""
Writing Hub Models
==================

Central models module for Writing Hub.
Imports all lookup models for Django discovery.
"""

from django.db import models
from django.contrib.auth import get_user_model

from .models_handler_lookups import ErrorStrategy, HandlerCategory, HandlerPhase
from .models_lookups import ArcType, ContentRating, ImportanceLevel, WritingStage
from .models_story_elements import (
    Beat,
    BeatType,
    ConflictLevel,
    EmotionalTone,
    Location,
    PlotThread,
    Scene,
    SceneConnection,
    SceneConnectionType,
    TimelineEvent,
)
from .models_prompt_system import (
    PromptMasterStyle,
    PromptCharacter,
    PromptLocation,
    PromptCulturalElement,
    PromptSceneTemplate,
    PromptGenerationLog,
)
from .models_publishing import (
    PublishingMetadata,
    BookCover,
    FrontMatter,
    BackMatter,
    AuthorProfile,
)
from .models_agents import (
    AgentRole,
    LlmTier,
    AgentRoleContentConfig,
    ProjectAgentConfig,
    AgentPipelineTemplate,
    AgentPipelineExecution,
    AgentPipelineStep,
)
from .models_literature import (
    LiteratureSource,
    Citation,
    CitationStyle,
    LiteratureCollection,
    BibTeXImport,
)
from .models_quality import (
    QualityDimension,
    GateDecisionType,
    PromiseStatus,
    ChapterQualityScore,
    ChapterDimensionScore,
    ProjectQualityConfig,
    ProjectDimensionThreshold,
    CanonFact,
    StoryPromise,
    PromiseEvent,
)
from .models_style import (
    AuthorStyleDNA,
    StyleLabSession,
    StyleObservation,
    StyleCandidate,
    SentenceFeedback,
    StyleFeedback,
    StyleAcceptanceTest,
    StyleAdoption,
    Author,
    WritingStyle,
    ProjectAuthor,
)
from .models_creative import (
    CreativeSession,
    BookIdea,
    CreativeMessage,
)
from .models_lektorat import (
    LektoratsSession,
    LektoratsFehler,
    FigurenRegister,
    ZeitlinienEintrag,
    StilProfil,
    WiederholungsAnalyse,
    GenreStyleProfile,
    CorrectionSuggestion,
)
from .models_series import (
    BookSeries,
    SharedCharacter,
    SharedWorld,
    ProjectCharacterLink,
    ProjectWorldLink,
)
from .models_import_framework import (
    ImportPromptTemplate,
    OutlineCategory,
    OutlineTemplate,
    ProjectOutline,
    ImportSession,
    OutlineRecommendation,
)

# Import base models from bfagent for proxy models
from apps.bfagent.models_main import (
    BookProjects as BfAgentBookProjects,
    BookChapters as BfAgentBookChapters,
    Characters as BfAgentCharacters,
)

User = get_user_model()


# =============================================================================
# Outline Versioning System
# =============================================================================

class OutlineVersion(models.Model):
    """
    Stores versioned snapshots of outline progress.
    Allows iterative refinement before proceeding to chapter writing.
    """
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Entwurf'
        IN_PROGRESS = 'in_progress', 'In Bearbeitung'
        REVIEW = 'review', 'Zur Überprüfung'
        APPROVED = 'approved', 'Freigegeben'
        FINALIZED = 'finalized', 'Finalisiert'
    
    class Framework(models.TextChoices):
        SAVE_THE_CAT = 'save_the_cat', 'Save the Cat (15 Beats)'
        HEROS_JOURNEY = 'heros_journey', "Hero's Journey (12 Stufen)"
        THREE_ACT = 'three_act', 'Three-Act Structure (12 Beats)'
        CUSTOM = 'custom', 'Eigene Struktur'
    
    # Relations
    project = models.ForeignKey(
        BfAgentBookProjects,
        on_delete=models.CASCADE,
        related_name='outline_versions'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='outline_versions'
    )
    
    # Version Info
    version_number = models.PositiveIntegerField(default=1)
    version_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="z.B. 'Erster Entwurf', 'Nach Feedback', 'Final'"
    )
    
    # Framework & Status
    framework = models.CharField(
        max_length=20,
        choices=Framework.choices,
        default=Framework.SAVE_THE_CAT
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    # Content (JSON snapshot of all chapters)
    chapters_snapshot = models.JSONField(
        default=list,
        help_text="Complete snapshot of all chapter outlines"
    )
    
    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Notizen zu dieser Version"
    )
    word_count_target = models.PositiveIntegerField(default=50000)
    chapter_count = models.PositiveIntegerField(default=0)
    
    # Feedback (Project-Level)
    project_feedback = models.TextField(
        blank=True,
        help_text="Allgemeines Feedback auf Projektebene (Stil, Ton, Konsistenz)"
    )
    chapter_feedback = models.JSONField(
        default=dict,
        help_text="Feedback pro Kapitel: {chapter_number: 'feedback text'}"
    )
    
    # Flags
    is_active = models.BooleanField(
        default=True,
        help_text="Aktive Version für Bearbeitung"
    )
    is_locked = models.BooleanField(
        default=False,
        help_text="Gesperrt für Änderungen"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'writing_outline_versions'
        ordering = ['-version_number', '-created_at']
        unique_together = ['project', 'version_number']
        verbose_name = 'Outline Version'
        verbose_name_plural = 'Outline Versions'
    
    def __str__(self):
        return f"{self.project.title} - v{self.version_number} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Auto-increment version number for new versions
        if not self.pk:
            last_version = OutlineVersion.objects.filter(
                project=self.project
            ).order_by('-version_number').first()
            self.version_number = (last_version.version_number + 1) if last_version else 1
        
        # Update chapter count
        if self.chapters_snapshot:
            self.chapter_count = len(self.chapters_snapshot)
        
        super().save(*args, **kwargs)
    
    def create_snapshot_from_chapters(self):
        """Create a snapshot from current BookChapters"""
        from apps.bfagent.models import BookChapters
        import json
        
        chapters = BookChapters.objects.filter(
            project=self.project
        ).order_by('chapter_number')
        
        snapshot = []
        for ch in chapters:
            # Extract notes data if available
            notes_data = {}
            if ch.notes:
                try:
                    notes_data = json.loads(ch.notes) if isinstance(ch.notes, str) else ch.notes
                except:
                    pass
            
            snapshot.append({
                'id': ch.id,
                'number': ch.chapter_number,
                'title': ch.title,
                'beat': notes_data.get('beat', ''),
                'act': notes_data.get('act', 1),
                'outline': notes_data.get('raw_outline', ch.outline or ''),
                'emotional_arc': notes_data.get('emotional_arc', ''),
                'target_words': ch.target_word_count or 2000,
            })
        
        self.chapters_snapshot = snapshot
        self.chapter_count = len(snapshot)
        return snapshot
    
    def restore_to_chapters(self):
        """Restore this version's snapshot to BookChapters"""
        from apps.bfagent.models import BookChapters
        import json
        
        # Delete existing chapters
        BookChapters.objects.filter(project=self.project).delete()
        
        # Create chapters from snapshot
        for ch_data in self.chapters_snapshot:
            outline_parts = []
            if ch_data.get('beat'):
                outline_parts.append(f"**Beat:** {ch_data['beat']}")
            if ch_data.get('act'):
                outline_parts.append(f"**Akt:** {ch_data['act']}")
            if ch_data.get('emotional_arc'):
                outline_parts.append(f"**Emotionaler Bogen:** {ch_data['emotional_arc']}")
            if ch_data.get('outline'):
                outline_parts.append(f"\n**Handlung:**\n{ch_data['outline']}")
            
            BookChapters.objects.create(
                project=self.project,
                chapter_number=ch_data.get('number', 1),
                title=ch_data.get('title', ''),
                outline="\n".join(outline_parts) if outline_parts else ch_data.get('outline', ''),
                target_word_count=ch_data.get('target_words', 2000),
                notes=json.dumps({
                    'beat': ch_data.get('beat', ''),
                    'act': ch_data.get('act', 1),
                    'emotional_arc': ch_data.get('emotional_arc', ''),
                    'raw_outline': ch_data.get('outline', ''),
                })
            )
        
        return True
    
    def can_proceed_to_writing(self):
        """Check if this version is ready for chapter writing"""
        return self.status == self.Status.FINALIZED and self.is_locked


# =============================================================================
# Proxy Models for Writing Hub Admin
# =============================================================================

class BookProject(BfAgentBookProjects):
    """Proxy model for BookProjects to appear in Writing Hub admin"""
    class Meta:
        proxy = True
        app_label = 'writing_hub'
        verbose_name = 'Book Project'
        verbose_name_plural = 'Book Projects'


class Chapter(BfAgentBookChapters):
    """Proxy model for BookChapters to appear in Writing Hub admin"""
    class Meta:
        proxy = True
        app_label = 'writing_hub'
        verbose_name = 'Chapter'
        verbose_name_plural = 'Chapters'


class Character(BfAgentCharacters):
    """Proxy model for Characters to appear in Writing Hub admin"""
    class Meta:
        proxy = True
        app_label = 'writing_hub'
        verbose_name = 'Character'
        verbose_name_plural = 'Characters'


# =============================================================================
# Content Type Framework System (DB-driven)
# =============================================================================

class ContentType(models.Model):
    """
    Content types for writing projects: Novel, Essay, Scientific Paper, etc.
    Replaces hardcoded content types with DB-driven configuration.
    """
    slug = models.SlugField(max_length=50, unique=True, help_text="e.g. 'novel', 'essay', 'scientific'")
    name = models.CharField(max_length=100, help_text="Display name")
    name_de = models.CharField(max_length=100, blank=True, help_text="German name")
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='bi-file-text', help_text="Bootstrap icon class")
    section_label = models.CharField(max_length=50, default='Kapitel', help_text="Label for sections: Kapitel, Abschnitt")
    section_label_plural = models.CharField(max_length=50, default='Kapitel', help_text="Plural label")
    
    # Default settings
    default_word_count = models.PositiveIntegerField(default=50000)
    default_section_count = models.PositiveIntegerField(default=15)
    
    # Features enabled for this content type
    has_characters = models.BooleanField(default=True, help_text="Enable character management")
    has_world_building = models.BooleanField(default=True, help_text="Enable world building")
    has_citations = models.BooleanField(default=False, help_text="Enable citation management")
    has_abstract = models.BooleanField(default=False, help_text="Enable abstract/summary")
    
    # LLM Configuration
    llm_system_prompt = models.TextField(blank=True, help_text="System prompt for LLM calls")
    
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_content_types'
        ordering = ['sort_order', 'name']
        verbose_name = 'Content Type'
        verbose_name_plural = 'Content Types'
    
    def __str__(self):
        return self.name_de or self.name


class StructureFramework(models.Model):
    """
    Structure frameworks for organizing content.
    Examples: Save the Cat, Hero's Journey, IMRaD, Argumentative Essay
    """
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='frameworks'
    )
    slug = models.SlugField(max_length=50, help_text="e.g. 'save_the_cat', 'imrad'")
    name = models.CharField(max_length=100)
    name_de = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='bi-diagram-3')
    
    # Framework configuration
    default_section_count = models.PositiveIntegerField(default=15)
    
    # LLM Prompts for this framework
    llm_system_prompt = models.TextField(blank=True, help_text="System prompt for outline generation")
    llm_user_template = models.TextField(blank=True, help_text="User prompt template with {placeholders}")
    
    is_default = models.BooleanField(default=False, help_text="Default framework for content type")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_structure_frameworks'
        ordering = ['content_type', 'sort_order', 'name']
        unique_together = ['content_type', 'slug']
        verbose_name = 'Structure Framework'
        verbose_name_plural = 'Structure Frameworks'
    
    def __str__(self):
        return f"{self.content_type.name} - {self.name_de or self.name}"
    
    def get_beats_as_list(self):
        """Return beats as a list of dicts for JavaScript"""
        return list(self.beats.values('name', 'name_de', 'position', 'part', 'description', 'sort_order'))


class FrameworkBeat(models.Model):
    """
    Individual beats/sections within a framework.
    Examples: "Opening Image", "Introduction", "Methods"
    """
    class Part(models.IntegerChoices):
        PART_1 = 1, 'Teil 1 / Einleitung'
        PART_2 = 2, 'Teil 2 / Hauptteil'
        PART_3 = 3, 'Teil 3 / Schluss'
    
    framework = models.ForeignKey(
        StructureFramework,
        on_delete=models.CASCADE,
        related_name='beats'
    )
    name = models.CharField(max_length=100, help_text="Beat name in English")
    name_de = models.CharField(max_length=100, blank=True, help_text="German name")
    description = models.TextField(blank=True, help_text="What should happen in this beat")
    description_de = models.TextField(blank=True, help_text="German description")
    
    # Position info
    position = models.CharField(max_length=20, default='0%', help_text="Position in story: '0-10%', '50%'")
    part = models.IntegerField(choices=Part.choices, default=Part.PART_1, help_text="Which act/part")
    sort_order = models.PositiveIntegerField(default=0)
    
    # LLM Prompts for this specific beat
    llm_prompt_template = models.TextField(blank=True, help_text="Prompt template for generating this beat")
    
    # Suggested word count for this beat
    suggested_word_percentage = models.FloatField(default=0.0, help_text="Percentage of total words")
    
    is_required = models.BooleanField(default=True, help_text="Required beat or optional")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_framework_beats'
        ordering = ['framework', 'sort_order']
        verbose_name = 'Framework Beat'
        verbose_name_plural = 'Framework Beats'
    
    def __str__(self):
        return f"{self.framework.name} - {self.name_de or self.name}"


# =============================================================================
# Idea Generation System (Projekttyp-spezifische Ideengenerierung)
# =============================================================================

class IdeaGenerationStep(models.Model):
    """
    Schritte der Ideengenerierung pro ContentType.
    Definiert die Fragen/Prompts die dem Autor gestellt werden.
    """
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='idea_steps'
    )
    
    # Step Configuration
    step_number = models.PositiveIntegerField(help_text="Reihenfolge des Schritts")
    name = models.CharField(max_length=100, help_text="Interner Name (z.B. 'core_conflict')")
    name_de = models.CharField(max_length=100, help_text="Anzeigename (z.B. 'Kernkonflikt')")
    
    # What to ask the user
    question = models.TextField(help_text="Die Hauptfrage an den User")
    question_de = models.TextField(help_text="Deutsche Version der Frage")
    
    # === KONTEXTHILFE-SYSTEM ===
    help_text_short = models.TextField(
        blank=True,
        help_text="Kurze Inline-Hilfe unter der Frage"
    )
    help_text_detailed = models.TextField(
        blank=True,
        help_text="Ausführliche Erklärung für Modal"
    )
    help_examples = models.JSONField(
        default=list,
        blank=True,
        help_text='Beispiele: ["Beispiel 1", "Beispiel 2"]'
    )
    help_tips = models.JSONField(
        default=list,
        blank=True,
        help_text='Tipps: ["Tipp 1", "Tipp 2"]'
    )
    help_common_mistakes = models.TextField(
        blank=True,
        help_text="Häufige Fehler die vermieden werden sollten"
    )
    help_video_url = models.URLField(
        blank=True,
        help_text="Optional: Link zu Tutorial-Video"
    )
    help_related_articles = models.JSONField(
        default=list,
        blank=True,
        help_text='Links zu Artikeln: [{"title": "...", "url": "..."}]'
    )
    
    # Field type for user input
    class InputType(models.TextChoices):
        TEXT = 'text', 'Kurztext (einzeilig)'
        TEXTAREA = 'textarea', 'Langtext (mehrzeilig)'
        SELECT = 'select', 'Auswahl (Dropdown)'
        MULTISELECT = 'multiselect', 'Mehrfachauswahl'
        SLIDER = 'slider', 'Skala/Slider'
        TAGS = 'tags', 'Tags/Schlagwörter'
    
    input_type = models.CharField(
        max_length=20,
        choices=InputType.choices,
        default=InputType.TEXTAREA
    )
    input_options = models.JSONField(
        default=dict,
        blank=True,
        help_text='Optionen für select/multiselect: {"options": ["A", "B", "C"]}'
    )
    input_placeholder = models.CharField(
        max_length=200,
        blank=True,
        help_text="Placeholder-Text im Eingabefeld"
    )
    input_min_length = models.PositiveIntegerField(
        default=0,
        help_text="Minimale Zeichenanzahl (0 = keine Begrenzung)"
    )
    input_max_length = models.PositiveIntegerField(
        default=0,
        help_text="Maximale Zeichenanzahl (0 = keine Begrenzung)"
    )
    
    # LLM Enhancement
    can_generate_with_ai = models.BooleanField(
        default=True,
        help_text="Kann AI diesen Schritt generieren?"
    )
    ai_prompt_template = models.TextField(
        blank=True,
        help_text="Prompt-Template für AI-Generierung (Jinja2-Syntax)"
    )
    ai_refinement_prompt = models.TextField(
        blank=True,
        help_text="Prompt für Verfeinerung basierend auf User-Feedback"
    )
    
    # Dependencies & Conditions
    depends_on_steps = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        help_text="Schritte die vorher abgeschlossen sein müssen"
    )
    show_condition = models.JSONField(
        default=dict,
        blank=True,
        help_text='Bedingung wann Schritt angezeigt wird: {"step": "genre", "value": "fantasy"}'
    )
    
    # Meta
    is_required = models.BooleanField(default=True, help_text="Pflichtfeld?")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_idea_generation_steps'
        ordering = ['content_type', 'sort_order', 'step_number']
        unique_together = ['content_type', 'name']
        verbose_name = 'Idea Generation Step'
        verbose_name_plural = 'Idea Generation Steps'
    
    def __str__(self):
        return f"{self.content_type.name} - {self.step_number}. {self.name_de}"


class IdeaSession(models.Model):
    """
    Eine Ideengenerierungs-Session für ein Projekt.
    Speichert den Gesamtzustand der Ideenfindung.
    """
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Entwurf'
        IN_PROGRESS = 'in_progress', 'In Bearbeitung'
        COMPLETED = 'completed', 'Abgeschlossen'
        ABANDONED = 'abandoned', 'Abgebrochen'
    
    # Relations
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='idea_sessions',
        null=True,
        blank=True,
        help_text="Verknüpftes Buchprojekt (optional bei neuen Projekten)"
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        related_name='idea_sessions'
    )
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='idea_sessions'
    )
    
    # Session State
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Arbeitstitel des Projekts"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    current_step = models.PositiveIntegerField(
        default=1,
        help_text="Aktueller Schritt in der Ideengenerierung"
    )
    
    # AI Summary
    idea_summary = models.TextField(
        blank=True,
        help_text="AI-generierte Zusammenfassung aller Ideen"
    )
    idea_summary_version = models.PositiveIntegerField(
        default=0,
        help_text="Version der Zusammenfassung"
    )
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_idea_sessions'
        ordering = ['-updated_at']
        verbose_name = 'Idea Session'
        verbose_name_plural = 'Idea Sessions'
    
    def __str__(self):
        return f"{self.title or 'Neue Idee'} ({self.content_type.name})"
    
    def get_progress_percentage(self):
        """Berechnet Fortschritt in Prozent"""
        total_steps = self.content_type.idea_steps.filter(is_active=True, is_required=True).count()
        if total_steps == 0:
            return 100
        completed = self.responses.filter(is_accepted=True).count()
        return int((completed / total_steps) * 100)


class IdeaResponse(models.Model):
    """
    Einzelne Antwort auf einen Ideengenerierungs-Schritt.
    Speichert User-Input und AI-Generierungen mit Versionshistorie.
    """
    class Source(models.TextChoices):
        USER = 'user', 'User-Eingabe'
        AI = 'ai', 'AI-Generiert'
        AI_REFINED = 'ai_refined', 'AI-Verfeinert'
        USER_EDITED = 'user_edited', 'User-Bearbeitet'
    
    # Relations
    session = models.ForeignKey(
        IdeaSession,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    step = models.ForeignKey(
        IdeaGenerationStep,
        on_delete=models.PROTECT,
        related_name='responses'
    )
    
    # Response Content
    content = models.TextField(help_text="Die eigentliche Antwort/Idee")
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.USER
    )
    
    # Version Control
    version = models.PositiveIntegerField(default=1)
    parent_response = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_versions',
        help_text="Vorherige Version dieser Antwort"
    )
    
    # AI Interaction
    ai_prompt_used = models.TextField(
        blank=True,
        help_text="Der verwendete Prompt für AI-Generierung"
    )
    user_feedback = models.TextField(
        blank=True,
        help_text="User-Feedback für Verfeinerung (z.B. 'Mehr Spannung')"
    )
    
    # State
    is_accepted = models.BooleanField(
        default=False,
        help_text="Hat der User diese Version akzeptiert?"
    )
    is_current = models.BooleanField(
        default=True,
        help_text="Ist dies die aktuelle Version?"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'writing_idea_responses'
        ordering = ['session', 'step__sort_order', '-version']
        verbose_name = 'Idea Response'
        verbose_name_plural = 'Idea Responses'
    
    def __str__(self):
        return f"{self.session} - {self.step.name_de} (v{self.version})"
    
    def save(self, *args, **kwargs):
        """Bei neuer Version: alte Versionen als nicht-aktuell markieren"""
        if not self.pk:  # Neue Response
            # Finde höchste Version für diesen Step in dieser Session
            existing = IdeaResponse.objects.filter(
                session=self.session,
                step=self.step
            ).order_by('-version').first()
            
            if existing:
                self.version = existing.version + 1
                self.parent_response = existing
                # Alte Version als nicht-aktuell markieren
                IdeaResponse.objects.filter(
                    session=self.session,
                    step=self.step
                ).update(is_current=False)
        
        super().save(*args, **kwargs)


__all__ = [
    # Proxy models for Writing Hub admin
    "BookProject",
    "Chapter",
    "Character",
    # Versioning
    "OutlineVersion",
    # Content Type Framework System
    "ContentType",
    "StructureFramework",
    "FrameworkBeat",
    # Idea Generation System
    "IdeaGenerationStep",
    "IdeaSession",
    "IdeaResponse",
    # Lektorats-Framework
    "LektoratsSession",
    "LektoratsFehler",
    "FigurenRegister",
    "ZeitlinienEintrag",
    "StilProfil",
    "WiederholungsAnalyse",
    # Lookup models
    "ContentRating",
    "WritingStage",
    "ArcType",
    "ImportanceLevel",
    "HandlerCategory",
    "HandlerPhase",
    "ErrorStrategy",
    "EmotionalTone",
    "ConflictLevel",
    "BeatType",
    "SceneConnectionType",
    "Scene",
    "Beat",
    "Location",
    "PlotThread",
    "SceneConnection",
    "TimelineEvent",
    "WorkflowPhaseLLMConfig",
]


# =============================================================================
# Workflow Phase LLM Configuration
# =============================================================================

class WorkflowPhaseLLMConfig(models.Model):
    """
    Configuration for which LLM to use for each workflow phase.
    Allows admins to pre-configure LLMs for different phases.
    """
    
    PHASE_CHOICES = [
        ('planning', 'Planung (Premise, Logline, Themes)'),
        ('characters', 'Charaktere'),
        ('world', 'Weltenbau'),
        ('outline', 'Outline/Struktur'),
        ('chapters', 'Kapitel schreiben'),
        ('editing', 'Lektorat'),
        ('illustration', 'Illustration'),
    ]
    
    phase = models.CharField(
        max_length=50, 
        choices=PHASE_CHOICES, 
        unique=True,
        help_text="Workflow-Phase"
    )
    llm = models.ForeignKey(
        'bfagent.Llms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workflow_phase_configs',
        help_text="Zugewiesenes LLM für diese Phase"
    )
    fallback_llm = models.ForeignKey(
        'bfagent.Llms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workflow_phase_fallbacks',
        help_text="Fallback LLM falls primäres nicht verfügbar"
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'workflow_phase_llm_config'
        verbose_name = 'Workflow Phase LLM Konfiguration'
        verbose_name_plural = 'Workflow Phase LLM Konfigurationen'
        ordering = ['phase']
    
    def __str__(self):
        llm_name = self.llm.name if self.llm else 'Nicht zugewiesen'
        return f"{self.get_phase_display()} → {llm_name}"
    
    @classmethod
    def get_llm_for_phase(cls, phase: str):
        """Get the configured LLM for a specific phase."""
        try:
            config = cls.objects.select_related('llm', 'fallback_llm').get(
                phase=phase, is_active=True
            )
            if config.llm and config.llm.is_active:
                return config.llm
            elif config.fallback_llm and config.fallback_llm.is_active:
                return config.fallback_llm
        except cls.DoesNotExist:
            pass
        return None
    
    @classmethod
    def get_llm_id_for_phase(cls, phase: str) -> int:
        """Get the configured LLM ID for a specific phase."""
        llm = cls.get_llm_for_phase(phase)
        return llm.id if llm else None


# =============================================================================
# MVP: Redaktions- und Review-System
# =============================================================================

class EditingSuggestion(models.Model):
    """
    AI-generierte Verbesserungsvorschläge für Kapitel.
    MVP für Redaktionsphase.
    """
    
    class SuggestionType(models.TextChoices):
        GRAMMAR = 'grammar', 'Grammatik'
        STYLE = 'style', 'Stil'
        CONSISTENCY = 'consistency', 'Konsistenz'
        REPETITION = 'repetition', 'Wiederholung'
        CLARITY = 'clarity', 'Klarheit'
        PACING = 'pacing', 'Tempo'
        DIALOGUE = 'dialogue', 'Dialog'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Offen'
        ACCEPTED = 'accepted', 'Angenommen'
        REJECTED = 'rejected', 'Abgelehnt'
        MODIFIED = 'modified', 'Modifiziert'
    
    chapter = models.ForeignKey(
        'bfagent.BookChapters',
        on_delete=models.CASCADE,
        related_name='editing_suggestions'
    )
    suggestion_type = models.CharField(
        max_length=50,
        choices=SuggestionType.choices,
        default=SuggestionType.STYLE
    )
    original_text = models.TextField(help_text="Originaltext aus dem Kapitel")
    suggested_text = models.TextField(help_text="Verbesserter Text")
    explanation = models.TextField(blank=True, help_text="Begründung für die Änderung")
    position_start = models.IntegerField(default=0, help_text="Startposition im Text")
    position_end = models.IntegerField(default=0, help_text="Endposition im Text")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'writing_editing_suggestions'
        verbose_name = 'Bearbeitungsvorschlag'
        verbose_name_plural = 'Bearbeitungsvorschläge'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_suggestion_type_display()}: {self.original_text[:50]}..."


class ChapterFeedback(models.Model):
    """
    Feedback von Beta-Readern oder Selbst-Review.
    MVP für Review-Phase.
    """
    
    class FeedbackType(models.TextChoices):
        POSITIVE = 'positive', '👍 Positiv'
        SUGGESTION = 'suggestion', '🔧 Verbesserung'
        QUESTION = 'question', '❓ Frage'
        BUG = 'bug', '🐛 Fehler'
        PLOT = 'plot', '📖 Handlung'
        CHARACTER = 'character', '👤 Charakter'
    
    class Status(models.TextChoices):
        OPEN = 'open', 'Offen'
        IN_PROGRESS = 'in_progress', 'In Bearbeitung'
        RESOLVED = 'resolved', 'Erledigt'
        WONT_FIX = 'wont_fix', 'Nicht umsetzen'
    
    chapter = models.ForeignKey(
        'bfagent.BookChapters',
        on_delete=models.CASCADE,
        related_name='feedbacks'
    )
    feedback_type = models.CharField(
        max_length=20,
        choices=FeedbackType.choices,
        default=FeedbackType.SUGGESTION
    )
    content = models.TextField(help_text="Feedback-Inhalt")
    text_selection = models.TextField(blank=True, help_text="Markierter Textbereich")
    position_start = models.IntegerField(default=0)
    position_end = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )
    reviewer_name = models.CharField(max_length=100, blank=True, default='Autor')
    resolution_note = models.TextField(blank=True, help_text="Notiz zur Lösung")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'writing_chapter_feedback'
        verbose_name = 'Kapitel-Feedback'
        verbose_name_plural = 'Kapitel-Feedbacks'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_feedback_type_display()}: {self.content[:50]}..."


class ProjectFeedback(models.Model):
    """
    Projekt-weites Feedback (betrifft ganzes Buch).
    Für übergreifende Themen wie Charakter-Entwicklung, Pacing, Plot-Konsistenz.
    """
    
    class FeedbackScope(models.TextChoices):
        CHARACTER = 'character', '👤 Charakter-Entwicklung'
        PACING = 'pacing', '⏱️ Pacing/Tempo'
        PLOT = 'plot', '📖 Plot/Handlung'
        STYLE = 'style', '✍️ Stil/Sprache'
        CONSISTENCY = 'consistency', '🔗 Konsistenz'
        STRUCTURE = 'structure', '🏗️ Struktur'
        OTHER = 'other', '📝 Sonstiges'
    
    class Status(models.TextChoices):
        OPEN = 'open', 'Offen'
        IN_PROGRESS = 'in_progress', 'In Bearbeitung'
        RESOLVED = 'resolved', 'Erledigt'
        WONT_FIX = 'wont_fix', 'Nicht umsetzen'
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='project_feedbacks'
    )
    scope = models.CharField(
        max_length=20,
        choices=FeedbackScope.choices,
        default=FeedbackScope.OTHER
    )
    title = models.CharField(max_length=200, help_text="Kurze Zusammenfassung")
    content = models.TextField(help_text="Ausführliche Beschreibung")
    affected_chapters = models.ManyToManyField(
        'bfagent.BookChapters',
        blank=True,
        related_name='project_feedbacks',
        help_text="Betroffene Kapitel (optional)"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )
    reviewer_name = models.CharField(max_length=100, blank=True, default='Autor')
    resolution_note = models.TextField(blank=True, help_text="Notiz zur Lösung")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'writing_project_feedback'
        verbose_name = 'Projekt-Feedback'
        verbose_name_plural = 'Projekt-Feedbacks'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_scope_display()}: {self.title}"


class ProjectVersion(models.Model):
    """
    Snapshot des gesamten Projekts für Versionierung.
    MVP für einfache Versionsverwaltung.
    """
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_name = models.CharField(max_length=100, help_text="z.B. 'Erster Entwurf'")
    version_number = models.IntegerField(default=1)
    description = models.TextField(blank=True)
    total_words = models.IntegerField(default=0)
    total_chapters = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'writing_project_versions'
        verbose_name = 'Projekt-Version'
        verbose_name_plural = 'Projekt-Versionen'
        ordering = ['-version_number']
        unique_together = ['project', 'version_number']
    
    def __str__(self):
        return f"v{self.version_number} - {self.version_name}"


class ChapterSnapshot(models.Model):
    """
    Kapitel-Inhalt zum Zeitpunkt einer Version.
    """
    
    version = models.ForeignKey(
        ProjectVersion,
        on_delete=models.CASCADE,
        related_name='chapter_snapshots'
    )
    chapter = models.ForeignKey(
        'bfagent.BookChapters',
        on_delete=models.CASCADE,
        related_name='snapshots'
    )
    chapter_number = models.IntegerField()
    title = models.CharField(max_length=200)
    content = models.TextField()
    outline = models.TextField(blank=True)
    word_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'writing_chapter_snapshots'
        verbose_name = 'Kapitel-Snapshot'
        verbose_name_plural = 'Kapitel-Snapshots'
        ordering = ['chapter_number']
    
    def __str__(self):
        return f"Kap. {self.chapter_number}: {self.title}"


# =============================================================================
# ILLUSTRATION MODELS
# =============================================================================

class IllustrationStyle(models.Model):
    """
    Definiert den visuellen Stil für alle Bilder eines Projekts.
    Stellt Konsistenz über alle generierten Bilder sicher.
    """
    
    class StyleType(models.TextChoices):
        WATERCOLOR = 'watercolor', '🎨 Aquarell'
        DIGITAL_ART = 'digital_art', '💻 Digital Art'
        OIL_PAINTING = 'oil_painting', '🖼️ Ölgemälde'
        MANGA = 'manga', '📚 Manga/Anime'
        REALISTIC = 'realistic', '📷 Fotorealistisch'
        CARTOON = 'cartoon', '🎪 Cartoon'
        PENCIL = 'pencil', '✏️ Bleistiftzeichnung'
        CUSTOM = 'custom', '⚙️ Benutzerdefiniert'
    
    class Provider(models.TextChoices):
        DALLE3 = 'dalle3', 'DALL-E 3'
        SDXL = 'sdxl', 'Stable Diffusion XL'
        MIDJOURNEY = 'midjourney', 'Midjourney'
    
    project = models.OneToOneField(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='illustration_style'
    )
    
    # Stil-Definition
    style_type = models.CharField(
        max_length=20,
        choices=StyleType.choices,
        default=StyleType.WATERCOLOR
    )
    style_name = models.CharField(
        max_length=100,
        help_text="z.B. 'Mystischer Aquarell-Stil'"
    )
    
    # Prompt-Komponenten (werden bei JEDEM Bild verwendet)
    base_prompt = models.TextField(
        help_text="Basis-Stil-Beschreibung für alle Bilder",
        default="watercolor painting, fantasy illustration, soft edges, magical atmosphere"
    )
    negative_prompt = models.TextField(
        blank=True,
        help_text="Was vermieden werden soll",
        default="photo, realistic, 3d render, blurry, low quality"
    )
    
    # Visuelle Konsistenz
    color_palette = models.JSONField(
        default=list,
        blank=True,
        help_text="Hex-Farbcodes z.B. ['#2E5A4C', '#8B4513']"
    )
    reference_seed = models.IntegerField(
        null=True,
        blank=True,
        help_text="Seed für Reproduzierbarkeit"
    )
    
    # Provider-Einstellungen
    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.DALLE3
    )
    quality = models.CharField(
        max_length=20,
        default='hd',
        help_text="standard oder hd"
    )
    image_size = models.CharField(
        max_length=20,
        default='1024x1024',
        help_text="z.B. 1024x1024, 1792x1024"
    )
    
    # Beispielbilder für Stil-Referenz
    reference_image = models.ImageField(
        upload_to='style_references/',
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_illustration_styles'
        verbose_name = 'Illustrations-Stil'
        verbose_name_plural = 'Illustrations-Stile'
    
    def __str__(self):
        return f"{self.style_name} ({self.get_style_type_display()})"
    
    def get_full_prompt(self, scene_description: str) -> str:
        """Kombiniert Stil-Prompt mit Szenen-Beschreibung"""
        parts = [self.base_prompt]
        if scene_description:
            parts.append(scene_description)
        if self.color_palette:
            colors = ", ".join(self.color_palette[:3])
            parts.append(f"color palette: {colors}")
        return ", ".join(parts)
    
    @classmethod
    def get_preset_for_genre(cls, genre: str) -> dict:
        """Gibt Stil-Preset basierend auf Genre zurück"""
        presets = {
            'fantasy': {
                'style_type': cls.StyleType.WATERCOLOR,
                'style_name': 'Fantasy Aquarell',
                'base_prompt': 'watercolor painting, fantasy illustration, soft edges, magical atmosphere, golden light, detailed backgrounds, ethereal',
                'negative_prompt': 'photo, realistic, 3d render, blurry, modern, urban',
                'color_palette': ['#2E5A4C', '#8B4513', '#FFD700', '#4A0080'],
            },
            'sci-fi': {
                'style_type': cls.StyleType.DIGITAL_ART,
                'style_name': 'Sci-Fi Digital',
                'base_prompt': 'digital art, sci-fi illustration, neon lighting, futuristic, clean lines, cyberpunk aesthetic, high tech',
                'negative_prompt': 'fantasy, medieval, nature, organic, hand-drawn',
                'color_palette': ['#00FFFF', '#FF00FF', '#0A0A2A', '#00FF00'],
            },
            'krimi': {
                'style_type': cls.StyleType.REALISTIC,
                'style_name': 'Noir Krimi',
                'base_prompt': 'noir style, high contrast, dramatic shadows, moody lighting, gritty atmosphere, cinematic',
                'negative_prompt': 'colorful, bright, cheerful, cartoon, fantasy',
                'color_palette': ['#1A1A1A', '#8B0000', '#C0C0C0'],
            },
            'kinderbuch': {
                'style_type': cls.StyleType.CARTOON,
                'style_name': 'Kinderbuch Illustration',
                'base_prompt': "children's book illustration, colorful, friendly, rounded shapes, soft colors, whimsical, cheerful",
                'negative_prompt': 'scary, dark, realistic, violent, complex',
                'color_palette': ['#FFB6C1', '#87CEEB', '#98FB98', '#FFD700'],
            },
            'roman': {
                'style_type': cls.StyleType.OIL_PAINTING,
                'style_name': 'Klassisches Ölgemälde',
                'base_prompt': 'oil painting style, classical composition, rich colors, dramatic lighting, emotional depth, Renaissance influence',
                'negative_prompt': 'cartoon, anime, flat colors, digital, modern',
                'color_palette': ['#8B4513', '#2F4F4F', '#800020', '#DAA520'],
            },
            'horror': {
                'style_type': cls.StyleType.DIGITAL_ART,
                'style_name': 'Dark Fantasy',
                'base_prompt': 'dark fantasy art, gothic, moody lighting, desaturated colors, ominous atmosphere, detailed',
                'negative_prompt': 'bright, cheerful, colorful, cartoon, cute',
                'color_palette': ['#1C1C1C', '#4A0000', '#2D2D2D', '#483D8B'],
            },
        }
        return presets.get(genre.lower(), presets['fantasy'])


class IllustrationStyleTemplate(models.Model):
    """
    Wiederverwendbare Illustrations-Stil-Vorlage.
    Kann gespeichert und verschiedenen Projekten zugewiesen werden.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Name der Vorlage")
    description = models.TextField(blank=True, help_text="Beschreibung des Stils")
    
    # Stil-Definition (gleiche Felder wie IllustrationStyle)
    style_type = models.CharField(
        max_length=20,
        choices=IllustrationStyle.StyleType.choices,
        default=IllustrationStyle.StyleType.WATERCOLOR
    )
    base_prompt = models.TextField(
        help_text="Basis-Stil-Beschreibung für alle Bilder",
        default="watercolor painting, fantasy illustration, soft edges, magical atmosphere"
    )
    negative_prompt = models.TextField(
        blank=True,
        help_text="Was vermieden werden soll",
        default="photo, realistic, 3d render, blurry, low quality"
    )
    color_palette = models.JSONField(
        default=list,
        blank=True,
        help_text="Hex-Farbcodes z.B. ['#2E5A4C', '#8B4513']"
    )
    
    # Provider-Einstellungen
    provider = models.CharField(
        max_length=20,
        choices=IllustrationStyle.Provider.choices,
        default=IllustrationStyle.Provider.DALLE3
    )
    quality = models.CharField(max_length=20, default='hd')
    image_size = models.CharField(max_length=20, default='1024x1024')
    
    # Referenzbild
    reference_image = models.ImageField(
        upload_to='style_templates/',
        blank=True,
        null=True
    )
    
    # Meta
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    is_public = models.BooleanField(default=False, help_text="Für alle Benutzer sichtbar")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_illustration_style_templates'
        verbose_name = 'Illustrations-Stil-Vorlage'
        verbose_name_plural = 'Illustrations-Stil-Vorlagen'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_style_type_display()})"
    
    def apply_to_project(self, project):
        """Wendet diese Vorlage auf ein Projekt an"""
        style, created = IllustrationStyle.objects.get_or_create(project=project)
        style.style_type = self.style_type
        style.style_name = self.name
        style.base_prompt = self.base_prompt
        style.negative_prompt = self.negative_prompt
        style.color_palette = self.color_palette
        style.provider = self.provider
        style.quality = self.quality
        style.image_size = self.image_size
        if self.reference_image:
            style.reference_image = self.reference_image
        style.save()
        return style


class ChapterIllustration(models.Model):
    """
    Ein generiertes Bild für ein Kapitel.
    Verwendet den Stil des Projekts für Konsistenz.
    """
    
    class Position(models.TextChoices):
        HEADER = 'header', '📖 Kapitel-Header'
        SCENE = 'scene', '🎬 Szene'
        CHARACTER = 'character', '👤 Charakter'
        LOCATION = 'location', '🏰 Ort'
        ENDING = 'ending', '🔚 Kapitel-Ende'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ausstehend'
        ANALYZING = 'analyzing', 'Wird analysiert'
        GENERATING = 'generating', 'Wird generiert'
        COMPLETED = 'completed', 'Fertig'
        FAILED = 'failed', 'Fehlgeschlagen'
        REJECTED = 'rejected', 'Abgelehnt'
    
    chapter = models.ForeignKey(
        'bfagent.BookChapters',
        on_delete=models.CASCADE,
        related_name='chapter_illustrations'
    )
    position = models.CharField(
        max_length=20,
        choices=Position.choices,
        default=Position.HEADER
    )
    position_index = models.IntegerField(
        default=0,
        help_text="Für mehrere Bilder pro Position"
    )
    
    # Szenen-Kontext
    scene_description = models.TextField(
        help_text="Beschreibung der Szene für die Bildgenerierung"
    )
    scene_text_excerpt = models.TextField(
        blank=True,
        help_text="Textausschnitt aus dem Kapitel"
    )
    
    # Generierung
    full_prompt = models.TextField(
        blank=True,
        help_text="Vollständiger Prompt inkl. Stil"
    )
    seed_used = models.IntegerField(null=True, blank=True)
    
    # Ergebnis
    image = models.ImageField(
        upload_to='chapter_illustrations/',
        blank=True,
        null=True
    )
    image_url = models.URLField(
        blank=True,
        help_text="URL zum generierten Bild (DALL-E)"
    )
    thumbnail = models.ImageField(
        upload_to='chapter_illustrations/thumbs/',
        blank=True,
        null=True
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    error_message = models.TextField(blank=True)
    
    is_selected = models.BooleanField(
        default=False,
        help_text="Ausgewählt für Verwendung im Buch"
    )
    
    # Abbildungstext (Caption)
    caption = models.TextField(
        blank=True,
        help_text="Abbildungstext/Caption für das Bild"
    )
    
    # Metadaten
    generation_cost = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=0,
        help_text="Kosten in USD"
    )
    generation_time_seconds = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_chapter_illustrations'
        verbose_name = 'Kapitel-Illustration'
        verbose_name_plural = 'Kapitel-Illustrationen'
        ordering = ['chapter__chapter_number', 'position', 'position_index']
    
    def __str__(self):
        return f"Kap. {self.chapter.chapter_number} - {self.get_position_display()}"
    
    def generate_prompt(self) -> str:
        """Generiert den vollständigen Prompt mit Projekt-Stil"""
        try:
            style = self.chapter.project.illustration_style
            self.full_prompt = style.get_full_prompt(self.scene_description)
            return self.full_prompt
        except IllustrationStyle.DoesNotExist:
            self.full_prompt = self.scene_description
            return self.full_prompt


class ChapterSceneAnalysis(models.Model):
    """
    Speichert LLM-Analyse eines Kapitels für inhaltsbasierte Bildgenerierung.
    
    Die Analyse extrahiert visuelle Szenen aus dem Kapitelinhalt,
    identifiziert Charaktere, Orte und Stimmungen für optimale Prompts.
    """
    
    chapter = models.OneToOneField(
        'bfagent.BookChapters',
        on_delete=models.CASCADE,
        related_name='scene_analysis'
    )
    
    # Analysierte Szenen (JSON Array)
    # Format: [
    #   {
    #     "title": "Kurzer Titel",
    #     "description": "Visuelle Beschreibung...",
    #     "characters": ["Name1", "Name2"],
    #     "character_actions": {"Name1": "steht am Fenster..."},
    #     "location": "Ort-Beschreibung",
    #     "time_of_day": "night",
    #     "lighting": "Mondlicht",
    #     "mood": "mysterious",
    #     "visual_elements": ["brennende Kerze", "offenes Buch"],
    #     "composition_suggestion": "Wide shot..."
    #   }
    # ]
    scenes = models.JSONField(default=list)
    
    # Beste Szene für Illustration
    best_scene_index = models.IntegerField(default=0)
    best_scene_reason = models.TextField(blank=True)
    
    # Gesamt-Atmosphäre des Kapitels
    overall_color_mood = models.CharField(max_length=200, blank=True)
    chapter_atmosphere = models.CharField(max_length=200, blank=True)
    
    # Analyse-Metadaten
    analysis_model = models.CharField(
        max_length=50,
        default='gpt-4o',
        help_text="LLM verwendet für Analyse"
    )
    analysis_version = models.IntegerField(default=1)
    analysis_tokens_used = models.IntegerField(default=0)
    
    # Content-Hash für Invalidierung bei Kapitel-Änderung
    content_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA256 des Kapitelinhalts"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_chapter_scene_analysis'
        verbose_name = 'Kapitel-Szenenanalyse'
        verbose_name_plural = 'Kapitel-Szenenanalysen'
    
    def __str__(self):
        return f"Analyse: {self.chapter.title} ({len(self.scenes)} Szenen)"
    
    def get_scene(self, index: int = 0) -> dict:
        """Gibt eine bestimmte Szene zurück."""
        if 0 <= index < len(self.scenes):
            return self.scenes[index]
        return {}
    
    def get_best_scene(self) -> dict:
        """Gibt die beste Szene für Illustration zurück."""
        return self.get_scene(self.best_scene_index)
    
    def is_valid(self) -> bool:
        """Prüft ob Analyse noch gültig ist (Content nicht geändert)."""
        if not self.chapter.content:
            return False
        current_hash = self.compute_content_hash(self.chapter.content)
        return current_hash == self.content_hash
    
    @classmethod
    def strip_images(cls, content: str) -> str:
        """Entfernt Bild-Markdown aus dem Inhalt für Hash-Berechnung."""
        import re
        # Remove markdown images: ![alt](url)
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
        # Remove extra blank lines created by removal
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content.strip()
    
    @classmethod
    def compute_content_hash(cls, content: str) -> str:
        """Berechnet Hash für Kapitelinhalt (ohne Bilder)."""
        import hashlib
        # Strip images before hashing so inserted images don't invalidate analysis
        clean_content = cls.strip_images(content)
        return hashlib.sha256(clean_content.encode('utf-8')).hexdigest()
