"""Synchronous ContentStore wrapper for Django apps (ADR-062).

Uses asgiref.sync.async_to_sync internally.
  - Safe in Django WSGI views, Celery tasks AND async Django views (ASGI).
  - Prevents deadlocks in Daphne/Uvicorn ASGI contexts (unlike asyncio.run()).

Usage in bfagent::

    from creative_services.storage.django_adapter import SyncContentStore
    from creative_services.storage.models import ContentItem, sha256

    store = SyncContentStore()
    item = store.save(ContentItem(
        source_svc="bfagent",
        source_type="draft",
        source_id=str(chapter.id),
        tenant_id=None,
        content=text,
        content_hash=sha256(text),
        model_used="gpt-4o-mini",
    ))

Usage in travel-beat::

    store = SyncContentStore()
    item = store.save(ContentItem(
        source_svc="travel-beat",
        source_type="chapter",
        source_id=str(chapter.id),
        tenant_id=chapter.tenant_id,   # required for travel-beat
        content=text,
        content_hash=sha256(text),
        model_used="gpt-4o-mini",
    ))
"""

from __future__ import annotations

import logging
from uuid import UUID

from asgiref.sync import async_to_sync

from .models import ContentItem, ContentRelation
from .store import ContentStore

logger = logging.getLogger(__name__)


class SyncContentStore:
    """Synchronous wrapper around ContentStore for Django WSGI and ASGI apps."""

    def __init__(self, dsn: str | None = None) -> None:
        self._store = ContentStore(dsn=dsn)

    def save(self, item: ContentItem) -> ContentItem:
        """Persist a ContentItem synchronously."""
        return async_to_sync(self._store.save)(item)

    def get(self, item_id: UUID) -> ContentItem | None:
        """Fetch a single item by id synchronously."""
        return async_to_sync(self._store.get)(item_id)

    def get_versions(
        self, source_svc: str, source_id: str
    ) -> list[ContentItem]:
        """All versions of an item, newest first."""
        return async_to_sync(self._store.get_versions)(source_svc, source_id)

    def latest(
        self, source_svc: str, source_id: str
    ) -> ContentItem | None:
        """Most recent version of an item."""
        return async_to_sync(self._store.latest)(source_svc, source_id)

    def add_relation(self, relation: ContentRelation) -> ContentRelation:
        """Persist a ContentRelation synchronously."""
        return async_to_sync(self._store.add_relation)(relation)

    def find_by_ref(
        self,
        target_ref: str,
        tenant_id: UUID | None = None,
    ) -> list[ContentItem]:
        """All items related to target_ref."""
        return async_to_sync(self._store.find_by_ref)(target_ref, tenant_id=tenant_id)
