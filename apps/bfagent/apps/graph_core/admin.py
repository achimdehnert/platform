"""
Graph Core Admin Configuration
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Framework, FrameworkPhase, FrameworkStep,
    NodeType, EdgeType, GraphNode, GraphEdge,
    ProjectFramework
)


# =============================================================================
# INLINES
# =============================================================================

class FrameworkPhaseInline(admin.TabularInline):
    model = FrameworkPhase
    extra = 0
    fields = ['order', 'name', 'slug', 'position_start', 'position_end', 'color', 'is_required']
    ordering = ['order']


class FrameworkStepInline(admin.TabularInline):
    model = FrameworkStep
    extra = 0
    fields = ['order', 'name', 'slug', 'typical_position', 'estimated_chapters']
    ordering = ['order']


# =============================================================================
# FRAMEWORK ADMIN
# =============================================================================

@admin.register(Framework)
class FrameworkAdmin(admin.ModelAdmin):
    list_display = [
        'display_name', 'domain', 'phase_count_display', 'step_count_display',
        'is_active', 'is_default', 'sort_order'
    ]
    list_filter = ['domain', 'is_active', 'is_default']
    search_fields = ['name', 'display_name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['domain', 'sort_order', 'name']
    inlines = [FrameworkPhaseInline]
    
    fieldsets = (
        ('Identity', {
            'fields': ('name', 'slug', 'display_name', 'description')
        }),
        ('Classification', {
            'fields': ('domain',)
        }),
        ('Visual', {
            'fields': ('icon', 'color')
        }),
        ('Configuration', {
            'fields': ('config',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_default', 'sort_order')
        }),
    )
    
    def phase_count_display(self, obj):
        return obj.phase_count
    phase_count_display.short_description = 'Phases'
    
    def step_count_display(self, obj):
        return obj.step_count
    step_count_display.short_description = 'Steps'


@admin.register(FrameworkPhase)
class FrameworkPhaseAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'framework', 'order', 'position_range_display',
        'step_count_display', 'is_required'
    ]
    list_filter = ['framework', 'is_required']
    search_fields = ['name', 'description', 'framework__name']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['framework', 'order']
    inlines = [FrameworkStepInline]
    
    def position_range_display(self, obj):
        return f"{obj.position_start:.0%} - {obj.position_end:.0%}"
    position_range_display.short_description = 'Position'
    
    def step_count_display(self, obj):
        return obj.step_count
    step_count_display.short_description = 'Steps'


@admin.register(FrameworkStep)
class FrameworkStepAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'phase', 'order', 'typical_position_display',
        'estimated_chapters', 'estimated_word_count'
    ]
    list_filter = ['phase__framework', 'phase']
    search_fields = ['name', 'description', 'chapter_guidance']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['phase__framework', 'phase__order', 'order']
    
    def typical_position_display(self, obj):
        return f"{obj.typical_position:.0%}"
    typical_position_display.short_description = 'Position'


# =============================================================================
# NODE/EDGE TYPE ADMIN
# =============================================================================

@admin.register(NodeType)
class NodeTypeAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'domain', 'shape', 'color_display']
    list_filter = ['domain', 'shape']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['domain', 'name']
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 10px; border-radius: 3px;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = 'Color'


@admin.register(EdgeType)
class EdgeTypeAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'domain', 'is_directed', 'line_style', 'color_display']
    list_filter = ['domain', 'is_directed', 'line_style']
    search_fields = ['name', 'display_name', 'description']
    filter_horizontal = ['source_types', 'target_types']
    ordering = ['domain', 'name']
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 10px; border-radius: 3px;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = 'Color'


# =============================================================================
# GRAPH NODE/EDGE ADMIN
# =============================================================================

@admin.register(GraphNode)
class GraphNodeAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'node_type', 'position_display', 'is_active', 'created_at']
    list_filter = ['node_type', 'is_active', 'project']
    search_fields = ['name', 'description', 'project__title']
    ordering = ['project', 'node_type', 'name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Identity', {
            'fields': ('project', 'node_type', 'name', 'description')
        }),
        ('Properties', {
            'fields': ('properties',),
            'classes': ('collapse',)
        }),
        ('Visual', {
            'fields': ('position_x', 'position_y', 'custom_color', 'custom_icon')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def position_display(self, obj):
        return f"({obj.position_x:.0f}, {obj.position_y:.0f})"
    position_display.short_description = 'Position'


@admin.register(GraphEdge)
class GraphEdgeAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'project', 'edge_type', 'weight', 'is_active']
    list_filter = ['edge_type', 'is_active', 'project']
    search_fields = ['source__name', 'target__name', 'label']
    ordering = ['project', 'edge_type']
    readonly_fields = ['created_at', 'updated_at']


# =============================================================================
# PROJECT FRAMEWORK ADMIN
# =============================================================================

@admin.register(ProjectFramework)
class ProjectFrameworkAdmin(admin.ModelAdmin):
    list_display = [
        'project', 'framework', 'progress_display', 'current_phase',
        'is_primary', 'started_at', 'completed_at'
    ]
    list_filter = ['framework', 'is_primary']
    search_fields = ['project__title', 'framework__name']
    ordering = ['project', '-is_primary']
    readonly_fields = ['created_at', 'updated_at']
    
    def progress_display(self, obj):
        color = 'success' if obj.progress_percent >= 100 else 'primary'
        return format_html(
            '<div class="progress" style="width: 100px; height: 20px;">'
            '<div class="progress-bar bg-{}" style="width: {}%;">{:.0f}%</div>'
            '</div>',
            color, obj.progress_percent, obj.progress_percent
        )
    progress_display.short_description = 'Progress'
