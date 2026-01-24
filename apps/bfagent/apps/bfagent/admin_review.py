"""
Django Admin configuration for Review System
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from .models import (
    ReviewRound,
    ReviewParticipant,
    Comment,
    ChapterRating,
)


class ReviewParticipantInline(admin.TabularInline):
    """Inline admin for Review Participants"""
    model = ReviewParticipant
    extra = 1
    fields = ['user', 'role', 'can_comment', 'can_rate', 'status', 'comments_count', 'ratings_count']
    readonly_fields = ['comments_count', 'ratings_count', 'joined_at', 'last_activity_at']


class CommentInline(admin.TabularInline):
    """Inline admin for Comments"""
    model = Comment
    extra = 0
    fields = ['chapter', 'author', 'text', 'comment_type', 'status']
    readonly_fields = ['author', 'created_at']
    can_delete = False


@admin.register(ReviewRound)
class ReviewRoundAdmin(admin.ModelAdmin):
    """Admin interface for Review Rounds"""

    list_display = [
        'title',
        'project_link',
        'status',
        'created_by',
        'participants_count',
        'comments_count',
        'ratings_count',
        'progress_bar',
        'start_date',
        'created_at',
    ]

    list_filter = [
        'status',
        'allow_comments',
        'allow_ratings',
        'created_at',
    ]

    search_fields = [
        'title',
        'description',
        'project__title',
        'created_by__username',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'total_comments',
        'unread_comments',
        'total_participants',
        'total_ratings',
        'average_rating',
        'progress_display',
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': ('project', 'title', 'description', 'created_by')
        }),
        ('Status & Timeline', {
            'fields': ('status', 'start_date', 'end_date', 'completed_at')
        }),
        ('Settings', {
            'fields': (
                'allow_comments',
                'allow_ratings',
                'comments_visible_to_others',
            )
        }),
        ('Statistics', {
            'fields': (
                'total_comments',
                'unread_comments',
                'total_participants',
                'total_ratings',
                'average_rating',
                'progress_display',
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [ReviewParticipantInline]

    def project_link(self, obj):
        """Link to project"""
        if obj.project:
            url = reverse('admin:bfagent_bookprojects_change', args=[obj.project.pk])
            return format_html('<a href="{}">{}</a>', url, obj.project.title)
        return '-'
    project_link.short_description = 'Project'

    def participants_count(self, obj):
        """Show participant count"""
        count = obj.total_participants
        if count > 0:
            return format_html('<span style="color: green;">✓ {}</span>', count)
        return format_html('<span style="color: gray;">0</span>')
    participants_count.short_description = 'Participants'

    def comments_count(self, obj):
        """Show comments count with unread indicator"""
        total = obj.total_comments
        unread = obj.unread_comments
        if unread > 0:
            return format_html(
                '<strong>{}</strong> <span style="color: red;">({})</span>',
                total,
                unread
            )
        return str(total)
    comments_count.short_description = 'Comments'

    def ratings_count(self, obj):
        """Show ratings count with average"""
        count = obj.total_ratings
        avg = obj.average_rating
        if avg:
            stars = '★' * int(avg) + '☆' * (5 - int(avg))
            return format_html('{} {} ({:.1f})', count, stars, avg)
        return str(count)
    ratings_count.short_description = 'Ratings'

    def progress_bar(self, obj):
        """Visual progress bar"""
        progress = obj.get_progress()
        if progress == 0:
            color = 'gray'
        elif progress < 50:
            color = 'orange'
        else:
            color = 'green'

        return format_html(
            '<div style="width:100px; background-color: #f0f0f0; '
            'border-radius: 3px; overflow: hidden;">'
            '<div style="width:{}%; background-color: {}; height: 20px; '
            'text-align: center; color: white; font-size: 11px; '
            'line-height: 20px;">{}</div></div>',
            progress,
            color,
            f'{progress}%'
        )
    progress_bar.short_description = 'Progress'

    def progress_display(self, obj):
        """Progress percentage"""
        return f"{obj.get_progress()}%"
    progress_display.short_description = 'Progress'

    actions = ['update_stats', 'mark_as_completed']

    def update_stats(self, request, queryset):
        """Update statistics for selected rounds"""
        for round in queryset:
            round.update_stats()
        self.message_user(request, f'Statistics updated for {queryset.count()} review rounds.')
    update_stats.short_description = 'Update statistics'

    def mark_as_completed(self, request, queryset):
        """Mark selected rounds as completed"""
        from django.utils import timezone
        count = queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(request, f'{count} review rounds marked as completed.')
    mark_as_completed.short_description = 'Mark as completed'


@admin.register(ReviewParticipant)
class ReviewParticipantAdmin(admin.ModelAdmin):
    """Admin interface for Review Participants"""

    list_display = [
        'user',
        'review_round',
        'role',
        'status',
        'permissions_display',
        'activity_display',
        'comments_count',
        'ratings_count',
        'joined_at',
    ]

    list_filter = [
        'role',
        'status',
        'can_comment',
        'can_rate',
        'joined_at',
    ]

    search_fields = [
        'user__username',
        'user__email',
        'review_round__title',
    ]

    readonly_fields = [
        'joined_at',
        'last_activity_at',
        'comments_count',
        'ratings_count',
    ]

    fieldsets = (
        ('Assignment', {
            'fields': ('review_round', 'user', 'role')
        }),
        ('Permissions', {
            'fields': (
                'can_comment',
                'can_rate',
                'can_see_other_comments',
                'status',
            )
        }),
        ('Activity', {
            'fields': (
                'joined_at',
                'last_activity_at',
                'comments_count',
                'ratings_count',
            ),
            'classes': ('collapse',)
        }),
    )

    def permissions_display(self, obj):
        """Show permissions as icons"""
        icons = []
        if obj.can_comment:
            icons.append('💬')
        if obj.can_rate:
            icons.append('⭐')
        if obj.can_see_other_comments:
            icons.append('👁')
        return ' '.join(icons) if icons else '-'
    permissions_display.short_description = 'Permissions'

    def activity_display(self, obj):
        """Show activity status"""
        if obj.last_activity_at:
            from django.utils import timezone
            delta = timezone.now() - obj.last_activity_at
            if delta.days == 0:
                return format_html('<span style="color: green;">● Active today</span>')
            elif delta.days < 7:
                return format_html(
                    '<span style="color: orange;">● {} days ago</span>',
                    delta.days
                )
            else:
                return format_html(
                    '<span style="color: gray;">● {} days ago</span>',
                    delta.days
                )
        return format_html('<span style="color: lightgray;">○ Never</span>')
    activity_display.short_description = 'Activity'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Admin interface for Comments"""

    list_display = [
        'id',
        'chapter_link',
        'author',
        'comment_type',
        'status',
        'text_preview',
        'reply_status',
        'created_at',
    ]

    list_filter = [
        'comment_type',
        'status',
        'review_round',
        'created_at',
    ]

    search_fields = [
        'text',
        'author_reply',
        'author__username',
        'chapter__title',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'replied_at',
        'resolved_at',
        'resolved_by',
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': ('review_round', 'chapter', 'author')
        }),
        ('Comment', {
            'fields': ('text', 'comment_type', 'status')
        }),
        ('Author Response', {
            'fields': ('author_reply', 'replied_at', 'resolved_by', 'resolved_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'is_edited', 'helpful_count'),
            'classes': ('collapse',)
        }),
    )

    def chapter_link(self, obj):
        """Link to chapter"""
        if obj.chapter:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:bfagent_bookchapters_change', args=[obj.chapter.pk]),
                obj.chapter.title
            )
        return '-'
    chapter_link.short_description = 'Chapter'

    def text_preview(self, obj):
        """Show preview of comment text"""
        if len(obj.text) > 60:
            return obj.text[:60] + '...'
        return obj.text
    text_preview.short_description = 'Comment'

    def reply_status(self, obj):
        """Show reply status"""
        if obj.author_reply:
            return format_html('<span style="color: green;">✓ Replied</span>')
        elif obj.status == 'open':
            return format_html('<span style="color: red;">! No reply</span>')
        return '-'
    reply_status.short_description = 'Reply'

    actions = ['mark_as_resolved', 'mark_as_open']

    def mark_as_resolved(self, request, queryset):
        """Mark selected comments as resolved"""
        count = queryset.update(status='resolved')
        self.message_user(request, f'{count} comments marked as resolved.')
    mark_as_resolved.short_description = 'Mark as resolved'

    def mark_as_open(self, request, queryset):
        """Mark selected comments as open"""
        count = queryset.update(status='open')
        self.message_user(request, f'{count} comments marked as open.')
    mark_as_open.short_description = 'Mark as open'


