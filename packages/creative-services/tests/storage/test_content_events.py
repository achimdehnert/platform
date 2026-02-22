"""Tests for shared_contracts.content_events (ADR-062 Phase 1)."""

from __future__ import annotations

import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "shared_contracts"))

from content_events import (
    ContentSavedEvent,
    ContentRelationAddedEvent,
    ContentVersionBumpedEvent,
)


def test_should_create_content_saved_event():
    item_id = uuid4()
    event = ContentSavedEvent(
        item_id=item_id,
        source_svc="agent-team",
        source_type="task_plan",
        source_id="adr:ADR-062",
        version=1,
        content_hash="a" * 64,
    )
    assert event.item_id == item_id
    assert event.tenant_id is None


def test_should_create_relation_added_event():
    event = ContentRelationAddedEvent(
        relation_id=uuid4(),
        source_item=uuid4(),
        target_ref="adr:ADR-059",
        relation_type="implements",
    )
    assert event.target_ref == "adr:ADR-059"


def test_should_create_version_bumped_event():
    event = ContentVersionBumpedEvent(
        item_id=uuid4(),
        source_svc="bfagent",
        source_id="chapter:42",
        old_version=1,
        new_version=2,
    )
    assert event.new_version > event.old_version
