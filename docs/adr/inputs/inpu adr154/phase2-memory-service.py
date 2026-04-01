"""
orchestrator_mcp/services/memory_service.py

MemoryService — Service-Layer für AgentMemoryEntry CRUD + pgvector-Suche.

Platform Standards:
  - Business-Logik ausschließlich hier (nie in Views/Tasks)
  - Pydantic v2 Schema-Validation vor Write
  - read_secret() für alle Credentials
  - asgiref.async_to_sync für Django-ASGI-Kompatibilität
  - transaction.on_commit() für Celery-Dispatch
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from django.db import transaction
from django.utils import timezone as dj_timezone
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic v2 Schemas (R-07: Schema-Validation vor Write)
# ---------------------------------------------------------------------------

class ErrorPatternData(BaseModel):
    symptom: str = Field(..., min_length=10, max_length=2000)
    root_cause: str = Field(..., min_length=10, max_length=2000)
    fix: str = Field(..., min_length=10, max_length=2000)
    prevention: str = Field(..., min_length=10, max_length=2000)
    file_path: str | None = None
    line_hint: int | None = None


class LessonLearnedData(BaseModel):
    what_happened: str = Field(..., min_length=10)
    what_to_do_instead: str = Field(..., min_length=10)
    applies_to: list[str] = Field(default_factory=list)


class MemoryEntrySchema(BaseModel):
    """Gate-Schema vor jedem agent_memory_upsert (R-07)."""

    entry_key: str = Field(..., min_length=5, max_length=512)
    entry_type: str = Field(...)
    title: str = Field(..., min_length=5, max_length=512)
    content: str = Field(..., min_length=20)
    tags: list[str] = Field(default_factory=list, max_length=20)
    repo: str = Field(default="", max_length=256)
    structured_data: dict[str, Any] | None = None
    tenant_id: int = Field(..., gt=0)

    @field_validator("entry_type")
    @classmethod
    def validate_entry_type(cls, v: str) -> str:
        from orchestrator_mcp.models import EntryType
        valid = [t.value for t in EntryType]
        if v not in valid:
            raise ValueError(f"entry_type muss einer von {valid} sein, nicht '{v}'")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        return [tag.lower().strip() for tag in v if tag.strip()]

    @model_validator(mode="after")
    def validate_structured_data_matches_type(self) -> "MemoryEntrySchema":
        if self.entry_type == "error_pattern" and self.structured_data:
            ErrorPatternData(**self.structured_data)
        elif self.entry_type == "lesson_learned" and self.structured_data:
            LessonLearnedData(**self.structured_data)
        return self


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def build_error_pattern_key(repo: str, error_type: str, file_path: str = "") -> str:
    """
    Deterministischer Hash für Error-Pattern-Keys (R-09).

    Format: error_pattern:<repo>:<hash16>
    Hash-Input: repo + error_type + file_path (normalisiert)
    """
    normalized = f"{repo.lower().strip()}:{error_type.lower().strip()}:{file_path.strip()}"
    hash16 = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"error_pattern:{repo}:{hash16}"


def build_session_key(repo: str, date: datetime | None = None) -> str:
    """Format: session:<date_str>:<repo>"""
    d = date or dj_timezone.now()
    return f"session:{d.strftime('%Y-%m-%d')}:{repo}"


# ---------------------------------------------------------------------------
# MemoryService
# ---------------------------------------------------------------------------

class MemoryService:
    """
    Service-Layer für AgentMemoryEntry.

    Alle Methoden sind sync (Django-kompatibel).
    Für FastMCP async-Kontext: asgiref.sync_to_async(MemoryService.upsert_entry)(...)
    """

    DEFAULT_TENANT_ID = 1  # IIL-Plattform: Tenant 1 = Internal

    @staticmethod
    def upsert_entry(data: dict[str, Any]) -> "AgentMemoryEntry":  # noqa: F821
        """
        Erstellt oder aktualisiert einen Memory-Eintrag.

        Pydantic-Validation als Gate (R-07).
        Embedding wird asynchron via Celery-Task generiert.
        """
        from orchestrator_mcp.models import AgentMemoryEntry

        # Schema-Validation
        schema = MemoryEntrySchema(**data)

        with transaction.atomic():
            entry, created = AgentMemoryEntry.all_objects.get_or_create(
                tenant_id=schema.tenant_id,
                entry_key=schema.entry_key,
                defaults={
                    "entry_type": schema.entry_type,
                    "title": schema.title,
                    "content": schema.content,
                    "tags": schema.tags,
                    "repo": schema.repo,
                    "structured_data": schema.structured_data,
                    "relevance_score": 1.0,
                    "deleted_at": None,
                },
            )
            if not created:
                # Reaktivieren falls soft-deleted
                entry.deleted_at = None
                entry.entry_type = schema.entry_type
                entry.title = schema.title
                entry.content = schema.content
                entry.tags = list(set(entry.tags + schema.tags))
                entry.structured_data = schema.structured_data or entry.structured_data
                entry.relevance_score = min(1.0, entry.relevance_score + 0.1)
                entry.save(update_fields=[
                    "deleted_at", "entry_type", "title", "content",
                    "tags", "structured_data", "relevance_score", "updated_at",
                ])

            # Embedding-Generierung via Celery (transaction.on_commit → R-Standard)
            transaction.on_commit(
                lambda eid=entry.id: _dispatch_embedding_task(eid)
            )

        action = "created" if created else "updated"
        logger.info(
            "MemoryService.upsert_entry: %s entry_key=%s type=%s repo=%s",
            action, schema.entry_key, schema.entry_type, schema.repo,
        )
        return entry

    @staticmethod
    def search_similar(
        query: str,
        tenant_id: int,
        entry_type: str | None = None,
        repo: str | None = None,
        top_k: int = 5,
        min_relevance: float = 0.3,
    ) -> list[dict[str, Any]]:
        """
        Semantische Suche via pgvector cosine-distance.

        Fallback auf Full-Text-Search wenn kein Embedding verfügbar.
        """
        from orchestrator_mcp.models import AgentMemoryEntry

        qs = AgentMemoryEntry.objects.filter(tenant_id=tenant_id)
        if entry_type:
            qs = qs.filter(entry_type=entry_type)
        if repo:
            qs = qs.filter(models.Q(repo=repo) | models.Q(repo=""))

        # Prüfen ob Embedding für Query verfügbar
        query_embedding = _get_embedding_sync(query)
        if query_embedding is not None:
            # pgvector cosine similarity
            from pgvector.django import CosineDistance
            results = (
                qs.filter(embedding__isnull=False)
                .annotate(similarity=1 - CosineDistance("embedding", query_embedding))
                .filter(similarity__gte=min_relevance)
                .order_by("-similarity", "-relevance_score")[:top_k]
            )
        else:
            # Fallback: Full-Text via icontains
            logger.warning("MemoryService.search_similar: kein Embedding — Full-Text Fallback")
            results = qs.filter(
                models.Q(title__icontains=query) | models.Q(content__icontains=query)
            ).order_by("-relevance_score", "-updated_at")[:top_k]

        # Access-Count erhöhen (bulk, kein N+1)
        ids = [r.id for r in results]
        if ids:
            AgentMemoryEntry.objects.filter(id__in=ids).update(
                access_count=models.F("access_count") + 1,
                last_accessed_at=dj_timezone.now(),
            )

        return [
            {
                "public_id": str(r.public_id),
                "entry_type": r.entry_type,
                "title": r.title,
                "content": r.content[:800],  # Truncate für MCP-Response
                "tags": r.tags,
                "repo": r.repo,
                "relevance_score": r.relevance_score,
                "updated_at": r.updated_at.isoformat(),
                "structured_data": r.structured_data,
            }
            for r in results
        ]

    @staticmethod
    def soft_delete(entry_key: str, tenant_id: int) -> bool:
        from orchestrator_mcp.models import AgentMemoryEntry
        updated = AgentMemoryEntry.objects.filter(
            tenant_id=tenant_id, entry_key=entry_key
        ).update(deleted_at=dj_timezone.now())
        return updated > 0

    @staticmethod
    def decay_old_entries(tenant_id: int, decay_factor: float = 0.95) -> int:
        """
        Reduziert relevance_score für alte Einträge (Temporal Decay, R-17).
        Einträge mit relevance_score < 0.1 werden soft-deleted.

        Aufruf: Celery-Beat-Task, täglich.
        """
        import django.db.models as dj_models
        from orchestrator_mcp.models import AgentMemoryEntry
        from django.utils import timezone as tz

        with transaction.atomic():
            # Decay anwenden
            updated = AgentMemoryEntry.objects.filter(
                tenant_id=tenant_id,
                access_count=0,  # nur nie-gelesene Einträge
                updated_at__lt=tz.now() - dj_models.fields.datetime.timedelta(days=30),
            ).update(
                relevance_score=dj_models.ExpressionWrapper(
                    dj_models.F("relevance_score") * decay_factor,
                    output_field=dj_models.FloatField(),
                )
            )

            # Veraltete archivieren
            archived = AgentMemoryEntry.objects.filter(
                tenant_id=tenant_id,
                relevance_score__lt=0.1,
            ).update(deleted_at=tz.now())

        logger.info(
            "MemoryService.decay: tenant=%s decayed=%s archived=%s",
            tenant_id, updated, archived,
        )
        return archived


# ---------------------------------------------------------------------------
# Private Helpers
# ---------------------------------------------------------------------------

def _dispatch_embedding_task(entry_id: int) -> None:
    """Dispatch Celery-Task für Embedding-Generierung."""
    try:
        from orchestrator_mcp.tasks import generate_memory_embedding
        generate_memory_embedding.delay(entry_id)
    except Exception:
        logger.exception("Fehler beim Dispatchen von generate_memory_embedding(%s)", entry_id)


def _get_embedding_sync(text: str) -> list[float] | None:
    """
    Generiert OpenAI-Embedding synchron (für Suche).
    Nutzt read_secret() für API-Key (Platform-Standard).
    """
    try:
        from platform_context.secrets import read_secret  # noqa: PLC0415
        import openai  # noqa: PLC0415
        client = openai.OpenAI(api_key=read_secret("OPENAI_API_KEY"))
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000],  # Token-Limit
        )
        return response.data[0].embedding
    except Exception:
        logger.warning("_get_embedding_sync: Embedding-Generierung fehlgeschlagen", exc_info=True)
        return None


# Import am Ende um zirkuläre Imports zu vermeiden
import django.db.models as models  # noqa: E402
