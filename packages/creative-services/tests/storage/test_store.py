"""Tests for ContentStore using a mock asyncpg pool (ADR-062 Phase 1)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from creative_services.storage.models import ContentItem, ContentRelation, sha256
from creative_services.storage.store import ContentStore


TEXT = "Agent task plan content"
HASH = sha256(TEXT)


def _make_item(**kwargs) -> ContentItem:
    defaults = dict(
        source_svc="agent-team",
        source_type="task_plan",
        source_id="adr:ADR-062",
        tenant_id=None,
        content=TEXT,
        content_hash=HASH,
        model_used="claude-opus-4",
    )
    defaults.update(kwargs)
    return ContentItem(**defaults)


def _make_row(item: ContentItem) -> MagicMock:
    row = MagicMock()
    row.__getitem__ = lambda self, k: {
        "id": item.id,
        "source_svc": item.source_svc,
        "source_type": item.source_type,
        "source_id": item.source_id,
        "tenant_id": item.tenant_id,
        "content": item.content,
        "content_hash": item.content_hash,
        "prompt_key": item.prompt_key,
        "model_used": item.model_used,
        "version": item.version,
        "parent_id": item.parent_id,
        "tags": item.tags,
        "properties": item.properties,
        "created_at": item.created_at,
    }[k]
    return row


@pytest.fixture
def store():
    s = ContentStore.__new__(ContentStore)
    s._dsn = "postgresql://test"
    s._pool = None
    return s


@pytest.mark.asyncio
async def test_should_save_item(store):
    item = _make_item()
    mock_conn = AsyncMock()
    mock_pool = AsyncMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    store._pool = mock_pool

    result = await store.save(item)

    assert result.id == item.id
    mock_conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_should_return_none_for_missing_item(store):
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = None
    mock_pool = AsyncMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    store._pool = mock_pool

    result = await store.get(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_should_add_relation(store):
    item = _make_item()
    rel = ContentRelation(
        source_item=item.id,
        target_ref="adr:ADR-059",
        relation_type="implements",
    )
    mock_conn = AsyncMock()
    mock_pool = AsyncMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    store._pool = mock_pool

    result = await store.add_relation(rel)
    assert result.id == rel.id
    mock_conn.execute.assert_called_once()
