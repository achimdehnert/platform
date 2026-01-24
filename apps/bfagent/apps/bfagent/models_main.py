"""
Django models for BF Agent - Book Factory Agent Management System
Generated from existing SQLite database with Django 5.2 LTS features
"""

import uuid
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.urls import reverse
from django.utils import timezone
from PIL import Image as PILImage

# Import Context Enrichment Models
from .models_context_enrichment import ContextEnrichmentLog, ContextSchema, ContextSource

# Import Domain Models for Multi-Hub Framework
from .models_domains import DomainArt, DomainPhase, DomainType
from .models_feature_documents import FeatureDocument, FeatureDocumentKeyword

# Import Handler System Models
from .models_handlers import ActionHandler, Handler, HandlerExecution

# Import Illustration System Models
from .models_illustration import (
    AIProvider,
    ArtStyle,
    IllustrationImage,
    ImageGenerationBatch,
    ImageStatus,
    ImageStyleProfile,
    ImageType,
)

# Import Component Registry Models
from .models_registry import (
    ComponentChangeLog,
    ComponentRegistry,
    ComponentStatus,
    ComponentType,
    ComponentUsageLog,
    MigrationConflict,
    MigrationRegistry,
)

# Import Review System Models
from .models_review import ChapterRating, Comment, ReviewParticipant, ReviewRound

# Import Testing & Requirements Models
from .models_testing import (
    RequirementTestLink,
    TestBug,
    TestCase,
    TestCoverageReport,
    TestExecution,
    TestLog,
    TestRequirement,
    TestScreenshot,
    TestSession,
)
from .utils.crud_config import CRUDConfigBase, CRUDConfigMixin

# Export all models for easy imports
__all__ = [
    # Core Models
    "BookProjects",
    "BookChapters",
    "BookTypes",
    "BookTypePhase",
    "Characters",
    "Worlds",
    "Agents",
    "AgentType",
    "AgentAction",
    "AgentExecutions",
    "AgentArtifacts",
    "Llms",
    # Workflow Models
    "WorkflowPhase",
    "WorkflowTemplate",
    "WorkflowPhaseStep",
    "PhaseAgentConfig",
    "PhaseActionConfig",
    "ProjectPhaseHistory",
    # Prompt Models
    "PromptTemplate",
    "PromptTemplateLegacy",
    "PromptExecution",
    "PromptTemplateTest",
    "ActionTemplate",
    # Story Models
    "StoryArc",
    "PlotPoint",
    "StoryBible",
    "StoryStrand",
    "StoryCharacter",
    "StoryChapter",
    "ChapterBeat",
    # Field Models
    "FieldGroup",
    "FieldDefinition",
    "ProjectFieldValue",
    "FieldValueHistory",
    "FieldTemplate",
    "TemplateField",
    "FieldUsage",
    # Master Data
    "Genre",
    "TargetAudience",
    "WritingStatus",
    # GraphQL
    "GraphQLOperation",
    "QueryPerformanceLog",
    # Enrichment
    "EnrichmentResponse",
    # Component Registry
    "ComponentRegistry",
    "ComponentStatus",
    "ComponentType",
    "ComponentUsageLog",
    "ComponentChangeLog",
    "MigrationRegistry",
    "MigrationConflict",
    # Handlers
    "Handler",
    "ActionHandler",
    "HandlerExecution",
    # Context Enrichment
    "ContextSchema",
    "ContextSource",
    "ContextEnrichmentLog",
    # Review System
    "ReviewRound",
    "ReviewParticipant",
    "Comment",
    "ChapterRating",
    # Illustration System
    "ImageStyleProfile",
    "GeneratedImage",
    "ImageGenerationBatch",
    "ArtStyle",
    "ImageType",
    "AIProvider",
    "ImageStatus",
    # Testing & Requirements
    "TestRequirement",
    "TestCase",
    "RequirementTestLink",
    "TestExecution",
    "TestSession",
    "TestLog",
    "TestScreenshot",
    "TestBug",
    "TestCoverageReport",
    # Domain Models for Multi-Hub Framework
    "DomainArt",
    "DomainType",
    "DomainPhase",
    # Feature Documents
    "FeatureDocument",
    "FeatureDocumentKeyword",
]


class BookProjects(models.Model, CRUDConfigMixin):
    """Main book project model - central entity for all book-related data"""

    # Owner
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="book_projects",
        null=True,  # Temporarily nullable for migration
        blank=True,
        help_text="Project owner",
    )

    title = models.CharField(max_length=500)
    genre = models.CharField(max_length=200)
    content_rating = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    tagline = models.TextField(blank=True, null=True)
    target_word_count = models.PositiveIntegerField()
    current_word_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=50)
    deadline = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    story_premise = models.TextField(blank=True, null=True)
    target_audience = models.CharField(max_length=100, blank=True, null=True)
    story_themes = models.TextField(blank=True, null=True)
    setting_time = models.TextField(blank=True, null=True)
    setting_location = models.TextField(blank=True, null=True)
    atmosphere_tone = models.TextField(blank=True, null=True)
    main_conflict = models.TextField(blank=True, null=True)
    stakes = models.TextField(blank=True, null=True)
    protagonist_concept = models.TextField(blank=True, null=True)
    antagonist_concept = models.TextField(blank=True, null=True)
    inspiration_sources = models.TextField(blank=True, null=True)
    unique_elements = models.TextField(
        blank=True, null=True
    )  # Changed from CharField(500) to TextField
    genre_settings = models.TextField(
        blank=True, null=True
    )  # Changed from CharField(500) to TextField

    # Book Type Integration
    book_type = models.ForeignKey(
        "BookTypes",
        on_delete=models.PROTECT,
        related_name="projects",
        help_text="Type of book (Novel, Short Story, etc.) - Required",
    )

    # Owner & Security
    owner = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="owned_projects",
        help_text="Project owner - required for authorization",
        null=True,  # Allow null for existing projects
        blank=True,
    )

    # Workflow Engine Integration
    workflow_template = models.ForeignKey(
        "WorkflowTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        help_text="Workflow template (auto-set from book_type default)",
    )
    current_phase_step = models.ForeignKey(
        "WorkflowPhaseStep",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_projects",
        help_text="Current phase step in workflow",
    )
    
    # Figure/Illustration Settings
    class FigureNumberingStyle(models.TextChoices):
        GLOBAL = 'global', 'Global (Abb. 1, 2, 3...)'
        PER_CHAPTER = 'per_chapter', 'Pro Kapitel (Abb. 1.1, 1.2, 2.1...)'
    
    figure_numbering_style = models.CharField(
        max_length=20,
        choices=FigureNumberingStyle.choices,
        default=FigureNumberingStyle.GLOBAL,
        help_text="Nummerierungsstil für Abbildungen"
    )
    include_figure_index = models.BooleanField(
        default=True,
        help_text="Abbildungsverzeichnis am Ende generieren"
    )
    
    # Book Series Integration (for multi-book universes)
    series = models.ForeignKey(
        'writing_hub.BookSeries',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='projects',
        help_text="Buchreihe/Universe, zu der dieses Projekt gehört"
    )
    series_order = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Position in der Reihe (Band 1, 2, 3...)"
    )
    
    # =========================================================================
    # IMPORT FRAMEWORK V2 - Agent-Ready Project Definition
    # =========================================================================
    
    # Project Definition XML (für Multi-Agenten-Systeme)
    project_definition_xml = models.TextField(
        blank=True, 
        null=True,
        help_text="Agent-Ready Project Definition XML für LangGraph etc."
    )
    
    # Outline-Integration
    outline_template_code = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Code des verwendeten Outline-Templates"
    )
    
    # Erweiterte Story-Metadaten
    logline = models.TextField(
        blank=True, 
        null=True,
        help_text="Ein-Satz-Zusammenfassung der Geschichte"
    )
    central_question = models.TextField(
        blank=True, 
        null=True,
        help_text="Die thematische Kernfrage des Werks"
    )
    
    # Stil-Metadaten
    narrative_voice = models.TextField(
        blank=True, 
        null=True,
        help_text="Beschreibung der Erzählstimme"
    )
    prose_style = models.TextField(
        blank=True, 
        null=True,
        help_text="Beschreibung des Prosa-Stils"
    )
    pacing_style = models.TextField(
        blank=True, 
        null=True,
        help_text="Pacing/Tempo-Stil (straff, gemächlich, etc.)"
    )
    dialogue_style = models.TextField(
        blank=True, 
        null=True,
        help_text="Beschreibung des Dialog-Stils"
    )
    comparable_titles = models.TextField(
        blank=True, 
        null=True,
        help_text="Vergleichbare Bücher/Autoren (JSON oder kommasepariert)"
    )
    
    # Genre-spezifische Felder
    spice_level = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Explizitäts-Level für Romance (none, low, medium, high)"
    )
    content_warnings = models.TextField(
        blank=True, 
        null=True,
        help_text="Content Warnings/Trigger Warnings"
    )
    
    # Serien-Kontext
    series_arc = models.TextField(
        blank=True, 
        null=True,
        help_text="Übergreifender Serien-Arc (für mehrbändige Werke)"
    )
    threads_to_continue = models.TextField(
        blank=True, 
        null=True,
        help_text="Offene Handlungsstränge für Folgebände (JSON)"
    )
    
    # Konsistenz-Regeln
    consistency_rules = models.TextField(
        blank=True, 
        null=True,
        help_text="Projekt-spezifische Konsistenz-Regeln (JSON)"
    )
    forbidden_elements = models.TextField(
        blank=True, 
        null=True,
        help_text="Was NICHT im Buch vorkommen darf (JSON)"
    )
    required_elements = models.TextField(
        blank=True, 
        null=True,
        help_text="Was im Buch vorkommen MUSS (JSON)"
    )
    agent_instructions = models.TextField(
        blank=True, 
        null=True,
        help_text="Spezifische Anweisungen für Writing-Agents"
    )

    class Meta:
        managed = True
        db_table = "book_projects"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.genre})"

    def get_absolute_url(self):
        return reverse("bfagent:project-detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        """Auto-set workflow_template from book_type default if not explicitly set"""
        is_new = self.pk is None

        # Only auto-set workflow if:
        # 1. book_type is set
        # 2. workflow_template is not set
        # 3. This is not an explicit workflow override
        if self.book_type and not self.workflow_template:
            default_workflow = self.book_type.workflows.filter(
                is_default=True, is_active=True
            ).first()
            if default_workflow:
                self.workflow_template = default_workflow

        super().save(*args, **kwargs)

        # Auto-create chapters for Essay booktype
        if is_new and self.book_type and self.book_type.name == "Essay":
            self._create_essay_chapters()

    def _create_essay_chapters(self):
        """Create 3 chapters for Essay booktype: Introduction, Body, Conclusion"""
        import json

        try:
            # Parse configuration from booktype
            config = (
                json.loads(self.book_type.configuration) if self.book_type.configuration else {}
            )
            structure = config.get("structure", [])

            # Create chapters based on structure
            for chapter_data in structure:
                BookChapters.objects.create(
                    project=self,
                    chapter_number=chapter_data.get("order", 1),
                    title=chapter_data.get("name", f"Chapter {chapter_data.get('order', 1)}"),
                    target_word_count=chapter_data.get("target_words", 150),
                    outline=chapter_data.get(
                        "purpose", ""
                    ),  # Use 'outline' instead of 'description'
                    writing_stage="planning",
                    status="draft",
                )
        except Exception as e:
            # Log error but don't fail book creation
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create essay chapters: {e}")

    @property
    def current_phase(self):
        """Get current workflow phase from history"""
        latest = self.phase_history.filter(exited_at__isnull=True).first()
        return latest.phase if latest else None

    @property
    def available_actions(self):
        """Get allowed agent actions for current phase"""
        if not self.current_phase:
            return []
        # PhaseActionConfig defined later in this file
        return self.current_phase.allowed_actions.all().order_by("order")

    class CRUDConfig(CRUDConfigBase):
        """CRUD configuration for BookProjects - Zero Hardcoding approach"""

        # List View Configuration
        list_display = ["title", "book_type", "genre", "status", "current_word_count", "created_at"]
        list_filters = ["book_type", "genre", "status", "content_rating", "target_audience"]
        search_fields = ["title", "description", "story_premise", "tagline"]
        ordering = ["-updated_at", "-created_at"]
        per_page = 12

        # Form Layout - Organized by logical sections
        form_layout = {
            "Basic Information": ["title", "book_type", "genre", "content_rating", "tagline"],
            "Story Foundation": ["description", "story_premise", "target_audience", "story_themes"],
            "World Building": ["setting_time", "setting_location", "atmosphere_tone"],
            "Plot Structure": [
                "main_conflict",
                "stakes",
                "protagonist_concept",
                "antagonist_concept",
            ],
            "Creative Elements": ["inspiration_sources", "unique_elements", "genre_settings"],
            "Project Management": ["status", "target_word_count", "deadline"],
        }

        # HTMX Configuration
        htmx_config = {
            "auto_save": True,
            "inline_edit": ["title", "status", "tagline"],
            "modal_edit": ["description", "story_premise", "main_conflict"],
            "live_search": True,
            "pagination_htmx": True,
            "loading_indicators": True,
            "auto_save_interval": 30,  # seconds
        }

        # Action Buttons
        actions = {
            "duplicate": {
                "label": "Duplicate Project",
                "icon": "copy",
                "confirm": False,
                "modal": False,
            },
            "archive": {
                "label": "Archive Project",
                "icon": "archive",
                "confirm": True,
                "confirm_text": "Are you sure you want to archive this project?",
            },
            "export": {
                "label": "Export Project",
                "icon": "download",
                "confirm": False,
                "modal": True,
            },
            "enrich": {
                "label": "AI Enrichment",
                "icon": "sparkles",
                "confirm": False,
                "modal": True,
                "primary": True,
            },
        }

        # UI Configuration
        ui_config = {
            "card_view": True,
            "table_view": True,
            "default_view": "card",
            "show_stats": True,
            "show_filters": True,
            "show_search": True,
            "stats_fields": ["current_word_count", "target_word_count", "status"],
            "card_preview_fields": ["description", "story_premise"],
            "card_meta_fields": ["genre", "target_audience", "updated_at"],
        }


class AgentType(models.Model):
    """
    Agent Type classification for different AI agent categories
    Provides centralized management and consistency for agent types
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique identifier for the agent type (e.g., 'chapter_agent')",
    )
    display_name = models.CharField(
        max_length=200, help_text="Human-readable name (e.g., 'Chapter Writing Agent')"
    )
    description = models.TextField(
        blank=True, null=True, help_text="Description of what this agent type does"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Icon class (e.g., 'bi-pencil')",
    )
    color = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Color code for UI (e.g., '#007bff')",
    )
    is_active = models.BooleanField(default=True, help_text="Whether this type is active")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "agent_types"
        ordering = ["display_name"]
        verbose_name = "Agent Type"
        verbose_name_plural = "Agent Types"

    def __str__(self):
        return self.display_name

    class CRUDConfig(CRUDConfigBase):
        """CRUD configuration for AgentType"""

        list_display = ["display_name", "name", "is_active", "updated_at"]
        list_filters = ["is_active"]
        search_fields = ["name", "display_name", "description"]
        ordering = ["display_name"]
        form_fields = [
            "name",
            "display_name",
            "description",
            "icon",
            "color",
            "is_active",
        ]
        detail_sections = {
            "Basic Info": ["name", "display_name", "description"],
            "UI Settings": ["icon", "color"],
            "Status": ["is_active"],
            "Timestamps": ["created_at", "updated_at"],
        }


