# Review & Implementierung: ADR-113 — Telegram Gateway + pgvector Memory Store

| | |
|---|---|
| **Reviewer** | Principal IT-Architekt / Senior Python-Entwickler |
| **Dokument** | ADR-113 (2026-03-08) |
| **Stack** | Django <6.0, PostgreSQL+pgvector, Celery, mcp-hub, iilgmbh/platform |
| **Review-Datum** | 2026-03-08 |
| **Ergebnis** | CHANGES REQUIRED — 4 Blocker, 5 Kritisch, 6 Hoch |

---

## 1. Review-Tabelle

### 🔴 BLOCKER

| # | Befund | Severity | Problem | Korrektur |
|---|---|---|---|---|
| B1 | `TEXT PRIMARY KEY` verletzt Platform-Standard | BLOCKER | `id TEXT PRIMARY KEY` — Platform-Standard ist `BigAutoField PK + public_id UUIDField`. `TEXT PRIMARY KEY` verhindert ORM-Integration, bricht `platform_context` Multi-Tenancy und ist inkompatibel mit Django Migrations. | `id = models.BigAutoField(primary_key=True)` + `public_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)` + `entry_key = models.CharField(max_length=64)` für den menschenlesbaren Key. |
| B2 | Kein `tenant_id` auf `AgentMemoryEntry` | BLOCKER | Platform-Standard: `tenant_id = BigIntegerField(db_index=True)` auf allen User-Data-Modellen. Fehlt → Memory-Einträge sind Org-weit sichtbar, kein Isolation zwischen Tenants. | `tenant_id = models.BigIntegerField(db_index=True)` + `UniqueConstraint(fields=["tenant_id", "entry_key"])`. |
| B3 | `python-telegram-bot` async + Django ASGI | BLOCKER | `python-telegram-bot>=21` ist vollständig async. Im Django-ASGI-Kontext darf niemals `asyncio.run()` aufgerufen werden (Platform-Standard). Management Command `run_telegram_bot` würde `asyncio.run(application.run_polling())` aufrufen — explizit verboten. | `asgiref.async_to_sync` + `Application.run_polling()` in separatem Thread via `threading.Thread`. Oder: dedizierter Uvicorn-Worker mit eigenem Event-Loop. Gezeigt in 3.3. |
| B4 | Kein `deleted_at` Soft-Delete | BLOCKER | Platform-Standard auf allen User-Data-Modellen. `AgentMemoryEntry` hat kein `deleted_at` — Hard-Delete verletzt Audit-Anforderungen und ADR-112-Kompatibilität. | `deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)` + Custom Manager `ActiveMemoryManager`. |

### 🔴 KRITISCH

| # | Befund | Severity | Problem | Korrektur |
|---|---|---|---|---|
| C1 | Telegram `ALLOWED_USER_IDS` als Env-String unsicher | KRITISCH | `TELEGRAM_ALLOWED_USER_IDS` als komma-getrennte Env-Var: `"123456,789012"` — trivial zu manipulieren, kein Typ-Check, keine Validierung. Integer-IDs als String-Vergleich → `" 123456"` (Leerzeichen) passiert Auth. | `TELEGRAM_ALLOWED_USER_IDS: list[int]` via Django Settings mit `[int(x.strip()) for x in os.environ.get(..., "").split(",") if x.strip()]`. Check: `update.effective_user.id in settings.TELEGRAM_ALLOWED_USER_IDS`. |
| C2 | OpenAI Embedding bei jedem Upsert — kein Caching | KRITISCH | Jeder `agent_memory_upsert` Call triggert einen OpenAI API-Call. Bei Batch-Operations (Repo-Scan, Session-Start) → N API-Calls parallel → Rate-Limit + $-Kosten skalieren unkontrolliert. | Content-Hash-basiertes Caching: Embedding nur neu berechnen wenn `sha256(content)` sich geändert hat. `content_hash = models.CharField(max_length=64)` speichert den Hash. |
| C3 | `ivfflat` Index ohne `lists` Tuning | KRITISCH | `WITH (lists = 100)` ist ein blindes Default. `lists` sollte `sqrt(row_count)` entsprechen. Bei <1000 Entries ist `lists=100` kontraproduktiv (mehr Lists als Rows). Bei >1M Entries zu niedrig. | `lists = 50` als sicherer Start (für <2500 Entries optimal). Kommentar im Migration-File mit Tuning-Anleitung. Alternativ: `hnsw` Index (besser für kleine Datasets, kein Rebuild nötig). |
| C4 | Kein Rate-Limiting auf Telegram Bot Commands | KRITISCH | `/task` kann beliebig oft aufgerufen werden → jeder Call triggert GitHub Actions Workflow → Actions-Budget erschöpft, unbegrenzte Agent-Kosten. | Pro User: max 10 Tasks/Stunde via Django Cache (`django.core.cache`). `/deploy` max 2/Stunde. Überschreitung → Bot antwortet mit Cooldown-Zeit. |
| C5 | `unique_together` im Pseudo-Schema statt `UniqueConstraint` | KRITISCH | ADR nennt kein explizites Unique-Constraint — aber die implizite Annahme `entry_id` ist unique verletzt Platform-Standard. `unique_together` ist deprecated seit Django 4.2. | `UniqueConstraint(fields=["tenant_id", "entry_key"], name="unique_memory_entry_per_tenant")` im Meta. |

### 🟠 HOCH

| # | Befund | Severity | Problem | Korrektur |
|---|---|---|---|---|
| H1 | Kein i18n auf Bot-Responses | HOCH | Platform-Standard: `_()` ab Tag 1. Alle Telegram-Response-Strings sind Hard-coded Deutsch/Englisch. | `from django.utils.translation import gettext_lazy as _` auf alle Bot-Response-Strings. Locale: `de` als Default. |
| H2 | `half_life_days` ohne per-type Defaults im Schema | HOCH | ADR nennt es als offene Frage — aber im Model-Code muss das Default entschieden sein bevor Migration läuft. Nachträgliches Ändern ist eine neue Migration. | `HALF_LIFE_DEFAULTS = {"open_task": 14, "decision": 180, "lesson_learned": 365, "repo_context": 7, "error_pattern": 90}` als Model-Konstante. `save()` Override setzt Default wenn nicht explizit gesetzt. |
| H3 | Kein Connection-Pooling für pgvector Queries | HOCH | Embedding-Queries via ORM ohne explizites `select_related`/`defer` laden alle Felder inkl. dem `vector(1536)` Blob. Bei Listen-Queries: N × 6KB = teuer. | `defer("embedding")` auf List-Queries. `values("id", "title", "content", "final_score")` für Retrieval-Results. Nur bei explizitem `get_embedding()` Call das Feld laden. |
| H4 | `dispatcher.py` ruft GitHub API direkt auf — kein Retry | HOCH | GitHub API Calls in `handlers.py` → `dispatcher.py` ohne Retry-Logik. Bei transientem 500er: Bot antwortet mit Fehler, Task nicht erstellt, User weiß nicht ob Task pending ist. | `tenacity` mit `retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))`. |
| H5 | `docker-compose.yml` ohne Health-Check für telegram-bot | HOCH | Container startet, aber Long-Polling kann silently sterben (Network-Timeout, Telegram-Server-Issue). Kein Health-Check → Docker denkt Service ist gesund. | `healthcheck: test: ["CMD", "python", "-c", "import requests; requests.get('https://api.telegram.org', timeout=5)"]` + `restart: unless-stopped`. |
| H6 | Migration Script ADR-112 → ADR-113 fehlt komplett | HOCH | ADR sagt "Migration-Script (MD → pgvector)" ist offen — aber ohne dieses Script ist kein sauberer Cutover möglich. Bestehende `AGENT_MEMORY.md` Entries gehen verloren. | `management/commands/migrate_agent_memory.py`: liest `AGENT_MEMORY.md`, erstellt Embeddings, inserted in pgvector. Idempotent via `get_or_create(entry_key=...)`. |

