"""Service layer for content_store (ADR-130, ADR-041).

All database access goes through this service — no direct
Model.objects. calls in views or external code.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Optional

from .models import AdrCompliance, ContentItem, ContentRelation

logger = logging.getLogger(__name__)

DB_ALIAS = "content_store"


class ContentStoreService:
    """Service-Layer fuer Content Store Operationen."""

    @staticmethod
    def save_content(
        tenant_id: int,
        source: str,
        content_type: str,
        ref_id: str,
        content: str,
        meta: Optional[dict] = None,
        model_used: str = "",
        prompt_key: str = "",
    ) -> ContentItem:
        """Save or version a content item. Deduplicates by SHA-256."""
        sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

        existing = (
            ContentItem.objects.using(DB_ALIAS)
            .filter(tenant_id=tenant_id, ref_id=ref_id, sha256=sha256)
            .first()
        )
        if existing:
            logger.debug(
                "Duplicate content: tenant=%s ref=%s sha=%s",
                tenant_id, ref_id, sha256[:12],
            )
            return existing

        latest = (
            ContentItem.objects.using(DB_ALIAS)
            .filter(tenant_id=tenant_id, ref_id=ref_id)
            .order_by("-version")
            .first()
        )
        version = (latest.version + 1) if latest else 1

        item = ContentItem.objects.using(DB_ALIAS).create(
            tenant_id=tenant_id,
            source=source,
            type=content_type,
            ref_id=ref_id,
            content=content,
            sha256=sha256,
            version=version,
            meta=meta or {},
            model_used=model_used,
            prompt_key=prompt_key,
        )
        logger.info(
            "ContentItem created: id=%s ref=%s v%d",
            item.pk, ref_id, version,
        )
        return item

    @staticmethod
    def get_latest(
        tenant_id: int,
        ref_id: str,
    ) -> Optional[ContentItem]:
        """Get the latest version of a content item."""
        return (
            ContentItem.objects.using(DB_ALIAS)
            .filter(tenant_id=tenant_id, ref_id=ref_id)
            .order_by("-version")
            .first()
        )

    @staticmethod
    def get_versions(
        tenant_id: int,
        ref_id: str,
    ) -> list[ContentItem]:
        """Get all versions of a content item, newest first."""
        return list(
            ContentItem.objects.using(DB_ALIAS)
            .filter(tenant_id=tenant_id, ref_id=ref_id)
            .order_by("-version")
        )

    @staticmethod
    def search(
        tenant_id: int,
        source: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[ContentItem]:
        """Search content items with optional filters."""
        qs = ContentItem.objects.using(DB_ALIAS).filter(
            tenant_id=tenant_id,
        )
        if source:
            qs = qs.filter(source=source)
        if content_type:
            qs = qs.filter(type=content_type)
        return list(qs[:limit])

    @staticmethod
    def add_relation(
        source_item: ContentItem,
        target_item: ContentItem,
        relation_type: str,
    ) -> ContentRelation:
        """Create or get a relation between two content items."""
        rel, created = ContentRelation.objects.using(
            DB_ALIAS,
        ).get_or_create(
            source_item=source_item,
            target_item=target_item,
            relation_type=relation_type,
        )
        if created:
            logger.info(
                "Relation created: %s --%s--> %s",
                source_item.pk, relation_type, target_item.pk,
            )
        return rel

    @staticmethod
    def save_compliance(
        tenant_id: int,
        adr_id: str,
        drift_score: float,
        status: str,
        details: Optional[dict] = None,
    ) -> AdrCompliance:
        """Persist an ADR drift-detector compliance result."""
        record = AdrCompliance.objects.using(DB_ALIAS).create(
            tenant_id=tenant_id,
            adr_id=adr_id,
            drift_score=drift_score,
            status=status,
            details=details or {},
        )
        logger.info(
            "Compliance logged: ADR-%s score=%.2f status=%s",
            adr_id, drift_score, status,
        )
        return record

    @staticmethod
    def get_compliance_history(
        tenant_id: int,
        adr_id: str,
        limit: int = 20,
    ) -> list[AdrCompliance]:
        """Get compliance check history for an ADR."""
        return list(
            AdrCompliance.objects.using(DB_ALIAS)
            .filter(tenant_id=tenant_id, adr_id=adr_id)
            .order_by("-checked_at")[:limit]
        )
