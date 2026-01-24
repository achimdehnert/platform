"""
Research Hub - Django Admin Configuration
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import ResearchProject, ResearchSource, ResearchFinding, ResearchResult, ResearchTemplate


@admin.register(ResearchProject)
class ResearchProjectAdmin(admin.ModelAdmin):
    """Admin configuration for Research Hub projects."""
    
    list_display = [
        'name',
        'research_type_badge',
        'status_badge',
        'current_phase',
        'owner',
        'sources_count',
        'findings_count',
        'created_at',
    ]
    list_filter = ['status', 'research_type', 'current_phase', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'query']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    raw_id_fields = ['owner']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'query', 'status')
        }),
        ('Research Settings', {
            'fields': ('research_type', 'output_format')
        }),
        ('Academic Settings', {
            'fields': ('citation_style', 'require_peer_reviewed'),
            'classes': ('collapse',),
            'description': 'Settings for academic research projects'
        }),
        ('Workflow', {
            'fields': ('current_phase', 'metadata')
        }),
        ('Ownership', {
            'fields': ('owner', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def research_type_badge(self, obj):
        """Display research type as colored badge."""
        icons = {
            'quick_facts': '🔍',
            'deep_dive': '📊',
            'academic': '🎓',
        }
        colors = {
            'quick_facts': '#10B981',
            'deep_dive': '#3B82F6',
            'academic': '#8B5CF6',
        }
        icon = icons.get(obj.research_type, '📋')
        color = colors.get(obj.research_type, '#6B7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 500;">{} {}</span>',
            color,
            icon,
            obj.get_research_type_display()
        )
    research_type_badge.short_description = 'Type'
    
    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'draft': '#6B7280',
            'in_progress': '#3B82F6',
            'review': '#F59E0B',
            'completed': '#10B981',
            'archived': '#9CA3AF',
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 500;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def sources_count(self, obj):
        return obj.sources.count()
    sources_count.short_description = 'Sources'
    
    def findings_count(self, obj):
        return obj.findings.count()
    findings_count.short_description = 'Findings'


@admin.register(ResearchSource)
class ResearchSourceAdmin(admin.ModelAdmin):
    """Admin configuration for Research Sources."""
    
    list_display = [
        'title_short',
        'project',
        'source_type',
        'relevance_display',
        'credibility_display',
        'created_at',
    ]
    list_filter = ['source_type', 'created_at']
    search_fields = ['title', 'url', 'snippet', 'project__name']
    raw_id_fields = ['project']
    
    def title_short(self, obj):
        return obj.title[:60] + '...' if len(obj.title) > 60 else obj.title
    title_short.short_description = 'Title'
    
    def relevance_display(self, obj):
        color = '#10B981' if obj.relevance_score > 0.7 else '#F59E0B' if obj.relevance_score > 0.4 else '#EF4444'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.0%}</span>',
            color,
            obj.relevance_score
        )
    relevance_display.short_description = 'Relevance'
    
    def credibility_display(self, obj):
        color = '#10B981' if obj.credibility_score > 0.7 else '#F59E0B' if obj.credibility_score > 0.4 else '#EF4444'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.0%}</span>',
            color,
            obj.credibility_score
        )
    credibility_display.short_description = 'Credibility'


@admin.register(ResearchFinding)
class ResearchFindingAdmin(admin.ModelAdmin):
    """Admin configuration for Research Findings."""
    
    list_display = [
        'content_short',
        'project',
        'finding_type',
        'importance',
        'verified_badge',
        'created_at',
    ]
    list_filter = ['finding_type', 'is_verified', 'importance', 'created_at']
    search_fields = ['content', 'project__name']
    raw_id_fields = ['project', 'source']
    
    def content_short(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    content_short.short_description = 'Content'
    
    def verified_badge(self, obj):
        if obj.is_verified:
            return format_html('<span style="color: #10B981;">✓ Verified</span>')
        return format_html('<span style="color: #9CA3AF;">Pending</span>')
    verified_badge.short_description = 'Verified'


@admin.register(ResearchResult)
class ResearchResultAdmin(admin.ModelAdmin):
    """Admin configuration for Research Hub results."""
    
    list_display = [
        'project',
        'handler_name',
        'phase',
        'success_badge',
        'execution_time_display',
        'created_at',
    ]
    list_filter = ['success', 'phase', 'handler_name', 'created_at']
    search_fields = ['project__name', 'handler_name', 'error_message']
    readonly_fields = ['created_at']
    raw_id_fields = ['project']
    
    def success_badge(self, obj):
        """Display success status as badge."""
        if obj.success:
            return format_html(
                '<span style="color: #10B981; font-weight: bold;">✓ Success</span>'
            )
        return format_html(
            '<span style="color: #EF4444; font-weight: bold;">✗ Failed</span>'
        )
    success_badge.short_description = 'Status'
    
    def execution_time_display(self, obj):
        """Display execution time formatted."""
        if obj.execution_time_ms > 1000:
            return f"{obj.execution_time_ms / 1000:.2f}s"
        return f"{obj.execution_time_ms}ms"
    execution_time_display.short_description = 'Duration'


@admin.register(ResearchTemplate)
class ResearchTemplateAdmin(admin.ModelAdmin):
    """Admin configuration for Research Templates."""
    
    list_display = [
        'name',
        'category_badge',
        'research_type',
        'is_system_badge',
        'is_public',
        'usage_count',
        'created_at',
    ]
    list_filter = ['category', 'research_type', 'is_system', 'is_public', 'is_active']
    search_fields = ['name', 'description', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    raw_id_fields = ['owner']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'category')
        }),
        ('Research Settings', {
            'fields': ('research_type', 'output_format')
        }),
        ('Academic Settings', {
            'fields': ('citation_style', 'require_peer_reviewed'),
            'classes': ('collapse',)
        }),
        ('Template Structure', {
            'fields': ('sections', 'default_query_template'),
            'classes': ('collapse',)
        }),
        ('Search Settings', {
            'fields': ('source_filters', 'min_sources', 'max_sources'),
            'classes': ('collapse',)
        }),
        ('Visibility', {
            'fields': ('owner', 'is_public', 'is_system', 'is_active')
        }),
        ('Statistics', {
            'fields': ('usage_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def category_badge(self, obj):
        """Display category as badge."""
        colors = {
            'literature_review': '#8B5CF6',
            'market_research': '#3B82F6',
            'competitive_analysis': '#F59E0B',
            'fact_checking': '#10B981',
            'technical_research': '#EC4899',
            'general': '#6B7280',
        }
        color = colors.get(obj.category, '#6B7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_category_display()
        )
    category_badge.short_description = 'Category'
    
    def is_system_badge(self, obj):
        """Display system status."""
        if obj.is_system:
            return format_html('<span style="color: #8B5CF6;">⚙️ System</span>')
        return format_html('<span style="color: #6B7280;">User</span>')
    is_system_badge.short_description = 'Type'
