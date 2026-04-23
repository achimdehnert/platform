"""Django admin for content_store (ADR-130)."""

from django.contrib import admin

from .models import AdrCompliance, ContentItem, ContentRelation


@admin.register(ContentItem)
class ContentItemAdmin(admin.ModelAdmin):
    list_display = [
        "pk",
        "tenant_id",
        "source",
        "type",
        "ref_id",
        "version",
        "model_used",
        "created_at",
    ]
    list_filter = ["source", "type", "tenant_id"]
    search_fields = ["ref_id", "sha256"]
    readonly_fields = ["sha256", "created_at", "updated_at"]
    ordering = ["-created_at"]


@admin.register(ContentRelation)
class ContentRelationAdmin(admin.ModelAdmin):
    list_display = [
        "pk",
        "source_item",
        "target_item",
        "relation_type",
        "created_at",
    ]
    list_filter = ["relation_type"]
    raw_id_fields = ["source_item", "target_item"]


@admin.register(AdrCompliance)
class AdrComplianceAdmin(admin.ModelAdmin):
    list_display = [
        "pk",
        "tenant_id",
        "adr_id",
        "drift_score",
        "status",
        "checked_at",
    ]
    list_filter = ["status", "adr_id"]
    ordering = ["-checked_at"]
