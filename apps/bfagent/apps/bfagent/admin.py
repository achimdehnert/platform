"""
Django admin configuration for BF Agent models
Read-only access to existing SQLite database
"""

from django.contrib import admin
from django.utils.html import format_html

# Import Feature Document admin classes
from .admin_feature_documents import FeatureDocumentAdmin, FeatureDocumentKeywordAdmin

# Import Documentation System admin classes
from .admin_documentation import (
    SystemDocumentationAdmin,
    DomainDocumentationAdmin,
    ChangelogEntryAdmin,
    GlossaryTermAdmin,
    DocumentationLinkAdmin,
)

# Import models directly from source files to avoid circular imports
from .models_main import (
    ActionTemplate,
    AgentAction,
    AgentArtifacts,
    AgentExecutions,
    Agents,
    AgentType,
    BookChapters,
    BookProjects,
    BookTypePhase,
    BookTypes,
    ChapterBeat,
    Characters,
    EnrichmentResponse,
    FieldDefinition,
    FieldGroup,
    FieldTemplate,
    FieldUsage,
    FieldValueHistory,
    Genre,
    GraphQLOperation,
    Llms,
    PhaseActionConfig,
    PhaseAgentConfig,
    PlotPoint,
    ProjectFieldValue,
    ProjectPhaseHistory,
    PromptExecution,
    PromptTemplate,
    PromptTemplateLegacy,
    PromptTemplateTest,
    StoryArc,
    StoryBible,
    StoryChapter,
    StoryCharacter,
    StoryStrand,
    TargetAudience,
    TemplateField,
    WorkflowPhase,
    WorkflowPhaseStep,
    WorkflowTemplate,
    Worlds,
    WritingStatus,
)

from .models_handlers import (
    ActionHandler,
    Handler,
    HandlerExecution,
)

from .models_registry import (
    ComponentChangeLog,
    ComponentRegistry,
    ComponentUsageLog,
    MigrationConflict,
    MigrationRegistry,
)

from .models_context_enrichment import (
    ContextEnrichmentLog,
    ContextSchema,
    ContextSource,
)

from .models_domains import DomainArt, DomainPhase, DomainType

from .models_testing import (
    BugFixPlan,
    Initiative,
    InitiativeActivity,
    MCPUsageLog,
    RequirementFeedback,
    RequirementTestLink,
    TestCase,
    TestCaseFeedback,
    TestExecution,
    TestRequirement,
)

# Import Handler admin classes
# TODO: Fix field names before enabling
# from .admin_handlers import HandlerAdmin, ActionHandlerAdmin, HandlerExecutionAdmin


class ReadOnlyAdminMixin:
    """Mixin to make admin interface read-only"""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BookProjects)
class BookProjectsAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    """Admin interface for Book Projects"""

    list_display = [
        "title",
        "genre",
        "status",
        "current_word_count",
        "target_word_count",
        "progress_bar",
        "created_at",
    ]
    list_filter = ["genre", "status", "content_rating", "created_at"]
    search_fields = ["title", "description", "tagline"]
    readonly_fields = [
        "id",
        "title",
        "genre",
        "content_rating",
        "description",
        "tagline",
        "target_word_count",
        "current_word_count",
        "status",
        "deadline",
        "created_at",
        "updated_at",
        "story_premise",
        "target_audience",
        "story_themes",
        "setting_time",
        "setting_location",
        "atmosphere_tone",
        "main_conflict",
        "stakes",
        "protagonist_concept",
        "antagonist_concept",
        "inspiration_sources",
        "unique_elements",
        "genre_settings",
        "book_type_id",
        "progress_bar",
    ]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("title", "genre", "content_rating", "status", "progress_bar")},
        ),
        (
            "Content Details",
            {"fields": ("description", "tagline", "story_premise", "target_audience")},
        ),
        (
            "Story Elements",
            {
                "fields": ("story_themes", "main_conflict", "stakes", "unique_elements"),
                "classes": ("collapse",),
            },
        ),
        (
            "Setting & Atmosphere",
            {
                "fields": ("setting_time", "setting_location", "atmosphere_tone"),
                "classes": ("collapse",),
            },
        ),
        (
            "Characters",
            {"fields": ("protagonist_concept", "antagonist_concept"), "classes": ("collapse",)},
        ),
        ("Progress Tracking", {"fields": ("current_word_count", "target_word_count", "deadline")}),
        (
            "Metadata",
            {"fields": ("created_at", "updated_at", "book_type_id"), "classes": ("collapse",)},
        ),
    )

    def progress_bar(self, obj):
        """Display progress as a visual bar"""
        if obj.target_word_count > 0:
            percentage = min((obj.current_word_count / obj.target_word_count) * 100, 100)
            color = "green" if percentage >= 100 else "orange" if percentage >= 50 else "red"
            return format_html(
                '<div style="width: 200px; background-color: #f0f0f0; border-radius: 3px;">'
                '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 12px; line-height: 20px;">'
                "{}%</div></div>",
                int(percentage),
                color,
                f"{percentage:.1f}",
            )
        return "N/A"

    progress_bar.short_description = "Progress"


@admin.register(Worlds)
class WorldsAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    """Admin interface for Worlds"""

    list_display = ["name", "world_type", "project", "created_at"]
    list_filter = ["world_type", "project"]
    search_fields = ["name", "description", "setting_details"]
    readonly_fields = [
        "id",
        "name",
        "project",
        "world_type",
        "description",
        "setting_details",
        "geography",
        "culture",
        "technology_level",
        "magic_system",
        "politics",
        "history",
        "inhabitants",
        "connections",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "world_type", "project", "description")}),
        ("World Building", {"fields": ("setting_details", "geography", "culture"), "classes": ("collapse",)}),
        ("Systems & Rules", {"fields": ("technology_level", "magic_system", "politics"), "classes": ("collapse",)}),
        ("Background", {"fields": ("history", "inhabitants", "connections"), "classes": ("collapse",)}),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(Agents)
class AgentsAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    """Admin interface for AI Agents"""

    list_display = [
        "name",
        "agent_type",
        "status",
        "success_rate_display",
        "total_requests",
        "average_response_time",
        "last_used_at",
    ]
    list_filter = ["agent_type", "status", "created_at"]
    search_fields = ["name", "description", "agent_type"]
    readonly_fields = [
        "id",
        "name",
        "agent_type",
        "status",
        "description",
        "system_prompt",
        "instructions",
        "llm_model_id",
        "creativity_level",
        "consistency_weight",
        "total_requests",
        "successful_requests",
        "average_response_time",
        "created_at",
        "updated_at",
        "last_used_at",
        "success_rate_display",
    ]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "agent_type", "status", "description")}),
        (
            "Configuration",
            {"fields": ("system_prompt", "instructions", "llm_model_id"), "classes": ("collapse",)},
        ),
        (
            "Parameters",
            {"fields": ("creativity_level", "consistency_weight"), "classes": ("collapse",)},
        ),
        (
            "Performance Metrics",
            {
                "fields": (
                    "total_requests",
                    "successful_requests",
                    "success_rate_display",
                    "average_response_time",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at", "last_used_at"), "classes": ("collapse",)},
        ),
    )

    def success_rate_display(self, obj):
        """Display success rate with color coding"""
        rate = obj.success_rate
        if rate >= 90:
            color = "green"
        elif rate >= 70:
            color = "orange"
        else:
            color = "red"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>', color, rate
        )

    success_rate_display.short_description = "Success Rate"


