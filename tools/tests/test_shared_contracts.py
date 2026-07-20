"""Schema-Stabilitaets-Tests fuer shared_contracts/ (platform#820, Entscheid A).

Owner-Entscheid (Issue #820): shared_contracts hat aktuell 0 verifizierte
externe Konsumenten (Stand 2026-07-02), wird aber als Zukunfts-Interface
vorgehalten statt archiviert. Diese Tests sichern die Pydantic-Contracts
in shared_contracts/content_events.py gegen unbeabsichtigte Breaking
Changes ab (Pflichtfelder, Typen, frozen-Invariante) — kein Netz, keine
externen Abhaengigkeiten ausser pydantic.

shared_contracts/db_views.py und task_schemas.py enthalten aktuell nur
leere Template-Dicts (keine Pydantic-Models) und sind hier bewusst nicht
Gegenstand von Instanziierungs-Tests; VIEW_CONTRACTS/TASK_SCHEMAS werden
nur auf ihren Basistyp geprueft.
"""

from __future__ import annotations

import pathlib
import sys
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared_contracts.content_events import (  # noqa: E402
    ContentRelationAddedEvent,
    ContentSavedEvent,
    ContentVersionBumpedEvent,
)
from shared_contracts import db_views, task_schemas  # noqa: E402


# ---------------------------------------------------------------------------
# ContentSavedEvent
# ---------------------------------------------------------------------------


def _valid_content_saved_kwargs() -> dict:
    return dict(
        item_id=uuid4(),
        source_svc="content-store",
        source_type="article",
        source_id="art-123",
        version=1,
        content_hash="a" * 64,
    )


def test_should_instantiate_content_saved_event_with_valid_data():
    event = ContentSavedEvent(**_valid_content_saved_kwargs())

    assert isinstance(event.item_id, UUID)
    assert event.source_svc == "content-store"
    assert event.source_type == "article"
    assert event.source_id == "art-123"
    assert event.tenant_id is None
    assert event.version == 1
    assert event.content_hash == "a" * 64
    assert isinstance(event.occurred_at, datetime)


@pytest.mark.parametrize(
    "missing_field",
    ["item_id", "source_svc", "source_type", "source_id", "version", "content_hash"],
)
def test_should_raise_validation_error_when_required_field_missing_content_saved(
    missing_field,
):
    kwargs = _valid_content_saved_kwargs()
    del kwargs[missing_field]

    with pytest.raises(ValidationError):
        ContentSavedEvent(**kwargs)


def test_should_reject_version_below_minimum_content_saved():
    kwargs = _valid_content_saved_kwargs()
    kwargs["version"] = 0

    with pytest.raises(ValidationError):
        ContentSavedEvent(**kwargs)


def test_should_be_frozen_content_saved_event():
    event = ContentSavedEvent(**_valid_content_saved_kwargs())

    with pytest.raises(ValidationError):
        event.version = 2


def test_should_default_occurred_at_when_omitted_content_saved():
    kwargs = _valid_content_saved_kwargs()
    assert "occurred_at" not in kwargs

    event = ContentSavedEvent(**kwargs)

    assert isinstance(event.occurred_at, datetime)


def test_should_accept_optional_tenant_id_content_saved():
    kwargs = _valid_content_saved_kwargs()
    tenant = uuid4()
    kwargs["tenant_id"] = tenant

    event = ContentSavedEvent(**kwargs)

    assert event.tenant_id == tenant


# ---------------------------------------------------------------------------
# ContentRelationAddedEvent
# ---------------------------------------------------------------------------


def _valid_content_relation_kwargs() -> dict:
    return dict(
        relation_id=uuid4(),
        source_item=uuid4(),
        target_ref="art-456",
        relation_type="references",
    )


def test_should_instantiate_content_relation_added_event_with_valid_data():
    event = ContentRelationAddedEvent(**_valid_content_relation_kwargs())

    assert isinstance(event.relation_id, UUID)
    assert isinstance(event.source_item, UUID)
    assert event.target_ref == "art-456"
    assert event.relation_type == "references"
    assert event.tenant_id is None
    assert isinstance(event.occurred_at, datetime)


@pytest.mark.parametrize(
    "missing_field",
    ["relation_id", "source_item", "target_ref", "relation_type"],
)
def test_should_raise_validation_error_when_required_field_missing_relation_added(
    missing_field,
):
    kwargs = _valid_content_relation_kwargs()
    del kwargs[missing_field]

    with pytest.raises(ValidationError):
        ContentRelationAddedEvent(**kwargs)


def test_should_be_frozen_content_relation_added_event():
    event = ContentRelationAddedEvent(**_valid_content_relation_kwargs())

    with pytest.raises(ValidationError):
        event.target_ref = "art-999"


# ---------------------------------------------------------------------------
# ContentVersionBumpedEvent
# ---------------------------------------------------------------------------


def _valid_content_version_bumped_kwargs() -> dict:
    return dict(
        item_id=uuid4(),
        source_svc="content-store",
        source_id="art-123",
        old_version=1,
        new_version=2,
    )


def test_should_instantiate_content_version_bumped_event_with_valid_data():
    event = ContentVersionBumpedEvent(**_valid_content_version_bumped_kwargs())

    assert isinstance(event.item_id, UUID)
    assert event.source_svc == "content-store"
    assert event.source_id == "art-123"
    assert event.old_version == 1
    assert event.new_version == 2
    assert event.tenant_id is None
    assert isinstance(event.occurred_at, datetime)


@pytest.mark.parametrize(
    "missing_field",
    ["item_id", "source_svc", "source_id", "old_version", "new_version"],
)
def test_should_raise_validation_error_when_required_field_missing_version_bumped(
    missing_field,
):
    kwargs = _valid_content_version_bumped_kwargs()
    del kwargs[missing_field]

    with pytest.raises(ValidationError):
        ContentVersionBumpedEvent(**kwargs)


def test_should_reject_new_version_below_minimum_version_bumped():
    kwargs = _valid_content_version_bumped_kwargs()
    kwargs["new_version"] = 1  # ge=2

    with pytest.raises(ValidationError):
        ContentVersionBumpedEvent(**kwargs)


def test_should_reject_old_version_below_minimum_version_bumped():
    kwargs = _valid_content_version_bumped_kwargs()
    kwargs["old_version"] = 0  # ge=1

    with pytest.raises(ValidationError):
        ContentVersionBumpedEvent(**kwargs)


def test_should_be_frozen_content_version_bumped_event():
    event = ContentVersionBumpedEvent(**_valid_content_version_bumped_kwargs())

    with pytest.raises(ValidationError):
        event.new_version = 3


# ---------------------------------------------------------------------------
# db_views.py / task_schemas.py — Basistyp-Kontrakt (aktuell leere Templates)
# ---------------------------------------------------------------------------


def test_should_expose_view_contracts_as_dict():
    assert isinstance(db_views.VIEW_CONTRACTS, dict)


def test_should_expose_task_schemas_as_dict():
    assert isinstance(task_schemas.TASK_SCHEMAS, dict)
