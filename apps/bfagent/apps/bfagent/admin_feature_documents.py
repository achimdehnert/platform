"""
Admin configuration for Feature Documentation System
"""

from django.contrib import admin
from django.utils.html import format_html
from .models_feature_documents import FeatureDocument, FeatureDocumentKeyword


class FeatureDocumentKeywordInline(admin.TabularInline):
    """Inline admin for feature document keywords"""
    model = FeatureDocumentKeyword
    extra = 1
    fields = ['keyword', 'keyword_type', 'weight']


@admin.register(FeatureDocument)
class FeatureDocumentAdmin(admin.ModelAdmin):
    """Admin interface for Feature Documents"""
    
    list_display = [
        'title',
        'feature_link',
        'doc_type_badge',
        'file_icon',
        'word_count',
        'is_auto_discovered',
        'discovered_at',
    ]
    
    list_filter = [
        'document_type',
        'is_auto_discovered',
        'discovered_at',
    ]
    
    search_fields = ['title', 'description', 'file_path', 'feature__name']
    
    readonly_fields = [
        'is_auto_discovered',
        'discovered_at',
        'file_size',
        'word_count',
        'last_modified',
        'file_extension',
        'is_markdown',
        'is_image',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('feature', 'title', 'document_type', 'description')
        }),
        ('File Information', {
            'fields': ('file_path', 'uploaded_file', 'file_size', 'word_count', 'file_extension')
        }),
        ('Discovery', {
            'fields': ('is_auto_discovered', 'discovered_at', 'last_modified'),
            'classes': ('collapse',)
        }),
        ('Display', {
            'fields': ('order', 'is_markdown', 'is_image'),
            'classes': ('collapse',)
        }),
    )
    
    def feature_link(self, obj):
        """Link to related feature"""
        if obj.feature:
            url = f'/admin/bfagent/componentregistry/{obj.feature.pk}/change/'
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.feature.name
            )
        return '-'
    feature_link.short_description = 'Feature'
    
    def doc_type_badge(self, obj):
        """Display document type with color"""
        colors = {
            'design': '#3498db',
            'architecture': '#9b59b6',
            'guide': '#2ecc71',
            'reference': '#95a5a6',
            'spec': '#e74c3c',
            'notes': '#f39c12',
            'diagram': '#1abc9c',
            'other': '#34495e',
        }
        color = colors.get(obj.document_type, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_document_type_display()
        )
    doc_type_badge.short_description = 'Type'
    
    def file_icon(self, obj):
        """Display file icon"""
        icons = {
            'md': '📝',
            'pdf': '📄',
            'txt': '📃',
            'docx': '📘',
            'png': '🖼️',
            'jpg': '🖼️',
            'svg': '🎨',
        }
        icon = icons.get(obj.file_extension, '📎')
        return f"{icon} {obj.file_extension or 'N/A'}"
    file_icon.short_description = 'File'


@admin.register(FeatureDocumentKeyword)
class FeatureDocumentKeywordAdmin(admin.ModelAdmin):
    """Admin interface for Feature Document Keywords"""
    
    list_display = [
        'feature_link',
        'keyword',
        'keyword_type',
        'weight',
    ]
    
    list_filter = [
        'keyword_type',
        'weight',
    ]
    
    search_fields = ['keyword', 'feature__name']
    
    def feature_link(self, obj):
        """Link to related feature"""
        if obj.feature:
            url = f'/admin/bfagent/componentregistry/{obj.feature.pk}/change/'
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.feature.name
            )
        return '-'
    feature_link.short_description = 'Feature'
