from django.contrib import admin
from .models import Story, Chapter, ReadingProgress


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    fields = ['number', 'title', 'act', 'beat', 'status', 'word_count']
    readonly_fields = ['word_count']


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'genre', 'status', 'total_chapters', 'total_words', 'created_at']
    list_filter = ['status', 'genre', 'created_at']
    search_fields = ['title', 'user__email']
    inlines = [ChapterInline]
    
    readonly_fields = [
        'generation_started', 'generation_completed', 
        'total_chapters', 'total_words', 'tokens_used', 'generation_cost_usd'
    ]
    
    fieldsets = [
        ('Basis', {
            'fields': ['user', 'trip', 'user_world', 'title', 'genre'],
        }),
        ('Einstellungen', {
            'fields': ['spice_level', 'ending_type', 'triggers_avoid'],
        }),
        ('Status', {
            'fields': ['status', 'generation_started', 'generation_completed', 'generation_error'],
        }),
        ('Statistiken', {
            'fields': ['total_chapters', 'total_words', 'tokens_used', 'generation_cost_usd'],
        }),
    ]


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['story', 'number', 'title', 'act', 'beat', 'status', 'word_count']
    list_filter = ['status', 'act', 'pacing']
    search_fields = ['title', 'story__title']


@admin.register(ReadingProgress)
class ReadingProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'story', 'chapters_completed', 'progress_percent', 'last_read_at']
    list_filter = ['last_read_at']
