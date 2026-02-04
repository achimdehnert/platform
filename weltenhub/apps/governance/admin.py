"""
DDL Governance Admin Configuration
===================================

Admin interface for Business Cases, Use Cases, ADRs, and supporting models.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    LookupDomain,
    LookupChoice,
    BusinessCase,
    UseCase,
    ADR,
    ADRUseCaseLink,
    Conversation,
    ConversationTurn,
    Review,
    StatusHistory,
)


# =============================================================================
# LOOKUP ADMIN
# =============================================================================

class LookupChoiceInline(admin.TabularInline):
    """Inline for choices within a domain."""
    model = LookupChoice
    extra = 1
    fields = ["code", "name", "name_de", "sort_order", "color", "is_active"]
    ordering = ["sort_order", "code"]


@admin.register(LookupDomain)
class LookupDomainAdmin(admin.ModelAdmin):
    """Admin for Lookup Domains."""
    
    list_display = ["code", "name", "choice_count", "is_active", "updated_at"]
    list_filter = ["is_active"]
    search_fields = ["code", "name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [LookupChoiceInline]
    
    def choice_count(self, obj):
        return obj.choices.count()
    choice_count.short_description = "Choices"


@admin.register(LookupChoice)
class LookupChoiceAdmin(admin.ModelAdmin):
    """Admin for Lookup Choices."""
    
    list_display = ["code", "domain", "name", "color_badge", "sort_order", "is_active"]
    list_filter = ["domain", "is_active"]
    search_fields = ["code", "name", "domain__code"]
    list_editable = ["sort_order", "is_active"]
    ordering = ["domain", "sort_order"]
    readonly_fields = ["created_at", "updated_at"]
    
    def color_badge(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.color,
            obj.color
        )
    color_badge.short_description = "Color"


# =============================================================================
# BUSINESS CASE ADMIN
# =============================================================================

class UseCaseInline(admin.TabularInline):
    """Inline for Use Cases within a Business Case."""
    model = UseCase
    extra = 0
    fields = ["code", "title", "status", "priority"]
    readonly_fields = ["code"]
    show_change_link = True


@admin.register(BusinessCase)
class BusinessCaseAdmin(admin.ModelAdmin):
    """Admin for Business Cases."""
    
    list_display = [
        "code", "title", "category_badge", "status_badge", 
        "priority_badge", "use_case_count", "owner", "updated_at"
    ]
    list_filter = ["status", "category", "priority", "requires_adr"]
    search_fields = ["code", "title", "problem_statement"]
    readonly_fields = ["code", "created_at", "updated_at"]
    autocomplete_fields = ["owner"]
    inlines = [UseCaseInline]
    
    fieldsets = (
        ("Identification", {
            "fields": ("code", "title", "category", "status", "priority", "owner")
        }),
        ("Problem & Solution", {
            "fields": ("problem_statement", "target_audience", "expected_benefits")
        }),
        ("Scope", {
            "fields": ("scope", "out_of_scope", "success_criteria")
        }),
        ("Risk & Assumptions", {
            "fields": ("assumptions", "risks"),
            "classes": ("collapse",)
        }),
        ("Architecture", {
            "fields": ("requires_adr", "adr_reason"),
            "classes": ("collapse",)
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def use_case_count(self, obj):
        return obj.use_cases.count()
    use_case_count.short_description = "Use Cases"
    
    def status_badge(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.status.color,
            obj.status.name
        )
    status_badge.short_description = "Status"
    
    def category_badge(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.category.color,
            obj.category.name
        )
    category_badge.short_description = "Category"
    
    def priority_badge(self, obj):
        if not obj.priority:
            return "-"
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.priority.color,
            obj.priority.name
        )
    priority_badge.short_description = "Priority"


# =============================================================================
# USE CASE ADMIN
# =============================================================================

@admin.register(UseCase)
class UseCaseAdmin(admin.ModelAdmin):
    """Admin for Use Cases."""
    
    list_display = [
        "code", "title", "business_case_link", "status_badge", 
        "priority_badge", "actor", "updated_at"
    ]
    list_filter = ["status", "priority", "complexity", "business_case"]
    search_fields = ["code", "title", "actor", "business_case__code"]
    readonly_fields = ["code", "created_at", "updated_at"]
    autocomplete_fields = ["business_case"]
    
    fieldsets = (
        ("Identification", {
            "fields": ("code", "title", "business_case", "status", "priority")
        }),
        ("Actor & Flow", {
            "fields": ("actor", "preconditions", "main_flow", "postconditions")
        }),
        ("Alternative Flows", {
            "fields": ("alternative_flows", "exception_flows"),
            "classes": ("collapse",)
        }),
        ("Estimation", {
            "fields": ("complexity", "estimated_effort"),
            "classes": ("collapse",)
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def business_case_link(self, obj):
        return format_html(
            '<a href="/admin/governance/businesscase/{}/change/">{}</a>',
            obj.business_case.id,
            obj.business_case.code
        )
    business_case_link.short_description = "Business Case"
    
    def status_badge(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.status.color,
            obj.status.name
        )
    status_badge.short_description = "Status"
    
    def priority_badge(self, obj):
        if not obj.priority:
            return "-"
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.priority.color,
            obj.priority.name
        )
    priority_badge.short_description = "Priority"


# =============================================================================
# ADR ADMIN
# =============================================================================

class ADRUseCaseLinkInline(admin.TabularInline):
    """Inline for ADR-UseCase links."""
    model = ADRUseCaseLink
    extra = 0
    autocomplete_fields = ["use_case"]


@admin.register(ADR)
class ADRAdmin(admin.ModelAdmin):
    """Admin for Architecture Decision Records."""
    
    list_display = ["code", "title", "status_badge", "supersedes", "file_path", "updated_at"]
    list_filter = ["status"]
    search_fields = ["code", "title", "context", "decision"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ADRUseCaseLinkInline]
    
    fieldsets = (
        ("Identification", {
            "fields": ("code", "title", "status", "file_path")
        }),
        ("Content", {
            "fields": ("context", "decision", "consequences", "alternatives")
        }),
        ("Relations", {
            "fields": ("supersedes",),
            "classes": ("collapse",)
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def status_badge(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.status.color,
            obj.status.name
        )
    status_badge.short_description = "Status"


@admin.register(ADRUseCaseLink)
class ADRUseCaseLinkAdmin(admin.ModelAdmin):
    """Admin for ADR-UseCase Links."""
    
    list_display = ["adr", "use_case", "relationship_type", "created_at"]
    list_filter = ["relationship_type"]
    autocomplete_fields = ["adr", "use_case"]


# =============================================================================
# CONVERSATION ADMIN
# =============================================================================

class ConversationTurnInline(admin.TabularInline):
    """Inline for conversation turns."""
    model = ConversationTurn
    extra = 0
    readonly_fields = ["turn_number", "role", "content", "created_at"]
    can_delete = False
    max_num = 0


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """Admin for Inception Conversations."""
    
    list_display = [
        "session_id", "business_case", "status_badge", 
        "turn_count", "started_by", "started_at"
    ]
    list_filter = ["status"]
    search_fields = ["session_id", "business_case__code"]
    readonly_fields = ["session_id", "started_at", "completed_at", "created_at", "updated_at"]
    inlines = [ConversationTurnInline]
    
    def turn_count(self, obj):
        return obj.turns.count()
    turn_count.short_description = "Turns"
    
    def status_badge(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.status.color,
            obj.status.name
        )
    status_badge.short_description = "Status"


# =============================================================================
# REVIEW ADMIN
# =============================================================================

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Admin for Reviews."""
    
    list_display = [
        "id", "entity_type", "entity_id", "reviewer", 
        "decision_badge", "created_at"
    ]
    list_filter = ["entity_type", "decision", "reviewer"]
    search_fields = ["comments"]
    readonly_fields = ["created_at", "updated_at"]
    
    def decision_badge(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.decision.color,
            obj.decision.name
        )
    decision_badge.short_description = "Decision"


# =============================================================================
# STATUS HISTORY ADMIN
# =============================================================================

@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    """Admin for Status History (Audit Trail)."""
    
    list_display = [
        "id", "entity_type", "entity_id", 
        "old_status", "new_status", "changed_by", "created_at"
    ]
    list_filter = ["entity_type", "new_status"]
    search_fields = ["reason"]
    readonly_fields = [
        "entity_type", "entity_id", "old_status", "new_status",
        "changed_by", "reason", "created_at", "updated_at"
    ]
    
    def has_add_permission(self, request):
        return False  # Audit trail - no manual adds
    
    def has_change_permission(self, request, obj=None):
        return False  # Audit trail - no edits
    
    def has_delete_permission(self, request, obj=None):
        return False  # Audit trail - no deletes
