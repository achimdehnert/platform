"""
Weltenhub Characters Admin
"""

from django.contrib import admin
from .models import Character, CharacterArc, CharacterRelationship


class CharacterArcInline(admin.TabularInline):
    model = CharacterArc
    extra = 0
    fields = ["arc_type", "starting_state", "ending_state"]


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = [
        "name", "world", "role", "age", "is_protagonist", "created_at"
    ]
    list_filter = ["role", "is_protagonist", "world__tenant"]
    search_fields = ["name", "nickname"]
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = [
        "tenant", "world", "role",
        "home_location", "current_location"
    ]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [CharacterArcInline]


@admin.register(CharacterArc)
class CharacterArcAdmin(admin.ModelAdmin):
    list_display = ["character", "arc_type", "story"]
    list_filter = ["arc_type"]
    search_fields = ["character__name"]
    raw_id_fields = ["character"]


@admin.register(CharacterRelationship)
class CharacterRelationshipAdmin(admin.ModelAdmin):
    list_display = [
        "character_a", "character_b",
        "relationship_type", "strength", "is_mutual"
    ]
    list_filter = ["relationship_type", "is_mutual"]
    search_fields = [
        "character_a__name", "character_b__name"
    ]
    raw_id_fields = ["character_a", "character_b"]
