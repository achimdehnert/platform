"""
Weltenhub Locations Admin
"""

from django.contrib import admin
from .models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = [
        "name", "world", "parent", "location_type", "created_at"
    ]
    list_filter = ["location_type", "world__tenant"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ["tenant", "world", "parent", "location_type"]
    readonly_fields = ["created_at", "updated_at"]