@admin.register(ChapterRating)
class ChapterRatingAdmin(admin.ModelAdmin):
    """Admin interface for Chapter Ratings"""

    list_display = [
        'id',
        'chapter_link',
        'reviewer',
        'rating_display',
        'has_feedback',
        'created_at',
    ]

    list_filter = [
        'overall_rating',
        'review_round',
        'created_at',
    ]

    search_fields = [
        'feedback_text',
        'reviewer__username',
        'chapter__title',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': ('review_round', 'chapter', 'reviewer')
        }),
        ('Rating', {
            'fields': ('overall_rating', 'feedback_text')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def chapter_link(self, obj):
        """Link to chapter"""
        if obj.chapter:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:bfagent_bookchapters_change', args=[obj.chapter.pk]),
                obj.chapter.title
            )
        return '-'
    chapter_link.short_description = 'Chapter'

    def rating_display(self, obj):
        """Show rating as stars"""
        stars = '★' * obj.overall_rating + '☆' * (5 - obj.overall_rating)
        color = 'green' if obj.overall_rating >= 4 else 'orange' if obj.overall_rating >= 3 else 'red'
        return format_html(
            '<span style="color: {}; font-size: 16px;">{}</span>',
            color,
            stars
        )
    rating_display.short_description = 'Rating'

    def has_feedback(self, obj):
        """Check if has feedback text"""
        if obj.feedback_text:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: lightgray;">-</span>')
    has_feedback.short_description = 'Feedback'
