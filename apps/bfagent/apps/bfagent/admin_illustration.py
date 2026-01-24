"""
Django Admin Configuration for Illustration System
"""
from django.contrib import admin
from django.utils.html import format_html
from .models_illustration import (
    ImageStyleProfile,
    IllustrationImage,
    ImageGenerationBatch,
)


@admin.register(ImageStyleProfile)
class ImageStyleProfileAdmin(admin.ModelAdmin):
    """Admin interface for Image Style Profiles"""
    
    list_display = [
        'style_id',
        'display_name',
        'art_style',
        'preferred_provider',
        'usage_count',
        'total_cost_display',
        'user',
        'created_at',
    ]
    
    list_filter = [
        'art_style',
        'preferred_provider',
        'default_quality',
        'created_at',
    ]
    
    search_fields = [
        'style_id',
        'display_name',
        'description',
        'base_prompt',
    ]
    
    readonly_fields = [
        'style_id',
        'created_at',
        'updated_at',
        'usage_count',
        'total_cost_usd',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'style_id',
                'display_name',
                'description',
                'user',
                'project',
            )
        }),
        ('Style Settings', {
            'fields': (
                'art_style',
                'color_mood',
                'base_prompt',
                'negative_prompt',
            )
        }),
        ('Technical Settings', {
            'fields': (
                'default_resolution',
                'default_quality',
                'preferred_provider',
            )
        }),
        ('Consistency Settings', {
            'fields': (
                'consistency_weight',
                'style_strength',
                'seed',
                'reference_images',
            )
        }),
        ('Metadata', {
            'fields': (
                'tags',
                'version',
                'created_at',
                'updated_at',
            )
        }),
        ('Statistics', {
            'fields': (
                'usage_count',
                'total_cost_usd',
            )
        }),
    )
    
    def total_cost_display(self, obj):
        """Format cost for display"""
        return f"${obj.total_cost_usd:.2f}"
    total_cost_display.short_description = 'Total Cost'


@admin.register(IllustrationImage)
class IllustrationImageAdmin(admin.ModelAdmin):
    """Admin interface for Illustration Images (Legacy)"""
    
    list_display = [
        'image_id',
        'image_thumbnail',
        'image_type',
        'status',
        'provider_used',
        'cost_display',
        'quality_display',
        'user',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'image_type',
        'provider_used',
        'quality',
        'created_at',
    ]
    
    search_fields = [
        'image_id',
        'prompt_used',
        'content_context',
    ]
    
    readonly_fields = [
        'image_id',
        'image_preview',
        'generation_time_seconds',
        'cost_usd',
        'created_at',
        'updated_at',
        'content_summary',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'image_id',
                'image_type',
                'status',
                'user',
            )
        }),
        ('Relations', {
            'fields': (
                'style_profile',
                'project',
                'chapter',
            )
        }),
        ('Generation Info', {
            'fields': (
                'provider_used',
                'prompt_used',
                'negative_prompt_used',
            )
        }),
        ('Image Data', {
            'fields': (
                'image_preview',
                'image_url',
                'image_file',
                'thumbnail_url',
            )
        }),
        ('Technical Details', {
            'fields': (
                'resolution',
                'quality',
                'seed',
            )
        }),
        ('Generation Metrics', {
            'fields': (
                'generation_time_seconds',
                'cost_usd',
                'retry_count',
            )
        }),
        ('Content Context', {
            'fields': (
                'content_context',
                'content_summary',
            )
        }),
        ('Quality & Approval', {
            'fields': (
                'quality_score',
                'user_rating',
                'approved_by',
                'approved_at',
                'rejection_reason',
            )
        }),
        ('Metadata', {
            'fields': (
                'tags',
                'metadata',
                'error_message',
                'created_at',
                'updated_at',
            )
        }),
    )
    
    actions = ['approve_images', 'reject_images']
    
    def image_thumbnail(self, obj):
        """Display small thumbnail"""
        if obj.thumbnail_url:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;"/>',
                obj.thumbnail_url
            )
        elif obj.image_url:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;"/>',
                obj.image_url
            )
        return "No image"
    image_thumbnail.short_description = 'Preview'
    
    def image_preview(self, obj):
        """Display larger image preview"""
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-width: 400px; max-height: 400px;"/>',
                obj.image_url
            )
        return "No image"
    image_preview.short_description = 'Image Preview'
    
    def cost_display(self, obj):
        """Format cost for display"""
        return f"${obj.cost_usd:.4f}"
    cost_display.short_description = 'Cost'
    
    def quality_display(self, obj):
        """Display quality with color"""
        if obj.quality_score:
            color = 'green' if obj.quality_score > 0.7 else 'orange' if obj.quality_score > 0.5 else 'red'
            return format_html(
                '<span style="color: {};">{:.2f}</span>',
                color,
                obj.quality_score
            )
        return '-'
    quality_display.short_description = 'Quality'
    
    def approve_images(self, request, queryset):
        """Bulk approve images"""
        for image in queryset:
            image.approve(request.user)
        self.message_user(request, f"{queryset.count()} images approved")
    approve_images.short_description = "Approve selected images"
    
    def reject_images(self, request, queryset):
        """Bulk reject images"""
        queryset.update(status='rejected')
        self.message_user(request, f"{queryset.count()} images rejected")
    reject_images.short_description = "Reject selected images"


@admin.register(ImageGenerationBatch)
class ImageGenerationBatchAdmin(admin.ModelAdmin):
    """Admin interface for Image Generation Batches"""
    
    list_display = [
        'batch_id',
        'name',
        'status',
        'progress_display',
        'image_type',
        'provider',
        'cost_display',
        'user',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'image_type',
        'provider',
        'created_at',
    ]
    
    search_fields = [
        'batch_id',
        'name',
        'description',
    ]
    
    readonly_fields = [
        'batch_id',
        'generated_count',
        'failed_count',
        'total_cost_usd',
        'progress_percentage',
        'created_at',
        'started_at',
        'completed_at',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'batch_id',
                'name',
                'description',
                'user',
            )
        }),
        ('Relations', {
            'fields': (
                'project',
                'style_profile',
            )
        }),
        ('Batch Settings', {
            'fields': (
                'image_type',
                'provider',
                'total_images',
            )
        }),
        ('Progress', {
            'fields': (
                'status',
                'generated_count',
                'failed_count',
                'progress_percentage',
            )
        }),
        ('Cost', {
            'fields': (
                'estimated_cost_usd',
                'total_cost_usd',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'started_at',
                'completed_at',
            )
        }),
    )
    
    def progress_display(self, obj):
        """Display progress bar"""
        percentage = obj.progress_percentage
        color = 'green' if percentage == 100 else 'blue'
        return format_html(
            '<div style="width: 100px; background: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background: {}; height: 20px; border-radius: 3px; text-align: center; color: white;">{}/{})</div>'
            '</div>',
            percentage,
            color,
            obj.generated_count,
            obj.total_images
        )
    progress_display.short_description = 'Progress'
    
    def cost_display(self, obj):
        """Format cost for display"""
        return f"${obj.total_cost_usd:.2f} / ${obj.estimated_cost_usd:.2f}"
    cost_display.short_description = 'Cost (Actual/Estimated)'
