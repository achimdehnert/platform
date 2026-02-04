"""
Weltenhub Worlds Admin
"""

from django.contrib import admin
from .models import World, WorldRule


class WorldRuleInline(admin.TabularInline):
    model = WorldRule
    extra = 0
    fields = ["category", "rule", "importance"]


@admin.register(World)
class WorldAdmin(admin.ModelAdmin):
    list_display = [
        "name", "tenant", "genre", "is_public", "is_template", "created_at"
    ]
    list_filter = ["is_public", "is_template", "genre", "tenant"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ["tenant", "genre", "created_by", "updated_by"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [WorldRuleInline]


@admin.register(WorldRule)
class WorldRuleAdmin(admin.ModelAdmin):
    list_display = ["world", "category", "rule", "importance"]
    list_filter = ["category", "importance"]
    search_fields = ["rule", "world__name"]
    raw_id_fields = ["world"]
