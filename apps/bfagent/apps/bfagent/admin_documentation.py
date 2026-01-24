"""
Admin Interface für das Dokumentations-System.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models_documentation import (
    SystemDocumentation,
    DomainDocumentation,
    ChangelogEntry,
    GlossaryTerm,
    DocumentationLink,
)


@admin.register(SystemDocumentation)
class SystemDocumentationAdmin(admin.ModelAdmin):
    list_display = ['title', 'doc_type', 'version', 'is_current', 'updated_at']
    list_filter = ['doc_type', 'is_current']
    search_fields = ['title', 'summary', 'content']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'doc_type', 'summary')
        }),
        ('Inhalt', {
            'fields': ('content',),
            'classes': ('wide',)
        }),
        ('Versionierung', {
            'fields': ('version', 'is_current', 'previous_version')
        }),
        ('Metadaten', {
            'fields': ('source_file', 'created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DomainDocumentation)
class DomainDocumentationAdmin(admin.ModelAdmin):
    list_display = ['domain', 'section', 'title', 'is_published', 'updated_at']
    list_filter = ['domain', 'section', 'is_published']
    search_fields = ['title', 'content']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['domain', 'order', 'section']


@admin.register(ChangelogEntry)
class ChangelogEntryAdmin(admin.ModelAdmin):
    list_display = ['change_type_badge', 'title', 'domain', 'version', 'is_public', 'created_at']
    list_filter = ['change_type', 'domain', 'is_public', 'is_breaking']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def change_type_badge(self, obj):
        colors = {
            'feature': '#28a745',
            'bugfix': '#dc3545',
            'enhancement': '#17a2b8',
            'breaking': '#ffc107',
            'security': '#6f42c1',
            'performance': '#fd7e14',
            'docs': '#20c997',
            'refactor': '#6c757d',
            'deprecation': '#e83e8c',
        }
        color = colors.get(obj.change_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color,
            obj.get_change_type_display()
        )
    change_type_badge.short_description = 'Typ'


@admin.register(GlossaryTerm)
class GlossaryTermAdmin(admin.ModelAdmin):
    list_display = ['term', 'category', 'domains_list', 'updated_at']
    list_filter = ['category', 'domains']
    search_fields = ['term', 'definition', 'examples']
    prepopulated_fields = {'slug': ('term',)}
    filter_horizontal = ['related_terms', 'domains']
    
    def domains_list(self, obj):
        return ", ".join([d.display_name for d in obj.domains.all()[:3]])
    domains_list.short_description = 'Domains'


@admin.register(DocumentationLink)
class DocumentationLinkAdmin(admin.ModelAdmin):
    list_display = ['requirement', 'linked_doc', 'link_type', 'created_at']
    list_filter = ['link_type']
    search_fields = ['requirement__name', 'notes']
    autocomplete_fields = ['requirement', 'system_doc', 'domain_doc']
    
    def linked_doc(self, obj):
        if obj.system_doc:
            return f"📄 {obj.system_doc.title}"
        elif obj.domain_doc:
            return f"🏠 {obj.domain_doc.title}"
        elif obj.external_file:
            return f"📁 {obj.external_file}"
        return "-"
    linked_doc.short_description = 'Dokumentation'
