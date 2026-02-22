"""Event contracts for content_store cross-service events (ADR-062 Phase 1).

These Pydantic models define the payload shape for Celery tasks and
any future event bus messages related to content persistence.

Consumers:
    - agent-team  (orchestrator_mcp)
    - bfagent     (apps/bfagent/tasks.py)
    - travel-beat (apps/stories/tasks.py)
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContentSavedEvent(BaseModel):
    """Emitted after a ContentItem is successfully persisted."""

    model_config = ConfigDict(frozen=True)

    item_id: UUID = Field(description="UUID of the persisted ContentItem")
    source_svc: str = Field(description="Originating service")
    source_type: str = Field(description="Content category")
    source_id: str = Field(description="Service-local identifier")
    tenant_id: UUID | None = Field(default=None)
    version: int = Field(ge=1)
    content_hash: str = Field(description="SHA-256 of content")
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ContentRelationAddedEvent(BaseModel):
    """Emitted after a ContentRelation is successfully persisted."""

    model_config = ConfigDict(frozen=True)

    relation_id: UUID
    source_item: UUID
    target_ref: str
    relation_type: str
    tenant_id: UUID | None = Field(default=None)
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ContentVersionBumpedEvent(BaseModel):
    """Emitted when a new version of an existing item is saved."""

    model_config = ConfigDict(frozen=True)

    item_id: UUID
    source_svc: str
    source_id: str
    old_version: int = Field(ge=1)
    new_version: int = Field(ge=2)
    tenant_id: UUID | None = Field(default=None)
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
