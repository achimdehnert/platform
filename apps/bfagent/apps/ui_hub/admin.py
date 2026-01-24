"""Admin interface for UI Hub."""

from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    CodeTemplate,
    GuardrailCategory,
    GuardrailRule,
    HTMXPattern,
    RuleExample,
    RuleViolation,
    ValidationSession,
)


@admin.register(GuardrailCategory)
class GuardrailCategoryAdmin(admin.ModelAdmin):
    """Admin for guardrail categories."""

    list_display = ["code", "name", "rule_count", "display_order", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["code", "name", "description"]
    ordering = ["display_order", "name"]

    fieldsets = (
        ("Basic Information", {"fields": ("code", "name", "description")}),
        ("Display", {"fields": ("display_order", "is_active")}),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    readonly_fields = ["created_at", "updated_at"]

    def rule_count(self, obj):
        """Show count of rules in category."""
        count = obj.rules.filter(is_active=True).count()
        return format_html(
            '<a href="{}?category__id__exact={}">{} rules</a>',
            reverse("admin:ui_hub_guardrailrule_changelist"),
            obj.id,
            count,
        )

    rule_count.short_description = "Active Rules"


class RuleExampleInline(admin.TabularInline):
    """Inline for rule examples."""

    model = RuleExample
    extra = 1
    fields = ["code", "is_valid", "explanation"]


@admin.register(GuardrailRule)
class GuardrailRuleAdmin(admin.ModelAdmin):
    """Admin for guardrail rules."""

    list_display = [
        "name",
        "category",
        "severity_badge",
        "is_builtin",
        "is_active",
        "violation_count",
        "created_at",
    ]
    list_filter = ["severity", "is_builtin", "is_active", "category", "created_at"]
    search_fields = ["name", "description", "message", "pattern"]
    ordering = ["category", "name"]

    fieldsets = (
        ("Basic Information", {"fields": ("category", "name", "description")}),
        ("Validation", {"fields": ("pattern", "message", "suggestion", "severity")}),
        ("Status", {"fields": ("is_builtin", "is_active")}),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    readonly_fields = ["created_at", "updated_at"]
    inlines = [RuleExampleInline]

    def severity_badge(self, obj):
        """Show colored badge for severity."""
        colors = {
            "info": "#17a2b8",
            "warning": "#ffc107",
            "error": "#dc3545",
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.severity, "#6c757d"),
            obj.get_severity_display(),
        )

    severity_badge.short_description = "Severity"

    def violation_count(self, obj):
        """Show count of violations."""
        count = obj.violations.filter(is_resolved=False).count()
        if count > 0:
            return format_html(
                '<a href="{}?rule__id__exact={}&is_resolved__exact=0" style="color: red; font-weight: bold;">{} unresolved</a>',
                reverse("admin:ui_hub_ruleviolation_changelist"),
                obj.id,
                count,
            )
        return "0"

    violation_count.short_description = "Violations"


@admin.register(RuleExample)
class RuleExampleAdmin(admin.ModelAdmin):
    """Admin for rule examples."""

    list_display = ["rule", "is_valid_badge", "code_preview", "created_at"]
    list_filter = ["is_valid", "created_at"]
    search_fields = ["code", "explanation"]
    ordering = ["-is_valid", "-created_at"]

    fieldsets = (
        ("Rule", {"fields": ("rule",)}),
        ("Example", {"fields": ("code", "is_valid", "explanation")}),
    )

    def is_valid_badge(self, obj):
        """Show valid/invalid badge."""
        if obj.is_valid:
            return format_html('<span style="color: green;">✅ Valid</span>')
        return format_html('<span style="color: red;">❌ Invalid</span>')

    is_valid_badge.short_description = "Status"

    def code_preview(self, obj):
        """Show code preview."""
        preview = obj.code[:100]
        if len(obj.code) > 100:
            preview += "..."
        return preview

    code_preview.short_description = "Code"


@admin.register(CodeTemplate)
class CodeTemplateAdmin(admin.ModelAdmin):
    """Admin for code templates."""

    list_display = ["name", "template_type", "is_active", "updated_at"]
    list_filter = ["template_type", "is_active", "created_at"]
    search_fields = ["name", "description", "content"]
    ordering = ["template_type", "name"]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "template_type", "description")}),
        ("Template", {"fields": ("content", "variables_schema")}),
        ("Status", {"fields": ("is_active",)}),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    readonly_fields = ["created_at", "updated_at"]


