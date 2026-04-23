"""
Django Admin for DB-driven LLM Configuration (ADR-089).
"""

from django.contrib import admin
from django.utils.html import format_html

from bfagent_llm.django_app.models import (
    AIActionType,
    AIUsageLog,
    LLMModel,
    LLMProvider,
)


@admin.register(LLMProvider)
class LLMProviderAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "display_name",
        "api_key_env_var",
        "is_active",
        "model_count",
    ]
    list_filter = ["is_active"]
    search_fields = ["name", "display_name"]
    list_editable = ["is_active"]

    def model_count(self, obj: LLMProvider) -> int:
        return obj.models.count()

    model_count.short_description = "Models"  # type: ignore[attr-defined]


@admin.register(LLMModel)
class LLMModelAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "provider",
        "display_name",
        "max_tokens",
        "context_window",
        "cost_display",
        "supports_vision",
        "supports_tools",
        "is_active",
        "is_default",
    ]
    list_filter = [
        "provider",
        "is_active",
        "is_default",
        "supports_vision",
        "supports_tools",
    ]
    search_fields = ["name", "display_name"]
    list_editable = ["is_active", "is_default"]

    def cost_display(self, obj: LLMModel) -> str:
        return f"${obj.input_cost_per_million} / ${obj.output_cost_per_million}"

    cost_display.short_description = "Cost (in/out per 1M)"  # type: ignore[attr-defined]


@admin.register(AIActionType)
class AIActionTypeAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "tenant_id",
        "default_model",
        "fallback_model",
        "max_tokens",
        "temperature",
        "is_active",
    ]
    list_filter = ["is_active", "tenant_id"]
    list_editable = ["default_model", "fallback_model", "is_active"]
    search_fields = ["code", "name"]

    fieldsets = (
        (None, {"fields": ("tenant_id", "code", "name", "description")}),
        (
            "Model Configuration",
            {"fields": ("default_model", "fallback_model")},
        ),
        (
            "Settings",
            {"fields": ("max_tokens", "temperature", "is_active")},
        ),
    )


@admin.register(AIUsageLog)
class AIUsageLogAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "tenant_id",
        "action_type",
        "model_used",
        "user",
        "total_tokens",
        "cost_display",
        "latency_display",
        "status_icon",
    ]
    list_filter = [
        "action_type",
        "model_used",
        "success",
        "tenant_id",
        "created_at",
    ]
    search_fields = ["user__username", "error_message"]
    date_hierarchy = "created_at"
    readonly_fields = [
        "created_at",
        "tenant_id",
        "action_type",
        "model_used",
        "user",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "estimated_cost",
        "latency_ms",
        "success",
        "error_message",
    ]

    def cost_display(self, obj: AIUsageLog) -> str:
        return f"${obj.estimated_cost:.4f}"

    cost_display.short_description = "Cost"  # type: ignore[attr-defined]

    def latency_display(self, obj: AIUsageLog) -> str:
        return f"{obj.latency_ms}ms"

    latency_display.short_description = "Latency"  # type: ignore[attr-defined]

    def status_icon(self, obj: AIUsageLog) -> str:
        if obj.success:
            return format_html('<span style="color: green;">OK</span>')
        return format_html('<span style="color: red;">FAIL</span>')

    status_icon.short_description = "Status"  # type: ignore[attr-defined]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False
