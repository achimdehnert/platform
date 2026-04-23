"""Tests for SyncContentStore Django adapter (ADR-062)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from creative_services.storage.django_adapter import SyncContentStore
from creative_services.storage.models import ContentItem, sha256


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


def _sync_wrapper(fn):
    """Test helper: wraps async fn so it runs synchronously via asyncio."""
    import asyncio
    def wrapper(*args, **kwargs):
        return asyncio.get_event_loop().run_until_complete(fn(*args, **kwargs))
    return wrapper


def test_should_save_via_sync_store_from_django_service():
    item = _make_item()
    store = SyncContentStore.__new__(SyncContentStore)
    mock_inner = MagicMock()
    mock_inner.save = AsyncMock(return_value=item)
    store._store = mock_inner

    with patch(
        "creative_services.storage.django_adapter.async_to_sync",
        side_effect=_sync_wrapper,
    ):
        result = store.save(item)

    assert result.id == item.id
    assert result.source_svc == "bfagent"


def test_should_return_none_for_missing_item_via_sync():
    store = SyncContentStore.__new__(SyncContentStore)
    mock_inner = MagicMock()
    mock_inner.get = AsyncMock(return_value=None)
    store._store = mock_inner

    with patch(
        "creative_services.storage.django_adapter.async_to_sync",
        side_effect=_sync_wrapper,
    ):
        result = store.get(uuid4())

    assert result is None


def test_should_require_tenant_id_for_travel_beat_via_sync():
    with pytest.raises(Exception, match="tenant_id is required"):
        _make_item(source_svc="travel-beat", tenant_id=None)


def test_uses_async_to_sync_not_asyncio_run():
    """Regression: SyncContentStore must NOT use asyncio.run (deadlocks in ASGI)."""
    from creative_services.storage import django_adapter
    import inspect
    src = inspect.getsource(django_adapter.SyncContentStore)
    assert "asyncio.run" not in src
    assert "async_to_sync" in src