### 🟡 MEDIUM

| # | Befund | Severity | Problem | Korrektur |
|---|---|---|---|---|
| M1 | `set -euo pipefail` fehlt im Telegram-Notify Script | MEDIUM | Platform-Standard für alle Shell-Skripte. | Erste Zeile jedes `run:` Blocks. |
| M2 | Kein Django Admin für `AgentMemoryEntry` | MEDIUM | ADR erwähnt `admin.py` aber ohne Implementierung. Ohne Admin kein manuelles Eingreifen ohne DB-Konsole. | `ModelAdmin` mit `list_display`, `search_fields`, `list_filter` — in 3.5 gezeigt. |
| M3 | Embedding-Provider nicht final entschieden | MEDIUM | ADR lässt OpenAI vs. Ollama offen. Code muss aber eine Entscheidung treffen. | `EMBEDDING_PROVIDER = "openai"` als Setting, `OllamaEmbeddingClient` als Drop-in Alternative mit identischem Interface. Feature-Flag: `SKILL_EMBEDDING_PROVIDER`. |
| M4 | Kein Prometheus-Metric für Memory-Queries | MEDIUM | Ohne Observability: wie lange dauert eine pgvector Similarity-Search? Wann ist der Index ineffizient? | `django-prometheus`: `memory_query_duration_seconds` Histogram + `memory_entries_total` Gauge. |

---

## 2. Implementierungsplan

```
Phase 1 — Django App: agent_memory (2h)
├── apps/agent_memory/models.py          ← AgentMemoryEntry (Platform-Standards)
├── apps/agent_memory/managers.py        ← ActiveMemoryManager (Soft-Delete)
├── apps/agent_memory/services.py        ← upsert(), query(), semantic_search(), gc()
├── apps/agent_memory/embeddings.py      ← EmbeddingClient (OpenAI + Ollama)
├── apps/agent_memory/admin.py           ← Django Admin
└── apps/agent_memory/migrations/
    └── 0001_initial.py                  ← HNSW Index, pgvector Extension

Phase 2 — Django App: telegram_gateway (2h)
├── apps/telegram_gateway/bot.py         ← Application Setup (async-safe)
├── apps/telegram_gateway/handlers.py    ← Command Handler mit Rate-Limit
├── apps/telegram_gateway/dispatcher.py  ← GitHub API (mit tenacity Retry)
├── apps/telegram_gateway/formatter.py   ← Response-Formatting
└── apps/telegram_gateway/management/
    └── commands/run_telegram_bot.py     ← Management Command (threading-safe)

Phase 3 — orchestrator_mcp v3.3 (1h)
├── orchestrator_mcp/skills/session_memory.py  ← pgvector Backend
└── orchestrator_mcp/agent_team/mcp_server.py  ← Neue Tools registrieren

Phase 4 — Migration + GitHub Actions (1h)
├── apps/agent_memory/management/
│   └── commands/migrate_agent_memory.py ← ADR-112 MD → pgvector
└── .github/workflows/
    ├── agent-task-dispatch.yml           ← +Telegram Notification
    └── agent-memory-gc.yml               ← pgvector GC statt MD-GC
```

**Feature-Flags:**
- `SKILL_MEMORY_BACKEND=pgvector|markdown` (default: `pgvector`)
- `SKILL_EMBEDDING_PROVIDER=openai|ollama` (default: `openai`)
- `TELEGRAM_GATEWAY_ENABLED=true|false`

---

## 3. Produktionsreife Implementierung

### 3.1 `apps/agent_memory/models.py`

```python
"""
AgentMemoryEntry — Persistent Memory Store mit pgvector Embeddings.

Platform-Standards:
- BigAutoField PK + public_id UUIDField
- tenant_id = BigIntegerField(db_index=True)
- deleted_at Soft-Delete
- UniqueConstraint (nicht unique_together)
- i18n via gettext_lazy
"""
from __future__ import annotations

import hashlib
import uuid
from enum import Enum

from django.db import models
from django.utils.translation import gettext_lazy as _
from pgvector.django import CosineDistance, HnswIndex, VectorField


class EntryType(models.TextChoices):
    OPEN_TASK      = "open_task",      _("Offener Task")
    DECISION       = "decision",       _("Entscheidung")
    REPO_CONTEXT   = "repo_context",   _("Repo-Kontext")
    LESSON_LEARNED = "lesson_learned", _("Lesson Learned")
    ERROR_PATTERN  = "error_pattern",  _("Fehler-Muster")
    AGENT_HANDOFF  = "agent_handoff",  _("Agent Handoff")


# Halbwertszeit in Tagen pro Entry-Typ (Platform-Entscheidung, nicht offene Frage)
HALF_LIFE_DEFAULTS: dict[str, int] = {
    EntryType.OPEN_TASK:      14,
    EntryType.DECISION:      180,
    EntryType.REPO_CONTEXT:    7,
    EntryType.LESSON_LEARNED: 365,
    EntryType.ERROR_PATTERN:   90,
    EntryType.AGENT_HANDOFF:   30,
}


class ActiveMemoryManager(models.Manager):
    """Manager der soft-gelöschte Entries ausblendet."""
    def get_queryset(self) -> models.QuerySet:
        return super().get_queryset().filter(deleted_at__isnull=True)


class AgentMemoryEntry(models.Model):
    """
    Persistenter Agent-Memory-Eintrag mit pgvector Embedding.

    Jeder Entry gehört zu einem Tenant (tenant_id) und hat einen
    menschenlesbaren Key (entry_key) der pro Tenant eindeutig ist.

    Temporal Decay via SQL (kein hard expires_at):
        score_final = semantic_similarity × e^(-ln(2)/half_life_days × age_days)
    """

    # ── Platform-Standard PKs ────────────────────────────────────────────────
    id        = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(
        default=uuid.uuid4, unique=True, db_index=True, editable=False,
        verbose_name=_("Public ID"),
    )

    # ── Multi-Tenancy ────────────────────────────────────────────────────────
    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Tenant ID"),
        help_text=_("Platform tenant_id — kein FK, kein JOIN"),
    )

    # ── Entry-Daten ──────────────────────────────────────────────────────────
    entry_key = models.CharField(
        max_length=64,
        verbose_name=_("Entry Key"),
        help_text=_("Menschenlesbarer Key, z.B. T-001, R-COACH-HUB"),
    )
    entry_type = models.CharField(
        max_length=32,
        choices=EntryType.choices,
        db_index=True,
        verbose_name=_("Typ"),
    )
    title   = models.CharField(max_length=200, verbose_name=_("Titel"))
    content = models.TextField(verbose_name=_("Inhalt"))
    agent   = models.CharField(
        max_length=64,
        verbose_name=_("Agent"),
        help_text=_("Name des schreibenden Agents"),
    )

    # ── Temporal Decay ───────────────────────────────────────────────────────
    half_life_days = models.PositiveSmallIntegerField(
        default=30,
        verbose_name=_("Halbwertszeit (Tage)"),
        help_text=_("Nach N Tagen hat der Entry noch 50% seines Scores"),
    )

    # ── Embedding ────────────────────────────────────────────────────────────
    embedding = VectorField(
        dimensions=1536,
        null=True,
        blank=True,
        verbose_name=_("Embedding"),
        help_text=_("OpenAI text-embedding-3-small (1536 dims)"),
    )
    content_hash = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_("Content Hash"),
        help_text=_("SHA-256 des Contents — Embedding nur neu berechnen wenn Hash geändert"),
    )

    # ── Metadaten ────────────────────────────────────────────────────────────
    tags         = models.JSONField(default=list, verbose_name=_("Tags"))
    related_ids  = models.JSONField(default=list, verbose_name=_("Verwandte Entries"))
    metadata     = models.JSONField(default=dict, verbose_name=_("Metadaten"))

    # ── Timestamps + Soft-Delete ─────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Erstellt am"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Aktualisiert am"))
    deleted_at = models.DateTimeField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Gelöscht am"),
        help_text=_("Soft-Delete: gesetzt statt hard-delete"),
    )

    # ── Managers ─────────────────────────────────────────────────────────────
    objects     = ActiveMemoryManager()
    all_objects = models.Manager()  # inkl. soft-deleted (für Admin/Audit)

    class Meta:
        verbose_name        = _("Agent Memory Entry")
        verbose_name_plural = _("Agent Memory Entries")
        ordering            = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "entry_key"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_memory_entry_per_tenant",
            ),
        ]
        indexes = [
            # HNSW Index für kleine-mittlere Datasets (kein Rebuild nötig)
            HnswIndex(
                name="agent_memory_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
            # Full-Text Search (Hybrid Retrieval)
            models.Index(fields=["tenant_id", "entry_type"], name="agent_memory_tenant_type_idx"),
            models.Index(fields=["tenant_id", "updated_at"], name="agent_memory_tenant_updated_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.entry_key} [{self.entry_type}] (tenant={self.tenant_id})"

    def save(self, *args, **kwargs) -> None:
        # half_life_days Default per entry_type setzen
        if not self.half_life_days or self.half_life_days == 30:
            self.half_life_days = HALF_LIFE_DEFAULTS.get(self.entry_type, 30)
        super().save(*args, **kwargs)

    @staticmethod
    def compute_content_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def needs_embedding_update(self) -> bool:
        """True wenn Embedding neu berechnet werden muss."""
        return self.compute_content_hash(self.content) != self.content_hash

    def soft_delete(self) -> None:
        """Soft-Delete: setzt deleted_at statt hard-delete."""
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])
```

