from django.contrib import admin
from ..models import Domain

from .work_item_admin import *


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['domain_id', 'name', 'category', 'version', 'is_active', 'created_at']
    list_filter = ['category', 'is_active']
    search_fields = ['domain_id', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['domain_id', 'name', 'description', 'category']
        }),
        ('Technical Details', {
            'fields': ['version', 'base_path', 'is_active']
        }),
        ('Dependencies', {
            'fields': ['dependencies']
        }),
        ('Metadata', {
            'fields': ['metadata'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
