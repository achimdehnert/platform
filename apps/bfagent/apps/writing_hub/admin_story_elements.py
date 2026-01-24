"""
Admin configuration for Story Elements
"""

from django.contrib import admin

from apps.writing_hub.models import (
    Beat,
    BeatType,
    ConflictLevel,
    EmotionalTone,
    Location,
    PlotThread,
    Scene,
    SceneConnection,
    SceneConnectionType,
    TimelineEvent,
)

# =============================================================================
# Lookup Tables (Master Data)
# =============================================================================


@admin.register(EmotionalTone)
class EmotionalToneAdmin(admin.ModelAdmin):
    list_display = ("name_en", "name_de", "code", "color", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name_en", "name_de", "code")
    ordering = ("order", "name_en")


@admin.register(ConflictLevel)
class ConflictLevelAdmin(admin.ModelAdmin):
    list_display = ("name_en", "name_de", "code", "intensity", "color", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name_en", "name_de", "code")
    ordering = ("order", "intensity")


@admin.register(BeatType)
class BeatTypeAdmin(admin.ModelAdmin):
    list_display = ("name_en", "name_de", "code", "icon", "color", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name_en", "name_de", "code")
    ordering = ("order", "name_en")


@admin.register(SceneConnectionType)
class SceneConnectionTypeAdmin(admin.ModelAdmin):
    list_display = ("name_en", "name_de", "code", "icon", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name_en", "name_de", "code")
    ordering = ("order", "name_en")


# =============================================================================
# Story Elements
# =============================================================================


class BeatInline(admin.TabularInline):
    model = Beat
    extra = 1
    fields = ("order", "beat_type", "description", "notes")
    ordering = ("order",)


@admin.register(Scene)
class SceneAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "chapter",
        "order",
        "pov_character",
        "conflict_level",
        "status",
        "word_count_actual",
        "word_count_target",
    )
    list_filter = ("status", "conflict_level", "emotional_start", "emotional_end", "chapter")
    search_fields = ("title", "summary", "notes")
    ordering = ("chapter", "order")

    fieldsets = (
        ("Basic Information", {"fields": ("title", "summary", "chapter", "order", "status")}),
        ("Characters & POV", {"fields": ("pov_character", "characters")}),
        (
            "Setting & Timeline",
            {"fields": ("location", "story_datetime", "story_date_description")},
        ),
        (
            "Plot & Emotional Arc",
            {"fields": ("plot_threads", ("emotional_start", "emotional_end"), "conflict_level")},
        ),
        (
            "Scene Method",
            {"fields": ("goal", "disaster"), "description": "Scene/Sequel method by Dwight Swain"},
        ),
        ("Word Counts", {"fields": (("word_count_target", "word_count_actual"),)}),
        ("Content", {"fields": ("content", "notes"), "classes": ("collapse",)}),
    )

    filter_horizontal = ("characters", "plot_threads")
    inlines = [BeatInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            "chapter",
            "pov_character",
            "location",
            "conflict_level",
            "status",
            "emotional_start",
            "emotional_end",
        ).prefetch_related("characters", "plot_threads")


@admin.register(Beat)
class BeatAdmin(admin.ModelAdmin):
    list_display = ("scene", "order", "beat_type", "description_preview")
    list_filter = ("beat_type", "scene__chapter")
    search_fields = ("description", "notes", "scene__title")
    ordering = ("scene", "order")

    def description_preview(self, obj):
        return obj.description[:100] + "..." if len(obj.description) > 100 else obj.description

    description_preview.short_description = "Description"


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "time_period", "mood")
    list_filter = ("project", "time_period")
    search_fields = ("name", "description", "mood")
    ordering = ("project", "name")


@admin.register(PlotThread)
class PlotThreadAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "thread_type", "status", "color")
    list_filter = ("project", "thread_type", "status")
    search_fields = ("name", "description", "resolution")
    ordering = ("project", "thread_type", "name")

    fieldsets = (
        ("Basic Information", {"fields": ("project", "name", "thread_type", "status")}),
        ("Details", {"fields": ("description", "resolution", "color")}),
    )


@admin.register(SceneConnection)
class SceneConnectionAdmin(admin.ModelAdmin):
    list_display = ("from_scene", "connection_type", "to_scene")
    list_filter = ("connection_type",)
    search_fields = ("description", "from_scene__title", "to_scene__title")
    ordering = ("from_scene", "to_scene")


@admin.register(TimelineEvent)
class TimelineEventAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "story_datetime",
        "story_date_description",
        "description_preview",
        "is_shown",
        "scene",
    )
    list_filter = ("project", "is_shown")
    search_fields = ("description", "story_date_description")
    ordering = ("project", "story_datetime")

    filter_horizontal = ("characters",)

    def description_preview(self, obj):
        return obj.description[:100] + "..." if len(obj.description) > 100 else obj.description

    description_preview.short_description = "Description"