---

### 3.2 `apps/agent_memory/services.py`

```python
"""
Agent Memory Service Layer.

Business-Logik ausschließlich hier — nie in Views, Tasks oder Handlers direkt.
Alle Public-Funktionen sind synchron (asgiref.async_to_sync für async Callers).
"""
from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.db.models import ExpressionWrapper, F, FloatField, QuerySet
from django.db.models.expressions import RawSQL

from .embeddings import get_embedding_client
from .models import AgentMemoryEntry, EntryType

log = logging.getLogger(__name__)


# ─── Temporal Decay SQL ───────────────────────────────────────────────────────

_DECAY_SQL = """
    exp(
        -0.693
        * EXTRACT(EPOCH FROM (NOW() - "agent_memory_agentmemoryentry"."updated_at"))
        / 86400.0
        / "agent_memory_agentmemoryentry"."half_life_days"
    )
"""


# ─── Public Service Functions ─────────────────────────────────────────────────

@transaction.atomic
def upsert_entry(
    *,
    tenant_id: int,
    entry_key: str,
    entry_type: str,
    title: str,
    content: str,
    agent: str,
    tags: list[str] | None = None,
    related_ids: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    half_life_days: int | None = None,
    compute_embedding: bool = True,
) -> AgentMemoryEntry:
    """
    Entry erstellen oder aktualisieren (upsert by entry_key + tenant_id).

    Embedding wird nur neu berechnet wenn Content sich geändert hat (content_hash).

    Args:
        tenant_id: Platform tenant_id
        entry_key: Menschenlesbarer Key (z.B. "T-001", "R-COACH-HUB")
        entry_type: EntryType Value
        title: Kurztitel
        content: Volltext-Inhalt (wird embedded)
        agent: Name des schreibenden Agents
        tags: Optional Liste von Tags
        related_ids: Optional Liste verwandter entry_keys
        metadata: Optional zusätzliche Metadaten
        half_life_days: Override für Halbwertszeit (default: per entry_type)
        compute_embedding: False = kein Embedding berechnen (z.B. für Tests)

    Returns:
        AgentMemoryEntry (neu oder aktualisiert)
    """
    content_hash = AgentMemoryEntry.compute_content_hash(content)

    entry, created = AgentMemoryEntry.all_objects.get_or_create(
        tenant_id=tenant_id,
        entry_key=entry_key,
        deleted_at__isnull=True,
        defaults={
            "entry_type":  entry_type,
            "title":       title,
            "content":     content,
            "agent":       agent,
            "tags":        tags or [],
            "related_ids": related_ids or [],
            "metadata":    metadata or {},
            "content_hash": content_hash,
        },
    )

    if not created:
        entry.title      = title
        entry.content    = content
        entry.agent      = agent
        entry.entry_type = entry_type
        if tags is not None:
            entry.tags = tags
        if related_ids is not None:
            entry.related_ids = related_ids
        if metadata is not None:
            entry.metadata = metadata

    if half_life_days is not None:
        entry.half_life_days = half_life_days

    # Embedding nur wenn Content geändert
    if compute_embedding and entry.needs_embedding_update():
        client = get_embedding_client()
        entry.embedding    = client.embed(content)
        entry.content_hash = content_hash
        log.info("Embedding berechnet für entry_key=%s", entry_key)
    elif not compute_embedding:
        entry.content_hash = content_hash

    entry.save()
    log.info(
        "Memory entry %s: %s (tenant=%s)",
        "erstellt" if created else "aktualisiert",
        entry_key,
        tenant_id,
    )
    return entry


def semantic_search(
    *,
    tenant_id: int,
    query: str,
    entry_type: str | None = None,
    tags: list[str] | None = None,
    limit: int = 10,
    min_score: float = 0.1,
) -> list[dict[str, Any]]:
    """
    Semantische Suche mit Temporal Decay.

    Kombiniert Cosine Similarity (pgvector) mit exponentiellem Decay.
    score_final = semantic_similarity × e^(-ln(2)/half_life_days × age_days)

    Args:
        tenant_id: Tenant-Isolation
        query: Suchanfrage (wird embedded)
        entry_type: Optional Filter auf EntryType
        tags: Optional Filter auf Tags (AND)
        limit: Max Ergebnisse (1-100)
        min_score: Minimum final_score (0.0-1.0)

    Returns:
        Liste von dicts mit id, entry_key, title, content_preview,
        entry_type, tags, semantic_score, decay_factor, final_score
    """
    if not 1 <= limit <= 100:
        raise ValueError(f"limit muss zwischen 1 und 100 liegen, nicht {limit}")

    client = get_embedding_client()
    query_embedding = client.embed(query)

    qs: QuerySet = (
        AgentMemoryEntry.objects
        .filter(tenant_id=tenant_id, embedding__isnull=False)
        .defer("embedding")  # Embedding-Blob nicht laden für Listing
    )

    if entry_type:
        qs = qs.filter(entry_type=entry_type)

    if tags:
        for tag in tags:
            qs = qs.filter(tags__contains=[tag])

    # Semantic Score via pgvector (1 - cosine_distance = cosine_similarity)
    qs = qs.annotate(
        semantic_score=ExpressionWrapper(
            1.0 - CosineDistance("embedding", query_embedding),
            output_field=FloatField(),
        ),
        decay_factor=RawSQL(_DECAY_SQL, [], output_field=FloatField()),
    ).annotate(
        final_score=ExpressionWrapper(
            F("semantic_score") * F("decay_factor"),
            output_field=FloatField(),
        ),
    ).filter(
        final_score__gte=min_score,
    ).order_by("-final_score")[:limit]

    return [
        {
            "id":              entry.public_id,
            "entry_key":       entry.entry_key,
            "title":           entry.title,
            "content_preview": entry.content[:300],
            "entry_type":      entry.entry_type,
            "tags":            entry.tags,
            "agent":           entry.agent,
            "updated_at":      entry.updated_at.isoformat(),
            "semantic_score":  round(entry.semantic_score or 0.0, 4),
            "decay_factor":    round(entry.decay_factor or 0.0, 4),
            "final_score":     round(entry.final_score or 0.0, 4),
        }
        for entry in qs
    ]


def get_context_for_task(
    *,
    tenant_id: int,
    task_description: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Top-K relevante Memory-Entries für einen neuen Agent-Task.

    Priorisiert: open_tasks > decisions > repo_context > rest.
    Wird beim Session-Start aufgerufen um Agent-Kontext aufzubauen.
    """
    return semantic_search(
        tenant_id=tenant_id,
        query=task_description,
        limit=top_k,
    )


def soft_delete_entry(*, tenant_id: int, entry_key: str) -> bool:
    """
    Entry soft-deleten. Gibt True zurück wenn Entry gefunden und gelöscht.
    """
    try:
        entry = AgentMemoryEntry.objects.get(tenant_id=tenant_id, entry_key=entry_key)
        entry.soft_delete()
        log.info("Memory entry soft-deleted: %s (tenant=%s)", entry_key, tenant_id)
        return True
    except AgentMemoryEntry.DoesNotExist:
        log.warning("Memory entry nicht gefunden: %s (tenant=%s)", entry_key, tenant_id)
        return False


def gc_expired_entries(*, tenant_id: int | None = None) -> int:
    """
    GC: Entries löschen deren Decay-Score unter einen Schwellwert gefallen ist.

    Soft-Delete statt hard-delete (Platform-Standard).
    Optionaler tenant_id Filter für tenant-spezifisches GC.

    Returns:
        Anzahl soft-gelöschter Entries
    """
    from django.utils import timezone

    qs = AgentMemoryEntry.objects.filter(embedding__isnull=False)
    if tenant_id is not None:
        qs = qs.filter(tenant_id=tenant_id)

    # Entries deren Decay < 5% des ursprünglichen Scores
    expired_qs = qs.annotate(
        decay_factor=RawSQL(_DECAY_SQL, [], output_field=FloatField()),
    ).filter(decay_factor__lt=0.05)

    count = expired_qs.count()
    if count:
        now = timezone.now()
        expired_qs.update(deleted_at=now)
        log.info("Memory GC: %d Entries soft-deleted (decay < 5%%)", count)

    return count
```

