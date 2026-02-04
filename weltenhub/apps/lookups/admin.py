"""
Weltenhub Lookups Admin
"""

from django.contrib import admin
from .models import (
    Genre, Mood, ConflictLevel, LocationType,
    SceneType, CharacterRole, TransportType,
)


class BaseLookupAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active", "order"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]
    ordering = ["order", "name"]


@admin.register(Genre)
class GenreAdmin(BaseLookupAdmin):
    list_display = ["code", "name", "color", "is_active", "order"]


@admin.register(Mood)
class MoodAdmin(BaseLookupAdmin):
    list_display = ["code", "name", "intensity", "color", "is_active"]


@admin.register(ConflictLevel)
class ConflictLevelAdmin(BaseLookupAdmin):
    list_display = ["code", "name", "intensity", "color", "is_active"]


@admin.register(LocationType)
class LocationTypeAdmin(BaseLookupAdmin):
    list_display = ["code", "name", "parent_type", "icon", "is_active"]


@admin.register(SceneType)
class SceneTypeAdmin(BaseLookupAdmin):
    list_display = ["code", "name", "icon", "typical_duration_minutes"]


@admin.register(CharacterRole)
class CharacterRoleAdmin(BaseLookupAdmin):
    list_display = ["code", "name", "is_main", "color", "is_active"]


@admin.register(TransportType)
class TransportTypeAdmin(BaseLookupAdmin):
    list_display = ["code", "name", "icon", "is_active"]