@admin.register(HTMXPattern)
class HTMXPatternAdmin(admin.ModelAdmin):
    """Admin for HTMX patterns."""

    list_display = ["name", "pattern_type", "has_view", "has_html", "has_partial", "is_active"]
    list_filter = ["pattern_type", "is_active", "created_at"]
    search_fields = ["name", "description"]
    ordering = ["pattern_type", "name"]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "pattern_type", "description")}),
        (
            "Templates",
            {"fields": ("view_template", "html_template", "partial_template", "javascript")},
        ),
        ("Status", {"fields": ("is_active",)}),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    readonly_fields = ["created_at", "updated_at"]

    def has_view(self, obj):
        """Check if has view template."""
        return "✅" if obj.view_template else "❌"

    has_view.short_description = "View"

    def has_html(self, obj):
        """Check if has HTML template."""
        return "✅" if obj.html_template else "❌"

    has_html.short_description = "HTML"

    def has_partial(self, obj):
        """Check if has partial template."""
        return "✅" if obj.partial_template else "❌"

    has_partial.short_description = "Partial"


@admin.register(RuleViolation)
class RuleViolationAdmin(admin.ModelAdmin):
    """Admin for rule violations."""

    list_display = [
        "rule",
        "file_path_short",
        "line_number",
        "severity_badge",
        "is_resolved_badge",
        "created_at",
    ]
    list_filter = ["severity", "is_resolved", "app_name", "created_at", "rule__category"]
    search_fields = ["file_path", "message", "code_snippet"]
    ordering = ["-created_at"]

    fieldsets = (
        ("Violation", {"fields": ("rule", "file_path", "line_number", "severity")}),
        ("Details", {"fields": ("message", "code_snippet", "app_name")}),
        ("Resolution", {"fields": ("is_resolved", "resolved_at", "resolution_note")}),
    )

    readonly_fields = ["created_at", "resolved_at"]

    actions = ["mark_resolved", "mark_unresolved"]

    def file_path_short(self, obj):
        """Show shortened file path."""
        path = obj.file_path
        if len(path) > 60:
            return "..." + path[-57:]
        return path

    file_path_short.short_description = "File"

    def severity_badge(self, obj):
        """Show colored severity badge."""
        colors = {
            "info": "#17a2b8",
            "warning": "#ffc107",
            "error": "#dc3545",
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.severity, "#6c757d"),
            obj.severity.upper(),
        )

    severity_badge.short_description = "Severity"

    def is_resolved_badge(self, obj):
        """Show resolved status badge."""
        if obj.is_resolved:
            return format_html('<span style="color: green;">✅ Resolved</span>')
        return format_html('<span style="color: red;">⚠️ Open</span>')

    is_resolved_badge.short_description = "Status"

    def mark_resolved(self, request, queryset):
        """Mark selected violations as resolved."""
        queryset.update(is_resolved=True)
        self.message_user(request, f"{queryset.count()} violations marked as resolved.")

    mark_resolved.short_description = "Mark as resolved"

    def mark_unresolved(self, request, queryset):
        """Mark selected violations as unresolved."""
        queryset.update(is_resolved=False, resolved_at=None)
        self.message_user(request, f"{queryset.count()} violations marked as unresolved.")

    mark_unresolved.short_description = "Mark as unresolved"


@admin.register(ValidationSession)
class ValidationSessionAdmin(admin.ModelAdmin):
    """Admin for validation sessions."""

    list_display = [
        "session_id",
        "target_path_short",
        "app_name",
        "status_badge",
        "violations_summary",
        "started_at",
    ]
    list_filter = ["status", "app_name", "started_at"]
    search_fields = ["session_id", "target_path", "app_name"]
    ordering = ["-started_at"]

    fieldsets = (
        ("Session", {"fields": ("session_id", "target_path", "app_name", "status")}),
        (
            "Results",
            {
                "fields": (
                    "total_files",
                    "violations_found",
                    "errors_count",
                    "warnings_count",
                    "info_count",
                )
            },
        ),
        ("Timing", {"fields": ("started_at", "completed_at")}),
        ("Summary", {"fields": ("summary",), "classes": ("collapse",)}),
    )

    readonly_fields = ["started_at", "completed_at"]

    def target_path_short(self, obj):
        """Show shortened target path."""
        path = obj.target_path
        if len(path) > 50:
            return "..." + path[-47:]
        return path

    target_path_short.short_description = "Target"

    def status_badge(self, obj):
        """Show colored status badge."""
        colors = {
            "running": "#17a2b8",
            "completed": "#28a745",
            "failed": "#dc3545",
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, "#6c757d"),
            obj.status.upper(),
        )

    status_badge.short_description = "Status"

    def violations_summary(self, obj):
        """Show violations summary."""
        return format_html(
            "🔴 {} errors | 🟡 {} warnings | ℹ️ {} info",
            obj.errors_count,
            obj.warnings_count,
            obj.info_count,
        )

    violations_summary.short_description = "Violations"