class Agents(models.Model):
    """AI Agents for book development tasks"""

    name = models.CharField(max_length=200)
    # Temporarily CharField to match current DB state
    agent_type = models.CharField(max_length=100)
    status = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    system_prompt = models.TextField()
    instructions = models.TextField(blank=True, null=True)
    llm_model_id = models.PositiveIntegerField(blank=True, null=True)
    creativity_level = models.DecimalField(max_digits=3, decimal_places=2, default=0.7)
    consistency_weight = models.DecimalField(max_digits=3, decimal_places=2, default=0.5)
    total_requests = models.PositiveIntegerField(default=0)
    successful_requests = models.PositiveIntegerField(default=0)
    average_response_time = models.DecimalField(max_digits=8, decimal_places=3, default=0.0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(blank=True, null=True)

    # Active Prompt Template
    active_prompt = models.ForeignKey(
        "PromptTemplateLegacy",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_for_agents",
        help_text="Currently active prompt template for this agent",
    )

    class Meta:
        managed = True
        db_table = "agents"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.agent_type})"

    @property
    def success_rate(self):
        if self.total_requests > 0:
            return round((self.successful_requests / self.total_requests) * 100, 2)
        return 0.0

    class CRUDConfig(CRUDConfigBase):
        """CRUD configuration for Agents - Zero Hardcoding approach"""

        list_display = ["name", "agent_type", "status", "success_rate", "last_used_at"]
        list_filters = ["agent_type", "status"]
        search_fields = ["name", "description", "system_prompt"]
        ordering = ["-last_used_at", "name"]
        per_page = 20

        form_layout = {
            "Basic Information": ["name", "agent_type", "status", "description"],
            "Configuration": [
                "system_prompt",
                "instructions",
                "llm_model_id",
                "active_prompt",
                "creativity_level",
                "consistency_weight",
            ],
            "Performance Metrics": [
                "total_requests",
                "successful_requests",
                "average_response_time",
            ],
        }

        htmx_config = {
            "auto_save": True,
            "inline_edit": ["name", "status"],
            "modal_edit": ["system_prompt", "instructions"],
            "live_search": True,
        }

        actions = {
            "test_agent": {"label": "Test Agent", "icon": "play-circle", "confirm": False},
            "reset_metrics": {
                "label": "Reset Metrics",
                "icon": "arrow-clockwise",
                "confirm": True,
                "confirm_text": "Reset all performance metrics?",
            },
        }


class BookChapters(models.Model):
    """Enhanced chapters with storyline integration and AI assistance"""

    # EXISTING FIELDS (preserved for compatibility)
    project = models.ForeignKey(BookProjects, on_delete=models.CASCADE, related_name="chapters")
    title = models.CharField(max_length=300)
    summary = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    chapter_number = models.PositiveIntegerField()
    status = models.CharField(max_length=50)
    word_count = models.PositiveIntegerField(default=0)
    target_word_count = models.PositiveIntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    outline = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # PHASE 1A: Enhanced Writing Features (Non-Breaking Extensions)
    writing_stage = models.CharField(
        max_length=50,
        default="planning",
        choices=[
            ("planning", "Planning"),
            ("outlining", "Outlining"),
            ("drafting", "Drafting"),
            ("revising", "Revising"),
            ("editing", "Editing"),
            ("completed", "Completed"),
        ],
        help_text="Current writing stage of the chapter",
    )

    # Content tracking and optimization
    content_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text="SHA-256 hash for change detection",
    )

    # Enhanced metadata (JSON for flexibility)
    metadata = models.JSONField(
        default=dict, blank=True, help_text="Flexible metadata storage for chapter attributes"
    )

    # AI assistance tracking
    ai_suggestions = models.JSONField(
        default=dict, blank=True, help_text="Cached AI suggestions and prompts"
    )

    # Consistency and quality metrics
    consistency_score = models.FloatField(
        default=0.0, help_text="Automated consistency score (0.0-1.0)"
    )

    # PHASE 1B: Storyline Integration (Non-Breaking Extensions)
    story_arc = models.ForeignKey(
        "StoryArc",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chapters",
        help_text="Primary story arc this chapter belongs to",
    )

    # Many-to-many relationship for plot points
    plot_points = models.ManyToManyField(
        "PlotPoint",
        blank=True,
        related_name="chapters",
        help_text="Plot points that occur in this chapter",
    )

    # Enhanced story metadata
    mood_tone = models.CharField(
        max_length=100, blank=True, null=True, help_text="Overall mood and tone of the chapter"
    )

    setting_location = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Primary location where chapter takes place",
    )

    time_period = models.CharField(
        max_length=100, blank=True, null=True, help_text="Time period or timeframe of the chapter"
    )

    # Character involvement
    featured_characters = models.ManyToManyField(
        "Characters",
        blank=True,
        related_name="featured_chapters",
        help_text="Main characters featured in this chapter",
    )

    # Character development tracking
    character_arcs = models.JSONField(
        default=dict,
        blank=True,
        help_text="Character development and arc progression in this chapter",
    )

    # PHASE 2: AI-Generated Content Fields (Separate AI Outputs)
    ai_generated_outline = models.TextField(
        blank=True,
        null=True,
        help_text="AI-generated chapter outline from Chapter Agent",
    )

    ai_generated_draft = models.TextField(
        blank=True,
        null=True,
        help_text="AI-generated chapter draft content from Chapter Agent",
    )

    ai_generated_summary = models.TextField(
        blank=True,
        null=True,
        help_text="AI-generated chapter summary from Chapter Agent",
    )

    ai_dialogue_suggestions = models.JSONField(
        default=dict,
        blank=True,
        help_text="AI-generated dialogue suggestions and character voice guidelines",
    )

    ai_prose_improvements = models.TextField(
        blank=True,
        null=True,
        help_text="AI-generated prose improvements and style suggestions",
    )

    ai_scene_expansions = models.JSONField(
        default=dict,
        blank=True,
        help_text="AI-generated scene expansions from plot points",
    )

    # AI Generation Metadata
    ai_generation_history = models.JSONField(
        default=list,
        blank=True,
        help_text="History of AI generations with timestamps and agents used",
    )

    class Meta:
        managed = True
        db_table = "book_chapters"
        ordering = ["chapter_number"]
        unique_together = ["project", "chapter_number"]
        indexes = [
            models.Index(fields=["project", "chapter_number"]),
            models.Index(fields=["writing_stage"]),
            models.Index(fields=["content_hash"]),
        ]

    def __str__(self):
        return f"Chapter {self.chapter_number}: {self.title}"

    # PHASE 1A: Enhanced Methods (Non-Breaking)
    def save(self, *args, **kwargs):
        """Enhanced save with content hash generation"""
        import hashlib

        # Generate content hash for change detection
        if self.content:
            self.content_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()

        # Auto-update word count
        if self.content:
            self.word_count = len(self.content.split())

        super().save(*args, **kwargs)

    @property
    def progress_percentage(self):
        """Calculate writing progress as percentage"""
        if not self.target_word_count:
            return 0
        return min(100, (self.word_count / self.target_word_count) * 100)

    @property
    def reading_time_minutes(self):
        """Estimate reading time in minutes (250 words per minute)"""
        if not self.word_count:
            return 0
        return max(1, round(self.word_count / 250))

    # PHASE 1A+1B: Enhanced CRUDConfig Integration (Zero-Hardcoding System)
    class CRUDConfig:
        """Chapter-specific CRUD configuration with storyline integration"""

        list_display = [
            "chapter_number",
            "title",
            "writing_stage",
            "story_arc",
            "word_count",
            "target_word_count",
            "consistency_score",
            "updated_at",
        ]
        list_filters = ["writing_stage", "project", "status", "story_arc", "mood_tone"]
        search_fields = ["title", "summary", "content", "notes", "setting_location"]

        # Enhanced form layout for chapter editing with storyline integration
        form_layout = {
            "Chapter Info": ["title", "chapter_number", "status"],
            "Storyline": ["story_arc", "plot_points", "featured_characters"],
            "Setting & Atmosphere": ["setting_location", "time_period", "mood_tone"],
            "Content": ["summary", "outline", "content"],
            "Writing Progress": ["writing_stage", "word_count", "target_word_count"],
            "Character Development": ["character_arcs"],
            "Notes & Metadata": ["notes", "metadata"],
        }

        # HTMX configuration
        htmx_config = {
            "auto_save": True,
            "auto_save_interval": 30,  # seconds
            "inline_edit": ["title", "writing_stage", "status"],
            "modal_edit": ["summary", "outline", "content"],
            "live_word_count": True,
            "consistency_check": True,
        }

        # Chapter-specific actions
        actions = {
            "generate_outline": {
                "label": "Generate AI Outline",
                "icon": "lightbulb",
                "agent_type": "chapter_agent",
                "primary": True,
            },
            "write_draft": {
                "label": "Write Chapter Draft",
                "icon": "pencil",
                "agent_type": "chapter_agent",
                "confirm": True,
            },
            "summarize": {
                "label": "Generate Summary",
                "icon": "file-text",
                "agent_type": "chapter_agent",
            },
            "check_consistency": {
                "label": "Check Consistency",
                "icon": "shield-check",
                "modal": True,
            },
            "duplicate": {"label": "Duplicate Chapter", "icon": "copy", "confirm": True},
        }


class StoryArc(models.Model, CRUDConfigMixin):
    """Story arcs for organizing chapters and plot progression"""

    project = models.ForeignKey(BookProjects, on_delete=models.CASCADE, related_name="story_arcs")
    name = models.CharField(max_length=200, help_text="Name of the story arc")
    description = models.TextField(
        blank=True, null=True, help_text="Detailed description of the arc"
    )
    arc_type = models.CharField(
        max_length=50,
        choices=[
            ("main", "Main Plot"),
            ("subplot", "Subplot"),
            ("character", "Character Arc"),
            ("romance", "Romance Arc"),
            ("mystery", "Mystery Arc"),
            ("action", "Action Arc"),
        ],
        default="main",
        help_text="Type of story arc",
    )

    # Arc progression
    start_chapter = models.PositiveIntegerField(help_text="Chapter where arc begins")
    end_chapter = models.PositiveIntegerField(
        blank=True, null=True, help_text="Chapter where arc ends"
    )

    # Arc details
    central_conflict = models.TextField(
        blank=True, null=True, help_text="Main conflict of this arc"
    )
    resolution = models.TextField(blank=True, null=True, help_text="How the arc resolves")

    # Metadata
    importance_level = models.CharField(
        max_length=20,
        choices=[
            ("critical", "Critical"),
            ("major", "Major"),
            ("minor", "Minor"),
            ("background", "Background"),
        ],
        default="major",
        help_text="Importance level of this arc",
    )

    # Progress tracking
    completion_status = models.CharField(
        max_length=20,
        choices=[
            ("planned", "Planned"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("revised", "Needs Revision"),
        ],
        default="planned",
    )

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "story_arcs"
        ordering = ["start_chapter", "importance_level"]
        unique_together = ["project", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_arc_type_display()})"

    @property
    def chapter_span(self):
        """Calculate how many chapters this arc spans"""
        if self.end_chapter:
            return self.end_chapter - self.start_chapter + 1
        return 1

    @property
    def progress_percentage(self):
        """Calculate completion percentage based on chapters"""
        if not self.end_chapter:
            return 0

        # Get chapters in this arc that are completed
        completed_chapters = self.project.chapters.filter(
            chapter_number__gte=self.start_chapter,
            chapter_number__lte=self.end_chapter,
            writing_stage="completed",
        ).count()

        total_chapters = self.chapter_span
        if total_chapters == 0:
            return 0

        return min(100, (completed_chapters / total_chapters) * 100)

    class CRUDConfig(CRUDConfigBase):
        """StoryArc CRUD configuration"""

        list_display = [
            "name",
            "arc_type",
            "start_chapter",
            "end_chapter",
            "importance_level",
            "completion_status",
            "updated_at",
        ]
        list_filters = ["arc_type", "importance_level", "completion_status", "project"]
        search_fields = ["name", "description", "central_conflict"]

        form_layout = {
            "Arc Info": ["name", "arc_type", "importance_level"],
            "Story Details": ["description", "central_conflict", "resolution"],
            "Chapter Range": ["start_chapter", "end_chapter"],
            "Progress": ["completion_status"],
        }

        htmx_config = {
            "auto_save": True,
            "auto_save_interval": 30,
            "inline_edit": ["name", "completion_status", "importance_level"],
            "modal_edit": ["description", "central_conflict", "resolution"],
            "live_progress": True,
        }

        actions = {
            "generate_plot_points": {
                "label": "Generate Plot Points",
                "icon": "diagram-3",
                "agent_type": "story_agent",
                "primary": True,
            },
            "analyze_pacing": {
                "label": "Analyze Pacing",
                "icon": "speedometer2",
                "agent_type": "story_agent",
            },
            "check_consistency": {
                "label": "Check Arc Consistency",
                "icon": "shield-check",
                "modal": True,
            },
        }


