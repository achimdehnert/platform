"""Admin für Expert Hub Models."""

from django.contrib import admin
from .models import ExAnalysisSession, ExZoneResult, ExEquipmentCheck, ExSubstance


@admin.register(ExAnalysisSession)
class ExAnalysisSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'project_name', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'project_name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(ExZoneResult)
class ExZoneResultAdmin(admin.ModelAdmin):
    list_display = ['room_name', 'zone_type', 'zone_category', 'risk_level', 'session', 'created_at']
    list_filter = ['zone_type', 'zone_category', 'risk_level']
    search_fields = ['room_name', 'justification']
    readonly_fields = ['id', 'created_at']


@admin.register(ExEquipmentCheck)
class ExEquipmentCheckAdmin(admin.ModelAdmin):
    list_display = ['equipment_name', 'ex_marking', 'target_zone', 'is_suitable', 'session', 'created_at']
    list_filter = ['is_suitable', 'target_zone']
    search_fields = ['equipment_name', 'ex_marking']
    readonly_fields = ['id', 'created_at']


@admin.register(ExSubstance)
class ExSubstanceAdmin(admin.ModelAdmin):
    list_display = ['name', 'cas_number', 'lower_explosion_limit', 'upper_explosion_limit', 
                    'temperature_class', 'explosion_group']
    list_filter = ['temperature_class', 'explosion_group', 'data_source']
    search_fields = ['name', 'name_en', 'cas_number']
    readonly_fields = ['created_at', 'updated_at']