---

### 3.3 `apps/agent_memory/embeddings.py`

```python
"""
Embedding Client — OpenAI + Ollama mit identischem Interface.

Feature-Flag: settings.SKILL_EMBEDDING_PROVIDER = "openai" | "ollama"
Content-Hash-Caching: kein redundanter API-Call wenn Content unverändert.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Final

from django.conf import settings

log = logging.getLogger(__name__)

EMBEDDING_DIMS: Final[int] = 1536
OPENAI_MODEL:   Final[str] = "text-embedding-3-small"
OLLAMA_MODEL:   Final[str] = "nomic-embed-text"  # 768 dims → Fallback auf zero-pad


class BaseEmbeddingClient(ABC):
    """Interface für alle Embedding-Providers."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Text in Embedding-Vektor konvertieren (1536 dims)."""

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch-Embedding (default: sequentiell — Override für echtes Batching)."""
        return [self.embed(t) for t in texts]


class OpenAIEmbeddingClient(BaseEmbeddingClient):
    """
    OpenAI text-embedding-3-small Client.

    Kosten: ~$0.00002 / 1000 Tokens (~$0.0001 pro typischem Memory-Entry).
    Rate-Limit: 3000 RPM / 1M TPM (Tier 1) — für unseren Use Case unkritisch.
    """

    def __init__(self, api_key: str | None = None) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "openai Paket nicht installiert. "
                "pip install openai>=1.0.0"
            ) from exc

        self._client = OpenAI(api_key=api_key or settings.OPENAI_API_KEY)

    def embed(self, text: str) -> list[float]:
        text = text.replace("\n", " ").strip()
        if not text:
            return [0.0] * EMBEDDING_DIMS

        response = self._client.embeddings.create(
            input=text,
            model=OPENAI_MODEL,
        )
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Echtes Batch-Embedding — ein API-Call für alle Texte."""
        cleaned = [t.replace("\n", " ").strip() or " " for t in texts]
        response = self._client.embeddings.create(
            input=cleaned,
            model=OPENAI_MODEL,
        )
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


class OllamaEmbeddingClient(BaseEmbeddingClient):
    """
    Lokaler Ollama Embedding Client (zero Kosten, kein Internet).

    Ollama nomic-embed-text: 768 dims → wird auf 1536 zero-padded
    für pgvector Kompatibilität.

    Voraussetzung: Ollama läuft auf localhost:11434
    """

    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        try:
            import httpx
        except ImportError as exc:
            raise ImportError("httpx nicht installiert: pip install httpx") from exc

        self._base_url = base_url
        self._httpx = httpx

    def embed(self, text: str) -> list[float]:
        import httpx

        response = httpx.post(
            f"{self._base_url}/api/embeddings",
            json={"model": OLLAMA_MODEL, "prompt": text},
            timeout=30,
        )
        response.raise_for_status()
        embedding = response.json()["embedding"]

        # Zero-pad auf 1536 dims für pgvector Kompatibilität
        if len(embedding) < EMBEDDING_DIMS:
            embedding = embedding + [0.0] * (EMBEDDING_DIMS - len(embedding))

        return embedding[:EMBEDDING_DIMS]


def get_embedding_client() -> BaseEmbeddingClient:
    """
    Embedding-Client via Feature-Flag auswählen.

    settings.SKILL_EMBEDDING_PROVIDER: "openai" (default) | "ollama"
    """
    provider = getattr(settings, "SKILL_EMBEDDING_PROVIDER", "openai")

    if provider == "ollama":
        ollama_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        log.debug("Ollama Embedding Client (%s)", ollama_url)
        return OllamaEmbeddingClient(base_url=ollama_url)

    log.debug("OpenAI Embedding Client (model=%s)", OPENAI_MODEL)
    return OpenAIEmbeddingClient()
```

---

### 3.4 `apps/telegram_gateway/handlers.py`