class PlotPoint(models.Model, CRUDConfigMixin):
    """Individual plot points within story arcs"""

    story_arc = models.ForeignKey(StoryArc, on_delete=models.CASCADE, related_name="plot_points")
    project = models.ForeignKey(BookProjects, on_delete=models.CASCADE, related_name="plot_points")

    # Plot point details
    name = models.CharField(max_length=200, help_text="Name/title of the plot point")
    description = models.TextField(help_text="Detailed description of what happens")

    # Positioning
    chapter_number = models.PositiveIntegerField(help_text="Chapter where this plot point occurs")
    sequence_order = models.PositiveIntegerField(
        default=1, help_text="Order within the chapter (1=first, 2=second, etc.)"
    )

    # Plot point type
    point_type = models.CharField(
        max_length=30,
        choices=[
            ("inciting_incident", "Inciting Incident"),
            ("plot_point_1", "Plot Point 1"),
            ("midpoint", "Midpoint"),
            ("plot_point_2", "Plot Point 2"),
            ("climax", "Climax"),
            ("resolution", "Resolution"),
            ("character_moment", "Character Moment"),
            ("revelation", "Revelation"),
            ("conflict", "Conflict"),
            ("twist", "Plot Twist"),
        ],
        default="character_moment",
        help_text="Type of plot point",
    )

    # Impact and connections
    emotional_impact = models.CharField(
        max_length=20,
        choices=[("high", "High Impact"), ("medium", "Medium Impact"), ("low", "Low Impact")],
        default="medium",
        help_text="Emotional impact on reader",
    )

    # Character involvement
    involved_characters = models.ManyToManyField(
        "Characters", blank=True, help_text="Characters involved in this plot point"
    )

    # Status tracking
    completion_status = models.CharField(
        max_length=20,
        choices=[
            ("planned", "Planned"),
            ("drafted", "Drafted"),
            ("completed", "Completed"),
            ("needs_revision", "Needs Revision"),
        ],
        default="planned",
    )

    # Metadata
    notes = models.TextField(blank=True, null=True, help_text="Additional notes and ideas")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "plot_points"
        ordering = ["chapter_number", "sequence_order"]
        unique_together = ["story_arc", "chapter_number", "sequence_order"]

    def __str__(self):
        return f"Ch.{self.chapter_number}: {self.name} ({self.get_point_type_display()})"

    @property
    def chapter_reference(self):
        """Get the associated chapter if it exists"""
        try:
            return self.project.chapters.get(chapter_number=self.chapter_number)
        except BookChapters.DoesNotExist:
            return None

    class CRUDConfig(CRUDConfigBase):
        """PlotPoint CRUD configuration"""

        list_display = [
            "name",
            "chapter_number",
            "point_type",
            "emotional_impact",
            "completion_status",
            "story_arc",
            "updated_at",
        ]
        list_filters = ["point_type", "emotional_impact", "completion_status", "story_arc"]
        search_fields = ["name", "description", "notes"]

        form_layout = {
            "Plot Point Info": ["name", "point_type", "emotional_impact"],
            "Positioning": ["story_arc", "chapter_number", "sequence_order"],
            "Details": ["description", "notes"],
            "Characters": ["involved_characters"],
            "Status": ["completion_status"],
        }

        htmx_config = {
            "auto_save": True,
            "auto_save_interval": 30,
            "inline_edit": ["name", "completion_status", "emotional_impact"],
            "modal_edit": ["description", "notes"],
            "character_selector": True,
        }

        actions = {
            "expand_scene": {
                "label": "Expand into Scene",
                "icon": "arrows-expand",
                "agent_type": "chapter_agent",
                "primary": True,
            },
            "analyze_impact": {
                "label": "Analyze Emotional Impact",
                "icon": "heart-pulse",
                "agent_type": "story_agent",
            },
            "check_pacing": {"label": "Check Pacing", "icon": "speedometer2", "modal": True},
        }


class Characters(models.Model):
    """Character definitions for book projects"""

    project = models.ForeignKey(BookProjects, on_delete=models.CASCADE, related_name="characters")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    role = models.CharField(max_length=100)
    age = models.PositiveIntegerField(blank=True, null=True)
    background = models.TextField(blank=True, null=True)
    personality = models.TextField(blank=True, null=True)
    appearance = models.TextField(blank=True, null=True)
    motivation = models.TextField(blank=True, null=True)
    conflict = models.TextField(blank=True, null=True)
    arc = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # =========================================================================
    # IMPORT FRAMEWORK V2 - Erweiterte Charakterfelder
    # =========================================================================
    
    # Psychologische Tiefe
    wound = models.TextField(
        blank=True, 
        null=True,
        help_text="Innere Verletzung/Trauma des Charakters"
    )
    secret = models.TextField(
        blank=True, 
        null=True,
        help_text="Verborgenes Geheimnis des Charakters"
    )
    dark_trait = models.TextField(
        blank=True, 
        null=True,
        help_text="Dunkle Seite/Schattenseite (für Dark Romance etc.)"
    )
    
    # Stärken & Schwächen (detaillierter)
    strengths = models.TextField(
        blank=True, 
        null=True,
        help_text="Hauptstärken des Charakters (JSON oder kommasepariert)"
    )
    weaknesses = models.TextField(
        blank=True, 
        null=True,
        help_text="Hauptschwächen des Charakters (JSON oder kommasepariert)"
    )
    
    # Stimme & Ausdruck
    voice_sample = models.TextField(
        blank=True, 
        null=True,
        help_text="Beispiel-Dialog, der die Stimme des Charakters zeigt"
    )
    speech_patterns = models.TextField(
        blank=True, 
        null=True,
        help_text="Sprachmuster, typische Ausdrücke, Dialekt"
    )
    
    # Beruf & Status
    occupation = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="Beruf/Tätigkeit des Charakters"
    )
    organization = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="Organisation/Firma des Charakters"
    )
    
    # Beziehungen (strukturiert)
    relationships_json = models.JSONField(
        blank=True, 
        null=True,
        help_text="Strukturierte Beziehungen: [{to: 'Name', type: 'love_interest'}]"
    )
    
    # Wichtigkeit
    importance = models.PositiveIntegerField(
        default=3,
        help_text="Wichtigkeit 1-5 (1=Protagonist, 5=Minor)"
    )
    
    # Nationalität/Herkunft
    nationality = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Nationalität des Charakters"
    )
    ethnicity = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Ethnische Herkunft des Charakters"
    )

    class Meta:
        managed = True
        db_table = "characters"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.role})"

    class CRUDConfig(CRUDConfigBase):
        """CRUD configuration for Characters - Zero Hardcoding approach"""

        list_display = ["name", "role", "age", "project", "updated_at"]
        list_filters = ["role", "project"]
        search_fields = ["name", "description", "background", "personality"]
        ordering = ["name"]
        per_page = 20

        form_layout = {
            "Basic Information": ["name", "role", "age", "project"],
            "Physical": ["appearance", "age"],
            "Psychological": ["personality", "motivation", "conflict"],
            "Story": ["background", "arc"],
            "Description": ["description"],
        }

        htmx_config = {
            "auto_save": True,
            "inline_edit": ["name", "role", "age"],
            "modal_edit": ["description", "background", "personality"],
            "live_search": True,
        }

        actions = {
            "generate_backstory": {
                "label": "Generate Backstory",
                "icon": "book",
                "agent_type": "character_agent",
            },
            "analyze_arc": {"label": "Analyze Character Arc", "icon": "graph-up"},
        }


class Worlds(models.Model, CRUDConfigMixin):
    """World definitions for book projects - multiple interconnected worlds"""

    project = models.ForeignKey(BookProjects, on_delete=models.CASCADE, related_name="worlds")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    world_type = models.CharField(
        max_length=100, default="primary"
    )  # primary, secondary, parallel, etc.
    setting_details = models.TextField(blank=True, null=True)
    geography = models.TextField(blank=True, null=True)
    culture = models.TextField(blank=True, null=True)
    technology_level = models.TextField(blank=True, null=True)
    magic_system = models.TextField(blank=True, null=True)
    politics = models.TextField(blank=True, null=True)
    history = models.TextField(blank=True, null=True)
    inhabitants = models.TextField(blank=True, null=True)
    connections = models.TextField(blank=True, null=True)  # How this world connects to others
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "worlds"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.world_type})"

    class CRUDConfig(CRUDConfigBase):
        list_display = ["name", "world_type", "project", "created_at"]
        list_filters = ["world_type", "project"]
        search_fields = ["name", "description", "setting_details"]

        form_layout = {
            "Basic Information": ["name", "world_type", "description"],
            "World Building": ["setting_details", "geography", "culture"],
            "Systems & Rules": ["technology_level", "magic_system", "politics"],
            "Background": ["history", "inhabitants"],
            "Connections": ["connections"],
        }

        htmx_config = {
            "auto_save": True,
            "inline_edit": ["name", "world_type"],
            "modal_edit": ["description", "setting_details"],
            "auto_save_interval": 30,
        }

        actions = {
            "duplicate": {"label": "Duplicate World", "icon": "copy"},
            "expand": {"label": "Expand Details", "icon": "plus-circle"},
            "connect": {"label": "Create Connections", "icon": "link", "modal": True},
        }


