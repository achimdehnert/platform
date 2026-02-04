"""
Weltenhub Scenes Admin
"""

from django.contrib import admin
from .models import SceneTemplate, Scene, SceneBeat, SceneConnection


@admin.register(SceneTemplate)
class SceneTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "scene_type", "is_public", "created_at"]
    list_filter = ["scene_type", "is_public"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}


class SceneBeatInline(admin.TabularInline):
    model = SceneBeat
    extra = 0
    fields = ["beat_type", "description", "order"]


@admin.register(Scene)
class SceneAdmin(admin.ModelAdmin):
    list_display = [
        "title", "story", "chapter", "template", "order", "status"
    ]
    list_filter = ["status", "template__scene_type", "story__tenant"]
    search_fields = ["title", "summary"]
    raw_id_fields = [
        "tenant", "story", "chapter", "template",
        "location", "pov_character", "mood", "conflict_level"
    ]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [SceneBeatInline]


@admin.register(SceneBeat)
class SceneBeatAdmin(admin.ModelAdmin):
    list_display = ["scene", "beat_type", "order"]
    list_filter = ["beat_type"]
    search_fields = ["description"]
    raw_id_fields = ["scene"]


@admin.register(SceneConnection)
class SceneConnectionAdmin(admin.ModelAdmin):
    list_display = [
        "from_scene", "to_scene", "connection_type"
    ]
    list_filter = ["connection_type"]
    raw_id_fields = ["from_scene", "to_scene"]