```python
"""
Telegram Bot Command Handler.

Platform-Standards:
- i18n via gettext_lazy auf alle User-facing Strings
- Rate-Limiting via Django Cache (nicht asyncio.sleep)
- asgiref.async_to_sync für synchrone Service-Calls
- TELEGRAM_ALLOWED_USER_IDS als list[int] (nicht String-Vergleich)

Async-Safety:
- Handler-Funktionen sind async (python-telegram-bot 21+)
- Synchrone Django-Code via sync_to_async() wrappen
- NIEMALS asyncio.run() im ASGI-Kontext
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext as _
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

# ─── Auth ─────────────────────────────────────────────────────────────────────

def _is_authorized(user_id: int) -> bool:
    """Telegram User-ID gegen Allowlist prüfen."""
    allowed: list[int] = getattr(settings, "TELEGRAM_ALLOWED_USER_IDS", [])
    return user_id in allowed


def _check_auth(update: Update) -> bool:
    """Auth prüfen und bei Ablehnung antworten."""
    if not update.effective_user:
        return False
    return _is_authorized(update.effective_user.id)


# ─── Rate Limiting ────────────────────────────────────────────────────────────

def _check_rate_limit(user_id: int, command: str, max_per_hour: int) -> tuple[bool, int]:
    """
    Rate-Limit via Django Cache.

    Returns:
        (allowed, remaining_seconds_if_blocked)
    """
    cache_key = f"telegram_rl:{user_id}:{command}"
    current   = cache.get(cache_key, 0)

    if current >= max_per_hour:
        ttl = cache.ttl(cache_key) if hasattr(cache, "ttl") else 3600
        return False, int(ttl or 3600)

    cache.set(cache_key, current + 1, timeout=3600)
    return True, 0


RATE_LIMITS = {
    "task":   10,   # max 10 Tasks/Stunde
    "deploy":  2,   # max 2 Deploys/Stunde
    "approve": 20,  # max 20 Approvals/Stunde
    "reject":  20,
    "memory":  30,
    "status":  60,
    "health":  30,
}


# ─── Formatter Helper ─────────────────────────────────────────────────────────

def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ─── Command Handlers ─────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Willkommens-Nachricht."""
    if not _check_auth(update):
        await update.message.reply_text(_("🚫 Nicht autorisiert."))
        return

    text = _("""
🤖 <b>iilgmbh Agent Gateway</b>

<b>Verfügbare Befehle:</b>
/task &lt;beschreibung&gt; — Agent-Task erstellen
/status — Laufende Tasks anzeigen
/approve &lt;task_id&gt; [kommentar] — Task freigeben
/reject &lt;task_id&gt; &lt;grund&gt; — Task ablehnen
/memory &lt;query&gt; — Memory durchsuchen
/health — Health-Status aller Services
/deploy &lt;repo&gt; — Deployment triggern (Gate 2)
""").strip()

    await update.message.reply_html(text)


async def cmd_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/task <beschreibung> [--workflow bugfix|feature_delivery] [--scope pfad]"""
    if not _check_auth(update):
        await update.message.reply_text(_("🚫 Nicht autorisiert."))
        return

    user_id = update.effective_user.id
    allowed, wait_secs = _check_rate_limit(user_id, "task", RATE_LIMITS["task"])
    if not allowed:
        await update.message.reply_text(
            _("⏱️ Rate-Limit erreicht. Bitte %(secs)d Sekunden warten.") % {"secs": wait_secs}
        )
        return

    if not context.args:
        await update.message.reply_text(
            _("Verwendung: /task <beschreibung> [--workflow bugfix] [--scope pfad]")
        )
        return

    # Args parsen
    raw = " ".join(context.args)
    workflow = "feature_delivery"
    scope    = ""

    workflow_match = re.search(r"--workflow\s+(\S+)", raw)
    scope_match    = re.search(r"--scope\s+(\S+)", raw)

    if workflow_match:
        workflow = workflow_match.group(1)
        raw = raw.replace(workflow_match.group(0), "").strip()

    if scope_match:
        scope = scope_match.group(1)
        raw = raw.replace(scope_match.group(0), "").strip()

    task_description = raw.strip()
    if len(task_description) < 10:
        await update.message.reply_text(_("❌ Task-Beschreibung zu kurz (min. 10 Zeichen)."))
        return

    # GitHub Dispatcher (sync_to_async)
    from .dispatcher import trigger_github_workflow
    await update.message.reply_text(_("⏳ Task wird erstellt..."))

    try:
        result = await sync_to_async(trigger_github_workflow)(
            task_description=task_description,
            workflow_type=workflow,
            scope_paths=scope or "apps/",
            telegram_chat_id=str(update.effective_chat.id),
        )
        issue_url = result.get("issue_url", "")
        run_url   = result.get("run_url", "")

        text = _(
            "✅ <b>Task erstellt</b>\n\n"
            "📋 <b>Task:</b> %(task)s\n"
            "⚙️ <b>Workflow:</b> %(workflow)s\n"
        ) % {
            "task":     _escape_html(task_description[:100]),
            "workflow": _escape_html(workflow),
        }
        if issue_url:
            text += f'🔗 <a href="{issue_url}">Issue</a>\n'
        if run_url:
            text += f'▶️ <a href="{run_url}">GitHub Actions</a>\n'

        await update.message.reply_html(text)

    except Exception as exc:
        log.exception("Task creation failed: %s", exc)
        await update.message.reply_text(
            _("❌ Fehler beim Erstellen des Tasks: %(error)s") % {"error": str(exc)[:200]}
        )


async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/approve <task_id> [kommentar]"""
    if not _check_auth(update):
        await update.message.reply_text(_("🚫 Nicht autorisiert."))
        return

    user_id = update.effective_user.id
    allowed, wait_secs = _check_rate_limit(user_id, "approve", RATE_LIMITS["approve"])
    if not allowed:
        await update.message.reply_text(
            _("⏱️ Rate-Limit. Warte %(secs)d Sekunden.") % {"secs": wait_secs}
        )
        return

    if not context.args:
        await update.message.reply_text(_("Verwendung: /approve <task_id> [kommentar]"))
        return

    task_id = context.args[0]
    comment = " ".join(context.args[1:]) if len(context.args) > 1 else ""

    from .dispatcher import post_gate_decision
    try:
        await sync_to_async(post_gate_decision)(
            task_id=task_id,
            decision="approve",
            comment=comment,
        )
        await update.message.reply_html(
            _("✅ <b>Freigabe</b> für Task <code>%(id)s</code> registriert.") % {"id": task_id}
        )
    except Exception as exc:
        log.exception("Gate approve failed: %s", exc)
        await update.message.reply_text(_("❌ Fehler: %(error)s") % {"error": str(exc)[:200]})


async def cmd_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/reject <task_id> <grund>"""
    if not _check_auth(update):
        await update.message.reply_text(_("🚫 Nicht autorisiert."))
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(_("Verwendung: /reject <task_id> <grund>"))
        return

    task_id = context.args[0]
    reason  = " ".join(context.args[1:])

    from .dispatcher import post_gate_decision
    try:
        await sync_to_async(post_gate_decision)(
            task_id=task_id,
            decision="reject",
            comment=reason,
        )
        await update.message.reply_html(
            _("❌ <b>Ablehnung</b> für Task <code>%(id)s</code> registriert.\n<i>%(reason)s</i>") % {
                "id":     task_id,
                "reason": _escape_html(reason),
            }
        )
    except Exception as exc:
        log.exception("Gate reject failed: %s", exc)
        await update.message.reply_text(_("❌ Fehler: %(error)s") % {"error": str(exc)[:200]})


async def cmd_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/memory <query> — Semantic Search im Agent Memory"""
    if not _check_auth(update):
        await update.message.reply_text(_("🚫 Nicht autorisiert."))
        return

    if not context.args:
        await update.message.reply_text(_("Verwendung: /memory <suchanfrage>"))
        return

    query = " ".join(context.args)

    from apps.agent_memory.services import semantic_search
    try:
        # Default tenant_id = 1 (iilgmbh internal) — im Multi-Tenant-Fall aus User-Mapping
        default_tenant = getattr(settings, "TELEGRAM_DEFAULT_TENANT_ID", 1)
        results = await sync_to_async(semantic_search)(
            tenant_id=default_tenant,
            query=query,
            limit=5,
        )

        if not results:
            await update.message.reply_text(_("🔍 Keine relevanten Memories gefunden."))
            return

        lines = [_("🧠 <b>Memory Search:</b> <i>%(query)s</i>\n") % {"query": _escape_html(query)}]
        for i, r in enumerate(results, 1):
            score_pct = int(r["final_score"] * 100)
            lines.append(
                f"<b>{i}. [{r['entry_key']}]</b> {_escape_html(r['title'])} "
                f"<i>({score_pct}%)</i>\n"
                f"{_escape_html(r['content_preview'][:150])}...\n"
            )

        await update.message.reply_html("\n".join(lines))

    except Exception as exc:
        log.exception("Memory search failed: %s", exc)
        await update.message.reply_text(_("❌ Fehler: %(error)s") % {"error": str(exc)[:200]})


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/health — Health-Status aller bekannten Deploy-Targets"""
    if not _check_auth(update):
        await update.message.reply_text(_("🚫 Nicht autorisiert."))
        return

    import httpx
    health_targets: dict[str, str] = getattr(settings, "DEPLOY_HEALTH_URLS", {})

    if not health_targets:
        await update.message.reply_text(_("⚠️ Keine Health-URLs konfiguriert (DEPLOY_HEALTH_URLS)."))
        return

    lines = [_("🏥 <b>Health Status</b>\n")]
    for name, url in health_targets.items():
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
            status = f"✅ {resp.status_code}" if resp.status_code < 400 else f"❌ {resp.status_code}"
        except Exception as exc:
            status = f"❌ ERROR ({type(exc).__name__})"

        lines.append(f"<b>{_escape_html(name)}</b>: {status}")

    await update.message.reply_html("\n".join(lines))
```

