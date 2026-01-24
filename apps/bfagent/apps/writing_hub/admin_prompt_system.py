"""
Prompt System Admin Configuration
=================================

Admin interfaces for managing image prompt components.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models_prompt_system import (
    PromptMasterStyle,
    PromptCharacter,
    PromptLocation,
    PromptCulturalElement,
    PromptSceneTemplate,
    PromptGenerationLog,
)


@admin.register(PromptMasterStyle)
class PromptMasterStyleAdmin(admin.ModelAdmin):
    """Admin for master styles."""
    
    list_display = [
        'name', 'project', 'preset', 'dimensions_display',
        'guidance_scale', 'inference_steps', 'updated_at'
    ]
    list_filter = ['preset', 'use_fixed_seed']
    search_fields = ['name', 'project__title']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Projekt', {
            'fields': ('project', 'name', 'preset')
        }),
        ('Stil-Prompts', {
            'fields': (
                'style_base_prompt',
                'style_modifiers',
                'negative_prompt',
            )
        }),
        ('Kultureller Kontext', {
            'fields': (
                'cultural_context',
                'artistic_references',
            ),
            'classes': ('collapse',)
        }),
        ('Technische Einstellungen', {
            'fields': (
                ('default_width', 'default_height'),
                ('guidance_scale', 'inference_steps'),
                ('use_fixed_seed', 'fixed_seed'),
            )
        }),
        ('Metadaten', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def dimensions_display(self, obj):
        return f"{obj.default_width}×{obj.default_height}"
    dimensions_display.short_description = 'Dimensionen'


@admin.register(PromptCharacter)
class PromptCharacterAdmin(admin.ModelAdmin):
    """Admin for character prompts."""
    
    list_display = [
        'name', 'project', 'role', 'book_character_link',
        'is_active', 'sort_order'
    ]
    list_filter = ['role', 'is_active', 'project']
    search_fields = ['name', 'project__title', 'appearance_prompt']
    list_editable = ['sort_order', 'is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basis', {
            'fields': ('project', 'book_character', 'name', 'role')
        }),
        ('Visuelles', {
            'fields': (
                'appearance_prompt',
                'clothing_prompt',
                'props_prompt',
                'expression_default',
            )
        }),
        ('Alters-Varianten', {
            'fields': (
                'age_child_prompt',
                'age_elder_prompt',
            ),
            'classes': ('collapse',)
        }),
        ('Konsistenz', {
            'fields': ('reference_seed',),
            'classes': ('collapse',)
        }),
        ('Sortierung', {
            'fields': ('sort_order', 'is_active')
        }),
    )
    
    def book_character_link(self, obj):
        if obj.book_character:
            return format_html(
                '<a href="/admin/bfagent/characters/{}/change/">{}</a>',
                obj.book_character.id,
                obj.book_character.name
            )
        return '-'
    book_character_link.short_description = 'Story-Charakter'


@admin.register(PromptLocation)
class PromptLocationAdmin(admin.ModelAdmin):
    """Admin for location prompts."""
    
    list_display = [
        'name', 'project', 'location_type', 'is_active', 'sort_order'
    ]
    list_filter = ['location_type', 'is_active', 'project']
    search_fields = ['name', 'project__title', 'environment_prompt']
    list_editable = ['sort_order', 'is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basis', {
            'fields': ('project', 'name', 'location_type')
        }),
        ('Umgebung', {
            'fields': (
                'environment_prompt',
                'architecture_prompt',
                'nature_prompt',
            )
        }),
        ('Beleuchtung', {
            'fields': (
                'lighting_default',
                'lighting_dawn',
                'lighting_night',
            ),
            'classes': ('collapse',)
        }),
        ('Atmosphäre', {
            'fields': (
                'atmosphere_prompt',
                'weather_default',
            )
        }),
        ('Sortierung', {
            'fields': ('sort_order', 'is_active')
        }),
    )


@admin.register(PromptCulturalElement)
class PromptCulturalElementAdmin(admin.ModelAdmin):
    """Admin for cultural glossary."""
    
    list_display = [
        'term_local', 'term_english', 'term_german',
        'category', 'project', 'is_active'
    ]
    list_filter = ['category', 'is_active', 'project']
    search_fields = ['term_local', 'term_english', 'term_german', 'description']
    list_editable = ['is_active']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Projekt', {
            'fields': ('project',)
        }),
        ('Begriffe', {
            'fields': (
                'term_local',
                'term_english',
                'term_german',
                'category',
            )
        }),
        ('Beschreibung', {
            'fields': (
                'description',
                'visual_prompt',
                'usage_context',
            )
        }),
        ('Sortierung', {
            'fields': ('sort_order', 'is_active')
        }),
    )


@admin.register(PromptSceneTemplate)
class PromptSceneTemplateAdmin(admin.ModelAdmin):
    """Admin for scene templates."""
    
    list_display = [
        'name', 'project', 'scene_type', 'recommended_aspect_ratio',
        'is_active', 'sort_order'
    ]
    list_filter = ['scene_type', 'recommended_aspect_ratio', 'is_active', 'project']
    search_fields = ['name', 'project__title', 'template_prompt']
    list_editable = ['sort_order', 'is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basis', {
            'fields': ('project', 'name', 'scene_type')
        }),
        ('Template', {
            'fields': (
                'template_prompt',
                'composition_hints',
            ),
            'description': 'Platzhalter: {character}, {location}, {action}, {emotion}'
        }),
        ('Format', {
            'fields': ('recommended_aspect_ratio',)
        }),
        ('Technische Überschreibungen', {
            'fields': (
                'override_steps',
                'override_guidance',
            ),
            'classes': ('collapse',)
        }),
        ('Sortierung', {
            'fields': ('sort_order', 'is_active')
        }),
    )


@admin.register(PromptGenerationLog)
class PromptGenerationLogAdmin(admin.ModelAdmin):
    """Admin for generation logs (read-only analysis)."""
    
    list_display = [
        'created_at', 'project', 'status_icon', 'chapter',
        'generation_time_display', 'user_rating', 'dimensions_display'
    ]
    list_filter = [
        'generation_successful', 'user_rating', 'project',
        ('created_at', admin.DateFieldListFilter)
    ]
    search_fields = ['scene_description', 'final_prompt', 'project__title']
    readonly_fields = [
        'project', 'chapter', 'illustration', 'master_style',
        'scene_description', 'final_prompt', 'negative_prompt',
        'width', 'height', 'steps', 'guidance_scale', 'seed_used',
        'generation_successful', 'generation_time_seconds', 'error_message',
        'created_at'
    ]
    filter_horizontal = ['characters_used']
    
    fieldsets = (
        ('Kontext', {
            'fields': ('project', 'chapter', 'illustration', 'master_style')
        }),
        ('Verwendete Komponenten', {
            'fields': ('characters_used', 'location_used', 'template_used')
        }),
        ('Prompts', {
            'fields': (
                'scene_description',
                'final_prompt',
                'negative_prompt',
            )
        }),
        ('Technische Parameter', {
            'fields': (
                ('width', 'height'),
                ('steps', 'guidance_scale'),
                'seed_used',
            )
        }),
        ('Ergebnis', {
            'fields': (
                'generation_successful',
                'generation_time_seconds',
                'error_message',
            )
        }),
        ('Benutzer-Feedback', {
            'fields': ('user_rating', 'user_notes')
        }),
        ('Metadaten', {
            'fields': ('created_at',)
        }),
    )
    
    def status_icon(self, obj):
        if obj.generation_successful:
            return format_html('<span style="color: green;">✅</span>')
        return format_html('<span style="color: red;">❌</span>')
    status_icon.short_description = 'Status'
    
    def generation_time_display(self, obj):
        if obj.generation_time_seconds:
            return f"{obj.generation_time_seconds:.1f}s"
        return '-'
    generation_time_display.short_description = 'Zeit'
    
    def dimensions_display(self, obj):
        return f"{obj.width}×{obj.height}"
    dimensions_display.short_description = 'Dim.'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        # Only allow editing user feedback fields
        return True
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
