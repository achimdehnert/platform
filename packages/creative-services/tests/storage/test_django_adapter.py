"""Tests for SyncContentStore Django adapter (ADR-062 Phase 1)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from creative_services.storage.models import ContentItem, sha256
from creative_services.storage.django_adapter import SyncContentStore


TEXT = "Chapter draft content"
HASH = sha256(TEXT)


def _make_item(source_svc="bfagent", tenant_id=None) -> ContentItem:
    return ContentItem(
        source_svc=source_svc,
        source_type="draft",
        source_id="chapter:42",
        tenant_id=tenant_id,
        content=TEXT,
        content_hash=HASH,
        model_used="gpt-4o-mini",
    )


def test_should_save_via_sync_store_from_django_service():
    item = _make_item()
    store = SyncContentStore.__new__(SyncContentStore)
    mock_inner = MagicMock()
    mock_inner.save = MagicMock(return_value=item)
    store._store = mock_inner

    with patch("asyncio.run", side_effect=lambda coro: mock_inner.save(item)):
        result = store.save(item)

    assert result.id == item.id
    assert result.source_svc == "bfagent"


def test_should_return_none_for_missing_item_via_sync():
    store = SyncContentStore.__new__(SyncContentStore)
    mock_inner = MagicMock()
    store._store = mock_inner

    with patch("asyncio.run", return_value=None):
        result = store.get(uuid4())

    assert result is None


def test_should_require_tenant_id_for_travel_beat_via_sync():
    import pytest
    with pytest.raises(Exception, match="tenant_id is required"):
        _make_item(source_svc="travel-beat", tenant_id=None)
