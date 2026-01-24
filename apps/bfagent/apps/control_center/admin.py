"""
Admin registration for Control Center models
"""
from django.contrib import admin

from .models_navigation import NavigationItem, NavigationSection, UserNavigationPreference


class NavigationItemInline(admin.TabularInline):
    model = NavigationItem
    extra = 0
    fields = ['code', 'name', 'url_name', 'icon', 'order', 'is_active']
    ordering = ['order', 'name']


@admin.register(NavigationSection)
class NavigationSectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'domain_id', 'order', 'is_collapsible', 'is_collapsed_default', 'is_active']
    list_filter = ['is_active', 'is_collapsible', 'domain_id']
    search_fields = ['name', 'code', 'description']
    ordering = ['order', 'name']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('code', 'name', 'description', 'domain_id', 'slug')
        }),
        ('Visual', {
            'fields': ('icon', 'color')
        }),
        ('Behavior', {
            'fields': ('order', 'is_active', 'is_collapsible', 'is_collapsed_default')
        }),
        ('Section Link (optional)', {
            'fields': ('url_name', 'external_url'),
            'classes': ('collapse',),
            'description': 'Configure a URL to make the section header clickable'
        }),
    )
    
    inlines = [NavigationItemInline]


@admin.register(NavigationItem)
class NavigationItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'section', 'url_name', 'icon', 'order', 'is_active']
    list_filter = ['is_active', 'section', 'item_type']
    search_fields = ['name', 'code', 'url_name', 'description']
    ordering = ['section__order', 'order', 'name']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('section', 'code', 'name', 'description', 'item_type')
        }),
        ('Navigation', {
            'fields': ('url_name', 'url_params', 'external_url', 'opens_in_new_tab')
        }),
        ('Visual', {
            'fields': ('icon', 'badge_text', 'badge_color')
        }),
        ('Ordering & Visibility', {
            'fields': ('order', 'is_active', 'parent')
        }),
    )


@admin.register(UserNavigationPreference)
class UserNavigationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'section', 'is_collapsed', 'is_hidden']
    list_filter = ['is_collapsed', 'is_hidden']
    search_fields = ['user__username', 'section__name']
