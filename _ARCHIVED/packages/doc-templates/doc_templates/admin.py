"""Admin registration for doc_templates."""

from django.contrib import admin

from .models import DocumentInstance, DocumentTemplate


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "scope", "status", "section_count", "field_count", "updated_at"]
    list_filter = ["status", "scope"]
    search_fields = ["name", "description"]
    readonly_fields = ["uuid", "created_at", "updated_at"]


@admin.register(DocumentInstance)
class DocumentInstanceAdmin(admin.ModelAdmin):
    list_display = ["name", "template", "status", "updated_at"]
    list_filter = ["status"]
    search_fields = ["name"]
    readonly_fields = ["uuid", "created_at", "updated_at"]
    raw_id_fields = ["template"]