class BookTypes(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    complexity = models.CharField(max_length=50, blank=True, null=True)
    estimated_duration_hours = models.IntegerField(blank=True, null=True)
    target_word_count_min = models.IntegerField(blank=True, null=True)
    target_word_count_max = models.IntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    configuration = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "book_types"

    def __str__(self):
        return self.name

    class CRUDConfig(CRUDConfigBase):
        """CRUD configuration for BookTypes - Zero Hardcoding approach"""

        list_display = ["name", "complexity", "target_word_count_min", "is_active", "updated_at"]
        list_filters = ["complexity", "is_active"]
        search_fields = ["name", "description"]
        ordering = ["name"]
        per_page = 20

        form_layout = {
            "Basic Information": ["name", "description", "complexity", "is_active"],
            "Word Count Targets": ["target_word_count_min", "target_word_count_max"],
            "Time & Configuration": ["estimated_duration_hours", "configuration"],
        }

        htmx_config = {
            "auto_save": True,
            "inline_edit": ["name", "is_active"],
            "modal_edit": ["description", "configuration"],
        }

        actions = {
            "duplicate": {"label": "Duplicate Type", "icon": "copy"},
        }


class Llms(models.Model):
    """LLM configuration and usage tracking"""

    name = models.CharField(max_length=100)
    provider = models.CharField(max_length=12)
    llm_name = models.CharField(max_length=100)
    api_key = models.TextField()
    api_endpoint = models.TextField()
    max_tokens = models.IntegerField()
    temperature = models.FloatField()
    top_p = models.FloatField()
    frequency_penalty = models.FloatField()
    presence_penalty = models.FloatField()
    total_tokens_used = models.IntegerField()
    total_requests = models.IntegerField()
    total_cost = models.FloatField()
    cost_per_1k_tokens = models.FloatField()
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = True
        db_table = "llms"
        ordering = ["provider", "name"]

    def __str__(self):
        return f"{self.provider} - {self.name}"

    @property
    def cost_per_request(self):
        """Calculate average cost per request"""
        if self.total_requests > 0:
            return self.total_cost / self.total_requests
        return 0

    @property
    def avg_tokens_per_request(self):
        """Calculate average tokens per request"""
        if self.total_requests > 0:
            return self.total_tokens_used / self.total_requests
        return 0

    class CRUDConfig(CRUDConfigBase):
        """CRUD configuration for Llms - Zero Hardcoding approach"""

        list_display = ["name", "provider", "is_active", "total_requests", "total_cost"]
        list_filters = ["provider", "is_active"]
        search_fields = ["name", "provider", "llm_name"]
        ordering = ["provider", "name"]
        per_page = 15

        form_layout = {
            "Basic Information": ["name", "provider", "llm_name", "description", "is_active"],
            "API Configuration": ["api_key", "api_endpoint", "max_tokens"],
            "Generation Parameters": [
                "temperature",
                "top_p",
                "frequency_penalty",
                "presence_penalty",
            ],
            "Usage & Costs": [
                "total_tokens_used",
                "total_requests",
                "total_cost",
                "cost_per_1k_tokens",
            ],
        }

        htmx_config = {
            "auto_save": False,
            "inline_edit": ["is_active"],
            "modal_edit": ["api_key", "description"],
        }

        actions = {
            "test_connection": {"label": "Test Connection", "icon": "plug", "confirm": False},
            "reset_stats": {
                "label": "Reset Statistics",
                "icon": "arrow-clockwise",
                "confirm": True,
            },
        }


class PromptTemplateLegacy(models.Model):
    """
    LEGACY: Old simple prompt templates for agents
    NOTE: This model is deprecated. Use PromptTemplate (V2) instead.
    Kept for backward compatibility with existing data.
    """

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    template_text = models.TextField(
        help_text="Use Django template syntax: {{ project.title }}, {{ context.outline }}"
    )
    agent = models.ForeignKey(Agents, on_delete=models.CASCADE, related_name="prompts_legacy")

    # Quality Metrics
    usage_count = models.IntegerField(default=0)
    avg_quality_score = models.FloatField(default=0.0, help_text="Average rating from 1-5 stars")

    # Versioning
    version = models.IntegerField(default=1)

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "prompt_templates_legacy"
        ordering = ["-avg_quality_score", "-version"]
        unique_together = [["agent", "name", "version"]]
        verbose_name = "Prompt Template (Legacy)"
        verbose_name_plural = "Prompt Templates (Legacy)"

    def __str__(self):
        return f"[LEGACY] {self.agent.name} - {self.name} (v{self.version})"

    class CRUDConfig(CRUDConfigBase):
        """CRUD configuration for PromptTemplateLegacy - Zero Hardcoding approach"""

        list_display = ["name", "agent", "version", "avg_quality_score", "usage_count"]
        list_filters = ["agent"]
        search_fields = ["name", "description", "template_text"]
        ordering = ["-avg_quality_score", "-version"]
        per_page = 20

        form_layout = {
            "Basic Information": ["name", "description", "agent"],
            "Prompt Content": ["template_text"],
            "Metrics": ["version", "usage_count", "avg_quality_score"],
        }

        field_config = {
            "template_text": {
                "widget": "textarea",
                "help_text": "Use Django template syntax: {{ project.title }}",
            },
            "avg_quality_score": {"readonly": True},
            "usage_count": {"readonly": True},
        }


class AgentAction(models.Model):
    """
    Defines specific actions that an agent can perform
    Each action has its own prompt template and metadata
    """

    agent = models.ForeignKey(Agents, on_delete=models.CASCADE, related_name="actions")
    name = models.CharField(
        max_length=100,
        help_text="Internal action name (e.g., 'brainstorm_characters')",
    )
    display_name = models.CharField(max_length=200, help_text="User-friendly name shown in UI")
    description = models.TextField(blank=True)

    # Prompt Template for this action
    prompt_template = models.ForeignKey(
        "PromptTemplateLegacy",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actions",
        help_text="Template used when executing this action",
    )

    # Field Mapping Configuration (JSON)
    target_model = models.CharField(
        max_length=50,
        default="project",
        help_text="Target model for this action (project, chapter, character, etc.)",
    )
    target_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="List of field names this action can modify (e.g., ['outline', 'unique_elements'])",
    )

    # Metadata
    order = models.IntegerField(default=0, help_text="Display order in UI")
    is_active = models.BooleanField(default=True)

    # Usage tracking
    usage_count = models.IntegerField(default=0)
    avg_execution_time = models.FloatField(default=0.0, help_text="Average seconds")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agent_actions"
        ordering = ["agent", "order", "name"]
        unique_together = [["agent", "name"]]
        verbose_name = "Agent Action"
        verbose_name_plural = "Agent Actions"

    def __str__(self):
        return f"{self.agent.name} â†’ {self.display_name}"

    def get_absolute_url(self):
        return reverse("bfagent:agentaction-detail", kwargs={"pk": self.pk})

    # Action â†’ Template Mapping Helper Methods
    def get_recommended_templates(self):
        """Get templates recommended for this action, ordered by priority"""
        return PromptTemplate.objects.filter(action_templates__action=self).order_by(
            "-action_templates__is_default", "action_templates__order"
        )

    def get_default_template(self):
        """Get the default template for this action"""
        try:
            action_template = self.action_templates.get(is_default=True)
            return action_template.template
        except ActionTemplate.DoesNotExist:
            # Fallback to the old prompt_template field if exists
            return self.prompt_template

    @property
    def has_templates(self):
        """Check if action has any associated templates"""
        return self.action_templates.exists()

    class CRUDConfig(CRUDConfigBase):
        """CRUD configuration for AgentAction"""

        list_display = ["agent", "display_name", "is_active", "order", "usage_count"]
        list_filters = ["agent", "is_active"]
        search_fields = ["name", "display_name", "description"]
        ordering = ["agent", "order", "name"]
        per_page = 50

        form_layout = {
            "Action Details": ["agent", "name", "display_name", "description"],
            "Configuration": ["prompt_template", "order", "is_active"],
        }

        htmx_config = {
            "auto_save": False,
            "inline_edit": ["is_active", "order"],
            "modal_edit": False,
            "live_search": True,
        }


class ActionTemplate(models.Model):
    """
    M2M through table: Which templates work with which actions
    Enables smart template recommendations and A/B testing
    """

    action = models.ForeignKey(
        AgentAction, on_delete=models.CASCADE, related_name="action_templates"
    )
    template = models.ForeignKey(
        "PromptTemplateLegacy", on_delete=models.CASCADE, related_name="action_templates"
    )

    # Ordering & Defaults
    is_default = models.BooleanField(
        default=False, help_text="Is this the recommended template for this action?"
    )
    order = models.IntegerField(default=0, help_text="Display order (lower = higher priority)")

    # Quality Metrics (for later optimization)
    effectiveness_score = models.FloatField(
        null=True, blank=True, help_text="Template effectiveness (0.0-1.0)"
    )
    usage_count = models.IntegerField(default=0, help_text="How often this combination was used")

    # Metadata
    description_override = models.TextField(
        blank=True, help_text="Override template description for this action context"
    )

    # Handler Pipeline Configuration
    pipeline_config = models.JSONField(
        null=True,
        blank=True,
        help_text="Handler pipeline configuration (input, processing, output handlers) - enables plug & play action configuration",
    )

    class Meta:
        db_table = "action_templates"
        ordering = ["-is_default", "order", "template__name"]
        unique_together = [["action", "template"]]
        verbose_name = "Action Template"
        verbose_name_plural = "Action Templates"

    def __str__(self):
        default = " (DEFAULT)" if self.is_default else ""
        return f"{self.action.display_name} â†’ {self.template.name}{default}"

    def get_absolute_url(self):
        return reverse("bfagent:actiontemplate-detail", kwargs={"pk": self.pk})

    class CRUDConfig(CRUDConfigBase):
        """CRUD configuration for ActionTemplate"""

        list_display = ["action", "template", "is_default", "order", "usage_count"]
        list_filters = ["action__agent", "is_default"]
        search_fields = ["action__display_name", "template__name", "description_override"]
        ordering = ["action", "-is_default", "order"]
        per_page = 50

        form_layout = {
            "Template Assignment": ["action", "template"],
            "Configuration": ["is_default", "order"],
            "Metrics": ["effectiveness_score", "usage_count"],
            "Description": ["description_override"],
        }

        htmx_config = {
            "auto_save": False,
            "inline_edit": ["is_default", "order"],
            "modal_edit": False,
            "live_search": True,
        }


# OLD EnrichmentResponse removed - see new implementation at line ~2082
# The old version tracked prompts/responses but didn't support edit-before-apply workflow


class AgentExecutions(models.Model):
    """Track agent execution history and performance"""

    project = models.ForeignKey(BookProjects, on_delete=models.CASCADE)
    agent = models.ForeignKey(Agents, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    field_name = models.CharField(max_length=200)
    content_preview = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "agent_executions"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.agent.name} - {self.project.title} ({self.status})"

    @property
    def duration(self):
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None

    class CRUDConfig(CRUDConfigBase):
        """CRUD configuration for AgentExecutions - Zero Hardcoding approach"""

        list_display = ["agent", "project", "status", "field_name", "started_at"]
        list_filters = ["status", "agent", "project"]
        search_fields = ["field_name", "content_preview", "error_message"]
        ordering = ["-started_at"]
        per_page = 25

        form_layout = {
            "Execution Info": ["agent", "project", "status", "field_name"],
            "Content": ["content_preview"],
            "Timing": ["started_at", "completed_at"],
            "Error Details": ["error_message"],
        }

        htmx_config = {
            "auto_save": False,
            "live_search": True,
        }

        actions = {
            "retry": {"label": "Retry Execution", "icon": "arrow-repeat", "confirm": False},
        }


class AgentArtifacts(models.Model):
    """Persistent artifacts generated by agents for reuse across steps."""

    CONTENT_TYPES = (
        ("outline", "Outline"),
        ("world", "World"),
        ("conflict", "Conflict"),
        ("characters", "Characters"),
        ("concepts", "Concepts"),
        ("notes", "Notes"),
        ("generic", "Generic"),
    )

    project = models.ForeignKey(BookProjects, on_delete=models.CASCADE, related_name="artifacts")
    agent = models.ForeignKey(Agents, on_delete=models.SET_NULL, blank=True, null=True)
    action = models.CharField(max_length=100)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, default="generic")
    content = models.TextField()
    metadata = models.JSONField(blank=True, null=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "agent_artifacts"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Artifact[{self.content_type}] for {self.project.title} (action={self.action})"

    class CRUDConfig(CRUDConfigBase):
        """CRUD configuration for AgentArtifacts - Zero Hardcoding approach"""

        list_display = ["project", "agent", "content_type", "action", "version", "created_at"]
        list_filters = ["content_type", "agent", "project"]
        search_fields = ["action", "content"]
        ordering = ["-created_at"]
        per_page = 20

        form_layout = {
            "Basic Information": ["project", "agent", "action", "content_type"],
            "Content": ["content", "metadata"],
            "Versioning": ["version"],
        }

        htmx_config = {
            "auto_save": True,
            "inline_edit": ["version"],
            "modal_edit": ["content"],
        }

        actions = {
            "duplicate": {"label": "Duplicate Artifact", "icon": "copy"},
            "increment_version": {"label": "Increment Version", "icon": "plus-circle"},
        }


# GraphQL Monitoring Models
from datetime import timedelta


class GraphQLOperation(models.Model):
    """Stores GraphQL Operations for analysis"""

    OPERATION_TYPES = [
        ("query", "Query"),
        ("mutation", "Mutation"),
        ("subscription", "Subscription"),
    ]

    # Basic Information
    operation_hash = models.CharField(max_length=64, db_index=True)
    operation_name = models.CharField(max_length=255, db_index=True, null=True)
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES)
    query_string = models.TextField()

    # Performance Tracking
    execution_count = models.BigIntegerField(default=0)
    total_duration_ms = models.FloatField(default=0)
    avg_duration_ms = models.FloatField(default=0)
    min_duration_ms = models.FloatField(null=True)
    max_duration_ms = models.FloatField(null=True)

    # Usage Tracking
    first_seen = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)

    # Complexity & Analysis
    complexity_score = models.IntegerField(default=0)
    depth = models.IntegerField(default=0)
    field_count = models.IntegerField(default=0)

    # HTMX specific tracking
    htmx_request = models.BooleanField(default=False)
    htmx_target = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        managed = True
        db_table = "graphql_operations"
        indexes = [
            models.Index(fields=["-last_used", "operation_type"]),
            models.Index(fields=["-execution_count"]),
            models.Index(fields=["avg_duration_ms"]),
        ]

    def __str__(self):
        return f"{self.operation_type}: {self.operation_name or 'anonymous'}"

    class CRUDConfig(CRUDConfigBase):
        """CRUD configuration for GraphQLOperation - Zero Hardcoding approach"""

        list_display = [
            "operation_name",
            "operation_type",
            "execution_count",
            "avg_duration_ms",
            "last_used",
        ]
        list_filters = ["operation_type", "htmx_request"]
        search_fields = ["operation_name", "query_string"]
        ordering = ["-execution_count"]
        per_page = 25

        form_layout = {
            "Basic Information": ["operation_name", "operation_type", "query_string"],
            "Performance": [
                "execution_count",
                "avg_duration_ms",
                "min_duration_ms",
                "max_duration_ms",
            ],
            "Complexity": ["complexity_score", "depth", "field_count"],
            "HTMX": ["htmx_request", "htmx_target"],
        }

        htmx_config = {
            "auto_save": False,
            "live_search": True,
        }

        actions = {
            "analyze": {"label": "Analyze Performance", "icon": "graph-up"},
        }


class FieldUsage(models.Model):
    """Tracks Field-Level Usage"""

    type_name = models.CharField(max_length=100, db_index=True)
    field_name = models.CharField(max_length=100, db_index=True)
    model_name = models.CharField(max_length=100, null=True)

    # Usage Stats
    usage_count = models.BigIntegerField(default=0)
    last_used = models.DateTimeField(auto_now=True)

    # Performance
    avg_resolve_time_ms = models.FloatField(default=0)
    error_count = models.IntegerField(default=0)

    # Deprecation tracking
    is_deprecated = models.BooleanField(default=False)
    deprecation_reason = models.TextField(null=True)
    suggested_alternative = models.CharField(max_length=255, null=True)

    class Meta:
        managed = True
        db_table = "graphql_field_usage"
        unique_together = ["type_name", "field_name"]
        indexes = [
            models.Index(fields=["-usage_count"]),
            models.Index(fields=["-last_used"]),
        ]

    def __str__(self):
        return f"{self.type_name}.{self.field_name}"

    @property
    def is_unused(self) -> bool:
        """Checks if field is unused (30 days)"""
        threshold = timezone.now() - timedelta(days=30)
        return self.last_used < threshold

    class CRUDConfig(CRUDConfigBase):
        """CRUD configuration for FieldUsage - Zero Hardcoding approach"""

        list_display = [
            "type_name",
            "field_name",
            "usage_count",
            "avg_resolve_time_ms",
            "is_deprecated",
        ]
        list_filters = ["is_deprecated", "model_name"]
        search_fields = ["type_name", "field_name"]
        ordering = ["-usage_count"]
        per_page = 30

        form_layout = {
            "Field Information": ["type_name", "field_name", "model_name"],
            "Usage Statistics": ["usage_count", "avg_resolve_time_ms", "error_count"],
            "Deprecation": ["is_deprecated", "deprecation_reason", "suggested_alternative"],
        }

        htmx_config = {
            "auto_save": False,
            "live_search": True,
        }

        actions = {
            "mark_deprecated": {"label": "Mark as Deprecated", "icon": "exclamation-triangle"},
        }


