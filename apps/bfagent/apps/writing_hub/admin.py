"""
Writing Hub Admin
=================

Admin interface for Writing Hub lookup tables.
"""

from django.contrib import admin

from .models import (
    ArcType,
    BookProject,
    Chapter,
    Character,
    ContentRating,
    ContentType,
    CreativeSession,
    BookIdea,
    CreativeMessage,
    ErrorStrategy,
    FrameworkBeat,
    HandlerCategory,
    HandlerPhase,
    ImportanceLevel,
    StructureFramework,
    WorkflowPhaseLLMConfig,
    WritingStage,
    # Import Framework V2 models
    ImportPromptTemplate,
    OutlineCategory,
    OutlineTemplate,
    ProjectOutline,
    ImportSession,
    OutlineRecommendation,
)


# =============================================================================
# Proxy Models Admin (BookProject, Chapter, Character)
# =============================================================================

@admin.register(BookProject)
class BookProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "genre", "content_rating", "status", "created_at"]
    list_filter = ["genre", "content_rating", "status"]
    search_fields = ["title", "description"]
    ordering = ["-created_at"]


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ["title", "project", "chapter_number", "status", "word_count"]
    list_filter = ["status", "project"]
    search_fields = ["title", "content"]
    ordering = ["project", "chapter_number"]


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ["name", "project", "role", "created_at"]
    list_filter = ["role"]
    search_fields = ["name", "description", "background"]
    ordering = ["project", "name"]


# =============================================================================
# Lookup Tables Admin
# =============================================================================

@admin.register(ContentRating)
class ContentRatingAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "min_age", "is_active", "sort_order"]
    list_filter = ["is_active"]
    search_fields = ["code", "name", "description"]
    ordering = ["sort_order", "min_age"]

    fieldsets = (
        ("Basic Info", {"fields": ("code", "name", "description", "min_age")}),
        ("Settings", {"fields": ("is_active", "sort_order")}),
    )


@admin.register(WritingStage)
class WritingStageAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "progress_percentage", "color", "is_active", "sort_order"]
    list_filter = ["is_active"]
    search_fields = ["code", "name", "description"]
    ordering = ["sort_order"]

    fieldsets = (
        ("Basic Info", {"fields": ("code", "name", "description")}),
        ("Progress", {"fields": ("progress_percentage",)}),
        ("Visual", {"fields": ("color", "icon")}),
        ("Settings", {"fields": ("is_active", "sort_order")}),
    )


@admin.register(ArcType)
class ArcTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "color", "is_active", "sort_order"]
    list_filter = ["is_active"]
    search_fields = ["code", "name", "description"]
    ordering = ["sort_order"]

    fieldsets = (
        ("Basic Info", {"fields": ("code", "name", "description")}),
        ("Visual", {"fields": ("color", "icon")}),
        ("Settings", {"fields": ("is_active", "sort_order")}),
    )


@admin.register(ImportanceLevel)
class ImportanceLevelAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "color", "is_active", "sort_order"]
    list_filter = ["is_active"]
    search_fields = ["code", "name", "description"]
    ordering = ["sort_order"]

    fieldsets = (
        ("Basic Info", {"fields": ("code", "name", "description")}),
        ("Visual", {"fields": ("color", "icon")}),
        ("Settings", {"fields": ("is_active", "sort_order")}),
    )