---

### 3.5 `apps/telegram_gateway/bot.py`

```python
"""
Telegram Bot Application — async-safe Django Integration.

Platform-Standard: asgiref.async_to_sync, NIEMALS asyncio.run() im ASGI-Kontext.

Threading-Strategie:
- Management Command startet Bot in eigenem Thread (kein Event-Loop-Konflikt)
- Bot-Thread hat eigenen Event-Loop via asyncio.new_event_loop()
- Django-Code im Bot via sync_to_async() wrappen
"""
from __future__ import annotations

import asyncio
import logging
import threading

from django.conf import settings
from telegram.ext import Application, CommandHandler

log = logging.getLogger(__name__)

_bot_thread: threading.Thread | None = None
_bot_application: Application | None = None


def build_application() -> Application:
    """Telegram Application bauen und Handler registrieren."""
    from .handlers import (
        cmd_approve, cmd_health, cmd_memory,
        cmd_reject, cmd_start, cmd_task,
    )

    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN ist nicht gesetzt.")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("task",    cmd_task))
    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("reject",  cmd_reject))
    app.add_handler(CommandHandler("memory",  cmd_memory))
    app.add_handler(CommandHandler("health",  cmd_health))

    log.info("Telegram Bot Application gebaut mit %d Handlern", len(app.handlers[0]))
    return app


def _run_bot_in_thread(app: Application) -> None:
    """
    Bot in eigenem Thread mit eigenem Event-Loop starten.

    Verhindert Konflikt mit Django ASGI Event-Loop.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            app.run_polling(
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True,
            )
        )
    except Exception as exc:
        log.exception("Bot polling fehlgeschlagen: %s", exc)
    finally:
        loop.close()
        log.info("Bot Event-Loop beendet")


def start_bot() -> None:
    """Bot in Background-Thread starten (idempotent)."""
    global _bot_thread, _bot_application

    if _bot_thread and _bot_thread.is_alive():
        log.info("Bot läuft bereits")
        return

    _bot_application = build_application()
    _bot_thread = threading.Thread(
        target=_run_bot_in_thread,
        args=(_bot_application,),
        daemon=True,
        name="telegram-bot",
    )
    _bot_thread.start()
    log.info("Telegram Bot gestartet (Thread: %s)", _bot_thread.name)


def stop_bot() -> None:
    """Bot graceful stoppen."""
    global _bot_application
    if _bot_application:
        asyncio.run_coroutine_threadsafe(
            _bot_application.stop(),
            asyncio.get_event_loop(),
        )
        log.info("Telegram Bot gestoppt")
```

---

### 3.6 `apps/telegram_gateway/management/commands/run_telegram_bot.py`

```python
"""
Django Management Command: python manage.py run_telegram_bot

Startet den Telegram Bot als Long-Polling Service.
Geeignet für Docker-Container (CMD) und lokale Entwicklung.

Platform-Standard: kein asyncio.run() — Bot läuft in eigenem Thread.
"""
from __future__ import annotations

import signal
import time

from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _


class Command(BaseCommand):
    help = "Telegram Bot als Long-Polling Service starten"

    def handle(self, *args, **options) -> None:
        from apps.telegram_gateway.bot import start_bot, stop_bot

        self.stdout.write(self.style.SUCCESS(_("Starte Telegram Bot...")))
        start_bot()

        def _shutdown(signum, frame):
            self.stdout.write(self.style.WARNING(_("Signal empfangen — stoppe Bot...")))
            stop_bot()
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, _shutdown)
        signal.signal(signal.SIGINT,  _shutdown)

        self.stdout.write(self.style.SUCCESS(_("Bot läuft. CTRL+C zum Beenden.")))

        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            stop_bot()
            self.stdout.write(self.style.SUCCESS(_("Bot beendet.")))
```

---

### 3.7 `apps/telegram_gateway/dispatcher.py`

