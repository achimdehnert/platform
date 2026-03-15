"""research-hub knowledge service layer.

Business logic for KnowledgeDocument — never in views or tasks directly.
Platform Standard: all business logic in service layer.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from django.db import transaction

from .models import KnowledgeDocument, KnowledgeDocumentStatus, KnowledgeDocumentType

logger = logging.getLogger(__name__)


def _collection_to_type(collection_id: str) -> str:
    """Map Outline collection ID to KnowledgeDocumentType.

    Falls back to OTHER if collection not recognized.
    Requires OUTLINE_COLLECTION_* settings to be configured.
    """
    from django.conf import settings

    mapping = {
        getattr(settings, "OUTLINE_COLLECTION_RUNBOOKS", ""): KnowledgeDocumentType.RUNBOOK,
        getattr(settings, "OUTLINE_COLLECTION_CONCEPTS", ""): KnowledgeDocumentType.CONCEPT,
        getattr(settings, "OUTLINE_COLLECTION_LESSONS", ""): KnowledgeDocumentType.LESSON_LEARNED,
        getattr(settings, "OUTLINE_COLLECTION_ADR_DRAFTS", ""): KnowledgeDocumentType.ADR_DRAFT,
        getattr(settings, "OUTLINE_COLLECTION_ADR_MIRROR", ""): KnowledgeDocumentType.ADR_MIRROR,
        getattr(settings, "OUTLINE_COLLECTION_HUB_DOCS", ""): KnowledgeDocumentType.HUB_DOCS,
    }
    # Remove empty-string keys (unconfigured collections)
    mapping = {k: v for k, v in mapping.items() if k}
    return mapping.get(collection_id, KnowledgeDocumentType.OTHER)


class KnowledgeDocumentService:
    """Service layer for KnowledgeDocument lifecycle operations."""

    def upsert_from_outline_id(
        self,
        tenant_id: int,
        outline_id: str,
        collection_id: str,
        outline_url: str,
        title: str,
    ) -> KnowledgeDocument:
        """Create or update a KnowledgeDocument from Outline webhook data.

        Sets enrichment_status back to PENDING to trigger re-enrichment on update.
        Uses select_for_update to prevent race conditions from concurrent webhooks.
        """
        doc_type = _collection_to_type(collection_id)

        with transaction.atomic():
            doc, created = KnowledgeDocument.objects.select_for_update().get_or_create(
                tenant_id=tenant_id,
                outline_id=outline_id,
                deleted_at__isnull=True,
                defaults={
                    "outline_collection_id": collection_id,
                    "outline_url": outline_url,
                    "title": title,
                    "doc_type": doc_type,
                    "enrichment_status": KnowledgeDocumentStatus.PENDING,
                    "outline_updated_at": datetime.now(UTC),
                },
            )

            if not created:
                doc.title = title
                doc.outline_collection_id = collection_id
                doc.outline_url = outline_url
                doc.doc_type = doc_type
                doc.enrichment_status = KnowledgeDocumentStatus.PENDING
                doc.outline_updated_at = datetime.now(UTC)
                doc.enrichment_error = ""
                doc.save(
                    update_fields=[
                        "title",
                        "outline_collection_id",
                        "outline_url",
                        "doc_type",
                        "enrichment_status",
                        "outline_updated_at",
                        "enrichment_error",
                        "updated_at",
                    ]
                )

        action = "created" if created else "updated"
        logger.info(
            "KnowledgeDocument %s: outline_id=%s tenant=%s",
            action,
            outline_id,
            tenant_id,
        )
        return doc

    def soft_delete_by_outline_id(self, tenant_id: int, outline_id: str) -> int:
        """Soft-delete matching KnowledgeDocument. Returns number of affected rows."""
        updated = KnowledgeDocument.objects.filter(
            tenant_id=tenant_id,
            outline_id=outline_id,
            deleted_at__isnull=True,
        ).update(deleted_at=datetime.now(UTC))

        if updated:
            logger.info(
                "KnowledgeDocument soft-deleted: outline_id=%s tenant=%s",
                outline_id,
                tenant_id,
            )
        return updated

    def mark_enriched(
        self,
        doc_id: int,
        summary: str,
        keywords: list[str],
        related_adrs: list[str],
        content_snapshot: str,
    ) -> None:
        """Mark document as enriched with AI-generated metadata."""
        KnowledgeDocument.objects.filter(pk=doc_id).update(
            summary=summary,
            keywords=keywords,
            related_adrs=related_adrs,
            content_snapshot=content_snapshot,
            enrichment_status=KnowledgeDocumentStatus.ENRICHED,
            enrichment_error="",
            enriched_at=datetime.now(UTC),
        )

    def mark_enrichment_error(self, doc_id: int, error_message: str) -> None:
        """Record enrichment failure. Sanitize message before storage."""
        # Truncate to avoid unbounded storage
        safe_message = str(error_message)[:500]
        KnowledgeDocument.objects.filter(pk=doc_id).update(
            enrichment_status=KnowledgeDocumentStatus.ERROR,
            enrichment_error=safe_message,
        )
