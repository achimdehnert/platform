"""Tests for creative_services.storage.models (ADR-062 Phase 1)."""

from __future__ import annotations

import pytest
from uuid import uuid4

from creative_services.storage.models import (
    ContentItem,
    ContentRelation,
    sha256,
)


TEXT = "Hello, world!"
HASH = sha256(TEXT)


def _item(**kwargs) -> ContentItem:
    defaults = dict(
        source_svc="agent-team",
        source_type="task_plan",
        source_id="adr:ADR-062",
        tenant_id=None,
        content=TEXT,
        content_hash=HASH,
        model_used="gpt-4o-mini",
    )
    defaults.update(kwargs)
    return ContentItem(**defaults)


def test_should_create_content_item_with_defaults():
    item = _item()
    assert item.version == 1
    assert item.parent_id is None
    assert item.tags == []
    assert item.properties == {}
    assert item.tenant_id is None


def test_should_compute_sha256():
    h = sha256(TEXT)
    assert len(h) == 64
    assert h == sha256(TEXT)


def test_should_reject_invalid_content_hash():
    with pytest.raises(Exception):
        _item(content_hash="tooshort")


def test_should_allow_null_tenant_for_platform_content():
    item = _item(source_svc="agent-team", tenant_id=None)
    assert item.tenant_id is None


def test_should_require_tenant_id_for_travel_beat():
    with pytest.raises(Exception, match="tenant_id is required"):
        _item(source_svc="travel-beat", tenant_id=None)


def test_should_accept_tenant_id_for_travel_beat():
    tid = uuid4()
    item = _item(source_svc="travel-beat", tenant_id=tid)
    assert item.tenant_id == tid


def test_should_not_leak_content_across_tenants():
    tid_a = uuid4()
    tid_b = uuid4()
    item_a = _item(source_svc="travel-beat", tenant_id=tid_a)
    item_b = _item(source_svc="travel-beat", tenant_id=tid_b)
    assert item_a.tenant_id != item_b.tenant_id


def test_should_create_new_version_on_save():
    item_v1 = _item(version=1)
    item_v2 = ContentItem(
        **{**item_v1.model_dump(), "id": uuid4(), "version": 2, "parent_id": item_v1.id}
    )
    assert item_v2.version == 2
    assert item_v2.parent_id == item_v1.id


def test_should_create_content_relation_with_valid_ref():
    item = _item()
    rel = ContentRelation(
        source_item=item.id,
        target_ref="adr:ADR-059",
        relation_type="implements",
    )
    assert rel.weight == 1.0
    assert rel.tenant_id is None


def test_should_reject_relation_with_invalid_target_ref():
    item = _item()
    with pytest.raises(Exception, match="target_ref must follow"):
        ContentRelation(
            source_item=item.id,
            target_ref="no-colon-here",
            relation_type="references",
        )


def test_should_accept_file_target_ref():
    item = _item()
    rel = ContentRelation(
        source_item=item.id,
        target_ref="file:apps/trips/models.py",
        relation_type="references",
    )
    assert rel.target_ref.startswith("file:")
