"""Django Admin configuration for chat-logging models.

Provides filterable, searchable admin views for conversation
review and quality management per ADR-037.
"""

from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    ChatConversation,
    ChatMessage,
    EvaluationScore,
    UseCaseCandidate,
)


class ChatMessageInline(admin.TabularInline):
    """Inline display of messages within a conversation."""

    model = ChatMessage
    extra = 0
    readonly_fields = [
        "role",
        "content_preview",
        "model",
        "tool_calls",
        "tokens_used",
        "latency_ms",
        "created_at",
    ]
    fields = [
        "role",
        "content_preview",
        "model",
        "tool_calls",
        "tokens_used",
        "latency_ms",
        "created_at",
    ]

    def content_preview(self, obj: ChatMessage) -> str:
        """Truncated content for inline display."""
        if not obj.content:
            return "(empty)"
        text = obj.content[:200]
        if len(obj.content) > 200:
            text += "..."
        return text

    content_preview.short_description = "Content"  # type: ignore[attr-defined]

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


class UseCaseCandidateInline(admin.TabularInline):
    """Inline display of use-case candidates."""

    model = UseCaseCandidate
    extra = 0
    fields = [
        "detection_method",
        "user_intent",
        "frequency",
        "status",
        "priority",
    ]


class EvaluationScoreInline(admin.TabularInline):
    """Inline display of evaluation scores."""

    model = EvaluationScore
    extra = 0
    readonly_fields = [
        "evaluator",
        "metric_name",
        "score",
        "reason",
        "evaluated_at",
    ]
    fields = [
        "evaluator",
        "metric_name",
        "score",
        "reason",
        "evaluated_at",
    ]

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    """Admin for browsing and reviewing chat conversations."""

    list_display = [
        "session_id_short",
        "app_name",
        "user",
        "goal_type",
        "outcome_status_badge",
        "message_count",
        "total_tool_calls",
        "review_status",
        "started_at",
    ]
    list_filter = [
        "app_name",
        "goal_type",
        "outcome_status",
        "review_status",
        ("started_at", admin.DateFieldListFilter),
    ]
    search_fields = [
        "session_id",
        "goal_summary",
        "outcome_summary",
        "messages__content",
        "user__email",
    ]
    readonly_fields = [
        "id",
        "session_id",
        "started_at",
        "ended_at",
        "message_count",
        "total_tokens",
        "total_tool_calls",
        "total_latency_ms",
        "models_used",
        "computed_duration",
    ]
    fieldsets = [
        (
            "Identifikation",
            {
                "fields": [
                    "id",
                    "session_id",
                    "user",
                    "app_name",
                    "tenant_id",
                ],
            },
        ),
        (
            "Kontext (Ziel)",
            {
                "fields": [
                    "goal_type",
                    "goal_summary",
                ],
            },
        ),
        (
            "Ergebnis",
            {
                "fields": [
                    "outcome_status",
                    "outcome_summary",
                    "outcome_artifacts",
                ],
            },
        ),
        (
            "Qualitätsmanagement",
            {
                "fields": [
                    "satisfaction_rating",
                    "review_status",
                    "review_notes",
                    "improvement_tags",
                ],
            },
        ),
        (
            "Metriken",
            {
                "fields": [
                    "message_count",
                    "total_tokens",
                    "total_tool_calls",
                    "total_latency_ms",
                    "models_used",
                    "computed_duration",
                    "started_at",
                    "ended_at",
                ],
            },
        ),
    ]
    inlines = [
        ChatMessageInline,
        UseCaseCandidateInline,
        EvaluationScoreInline,
    ]
    list_per_page = 25
    date_hierarchy = "started_at"
    actions = ["mark_reviewed", "mark_action_taken"]

    def session_id_short(self, obj: ChatConversation) -> str:
        """Truncated session ID for list display."""
        return obj.session_id[:16] + "..."

    session_id_short.short_description = "Session"  # type: ignore[attr-defined]

    def outcome_status_badge(
        self, obj: ChatConversation
    ) -> str:
        """Colored badge for outcome status."""
        colors = {
            "completed": "#28a745",
            "partial": "#ffc107",
            "abandoned": "#6c757d",
            "error": "#dc3545",
        }
        color = colors.get(obj.outcome_status, "#6c757d")
        label = obj.get_outcome_status_display()
        return format_html(
            '<span style="color: {}; font-weight: bold;">'
            "{}</span>",
            color,
            label,
        )

    outcome_status_badge.short_description = "Outcome"  # type: ignore[attr-defined]

    def computed_duration(
        self, obj: ChatConversation
    ) -> str:
        """Human-readable duration."""
        seconds = obj.duration_seconds
        if seconds is None:
            return "-"
        if seconds < 60:
            return f"{seconds:.0f}s"
        minutes = seconds / 60
        return f"{minutes:.1f}min"

    computed_duration.short_description = "Dauer"  # type: ignore[attr-defined]

    @admin.action(description="Als geprüft markieren")
    def mark_reviewed(self, request, queryset) -> None:
        updated = queryset.update(
            review_status=ChatConversation.ReviewStatus.REVIEWED
        )
        self.message_user(
            request,
            f"{updated} Konversationen als geprüft markiert.",
        )

    @admin.action(
        description="Maßnahme eingeleitet markieren"
    )
    def mark_action_taken(self, request, queryset) -> None:
        updated = queryset.update(
            review_status=ChatConversation.ReviewStatus.ACTION_TAKEN
        )
        self.message_user(
            request,
            f"{updated} Konversationen: Maßnahme eingeleitet.",
        )


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Admin for browsing individual messages."""

    list_display = [
        "role",
        "content_short",
        "model",
        "tokens_used",
        "latency_ms",
        "conversation_link",
        "created_at",
    ]
    list_filter = [
        "role",
        "conversation__app_name",
        ("created_at", admin.DateFieldListFilter),
    ]
    search_fields = ["content", "conversation__session_id"]
    readonly_fields = [
        "id",
        "conversation",
        "role",
        "content",
        "model",
        "tool_calls",
        "tool_call_id",
        "name",
        "tokens_used",
        "latency_ms",
        "created_at",
    ]
    list_per_page = 50

    def content_short(self, obj: ChatMessage) -> str:
        """Truncated content for list display."""
        if not obj.content:
            return "(empty)"
        text = obj.content[:100]
        if len(obj.content) > 100:
            text += "..."
        return text

    content_short.short_description = "Content"  # type: ignore[attr-defined]

    def conversation_link(self, obj: ChatMessage) -> str:
        """Link to parent conversation."""
        return format_html(
            '<a href="/admin/chat_logging/chatconversation'
            '/{}/change/">{}</a>',
            obj.conversation_id,
            str(obj.conversation),
        )

    conversation_link.short_description = "Conversation"  # type: ignore[attr-defined]

    def has_add_permission(self, request) -> bool:
        return False


@admin.register(UseCaseCandidate)
class UseCaseCandidateAdmin(admin.ModelAdmin):
    """Admin for managing detected use-case candidates."""

    list_display = [
        "user_intent_short",
        "app_name",
        "detection_method",
        "frequency",
        "status",
        "priority",
        "created_at",
    ]
    list_filter = [
        "status",
        "priority",
        "app_name",
        "detection_method",
    ]
    list_editable = ["status", "priority"]
    search_fields = ["user_intent", "notes"]
    list_per_page = 25

    def user_intent_short(
        self, obj: UseCaseCandidate
    ) -> str:
        """Truncated intent for list display."""
        text = obj.user_intent[:80]
        if len(obj.user_intent) > 80:
            text += "..."
        return text

    user_intent_short.short_description = "User Intent"  # type: ignore[attr-defined]


@admin.register(EvaluationScore)
class EvaluationScoreAdmin(admin.ModelAdmin):
    """Admin for browsing evaluation scores."""

    list_display = [
        "conversation",
        "evaluator",
        "metric_name",
        "score",
        "evaluated_at",
    ]
    list_filter = [
        "evaluator",
        "metric_name",
        ("evaluated_at", admin.DateFieldListFilter),
    ]
    search_fields = [
        "metric_name",
        "reason",
        "conversation__session_id",
    ]
    readonly_fields = [
        "id",
        "conversation",
        "evaluator",
        "metric_name",
        "score",
        "reason",
        "metadata",
        "evaluated_at",
    ]
    list_per_page = 50

    def has_add_permission(self, request) -> bool:
        return False
