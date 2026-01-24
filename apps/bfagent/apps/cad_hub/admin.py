# apps/cad_hub/admin.py
"""
Admin-Konfiguration für IFC Dashboard
"""
from django.contrib import admin

from .models import Door, Floor, IFCModel, IFCProject, Room, Slab, Wall, Window


@admin.register(IFCProject)
class IFCProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "model_count", "created_at", "updated_at"]
    search_fields = ["name"]
    list_filter = ["created_at", "created_by"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("name", "created_by")}),
        ("Metadaten", {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def model_count(self, obj):
        return obj.models.count()

    model_count.short_description = "Modelle"


@admin.register(IFCModel)
class IFCModelAdmin(admin.ModelAdmin):
    list_display = ["__str__", "ifc_schema", "status", "room_count", "uploaded_at"]
    list_filter = ["status", "ifc_schema", "project"]
    search_fields = ["project__name"]
    readonly_fields = ["id", "uploaded_at", "processed_at"]

    fieldsets = (
        (None, {"fields": ("project", "version", "status")}),
        ("Dateien", {"fields": ("ifc_file", "xkt_file")}),
        ("IFC Metadaten", {"fields": ("ifc_schema", "application")}),
        (
            "Status",
            {"fields": ("error_message", "uploaded_at", "processed_at"), "classes": ("collapse",)},
        ),
    )

    def room_count(self, obj):
        return obj.rooms.count()

    room_count.short_description = "Räume"


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "elevation", "room_count", "ifc_model"]
    list_filter = ["ifc_model__project", "ifc_model"]
    search_fields = ["name", "code"]
    ordering = ["ifc_model", "sort_order"]

    def room_count(self, obj):
        return obj.rooms.count()

    room_count.short_description = "Räume"


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["number", "name", "floor", "area", "height", "usage_category"]
    list_filter = ["usage_category", "floor", "ifc_model__project"]
    search_fields = ["number", "name", "long_name"]
    list_editable = ["usage_category"]

    fieldsets = (
        (None, {"fields": ("ifc_model", "floor", "ifc_guid")}),
        ("Stammdaten", {"fields": ("number", "name", "long_name")}),
        ("Geometrie", {"fields": ("area", "height", "volume", "perimeter")}),
        ("Klassifizierung", {"fields": ("usage_category",)}),
    )


@admin.register(Window)
class WindowAdmin(admin.ModelAdmin):
    list_display = ["number", "name", "floor", "width", "height", "area", "u_value"]
    list_filter = ["floor", "ifc_model__project"]
    search_fields = ["number", "name", "ifc_guid"]

    fieldsets = (
        (None, {"fields": ("ifc_model", "floor", "room", "ifc_guid")}),
        ("Stammdaten", {"fields": ("number", "name")}),
        ("Geometrie", {"fields": ("width", "height", "area", "wall_position", "elevation")}),
        ("Eigenschaften", {"fields": ("material", "glazing_type", "u_value")}),
        ("IFC Properties", {"fields": ("properties",), "classes": ("collapse",)}),
    )


@admin.register(Door)
class DoorAdmin(admin.ModelAdmin):
    list_display = ["number", "name", "floor", "door_type", "width", "height", "fire_rating"]
    list_filter = ["door_type", "fire_rating", "floor", "ifc_model__project"]
    search_fields = ["number", "name", "ifc_guid"]

    fieldsets = (
        (None, {"fields": ("ifc_model", "floor", "from_room", "to_room", "ifc_guid")}),
        ("Stammdaten", {"fields": ("number", "name", "door_type")}),
        ("Geometrie", {"fields": ("width", "height")}),
        ("Eigenschaften", {"fields": ("material", "fire_rating")}),
    )


@admin.register(Wall)
class WallAdmin(admin.ModelAdmin):
    list_display = ["name", "floor", "is_external", "length", "height", "gross_area", "net_area"]
    list_filter = ["is_external", "is_load_bearing", "floor", "ifc_model__project"]
    search_fields = ["name", "ifc_guid"]

    fieldsets = (
        (None, {"fields": ("ifc_model", "floor", "ifc_guid", "name")}),
        (
            "Geometrie",
            {"fields": ("length", "height", "width", "gross_area", "net_area", "volume")},
        ),
        ("Eigenschaften", {"fields": ("is_external", "is_load_bearing", "material")}),
    )


@admin.register(Slab)
class SlabAdmin(admin.ModelAdmin):
    list_display = ["name", "slab_type", "floor", "area", "thickness", "volume"]
    list_filter = ["slab_type", "floor", "ifc_model__project"]
    search_fields = ["name", "ifc_guid"]

    fieldsets = (
        (None, {"fields": ("ifc_model", "floor", "ifc_guid")}),
        ("Stammdaten", {"fields": ("name", "slab_type")}),
        ("Geometrie", {"fields": ("area", "thickness", "volume", "perimeter")}),
        ("Eigenschaften", {"fields": ("material",)}),
    )


# Import AVB Admin (Ausschreibung, Vergabe, Bauausführung)
from .admin_avb import *  # noqa

# Import Brandschutz Admin
from .admin_brandschutz import *  # noqa
