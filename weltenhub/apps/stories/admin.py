"""
Weltenhub Stories Admin
"""

from django.contrib import admin
from .models import Story, Chapter, PlotThread, TimelineEvent


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    fields = ["number", "title", "status", "actual_word_count"]


class PlotThreadInline(admin.TabularInline):
    model = PlotThread
    extra = 0
    fields = ["name", "thread_type", "status", "color"]


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = [
        "title", "world", "genre", "status",
        "actual_word_count", "is_public", "created_at"
    ]
    list_filter = ["status", "genre", "is_public", "world__tenant"]
    search_fields = ["title", "logline", "premise"]
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ["tenant", "world", "genre", "created_by", "updated_by"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ChapterInline, PlotThreadInline]


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = [
        "title", "story", "number", "status", "actual_word_count"
    ]
    list_filter = ["status"]
    search_fields = ["title", "story__title"]
    raw_id_fields = ["story"]


@admin.register(PlotThread)
class PlotThreadAdmin(admin.ModelAdmin):
    list_display = ["name", "story", "thread_type", "status", "color"]
    list_filter = ["thread_type", "status"]
    search_fields = ["name", "story__title"]
    raw_id_fields = ["story"]


@admin.register(TimelineEvent)
class TimelineEventAdmin(admin.ModelAdmin):
    list_display = [
        "story", "description", "story_datetime", "is_shown", "is_pivotal"
    ]
    list_filter = ["is_shown", "is_pivotal"]
    search_fields = ["description"]
    raw_id_fields = ["story", "scene", "location"]
