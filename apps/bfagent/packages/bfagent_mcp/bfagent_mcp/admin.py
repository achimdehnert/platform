"""
BF Agent MCP Server - Django Admin
===================================

Admin-Interface für alle MCP Models.
Ermöglicht DB-getriebene Konfiguration ohne Code-Deployment.

Features:
- Colored status badges
- Search und Filtering
- Inline editing
- Import/Export (optional)
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

# Import models - handle both standalone and integrated mode
try:
    from .models import (
        Tag, Domain, Phase, Handler, HandlerTag, DomainTag,
        BestPractice, PromptTemplate, HandlerExecution,
    )
    from .models_extension import (
        CodingConvention, ProjectStructure, MCPContext,
        ConventionCategory, ConventionSeverity, ComponentType, ContextType,
        DomainRefactorConfig, ProtectedPath, RefactorSession, RefactorRisk,
    )
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False


if MODELS_AVAILABLE:
    
    # =========================================================================
    # HELPER MIXINS
    # =========================================================================
    
    class ColoredStatusMixin:
        """Mixin for colored status display."""
        
        def colored_status(self, obj):
            colors = {
                'production': '#22c55e',  # green
                'beta': '#f59e0b',        # amber
                'development': '#3b82f6', # blue
                'planned': '#8b5cf6',     # purple
                'deprecated': '#ef4444',  # red
            }
            status = getattr(obj, 'status', None)
            if status:
                color = colors.get(status, '#6b7280')
                return format_html(
                    '<span style="background-color: {}; color: white; '
                    'padding: 3px 10px; border-radius: 3px;">{}</span>',
                    color, status.title()
                )
            return '-'
        colored_status.short_description = _("Status")
    
    
    class SeverityColorMixin:
        """Mixin for colored severity display."""
        
        def colored_severity(self, obj):
            colors = {
                'error': '#ef4444',    # red
                'warning': '#f59e0b',  # amber
                'info': '#3b82f6',     # blue
                'hint': '#8b5cf6',     # purple
            }
            severity = getattr(obj, 'severity', None)
            if severity:
                color = colors.get(severity, '#6b7280')
                return format_html(
                    '<span style="background-color: {}; color: white; '
                    'padding: 3px 10px; border-radius: 3px;">{}</span>',
                    color, severity.upper()
                )
            return '-'
        colored_severity.short_description = _("Severity")
    
    
    class ActiveStatusMixin:
        """Mixin for active/inactive display."""
        
        def active_badge(self, obj):
            if obj.is_active:
                return format_html(
                    '<span style="color: #22c55e;">●</span> Active'
                )
            return format_html(
                '<span style="color: #ef4444;">●</span> Inactive'
            )
        active_badge.short_description = _("Status")
    
    
    # =========================================================================
    # TAG ADMIN
    # =========================================================================
    
    @admin.register(Tag)
    class TagAdmin(admin.ModelAdmin):
        list_display = ['name', 'display_name', 'category', 'color_preview', 'handler_count']
        list_filter = ['category']
        search_fields = ['name', 'display_name']
        ordering = ['category', 'name']
        
        def color_preview(self, obj):
            return format_html(
                '<span style="background-color: {}; padding: 5px 15px; '
                'border-radius: 3px; color: white;">{}</span>',
                obj.color, obj.color
            )
        color_preview.short_description = _("Color")
        
        def handler_count(self, obj):
            return obj.handlers.count()
        handler_count.short_description = _("Handlers")
    
    
    # =========================================================================
    # DOMAIN ADMIN
    # =========================================================================
    
    class PhaseInline(admin.TabularInline):
        model = Phase
        extra = 0
        ordering = ['order']
        fields = ['name', 'display_name', 'order', 'color', 'icon', 'is_active']
    
    
    class HandlerInline(admin.TabularInline):
        model = Handler
        extra = 0
        fields = ['name', 'handler_type', 'ai_provider', 'is_active']
        readonly_fields = ['name']
        show_change_link = True
    
    
    @admin.register(Domain)
    class DomainAdmin(ColoredStatusMixin, admin.ModelAdmin):
        list_display = ['domain_id', 'display_name', 'colored_status', 'handler_count', 'phase_count', 'icon']
        list_filter = ['status', 'is_active']
        search_fields = ['domain_id', 'display_name', 'description']
        ordering = ['status', 'domain_id']
        inlines = [PhaseInline, HandlerInline]
        
        fieldsets = (
            (None, {
                'fields': ('domain_id', 'display_name', 'description')
            }),
            (_('Appearance'), {
                'fields': ('icon', 'color'),
                'classes': ('collapse',)
            }),
            (_('Status'), {
                'fields': ('status', 'is_active')
            }),
        )
        
        def handler_count(self, obj):
            count = obj.handlers.filter(is_active=True).count()
            return format_html('<strong>{}</strong>', count)
        handler_count.short_description = _("Handlers")
        
        def phase_count(self, obj):
            return obj.phases.count()
        phase_count.short_description = _("Phases")
    
    
    # =========================================================================
    # HANDLER ADMIN
    # =========================================================================
    
    @admin.register(Handler)
    class HandlerAdmin(ActiveStatusMixin, admin.ModelAdmin):
        list_display = ['name', 'domain', 'handler_type_badge', 'ai_provider', 'active_badge', 'tag_list']
        list_filter = ['domain', 'handler_type', 'ai_provider', 'is_active']
        search_fields = ['name', 'description']
        ordering = ['domain', 'name']
        filter_horizontal = ['tags']
        
        fieldsets = (
            (None, {
                'fields': ('name', 'domain', 'phase', 'description')
            }),
            (_('Type & Provider'), {
                'fields': ('handler_type', 'ai_provider')
            }),
            (_('Schemas'), {
                'fields': ('input_schema', 'output_schema'),
                'classes': ('collapse',)
            }),
            (_('Tags'), {
                'fields': ('tags',)
            }),
            (_('Status'), {
                'fields': ('is_active',)
            }),
        )
        
        def handler_type_badge(self, obj):
            colors = {
                'ai_powered': '#8b5cf6',
                'rule_based': '#3b82f6',
                'hybrid': '#22c55e',
                'utility': '#6b7280',
            }
            color = colors.get(obj.handler_type, '#6b7280')
            return format_html(
                '<span style="background-color: {}; color: white; '
                'padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
                color, obj.get_handler_type_display()
            )
        handler_type_badge.short_description = _("Type")
        
        def tag_list(self, obj):
            tags = obj.tags.all()[:3]
            return ', '.join(t.name for t in tags)
        tag_list.short_description = _("Tags")
    
    
    # =========================================================================
    # BEST PRACTICE ADMIN
    # =========================================================================
    
    @admin.register(BestPractice)
    class BestPracticeAdmin(admin.ModelAdmin):
        list_display = ['topic', 'display_name', 'order', 'content_preview']
        list_editable = ['order']
        search_fields = ['topic', 'display_name', 'content']
        ordering = ['order', 'topic']
        filter_horizontal = ['related_topics']
        
        def content_preview(self, obj):
            preview = obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
            return preview
        content_preview.short_description = _("Preview")
    
    
    # =========================================================================
    # CODING CONVENTION ADMIN
    # =========================================================================
    
    @admin.register(CodingConvention)
    class CodingConventionAdmin(SeverityColorMixin, ActiveStatusMixin, admin.ModelAdmin):
        list_display = ['name', 'display_name', 'category', 'colored_severity', 'applies_to_list', 'active_badge']
        list_filter = ['category', 'severity', 'is_active']
        search_fields = ['name', 'display_name', 'rule']
        ordering = ['category', 'order', 'name']
        list_editable = ['category']
        
        fieldsets = (
            (None, {
                'fields': ('name', 'display_name', 'category', 'severity')
            }),
            (_('Rule'), {
                'fields': ('rule', 'rationale')
            }),
            (_('Examples'), {
                'fields': ('example_good', 'example_bad'),
                'classes': ('collapse',)
            }),
            (_('Applicability'), {
                'fields': ('applies_to', 'check_pattern')
            }),
            (_('Ordering'), {
                'fields': ('order', 'is_active')
            }),
        )
        
        def applies_to_list(self, obj):
            if obj.applies_to:
                return ', '.join(obj.applies_to)
            return '-'
        applies_to_list.short_description = _("Applies To")
    
    
    # =========================================================================
    # PROJECT STRUCTURE ADMIN
    # =========================================================================
    
    @admin.register(ProjectStructure)
    class ProjectStructureAdmin(ActiveStatusMixin, admin.ModelAdmin):
        list_display = ['component_type', 'path_pattern', 'file_naming_pattern', 'active_badge']
        list_filter = ['is_active']
        search_fields = ['path_pattern', 'description']
        filter_horizontal = ['related_conventions']
        
        fieldsets = (
            (None, {
                'fields': ('component_type', 'description')
            }),
            (_('Path & Naming'), {
                'fields': ('path_pattern', 'file_naming_pattern', 'class_naming_pattern')
            }),
            (_('Template'), {
                'fields': ('boilerplate_template',),
                'classes': ('collapse',)
            }),
            (_('Related'), {
                'fields': ('related_conventions',)
            }),
            (_('Status'), {
                'fields': ('is_active',)
            }),
        )
    
    
    # =========================================================================
    # MCP CONTEXT ADMIN
    # =========================================================================
    
    @admin.register(MCPContext)
    class MCPContextAdmin(ActiveStatusMixin, admin.ModelAdmin):
        list_display = ['context_type', 'display_name', 'include_flags', 'active_badge']
        list_filter = ['include_conventions', 'include_best_practices', 'is_active']
        search_fields = ['display_name', 'context_template']
        
        fieldsets = (
            (None, {
                'fields': ('context_type', 'display_name')
            }),
            (_('Template'), {
                'fields': ('context_template', 'required_info')
            }),
            (_('Include Options'), {
                'fields': (
                    'include_conventions', 'include_best_practices',
                    'include_similar_code', 'include_structure'
                )
            }),
            (_('Filter'), {
                'fields': ('best_practice_topics', 'convention_categories'),
                'classes': ('collapse',)
            }),
            (_('Status'), {
                'fields': ('is_active',)
            }),
        )
        
        def include_flags(self, obj):
            flags = []
            if obj.include_conventions:
                flags.append('Conv')
            if obj.include_best_practices:
                flags.append('BP')
            if obj.include_similar_code:
                flags.append('Code')
            if obj.include_structure:
                flags.append('Struct')
            return ', '.join(flags) if flags else '-'
        include_flags.short_description = _("Includes")
    
    
    # =========================================================================
    # PROMPT TEMPLATE ADMIN
    # =========================================================================
    
    @admin.register(PromptTemplate)
    class PromptTemplateAdmin(ActiveStatusMixin, admin.ModelAdmin):
        list_display = ['name', 'domain', 'ai_provider', 'model_name', 'version', 'active_badge']
        list_filter = ['domain', 'ai_provider', 'is_active']
        search_fields = ['name', 'description']
        ordering = ['domain', 'name']
        
        fieldsets = (
            (None, {
                'fields': ('name', 'domain', 'description')
            }),
            (_('Prompts'), {
                'fields': ('system_prompt', 'user_prompt_template')
            }),
            (_('AI Config'), {
                'fields': ('ai_provider', 'model_name', 'temperature', 'max_tokens')
            }),
            (_('Version'), {
                'fields': ('version', 'is_active')
            }),
        )
    
    
    # =========================================================================
    # HANDLER EXECUTION ADMIN (Read-Only Analytics)
    # =========================================================================
    
    @admin.register(HandlerExecution)
    class HandlerExecutionAdmin(admin.ModelAdmin):
        list_display = ['handler', 'started_at', 'duration_ms', 'success_badge', 'tokens_used', 'cost_usd']
        list_filter = ['success', 'handler__domain', 'handler']
        date_hierarchy = 'started_at'
        ordering = ['-started_at']
        readonly_fields = [
            'handler', 'started_at', 'completed_at', 'duration_ms',
            'success', 'error_message', 'tokens_used', 'cost_usd'
        ]
        
        def success_badge(self, obj):
            if obj.success:
                return format_html('<span style="color: #22c55e;">✓</span>')
            return format_html('<span style="color: #ef4444;">✗</span>')
        success_badge.short_description = _("OK")
        
        def has_add_permission(self, request):
            return False
        
        def has_change_permission(self, request, obj=None):
            return False


    # =========================================================================
    # DOMAIN REFACTOR CONFIG ADMIN
    # =========================================================================
    
    class RiskColorMixin:
        """Mixin for colored risk level display."""
        
        def colored_risk(self, obj):
            colors = {
                'critical': '#dc2626',  # red-600
                'high': '#ea580c',      # orange-600
                'medium': '#ca8a04',    # yellow-600
                'low': '#16a34a',       # green-600
                'minimal': '#0891b2',   # cyan-600
            }
            risk = getattr(obj, 'risk_level', None)
            if risk:
                color = colors.get(risk, '#6b7280')
                return format_html(
                    '<span style="background-color: {}; color: white; '
                    'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
                    color, risk.upper()
                )
            return '-'
        colored_risk.short_description = _("Risk")
    
    
    @admin.register(DomainRefactorConfig)
    class DomainRefactorConfigAdmin(RiskColorMixin, admin.ModelAdmin):
        list_display = [
            'domain', 'base_path', 'colored_risk', 'refactor_order',
            'components_badges', 'status_badges', 'refactor_count'
        ]
        list_filter = ['risk_level', 'is_refactor_ready', 'is_protected', 'is_active']
        search_fields = ['domain__domain_id', 'domain__display_name', 'base_path']
        ordering = ['refactor_order', 'domain__domain_id']
        filter_horizontal = ['depends_on']
        list_editable = ['refactor_order']
        
        fieldsets = (
            (None, {
                'fields': ('domain', 'base_path')
            }),
            (_('Components'), {
                'fields': (
                    ('has_handlers', 'has_services', 'has_repositories'),
                    ('has_models', 'has_schemas', 'has_tests'),
                ),
                'description': _('Which components does this domain have?')
            }),
            (_('Risk Assessment'), {
                'fields': ('risk_level', 'risk_notes')
            }),
            (_('Status'), {
                'fields': (
                    ('is_refactor_ready', 'is_protected', 'requires_approval'),
                    'refactor_order',
                )
            }),
            (_('Dependencies'), {
                'fields': ('depends_on',),
                'description': _('Domains that must be refactored before this one')
            }),
            (_('Tracking'), {
                'fields': (
                    ('last_refactored_at', 'refactor_count'),
                    'last_refactor_notes',
                ),
                'classes': ('collapse',)
            }),
        )
        
        def components_badges(self, obj):
            components = []
            if obj.has_handlers:
                components.append('H')
            if obj.has_services:
                components.append('S')
            if obj.has_repositories:
                components.append('R')
            if obj.has_models:
                components.append('M')
            if obj.has_schemas:
                components.append('Sc')
            if obj.has_tests:
                components.append('T')
            return format_html(
                '<span style="font-family: monospace; font-size: 11px;">{}</span>',
                ' '.join(components) if components else '-'
            )
        components_badges.short_description = _("Components")
        
        def status_badges(self, obj):
            badges = []
            if obj.is_protected:
                badges.append('<span style="color: #dc2626;">🔒</span>')
            if obj.is_refactor_ready:
                badges.append('<span style="color: #16a34a;">✓</span>')
            if obj.requires_approval:
                badges.append('<span style="color: #ca8a04;">⚠</span>')
            return format_html(' '.join(badges)) if badges else '-'
        status_badges.short_description = _("Status")
    
    
    # =========================================================================
    # PROTECTED PATH ADMIN
    # =========================================================================
    
    @admin.register(ProtectedPath)
    class ProtectedPathAdmin(admin.ModelAdmin):
        list_display = [
            'path_pattern', 'category', 'protection_badge', 'reason_preview', 'is_active'
        ]
        list_filter = ['category', 'protection_level', 'is_active']
        search_fields = ['path_pattern', 'reason']
        ordering = ['category', 'path_pattern']
        list_editable = ['is_active']
        
        fieldsets = (
            (None, {
                'fields': ('path_pattern', 'category')
            }),
            (_('Protection'), {
                'fields': ('protection_level', 'reason')
            }),
            (_('Status'), {
                'fields': ('is_active',)
            }),
        )
        
        def protection_badge(self, obj):
            colors = {
                'absolute': '#dc2626',  # red
                'warn': '#ca8a04',      # yellow
                'review': '#2563eb',    # blue
            }
            icons = {
                'absolute': '🔒',
                'warn': '⚠️',
                'review': '👁️',
            }
            color = colors.get(obj.protection_level, '#6b7280')
            icon = icons.get(obj.protection_level, '?')
            return format_html(
                '{} <span style="color: {};">{}</span>',
                icon, color, obj.get_protection_level_display()
            )
        protection_badge.short_description = _("Protection")
        
        def reason_preview(self, obj):
            if len(obj.reason) > 50:
                return obj.reason[:50] + '...'
            return obj.reason
        reason_preview.short_description = _("Reason")
    
    
    # =========================================================================
    # REFACTOR SESSION ADMIN (Read-Only Audit Log)
    # =========================================================================
    
    @admin.register(RefactorSession)
    class RefactorSessionAdmin(admin.ModelAdmin):
        list_display = [
            'domain_config', 'started_at', 'status_badge',
            'components_list', 'files_changed', 'duration'
        ]
        list_filter = ['status', 'domain_config__domain']
        date_hierarchy = 'started_at'
        ordering = ['-started_at']
        readonly_fields = [
            'domain_config', 'components_refactored', 'started_at', 'completed_at',
            'status', 'files_changed', 'lines_added', 'lines_removed',
            'summary', 'error_message', 'git_commit_before', 'git_commit_after',
            'created_at', 'updated_at'
        ]
        
        fieldsets = (
            (None, {
                'fields': ('domain_config', 'components_refactored', 'status')
            }),
            (_('Timing'), {
                'fields': ('started_at', 'completed_at')
            }),
            (_('Changes'), {
                'fields': (
                    ('files_changed', 'lines_added', 'lines_removed'),
                    'summary',
                )
            }),
            (_('Git'), {
                'fields': ('git_commit_before', 'git_commit_after'),
                'classes': ('collapse',)
            }),
            (_('Error'), {
                'fields': ('error_message',),
                'classes': ('collapse',)
            }),
        )
        
        def status_badge(self, obj):
            colors = {
                'in_progress': '#2563eb',  # blue
                'completed': '#16a34a',    # green
                'failed': '#dc2626',       # red
                'rolled_back': '#ca8a04',  # yellow
            }
            icons = {
                'in_progress': '⏳',
                'completed': '✓',
                'failed': '✗',
                'rolled_back': '↩️',
            }
            color = colors.get(obj.status, '#6b7280')
            icon = icons.get(obj.status, '?')
            return format_html(
                '{} <span style="color: {};">{}</span>',
                icon, color, obj.get_status_display()
            )
        status_badge.short_description = _("Status")
        
        def components_list(self, obj):
            if obj.components_refactored:
                return ', '.join(obj.components_refactored)
            return '-'
        components_list.short_description = _("Components")
        
        def duration(self, obj):
            if obj.started_at and obj.completed_at:
                delta = obj.completed_at - obj.started_at
                minutes = delta.total_seconds() / 60
                return f"{minutes:.1f} min"
            return '-'
        duration.short_description = _("Duration")
        
        def has_add_permission(self, request):
            return False
        
        def has_change_permission(self, request, obj=None):
            return False


# If models not available, register nothing
else:
    pass