@admin.register(BookChapters)
class BookChaptersAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    """Admin interface for Book Chapters"""

    list_display = [
        "project",
        "chapter_number",
        "title",
        "status",
        "word_count",
        "target_word_count",
        "updated_at",
    ]
    list_filter = ["status", "project", "updated_at"]
    search_fields = ["title", "summary", "project__title"]
    readonly_fields = [
        "id",
        "project",
        "title",
        "summary",
        "content",
        "chapter_number",
        "status",
        "word_count",
        "target_word_count",
        "notes",
        "outline",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        ("Chapter Information", {"fields": ("project", "chapter_number", "title", "status")}),
        (
            "Content",
            {"fields": ("summary", "content", "notes", "outline"), "classes": ("collapse",)},
        ),
        ("Progress", {"fields": ("word_count", "target_word_count")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(Characters)
class CharactersAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    """Admin interface for Characters"""

    list_display = ["name", "project", "role", "age", "updated_at"]
    list_filter = ["role", "project", "updated_at"]
    search_fields = ["name", "description", "project__title"]
    readonly_fields = [
        "id",
        "project",
        "name",
        "description",
        "role",
        "age",
        "background",
        "personality",
        "appearance",
        "motivation",
        "conflict",
        "arc",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        ("Basic Information", {"fields": ("project", "name", "role", "age")}),
        (
            "Character Details",
            {
                "fields": ("description", "background", "personality", "appearance"),
                "classes": ("collapse",),
            },
        ),
        (
            "Character Development",
            {"fields": ("motivation", "conflict", "arc"), "classes": ("collapse",)},
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(Llms)
class LlmsAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    """Admin interface for LLM configurations"""

    list_display = [
        "name",
        "provider",
        "is_active",
        "total_requests",
        "total_cost",
        "cost_per_1k_tokens",
        "updated_at",
    ]
    list_filter = ["provider", "is_active", "created_at"]
    search_fields = ["name", "provider", "llm_name"]
    readonly_fields = [
        "id",
        "name",
        "provider",
        "llm_name",
        "api_key",
        "api_endpoint",
        "max_tokens",
        "temperature",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "total_tokens_used",
        "total_requests",
        "total_cost",
        "cost_per_1k_tokens",
        "description",
        "is_active",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "provider", "llm_name", "is_active")}),
        ("API Configuration", {"fields": ("api_key", "api_endpoint"), "classes": ("collapse",)}),
        (
            "Model Parameters",
            {
                "fields": (
                    "max_tokens",
                    "temperature",
                    "top_p",
                    "frequency_penalty",
                    "presence_penalty",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Usage Statistics",
            {"fields": ("total_tokens_used", "total_requests", "total_cost", "cost_per_1k_tokens")},
        ),
        (
            "Metadata",
            {"fields": ("description", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(AgentExecutions)
class AgentExecutionsAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    """Admin interface for Agent Executions"""

    list_display = [
        "agent",
        "project",
        "status",
        "field_name",
        "started_at",
        "duration_display",
        "has_error",
    ]
    list_filter = ["status", "agent", "started_at"]
    search_fields = ["agent__name", "project__title", "field_name"]
    readonly_fields = [
        "id",
        "project",
        "agent",
        "status",
        "field_name",
        "content_preview",
        "started_at",
        "completed_at",
        "error_message",
        "duration_display",
    ]

    fieldsets = (
        ("Execution Information", {"fields": ("agent", "project", "status", "field_name")}),
        ("Content", {"fields": ("content_preview",), "classes": ("collapse",)}),
        ("Timing", {"fields": ("started_at", "completed_at", "duration_display")}),
        ("Error Information", {"fields": ("error_message",), "classes": ("collapse",)}),
    )

    def duration_display(self, obj):
        """Display execution duration"""
        duration = obj.duration
        if duration:
            total_seconds = int(duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return "N/A"

    duration_display.short_description = "Duration"

    def has_error(self, obj):
        """Display error status"""
        if obj.error_message:
            return format_html('<span style="color: red;">✗ Error</span>')
        return format_html('<span style="color: green;">✓ OK</span>')

    has_error.short_description = "Status"


@admin.register(PhaseAgentConfig)
class PhaseAgentConfigAdmin(admin.ModelAdmin):
    """Admin interface for Phase-Agent Configurations"""

    list_display = [
        "phase",
        "agent",
        "agent_type_display",
        "action_count",
        "is_required",
        "order",
    ]

    list_filter = [
        ("phase", admin.RelatedOnlyFieldListFilter),
        ("agent__agent_type", admin.ChoicesFieldListFilter),
        "is_required",
    ]

    search_fields = [
        "phase__name",
        "agent__name",
        "agent__agent_type",
    ]

    ordering = ["phase__name", "order", "agent__name"]

    readonly_fields = [
        "phase",
        "agent",
        "agent_type_display",
        "action_count",
        "action_list",
    ]

    fieldsets = (
        (
            "Mapping",
            {"fields": ("phase", "agent", "agent_type_display")},
        ),
        (
            "Configuration",
            {"fields": ("is_required", "order", "description")},
        ),
        (
            "Actions",
            {"fields": ("action_count", "action_list")},
        ),
    )

    def agent_type_display(self, obj):
        """Display agent type"""
        return obj.agent.agent_type

    agent_type_display.short_description = "Agent Type"
    agent_type_display.admin_order_field = "agent__agent_type"

    def action_count(self, obj):
        """Count actions for this agent"""
        count = AgentAction.objects.filter(agent=obj.agent).count()
        if count == 0:
            return format_html('<span style="color: red;">⚠ 0 actions</span>')
        return format_html('<span style="color: green;">✓ {} actions</span>', count)

    action_count.short_description = "Actions"

    def action_list(self, obj):
        """List all actions for this agent"""
        actions = AgentAction.objects.filter(agent=obj.agent).order_by("order", "name")
        if not actions.exists():
            return format_html('<span style="color: red;">No actions available</span>')

        action_html = "<ul>"
        for action in actions:
            action_html += f"<li>{action.display_name} ({action.name})</li>"
        action_html += "</ul>"
        return format_html(action_html)

    action_list.short_description = "Available Actions"


# ============================================================================
# PROMPT MANAGEMENT SYSTEM V2.0
# ============================================================================


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    """Admin interface for Prompt Templates v2.0"""

    list_display = [
        "template_key",
        "version",
        "name",
        "category",
        "llm_display",
        "is_active",
        "is_default",
        "usage_display",
        "success_rate",
        "created_at",
    ]

    list_filter = [
        "category",
        "preferred_llm",
        "is_active",
        "is_default",
        "ab_test_group",
        "language",
        "created_at",
    ]

    search_fields = [
        "template_key",
        "name",
        "description",
        "system_prompt",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
        "usage_count",
        "success_count",
        "failure_count",
        "avg_confidence",
        "avg_execution_time",
        "avg_tokens_used",
        "avg_cost",
    ]

    fieldsets = (
        (
            "Identification",
            {
                "fields": (
                    "template_key",
                    "version",
                    "name",
                    "description",
                    "category",
                )
            },
        ),
        (
            "Template Content",
            {
                "fields": (
                    "system_prompt",
                    "user_prompt_template",
                    "output_format",
                    "output_schema",
                )
            },
        ),
        (
            "Variables",
            {
                "fields": (
                    "required_variables",
                    "optional_variables",
                    "variable_defaults",
                )
            },
        ),
        (
            "LLM Configuration",
            {
                "fields": (
                    "preferred_llm",
                    "temperature",
                    "top_p",
                    "max_tokens",
                    "frequency_penalty",
                    "presence_penalty",
                )
            },
        ),
        (
            "Status & Testing",
            {
                "fields": (
                    "is_active",
                    "is_default",
                    "ab_test_group",
                    "ab_test_weight",
                    "language",
                )
            },
        ),
        (
            "Relationships",
            {
                "fields": (
                    "parent_template",
                    "fallback_template",
                    "created_by",
                )
            },
        ),
        (
            "🔧 AgentSkills.io Integration",
            {
                "classes": ("collapse",),
                "description": "Felder für AgentSkills.io Standard-Konformität. "
                              "Siehe: https://agentskills.io/specification",
                "fields": (
                    "skill_description",
                    "compatibility",
                    ("license", "author"),
                    "allowed_tools",
                    "references",
                    "agent_class",
                ),
            },
        ),
        (
            "Performance Metrics",
            {
                "fields": (
                    "usage_count",
                    "success_count",
                    "failure_count",
                    "avg_confidence",
                    "avg_execution_time",
                    "avg_tokens_used",
                    "avg_cost",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    def usage_display(self, obj):
        """Display usage statistics"""
        if obj.usage_count == 0:
            return format_html('<span style="color: gray;">Not used yet</span>')
        return format_html(
            '<span style="color: blue;"><strong>{}</strong> uses</span>', obj.usage_count
        )

    usage_display.short_description = "Usage"
    usage_display.admin_order_field = "usage_count"

    def llm_display(self, obj):
        """Display preferred LLM with fallback indicator"""
        if obj.preferred_llm:
            return format_html(
                '<span style="color: green;"><strong>{}</strong></span>', obj.preferred_llm.name
            )
        return format_html(
            '<span style="color: gray;" title="Uses agent/system default">Default</span>'
        )

    llm_display.short_description = "LLM"
    llm_display.admin_order_field = "preferred_llm"

    def success_rate(self, obj):
        """Calculate and display success rate"""
        if obj.usage_count == 0:
            return "-"

        rate = (obj.success_count / obj.usage_count) * 100

        if rate >= 90:
            color = "green"
        elif rate >= 70:
            color = "orange"
        else:
            color = "red"

        return format_html('<span style="color: {};">{}</span>', color, f"{rate:.1f}%")

    success_rate.short_description = "Success Rate"


@admin.register(PromptExecution)
class PromptExecutionAdmin(admin.ModelAdmin):
    """Admin interface for Prompt Executions - Read-only audit trail"""

    list_display = [
        "id",
        "template_link",
        "target_display",
        "confidence_badge",
        "user_accepted",
        "created_at",
    ]

    list_filter = [
        "template__template_key",
        "template__category",
        "user_accepted",
        "user_edited",
        "created_at",
    ]

    search_fields = [
        "template__template_key",
        "template__name",
        "target_model",
        "rendered_prompt",
    ]

    readonly_fields = [
        "template",
        "target_model",
        "target_id",
        "rendered_prompt",
        "context_used",
        "llm_response",
        "parsed_output",
        "confidence_score",
        "user_accepted",
        "user_edited",
        "execution_time",
        "tokens_used",
        "cost",
        "error_message",
        "retry_of",
        "created_at",
    ]

    fieldsets = (
        (
            "Execution Info",
            {
                "fields": (
                    "template",
                    "target_model",
                    "target_id",
                    "created_at",
                )
            },
        ),
        (
            "Prompt & Response",
            {
                "fields": (
                    "rendered_prompt",
                    "llm_response",
                    "parsed_output",
                )
            },
        ),
        (
            "Context",
            {"fields": ("context_used",)},
        ),
        (
            "Quality Metrics",
            {
                "fields": (
                    "confidence_score",
                    "user_accepted",
                    "user_edited",
                )
            },
        ),
        (
            "Performance",
            {
                "fields": (
                    "execution_time",
                    "tokens_used",
                    "cost",
                )
            },
        ),
        (
            "Error Handling",
            {
                "fields": (
                    "error_message",
                    "retry_of",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        """Executions are created programmatically only"""
        return False

    def has_change_permission(self, request, obj=None):
        """Executions are read-only audit trail"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Keep audit trail intact"""
        return request.user.is_superuser

    def template_link(self, obj):
        """Link to template"""
        return format_html(
            '<a href="/admin/bfagent/prompttemplate/{}/change/">{} (v{})</a>',
            obj.template.id,
            obj.template.template_key,
            obj.template.version,
        )

    template_link.short_description = "Template"

    def target_display(self, obj):
        """Display target model and ID"""
        return format_html("<code>{}</code> #{}", obj.target_model, obj.target_id)

    target_display.short_description = "Target"

    def confidence_badge(self, obj):
        """Display confidence score with color coding"""
        if obj.confidence_score is None:
            return "-"

        score = obj.confidence_score

        if score >= 0.9:
            color = "green"
        elif score >= 0.7:
            color = "orange"
        else:
            color = "red"

        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.2f}</span>', color, score
        )

    confidence_badge.short_description = "Confidence"
    confidence_badge.admin_order_field = "confidence_score"


@admin.register(PromptTemplateTest)
class PromptTemplateTestAdmin(admin.ModelAdmin):
    """Admin interface for Template Testing"""

    list_display = [
        "name",
        "template_link",
        "is_active",
        "test_status",
        "last_run_at",
        "created_at",
    ]

    list_filter = ["is_active", "last_run_passed", "created_at"]

    search_fields = ["name", "description", "template__template_key"]

    readonly_fields = [
        "last_run_at",
        "last_run_passed",
        "last_run_output",
        "last_run_error",
        "created_at",
    ]

    fieldsets = (
        (
            "Test Info",
            {
                "fields": (
                    "template",
                    "name",
                    "description",
                    "is_active",
                )
            },
        ),
        (
            "Test Input",
            {"fields": ("test_context",)},
        ),
        (
            "Expected Output",
            {
                "fields": (
                    "expected_output_contains",
                    "expected_output_not_contains",
                    "expected_min_length",
                    "expected_max_length",
                )
            },
        ),
        (
            "Last Run Results",
            {
                "fields": (
                    "last_run_at",
                    "last_run_passed",
                    "last_run_output",
                    "last_run_error",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at",)},
        ),
    )

    def template_link(self, obj):
        """Link to template"""
        return format_html(
            '<a href="/admin/bfagent/prompttemplate/{}/change/">{}</a>',
            obj.template.id,
            obj.template.template_key,
        )

    template_link.short_description = "Template"

    def test_status(self, obj):
        """Display test status with color coding"""
        if obj.last_run_passed is None:
            return format_html('<span style="color: gray;">Not run yet</span>')
        elif obj.last_run_passed:
            return format_html('<span style="color: green; font-weight: bold;">✓ PASSED</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">✗ FAILED</span>')

    test_status.short_description = "Status"
    test_status.admin_order_field = "last_run_passed"


@admin.register(PromptTemplateLegacy)
class PromptTemplateLegacyAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    """Admin interface for Legacy Templates (read-only)"""

    list_display = [
        "id",
        "name",
        "agent",
        "usage_count",
        "created_at",
    ]

    list_filter = ["agent", "created_at"]

    search_fields = ["name", "template_text"]


# ============================================================================
# COMPONENT & MIGRATION REGISTRY
# ============================================================================


@admin.register(ComponentRegistry)
class ComponentRegistryAdmin(admin.ModelAdmin):
    """Admin interface for Component Registry / Feature Planning"""

    list_display = [
        "name",
        "status",
        "priority_badge",
        "component_type",
        "domain",
        "owner",
        "proposed_at",
    ]

    list_filter = [
        "status",
        "priority",
        "component_type",
        "domain",
        "owner",
    ]

    search_fields = ["name", "description", "identifier", "module_path"]

    readonly_fields = [
        "proposed_at",
        "planned_at",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "identifier", "component_type", "domain", "description")},
        ),
        ("Feature Planning", {"fields": ("status", "priority", "owner")}),
        (
            "Timeline",
            {
                "fields": ("proposed_at", "planned_at", "started_at", "completed_at"),
                "classes": ("collapse",),
            },
        ),
        (
            "Technical Details",
            {
                "fields": (
                    "module_path",
                    "file_path",
                    "class_name",
                    "input_schema",
                    "output_schema",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def priority_badge(self, obj):
        """Display priority with colored badge"""
        colors = {
            "critical": "red",
            "high": "orange",
            "medium": "blue",
            "low": "green",
            "backlog": "gray",
        }
        color = colors.get(obj.priority, "gray")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_priority_display(),
        )

    priority_badge.short_description = "Priority"


@admin.register(MigrationRegistry)
class MigrationRegistryAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    """Admin interface for Migration Registry (Read-Only)"""

    list_display = [
        "migration_name",
        "app_label",
        "is_applied",
        "complexity_badge",
        "risk_level",
        "migration_type",
        "discovered_at",
    ]

    list_filter = [
        "is_applied",
        "app_label",
        "migration_type",
        "is_reversible",
        "requires_downtime",
    ]

    search_fields = ["migration_name", "app_label", "description"]

    readonly_fields = ["discovered_at", "applied_at", "updated_at"]

    def complexity_badge(self, obj):
        """Display complexity score with color"""
        if obj.complexity_score >= 71:
            color = "red"
        elif obj.complexity_score >= 51:
            color = "orange"
        elif obj.complexity_score >= 31:
            color = "blue"
        else:
            color = "green"
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.complexity_score,
        )

    complexity_badge.short_description = "Complexity"

    def risk_level(self, obj):
        """Display risk level"""
        if obj.complexity_score >= 71:
            return "🚨 Critical"
        elif obj.complexity_score >= 51:
            return "🔥 Risky"
        elif obj.complexity_score >= 31:
            return "⚠️ Careful"
        else:
            return "✅ Safe"

    risk_level.short_description = "Risk"


# Import Context Enrichment Admin configurations
from .admin_context_enrichment import (
    ContextEnrichmentLogAdmin,
    ContextSchemaAdmin,
    ContextSourceAdmin,
)

# Import Illustration System Admin configurations
from .admin_illustration import (
    IllustrationImageAdmin,
    ImageGenerationBatchAdmin,
    ImageStyleProfileAdmin,
)

# ============================================================================
# TESTING & BUG FIX SYSTEM ADMIN
# ============================================================================


@admin.register(BugFixPlan)
class BugFixPlanAdmin(admin.ModelAdmin):
    """Admin for Bug Fix Plans"""

    list_display = [
        "fix_type",
        "requirement",
        "status",
        "created_at",
        "approved_by",
        "rollback_possible",
    ]
    list_filter = ["status", "fix_type", "rollback_possible", "created_at"]
    search_fields = ["fix_description", "handler_id", "requirement__name"]
    readonly_fields = ["created_at", "approved_at", "executed_at"]

    fieldsets = (
        ("Fix Details", {"fields": ("requirement", "fix_type", "fix_description", "fix_actions")}),
        ("Handler", {"fields": ("handler_id", "handler_code")}),
        ("Status & Approval", {"fields": ("status", "created_by", "approved_by", "approved_at")}),
        ("Execution", {"fields": ("execution_result", "execution_log", "executed_at")}),
        ("Rollback", {"fields": ("rollback_possible", "rollback_data")}),
        ("Timestamps", {"fields": ("created_at",)}),
    )


class InitiativeActivityInline(admin.TabularInline):
    """Inline for Initiative Activities"""
    model = InitiativeActivity
    extra = 0
    readonly_fields = ["action", "details", "actor", "mcp_tool_used", "tokens_used", "created_at"]
    can_delete = False
    ordering = ["-created_at"]
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Initiative)
class InitiativeAdmin(admin.ModelAdmin):
    """Admin for Initiatives/Epics"""
    
    list_display = ["title", "domain", "priority", "status", "workflow_phase", "requirements_count", "progress_display", "created_at"]
    list_filter = ["status", "workflow_phase", "priority", "domain", "created_at"]
    search_fields = ["title", "description", "analysis", "concept", "lessons_learned"]
    readonly_fields = ["id", "created_at", "updated_at", "requirements_count", "progress_display"]
    raw_id_fields = ["created_by"]
    inlines = [InitiativeActivityInline]
    
    fieldsets = (
        (None, {"fields": ("id", "title", "description")}),
        ("Analyse & Konzept", {"fields": ("analysis", "concept"), "classes": ("collapse",)}),
        ("Klassifizierung", {"fields": ("domain", "priority", "status", "workflow_phase", "tags")}),
        ("Workflow & Dokumentation", {
            "fields": ("next_steps", "blockers", "lessons_learned"),
            "classes": ("collapse",),
        }),
        ("Referenzen", {
            "fields": ("related_files", "related_urls"),
            "classes": ("collapse",),
        }),
        ("Fortschritt", {"fields": ("estimated_hours", "requirements_count", "progress_display")}),
        ("Metadaten", {"fields": ("created_by", "created_at", "updated_at")}),
    )
    
    def requirements_count(self, obj):
        return obj.requirements_count
    requirements_count.short_description = "Requirements"
    
    def progress_display(self, obj):
        pct = obj.progress_percentage
        return f"{obj.completed_requirements}/{obj.requirements_count} ({pct}%)"
    progress_display.short_description = "Fortschritt"


@admin.register(InitiativeActivity)
class InitiativeActivityAdmin(admin.ModelAdmin):
    """Admin for Initiative Activities"""
    
    list_display = ["initiative_short", "action", "actor", "mcp_tool_used", "tokens_used", "created_at"]
    list_filter = ["action", "actor", "mcp_tool_used", "created_at"]
    search_fields = ["details", "initiative__title"]
    readonly_fields = ["created_at"]
    raw_id_fields = ["initiative"]
    
    def initiative_short(self, obj):
        return obj.initiative.title[:40]
    initiative_short.short_description = "Initiative"


@admin.register(MCPUsageLog)
class MCPUsageLogAdmin(admin.ModelAdmin):
    """Admin for MCP Usage Logs - Transparency Dashboard"""
    
    list_display = [
        "tool_name", "tool_category", "status_badge", 
        "duration_display", "tokens_display", "cost_display",
        "initiative_short", "created_at"
    ]
    list_filter = ["tool_name", "tool_category", "status", "created_at"]
    search_fields = ["tool_name", "result_summary", "error_message", "session_id"]
    readonly_fields = ["created_at", "id"]
    raw_id_fields = ["initiative", "requirement", "user"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    
    fieldsets = (
        ("Tool Info", {
            "fields": ("tool_name", "tool_category", "status", "id")
        }),
        ("Invocation", {
            "fields": ("arguments", "result_summary", "error_message")
        }),
        ("Context", {
            "fields": ("initiative", "requirement", "user", "session_id"),
            "classes": ("collapse",)
        }),
        ("LLM Usage", {
            "fields": ("llm_model", "tokens_input", "tokens_output", "tokens_total", "estimated_cost"),
            "classes": ("collapse",)
        }),
        ("Timing", {
            "fields": ("duration_ms", "created_at")
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'success': 'green',
            'error': 'red',
            'timeout': 'orange',
            'cancelled': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def duration_display(self, obj):
        if obj.duration_ms > 1000:
            return f"{obj.duration_ms / 1000:.1f}s"
        return f"{obj.duration_ms}ms"
    duration_display.short_description = "Dauer"
    
    def tokens_display(self, obj):
        if obj.tokens_total:
            return f"{obj.tokens_total:,}"
        return "-"
    tokens_display.short_description = "Tokens"
    
    def cost_display(self, obj):
        if obj.estimated_cost:
            return f"${obj.estimated_cost:.4f}"
        return "-"
    cost_display.short_description = "Kosten"
    
    def initiative_short(self, obj):
        if obj.initiative:
            return obj.initiative.title[:25] + "..."
        return "-"
    initiative_short.short_description = "Initiative"


@admin.register(TestRequirement)
class TestRequirementAdmin(admin.ModelAdmin):
    """Admin for Test Requirements"""

    list_display = ["name", "priority", "status", "dependency_display", "initiative", "domain", "created_at"]
    list_filter = ["priority", "status", "domain", "initiative", "created_at"]
    search_fields = ["name", "description"]
    raw_id_fields = ["initiative", "depends_on"]
    autocomplete_fields = ["depends_on"]
    
    def dependency_display(self, obj):
        if not obj.depends_on:
            return "-"
        icon = "✅" if obj.can_start else "⏳"
        return format_html('{} <a href="/admin/bfagent/testrequirement/{}/change/">{}</a>', 
                          icon, obj.depends_on.pk, obj.depends_on.name[:20])
    dependency_display.short_description = "Abhängig von"


@admin.register(RequirementFeedback)
class RequirementFeedbackAdmin(admin.ModelAdmin):
    """Admin for Requirement Feedback"""

    list_display = ["requirement_short", "feedback_type_badge", "author", "content_short", "is_from_cascade", "created_at"]
    list_filter = ["feedback_type", "is_from_cascade", "created_at"]
    search_fields = ["content", "requirement__name", "author__username"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["requirement", "author"]
    ordering = ["-created_at"]
    
    def requirement_short(self, obj):
        return obj.requirement.name[:40] + "..." if len(obj.requirement.name) > 40 else obj.requirement.name
    requirement_short.short_description = "Requirement"
    
    def content_short(self, obj):
        return obj.content[:60] + "..." if len(obj.content) > 60 else obj.content
    content_short.short_description = "Content"
    
    def feedback_type_badge(self, obj):
        colors = {
            'comment': 'info',
            'progress': 'success',
            'blocker': 'danger',
            'question': 'warning',
            'solution': 'primary',
            'screenshot': 'secondary',
        }
        color = colors.get(obj.feedback_type, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_feedback_type_display()
        )
    feedback_type_badge.short_description = "Type"


@admin.register(TestCaseFeedback)
class TestCaseFeedbackAdmin(admin.ModelAdmin):
    """Admin for Test Case Feedback"""

    list_display = ["testcase_short", "feedback_type_badge", "author", "content_short", "is_from_cascade", "created_at"]
    list_filter = ["feedback_type", "is_from_cascade", "created_at"]
    search_fields = ["content", "test_case__name", "author__username"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["test_case", "author"]
    ordering = ["-created_at"]
    
    def testcase_short(self, obj):
        return obj.test_case.name[:40] + "..." if len(obj.test_case.name) > 40 else obj.test_case.name
    testcase_short.short_description = "Test Case"
    
    def content_short(self, obj):
        return obj.content[:60] + "..." if len(obj.content) > 60 else obj.content
    content_short.short_description = "Content"
    
    def feedback_type_badge(self, obj):
        colors = {
            'comment': 'info',
            'progress': 'success',
            'blocker': 'danger',
            'question': 'warning',
            'solution': 'primary',
            'screenshot': 'secondary',
            'bug': 'danger',
            'flaky': 'warning',
        }
        color = colors.get(obj.feedback_type, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_feedback_type_display()
        )
    feedback_type_badge.short_description = "Type"


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    """Admin for Test Cases"""

    list_display = ["test_id", "name", "framework", "status", "is_auto_generated"]
    list_filter = ["framework", "status", "test_type", "is_auto_generated"]
    search_fields = ["test_id", "name", "description"]


@admin.register(TestExecution)
class TestExecutionAdmin(admin.ModelAdmin):
    """Admin for Test Executions"""

    list_display = ["test_case", "result", "executed_at", "executed_by", "duration"]
    list_filter = ["result", "executed_at"]
    search_fields = ["test_case__test_id", "test_case__name"]
    readonly_fields = ["executed_at"]


# ============================================================================
# MULTI-HUB FRAMEWORK - DOMAIN MODELS ADMIN
# ============================================================================


class DomainTypeInline(admin.TabularInline):
    """Inline admin for DomainTypes within DomainArt"""

    model = DomainType
    extra = 0
    fields = ["name", "slug", "display_name", "icon", "color", "is_active", "sort_order"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["sort_order", "name"]


class DomainPhaseInline(admin.TabularInline):
    """Inline admin for DomainPhases within DomainType"""

    model = DomainPhase
    extra = 0
    fields = ["workflow_phase", "sort_order", "is_active", "is_required"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["sort_order"]


@admin.register(DomainArt)
class DomainArtAdmin(admin.ModelAdmin):
    """Admin interface for Domain Arts (Hubs)"""

    list_display = [
        "display_name",
        "name",
        "colored_badge",
        "status_display",
        "type_count",
        "created_at",
    ]

    list_filter = ["is_active", "is_experimental", "created_at"]

    search_fields = ["name", "display_name", "description"]

    readonly_fields = ["created_at", "updated_at"]

    inlines = [DomainTypeInline]

    fieldsets = (
        ("Hub Identity", {"fields": ("name", "slug", "display_name", "description")}),
        ("Visual Configuration", {"fields": ("icon", "color")}),
        ("Status", {"fields": ("is_active", "is_experimental")}),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def colored_badge(self, obj):
        """Display hub with its color"""
        colors = {
            "primary": "#0d6efd",
            "success": "#198754",
            "info": "#0dcaf0",
            "warning": "#ffc107",
            "secondary": "#6c757d",
        }
        color = colors.get(obj.color, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; '
            'border-radius: 4px; font-weight: bold;">'
            '<i class="bi bi-{}"></i> {}</span>',
            color,
            obj.icon or "circle",
            obj.display_name,
        )

    colored_badge.short_description = "Hub Badge"

    def status_display(self, obj):
        """Display status with badges"""
        badges = []
        if obj.is_active:
            badges.append('<span style="color: green;">✓ Active</span>')
        else:
            badges.append('<span style="color: red;">✗ Inactive</span>')

        if obj.is_experimental:
            badges.append('<span style="color: orange;">🧪 Experimental</span>')

        return format_html(" ".join(badges))

    status_display.short_description = "Status"

    def type_count(self, obj):
        """Count of domain types"""
        count = obj.domain_types.count()
        if count == 0:
            return format_html('<span style="color: gray;">No types</span>')
        return format_html(
            '<span style="color: blue; font-weight: bold;">{} type{}</span>',
            count,
            "s" if count != 1 else "",
        )

    type_count.short_description = "Types"

    actions = ["activate_domains", "deactivate_domains", "mark_experimental"]

    def activate_domains(self, request, queryset):
        """Activate selected domains"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} domain(s) activated.")

    activate_domains.short_description = "Activate selected domains"

    def deactivate_domains(self, request, queryset):
        """Deactivate selected domains"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} domain(s) deactivated.")

    deactivate_domains.short_description = "Deactivate selected domains"

    def mark_experimental(self, request, queryset):
        """Mark domains as experimental"""
        updated = queryset.update(is_experimental=True)
        self.message_user(request, f"{updated} domain(s) marked as experimental.")

    mark_experimental.short_description = "Mark as experimental"


@admin.register(DomainType)
class DomainTypeAdmin(admin.ModelAdmin):
    """Admin interface for Domain Types"""

    list_display = [
        "display_name",
        "domain_art",
        "name",
        "visual_badge",
        "is_active",
        "sort_order",
        "phase_count",
    ]

    list_filter = [
        ("domain_art", admin.RelatedOnlyFieldListFilter),
        "is_active",
        "created_at",
    ]

    search_fields = ["name", "display_name", "description", "domain_art__name"]

    readonly_fields = [
        "created_at",
        "updated_at",
        "effective_icon_display",
        "effective_color_display",
    ]

    inlines = [DomainPhaseInline]

    ordering = ["domain_art", "sort_order", "name"]

    fieldsets = (
        (
            "Type Identity",
            {"fields": ("domain_art", "name", "slug", "display_name", "description")},
        ),
        (
            "Visual Configuration",
            {
                "fields": ("icon", "color", "effective_icon_display", "effective_color_display"),
                "description": "Leave icon/color empty to inherit from domain art",
            },
        ),
        ("Configuration", {"fields": ("config", "is_active", "sort_order")}),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def visual_badge(self, obj):
        """Display type with visual badge"""
        icon = obj.effective_icon
        color = obj.effective_color
        colors = {
            "primary": "#0d6efd",
            "success": "#198754",
            "info": "#0dcaf0",
            "warning": "#ffc107",
            "secondary": "#6c757d",
        }
        bg_color = colors.get(color, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">'
            '<i class="bi bi-{}"></i> {}</span>',
            bg_color,
            icon or "circle",
            obj.display_name,
        )

    visual_badge.short_description = "Badge"

    def phase_count(self, obj):
        """Count of linked phases"""
        count = obj.domain_phases.count()
        if count == 0:
            return format_html('<span style="color: orange;">⚠ No phases</span>')
        return format_html(
            '<span style="color: green;">✓ {} phase{}</span>', count, "s" if count != 1 else ""
        )

    phase_count.short_description = "Phases"

    def effective_icon_display(self, obj):
        """Show effective icon with inheritance info"""
        if obj.icon:
            return format_html("<code>{}</code> (custom)", obj.icon)
        return format_html(
            '<code>{}</code> <span style="color: gray;">(inherited from {})</span>',
            obj.domain_art.icon,
            obj.domain_art.display_name,
        )

    effective_icon_display.short_description = "Effective Icon"

    def effective_color_display(self, obj):
        """Show effective color with inheritance info"""
        color = obj.effective_color
        colors = {
            "primary": "#0d6efd",
            "success": "#198754",
            "info": "#0dcaf0",
            "warning": "#ffc107",
            "secondary": "#6c757d",
        }
        bg_color = colors.get(color, "#6c757d")

        if obj.color:
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 8px; '
                'border-radius: 3px;">{}</span> (custom)',
                bg_color,
                color,
            )
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px;">{}</span> '
            '<span style="color: gray;">(inherited from {})</span>',
            bg_color,
            color,
            obj.domain_art.display_name,
        )

    effective_color_display.short_description = "Effective Color"

    actions = ["activate_types", "deactivate_types"]

    def activate_types(self, request, queryset):
        """Activate selected types"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} type(s) activated.")

    activate_types.short_description = "Activate selected types"

    def deactivate_types(self, request, queryset):
        """Deactivate selected types"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} type(s) deactivated.")

    deactivate_types.short_description = "Deactivate selected types"


@admin.register(DomainPhase)
class DomainPhaseAdmin(admin.ModelAdmin):
    """Admin interface for Domain Phases"""

    list_display = [
        "phase_link",
        "domain_type",
        "workflow_phase",
        "sort_order",
        "status_badges",
        "created_at",
    ]

    list_filter = [
        ("domain_type__domain_art", admin.RelatedOnlyFieldListFilter),
        ("domain_type", admin.RelatedOnlyFieldListFilter),
        "is_active",
        "is_required",
        "created_at",
    ]

    search_fields = [
        "domain_type__name",
        "domain_type__display_name",
        "workflow_phase__name",
    ]

    readonly_fields = ["created_at", "updated_at"]

    ordering = ["domain_type__domain_art", "domain_type", "sort_order"]

    fieldsets = (
        ("Phase Mapping", {"fields": ("domain_type", "workflow_phase", "sort_order")}),
        ("Configuration", {"fields": ("config", "is_active", "is_required")}),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def phase_link(self, obj):
        """Display as clickable link"""
        return format_html(
            "<strong>{}</strong> → {}", obj.domain_type.display_name, obj.workflow_phase.name
        )

    phase_link.short_description = "Phase Link"

    def status_badges(self, obj):
        """Display status badges"""
        badges = []

        if obj.is_active:
            badges.append('<span style="color: green;">✓ Active</span>')
        else:
            badges.append('<span style="color: gray;">○ Inactive</span>')

        if obj.is_required:
            badges.append('<span style="color: red;">★ Required</span>')
        else:
            badges.append('<span style="color: blue;">☆ Optional</span>')

        return format_html(" ".join(badges))

    status_badges.short_description = "Status"

    actions = ["activate_phases", "deactivate_phases", "mark_required", "mark_optional"]

    def activate_phases(self, request, queryset):
        """Activate selected phases"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} phase(s) activated.")

    activate_phases.short_description = "Activate selected phases"

    def deactivate_phases(self, request, queryset):
        """Deactivate selected phases"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} phase(s) deactivated.")

    deactivate_phases.short_description = "Deactivate selected phases"

    def mark_required(self, request, queryset):
        """Mark phases as required"""
        updated = queryset.update(is_required=True)
        self.message_user(request, f"{updated} phase(s) marked as required.")

    mark_required.short_description = "Mark as required"

    def mark_optional(self, request, queryset):
        """Mark phases as optional"""
        updated = queryset.update(is_required=False)
        self.message_user(request, f"{updated} phase(s) marked as optional.")

    mark_optional.short_description = "Mark as optional"


# ============================================================================
# STORY ENGINE - AI Novel Generation System
# ============================================================================


@admin.register(StoryBible)
class StoryBibleAdmin(admin.ModelAdmin):
    """Admin interface for Story Bibles"""

    list_display = [
        "title",
        "genre",
        "status",
        "target_word_count",
        "strand_count",
        "character_count",
        "created_at",
    ]

    list_filter = ["status", "genre", "created_at"]
    search_fields = ["title", "subtitle", "description"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Basic Info",
            {"fields": ("title", "subtitle", "genre", "target_word_count", "created_by")},
        ),
        (
            "World Building",
            {
                "fields": ("scientific_concepts", "world_rules", "technology_levels"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timeline",
            {
                "fields": ("timeline", "timeline_start_year", "timeline_end_year"),
                "classes": ("collapse",),
            },
        ),
        (
            "Style Guide",
            {"fields": ("prose_style", "tone", "pacing_profile"), "classes": ("collapse",)},
        ),
        ("Status", {"fields": ("status",)}),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def strand_count(self, obj):
        return obj.strands.count()

    strand_count.short_description = "Strands"

    def character_count(self, obj):
        return obj.characters.count()

    character_count.short_description = "Characters"


@admin.register(StoryStrand)
class StoryStrandAdmin(admin.ModelAdmin):
    """Admin interface for Story Strands"""

    list_display = [
        "name",
        "story_bible",
        "order",
        "starts_in_book",
        "ends_in_book",
        "beat_count",
        "chapter_count",
    ]

    list_filter = ["story_bible", "starts_in_book", "ends_in_book"]
    search_fields = ["name", "focus", "core_theme"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Basic Info", {"fields": ("story_bible", "name", "order")}),
        ("Story Focus", {"fields": ("focus", "genre_weights", "core_theme", "primary_character")}),
        ("Timeline", {"fields": ("starts_in_book", "ends_in_book")}),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def beat_count(self, obj):
        return obj.beats.count()

    beat_count.short_description = "Beats"

    def chapter_count(self, obj):
        return obj.chapters.count()

    chapter_count.short_description = "Chapters"


@admin.register(StoryCharacter)
class StoryCharacterAdmin(admin.ModelAdmin):
    """Admin interface for Story Characters"""

    list_display = [
        "name",
        "story_bible",
        "age",
        "trait_count",
        "skill_count",
        "created_at",
    ]

    list_filter = ["story_bible", "created_at"]
    search_fields = ["name", "full_name", "biography"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Basic Info", {"fields": ("story_bible", "name", "full_name", "age")}),
        (
            "Attributes",
            {"fields": ("physical_traits", "personality_traits", "skills", "relationships")},
        ),
        (
            "Descriptions",
            {"fields": ("biography", "psychological_profile"), "classes": ("collapse",)},
        ),
        ("Character Arc", {"fields": ("character_arc",), "classes": ("collapse",)}),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def trait_count(self, obj):
        return len(obj.personality_traits) if obj.personality_traits else 0

    trait_count.short_description = "Traits"

    def skill_count(self, obj):
        return len(obj.skills) if obj.skills else 0

    skill_count.short_description = "Skills"


@admin.register(ChapterBeat)
class ChapterBeatAdmin(admin.ModelAdmin):
    """Admin interface for Chapter Beats"""

    list_display = [
        "beat_number",
        "title",
        "strand",
        "order",
        "target_word_count",
        "tension_level",
        "chapter_generated",
    ]

    list_filter = ["story_bible", "strand", "tension_level"]
    search_fields = ["title", "description"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["strand", "order"]

    fieldsets = (
        ("Basic Info", {"fields": ("story_bible", "strand", "beat_number", "title", "order")}),
        (
            "Description",
            {"fields": ("description", "key_events", "character_focus", "emotional_tone")},
        ),
        ("Generation Targets", {"fields": ("target_word_count", "tension_level")}),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def chapter_generated(self, obj):
        count = obj.generated_chapters.count()
        if count > 0:
            return format_html('<span style="color: green;">✓ {} version(s)</span>', count)
        return format_html('<span style="color: gray;">○ Not generated</span>')

    chapter_generated.short_description = "Status"


@admin.register(StoryChapter)
class StoryChapterAdmin(admin.ModelAdmin):
    """Admin interface for Story Chapters"""

    list_display = [
        "chapter_number",
        "title",
        "strand",
        "word_count",
        "status",
        "version",
        "quality_display",
        "created_at",
    ]

    list_filter = ["status", "story_bible", "strand", "generation_method"]
    search_fields = ["title", "content", "summary"]
    readonly_fields = ["word_count", "created_at", "updated_at"]
    ordering = ["strand", "chapter_number", "-version"]

    fieldsets = (
        ("Basic Info", {"fields": ("story_bible", "strand", "beat", "chapter_number", "title")}),
        ("Content", {"fields": ("content", "summary", "word_count")}),
        ("Metadata", {"fields": ("pov_character", "generation_method", "status", "version")}),
        (
            "Quality Metrics",
            {"fields": ("quality_score", "consistency_score"), "classes": ("collapse",)},
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def quality_display(self, obj):
        """Display quality score with color coding"""
        if obj.quality_score is None:
            return "-"
        color = "green" if obj.quality_score >= 80 else "orange" if obj.quality_score >= 60 else "red"
        return format_html('<span style="color: {};">{}</span>', color, obj.quality_score)

    quality_display.short_description = "Quality"
    quality_display.admin_order_field = "quality_score"


# =============================================================================
# ILLUSTRATION SYSTEM LOOKUPS
# =============================================================================

from .models_lookups_illustration import (
    IllustrationArtStyle,
    IllustrationImageType,
    IllustrationAIProvider,
    IllustrationImageStatus,
)


@admin.register(IllustrationArtStyle)
class IllustrationArtStyleAdmin(admin.ModelAdmin):
    """Admin interface for Art Styles"""

    list_display = ['code', 'name', 'complexity', 'is_active', 'order']
    list_filter = ['is_active', 'complexity']
    search_fields = ['code', 'name', 'description', 'prompt_keywords']
    list_editable = ['is_active', 'order']
    ordering = ['order', 'name']

    fieldsets = (
        ('Basic Info', {
            'fields': ('code', 'name', 'description')
        }),
        ('Visual Reference', {
            'fields': ('example_url', 'thumbnail'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('suitable_for', 'complexity', 'prompt_keywords', 'negative_prompt_defaults')
        }),
        ('Settings', {
            'fields': ('is_active', 'order')
        }),
    )


@admin.register(IllustrationImageType)
class IllustrationImageTypeAdmin(admin.ModelAdmin):
    """Admin interface for Image Types"""

    list_display = ['code', 'name', 'resolution_display', 'aspect_ratio', 'icon', 'is_active', 'order']
    list_filter = ['is_active', 'aspect_ratio']
    search_fields = ['code', 'name', 'description']
    list_editable = ['is_active', 'order']
    ordering = ['order', 'name']
    filter_horizontal = ['recommended_styles']

    fieldsets = (
        ('Basic Info', {
            'fields': ('code', 'name', 'description', 'icon')
        }),
        ('Technical Specs', {
            'fields': ('default_width', 'default_height', 'aspect_ratio')
        }),
        ('Recommendations', {
            'fields': ('recommended_styles', 'use_case_examples')
        }),
        ('Settings', {
            'fields': ('is_active', 'order')
        }),
    )

    def resolution_display(self, obj):
        """Display resolution as WxH"""
        return f"{obj.default_width}x{obj.default_height}"

    resolution_display.short_description = "Resolution"


@admin.register(IllustrationAIProvider)
class IllustrationAIProviderAdmin(admin.ModelAdmin):
    """Admin interface for AI Providers"""

    list_display = [
        'code', 'name', 'max_resolution', 'pricing_display',
        'capabilities_display', 'is_recommended', 'is_active', 'order'
    ]
    list_filter = ['is_active', 'is_recommended', 'supports_batch', 'supports_img2img']
    search_fields = ['code', 'name', 'description']
    list_editable = ['is_active', 'is_recommended', 'order']
    ordering = ['order', 'name']

    fieldsets = (
        ('Basic Info', {
            'fields': ('code', 'name', 'description')
        }),
        ('Technical', {
            'fields': ('api_endpoint', 'api_key_required', 'documentation_url', 'max_resolution')
        }),
        ('Capabilities', {
            'fields': ('supports_batch', 'supports_img2img', 'supports_inpainting')
        }),
        ('Pricing & Performance', {
            'fields': ('pricing_per_image', 'pricing_model', 'avg_generation_time_seconds')
        }),
        ('Settings', {
            'fields': ('is_active', 'is_recommended', 'order')
        }),
    )

    def pricing_display(self, obj):
        """Display pricing"""
        if obj.pricing_per_image:
            return f"${obj.pricing_per_image:.4f}"
        return "-"

    pricing_display.short_description = "Price/Image"

    def capabilities_display(self, obj):
        """Display capabilities as badges"""
        caps = []
        if obj.supports_batch:
            caps.append("Batch")
        if obj.supports_img2img:
            caps.append("Img2Img")
        if obj.supports_inpainting:
            caps.append("Inpaint")
        return ", ".join(caps) if caps else "-"

    capabilities_display.short_description = "Capabilities"


@admin.register(IllustrationImageStatus)
class IllustrationImageStatusAdmin(admin.ModelAdmin):
    """Admin interface for Image Statuses"""

    list_display = [
        'code', 'name', 'color_badge', 'progress_percentage',
        'workflow_display', 'is_active', 'order'
    ]
    list_filter = ['is_active', 'is_terminal_state', 'is_error_state', 'can_retry_from']
    search_fields = ['code', 'name', 'description']
    list_editable = ['is_active', 'order']
    ordering = ['order', 'name']

    fieldsets = (
        ('Basic Info', {
            'fields': ('code', 'name', 'description')
        }),
        ('UI Styling', {
            'fields': ('color', 'icon', 'progress_percentage')
        }),
        ('Workflow Settings', {
            'fields': (
                'is_terminal_state', 'is_error_state',
                'can_retry_from', 'can_edit_from'
            )
        }),
        ('Settings', {
            'fields': ('is_active', 'order')
        }),
    )

    def color_badge(self, obj):
        """Display color as badge"""
        colors = {
            'primary': '#0d6efd',
            'success': '#198754',
            'danger': '#dc3545',
            'warning': '#ffc107',
            'info': '#0dcaf0',
            'secondary': '#6c757d',
        }
        color_hex = colors.get(obj.color, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color_hex, obj.name
        )

    color_badge.short_description = "Color"

    def workflow_display(self, obj):
        """Display workflow flags"""
        flags = []
        if obj.is_terminal_state:
            flags.append("Terminal")
        if obj.is_error_state:
            flags.append("Error")
        if obj.can_retry_from:
            flags.append("Retryable")
        return ", ".join(flags) if flags else "Active"

    workflow_display.short_description = "Workflow"


# =============================================================================
# CASCADE AUTONOMOUS WORK SESSIONS
# =============================================================================

from .models_cascade import CascadeWorkSession, CascadeWorkLog


class CascadeWorkLogInline(admin.TabularInline):
    """Inline display of logs within a session"""
    model = CascadeWorkLog
    extra = 0
    readonly_fields = ['timestamp', 'log_type', 'iteration', 'message']
    fields = ['timestamp', 'log_type', 'iteration', 'message']
    ordering = ['-timestamp']
    max_num = 50
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(CascadeWorkSession)
class CascadeWorkSessionAdmin(admin.ModelAdmin):
    """Admin interface for Cascade Work Sessions"""
    
    list_display = [
        'short_id', 'requirement_name', 'status_badge', 
        'progress_display', 'iteration_display', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['requirement__name', 'initial_context']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'started_at', 'completed_at',
        'progress_display', 'files_changed', 'success_indicators'
    ]
    inlines = [CascadeWorkLogInline]
    
    fieldsets = (
        ('Session Info', {
            'fields': ('id', 'requirement', 'status', 'created_by')
        }),
        ('Progress', {
            'fields': ('current_iteration', 'max_iterations', 'progress_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at', 'updated_at')
        }),
        ('Context', {
            'fields': ('initial_context', 'final_summary'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('files_changed', 'error_count', 'success_indicators'),
            'classes': ('collapse',)
        }),
    )
    
    def short_id(self, obj):
        return obj.id.hex[:8]
    short_id.short_description = "ID"
    
    def requirement_name(self, obj):
        return obj.requirement.name[:40] + "..." if len(obj.requirement.name) > 40 else obj.requirement.name
    requirement_name.short_description = "Requirement"
    
    def status_badge(self, obj):
        colors = {
            'pending': 'secondary',
            'running': 'primary',
            'success': 'success',
            'failed': 'danger',
            'stopped': 'warning',
            'max_iterations': 'info',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def progress_display(self, obj):
        pct = obj.progress_percentage
        color = 'success' if pct >= 80 else 'warning' if pct >= 50 else 'danger'
        return format_html(
            '<div class="progress" style="width: 100px;"><div class="progress-bar bg-{}" style="width: {}%">{}</div></div>',
            color, pct, f"{pct}%"
        )
    progress_display.short_description = "Progress"
    
    def iteration_display(self, obj):
        return f"{obj.current_iteration}/{obj.max_iterations}"
    iteration_display.short_description = "Iteration"


@admin.register(CascadeWorkLog)
class CascadeWorkLogAdmin(admin.ModelAdmin):
    """Admin interface for Cascade Work Logs"""
    
    list_display = ['timestamp', 'session_short', 'log_type_badge', 'iteration', 'message_short']
    list_filter = ['log_type', 'timestamp']
    search_fields = ['message', 'session__requirement__name']
    readonly_fields = ['timestamp', 'session', 'log_type', 'iteration', 'message', 'details']
    
    def session_short(self, obj):
        return obj.session.id.hex[:8]
    session_short.short_description = "Session"
    
    def log_type_badge(self, obj):
        colors = {
            'info': 'info',
            'action': 'primary',
            'stdout': 'secondary',
            'stderr': 'danger',
            'success': 'success',
            'error': 'danger',
            'warning': 'warning',
            'file_change': 'primary',
            'test_result': 'info',
        }
        color = colors.get(obj.log_type, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_log_type_display()
        )
    log_type_badge.short_description = "Type"
    
    def message_short(self, obj):
        return obj.message[:80] + "..." if len(obj.message) > 80 else obj.message
    message_short.short_description = "Message"


# ============================================================================
# BUG LLM ASSIGNMENT ADMIN
# ============================================================================

from .models_testing import BugLLMAssignment, BugResolutionStats


@admin.register(BugLLMAssignment)
class BugLLMAssignmentAdmin(admin.ModelAdmin):
    """Admin für Bug-LLM-Zuweisungen mit Kosten-Tracking."""
    
    list_display = [
        "requirement_name", "tier_badge", "status_badge", 
        "attempts", "escalation_count", "cost_display", "created_at"
    ]
    list_filter = ["current_tier", "status", "created_at"]
    search_fields = ["requirement__name", "resolution_notes"]
    readonly_fields = [
        "id", "created_at", "started_at", "resolved_at",
        "tokens_input", "tokens_output", "cost_usd", 
        "attempt_history", "complexity_score"
    ]
    raw_id_fields = ["requirement", "llm_used"]
    ordering = ["-created_at"]
    
    fieldsets = (
        ("Requirement", {
            "fields": ("requirement",)
        }),
        ("Tier-Zuweisung", {
            "fields": ("initial_tier", "current_tier", "complexity_score")
        }),
        ("LLM & Versuche", {
            "fields": ("llm_used", "attempts", "escalation_count")
        }),
        ("Kosten", {
            "fields": ("tokens_input", "tokens_output", "cost_usd"),
            "classes": ("collapse",)
        }),
        ("Ergebnis", {
            "fields": ("status", "resolution_confidence", "resolution_notes")
        }),
        ("Timestamps", {
            "fields": ("created_at", "started_at", "resolved_at"),
            "classes": ("collapse",)
        }),
        ("History (JSON)", {
            "fields": ("attempt_history",),
            "classes": ("collapse",)
        }),
    )
    
    def requirement_name(self, obj):
        name = obj.requirement.name
        return name[:40] + "..." if len(name) > 40 else name
    requirement_name.short_description = "Requirement"
    
    def tier_badge(self, obj):
        colors = {
            'tier_1': 'success',
            'tier_2': 'warning', 
            'tier_3': 'danger',
        }
        icons = {
            'tier_1': '💚',
            'tier_2': '💛',
            'tier_3': '🔴',
        }
        color = colors.get(obj.current_tier, 'secondary')
        icon = icons.get(obj.current_tier, '')
        return format_html(
            '<span class="badge bg-{}">{} {}</span>',
            color, icon, obj.get_current_tier_display()
        )
    tier_badge.short_description = "Tier"
    
    def status_badge(self, obj):
        colors = {
            'pending': 'secondary',
            'in_progress': 'info',
            'resolved': 'success',
            'escalated': 'warning',
            'failed': 'danger',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def cost_display(self, obj):
        cost = float(obj.cost_usd)
        if cost < 0.01:
            return f"${cost:.6f}"
        return f"${cost:.4f}"
    cost_display.short_description = "Kosten"


@admin.register(BugResolutionStats)
class BugResolutionStatsAdmin(admin.ModelAdmin):
    """Admin für monatliche Bug-Resolution-Statistiken."""
    
    list_display = [
        "month", "total_bugs", "tier_distribution",
        "total_cost_display", "savings_display"
    ]
    list_filter = ["month"]
    ordering = ["-month"]
    readonly_fields = [
        "tier_1_count", "tier_2_count", "tier_3_count",
        "tier_1_success_rate", "tier_2_success_rate", "tier_3_success_rate",
        "total_cost_usd", "cost_saved_usd", "total_tokens"
    ]
    
    def total_bugs(self, obj):
        return obj.tier_1_count + obj.tier_2_count + obj.tier_3_count
    total_bugs.short_description = "Total Bugs"
    
    def tier_distribution(self, obj):
        total = self.total_bugs(obj)
        if total == 0:
            return "-"
        t1_pct = (obj.tier_1_count / total) * 100
        t2_pct = (obj.tier_2_count / total) * 100
        t3_pct = (obj.tier_3_count / total) * 100
        return format_html(
            '<span class="badge bg-success">T1: {}%</span> '
            '<span class="badge bg-warning">T2: {}%</span> '
            '<span class="badge bg-danger">T3: {}%</span>',
            int(t1_pct), int(t2_pct), int(t3_pct)
        )
    tier_distribution.short_description = "Tier-Verteilung"
    
    def total_cost_display(self, obj):
        return f"${obj.total_cost_usd:.2f}"
    total_cost_display.short_description = "Kosten"
    
    def savings_display(self, obj):
        return format_html(
            '<span class="text-success">${:.2f} gespart</span>',
            obj.cost_saved_usd
        )
    savings_display.short_description = "Ersparnis"


# Import Autocoding System Admin configurations
from .admin_autocoding import (
    AutocodingRunAdmin,
    ToolCallAdmin,
    ArtifactAdmin,
)