@admin.register(HandlerCategory)
class HandlerCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "color", "icon", "is_active", "display_order"]
    list_filter = ["is_active", "is_system"]
    search_fields = ["code", "name", "description"]
    ordering = ["display_order", "name"]
    readonly_fields = ["is_system", "created_at", "updated_at"]

    fieldsets = (
        ("Basic Info", {"fields": ("code", "name", "description")}),
        ("Visual", {"fields": ("color", "icon", "display_order")}),
        ("Settings", {"fields": ("is_active", "is_system")}),
        ("Configuration", {"fields": ("config",), "classes": ("collapse",)}),
        ("Audit", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(HandlerPhase)
class HandlerPhaseAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "execution_order", "color", "is_active", "sort_order"]
    list_filter = ["is_active"]
    search_fields = ["code", "name", "description"]
    ordering = ["execution_order", "sort_order"]

    fieldsets = (
        ("Basic Info", {"fields": ("code", "name", "description")}),
        ("Execution", {"fields": ("execution_order",)}),
        ("Visual", {"fields": ("color", "icon")}),
        ("Settings", {"fields": ("is_active", "sort_order")}),
    )


@admin.register(ErrorStrategy)
class ErrorStrategyAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "stops_execution",
        "allows_retry",
        "max_retries",
        "is_active",
        "sort_order",
    ]
    list_filter = ["is_active", "stops_execution", "allows_retry"]
    search_fields = ["code", "name", "description"]
    ordering = ["sort_order"]

    fieldsets = (
        ("Basic Info", {"fields": ("code", "name", "description")}),
        ("Behavior", {"fields": ("stops_execution", "allows_retry", "max_retries")}),
        ("Visual", {"fields": ("color", "icon")}),
        ("Settings", {"fields": ("is_active", "sort_order")}),
    )


# =============================================================================
# Content Type Framework System Admin
# =============================================================================

class FrameworkBeatInline(admin.TabularInline):
    """Inline admin for framework beats"""
    model = FrameworkBeat
    extra = 1
    ordering = ['sort_order']
    fields = ['name', 'name_de', 'position', 'part', 'sort_order', 'is_required']


class StructureFrameworkInline(admin.TabularInline):
    """Inline admin for frameworks within a content type"""
    model = StructureFramework
    extra = 0
    show_change_link = True
    fields = ['slug', 'name_de', 'icon', 'is_default', 'is_active', 'sort_order']


