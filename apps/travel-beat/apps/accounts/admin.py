from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'display_name', 'subscription_tier', 'stories_generated', 'is_active']
    list_filter = ['subscription_tier', 'is_active', 'is_staff']
    search_fields = ['email', 'display_name', 'username']
    ordering = ['-created_at']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile', {
            'fields': ('display_name', 'avatar', 'reading_speed', 'preferred_genre'),
        }),
        ('Subscription', {
            'fields': ('subscription_tier', 'subscription_expires'),
        }),
        ('Stats', {
            'fields': ('stories_generated', 'total_words_read'),
        }),
    )
