"""
Media Hub Admin
===============

Admin interfaces for media production models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from .models import (
    StylePreset,
    FormatPreset,
    QualityPreset,
    VoicePreset,
    WorkflowDefinition,
    WorkflowBinding,
    RenderJob,
    RenderAttempt,
    Asset,
    AssetFile,
    ParameterMapping,
)


# =============================================================================
# PRESET ADMINS
# =============================================================================

@admin.register(StylePreset)
class StylePresetAdmin(admin.ModelAdmin):
    list_display = ['key', 'name', 'category', 'is_approved', 'is_active', 'version', 'updated_at']
    list_filter = ['category', 'is_approved', 'is_active']
    search_fields = ['key', 'name', 'description', 'prompt_style']
    readonly_fields = ['version', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('key', 'name', 'description', 'category')
        }),
        ('Prompts', {
            'fields': ('prompt_style', 'prompt_negative')
        }),
        ('Defaults', {
            'fields': ('defaults', 'color_palette', 'reference_image')
        }),
        ('Status', {
            'fields': ('is_approved', 'is_active', 'version')
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FormatPreset)
class FormatPresetAdmin(admin.ModelAdmin):
    list_display = ['key', 'name', 'use_case', 'resolution_display', 'is_approved', 'is_active']
    list_filter = ['use_case', 'is_approved', 'is_active']
    search_fields = ['key', 'name']
    readonly_fields = ['version', 'created_at', 'updated_at']
    
    @admin.display(description='Resolution')
    def resolution_display(self, obj):
        return f"{obj.width}x{obj.height}"


@admin.register(QualityPreset)
class QualityPresetAdmin(admin.ModelAdmin):
    list_display = ['key', 'name', 'is_approved', 'is_active', 'estimated_time_seconds', 'estimated_cost']
    list_filter = ['is_approved', 'is_active']
    search_fields = ['key', 'name']
    readonly_fields = ['version', 'created_at', 'updated_at']


@admin.register(VoicePreset)
class VoicePresetAdmin(admin.ModelAdmin):
    list_display = ['key', 'name', 'engine', 'language', 'gender', 'is_approved', 'is_active']
    list_filter = ['engine', 'language', 'gender', 'is_approved', 'is_active']
    search_fields = ['key', 'name', 'voice_id']
    readonly_fields = ['version', 'created_at', 'updated_at']


# =============================================================================
# WORKFLOW ADMINS
# =============================================================================

@admin.register(WorkflowDefinition)
class WorkflowDefinitionAdmin(admin.ModelAdmin):
    list_display = ['key', 'version', 'engine', 'is_active', 'sha256_short', 'created_at']
    list_filter = ['engine', 'is_active']
    search_fields = ['key', 'description']
    readonly_fields = ['sha256', 'created_at']
    
    @admin.display(description='SHA256')
    def sha256_short(self, obj):
        return obj.sha256[:12] + '...' if obj.sha256 else '-'


@admin.register(WorkflowBinding)
class WorkflowBindingAdmin(admin.ModelAdmin):
    list_display = ['job_type', 'workflow', 'is_active', 'created_at']
    list_filter = ['job_type', 'is_active']
    autocomplete_fields = ['workflow', 'default_style_preset', 'default_format_preset', 'default_quality_preset']


# =============================================================================
# RENDER JOB ADMINS
# =============================================================================

# RenderJob, RenderAttempt, Asset, AssetFile - simplified admin (fields don't match model yet)
@admin.register(RenderJob)
class RenderJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'job_type', 'status', 'created_at']
    list_filter = ['status', 'job_type']


@admin.register(RenderAttempt)
class RenderAttemptAdmin(admin.ModelAdmin):
    list_display = ['id', 'job', 'attempt_no', 'status', 'started_at']
    list_filter = ['status']


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['id', 'asset_type', 'is_approved', 'created_at']
    list_filter = ['asset_type', 'is_approved']


@admin.register(AssetFile)
class AssetFileAdmin(admin.ModelAdmin):
    list_display = ['id', 'asset', 'mime_type', 'created_at']
    list_filter = ['mime_type']


# =============================================================================
# PARAMETER MAPPING ADMIN
# =============================================================================

@admin.register(ParameterMapping)
class ParameterMappingAdmin(admin.ModelAdmin):
    list_display = ['job_type', 'source_field', 'target_field', 'transform', 'is_required', 'order']
    list_filter = ['job_type', 'transform', 'is_required']
    search_fields = ['source_field', 'target_field']
    ordering = ['job_type', 'order']