@admin.register(ContentType)
class ContentTypeAdmin(admin.ModelAdmin):
    list_display = ['name_de', 'slug', 'icon', 'section_label', 'default_word_count', 'is_active', 'sort_order']
    list_filter = ['is_active', 'has_characters', 'has_world_building', 'has_citations']
    search_fields = ['slug', 'name', 'name_de', 'description']
    ordering = ['sort_order', 'name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [StructureFrameworkInline]
    
    fieldsets = (
        ('Grundinfo', {
            'fields': ('slug', 'name', 'name_de', 'description', 'icon')
        }),
        ('Abschnitte', {
            'fields': ('section_label', 'section_label_plural', 'default_section_count', 'default_word_count')
        }),
        ('Features', {
            'fields': ('has_characters', 'has_world_building', 'has_citations', 'has_abstract'),
            'classes': ('collapse',)
        }),
        ('LLM Konfiguration', {
            'fields': ('llm_system_prompt',),
            'classes': ('collapse',)
        }),
        ('Einstellungen', {
            'fields': ('is_active', 'sort_order')
        }),
    )


@admin.register(StructureFramework)
class StructureFrameworkAdmin(admin.ModelAdmin):
    list_display = ['name_de', 'content_type', 'slug', 'icon', 'default_section_count', 'is_default', 'is_active']
    list_filter = ['content_type', 'is_active', 'is_default']
    search_fields = ['slug', 'name', 'name_de', 'description']
    ordering = ['content_type', 'sort_order', 'name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [FrameworkBeatInline]
    
    fieldsets = (
        ('Grundinfo', {
            'fields': ('content_type', 'slug', 'name', 'name_de', 'description', 'icon')
        }),
        ('Konfiguration', {
            'fields': ('default_section_count', 'is_default')
        }),
        ('LLM Prompts', {
            'fields': ('llm_system_prompt', 'llm_user_template'),
            'classes': ('collapse',)
        }),
        ('Einstellungen', {
            'fields': ('is_active', 'sort_order')
        }),
    )


@admin.register(FrameworkBeat)
class FrameworkBeatAdmin(admin.ModelAdmin):
    list_display = ['name_de', 'framework', 'position', 'part', 'sort_order', 'is_required']
    list_filter = ['framework__content_type', 'framework', 'part', 'is_required']
    search_fields = ['name', 'name_de', 'description']
    ordering = ['framework', 'sort_order']
    
    fieldsets = (
        ('Grundinfo', {
            'fields': ('framework', 'name', 'name_de')
        }),
        ('Beschreibung', {
            'fields': ('description', 'description_de')
        }),
        ('Position', {
            'fields': ('position', 'part', 'sort_order', 'suggested_word_percentage')
        }),
        ('LLM Prompt', {
            'fields': ('llm_prompt_template',),
            'classes': ('collapse',)
        }),
        ('Einstellungen', {
            'fields': ('is_required',)
        }),
    )


# =============================================================================
# Idea Generation System Admin
# =============================================================================

from .models import IdeaGenerationStep, IdeaSession, IdeaResponse


class IdeaGenerationStepInline(admin.TabularInline):
    """Inline admin for idea steps within a content type"""
    model = IdeaGenerationStep
    extra = 0
    show_change_link = True
    fields = ['step_number', 'name_de', 'input_type', 'is_required', 'can_generate_with_ai', 'is_active', 'sort_order']
    ordering = ['sort_order', 'step_number']


class IdeaResponseInline(admin.TabularInline):
    """Inline admin for responses within a session"""
    model = IdeaResponse
    extra = 0
    readonly_fields = ['step', 'version', 'source', 'is_accepted', 'created_at']
    fields = ['step', 'content', 'source', 'version', 'is_accepted', 'is_current', 'created_at']
    ordering = ['step__sort_order', '-version']


@admin.register(IdeaGenerationStep)
class IdeaGenerationStepAdmin(admin.ModelAdmin):
    list_display = ['name_de', 'content_type', 'step_number', 'input_type', 'is_required', 'can_generate_with_ai', 'is_active']
    list_filter = ['content_type', 'input_type', 'is_required', 'can_generate_with_ai', 'is_active']
    search_fields = ['name', 'name_de', 'question', 'question_de']
    ordering = ['content_type', 'sort_order', 'step_number']
    list_editable = ['is_active', 'sort_order'] if False else []  # Enable if needed
    
    fieldsets = (
        ('Grundinfo', {
            'fields': ('content_type', 'step_number', 'name', 'name_de', 'sort_order')
        }),
        ('Frage', {
            'fields': ('question', 'question_de')
        }),
        ('Kontexthilfe', {
            'fields': ('help_text_short', 'help_text_detailed', 'help_examples', 'help_tips', 'help_common_mistakes', 'help_video_url', 'help_related_articles'),
            'classes': ('collapse',)
        }),
        ('Eingabefeld', {
            'fields': ('input_type', 'input_options', 'input_placeholder', 'input_min_length', 'input_max_length')
        }),
        ('AI Generierung', {
            'fields': ('can_generate_with_ai', 'ai_prompt_template', 'ai_refinement_prompt'),
            'classes': ('collapse',)
        }),
        ('Abhängigkeiten', {
            'fields': ('depends_on_steps', 'show_condition'),
            'classes': ('collapse',)
        }),
        ('Einstellungen', {
            'fields': ('is_required', 'is_active')
        }),
    )
    
    filter_horizontal = ['depends_on_steps']


@admin.register(IdeaSession)
class IdeaSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'content_type', 'user', 'status', 'current_step', 'get_progress', 'started_at', 'updated_at']
    list_filter = ['content_type', 'status', 'started_at']
    search_fields = ['title', 'user__username', 'idea_summary']
    ordering = ['-updated_at']
    readonly_fields = ['started_at', 'updated_at', 'get_progress']
    inlines = [IdeaResponseInline]
    
    fieldsets = (
        ('Session', {
            'fields': ('title', 'content_type', 'user', 'project', 'status')
        }),
        ('Fortschritt', {
            'fields': ('current_step', 'get_progress')
        }),
        ('Zusammenfassung', {
            'fields': ('idea_summary', 'idea_summary_version'),
            'classes': ('collapse',)
        }),
        ('Zeitstempel', {
            'fields': ('started_at', 'completed_at', 'updated_at')
        }),
    )
    
    def get_progress(self, obj):
        return f"{obj.get_progress_percentage()}%"
    get_progress.short_description = 'Fortschritt'


@admin.register(IdeaResponse)
class IdeaResponseAdmin(admin.ModelAdmin):
    list_display = ['session', 'step', 'version', 'source', 'is_accepted', 'is_current', 'created_at']
    list_filter = ['source', 'is_accepted', 'is_current', 'step__content_type']
    search_fields = ['content', 'user_feedback', 'session__title']
    ordering = ['-created_at']
    readonly_fields = ['version', 'parent_response', 'created_at']
    
    fieldsets = (
        ('Zuordnung', {
            'fields': ('session', 'step')
        }),
        ('Inhalt', {
            'fields': ('content', 'source')
        }),
        ('Version', {
            'fields': ('version', 'parent_response', 'is_current')
        }),
        ('AI Interaktion', {
            'fields': ('ai_prompt_used', 'user_feedback'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_accepted', 'created_at')
        }),
    )


# Add IdeaGenerationStep inline to ContentTypeAdmin
ContentTypeAdmin.inlines = [StructureFrameworkInline, IdeaGenerationStepInline]


# =============================================================================
# Workflow Phase LLM Configuration Admin
# =============================================================================

@admin.register(WorkflowPhaseLLMConfig)
class WorkflowPhaseLLMConfigAdmin(admin.ModelAdmin):
    """Admin for configuring LLMs per workflow phase"""
    list_display = ['phase', 'get_phase_display', 'llm', 'fallback_llm', 'is_active', 'updated_at']
    list_filter = ['is_active', 'phase']
    list_editable = ['is_active']
    search_fields = ['phase', 'notes']
    autocomplete_fields = ['llm', 'fallback_llm']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Phase', {
            'fields': ('phase', 'is_active')
        }),
        ('LLM Konfiguration', {
            'fields': ('llm', 'fallback_llm'),
            'description': 'Primäres LLM und Fallback falls primäres nicht verfügbar'
        }),
        ('Notizen', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadaten', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# =============================================================================
# Story Elements Admin (imported from admin_story_elements.py)
# =============================================================================
# This import registers all the new story planning models
from . import admin_story_elements  # noqa: F401, E402

# =============================================================================
# Prompt System Admin (imported from admin_prompt_system.py)
# =============================================================================
# This import registers all prompt system models for image generation
from . import admin_prompt_system  # noqa: F401, E402

# =============================================================================
# Quality System Admin
# =============================================================================
from . import admin_quality  # noqa: F401, E402

# =============================================================================
# Style System Admin
# =============================================================================
try:
    from . import admin_style  # noqa: F401, E402
except ImportError:
    pass  # Models not migrated yet

# =============================================================================
# Lektorats-Framework Admin
# =============================================================================
try:
    from . import admin_lektorat  # noqa: F401, E402
except ImportError:
    pass  # Models not migrated yet

# =============================================================================
# Book Series Admin (Buchreihen/Universes)
# =============================================================================
try:
    from . import admin_series  # noqa: F401, E402
except ImportError:
    pass  # Models not migrated yet


# =============================================================================
# Creative Agent Admin (Kreativ-Phase)
# =============================================================================

class BookIdeaInline(admin.TabularInline):
    model = BookIdea
    extra = 0
    fields = ['title_sketch', 'hook', 'genre', 'user_rating', 'has_full_premise']
    readonly_fields = ['has_full_premise']


class CreativeMessageInline(admin.TabularInline):
    model = CreativeMessage
    extra = 0
    fields = ['sender', 'message_type', 'content', 'created_at']
    readonly_fields = ['created_at']


@admin.register(CreativeSession)
class CreativeSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'author', 'current_phase', 'ideas_count', 'created_at']
    list_filter = ['current_phase', 'created_at']
    search_fields = ['name', 'initial_input']
    readonly_fields = ['id', 'created_at', 'updated_at', 'completed_at']
    inlines = [BookIdeaInline, CreativeMessageInline]
    
    def ideas_count(self, obj):
        return obj.ideas.count()
    ideas_count.short_description = 'Ideen'


