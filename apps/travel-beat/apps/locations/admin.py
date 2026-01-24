from django.contrib import admin
from .models import BaseLocation, LocationLayer, ResearchCache


class LocationLayerInline(admin.TabularInline):
    model = LocationLayer
    extra = 0
    fields = ['genre', 'atmosphere', 'generated_at']
    readonly_fields = ['generated_at']


@admin.register(BaseLocation)
class BaseLocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'location_type', 'primary_language', 'generated_at']
    list_filter = ['location_type', 'country', 'primary_language']
    search_fields = ['name', 'country', 'region']
    inlines = [LocationLayerInline]
    
    fieldsets = [
        ('Identifikation', {
            'fields': ['name', 'name_local', 'location_type'],
        }),
        ('Geografie', {
            'fields': ['country', 'country_code', 'region', 'latitude', 'longitude'],
        }),
        ('Kultur', {
            'fields': ['primary_language', 'languages', 'currency'],
        }),
        ('Beschreibung', {
            'fields': ['description', 'notable_features', 'districts'],
        }),
        ('Klima', {
            'fields': ['climate_type', 'best_seasons'],
        }),
        ('Meta', {
            'fields': ['generation_model', 'generated_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]
    readonly_fields = ['generated_at', 'updated_at']


@admin.register(LocationLayer)
class LocationLayerAdmin(admin.ModelAdmin):
    list_display = ['base_location', 'genre', 'generated_at']
    list_filter = ['genre']
    search_fields = ['base_location__name']


@admin.register(ResearchCache)
class ResearchCacheAdmin(admin.ModelAdmin):
    list_display = ['cache_key', 'created_at', 'expires_at', 'hit_count', 'is_valid']
    list_filter = ['created_at']
    search_fields = ['cache_key']
    readonly_fields = ['cache_key', 'data', 'created_at', 'hit_count', 'last_hit']
