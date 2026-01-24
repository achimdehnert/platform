"""
Quality System Admin
====================

Admin interface for Quality Scoring & Series Memory models.
"""

from django.contrib import admin

from .models_quality import (
    CanonFact,
    ChapterDimensionScore,
    ChapterQualityScore,
    GateDecisionType,
    ProjectDimensionThreshold,
    ProjectQualityConfig,
    PromiseEvent,
    PromiseStatus,
    QualityDimension,
    StoryPromise,
    StyleIssue,
    StyleIssueType,
)


# =============================================================================
# LOOKUP TABLES ADMIN
# =============================================================================


@admin.register(QualityDimension)
class QualityDimensionAdmin(admin.ModelAdmin):
    """Admin für Qualitätsdimensionen."""
    list_display = ['code', 'name_de', 'weight', 'is_active', 'sort_order']
    list_filter = ['is_active']
    list_editable = ['weight', 'is_active', 'sort_order']
    search_fields = ['code', 'name_de', 'name_en']
    ordering = ['sort_order', 'code']


@admin.register(GateDecisionType)
class GateDecisionTypeAdmin(admin.ModelAdmin):
    """Admin für Gate-Entscheidungstypen."""
    list_display = ['code', 'name_de', 'color', 'icon', 'allows_commit', 'sort_order']
    list_filter = ['allows_commit']
    list_editable = ['color', 'allows_commit', 'sort_order']
    search_fields = ['code', 'name_de', 'name_en']
    ordering = ['sort_order']


@admin.register(PromiseStatus)
class PromiseStatusAdmin(admin.ModelAdmin):
    """Admin für Promise-Status."""
    list_display = ['code', 'name_de', 'color', 'is_terminal', 'sort_order']
    list_filter = ['is_terminal']
    list_editable = ['color', 'is_terminal', 'sort_order']
    search_fields = ['code', 'name_de', 'name_en']
    ordering = ['sort_order']


@admin.register(StyleIssueType)
class StyleIssueTypeAdmin(admin.ModelAdmin):
    """Admin für Style-Issue-Typen."""
    list_display = ['code', 'name_de', 'severity', 'auto_fixable', 'is_active', 'sort_order']
    list_filter = ['severity', 'auto_fixable', 'is_active']
    list_editable = ['severity', 'auto_fixable', 'is_active', 'sort_order']
    search_fields = ['code', 'name_de', 'name_en']
    ordering = ['sort_order', 'severity']


# =============================================================================
# QUALITY SCORING ADMIN
# =============================================================================


class ChapterDimensionScoreInline(admin.TabularInline):
    """Inline für Dimension-Scores in ChapterQualityScore."""
    model = ChapterDimensionScore
    extra = 0
    readonly_fields = ['dimension', 'score', 'notes']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class StyleIssueInline(admin.TabularInline):
    """Inline für Style Issues in ChapterQualityScore."""
    model = StyleIssue
    extra = 0
    fields = ['issue_type', 'text_excerpt', 'is_fixed', 'is_ignored']
    readonly_fields = ['issue_type', 'text_excerpt']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChapterQualityScore)
class ChapterQualityScoreAdmin(admin.ModelAdmin):
    """Admin für Kapitel-Qualitätsbewertungen."""
    list_display = [
        'chapter', 
        'overall_score', 
        'gate_decision', 
        'scored_by', 
        'scored_at'
    ]
    list_filter = ['gate_decision', 'scored_at']
    search_fields = ['chapter__title', 'notes']
    readonly_fields = ['scored_at', 'overall_score']
    autocomplete_fields = ['chapter', 'scored_by']
    raw_id_fields = ['pipeline_execution']
    inlines = [ChapterDimensionScoreInline, StyleIssueInline]
    ordering = ['-scored_at']
    
    fieldsets = (
        ('Kapitel', {
            'fields': ('chapter', 'gate_decision', 'overall_score')
        }),
        ('Bewertung', {
            'fields': ('scored_by', 'scored_at', 'pipeline_execution')
        }),
        ('Details', {
            'fields': ('findings', 'notes'),
            'classes': ('collapse',)
        }),
    )


# =============================================================================
# PROJECT QUALITY CONFIG ADMIN
# =============================================================================


class ProjectDimensionThresholdInline(admin.TabularInline):
    """Inline für Dimension-Schwellenwerte."""
    model = ProjectDimensionThreshold
    extra = 1
    autocomplete_fields = ['dimension']


