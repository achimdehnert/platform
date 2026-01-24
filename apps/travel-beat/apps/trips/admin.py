from django.contrib import admin
from .models import Trip, Stop, Transport


class StopInline(admin.TabularInline):
    model = Stop
    extra = 1
    fields = ['city', 'country', 'arrival_date', 'departure_date', 'accommodation_type', 'order']


class TransportInline(admin.TabularInline):
    model = Transport
    extra = 0
    fields = ['from_stop', 'to_stop', 'transport_type', 'duration_minutes']


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'trip_type', 'status', 'start_date', 'end_date', 'stops_count']
    list_filter = ['status', 'trip_type', 'created_at']
    search_fields = ['name', 'user__email', 'origin']
    date_hierarchy = 'start_date'
    inlines = [StopInline, TransportInline]
    
    readonly_fields = ['total_reading_minutes', 'recommended_chapters', 'recommended_words']
    
    fieldsets = [
        ('Basis', {
            'fields': ['user', 'name', 'trip_type', 'status'],
        }),
        ('Reisedaten', {
            'fields': ['origin', 'start_date', 'end_date'],
        }),
        ('Berechnet', {
            'fields': ['total_reading_minutes', 'recommended_chapters', 'recommended_words'],
            'classes': ['collapse'],
        }),
    ]


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ['city', 'country', 'trip', 'arrival_date', 'departure_date', 'nights']
    list_filter = ['country', 'accommodation_type']
    search_fields = ['city', 'country', 'trip__name']


@admin.register(Transport)
class TransportAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'trip', 'transport_type', 'duration_minutes', 'reading_minutes']
    list_filter = ['transport_type']
