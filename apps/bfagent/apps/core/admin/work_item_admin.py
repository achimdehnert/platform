# -*- coding: utf-8 -*-
"""
Admin Registration for Unified Work Item System
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from apps.core.models import (
    WorkItem,
    WorkItemType,
    WorkItemStatus,
    WorkItemPriority,
    BugDetails,
    FeatureDetails,
    TaskDetails,
    WorkItemLLMAssignment,
    WorkItemComment,
)


# =============================================================================
# INLINE ADMINS
# =============================================================================

class BugDetailsInline(admin.StackedInline):
    model = BugDetails
    extra = 0
    classes = ['collapse']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('work_item')


class FeatureDetailsInline(admin.StackedInline):
    model = FeatureDetails
    extra = 0
    classes = ['collapse']


class TaskDetailsInline(admin.StackedInline):
    model = TaskDetails
    extra = 0
    classes = ['collapse']


class WorkItemCommentInline(admin.TabularInline):
    model = WorkItemComment
    extra = 0
    readonly_fields = ['created_at', 'author', 'is_from_cascade']
    fields = ['comment_type', 'content', 'author', 'is_from_cascade', 'created_at']


class WorkItemLLMAssignmentInline(admin.TabularInline):
    model = WorkItemLLMAssignment
    extra = 0
    readonly_fields = ['created_at', 'initial_tier', 'attempts', 'cost_usd', 'status']
    fields = ['initial_tier', 'current_tier', 'llm_used', 'status', 'attempts', 'cost_usd', 'created_at']


# =============================================================================
# WORK ITEM ADMIN
# =============================================================================

@admin.register(WorkItem)
class WorkItemAdmin(admin.ModelAdmin):
    """Admin for unified Work Items"""
    
    list_display = [
        'identifier',
        'title_short',
        'item_type_badge',
        'status_badge',
        'priority_badge',
        'domain',
        'assigned_to',
        'llm_tier',
        'created_at',
    ]
    
    list_filter = [
        'item_type',
        'status',
        'priority',
        'domain',
        'llm_tier',
        'created_at',
    ]
    
    search_fields = [
        'identifier',
        'title',
        'description',
        'tags',
    ]
    
    readonly_fields = [
        'id',
        'identifier',
        'created_at',
        'updated_at',
        'started_at',
        'completed_at',
        'legacy_requirement_id',
    ]
    
    fieldsets = [
        ('Identifikation', {
            'fields': ['id', 'identifier', 'item_type']
        }),
        ('Inhalt', {
            'fields': ['title', 'description', 'tags']
        }),
        ('Klassifikation', {
            'fields': ['status', 'priority', 'domain']
        }),
        ('Zuweisung', {
            'fields': ['created_by', 'assigned_to']
        }),
        ('LLM Routing', {
            'fields': ['complexity', 'llm_tier', 'llm_override'],
            'classes': ['collapse']
        }),
        ('Hierarchie', {
            'fields': ['parent'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at', 'started_at', 'completed_at'],
            'classes': ['collapse']
        }),
        ('Migration', {
            'fields': ['legacy_requirement_id', 'metadata'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [
        BugDetailsInline,
        FeatureDetailsInline,
        TaskDetailsInline,
        WorkItemLLMAssignmentInline,
        WorkItemCommentInline,
    ]
    
    list_per_page = 50
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def get_inlines(self, request, obj):
        """Show only relevant detail inline based on item_type"""
        inlines = []
        
        if obj:
            if obj.item_type == WorkItemType.BUG:
                inlines.append(BugDetailsInline)
            elif obj.item_type == WorkItemType.FEATURE:
                inlines.append(FeatureDetailsInline)
            elif obj.item_type == WorkItemType.TASK:
                inlines.append(TaskDetailsInline)
        
        inlines.extend([WorkItemLLMAssignmentInline, WorkItemCommentInline])
        return inlines
    
    def title_short(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_short.short_description = 'Title'
    
    def item_type_badge(self, obj):
        colors = {
            'bug': '#dc3545',
            'feature': '#28a745',
            'task': '#007bff',
            'enhancement': '#6c757d',
            'refactor': '#17a2b8',
        }
        color = colors.get(obj.item_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_item_type_display()
        )
    item_type_badge.short_description = 'Type'
    
    def status_badge(self, obj):
        colors = {
            'backlog': '#6c757d',
            'todo': '#17a2b8',
            'in_progress': '#ffc107',
            'in_review': '#fd7e14',
            'testing': '#6f42c1',
            'done': '#28a745',
            'blocked': '#dc3545',
            'cancelled': '#343a40',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def priority_badge(self, obj):
        colors = {
            'critical': '#dc3545',
            'high': '#fd7e14',
            'medium': '#ffc107',
            'low': '#28a745',
        }
        color = colors.get(obj.priority, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'


# =============================================================================
# LLM ASSIGNMENT ADMIN
# =============================================================================

@admin.register(WorkItemLLMAssignment)
class WorkItemLLMAssignmentAdmin(admin.ModelAdmin):
    """Admin for LLM Assignments"""
    
    list_display = [
        'work_item',
        'current_tier',
        'status',
        'llm_used',
        'attempts',
        'cost_display',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'current_tier',
        'initial_tier',
        'llm_used',
    ]
    
    search_fields = [
        'work_item__identifier',
        'work_item__title',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'started_at',
        'resolved_at',
        'attempt_history',
    ]
    
    def cost_display(self, obj):
        return f"${obj.cost_usd:.4f}"
    cost_display.short_description = 'Cost'


# =============================================================================
# COMMENT ADMIN
# =============================================================================

@admin.register(WorkItemComment)
class WorkItemCommentAdmin(admin.ModelAdmin):
    """Admin for Work Item Comments"""
    
    list_display = [
        'work_item',
        'comment_type',
        'author',
        'is_from_cascade',
        'content_short',
        'created_at',
    ]
    
    list_filter = [
        'comment_type',
        'is_from_cascade',
        'created_at',
    ]
    
    search_fields = [
        'work_item__identifier',
        'content',
    ]
    
    def content_short(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    content_short.short_description = 'Content'