@admin.register(BookIdea)
class BookIdeaAdmin(admin.ModelAdmin):
    list_display = ['title_sketch', 'session', 'genre', 'user_rating', 'has_full_premise']
    list_filter = ['user_rating', 'has_full_premise', 'genre']
    search_fields = ['title_sketch', 'hook', 'full_premise']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(CreativeMessage)
class CreativeMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'sender', 'message_type', 'content_preview', 'created_at']
    list_filter = ['sender', 'message_type']
    search_fields = ['content']
    readonly_fields = ['id', 'created_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


# =============================================================================
# Import Framework V2 Admin
# =============================================================================

@admin.register(ImportPromptTemplate)
class ImportPromptTemplateAdmin(admin.ModelAdmin):
    list_display = ['step_code', 'step_name', 'step_order', 'is_active', 'version', 'updated_at']
    list_filter = ['is_active']
    search_fields = ['step_code', 'step_name', 'description']
    ordering = ['step_order', 'step_code']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('step_code', 'step_name', 'step_name_de', 'description', 'step_order')
        }),
        ('Prompts', {
            'fields': ('system_prompt', 'user_prompt_template'),
            'classes': ('wide',)
        }),
        ('Schema & Examples', {
            'fields': ('output_schema', 'example_input', 'example_output'),
            'classes': ('collapse',)
        }),
        ('LLM Settings', {
            'fields': ('temperature', 'max_tokens', 'preferred_model', 'fallback_model')
        }),
        ('Status', {
            'fields': ('is_active', 'version', 'created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(OutlineCategory)
class OutlineCategoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'name_de', 'icon', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name', 'description']
    ordering = ['order', 'name']


@admin.register(OutlineTemplate)
class OutlineTemplateAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'difficulty_level', 'is_featured', 'is_active', 'usage_count']
    list_filter = ['category', 'difficulty_level', 'is_featured', 'is_active']
    search_fields = ['code', 'name', 'description', 'example_books']
    ordering = ['-is_featured', '-usage_count', 'name']
    readonly_fields = ['created_at', 'updated_at', 'usage_count', 'avg_rating']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('code', 'name', 'name_de', 'category', 'description', 'description_de')
        }),
        ('Structure', {
            'fields': ('structure_json',),
            'classes': ('wide',)
        }),
        ('Tags & Matching', {
            'fields': ('genre_tags', 'theme_tags', 'pov_tags', 'word_count_min', 'word_count_max')
        }),
        ('Metadata', {
            'fields': ('difficulty_level', 'example_books', 'pros', 'cons')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured', 'usage_count', 'avg_rating', 'created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(ProjectOutline)
class ProjectOutlineAdmin(admin.ModelAdmin):
    list_display = ['project', 'template', 'version', 'status', 'is_active', 'updated_at']
    list_filter = ['status', 'is_active', 'template']
    search_fields = ['project__title', 'notes']
    ordering = ['-updated_at']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['project', 'template']


@admin.register(ImportSession)
class ImportSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'source_filename', 'status', 'document_type', 'user', 'started_at', 'completed_at']
    list_filter = ['status', 'source_type', 'document_type']
    search_fields = ['session_id', 'source_filename', 'error_message']
    ordering = ['-started_at']
    readonly_fields = ['session_id', 'started_at', 'completed_at', 'total_tokens_used', 'total_llm_cost']
    raw_id_fields = ['user', 'created_project', 'selected_outline_template']
    
    fieldsets = (
        ('Session Info', {
            'fields': ('session_id', 'user', 'source_filename', 'source_type', 'document_type')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Data', {
            'fields': ('raw_content', 'extracted_data', 'selected_items'),
            'classes': ('collapse',)
        }),
        ('Metrics', {
            'fields': ('total_tokens_used', 'total_llm_cost', 'started_at', 'completed_at')
        }),
        ('Result', {
            'fields': ('created_project', 'selected_outline_template')
        }),
    )


class OutlineRecommendationInline(admin.TabularInline):
    model = OutlineRecommendation
    extra = 0
    readonly_fields = ['template', 'rank', 'match_score', 'was_selected', 'created_at']
    can_delete = False


@admin.register(OutlineRecommendation)
class OutlineRecommendationAdmin(admin.ModelAdmin):
    list_display = ['import_session', 'template', 'rank', 'match_score', 'was_selected', 'created_at']
    list_filter = ['was_selected', 'template']
    search_fields = ['import_session__session_id', 'match_reason']
    ordering = ['import_session', 'rank']
    readonly_fields = ['created_at']
    raw_id_fields = ['import_session', 'template']