```python
"""
GitHub Actions Dispatcher — triggert Workflows via GitHub API.

Retry-Logik via tenacity (3 Versuche, exponential Backoff).
Kein direkte httpx-Calls in Handlers — Isolation im Service-Layer.
"""
from __future__ import annotations

import logging
import os

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


def _get_token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("PROJECT_PAT", "")
    if not token:
        raise ValueError("GITHUB_TOKEN oder PROJECT_PAT Env-Var fehlt")
    return token


def _headers() -> dict[str, str]:
    return {
        "Authorization":        f"Bearer {_get_token()}",
        "Accept":               "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def trigger_github_workflow(
    *,
    task_description: str,
    workflow_type: str = "feature_delivery",
    scope_paths: str = "apps/",
    telegram_chat_id: str = "",
    org: str = "iilgmbh",
    repo: str = "mcp-hub",
) -> dict:
    """
    GitHub Actions Workflow via `workflow_dispatch` triggern.

    Returns:
        dict mit issue_url, run_url (wenn verfügbar)
    """
    from django.conf import settings
    org  = getattr(settings, "GITHUB_ORG", org)
    repo = getattr(settings, "GITHUB_REPO", repo)

    payload = {
        "ref": "main",
        "inputs": {
            "task_description": task_description,
            "workflow_type":    workflow_type,
            "scope_paths":      scope_paths,
            "dry_run":          "false",
        },
    }
    if telegram_chat_id:
        payload["inputs"]["telegram_chat_id"] = telegram_chat_id

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{GITHUB_API}/repos/{org}/{repo}/actions/workflows/agent-task-dispatch.yml/dispatches",
            headers=_headers(),
            json=payload,
        )

    if resp.status_code == 204:
        log.info("Workflow getriggert: %s/%s", org, repo)
        return {"triggered": True, "issue_url": "", "run_url": ""}

    resp.raise_for_status()
    return resp.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
def post_gate_decision(
    *,
    task_id: str,
    decision: str,
    comment: str = "",
    org: str = "iilgmbh",
    repo: str = "mcp-hub",
) -> dict:
    """
    Gate-Entscheidung via Issue-Kommentar posten.

    task_id ist die GitHub Issue-Nummer.
    """
    from django.conf import settings
    org  = getattr(settings, "GITHUB_ORG", org)
    repo = getattr(settings, "GITHUB_REPO", repo)

    try:
        issue_number = int(task_id.lstrip("#"))
    except ValueError:
        raise ValueError(f"Ungültige task_id: '{task_id}' — erwartet Zahl oder #Zahl")

    body = f"/{decision}"
    if comment:
        body += f" {comment}"

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{GITHUB_API}/repos/{org}/{repo}/issues/{issue_number}/comments",
            headers=_headers(),
            json={"body": body},
        )

    resp.raise_for_status()
    log.info("Gate decision '%s' gepostet auf Issue #%d", decision, issue_number)
    return resp.json()
```

---

### 3.8 `apps/agent_memory/migrations/0001_initial.py`

```python
"""
Initial Migration für AgentMemoryEntry.

Idempotente Migration: pgvector Extension via SeparateDatabaseAndState.
HNSW Index: besser als ivfflat für <100k Entries (kein Rebuild bei Inserts).
"""
from __future__ import annotations

import uuid

import django.db.models.deletion
from django.db import migrations, models

import pgvector.django


class Migration(migrations.Migration):

    initial = True
    dependencies: list = []

    operations = [
        # pgvector Extension idempotent installieren
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="-- Extension bewusst nicht entfernen (shared resource)",
            state_operations=[],
        ),

        migrations.CreateModel(
            name="AgentMemoryEntry",
            fields=[
                ("id",        models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)),
                ("tenant_id", models.BigIntegerField(db_index=True)),
                ("entry_key", models.CharField(max_length=64)),
                ("entry_type",models.CharField(max_length=32, db_index=True, choices=[
                    ("open_task",      "Offener Task"),
                    ("decision",       "Entscheidung"),
                    ("repo_context",   "Repo-Kontext"),
                    ("lesson_learned", "Lesson Learned"),
                    ("error_pattern",  "Fehler-Muster"),
                    ("agent_handoff",  "Agent Handoff"),
                ])),
                ("title",          models.CharField(max_length=200)),
                ("content",        models.TextField()),
                ("agent",          models.CharField(max_length=64)),
                ("half_life_days", models.PositiveSmallIntegerField(default=30)),
                ("embedding",      pgvector.django.VectorField(dimensions=1536, null=True, blank=True)),
                ("content_hash",   models.CharField(max_length=64, blank=True)),
                ("tags",           models.JSONField(default=list)),
                ("related_ids",    models.JSONField(default=list)),
                ("metadata",       models.JSONField(default=dict)),
                ("created_at",     models.DateTimeField(auto_now_add=True)),
                ("updated_at",     models.DateTimeField(auto_now=True)),
                ("deleted_at",     models.DateTimeField(null=True, blank=True, db_index=True)),
            ],
            options={
                "verbose_name":        "Agent Memory Entry",
                "verbose_name_plural": "Agent Memory Entries",
                "ordering":            ["-updated_at"],
            },
        ),

        migrations.AddConstraint(
            model_name="agentmemoryentry",
            constraint=models.UniqueConstraint(
                fields=["tenant_id", "entry_key"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_memory_entry_per_tenant",
            ),
        ),

        # HNSW Index (besser als ivfflat für <100k Entries)
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS agent_memory_embedding_hnsw
                ON agent_memory_agentmemoryentry
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """,
            reverse_sql="DROP INDEX IF EXISTS agent_memory_embedding_hnsw;",
            state_operations=[],
        ),

        # Full-Text Search Index (German)
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS agent_memory_fts_idx
                ON agent_memory_agentmemoryentry
                USING gin(to_tsvector('german', content || ' ' || title));
            """,
            reverse_sql="DROP INDEX IF EXISTS agent_memory_fts_idx;",
            state_operations=[],
        ),
    ]
```

---

### 3.9 `apps/agent_memory/management/commands/migrate_agent_memory.py`

```python
"""
Management Command: AGENT_MEMORY.md → pgvector Migration (ADR-112 → ADR-113).

Idempotent: get_or_create via entry_key + tenant_id.
Verwendet batch embedding für Effizienz.

Usage:
    python manage.py migrate_agent_memory --file AGENT_MEMORY.md --tenant-id 1
    python manage.py migrate_agent_memory --file AGENT_MEMORY.md --tenant-id 1 --dry-run
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migriert AGENT_MEMORY.md Entries nach pgvector (ADR-112 → ADR-113)"

    def add_arguments(self, parser):
        parser.add_argument("--file",      default="AGENT_MEMORY.md", help="Pfad zur AGENT_MEMORY.md")
        parser.add_argument("--tenant-id", type=int, default=1,       help="Tenant ID für Entries")
        parser.add_argument("--dry-run",   action="store_true",        help="Keine Datenbankänderungen")

    def handle(self, *args, **options) -> None:
        md_path   = Path(options["file"])
        tenant_id = options["tenant_id"]
        dry_run   = options["dry_run"]

        if not md_path.exists():
            raise CommandError(f"Datei nicht gefunden: {md_path}")

        self.stdout.write(f"Lese {md_path}...")
        entries = self._parse_markdown(md_path)
        self.stdout.write(f"Gefunden: {len(entries)} Entries")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — keine DB-Änderungen"))
            for e in entries:
                self.stdout.write(f"  → {e['entry_key']} [{e['entry_type']}]")
            return

        from apps.agent_memory.services import upsert_entry

        migrated = 0
        for entry_dict in entries:
            try:
                upsert_entry(
                    tenant_id=tenant_id,
                    entry_key=entry_dict["entry_key"],
                    entry_type=entry_dict.get("entry_type", "lesson_learned"),
                    title=entry_dict.get("title", entry_dict["entry_key"]),
                    content=entry_dict.get("content", ""),
                    agent=entry_dict.get("agent", "migration-command"),
                    tags=entry_dict.get("tags", ["migrated-from-md"]),
                    metadata=entry_dict.get("metadata", {}),
                    compute_embedding=True,
                )
                migrated += 1
                self.stdout.write(f"  ✅ {entry_dict['entry_key']}")
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  ❌ {entry_dict['entry_key']}: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(f"Migration abgeschlossen: {migrated}/{len(entries)} Entries migriert")
        )

    def _parse_markdown(self, path: Path) -> list[dict]:
        """JSON-Blöcke aus AGENT_MEMORY.md extrahieren (ADR-112 Format)."""
        content = path.read_text(encoding="utf-8")
        entries = []
        in_block = False
        lines: list[str] = []

        for line in content.splitlines():
            if line.strip() == "```json":
                in_block = True
                lines = []
            elif line.strip() == "```" and in_block:
                in_block = False
                try:
                    raw = json.loads("\n".join(lines))
                    if raw.get("_type") == "entry":
                        entries.append({
                            "entry_key":  raw.get("entry_id", "UNKNOWN"),
                            "entry_type": raw.get("entry_type", "lesson_learned"),
                            "title":      raw.get("title", ""),
                            "content":    raw.get("content", ""),
                            "agent":      raw.get("agent", "migration"),
                            "tags":       raw.get("tags", []) + ["migrated-from-md"],
                            "metadata":   raw.get("metadata", {}),
                        })
                except json.JSONDecodeError:
                    pass
            elif in_block:
                lines.append(line)

        return entries
