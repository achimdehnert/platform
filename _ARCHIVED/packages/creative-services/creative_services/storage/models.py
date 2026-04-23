"""Pydantic models for content_store schema (ADR-062 Phase 1)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


SourceService = Literal["agent-team", "bfagent", "travel-beat", "creative-services"]

SourceType = Literal[
    "task_plan",
    "impact_report",
    "code_review",
    "adr_analysis",
    "chapter",
    "story",
    "scene",
    "character_description",
    "draft",
    "draft_variant",
    "llm_execution",
    "prompt_result",
]

RelationType = Literal[
    "implements",
    "references",
    "derived_from",
    "tested_by",
    "appears_in",
    "located_in",
]

_TENANT_REQUIRED_SERVICES: frozenset[str] = frozenset({"travel-beat"})


class ContentItem(BaseModel):
    """Single persisted content artifact."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    source_svc: SourceService = Field(description="Originating service")
    source_type: SourceType = Field(description="Content category")
    source_id: str = Field(description="Service-local identifier for the originating object")
    tenant_id: UUID | None = Field(
        default=None,
        description="NULL = platform-wide (Agent-Team). Required for tenant-scoped services.",
    )
    content: str = Field(description="Raw text content")
    content_hash: str = Field(description="SHA-256 of content, used for deduplication")
    prompt_key: str | None = Field(default=None, description="Prompt template key used")
    model_used: str = Field(description="LLM model identifier, e.g. 'gpt-4o-mini'")
    version: int = Field(default=1, ge=1, description="Version counter, incremented on update")
    parent_id: UUID | None = Field(default=None, description="Previous version UUID")
    tags: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("tenant_id", mode="after")
    @classmethod
    def _validate_tenant_required(cls, v: UUID | None, info: Any) -> UUID | None:
        svc = info.data.get("source_svc")
        if svc in _TENANT_REQUIRED_SERVICES and v is None:
            raise ValueError(f"tenant_id is required for source_svc='{svc}'")
        return v

    @field_validator("content_hash", mode="before")
    @classmethod
    def _validate_hash_format(cls, v: str) -> str:
        if len(v) != 64:
            raise ValueError("content_hash must be a 64-char SHA-256 hex string")
        return v


class ContentRelation(BaseModel):
    """Directed relation from a ContentItem to any platform entity."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    source_item: UUID = Field(description="FK to content_store.items")
    target_ref: str = Field(
        description="Format: '<type>:<id>', e.g. 'adr:ADR-059' or 'file:apps/trips/models.py'"
    )
    relation_type: RelationType
    tenant_id: UUID | None = Field(default=None)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("target_ref", mode="after")
    @classmethod
    def _validate_target_ref_format(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError("target_ref must follow '<type>:<id>' format, e.g. 'adr:ADR-059'")
        return v


def sha256(text: str) -> str:
    """Compute SHA-256 hex digest for use as content_hash."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
