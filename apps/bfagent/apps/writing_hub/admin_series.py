"""
Django Admin Configuration for Book Series
===========================================

Provides admin interface for managing:
- BookSeries (Buchreihen)
- SharedCharacter (Gemeinsame Charaktere)
- SharedWorld (Gemeinsame Welten)
- ProjectCharacterLink / ProjectWorldLink (Verknüpfungen)
"""

from django.contrib import admin
from django.utils.html import format_html

from .models_series import (
    BookSeries,
    SharedCharacter,
    SharedWorld,
    ProjectCharacterLink,
    ProjectWorldLink,
)


# =============================================================================
# INLINE ADMINS
# =============================================================================

class SharedCharacterInline(admin.TabularInline):
    """Inline für Charaktere innerhalb einer Serie"""
    model = SharedCharacter
    extra = 0
    fields = ['name', 'role', 'age_at_series_start', 'description']
    show_change_link = True


class SharedWorldInline(admin.TabularInline):
    """Inline für Welten innerhalb einer Serie"""
    model = SharedWorld
    extra = 0
    fields = ['name', 'world_type', 'description']
    show_change_link = True


class ProjectCharacterLinkInline(admin.TabularInline):
    """Inline für Charakter-Verknüpfungen"""
    model = ProjectCharacterLink
    extra = 0
    fields = ['shared_character', 'age_in_book', 'role_in_book', 'is_active']
    autocomplete_fields = ['shared_character']


class ProjectWorldLinkInline(admin.TabularInline):
    """Inline für Welt-Verknüpfungen"""
    model = ProjectWorldLink
    extra = 0
    fields = ['shared_world', 'relevance', 'time_period', 'is_active']
    autocomplete_fields = ['shared_world']


# =============================================================================
# BOOK SERIES ADMIN
# =============================================================================

@admin.register(BookSeries)
class BookSeriesAdmin(admin.ModelAdmin):
    """Admin für Buchreihen/Universes"""
    
    list_display = [
        'name',
        'genre',
        'projects_count_display',
        'characters_count_display',
        'worlds_count_display',
        'created_by',
        'is_active',
        'created_at',
    ]
    
    list_filter = ['is_active', 'genre', 'created_at']
    search_fields = ['name', 'description', 'genre']
    
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Grundinformationen', {
            'fields': ('name', 'description', 'genre', 'cover_image')
        }),
        ('Einheitliche Stile', {
            'fields': ('illustration_style_template', 'writing_style'),
            'description': 'Optionale einheitliche Stile für alle Bücher der Reihe'
        }),
        ('Verwaltung', {
            'fields': ('created_by', 'is_active'),
        }),
        ('Metadaten', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [SharedCharacterInline, SharedWorldInline]
    
    autocomplete_fields = ['created_by']
    raw_id_fields = ['illustration_style_template', 'writing_style']
    
    def projects_count_display(self, obj):
        count = obj.projects_count
        return format_html(
            '<span style="color: {};">{} Bücher</span>',
            '#28a745' if count > 0 else '#6c757d',
            count
        )
    projects_count_display.short_description = 'Bücher'
    
    def characters_count_display(self, obj):
        count = obj.characters_count
        return format_html(
            '<span style="color: {};">{} Charaktere</span>',
            '#007bff' if count > 0 else '#6c757d',
            count
        )
    characters_count_display.short_description = 'Charaktere'
    
    def worlds_count_display(self, obj):
        count = obj.worlds_count
        return format_html(
            '<span style="color: {};">{} Welten</span>',
            '#17a2b8' if count > 0 else '#6c757d',
            count
        )
    worlds_count_display.short_description = 'Welten'
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# =============================================================================
# SHARED CHARACTER ADMIN
# =============================================================================

@admin.register(SharedCharacter)
class SharedCharacterAdmin(admin.ModelAdmin):
    """Admin für gemeinsame Charaktere"""
    
    list_display = [
        'name',
        'series',
        'role',
        'age_at_series_start',
        'projects_using_count',
        'updated_at',
    ]
    
    list_filter = ['role', 'series']
    search_fields = ['name', 'description', 'background', 'personality']
    
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Grundinformationen', {
            'fields': ('series', 'name', 'role', 'age_at_series_start', 'portrait_image')
        }),
        ('Beschreibung', {
            'fields': ('description', 'appearance', 'personality')
        }),
        ('Hintergrund', {
            'fields': ('background', 'motivation', 'arc'),
            'classes': ('collapse',)
        }),
        ('Metadaten', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    autocomplete_fields = ['series']
    
    def projects_using_count(self, obj):
        count = obj.project_links.filter(is_active=True).count()
        return f"{count} Projekte"
    projects_using_count.short_description = 'Verwendet in'


# =============================================================================
# SHARED WORLD ADMIN
# =============================================================================

@admin.register(SharedWorld)
class SharedWorldAdmin(admin.ModelAdmin):
    """Admin für gemeinsame Welten"""
    
    list_display = [
        'name',
        'series',
        'world_type',
        'projects_using_count',
        'updated_at',
    ]
    
    list_filter = ['world_type', 'series']
    search_fields = ['name', 'description', 'geography', 'culture']
    
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Grundinformationen', {
            'fields': ('series', 'name', 'world_type', 'preview_image')
        }),
        ('Beschreibung', {
            'fields': ('description', 'geography', 'culture')
        }),
        ('Worldbuilding', {
            'fields': ('technology_level', 'magic_system', 'politics', 'history'),
            'classes': ('collapse',)
        }),
        ('Metadaten', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    autocomplete_fields = ['series']
    
    def projects_using_count(self, obj):
        count = obj.project_links.filter(is_active=True).count()
        return f"{count} Projekte"
    projects_using_count.short_description = 'Verwendet in'


# =============================================================================
# PROJECT LINK ADMINS
# =============================================================================

@admin.register(ProjectCharacterLink)
class ProjectCharacterLinkAdmin(admin.ModelAdmin):
    """Admin für Projekt-Charakter-Verknüpfungen"""
    
    list_display = [
        'shared_character',
        'project',
        'role_in_book',
        'age_in_book',
        'is_active',
    ]
    
    list_filter = ['is_active', 'project__series']
    search_fields = ['shared_character__name', 'project__title']
    
    autocomplete_fields = ['project', 'shared_character']


@admin.register(ProjectWorldLink)
class ProjectWorldLinkAdmin(admin.ModelAdmin):
    """Admin für Projekt-Welt-Verknüpfungen"""
    
    list_display = [
        'shared_world',
        'project',
        'relevance',
        'time_period',
        'is_active',
    ]
    
    list_filter = ['is_active', 'relevance', 'project__series']
    search_fields = ['shared_world__name', 'project__title']
    
    autocomplete_fields = ['project', 'shared_world']