class QueryPerformanceLog(models.Model):
    """Detailed Performance Logging"""

    operation = models.ForeignKey(GraphQLOperation, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # Performance Metrics
    duration_ms = models.FloatField()
    db_queries = models.IntegerField(default=0)
    db_time_ms = models.FloatField(default=0)

    # Context
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.CharField(max_length=255, null=True)

    # Errors
    has_errors = models.BooleanField(default=False)
    error_message = models.TextField(null=True)

    class Meta:
        managed = True
        db_table = "graphql_performance_logs"
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["operation", "-timestamp"]),
        ]

    def __str__(self):
        return f"Log for {self.operation} at {self.timestamp}"

    class CRUDConfig(CRUDConfigBase):
        """CRUD configuration for QueryPerformanceLog - Zero Hardcoding approach"""

        list_display = ["operation", "timestamp", "duration_ms", "db_queries", "has_errors"]
        list_filters = ["has_errors", "operation"]
        search_fields = ["error_message", "user_agent"]
        ordering = ["-timestamp"]
        per_page = 50

        form_layout = {
            "Basic Information": ["operation", "timestamp"],
            "Performance Metrics": ["duration_ms", "db_queries", "db_time_ms"],
            "Context": ["ip_address", "user_agent"],
            "Error Details": ["has_errors", "error_message"],
        }

        htmx_config = {
            "auto_save": False,
            "live_search": True,
        }

        actions = {
            "analyze_performance": {"label": "Analyze Performance", "icon": "speedometer"},
        }


# ============================================================================
# MASTER DATA MODELS - Reference Data for Dropdowns and Configuration
# ============================================================================


