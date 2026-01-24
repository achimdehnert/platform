from django.contrib import admin
from .models import UserWorld, Character, PersonalPlace, LocationMemory


class CharacterInline(admin.TabularInline):
    model = Character
    extra = 0
    fields = ['name', 'role', 'gender', 'is_active']


class PersonalPlaceInline(admin.TabularInline):
    model = PersonalPlace
    extra = 0
    fields = ['name', 'city', 'country', 'place_type']


@admin.register(UserWorld)
class UserWorldAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'default_genre', 'created_at']
    search_fields = ['user__email', 'name']
    inlines = [CharacterInline, PersonalPlaceInline]


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ['name', 'user_world', 'role', 'gender', 'is_active']
    list_filter = ['role', 'is_active']
    search_fields = ['name', 'user_world__user__email']


@admin.register(PersonalPlace)
class PersonalPlaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'country', 'place_type', 'user_world']
    list_filter = ['place_type', 'country']
    search_fields = ['name', 'city']


@admin.register(LocationMemory)
class LocationMemoryAdmin(admin.ModelAdmin):
    list_display = ['base_location', 'story', 'emotional_significance', 'can_reference']
    list_filter = ['can_reference', 'emotional_significance']