@admin.register(ProjectQualityConfig)
class ProjectQualityConfigAdmin(admin.ModelAdmin):
    """Admin für Projekt-Qualitätskonfiguration."""
    list_display = [
        'project',
        'min_overall_score',
        'auto_approve_threshold',
        'require_manual_approval',
        'updated_at'
    ]
    list_filter = ['require_manual_approval']
    search_fields = ['project__title']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['project']
    inlines = [ProjectDimensionThresholdInline]
    
    fieldsets = (
        ('Projekt', {
            'fields': ('project',)
        }),
        ('Schwellenwerte', {
            'fields': (
                'min_overall_score',
                'auto_approve_threshold',
                'auto_reject_threshold'
            )
        }),
        ('Blocker-Konfiguration', {
            'fields': ('hard_block_severity', 'max_open_blockers')
        }),
        ('Optionen', {
            'fields': ('require_manual_approval',)
        }),
        ('Metadaten', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# =============================================================================
# SERIES MEMORY ADMIN
# =============================================================================


@admin.register(CanonFact)
class CanonFactAdmin(admin.ModelAdmin):
    """Admin für kanonische Fakten."""
    list_display = [
        'fact_key',
        'project',
        'confidence',
        'is_active',
        'introduced_chapter',
        'created_at'
    ]
    list_filter = ['is_active', 'confidence', 'project']
    search_fields = ['fact_key', 'fact_value']
    autocomplete_fields = ['project', 'introduced_chapter', 'superseded_by', 'created_by']
    readonly_fields = ['created_at']
    ordering = ['project', 'fact_key']
    
    fieldsets = (
        ('Fakt', {
            'fields': ('project', 'fact_key', 'fact_value')
        }),
        ('Herkunft', {
            'fields': ('introduced_chapter', 'confidence')
        }),
        ('Status', {
            'fields': ('is_active', 'superseded_by')
        }),
        ('Metadaten', {
            'fields': ('tags', 'created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )


class PromiseEventInline(admin.TabularInline):
    """Inline für Promise-Events."""
    model = PromiseEvent
    extra = 0
    readonly_fields = ['chapter', 'event_type', 'note', 'created_at']
    can_delete = False
    ordering = ['chapter__chapter_number', 'created_at']
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(StoryPromise)
class StoryPromiseAdmin(admin.ModelAdmin):
    """Admin für Story Promises (Hooks & Payoffs)."""
    list_display = [
        'title',
        'project',
        'status',
        'priority',
        'introduced_chapter',
        'paid_chapter'
    ]
    list_filter = ['status', 'priority', 'project']
    search_fields = ['title', 'description', 'promise_key']
    autocomplete_fields = ['project', 'status', 'introduced_chapter', 'paid_chapter']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PromiseEventInline]
    ordering = ['priority', 'title']
    
    fieldsets = (
        ('Promise', {
            'fields': ('project', 'promise_key', 'title', 'description')
        }),
        ('Status', {
            'fields': ('status', 'priority')
        }),
        ('Kapitel', {
            'fields': ('introduced_chapter', 'paid_chapter')
        }),
        ('Metadaten', {
            'fields': ('tags', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PromiseEvent)
class PromiseEventAdmin(admin.ModelAdmin):
    """Admin für Promise-Events (für direkten Zugriff)."""
    list_display = ['promise', 'chapter', 'event_type', 'created_at']
    list_filter = ['event_type', 'promise__project']
    search_fields = ['promise__title', 'note']
    autocomplete_fields = ['promise', 'chapter', 'created_by']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


# =============================================================================
# STYLE ISSUES ADMIN
# =============================================================================


@admin.register(StyleIssue)
class StyleIssueAdmin(admin.ModelAdmin):
    """Admin für Style Issues."""
    list_display = [
        'get_chapter',
        'issue_type',
        'get_severity',
        'is_fixed',
        'is_ignored',
        'created_at'
    ]
    list_filter = ['issue_type', 'is_fixed', 'is_ignored', 'issue_type__severity']
    search_fields = ['text_excerpt', 'suggestion', 'explanation']
    readonly_fields = ['created_at', 'quality_score']
    autocomplete_fields = ['issue_type', 'fixed_by']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Issue', {
            'fields': ('quality_score', 'issue_type')
        }),
        ('Text', {
            'fields': ('text_excerpt', 'line_number', 'char_position')
        }),
        ('Korrektur', {
            'fields': ('suggestion', 'explanation')
        }),
        ('Status', {
            'fields': ('is_fixed', 'fixed_at', 'fixed_by', 'is_ignored')
        }),
        ('Metadaten', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    @admin.display(description='Kapitel')
    def get_chapter(self, obj):
        return obj.quality_score.chapter if obj.quality_score else '-'
    
    @admin.display(description='Severity', ordering='issue_type__severity')
    def get_severity(self, obj):
        severity_map = {1: '🔵 Info', 2: '🟡 Warning', 3: '🟠 Error', 4: '🔴 Blocker'}
        return severity_map.get(obj.issue_type.severity, str(obj.issue_type.severity))