class Genre(models.Model):
    """
    Genre classification for books
    Master data for genre dropdown selections
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent_genre = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="subgenres"
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "genres"
        ordering = ["sort_order", "name"]
        verbose_name = "Genre"
        verbose_name_plural = "Genres"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("bfagent:genre-detail", kwargs={"pk": self.pk})

    class CRUDConfig(CRUDConfigBase):
        list_display_fields = ["name", "parent_genre", "is_active", "sort_order"]
        search_fields = ["name", "description"]
        form_fields = ["name", "description", "parent_genre", "is_active", "sort_order"]
        detail_sections = {
            "Basic Info": ["name", "description", "parent_genre"],
            "Settings": ["is_active", "sort_order"],
            "Timestamps": ["created_at", "updated_at"],
        }


class TargetAudience(models.Model):
    """
    Target audience/age groups for books
    Master data for audience dropdown selections
    """

    name = models.CharField(max_length=100, unique=True)
    age_range = models.CharField(max_length=50, blank=True, help_text="e.g., '12-18', 'Adult'")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "target_audiences"
        ordering = ["sort_order", "name"]
        verbose_name = "Target Audience"
        verbose_name_plural = "Target Audiences"

    def __str__(self):
        if self.age_range:
            return f"{self.name} ({self.age_range})"
        return self.name

    def get_absolute_url(self):
        return reverse("bfagent:targetaudience-detail", kwargs={"pk": self.pk})

    class CRUDConfig(CRUDConfigBase):
        list_display_fields = ["name", "age_range", "is_active", "sort_order"]
        search_fields = ["name", "description"]
        form_fields = ["name", "age_range", "description", "is_active", "sort_order"]
        detail_sections = {
            "Basic Info": ["name", "age_range", "description"],
            "Settings": ["is_active", "sort_order"],
            "Timestamps": ["created_at", "updated_at"],
        }


class WritingStatus(models.Model):
    """
    Project status options
    Master data for status dropdown selections with styling
    """

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=20,
        default="secondary",
        help_text="Bootstrap color: primary, success, danger, etc.",
    )
    icon = models.CharField(max_length=50, blank=True, help_text="Bootstrap icon name")
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "writing_statuses"
        ordering = ["sort_order"]
        verbose_name = "Writing Status"
        verbose_name_plural = "Writing Statuses"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("bfagent:writingstatus-detail", kwargs={"pk": self.pk})

    class CRUDConfig(CRUDConfigBase):
        list_display_fields = ["name", "color", "icon", "is_active", "sort_order"]
        search_fields = ["name", "description"]
        form_fields = ["name", "description", "color", "icon", "is_active", "sort_order"]
        detail_sections = {
            "Basic Info": ["name", "description"],
            "Styling": ["color", "icon"],
            "Settings": ["is_active", "sort_order"],
            "Timestamps": ["created_at", "updated_at"],
        }


# ============================================================================
# WORKFLOW ENGINE MODELS - Phase Management & Action Configuration
# ============================================================================


class WorkflowPhase(models.Model):
    """
    Workflow phases for book projects (Planning, Outlining, Writing, etc.)
    Master data for available project phases
    """

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Bootstrap icon name")
    color = models.CharField(max_length=20, default="primary", help_text="Bootstrap color class")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workflow_phases"
        ordering = ["name"]
        verbose_name = "Workflow Phase"
        verbose_name_plural = "Workflow Phases"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("bfagent:workflowphase-detail", kwargs={"pk": self.pk})

    class CRUDConfig(CRUDConfigBase):
        list_display_fields = ["name", "icon", "color", "is_active"]
        search_fields = ["name", "description"]
        form_fields = ["name", "description", "icon", "color", "is_active"]
        detail_sections = {
            "Basic Info": ["name", "description"],
            "Styling": ["icon", "color"],
            "Settings": ["is_active"],
            "Timestamps": ["created_at", "updated_at"],
        }


class WorkflowTemplate(models.Model):
    """
    Workflow template definition per BookType
    Defines which phases in which order for a specific book type
    """

    name = models.CharField(max_length=100)
    book_type = models.ForeignKey(BookTypes, on_delete=models.CASCADE, related_name="workflows")
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False, help_text="Default workflow for this book type")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workflow_templates"
        ordering = ["book_type", "name"]
        unique_together = [["book_type", "name"]]
        verbose_name = "Workflow Template"
        verbose_name_plural = "Workflow Templates"

    def __str__(self):
        return f"{self.book_type.name} - {self.name}"

    def get_absolute_url(self):
        return reverse("bfagent:workflowtemplate-detail", kwargs={"pk": self.pk})

    class CRUDConfig(CRUDConfigBase):
        list_display_fields = ["name", "book_type", "is_default", "is_active"]
        search_fields = ["name", "description"]
        form_fields = ["name", "book_type", "description", "is_default", "is_active"]
        detail_sections = {
            "Basic Info": ["name", "book_type", "description"],
            "Settings": ["is_default", "is_active"],
            "Timestamps": ["created_at", "updated_at"],
        }


class WorkflowPhaseStep(models.Model):
    """
    Individual step in workflow template
    Defines order and transition requirements
    """

    template = models.ForeignKey(WorkflowTemplate, on_delete=models.CASCADE, related_name="steps")
    phase = models.ForeignKey(WorkflowPhase, on_delete=models.CASCADE)
    order = models.IntegerField(help_text="Step order in workflow (1, 2, 3, ...)")

    # Transition Requirements
    required_chapters = models.IntegerField(
        default=0, help_text="Minimum chapters required to proceed to next phase"
    )
    required_characters = models.IntegerField(
        default=0, help_text="Minimum characters required to proceed"
    )
    can_skip = models.BooleanField(default=False, help_text="Can this phase be skipped?")
    can_return = models.BooleanField(
        default=True, help_text="Can return to this phase from later phases?"
    )

    class Meta:
        db_table = "workflow_phase_steps"
        ordering = ["template", "order"]
        unique_together = [["template", "order"], ["template", "phase"]]
        verbose_name = "Workflow Template Phase"
        verbose_name_plural = "Workflow Template Phases"

    def __str__(self):
        return f"{self.template.name} - Step {self.order}: {self.phase.name}"

    def get_absolute_url(self):
        return reverse("bfagent:workflowphasestep-detail", kwargs={"pk": self.pk})

    class CRUDConfig(CRUDConfigBase):
        list_display_fields = [
            "template",
            "order",
            "phase",
            "required_chapters",
            "can_skip",
        ]
        search_fields = ["template__name", "phase__name"]
        form_fields = [
            "template",
            "phase",
            "order",
            "required_chapters",
            "required_characters",
            "can_skip",
            "can_return",
        ]
        detail_sections = {
            "Step Info": ["template", "phase", "order"],
            "Requirements": ["required_chapters", "required_characters"],
            "Permissions": ["can_skip", "can_return"],
        }


class PhaseAgentConfig(models.Model):
    """
    NEW: Defines which agents are available in which workflow phase
    Uses real ForeignKey relations instead of string-based matching
    """

    phase = models.ForeignKey(WorkflowPhase, on_delete=models.CASCADE, related_name="phase_agents")
    agent = models.ForeignKey("Agents", on_delete=models.CASCADE, related_name="phase_assignments")

    # Metadata
    is_required = models.BooleanField(
        default=False, help_text="Is this agent required for this phase?"
    )
    order = models.IntegerField(default=0, help_text="Display order")
    description = models.TextField(blank=True)

    class Meta:
        db_table = "phase_agent_configs"
        ordering = ["phase", "order", "agent"]
        unique_together = [["phase", "agent"]]
        verbose_name = "Phase Agent Configuration"
        verbose_name_plural = "Phase Agent Configurations"

    def __str__(self):
        return f"{self.phase.name} â†’ {self.agent.name}"

    def get_absolute_url(self):
        return reverse("bfagent:phaseagentconfig-detail", kwargs={"pk": self.pk})

    class CRUDConfig(CRUDConfigBase):
        list_display_fields = ["phase", "agent", "is_required", "order"]
        search_fields = ["phase__name", "agent__name"]
        form_fields = ["phase", "agent", "description", "is_required", "order"]
        detail_sections = {
            "Basic Info": ["phase", "agent"],
            "Settings": ["is_required", "order", "description"],
        }


class PhaseActionConfig(models.Model):
    """
    UPDATED: Defines which agent actions are available in which phase
    Now uses proper ForeignKey to AgentAction instead of strings
    """

    phase = models.ForeignKey(WorkflowPhase, on_delete=models.CASCADE, related_name="phase_actions")
    action = models.ForeignKey(AgentAction, on_delete=models.CASCADE, related_name="phase_configs")

    # Action Metadata
    is_required = models.BooleanField(default=False, help_text="Must this action be executed?")
    order = models.IntegerField(default=0, help_text="Recommended execution order")
    description = models.TextField(blank=True)

    class Meta:
        db_table = "phase_action_configs"
        ordering = ["phase", "order", "action"]
        unique_together = [["phase", "action"]]
        verbose_name = "Phase Action Configuration"
        verbose_name_plural = "Phase Action Configurations"

    def __str__(self):
        return f"{self.phase.name} â†’ {self.action.display_name}"

    def get_absolute_url(self):
        return reverse("bfagent:phaseactionconfig-detail", kwargs={"pk": self.pk})

    class CRUDConfig(CRUDConfigBase):
        """CRUD configuration for PhaseActionConfig"""

        list_display = ["phase", "action", "is_required", "order"]
        list_filters = ["phase", "action__agent", "is_required"]
        search_fields = ["phase__name", "action__display_name", "action__name", "description"]
        ordering = ["phase", "order", "action"]
        per_page = 50

        form_layout = {
            "Phase & Action": ["phase", "action"],
            "Configuration": ["is_required", "order", "description"],
        }

        htmx_config = {
            "auto_save": False,
            "inline_edit": ["is_required", "order"],
            "modal_edit": False,
            "live_search": True,
        }


class ProjectPhaseHistory(models.Model):
    """
    Tracks which project was in which phase when
    Complete audit trail of phase transitions
    """

    project = models.ForeignKey(
        BookProjects, on_delete=models.CASCADE, related_name="phase_history"
    )
    workflow_step = models.ForeignKey(WorkflowPhaseStep, on_delete=models.CASCADE)
    phase = models.ForeignKey(WorkflowPhase, on_delete=models.CASCADE)

    # Timing
    entered_at = models.DateTimeField(default=timezone.now)
    exited_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    entered_by = models.CharField(max_length=100, blank=True, help_text="User or System")
    notes = models.TextField(blank=True)

    # Completion Metrics
    actions_completed = models.JSONField(
        default=dict, help_text="Completed actions: {agent: [actions]}"
    )
    requirements_met = models.BooleanField(default=False)

    class Meta:
        db_table = "project_phase_history"
        ordering = ["-entered_at"]
        indexes = [
            models.Index(fields=["project", "-entered_at"]),
        ]
        verbose_name = "Project Phase History"
        verbose_name_plural = "Project Phase Histories"

    def __str__(self):
        return f"{self.project.title} - {self.phase.name} ({self.entered_at.date()})"

    def get_absolute_url(self):
        return reverse("bfagent:projectphasehistory-detail", kwargs={"pk": self.pk})

    @property
    def duration(self):
        """Calculate how long project was in this phase"""
        if self.exited_at:
            return self.exited_at - self.entered_at
        return timezone.now() - self.entered_at

    class CRUDConfig(CRUDConfigBase):
        list_display_fields = [
            "project",
            "phase",
            "entered_at",
            "exited_at",
            "requirements_met",
        ]
        search_fields = ["project__title", "phase__name", "notes"]
        form_fields = [
            "project",
            "workflow_step",
            "phase",
            "entered_by",
            "notes",
            "requirements_met",
        ]
        detail_sections = {
            "Phase Info": ["project", "workflow_step", "phase"],
            "Timing": ["entered_at", "exited_at"],
            "Details": ["entered_by", "notes", "requirements_met"],
            "Metrics": ["actions_completed"],
        }


class EnrichmentResponse(models.Model):
    """
    Tracks AI-generated suggestions and their application status
    Enables editing and review before applying to project/chapter
    """

    # Source Information
    project = models.ForeignKey(
        BookProjects,
        on_delete=models.CASCADE,
        related_name="enrichment_responses",
        help_text="Project this enrichment belongs to",
    )
    agent = models.ForeignKey(
        Agents, on_delete=models.CASCADE, related_name="enrichment_responses", null=True, blank=True
    )
    action = models.ForeignKey(
        AgentAction,
        on_delete=models.CASCADE,
        related_name="enrichment_responses",
        null=True,
        blank=True,
    )
    action_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Action name (for backwards compatibility)",
    )

    # Target Information
    # NEW: Reference to FieldDefinition for dynamic fields
    target_field = models.ForeignKey(
        "FieldDefinition",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrichment_responses",
        help_text="Dynamic field definition (NEW system)",
    )

    # LEGACY: For backwards compatibility with old hardcoded fields
    target_model = models.CharField(
        max_length=50,
        default="project",
        blank=True,
        help_text="[LEGACY] Target model type (project, chapter, character, etc.)",
    )
    target_id = models.IntegerField(
        null=True, blank=True, help_text="ID of target object if not project"
    )
    field_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="[LEGACY] Field name to update (use target_field instead)",
    )

    # Content
    original_value = models.TextField(
        blank=True, default="", help_text="Original value before enrichment"
    )
    suggested_value = models.TextField(blank=True, default="", help_text="AI-generated suggestion")
    edited_value = models.TextField(
        blank=True, default="", help_text="User-edited version of suggestion"
    )

    # NEW: Multi-Field Response System
    response_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured response data with multiple fields (NEW Pipeline System)",
    )
    field_mappings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Maps response fields to model fields (NEW Pipeline System)",
    )

    # Metadata
    confidence = models.FloatField(default=0.0, help_text="AI confidence score (0.0-1.0)")
    rationale = models.TextField(blank=True, default="", help_text="Why this suggestion was made")
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Handler metadata and execution info (NEW Pipeline System)",
    )

    # LLM Performance Tracking (NEW Pipeline System)
    llm_used = models.ForeignKey(
        Llms,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrichment_responses",
        help_text="Which LLM was used to generate this response",
    )
    tokens_used = models.IntegerField(
        default=0, help_text="Total tokens consumed (prompt + completion)"
    )
    prompt_tokens = models.IntegerField(default=0, help_text="Tokens used in the prompt")
    completion_tokens = models.IntegerField(
        default=0, help_text="Tokens generated in the completion"
    )
    generation_cost = models.DecimalField(
        max_digits=10, decimal_places=4, default=0, help_text="Cost in USD for this generation"
    )
    execution_time_ms = models.IntegerField(
        default=0, help_text="Time taken to generate response in milliseconds"
    )
    quality_score = models.FloatField(
        null=True, blank=True, help_text="User-rated quality score (0.0-5.0) for benchmarking"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending Review"),
            ("edited", "Edited by User"),
            ("applied", "Applied to Project"),
            ("rejected", "Rejected"),
        ],
        default="pending",
    )
    applied_at = models.DateTimeField(null=True, blank=True)
    applied_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applied_enrichments",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "enrichment_responses"
        ordering = ["-created_at"]
        verbose_name = "Enrichment Response"
        verbose_name_plural = "Enrichment Responses"
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["agent", "action_name"]),
            models.Index(fields=["target_model", "target_id"]),
        ]

    def __str__(self):
        return f"{self.agent.name} â†’ {self.field_name} ({self.status})"

    def apply_to_target(self, user=None):
        """
        Apply the suggestion to the target model
        Supports both NEW (FieldDefinition) and LEGACY (hardcoded field_name) systems
        """
        value_to_apply = self.edited_value if self.edited_value else self.suggested_value

        # NEW SYSTEM: Use FieldDefinition
        if self.target_field:
            field_value, created = ProjectFieldValue.objects.get_or_create(
                project=self.project, field_definition=self.target_field
            )

            field_value.set_value(value_to_apply, user=user)

            # Create history entry
            FieldValueHistory.objects.create(
                field_value=field_value,
                old_value=field_value.get_value() or "",
                new_value=value_to_apply,
                changed_by=user,
                change_source="ai_enrichment",
            )

        # LEGACY SYSTEM: Direct field assignment
        else:
            if self.target_model == "project":
                target = self.project
            elif self.target_model == "chapter":
                target = BookChapters.objects.get(id=self.target_id)
            elif self.target_model == "character":
                target = Characters.objects.get(id=self.target_id)
            else:
                raise ValueError(f"Unknown target_model: {self.target_model}")

            # Validate field exists
            if not hasattr(target, self.field_name):
                raise ValueError(f"{self.target_model} does not have field '{self.field_name}'")

            # Apply the value
            setattr(target, self.field_name, value_to_apply)
            target.save()

        # Update status
        self.status = "applied"
        self.applied_at = timezone.now()
        if user:
            self.applied_by = user
        self.save()

    class CRUDConfig(CRUDConfigBase):
        list_display_fields = [
            "project",
            "agent",
            "action_name",
            "field_name",
            "status",
            "created_at",
        ]
        search_fields = [
            "project__title",
            "agent__name",
            "action_name",
            "field_name",
            "suggested_value",
        ]
        list_filter = ["status", "agent", "target_model", "created_at"]
        form_fields = [
            "project",
            "agent",
            "action_name",
            "target_model",
            "target_id",
            "field_name",
            "suggested_value",
            "edited_value",
            "confidence",
            "rationale",
            "status",
        ]
        detail_sections = {
            "Source": ["project", "agent", "action", "action_name"],
            "Target": ["target_model", "target_id", "field_name"],
            "Content": [
                "original_value",
                "suggested_value",
                "edited_value",
            ],
            "Metadata": ["confidence", "rationale", "status"],
            "Tracking": ["applied_at", "applied_by", "created_at", "updated_at"],
        }


# ============================================================================
# FLEXIBLE FIELD SYSTEM - Dynamic Custom Fields
# ============================================================================


class FieldGroup(models.Model):
    """
    Groups related fields together for better organization
    Example: "Plot Elements", "Character Details", "World Building"
    """

    name = models.CharField(
        max_length=100, unique=True, help_text="Group name (e.g., 'Plot Elements')"
    )
    display_name = models.CharField(max_length=200, help_text="Human-readable name")
    description = models.TextField(blank=True, help_text="What this group contains")
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class (e.g., 'bi-book')")
    color = models.CharField(max_length=20, blank=True, help_text="Color code for UI")
    order = models.IntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "field_groups"
        ordering = ["order", "display_name"]
        verbose_name = "Field Group"
        verbose_name_plural = "Field Groups"

    def __str__(self):
        return self.display_name


class FieldDefinition(models.Model):
    """
    Defines custom fields that can be added to projects/chapters/characters
    Allows admins to create new fields without code changes
    """

    FIELD_TYPE_CHOICES = [
        ("text", "Short Text"),
        ("textarea", "Long Text"),
        ("markdown", "Markdown"),
        ("json", "Structured Data (JSON)"),
        ("number", "Number"),
        ("date", "Date"),
        ("boolean", "Yes/No"),
        ("choice", "Multiple Choice"),
    ]

    TARGET_MODEL_CHOICES = [
        ("project", "Project"),
        ("chapter", "Chapter"),
        ("character", "Character"),
        ("world", "World"),
    ]

    # Identity
    name = models.CharField(
        max_length=100, unique=True, help_text="Internal name (snake_case, e.g., 'story_themes')"
    )
    display_name = models.CharField(
        max_length=200, help_text="Human-readable name (e.g., 'Story Themes')"
    )
    description = models.TextField(blank=True, help_text="What this field is for")

    # Type & Target
    field_type = models.CharField(max_length=50, choices=FIELD_TYPE_CHOICES, default="textarea")
    target_model = models.CharField(max_length=50, choices=TARGET_MODEL_CHOICES, default="project")

    # Grouping
    group = models.ForeignKey(
        FieldGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name="fields"
    )

    # Validation Rules (JSON)
    validation_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text='JSON: {"min_length": 100, "max_length": 5000, "required": true}',
    )

    # AI Integration
    is_ai_enrichable = models.BooleanField(
        default=True, help_text="Can AI generate content for this field?"
    )
    ai_prompt_template = models.TextField(
        blank=True, help_text="Template for AI prompts (use {{placeholders}})"
    )

    # Display
    placeholder = models.CharField(max_length=200, blank=True)
    help_text = models.TextField(blank=True)
    order = models.IntegerField(default=0)

    # Status
    is_active = models.BooleanField(default=True)
    is_required = models.BooleanField(default=False)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_field_definitions",
    )

    class Meta:
        db_table = "field_definitions"
        ordering = ["target_model", "order", "display_name"]
        verbose_name = "Field Definition"
        verbose_name_plural = "Field Definitions"
        indexes = [
            models.Index(fields=["target_model", "is_active"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.target_model})"


class ProjectFieldValue(models.Model):
    """
    Stores actual values for custom fields on projects
    Polymorphic storage based on field type
    """

    # Relationship
    project = models.ForeignKey(
        BookProjects, on_delete=models.CASCADE, related_name="custom_field_values"
    )
    field_definition = models.ForeignKey(
        FieldDefinition, on_delete=models.CASCADE, related_name="values"
    )

    # Polymorphic Value Storage
    value_text = models.TextField(blank=True, default="")
    value_json = models.JSONField(null=True, blank=True)
    value_number = models.FloatField(null=True, blank=True)
    value_date = models.DateField(null=True, blank=True)
    value_bool = models.BooleanField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_field_values",
    )

    # Version Control
    version = models.IntegerField(default=1)

    class Meta:
        db_table = "project_field_values"
        unique_together = [["project", "field_definition"]]
        ordering = ["-updated_at"]
        verbose_name = "Project Field Value"
        verbose_name_plural = "Project Field Values"
        indexes = [
            models.Index(fields=["project", "field_definition"]),
        ]

    def __str__(self):
        return f"{self.project.title} - {self.field_definition.display_name}"

    def get_value(self):
        """Returns the correct value based on field type"""
        field_type = self.field_definition.field_type
        if field_type in ["text", "textarea", "markdown"]:
            return self.value_text
        elif field_type == "json":
            return self.value_json
        elif field_type == "number":
            return self.value_number
        elif field_type == "date":
            return self.value_date
        elif field_type == "boolean":
            return self.value_bool
        return None

    def set_value(self, value, user=None):
        """Sets the correct field based on field type"""
        field_type = self.field_definition.field_type

        # Store old value for history
        old_value = self.get_value()

        if field_type in ["text", "textarea", "markdown"]:
            self.value_text = str(value) if value is not None else ""
        elif field_type == "json":
            self.value_json = value
        elif field_type == "number":
            self.value_number = float(value) if value is not None else None
        elif field_type == "date":
            self.value_date = value
        elif field_type == "boolean":
            self.value_bool = bool(value) if value is not None else None

        if user:
            self.updated_by = user

        self.version += 1
        self.save()

        # Create history record
        if old_value != value:
            FieldValueHistory.objects.create(
                field_value=self,
                old_value=str(old_value) if old_value else "",
                new_value=str(value) if value else "",
                changed_by=user,
                change_source="manual_edit",
            )


class FieldValueHistory(models.Model):
    """
    Audit trail for all changes to field values
    Tracks who changed what and when
    """

    field_value = models.ForeignKey(
        ProjectFieldValue, on_delete=models.CASCADE, related_name="history"
    )
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    changed_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    change_source = models.CharField(
        max_length=50,
        choices=[
            ("manual_edit", "Manual Edit"),
            ("ai_enrichment", "AI Enrichment"),
            ("import", "Import"),
            ("api", "API"),
        ],
        default="manual_edit",
    )

    class Meta:
        db_table = "field_value_history"
        ordering = ["-changed_at"]
        verbose_name = "Field Value History"
        verbose_name_plural = "Field Value History"

    def __str__(self):
        return f"{self.field_value} - {self.changed_at}"


class FieldTemplate(models.Model):
    """
    Predefined sets of fields for different project types
    Example: "Fantasy Novel Template", "Short Story Template"
    """

    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    fields = models.ManyToManyField(
        FieldDefinition, through="TemplateField", related_name="templates"
    )

    class Meta:
        db_table = "field_templates"
        ordering = ["display_name"]
        verbose_name = "Field Template"
        verbose_name_plural = "Field Templates"

    def __str__(self):
        return self.display_name


class TemplateField(models.Model):
    """
    Through model for FieldTemplate <-> FieldDefinition
    Allows ordering and required flags per template
    """

    template = models.ForeignKey(FieldTemplate, on_delete=models.CASCADE)
    field = models.ForeignKey(FieldDefinition, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)
    is_required = models.BooleanField(default=False)

    class Meta:
        db_table = "template_fields"
        ordering = ["order"]
        unique_together = [["template", "field"]]

    def __str__(self):
        return f"{self.template.name} - {self.field.name}"


# ============================================================================
# BOOKTYPE â†’ PHASE â†’ ACTION WORKFLOW SYSTEM (OPTION 2: DIRECT M2M)
# ============================================================================


class BookTypePhase(models.Model):
    """
    M2M through table: Which phases belong to which book type
    Direct mapping for simple workflow assignment
    """

    book_type = models.ForeignKey(
        BookTypes, on_delete=models.CASCADE, related_name="book_type_phases"
    )
    phase = models.ForeignKey(
        WorkflowPhase, on_delete=models.CASCADE, related_name="book_type_phases"
    )
    order = models.IntegerField(default=0, help_text="Order of this phase in the workflow")
    is_required = models.BooleanField(default=True, help_text="Is this phase mandatory?")
    estimated_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Estimated days to complete this phase",
    )
    description_override = models.TextField(
        blank=True,
        help_text="Override phase description for this book type (optional)",
    )

    class Meta:
        db_table = "book_type_phases"
        ordering = ["book_type", "order"]
        unique_together = [["book_type", "phase"]]
        verbose_name = "Book Type Phase"
        verbose_name_plural = "Book Type Phases"

    def __str__(self):
        return f"{self.book_type.name} - Step {self.order}: {self.phase.name}"


# PhaseActionConfig already exists above (line 1874)
# We use the existing PhaseActionConfig model instead of creating a duplicate


# ============================================================================
# AI PROMPT MANAGEMENT SYSTEM V2.0
# ============================================================================
# Production-ready prompt template system with:
# - Template inheritance & versioning
# - Graceful degradation (required vs optional variables)
# - A/B testing framework
# - Execution tracking & analytics
# - Fallback templates & retry logic
# - Security (prompt injection prevention)
# - Multi-language support
# ============================================================================


class PromptTemplate(models.Model):
    """
    Reusable AI prompt templates with advanced features

    Features:
    - Template inheritance (parent_template)
    - Fallback templates for error recovery
    - Required vs optional variables with defaults
    - A/B testing support
    - Multi-language support
    - Detailed usage tracking
    """

    # === IDENTITY ===
    name = models.CharField(max_length=200, help_text="Human-readable name")
    template_key = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Unique key for code reference: character_backstory_v1",
    )
    category = models.CharField(
        max_length=50,
        db_index=True,
        choices=[
            ("character", "Character Development"),
            ("chapter", "Chapter Writing"),
            ("world", "World Building"),
            ("plot", "Plot Development"),
            ("dialogue", "Dialogue"),
            ("description", "Description"),
            ("analysis", "Analysis"),
            ("revision", "Revision"),
            ("correction", "Repetition Correction"),
        ],
        help_text="Template category",
    )

    # === INHERITANCE ===
    parent_template = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_templates",
        help_text="Inherit from parent template",
    )

    # === PROMPT CONTENT ===
    system_prompt = models.TextField(help_text="System message defining AI role and constraints")
    user_prompt_template = models.TextField(help_text="User prompt with {placeholder} variables")

    # === CONFIGURATION ===
    required_variables = models.JSONField(
        default=list,
        help_text='Variables that MUST be present: ["character_name", "project_genre"]',
    )
    optional_variables = models.JSONField(
        default=list, help_text='Variables that can be missing: ["character_arc", "world_rules"]'
    )
    variable_defaults = models.JSONField(
        default=dict,
        help_text='Default values for optional variables: {"world_rules": "Standard fantasy"}',
    )

    # === OUTPUT SPECIFICATION ===
    output_format = models.CharField(
        max_length=20,
        default="text",
        choices=[
            ("text", "Plain Text"),
            ("json", "JSON"),
            ("markdown", "Markdown"),
            ("structured", "Structured (with fields)"),
        ],
    )
    output_schema = models.JSONField(
        default=dict, blank=True, help_text="JSON Schema for output validation"
    )

    # === LLM PARAMETERS ===
    preferred_llm = models.ForeignKey(
        "Llms",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_templates",
        help_text="Preferred LLM for this template (optional, falls back to agent/system default)",
    )
    max_tokens = models.IntegerField(default=500)
    temperature = models.FloatField(default=0.7)
    top_p = models.FloatField(default=1.0)
    frequency_penalty = models.FloatField(default=0.0)
    presence_penalty = models.FloatField(default=0.0)

    # === VERSIONING ===
    version = models.CharField(max_length=20, default="1.0")
    is_active = models.BooleanField(default=True, db_index=True)
    is_default = models.BooleanField(default=False, help_text="Default template for this category")

    # === A/B TESTING ===
    ab_test_group = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ("", "None"),
            ("A", "Group A"),
            ("B", "Group B"),
            ("C", "Group C"),
        ],
        help_text="A/B test group identifier",
    )
    ab_test_weight = models.FloatField(
        default=1.0, help_text="Weight for random selection (0.0-1.0)"
    )

    # === FALLBACK ===
    fallback_template = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fallback_for",
        help_text="Template to use if this one fails",
    )

    # === MULTI-LANGUAGE ===
    language = models.CharField(
        max_length=10,
        default="en",
        choices=[
            ("en", "English"),
            ("de", "German"),
            ("es", "Spanish"),
            ("fr", "French"),
        ],
    )

    # === USAGE TRACKING ===
    usage_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    failure_count = models.IntegerField(default=0)
    avg_confidence = models.FloatField(default=0.0)
    avg_execution_time = models.FloatField(default=0.0)
    avg_tokens_used = models.IntegerField(default=0)
    avg_cost = models.DecimalField(max_digits=10, decimal_places=4, default=0)

    # === METADATA ===
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list)
    created_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, related_name="created_prompt_templates"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # === AGENTSKILLS.IO KOMPATIBILITÄT ===
    # Gemäß https://agentskills.io/specification
    
    skill_description = models.TextField(
        blank=True,
        help_text="Kurzbeschreibung mit Keywords für Auto-Matching (1-1024 chars). "
                  "AgentSkills.io 'description' field für Trigger-Erkennung."
    )
    
    compatibility = models.CharField(
        max_length=500,
        blank=True,
        help_text="Umgebungsanforderungen (z.B. 'Requires internet access, Python 3.8+')"
    )
    
    license = models.CharField(
        max_length=100,
        blank=True,
        default="Proprietary",
        help_text="Lizenz für diesen Skill (z.B. 'Apache-2.0', 'MIT', 'Proprietary')"
    )
    
    author = models.CharField(
        max_length=100,
        blank=True,
        help_text="Skill-Autor oder Team"
    )
    
    allowed_tools = models.JSONField(
        default=list,
        blank=True,
        help_text='Pre-approved Tools: ["Bash(git:*)", "Read", "Write", "WebSearch"]'
    )
    
    references = models.JSONField(
        default=dict,
        blank=True,
        help_text='Referenz-Dokumente: {"REFERENCE": "...", "FORMS": "...", "domain": "..."}'
    )
    
    agent_class = models.CharField(
        max_length=200,
        blank=True,
        help_text="Python-Pfad zum ausführenden Agent: apps.bfagent.agents.ResearchAgent"
    )

    class Meta:
        db_table = "prompt_templates"
        ordering = ["-is_active", "category", "name"]
        indexes = [
            models.Index(fields=["template_key", "is_active"]),
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["ab_test_group"]),
        ]
        unique_together = [("template_key", "version")]
        verbose_name = "Prompt Template"
        verbose_name_plural = "Prompt Templates"

    def __str__(self):
        return f"{self.name} (v{self.version})"

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.usage_count == 0:
            return 0.0
        return (self.success_count / self.usage_count) * 100

    def to_agentskills_format(self) -> str:
        """
        Exportiert als SKILL.md gemäß AgentSkills.io Spezifikation.
        
        Returns:
            String im SKILL.md Format (YAML frontmatter + Markdown body)
        """
        import json
        
        # Build frontmatter
        frontmatter_lines = [
            "---",
            f"name: {self.template_key}",
            f"description: {self.skill_description or self.description or self.name}",
        ]
        
        if self.license:
            frontmatter_lines.append(f"license: {self.license}")
        
        if self.compatibility:
            frontmatter_lines.append(f"compatibility: {self.compatibility}")
        
        # Metadata section
        frontmatter_lines.append("metadata:")
        if self.author:
            frontmatter_lines.append(f"  author: {self.author}")
        frontmatter_lines.append(f'  version: "{self.version}"')
        frontmatter_lines.append(f"  category: {self.category}")
        
        if self.allowed_tools:
            tools_str = " ".join(self.allowed_tools)
            frontmatter_lines.append(f"allowed-tools: {tools_str}")
        
        frontmatter_lines.append("---")
        
        # Build body
        body_lines = [
            "",
            f"# {self.name}",
            "",
        ]
        
        if self.system_prompt:
            body_lines.extend([
                "## System Role",
                "",
                self.system_prompt,
                "",
            ])
        
        if self.user_prompt_template:
            body_lines.extend([
                "## Instructions",
                "",
                self.user_prompt_template,
                "",
            ])
        
        if self.output_format != "text":
            body_lines.extend([
                "## Output Format",
                "",
                f"Format: {self.output_format}",
            ])
            if self.output_schema:
                body_lines.append(f"Schema: ```json\n{json.dumps(self.output_schema, indent=2)}\n```")
            body_lines.append("")
        
        if self.required_variables:
            body_lines.extend([
                "## Required Variables",
                "",
            ])
            for var in self.required_variables:
                body_lines.append(f"- `{var}`")
            body_lines.append("")
        
        if self.references:
            body_lines.extend([
                "## References",
                "",
            ])
            for key, value in self.references.items():
                body_lines.append(f"### {key}")
                body_lines.append(value)
                body_lines.append("")
        
        return "\n".join(frontmatter_lines + body_lines)

    def render(self, variables: dict) -> str:
        """
        Render template with provided variables using Jinja2-style syntax

        Args:
            variables: Dictionary of template variables

        Returns:
            Rendered prompt string with variables substituted

        Raises:
            ValueError: If required variables are missing
        """
        import json

        from jinja2 import Template

        # Parse required and optional variables
        required = json.loads(self.required_variables) if self.required_variables else []
        defaults = json.loads(self.variable_defaults) if self.variable_defaults else {}

        # Check for missing required variables
        missing = [var for var in required if var not in variables]
        if missing:
            raise ValueError(f"Missing required variables: {', '.join(missing)}")

        # Merge with defaults for optional variables
        final_vars = {**defaults, **variables}

        # Render system prompt
        system_template = Template(self.system_prompt)
        rendered_system = system_template.render(final_vars)

        # Render user prompt if separate
        if self.user_prompt_template:
            user_template = Template(self.user_prompt_template)
            rendered_user = user_template.render(final_vars)
            return f"{rendered_system}\n\nUser: {rendered_user}"

        return rendered_system


class PromptExecution(models.Model):
    """
    Track prompt executions for learning & optimization

    Features:
    - Detailed error tracking
    - Context completeness scoring
    - Retry information
    - User feedback
    - Performance metrics
    """

    # === REFERENCES ===
    template = models.ForeignKey(
        PromptTemplate, on_delete=models.CASCADE, related_name="executions"
    )
    agent = models.ForeignKey("Agents", on_delete=models.SET_NULL, null=True)

    # === EXECUTION CONTEXT ===
    project = models.ForeignKey(
        "BookProjects", on_delete=models.CASCADE, related_name="prompt_executions"
    )
    target_model = models.CharField(max_length=50)
    target_id = models.IntegerField()

    # === INPUT/OUTPUT ===
    rendered_prompt = models.TextField(help_text="Final prompt after variable substitution")
    context_used = models.JSONField(help_text="Complete context that was available")
    llm_response = models.TextField(blank=True)
    parsed_output = models.JSONField(null=True, blank=True, help_text="Parsed and validated output")

    # === QUALITY METRICS ===
    confidence_score = models.FloatField(null=True)
    user_accepted = models.BooleanField(null=True)
    user_edited = models.BooleanField(default=False)
    user_rating = models.IntegerField(null=True, choices=[(i, f"{i} Stars") for i in range(1, 6)])
    user_feedback = models.TextField(blank=True)

    # === CONTEXT COMPLETENESS ===
    context_completeness_score = models.FloatField(
        default=0.0, help_text="Percentage of optional variables that were present (0-100)"
    )
    missing_variables = models.JSONField(
        default=list, help_text="List of variables that were missing"
    )

    # === PERFORMANCE ===
    execution_time = models.FloatField(help_text="Execution time in seconds")
    tokens_used = models.IntegerField(null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=4, null=True)

    # === STATUS & ERROR HANDLING ===
    status = models.CharField(
        max_length=20,
        default="success",
        choices=[
            ("success", "Success"),
            ("error", "Error"),
            ("timeout", "Timeout"),
            ("validation_failed", "Validation Failed"),
            ("partial_success", "Partial Success"),
        ],
    )
    error_message = models.TextField(blank=True)
    error_type = models.CharField(max_length=100, blank=True)

    # === RETRY INFORMATION ===
    retry_count = models.IntegerField(default=0)
    retry_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="retries"
    )

    # === METADATA ===
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "prompt_executions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["template", "status"]),
            models.Index(fields=["project", "created_at"]),
            models.Index(fields=["user_accepted"]),
            models.Index(fields=["status", "created_at"]),
        ]
        verbose_name = "Prompt Execution"
        verbose_name_plural = "Prompt Executions"

    def __str__(self):
        return f"Execution of {self.template.name} - {self.status}"


class PromptTemplateTest(models.Model):
    """
    Automated test cases for prompt templates

    Features:
    - Expected output validation
    - Length checks
    - Regression prevention
    - Automated execution
    """

    template = models.ForeignKey(PromptTemplate, on_delete=models.CASCADE, related_name="tests")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # === TEST INPUT ===
    test_context = models.JSONField(help_text="Test context data")

    # === EXPECTED OUTPUT ===
    expected_output_contains = models.JSONField(
        default=list, help_text="Strings that should be in output"
    )
    expected_output_not_contains = models.JSONField(
        default=list, help_text="Strings that should NOT be in output"
    )
    expected_min_length = models.IntegerField(null=True)
    expected_max_length = models.IntegerField(null=True)

    # === TEST RESULTS ===
    last_run_at = models.DateTimeField(null=True)
    last_run_passed = models.BooleanField(null=True)
    last_run_output = models.TextField(blank=True)
    last_run_error = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "prompt_template_tests"
        ordering = ["template", "name"]
        verbose_name = "Prompt Template Test"
        verbose_name_plural = "Prompt Template Tests"

    def __str__(self):
        return f"Test: {self.name}"


# ============================================================================
# IMAGE GENERATION MODELS
# ============================================================================


class GeneratedImage(models.Model):
    """
    Track generated images with full metadata.
    """

    PROVIDER_CHOICES = [
        ("openai", "OpenAI DALL-E"),
        ("stability", "Stability AI"),
        ("replicate", "Replicate"),
        ("other", "Other"),
    ]

    QUALITY_CHOICES = [
        ("standard", "Standard"),
        ("hd", "HD"),
        ("high", "High"),
    ]

    # === IDENTITY ===
    image_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # === GENERATION DETAILS ===
    prompt = models.TextField(help_text="Original prompt")
    revised_prompt = models.TextField(blank=True, help_text="AI-revised prompt")
    negative_prompt = models.TextField(blank=True)

    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, db_index=True)
    model = models.CharField(max_length=100, help_text="Model name")

    # === FILE STORAGE ===
    image_file = models.ImageField(upload_to="generated_images/%Y/%m/%d/")
    thumbnail = models.ImageField(
        upload_to="generated_images/thumbnails/%Y/%m/%d/", blank=True, null=True
    )
    original_url = models.URLField(max_length=1000, blank=True)

    # === IMAGE METADATA ===
    size = models.CharField(max_length=50)
    quality = models.CharField(max_length=20, choices=QUALITY_CHOICES, default="standard")
    style = models.CharField(max_length=100, blank=True)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)

    # === COST & PERFORMANCE ===
    cost_cents = models.DecimalField(max_digits=10, decimal_places=2)
    generation_time_seconds = models.FloatField()

    # === BOOK/CHAPTER ASSOCIATION ===
    book_id = models.IntegerField(null=True, blank=True, db_index=True)
    chapter_id = models.IntegerField(null=True, blank=True)
    scene_number = models.IntegerField(null=True, blank=True)
    scene_description = models.TextField(blank=True)

    # === HANDLER & USER ===
    handler = models.ForeignKey(
        "core.Handler",  # Moved to core in Phase 2a
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_images",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_images",
    )

    # === STATUS ===
    is_active = models.BooleanField(default=True, db_index=True)
    is_favorite = models.BooleanField(default=False)
    tags = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    generation_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "generated_images"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "-created_at"]),
            models.Index(fields=["book_id", "chapter_id", "scene_number"]),
            models.Index(fields=["is_active", "-created_at"]),
        ]

    def __str__(self):
        if self.book_id:
            return f"Book {self.book_id} - {self.prompt[:50]}"
        return f"{self.provider} - {self.prompt[:50]}"

    def save(self, *args, **kwargs):
        if self.image_file and not self.thumbnail:
            self.create_thumbnail()
        if self.image_file and (not self.width or not self.height):
            self.extract_dimensions()
        super().save(*args, **kwargs)

    def create_thumbnail(self, size=(300, 300)):
        if not self.image_file:
            return
        try:
            image = PILImage.open(self.image_file)
            if image.mode in ("RGBA", "LA", "P"):
                background = PILImage.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                background.paste(image, mask=image.split()[-1])
                image = background
            image.thumbnail(size, PILImage.Resampling.LANCZOS)
            thumb_io = BytesIO()
            image.save(thumb_io, format="JPEG", quality=85)
            thumb_io.seek(0)
            filename = f"thumb_{self.image_id}.jpg"
            self.thumbnail.save(filename, ContentFile(thumb_io.read()), save=False)
        except Exception as e:
            pass

    def extract_dimensions(self):
        if not self.image_file:
            return
        try:
            image = PILImage.open(self.image_file)
            self.width, self.height = image.size
            self.file_size_bytes = self.image_file.size
        except Exception:
            pass

    @property
    def cost_usd(self):
        return float(self.cost_cents) / 100

    @property
    def aspect_ratio(self):
        if self.width and self.height:
            from math import gcd

            g = gcd(self.width, self.height)
            return f"{self.width//g}:{self.height//g}"
        return self.size

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("bfagent:image_detail", kwargs={"image_id": self.image_id})

    def get_download_url(self):
        return self.image_file.url if self.image_file else None

    def get_thumbnail_url(self):
        if self.thumbnail:
            return self.thumbnail.url
        return self.image_file.url if self.image_file else None


# ============================================================================
# STORY ENGINE - AI-Powered Novel Generation System
# ============================================================================


class StoryBible(models.Model):
    """
    Primary story universe document - The "bible" for a novel series
    Contains all world-building, rules, timelines, and style guides
    """

    # Basic Info
    title = models.CharField(max_length=200, help_text="Story/Series title")
    subtitle = models.CharField(max_length=300, blank=True, help_text="Series subtitle or tagline")
    genre = models.CharField(max_length=100, help_text="Primary genre")
    target_word_count = models.IntegerField(default=80000, help_text="Target total word count")

    # Structured World Building
    scientific_concepts = models.JSONField(
        default=dict,
        blank=True,
        help_text="Key scientific/technical concepts (e.g., {'si_emergence': 'Gradual cognitive enhancement via BCIs'})",
    )
    world_rules = models.JSONField(
        default=list,
        blank=True,
        help_text="Established world rules (e.g., [{'rule': 'No time travel', 'established_in': 'Chapter 1'}])",
    )
    technology_levels = models.JSONField(
        default=dict, blank=True, help_text="Technology availability by year/location"
    )

    # Timeline
    timeline = models.JSONField(
        default=list,
        blank=True,
        help_text="Story timeline events (e.g., [{'year': 2045, 'event': 'First BCI enhancement'}])",
    )
    timeline_start_year = models.IntegerField(null=True, blank=True, help_text="Story start year")
    timeline_end_year = models.IntegerField(null=True, blank=True, help_text="Story end year")

    # Style Guide
    prose_style = models.TextField(blank=True, help_text="Prose style description")
    tone = models.CharField(
        max_length=100, blank=True, help_text="Overall tone (e.g., 'Dark, philosophical')"
    )
    pacing_profile = models.JSONField(
        default=dict, blank=True, help_text="Pacing preferences per story segment"
    )

    # Status
    status = models.CharField(
        max_length=20,
        default="planning",
        choices=[
            ("planning", "Planning"),
            ("development", "Development"),
            ("writing", "Writing"),
            ("revision", "Revision"),
            ("complete", "Complete"),
        ],
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, related_name="story_bibles"
    )

    class Meta:
        db_table = "story_bibles"
        ordering = ["-created_at"]
        verbose_name = "Story Bible"
        verbose_name_plural = "Story Bibles"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("bfagent:story_bible_detail", kwargs={"pk": self.pk})


class StoryStrand(models.Model):
    """
    Individual story threads within a Story Bible
    Each strand represents a parallel plotline (e.g., 'The Awakening', 'Corporate Conspiracy')
    """

    story_bible = models.ForeignKey(StoryBible, on_delete=models.CASCADE, related_name="strands")

    # Basic Info
    name = models.CharField(max_length=100, help_text="Strand name (e.g., 'Das Erwachen')")
    order = models.IntegerField(default=1, help_text="Display/execution order (1-6)")

    # Story Focus
    focus = models.CharField(
        max_length=200, help_text="Central focus of this strand (e.g., 'Individual transformation')"
    )
    genre_weights = models.JSONField(
        default=dict,
        blank=True,
        help_text="Genre mix for this strand (e.g., {'thriller': 70, 'philosophy': 30})",
    )
    core_theme = models.TextField(help_text="Central theme of this strand")

    # Timeline
    starts_in_book = models.IntegerField(default=1, help_text="Which book does this strand begin?")
    ends_in_book = models.IntegerField(default=1, help_text="Which book does this strand conclude?")

    # Primary Character (optional)
    primary_character = models.ForeignKey(
        "StoryCharacter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_strands",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "story_strands"
        ordering = ["story_bible", "order"]
        unique_together = [["story_bible", "name"]]
        verbose_name = "Story Strand"
        verbose_name_plural = "Story Strands"

    def __str__(self):
        return f"{self.story_bible.title} - {self.name}"


class StoryCharacter(models.Model):
    """
    Characters within a Story Bible with structured attributes
    Supports detailed character development and consistency tracking
    """

    story_bible = models.ForeignKey(StoryBible, on_delete=models.CASCADE, related_name="characters")

    # Basic Info
    name = models.CharField(max_length=100, help_text="Character name")
    full_name = models.CharField(max_length=200, blank=True, help_text="Full legal name")
    age = models.IntegerField(null=True, blank=True, help_text="Age at story start")

    # Structured Attributes (for AI consistency checking)
    physical_traits = models.JSONField(
        default=dict,
        blank=True,
        help_text="Physical appearance (e.g., {'height': 165, 'hair': 'black', 'eyes': 'brown'})",
    )
    personality_traits = models.JSONField(
        default=list,
        blank=True,
        help_text="Personality traits (e.g., ['intelligent', 'cautious', 'empathetic'])",
    )
    skills = models.JSONField(
        default=list,
        blank=True,
        help_text="Skills and abilities (e.g., ['neuroscience', 'programming'])",
    )

    # Relationships (IDs of other characters)
    relationships = models.JSONField(
        default=dict,
        blank=True,
        help_text="Relationships to other characters (e.g., {'colleague_of': [2, 5], 'mentor_to': [7]})",
    )

    # Full Descriptions (for Vector Store / AI context)
    biography = models.TextField(blank=True, help_text="Full character biography")
    psychological_profile = models.TextField(
        blank=True, help_text="Psychological profile and motivations"
    )

    # Character Arc Tracking
    character_arc = models.JSONField(
        default=dict, blank=True, help_text="Character development arc milestones"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "story_characters"
        ordering = ["story_bible", "name"]
        unique_together = [["story_bible", "name"]]
        verbose_name = "Story Character"
        verbose_name_plural = "Story Characters"

    def __str__(self):
        return f"{self.name} ({self.story_bible.title})"


class ChapterBeat(models.Model):
    """
    Planned chapter structure before AI generation
    Defines what should happen in a chapter at a high level
    """

    story_bible = models.ForeignKey(
        StoryBible, on_delete=models.CASCADE, related_name="chapter_beats"
    )
    strand = models.ForeignKey(StoryStrand, on_delete=models.CASCADE, related_name="beats")

    # Beat Info
    beat_number = models.IntegerField(help_text="Sequential beat number")
    title = models.CharField(max_length=200, help_text="Beat/chapter title")
    description = models.TextField(help_text="What happens in this beat")

    # Story Elements
    key_events = models.JSONField(
        default=list,
        blank=True,
        help_text="Key events in this beat (e.g., ['Discovery of enhancement', 'First contact fails'])",
    )
    character_focus = models.ForeignKey(
        StoryCharacter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="focused_beats",
    )
    emotional_tone = models.CharField(
        max_length=100,
        blank=True,
        help_text="Emotional tone for this beat (e.g., 'tense', 'hopeful')",
    )

    # Generation Targets
    target_word_count = models.IntegerField(
        default=2000, help_text="Target word count for generated chapter"
    )
    tension_level = models.IntegerField(
        default=5, help_text="Tension level 1-10 for pacing control"
    )

    # Order
    order = models.IntegerField(default=1, help_text="Order within strand")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chapter_beats"
        ordering = ["story_bible", "strand", "order"]
        unique_together = [["strand", "beat_number"]]
        verbose_name = "Chapter Beat"
        verbose_name_plural = "Chapter Beats"

    def __str__(self):
        return f"{self.strand.name} - Beat {self.beat_number}: {self.title}"


class StoryChapter(models.Model):
    """
    AI-generated chapters with full metadata and quality tracking
    Links to ChapterBeat (the plan) and stores the generated prose
    """

    story_bible = models.ForeignKey(StoryBible, on_delete=models.CASCADE, related_name="chapters")
    strand = models.ForeignKey(StoryStrand, on_delete=models.CASCADE, related_name="chapters")
    beat = models.ForeignKey(
        ChapterBeat,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_chapters",
        help_text="The beat this chapter was generated from",
    )

    # Chapter Info
    chapter_number = models.IntegerField(help_text="Sequential chapter number")
    title = models.CharField(max_length=200, help_text="Chapter title")

    # Content
    content = models.TextField(help_text="Full chapter prose")
    summary = models.TextField(blank=True, help_text="AI-generated summary")

    # Metadata
    word_count = models.IntegerField(default=0, help_text="Actual word count")
    pov_character = models.ForeignKey(
        StoryCharacter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pov_chapters",
        help_text="POV character for this chapter",
    )

    # Generation Metadata
    generation_method = models.CharField(
        max_length=50,
        default="agent_system",
        help_text="How was this generated? (e.g., 'agent_system', 'manual')",
    )
    quality_score = models.FloatField(
        null=True, blank=True, help_text="AI quality assessment (0-1)"
    )
    consistency_score = models.FloatField(
        null=True, blank=True, help_text="Consistency check score (0-1)"
    )

    # Status
    status = models.CharField(
        max_length=20,
        default="draft",
        choices=[
            ("draft", "Draft"),
            ("review", "Review"),
            ("approved", "Approved"),
            ("published", "Published"),
        ],
    )
    version = models.IntegerField(default=1, help_text="Version number (for revisions)")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "story_chapters"
        ordering = ["story_bible", "strand", "chapter_number"]
        unique_together = [["strand", "chapter_number", "version"]]
        verbose_name = "Story Chapter"
        verbose_name_plural = "Story Chapters"
        indexes = [
            models.Index(fields=["story_bible", "status"]),
            models.Index(fields=["strand", "chapter_number"]),
        ]

    def __str__(self):
        return f"{self.strand.name} - Chapter {self.chapter_number}: {self.title}"

    def save(self, *args, **kwargs):
        # Auto-calculate word count
        if self.content:
            self.word_count = len(self.content.split())
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("bfagent:story_chapter_detail", kwargs={"pk": self.pk})