```

---

### 3.10 `apps/agent_memory/admin.py`

```python
"""Django Admin für AgentMemoryEntry."""
from __future__ import annotations

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import AgentMemoryEntry


@admin.register(AgentMemoryEntry)
class AgentMemoryEntryAdmin(admin.ModelAdmin):
    list_display  = ["entry_key", "entry_type", "title", "agent", "tenant_id",
                     "half_life_days", "updated_at", "deleted_at"]
    list_filter   = ["entry_type", "agent", "deleted_at"]
    search_fields = ["entry_key", "title", "content", "agent"]
    readonly_fields = ["public_id", "content_hash", "created_at", "updated_at", "embedding"]
    ordering      = ["-updated_at"]

    fieldsets = (
        (None, {"fields": ("entry_key", "entry_type", "title", "content", "agent", "tenant_id")}),
        (_("Temporal Decay"), {"fields": ("half_life_days",)}),
        (_("Metadaten"),  {"fields": ("tags", "related_ids", "metadata")}),
        (_("Embedding"),  {"fields": ("embedding", "content_hash"), "classes": ("collapse",)}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at", "deleted_at", "public_id"),
                           "classes": ("collapse",)}),
    )

    actions = ["soft_delete_selected", "restore_selected"]

    @admin.action(description=_("Ausgewählte Entries soft-deleten"))
    def soft_delete_selected(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(deleted_at=timezone.now())
        self.message_user(request, _(f"{count} Entries soft-deleted."))

    @admin.action(description=_("Ausgewählte Entries wiederherstellen"))
    def restore_selected(self, request, queryset):
        count = queryset.update(deleted_at=None)
        self.message_user(request, _(f"{count} Entries wiederhergestellt."))

    def get_queryset(self, request):
        # Admin zeigt auch soft-deleted Entries
        return AgentMemoryEntry.all_objects.all()
```

---

## 4. Docker-Compose Ergänzung

```yaml
# docker-compose.prod.yml — Ergänzung

services:
  # ── bestehende Services ──────────────────────────────────────────────────

  telegram-bot:
    build:
      context: .
      dockerfile: Dockerfile
    command: python manage.py run_telegram_bot
    restart: unless-stopped
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_ALLOWED_USER_IDS=${TELEGRAM_ALLOWED_USER_IDS}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SKILL_EMBEDDING_PROVIDER=${SKILL_EMBEDDING_PROVIDER:-openai}
      - TELEGRAM_DEFAULT_TENANT_ID=${TELEGRAM_DEFAULT_TENANT_ID:-1}
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - "import httpx; httpx.get('https://api.telegram.org', timeout=5)"
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 30s
    depends_on:
      db:
        condition: service_healthy
    networks:
      - internal
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 5. Settings-Ergänzungen

```python
# config/settings/base.py — Ergänzungen

# ── Telegram Gateway ─────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_ALLOWED_USER_IDS: list[int] = [
    int(x.strip())
    for x in env("TELEGRAM_ALLOWED_USER_IDS", default="").split(",")
    if x.strip().isdigit()
]
TELEGRAM_DEFAULT_TENANT_ID: int = env.int("TELEGRAM_DEFAULT_TENANT_ID", default=1)
TELEGRAM_GATEWAY_ENABLED: bool = env.bool("TELEGRAM_GATEWAY_ENABLED", default=False)

# ── Agent Memory ─────────────────────────────────────────────────────────────
SKILL_MEMORY_BACKEND: str = env("SKILL_MEMORY_BACKEND", default="pgvector")  # pgvector|markdown
SKILL_EMBEDDING_PROVIDER: str = env("SKILL_EMBEDDING_PROVIDER", default="openai")  # openai|ollama
OLLAMA_BASE_URL: str = env("OLLAMA_BASE_URL", default="http://localhost:11434")

# ── GitHub Dispatcher ────────────────────────────────────────────────────────
GITHUB_ORG: str  = env("GITHUB_ORG", default="iilgmbh")
GITHUB_REPO: str = env("GITHUB_REPO", default="mcp-hub")

# ── Health URLs für /health Befehl ───────────────────────────────────────────
DEPLOY_HEALTH_URLS: dict[str, str] = {
    "coach-hub":    "https://kiohnerisiko.de/healthz/",
    "risk-hub":     "https://risk.iilgmbh.com/healthz/",
    # weitere nach Bedarf
}

INSTALLED_APPS = [
    # ...
    "apps.agent_memory",
    "apps.telegram_gateway",
]
```

---

## 6. Alternatives: ivfflat vs. HNSW

| Index | Beste für | Build-Zeit | Query-Speed | Rebuild nötig? |
|---|---|---|---|---|
| **ivfflat** (ADR-Original) | >100k Entries | Schnell | Gut | Ja bei >10% neuen Rows |
| **HNSW** (empfohlen) | <100k Entries | Langsamer | Besser | Nein |

**Entscheidung:** HNSW für Agent Memory — Datenmenge bleibt klein (<10k Entries), kein Rebuild nötig, bessere Query-Performance bei kleinen Datasets.

---

## 7. Revidierter Migrations-Plan

| Schritt | Aktion | Aufwand | Feature-Flag | Rollback |
|---|---|---|---|---|
| 1 | `apps/agent_memory/` + Migration anlegen | 45 min | nein | `git revert` |
| 2 | `apps/agent_memory/embeddings.py` + Settings | 30 min | `SKILL_MEMORY_BACKEND` | Flag → markdown |
| 3 | `apps/agent_memory/services.py` | 45 min | `SKILL_MEMORY_BACKEND` | Flag → markdown |
| 4 | `migrate_agent_memory` Command ausführen | 15 min | nein | Idempotent |
| 5 | `apps/telegram_gateway/` anlegen | 60 min | `TELEGRAM_GATEWAY_ENABLED` | Flag → false |
| 6 | docker-compose + telegram-bot Service | 15 min | nein | Service stoppen |
| 7 | orchestrator_mcp v3.3 neue Tools | 30 min | nein | Tools weglassen |

**Gesamt:** ~4h | **Gate:** Schritt 5+ nur mit `TELEGRAM_GATEWAY_ENABLED=true`

---

*Review: 2026-03-08 | Reviewer: Principal IT-Architekt | Status: CHANGES REQUIRED → ACCEPTED nach Blocker-Fix*
