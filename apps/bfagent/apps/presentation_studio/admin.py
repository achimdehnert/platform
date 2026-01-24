from django.contrib import admin
from .models import Presentation, Enhancement, TemplateCollection, PreviewSlide


@admin.register(Presentation)
class PresentationAdmin(admin.ModelAdmin):
    list_display = ['title', 'uploaded_by', 'enhancement_status', 'slide_count_original', 'slides_added', 'uploaded_at']
    list_filter = ['enhancement_status', 'uploaded_at']
    search_fields = ['title', 'description', 'uploaded_by__username']
    readonly_fields = ['uploaded_at', 'updated_at', 'id']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'description', 'uploaded_by')
        }),
        ('Files', {
            'fields': ('original_file', 'enhanced_file')
        }),
        ('Status & Statistics', {
            'fields': ('enhancement_status', 'slide_count_original', 'slide_count_enhanced')
        }),
        ('Enhancement Data', {
            'fields': ('concepts_added', 'enhancement_metadata')
        }),
        ('Templates', {
            'fields': ('template_collection', 'slide_templates'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('uploaded_at', 'updated_at')
        }),
    )


@admin.register(Enhancement)
class EnhancementAdmin(admin.ModelAdmin):
    list_display = ['presentation', 'enhancement_type', 'enhancement_mode', 'slides_added_count', 'success', 'executed_at']
    list_filter = ['enhancement_type', 'enhancement_mode', 'success', 'executed_at']
    search_fields = ['presentation__title']
    readonly_fields = ['executed_at', 'id', 'duration_seconds']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'presentation', 'enhancement_type', 'enhancement_mode')
        }),
        ('Configuration', {
            'fields': ('concepts', 'configuration')
        }),
        ('Results', {
            'fields': ('slides_before', 'slides_after', 'success', 'error_message', 'result_data')
        }),
        ('Execution', {
            'fields': ('executed_by', 'executed_at', 'duration_seconds')
        }),
    )


@admin.register(TemplateCollection)
class TemplateCollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'client', 'industry', 'template_count', 'presentation_count', 'usage_count', 'is_default', 'created_at']
    list_filter = ['industry', 'is_active', 'is_default', 'is_system', 'created_at']
    search_fields = ['name', 'client', 'project', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'usage_count', 'template_count', 'presentation_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'description')
        }),
        ('Organization', {
            'fields': ('client', 'project', 'industry')
        }),
        ('Template Configuration', {
            'fields': ('templates', 'master_pptx')
        }),
        ('Settings', {
            'fields': ('is_active', 'is_default', 'is_system')
        }),
        ('Statistics', {
            'fields': ('template_count', 'presentation_count', 'usage_count'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make is_system read-only if editing existing system template"""
        readonly = list(self.readonly_fields)
        if obj and obj.is_system:
            readonly.append('is_system')
        return readonly


@admin.register(PreviewSlide)
class PreviewSlideAdmin(admin.ModelAdmin):
    list_display = ['title', 'presentation', 'preview_order', 'status', 'source_type', 'created_at']
    list_filter = ['status', 'source_type', 'created_at']
    search_fields = ['title', 'presentation__title']
    readonly_fields = ['id', 'created_at', 'updated_at', 'converted_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'presentation', 'title', 'preview_order')
        }),
        ('Content', {
            'fields': ('content_data',)
        }),
        ('Status', {
            'fields': ('status', 'pptx_slide_number')
        }),
        ('Source', {
            'fields': ('source_type', 'source_file_name')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'converted_at'),
            'classes': ('collapse',)
        }),
    )
