"""Async ContentStore backed by asyncpg (ADR-062 Phase 1).

Designed for use in async contexts: MCP servers, Agent-Team, FastAPI.
For Django apps use SyncContentStore from django_adapter.py.
"""

from __future__ import annotations

import logging
import os
from typing import Any
from uuid import UUID

try:
    import asyncpg
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "asyncpg is required for ContentStore. "
        "Install: pip install creative-services[storage]"
    ) from exc

from .models import ContentItem, ContentRelation

logger = logging.getLogger(__name__)

_INSERT_ITEM = """
    INSERT INTO content_store.items (
        id, source_svc, source_type, source_id, tenant_id,
        content, content_hash, prompt_key, model_used,
        version, parent_id, tags, properties, created_at, updated_at
    ) VALUES (
        $1, $2, $3, $4, $5,
        $6, $7, $8, $9,
        $10, $11, $12, $13::jsonb, $14, $14
    )
    ON CONFLICT (id) DO NOTHING
    RETURNING id
"""

_SELECT_ITEM = """
    SELECT id, source_svc, source_type, source_id, tenant_id,
           content, content_hash, prompt_key, model_used,
           version, parent_id, tags, properties, created_at
    FROM content_store.items
    WHERE id = $1
"""

_SELECT_VERSIONS = """
    SELECT id, source_svc, source_type, source_id, tenant_id,
           content, content_hash, prompt_key, model_used,
           version, parent_id, tags, properties, created_at
    FROM content_store.items
    WHERE source_svc = $1 AND source_id = $2
    ORDER BY version DESC
"""

_SELECT_LATEST = """
    SELECT id, source_svc, source_type, source_id, tenant_id,
           content, content_hash, prompt_key, model_used,
           version, parent_id, tags, properties, created_at
    FROM content_store.items
    WHERE source_svc = $1 AND source_id = $2
    ORDER BY version DESC
    LIMIT 1
"""

_INSERT_RELATION = """
    INSERT INTO content_store.relations (
        id, source_item, target_ref, relation_type,
        tenant_id, weight, properties, created_at
    ) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
    ON CONFLICT (id) DO NOTHING
    RETURNING id
"""

_SELECT_BY_REF = """
    SELECT i.id, i.source_svc, i.source_type, i.source_id, i.tenant_id,
           i.content, i.content_hash, i.prompt_key, i.model_used,
           i.version, i.parent_id, i.tags, i.properties, i.created_at
    FROM content_store.items i
    JOIN content_store.relations r ON r.source_item = i.id
    WHERE r.target_ref = $1
    ORDER BY i.created_at DESC
"""


def _row_to_item(row: asyncpg.Record) -> ContentItem:
    import json
    props = row["properties"]
    if isinstance(props, str):
        props = json.loads(props)
    return ContentItem(
        id=row["id"],
        source_svc=row["source_svc"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        tenant_id=row["tenant_id"],
        content=row["content"],
        content_hash=row["content_hash"],
        prompt_key=row["prompt_key"],
        model_used=row["model_used"],
        version=row["version"],
        parent_id=row["parent_id"],
        tags=list(row["tags"]) if row["tags"] else [],
        properties=props if isinstance(props, dict) else {},
        created_at=row["created_at"],
    )


class ContentStore:
    """Async content store backed by asyncpg.

    Usage::

        store = ContentStore()  # reads CONTENT_STORE_DSN from env
        item = await store.save(ContentItem(...))
        latest = await store.latest("agent-team", "adr:ADR-062")
    """

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or os.environ.get("CONTENT_STORE_DSN")
        if not self._dsn:
            raise RuntimeError("CONTENT_STORE_DSN not set — pass dsn= or export env var")
        self._pool: asyncpg.Pool | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=10)
        return self._pool

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def __aenter__(self) -> "ContentStore":
        await self._get_pool()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def save(self, item: ContentItem) -> ContentItem:
        """Persist a ContentItem. Idempotent on id (ON CONFLICT DO NOTHING)."""
        import json
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                _INSERT_ITEM,
                item.id,
                item.source_svc,
                item.source_type,
                item.source_id,
                item.tenant_id,
                item.content,
                item.content_hash,
                item.prompt_key,
                item.model_used,
                item.version,
                item.parent_id,
                item.tags,
                json.dumps(item.properties),
                item.created_at,
            )
        logger.debug("saved item id=%s svc=%s type=%s", item.id, item.source_svc, item.source_type)
        return item

    async def get(self, item_id: UUID) -> ContentItem | None:
        """Fetch a single item by id."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(_SELECT_ITEM, item_id)
        return _row_to_item(row) if row else None

    async def get_versions(
        self, source_svc: str, source_id: str
    ) -> list[ContentItem]:
        """All versions of an item, newest first."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(_SELECT_VERSIONS, source_svc, source_id)
        return [_row_to_item(r) for r in rows]

    async def latest(
        self, source_svc: str, source_id: str
    ) -> ContentItem | None:
        """Most recent version of an item."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(_SELECT_LATEST, source_svc, source_id)
        return _row_to_item(row) if row else None

    async def add_relation(self, relation: ContentRelation) -> ContentRelation:
        """Persist a ContentRelation. Idempotent on id."""
        import json
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                _INSERT_RELATION,
                relation.id,
                relation.source_item,
                relation.target_ref,
                relation.relation_type,
                relation.tenant_id,
                relation.weight,
                json.dumps(relation.properties),
                relation.created_at,
            )
        return relation

    async def find_by_ref(
        self,
        target_ref: str,
        tenant_id: UUID | None = None,
    ) -> list[ContentItem]:
        """All items that have a relation pointing to target_ref."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(_SELECT_BY_REF, target_ref)
        items = [_row_to_item(r) for r in rows]
        if tenant_id is not None:
            items = [i for i in items if i.tenant_id == tenant_id]
        return items
