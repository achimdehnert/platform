from django.contrib import admin

from .models import Customer, Presentation, PresentationText


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["customer_id", "customer_name", "user", "dashboard_access", "created_at"]
    list_filter = ["dashboard_access", "created_at"]
    search_fields = ["customer_id", "customer_name", "user__username"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        ("Customer Information", {"fields": ("customer_id", "customer_name", "user")}),
        ("Access", {"fields": ("dashboard_access",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


class PresentationTextInline(admin.TabularInline):
    """Inline admin for presentation texts"""

    model = PresentationText
    extra = 0
    fields = ["slide_number", "text_id", "original_text", "translated_text", "translation_method", "manually_edited"]
    readonly_fields = ["text_id", "original_text"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        """Don't allow adding texts manually"""
        return False


@admin.register(Presentation)
class PresentationAdmin(admin.ModelAdmin):
    list_display = [
        "filename",
        "customer",
        "source_language",
        "target_language",
        "status",
        "progress_percentage",
        "created_at",
    ]
    list_filter = ["status", "source_language", "target_language", "created_at"]
    search_fields = ["pptx_file", "customer__customer_name"]
    readonly_fields = ["created_at", "updated_at", "progress_percentage"]
    inlines = [PresentationTextInline]
    fieldsets = (
        ("Presentation Information", {"fields": ("customer", "pptx_file")}),
        ("Translation Settings", {"fields": ("source_language", "target_language", "status")}),
        ("Progress", {"fields": ("total_texts", "translated_texts", "progress_percentage")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(PresentationText)
class PresentationTextAdmin(admin.ModelAdmin):
    """Standalone admin for all presentation texts"""

    list_display = [
        "text_id",
        "presentation",
        "slide_number",
        "original_preview",
        "translated_preview",
        "translation_method",
        "manually_edited",
    ]
    list_filter = ["translation_method", "manually_edited", "slide_number"]
    search_fields = ["text_id", "original_text", "translated_text", "presentation__pptx_file"]
    readonly_fields = ["text_id", "created_at", "updated_at"]
    fieldsets = (
        ("Text Information", {"fields": ("presentation", "slide_number", "text_id")}),
        ("Original Text", {"fields": ("original_text",)}),
        ("Translation", {"fields": ("translated_text", "translation_method", "manually_edited")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def original_preview(self, obj):
        """Show preview of original text"""
        return obj.original_text[:50] + "..." if len(obj.original_text) > 50 else obj.original_text

    original_preview.short_description = "Original Text"

    def translated_preview(self, obj):
        """Show preview of translated text"""
        if not obj.translated_text:
            return "-"
        return obj.translated_text[:50] + "..." if len(obj.translated_text) > 50 else obj.translated_text

    translated_preview.short_description = "Translated Text"
