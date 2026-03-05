"""
aifw/admin.py — Django Admin registration for aifw 0.6.0.

ADR-097 §7 — Admin Registration.
"""
from django.contrib import admin

from .models import AIActionType, TierQualityMapping, AIUsageLog


@admin.register(AIActionType)
class AIActionTypeAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "quality_level",
        "quality_band_display",
        "priority",
        "default_model",
        "prompt_template_key",
        "max_tokens",
        "is_active",
    ]
    list_filter = ["is_active", "priority"]
    search_fields = ["code", "name", "prompt_template_key"]
    ordering = ["code", "quality_level", "priority"]
    readonly_fields = []

    @admin.display(description="Band")
    def quality_band_display(self, obj: AIActionType) -> str:
        if obj.quality_level is None:
            return "catch-all"
        from .constants import QualityLevel
        return QualityLevel.band_for(obj.quality_level)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("default_model", "fallback_model")

    class Media:
        # Inline help for admin users re: NULL semantics
        js = []


@admin.register(TierQualityMapping)
class TierQualityMappingAdmin(admin.ModelAdmin):
    list_display = ["tier", "quality_level", "quality_band_display", "is_active", "updated_at"]
    list_filter = ["is_active"]
    ordering = ["-quality_level"]

    @admin.display(description="Band")
    def quality_band_display(self, obj: TierQualityMapping) -> str:
        from .constants import QualityLevel
        return QualityLevel.band_for(obj.quality_level)


@admin.register(AIUsageLog)
class AIUsageLogAdmin(admin.ModelAdmin):
    list_display = [
        "action_code",
        "model",
        "quality_level",
        "quality_band_display",
        "input_tokens",
        "output_tokens",
        "cost_usd",
        "latency_ms",
        "success",
        "created_at",
    ]
    list_filter = ["success", "quality_level", "action_code"]
    search_fields = ["action_code", "model"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    @admin.display(description="Band")
    def quality_band_display(self, obj: AIUsageLog) -> str:
        if obj.quality_level is None:
            return "—"
        from .constants import QualityLevel
        return QualityLevel.band_for(obj.quality_level)

    def has_add_permission(self, request) -> bool:
        return False  # Logs are system-generated only

    def has_change_permission(self, request, obj=None) -> bool:
        return False  # Logs are immutable
