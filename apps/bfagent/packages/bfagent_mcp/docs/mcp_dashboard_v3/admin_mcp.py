"""
MCP Dashboard Admin
===================

Django Admin Konfiguration für alle MCP Models.

Features:
- Farbkodierte Badges für Risk/Protection Levels
- Inline-Editing für Components
- Filterbare Listen
- Quick Actions

Author: BF Agent Team
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models_mcp import (
    Domain,
    MCPRiskLevel,
    MCPProtectionLevel,
    MCPPathCategory,
    MCPComponentType,
    MCPDomainConfig,
    MCPDomainComponent,
    MCPProtectedPath,
    MCPRefactorSession,
    MCPSessionFileChange,
    MCPRefactoringRule,
    TableNamingConvention,
)


# =============================================================================
# MIXINS
# =============================================================================

class ActiveFilterMixin:
    """Mixin to filter by is_active by default."""
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.GET.get('is_active__exact'):
            # Default to showing only active items
            return qs.filter(is_active=True)
        return qs


class ColorBadgeMixin:
    """Mixin for displaying colored badges."""
    
    def colored_badge(self, text, color='secondary', icon=''):
        """Create a Bootstrap-style badge."""
        return format_html(
            '<span class="badge bg-{}" style="font-size: 0.9em;">{} {}</span>',
            color, icon, text
        )


# =============================================================================
# LOOKUP MODEL ADMINS
# =============================================================================

@admin.register(MCPRiskLevel)
class MCPRiskLevelAdmin(ColorBadgeMixin, admin.ModelAdmin):
    list_display = ['display_badge', 'severity_score', 'requires_approval', 'requires_backup', 'is_active']
    list_filter = ['requires_approval', 'requires_backup', 'is_active']
    search_fields = ['name', 'display_name']
    ordering = ['-severity_score']
    
    def display_badge(self, obj):
        return self.colored_badge(obj.display_name, obj.color, obj.icon)
    display_badge.short_description = 'Risk Level'


@admin.register(MCPProtectionLevel)
class MCPProtectionLevelAdmin(ColorBadgeMixin, admin.ModelAdmin):
    list_display = ['display_badge', 'severity_score', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'display_name']
    ordering = ['-severity_score']
    
    def display_badge(self, obj):
        return self.colored_badge(obj.display_name, obj.color, obj.icon)
    display_badge.short_description = 'Protection Level'


@admin.register(MCPPathCategory)
class MCPPathCategoryAdmin(admin.ModelAdmin):
    list_display = ['icon', 'display_name', 'order', 'is_active']
    list_editable = ['order']
    list_filter = ['is_active']
    search_fields = ['name', 'display_name']
    ordering = ['order']


@admin.register(MCPComponentType)
class MCPComponentTypeAdmin(admin.ModelAdmin):
    list_display = ['icon', 'display_name', 'file_pattern', 'is_refactorable', 'order', 'is_active']
    list_editable = ['order', 'is_refactorable']
    list_filter = ['is_refactorable', 'is_active']
    search_fields = ['name', 'display_name', 'file_pattern']
    ordering = ['order']


# =============================================================================
# DOMAIN ADMIN
# =============================================================================

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['domain_id', 'display_name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['domain_id', 'name', 'display_name']
    readonly_fields = ['created_at', 'updated_at']


# =============================================================================
# DOMAIN CONFIG ADMIN
# =============================================================================

class MCPDomainComponentInline(admin.TabularInline):
    model = MCPDomainComponent
    extra = 0
    fields = ['component_type', 'name', 'file_path', 'is_refactorable', 'is_active']
    readonly_fields = ['last_refactored']
    autocomplete_fields = ['component_type']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('component_type')


@admin.register(MCPDomainConfig)
class MCPDomainConfigAdmin(ColorBadgeMixin, admin.ModelAdmin):
    list_display = [
        'domain_display',
        'base_path',
        'risk_badge',
        'component_count_display',
        'status_badges',
        'refactor_order',
        'is_active',
    ]
    list_filter = [
        'risk_level',
        'allows_refactoring',
        'is_protected',
        'is_refactor_ready',
        'is_active',
    ]
    search_fields = ['domain__domain_id', 'domain__display_name', 'base_path']
    list_editable = ['refactor_order']
    ordering = ['refactor_order', 'domain__name']
    
    autocomplete_fields = ['domain', 'risk_level', 'depends_on']
    filter_horizontal = ['depends_on']
    readonly_fields = ['created_at', 'updated_at']
    
    inlines = [MCPDomainComponentInline]
    
    fieldsets = [
        (None, {
            'fields': ['domain', 'base_path', 'risk_level']
        }),
        ('Refactoring Settings', {
            'fields': [
                'allows_refactoring',
                'is_protected',
                'is_refactor_ready',
                'refactor_order',
            ]
        }),
        ('Dependencies', {
            'fields': ['depends_on'],
            'classes': ['collapse']
        }),
        ('Notes', {
            'fields': ['notes'],
            'classes': ['collapse']
        }),
        ('Audit', {
            'fields': ['is_active', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def domain_display(self, obj):
        return obj.domain.display_name
    domain_display.short_description = 'Domain'
    domain_display.admin_order_field = 'domain__display_name'
    
    def risk_badge(self, obj):
        return self.colored_badge(
            obj.risk_level.name.upper(),
            obj.risk_level.color,
            obj.risk_level.icon
        )
    risk_badge.short_description = 'Risk'
    
    def component_count_display(self, obj):
        count = obj.components.filter(is_active=True).count()
        return format_html('<span class="badge bg-info">{}</span>', count)
    component_count_display.short_description = 'Components'
    
    def status_badges(self, obj):
        badges = []
        if obj.is_protected:
            badges.append(self.colored_badge('Protected', 'danger', '🔒'))
        elif obj.is_refactor_ready:
            badges.append(self.colored_badge('Ready', 'success', '✓'))
        if obj.allows_refactoring and not obj.is_protected:
            badges.append(self.colored_badge('Refactorable', 'primary', ''))
        return mark_safe(' '.join(badges)) if badges else '-'
    status_badges.short_description = 'Status'


@admin.register(MCPDomainComponent)
class MCPDomainComponentAdmin(admin.ModelAdmin):
    list_display = ['name', 'domain_config', 'component_type', 'file_path', 'is_refactorable', 'is_active']
    list_filter = ['component_type', 'is_refactorable', 'is_active', 'domain_config__domain']
    search_fields = ['name', 'file_path', 'domain_config__domain__display_name']
    autocomplete_fields = ['domain_config', 'component_type']
    readonly_fields = ['last_refactored', 'created_at', 'updated_at']


# =============================================================================
# PROTECTED PATHS ADMIN
# =============================================================================

@admin.register(MCPProtectedPath)
class MCPProtectedPathAdmin(ColorBadgeMixin, admin.ModelAdmin):
    list_display = [
        'path_pattern',
        'protection_badge',
        'category_display',
        'is_regex',
        'reason',
        'is_active',
    ]
    list_filter = ['protection_level', 'category', 'is_regex', 'is_active']
    search_fields = ['path_pattern', 'reason']
    ordering = ['category__order', 'path_pattern']
    
    autocomplete_fields = ['protection_level', 'category']
    
    def protection_badge(self, obj):
        return self.colored_badge(
            obj.protection_level.name,
            obj.protection_level.color,
            obj.protection_level.icon
        )
    protection_badge.short_description = 'Protection'
    
    def category_display(self, obj):
        if obj.category:
            return f"{obj.category.icon} {obj.category.display_name}"
        return '-'
    category_display.short_description = 'Category'


# =============================================================================
# REFACTOR SESSION ADMIN
# =============================================================================

class MCPSessionFileChangeInline(admin.TabularInline):
    model = MCPSessionFileChange
    extra = 0
    fields = ['file_path', 'change_type', 'lines_added', 'lines_removed']
    readonly_fields = ['file_path', 'change_type', 'lines_added', 'lines_removed']
    can_delete = False
    max_num = 0
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(MCPRefactorSession)
class MCPRefactorSessionAdmin(ColorBadgeMixin, admin.ModelAdmin):
    list_display = [
        'id',
        'domain_display',
        'status_badge',
        'files_changed',
        'lines_stats',
        'triggered_by',
        'started_at',
        'duration_display',
    ]
    list_filter = ['status', 'domain_config__domain', 'triggered_by']
    search_fields = ['domain_config__domain__display_name', 'error_message']
    date_hierarchy = 'started_at'
    ordering = ['-started_at']
    
    readonly_fields = [
        'started_at', 'ended_at', 'files_changed',
        'lines_added', 'lines_removed', 'celery_task_id',
        'backup_path', 'created_at', 'updated_at',
    ]
    
    inlines = [MCPSessionFileChangeInline]
    
    fieldsets = [
        (None, {
            'fields': ['domain_config', 'status', 'error_message']
        }),
        ('Timing', {
            'fields': ['started_at', 'ended_at']
        }),
        ('Statistics', {
            'fields': ['files_changed', 'lines_added', 'lines_removed']
        }),
        ('Configuration', {
            'fields': ['components_selected', 'triggered_by', 'triggered_by_user']
        }),
        ('Technical', {
            'fields': ['celery_task_id', 'backup_path'],
            'classes': ['collapse']
        }),
    ]
    
    def domain_display(self, obj):
        return obj.domain_config.domain.display_name
    domain_display.short_description = 'Domain'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'secondary',
            'in_progress': 'primary',
            'completed': 'success',
            'failed': 'danger',
            'cancelled': 'warning',
        }
        icons = {
            'pending': '⏳',
            'in_progress': '🔄',
            'completed': '✓',
            'failed': '❌',
            'cancelled': '⚠️',
        }
        return self.colored_badge(
            obj.get_status_display(),
            colors.get(obj.status, 'secondary'),
            icons.get(obj.status, '')
        )
    status_badge.short_description = 'Status'
    
    def lines_stats(self, obj):
        return format_html(
            '<span class="text-success">+{}</span> / '
            '<span class="text-danger">-{}</span>',
            obj.lines_added, obj.lines_removed
        )
    lines_stats.short_description = '+/-'
    
    def duration_display(self, obj):
        if obj.duration:
            return str(obj.duration).split('.')[0]  # Remove microseconds
        return '-'
    duration_display.short_description = 'Duration'


@admin.register(MCPSessionFileChange)
class MCPSessionFileChangeAdmin(admin.ModelAdmin):
    list_display = ['session', 'file_path', 'change_type', 'lines_added', 'lines_removed']
    list_filter = ['change_type', 'session__domain_config__domain']
    search_fields = ['file_path', 'session__id']
    readonly_fields = ['session', 'file_path', 'change_type', 'lines_added', 'lines_removed', 'diff_content']


# =============================================================================
# REFACTORING RULES ADMIN
# =============================================================================

@admin.register(MCPRefactoringRule)
class MCPRefactoringRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'component_type', 'order', 'is_active']
    list_filter = ['component_type', 'is_active']
    list_editable = ['order']
    search_fields = ['name', 'description']
    ordering = ['component_type', 'order']
    
    fieldsets = [
        (None, {
            'fields': ['name', 'component_type', 'order', 'is_active']
        }),
        ('Pattern', {
            'fields': ['pattern', 'replacement'],
            'description': 'Regex pattern and replacement string'
        }),
        ('Condition', {
            'fields': ['condition_code'],
            'classes': ['collapse'],
            'description': 'Python code that returns True/False'
        }),
        ('Documentation', {
            'fields': ['description']
        }),
    ]


# =============================================================================
# NAMING CONVENTIONS ADMIN
# =============================================================================

@admin.register(TableNamingConvention)
class TableNamingConventionAdmin(ColorBadgeMixin, admin.ModelAdmin):
    list_display = [
        'app_label',
        'component_type',
        'file_pattern',
        'class_pattern',
        'enforce_badge',
        'is_active',
    ]
    list_filter = ['component_type', 'enforce_convention', 'is_active']
    list_editable = ['enforce_convention']
    search_fields = ['app_label', 'component_type', 'description']
    ordering = ['app_label', 'component_type']
    
    fieldsets = [
        (None, {
            'fields': ['app_label', 'component_type']
        }),
        ('Patterns', {
            'fields': ['file_pattern', 'class_pattern', 'prefix', 'suffix']
        }),
        ('Settings', {
            'fields': ['enforce_convention', 'is_active']
        }),
        ('Documentation', {
            'fields': ['description', 'example']
        }),
    ]
    
    def enforce_badge(self, obj):
        if obj.enforce_convention:
            return self.colored_badge('Strict', 'danger', '⚠️')
        return self.colored_badge('Flexible', 'secondary', '')
    enforce_badge.short_description = 'Enforcement'
