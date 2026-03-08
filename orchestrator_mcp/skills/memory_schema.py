"""
AGENT_MEMORY.md Schema — Pydantic v2 Modelle für den persistenten Kontext-Store.

Format: JSON-Fences in Markdown (strukturiert + parserbar).
Jeder Entry hat expires_at (TTL) — abgelaufene Entries werden via gc() entfernt.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EntryType(str, Enum):
    SOLVED_PROBLEM = "solved_problem"
    REPO_CONTEXT   = "repo_context"
    OPEN_TASK      = "open_task"
    AGENT_DECISION = "agent_decision"
    ERROR_PATTERN  = "error_pattern"


class MemoryEntry(BaseModel):
    """Einzelner strukturierter Eintrag im Agent Memory Store."""
    model_config = ConfigDict(extra="forbid")

    entry_id: str = Field(
        ...,
        description="Eindeutige ID: T-001, R-coach-hub, D-2026-03-08-001",
        pattern=r'^[A-Z][A-Z0-9\-]+$',
    )
    entry_type: EntryType
    title: str = Field(..., min_length=5, max_length=200)
    content: str = Field(..., min_length=1)
    agent: str = Field(..., description="Schreibender Agent")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30),
        description="TTL: Entry wird nach diesem Datum via gc() entfernt",
    )
    tags: list[str] = Field(default_factory=list)
    related_entries: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    def touch(self) -> None:
        """updated_at aktualisieren (in-place)."""
        self.updated_at = datetime.now(timezone.utc)


class MemoryStore(BaseModel):
    """Vollständiger Agent Memory Store — wird als AGENT_MEMORY.md serialisiert."""
    model_config = ConfigDict(extra="forbid")

    version: str = "1.0"
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    last_updated_by: str = "unknown-agent"
    entries: list[MemoryEntry] = Field(default_factory=list)

    def get(self, entry_id: str) -> MemoryEntry | None:
        for entry in self.entries:
            if entry.entry_id == entry_id:
                return entry
        return None

    def upsert(self, entry: MemoryEntry, agent: str = "unknown-agent") -> None:
        """Entry hinzufügen oder aktualisieren."""
        existing = self.get(entry.entry_id)
        if existing:
            idx = self.entries.index(existing)
            self.entries[idx] = entry
            self.entries[idx].touch()
        else:
            self.entries.append(entry)
        self.last_updated = datetime.now(timezone.utc)
        self.last_updated_by = agent

    def gc(self) -> int:
        """Abgelaufene Entries entfernen. Gibt Anzahl entfernter Entries zurück."""
        before = len(self.entries)
        self.entries = [e for e in self.entries if not e.is_expired]
        removed = before - len(self.entries)
        if removed:
            self.last_updated = datetime.now(timezone.utc)
            self.last_updated_by = "memory-gc"
        return removed

    def by_type(self, entry_type: EntryType) -> list[MemoryEntry]:
        return [e for e in self.entries if e.entry_type == entry_type]

    def by_tag(self, tag: str) -> list[MemoryEntry]:
        return [e for e in self.entries if tag in e.tags]
