---
status: proposed
date: 2026-02-22
decision-makers: Achim Dehnert
consulted: –
informed: –
---

# ADR-062: Adopt Shared PostgreSQL Schema `content_store` for AI-Generated Content Persistence

## Metadaten

| Attribut          | Wert                                                                                      |
|-------------------|-------------------------------------------------------------------------------------------|
| **Status**        | Proposed                                                                                  |
| **Scope**         | platform                                                                                  |
| **Erstellt**      | 2026-02-22                                                                                |
| **Autor**         | Achim Dehnert                                                                             |
| **Reviewer**      | –                                                                                         |
| **Supersedes**    | –                                                                                         |
| **Superseded by** | –                                                                                         |
| **Relates to**    | ADR-056 (Multi-Tenancy), ADR-059 (ADR-Drift-Detector), ADR-014 (AI-Native Development), ADR-057 (Platform Test Strategy) |

## Repo-Zugehörigkeit

| Repo          | Rolle    | Betroffene Pfade / Komponenten                                   |
|---------------|----------|------------------------------------------------------------------|
| `platform`    | Primär   | `packages/creative-services/creative_services/storage/`         |
| `platform`    | Primär   | `packages/creative-services/creative_services/graph/`           |
| `platform`    | Primär   | `shared_contracts/content_events.py` (neu)                      |
| `mcp-hub`     | Sekundär | `content_mcp/` (neu, Phase 3), `query_agent_mcp/` (Erweiterung) |
| `mcp-hub`     | Sekundär | `orchestrator_mcp/agent_team/` (Consumer A)                     |
| `travel-beat` | Sekundär | `apps/stories/services.py` (Consumer B)                         |
| `bfagent`     | Sekundär | `apps/bfagent/services/` (Consumer C)                           |

---

## Decision Drivers

- **Kein Content-Memory**: `creative-services` ist ein reiner Execution-Layer — jeder LLM-Call ist stateless, generierter Content geht verloren oder landet unstrukturiert in App-DBs
- **4 aktive Consumer** mit unterschiedlichen Anforderungen: AI-Agent-Team (ADR-059), DriftTales, bfagent, creative-services selbst
- **ADR-059 Context-Problem**: Der Tech-Lead-Agent hat ohne persistierten Content kein Gedächtnis — TaskPlans, ImpactReports und Entscheidungen gehen nach jedem Run verloren
- **Doppelte Datenhaltung**: Charaktere, Welten und Orte werden in mehreren Services redundant gespeichert ohne Cross-Service-Referenzierbarkeit
- **Keine Versionierung**: AI-generierte Drafts überschreiben sich — kein A/B-Vergleich, kein Rollback
- **Multi-Tenancy von Anfang an**: Nachträgliches Einbauen von `tenant_id` ist die teuerste Migration (Erfahrung aus ADR-056)

---

## 1. Context and Problem Statement

### 1.1 Ist-Zustand

Das Platform-Package `creative-services` stellt einen vollständigen AI-Execution-Layer bereit: LLM-Client mit Tier-System, Prompt-Template-System (195 Tests), Usage-Tracker, Redis-Caching und Django-Adapter. Domain-Module für `character/`, `world/`, `story/` und `scene/` existieren bereits.

**Was fehlt:** Persistenz. Jeder LLM-Call generiert Content der entweder verworfen wird oder unstrukturiert in der jeweiligen App-DB landet. Es gibt keinen gemeinsamen Content-Store, keine Versionierung, keine Cross-Service-Referenzierbarkeit und keine MCP-Zugangsschicht für den AI-Agent-Team.

```
HEUTE — vollständige Isolation:

bfagent DB          travel-beat DB        agent-team (kein Store)
┌──────────────┐    ┌──────────────┐      ┌──────────────────────┐
│ drafts (raw) │    │ chapters(raw)│      │ TaskPlans:    weg    │
│ kein Kontext │    │ kein Kontext │      │ ImpactReports: weg   │
└──────────────┘    └──────────────┘      └──────────────────────┘
```

### 1.2 Consumer-Analyse: 4 verschiedene Content-Typen

| Consumer | Content-Typ | Tenant-Isolation | Versionierung | Graph | Volumen |
|---|---|---|---|---|---|
| **A: AI-Agent-Team** | `DecisionContent` — TaskPlans, ImpactReports, Reviews | NEIN (plattformweit) | JA (Audit-Trail) | JA (ADR→Task→Code) | Niedrig |
| **B: DriftTales** | `NarrativeContent` — Story-Kapitel, Reisebeschreibungen | JA (strikt) | JA (User-Feedback) | NEIN | Hoch |
| **C: bfagent** | `DraftContent` — Kapitel-Drafts, Varianten | NEIN (single-tenant) | JA (A/B-Vergleich) | NEIN | Mittel |
| **D: creative-services** | `ExecutionContent` — LLM-Call-Metadaten, Scores | BEIDES | NEIN | NEIN | Sehr hoch |

### 1.3 Warum jetzt

ADR-059 definiert einen Tech-Lead-Agenten der ADRs liest, Tasks plant und Entscheidungen trifft. Ohne Content-Store hat dieser Agent kein Gedächtnis — jeder Run startet bei Null. Das ist der unmittelbare Auslöser.

---

## 2. Considered Options

### Option A: Shared PostgreSQL Schema `content_store.*` in `creative-services` ✅

Erweiterung des bestehenden `creative-services` Package um `storage/` und `graph/` Module. Das Datenbankschema `content_store.*` lebt in der bestehenden Postgres-Instanz (shared DB, eigenes Schema). Kein neuer Service, kein neues Repo.

**Pros:**
- Kein neues Repo, kein neuer Service, keine neue Infrastruktur
- `creative-services` bereits in `bfagent` und `travel-beat` installiert — direkter Upgrade-Pfad
- `tenant_id IS NULL` für plattformweite Inhalte (Agent-Team), `tenant_id IS NOT NULL` für tenant-isolierte (DriftTales) — ein Schema, zwei Modi
- Klarer Migrationspfad zu eigenem Repo wenn Trigger-Bedingungen erfüllt sind

**Cons:**
- Shared DB: Content-Store-Queries belasten dieselbe Postgres-Instanz wie App-Queries
- Schema-Änderungen in `creative-services` betreffen alle Consumer gleichzeitig

### Option B: Eigenes `content-hub` Repository (Django-Service)

**Abgelehnt weil:** Trigger-Bedingungen (≥5 aktive Consumer, >5 GB Volumen, eigene Business-Logik) sind heute nicht erfüllt. Neuer SPOF. Overengineering für den aktuellen Stand. Wird als Migrationsziel mit expliziten Trigger-Bedingungen (§4.6) definiert.

### Option C: `content_mcp` als primärer Datenspeicher

**Abgelehnt weil:** MCP ist ein LLM-Tool-Protokoll, kein Service-to-Service-Protokoll. Django-Services können MCP nicht direkt aufrufen. MCP bleibt Zugangsschicht (Phase 3), nicht Datenspeicher.

### Option D: Event-basierter Index ohne zentralen Store

**Abgelehnt als primäre Strategie weil:** Eventual Consistency löst das ADR-059 Context-Problem nicht — der Agent braucht synchronen Zugriff auf seine eigenen Artefakte. Bleibt als ergänzendes Muster für Cross-Service-Referenzen (Phase 2).

---

## 3. Decision Outcome

**Gewählte Option: Option A — Shared PostgreSQL Schema `content_store.*` in `creative-services`**

`creative-services` wird vom reinen Execution-Layer zum vollständigen Content-Repository erweitert. Pilot-Consumer ist das AI-Agent-Team (ADR-059): niedrigstes Volumen, schnellster Feedback-Loop (eigene Entwicklungsarbeit), größter unmittelbarer Nutzen.

Option B wird als Migrationsziel definiert — mit expliziten, messbaren Trigger-Bedingungen (§4.6). Die Migration ist trivial weil das Datenbankschema identisch bleibt.

---

## 4. Implementation Details

### 4.1 Datenbankschema

```sql
CREATE SCHEMA IF NOT EXISTS content_store;

CREATE TABLE content_store.items (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    source_svc    TEXT        NOT NULL,
    source_type   TEXT        NOT NULL,
    source_id     TEXT        NOT NULL,
    tenant_id     UUID,                   -- NULL = plattformweit (Agent-Team)
    content       TEXT        NOT NULL,
    content_hash  TEXT        NOT NULL,   -- SHA-256
    prompt_key    TEXT,
    model_used    TEXT        NOT NULL,
    version       INT         NOT NULL DEFAULT 1,
    parent_id     UUID        REFERENCES content_store.items(id) ON DELETE SET NULL,
    tags          TEXT[]      NOT NULL DEFAULT '{}',
    properties    JSONB       NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    embedding     vector(1536)            -- pgvector, optional
);

CREATE TABLE content_store.relations (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    source_item   UUID        NOT NULL REFERENCES content_store.items(id) ON DELETE CASCADE,
    target_ref    TEXT        NOT NULL,   -- "adr:ADR-059" | "trip:42" | "char:7"
    relation_type TEXT        NOT NULL,   -- 'implements' | 'references' | 'derived_from'
    tenant_id     UUID,
    weight        FLOAT       NOT NULL DEFAULT 1.0,
    properties    JSONB       NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indizes
CREATE INDEX ON content_store.items (source_svc, source_type, source_id);
CREATE INDEX ON content_store.items (tenant_id) WHERE tenant_id IS NOT NULL;
CREATE INDEX ON content_store.items (parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX ON content_store.items (created_at DESC);
CREATE INDEX ON content_store.items USING GIN (tags);
CREATE INDEX ON content_store.relations (source_item, relation_type);
CREATE INDEX ON content_store.relations (target_ref);

-- Consumer-spezifische Views
CREATE VIEW content_store.v_decisions AS
    SELECT * FROM content_store.items
    WHERE source_svc = 'agent-team' AND tenant_id IS NULL;

CREATE VIEW content_store.v_narrative AS
    SELECT * FROM content_store.items
    WHERE source_svc = 'travel-beat' AND tenant_id IS NOT NULL;

CREATE VIEW content_store.v_drafts AS
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY source_id ORDER BY version DESC
    ) AS version_rank
    FROM content_store.items WHERE source_svc = 'bfagent';
```

### 4.2 Python-Modelle (`creative_services/storage/models.py`)

```python
from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field

SourceService = Literal["bfagent", "travel-beat", "agent-team", "creative-services"]
SourceType = Literal[
    "chapter", "story", "scene", "character_description",
    "task_plan", "impact_report", "code_review", "adr_analysis",
    "draft", "draft_variant",
    "llm_execution", "prompt_result",
]

class ContentItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    source_svc: SourceService
    source_type: SourceType
    source_id: str = Field(description="ID im Quell-Service")
    tenant_id: UUID | None = Field(
        default=None,
        description="NULL = plattformweit, UUID = tenant-isoliert",
    )
    content: str
    content_hash: str
    prompt_key: str | None = None
    model_used: str
    version: int = Field(default=1, ge=1)
    parent_id: UUID | None = None
    tags: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ContentRelation(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    source_item: UUID
    target_ref: str = Field(description="Format: '<type>:<id>', z.B. 'adr:ADR-059'")
    relation_type: Literal[
        "implements", "references", "derived_from",
        "tested_by", "appears_in", "located_in",
    ]
    tenant_id: UUID | None = None
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: dict[str, Any] = Field(default_factory=dict)
```

### 4.3 ContentStore API (`creative_services/storage/store.py`)

```python
class ContentStore:
    """Persistenz-Layer fuer AI-generierten Content.
    Zugriff via asyncpg direkt (kein Django ORM).
    """

    async def save(self, item: ContentItem) -> ContentItem: ...
    async def get(self, item_id: UUID) -> ContentItem | None: ...
    async def get_versions(self, source_svc: str, source_id: str) -> list[ContentItem]: ...
    async def latest(self, source_svc: str, source_id: str) -> ContentItem | None: ...
    async def add_relation(self, relation: ContentRelation) -> ContentRelation: ...
    async def find_by_ref(
        self,
        target_ref: str,
        relation_type: str | None = None,
        tenant_id: UUID | None = None,
    ) -> list[ContentItem]: ...
    async def search(
        self,
        query: str,
        source_svc: str | None = None,
        source_type: str | None = None,
        tenant_id: UUID | None = None,
        limit: int = 10,
    ) -> list[ContentItem]: ...
```

### 4.4 Event-Contract (`shared_contracts/content_events.py`)

```python
from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class ContentStoredEvent(BaseModel):
    """Wird nach jedem save() via Celery publiziert."""
    model_config = ConfigDict(frozen=True)

    event_type: Literal["content.stored"] = "content.stored"
    item_id: UUID
    source_svc: str
    source_type: str
    source_id: str
    tenant_id: UUID | None
    version: int
    model_used: str
    tags: list[str]
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class EntityPublishedEvent(BaseModel):
    """Publiziert wenn eine Domain-Entitaet cross-service sichtbar werden soll."""
    model_config = ConfigDict(frozen=True)

    event_type: Literal["entity.published"] = "entity.published"
    entity_type: Literal["character", "world", "location", "story", "trip"]
    entity_id: str
    source_svc: str
    tenant_id: UUID
    display_name: str
    summary: str = Field(description="Max 500 Zeichen")
    canonical_url: str
    published_at: datetime = Field(default_factory=datetime.utcnow)
    properties: dict[str, Any] = Field(default_factory=dict)
```

### 4.5 Pilot-Integration: AI-Agent-Team (Consumer A)

```python
# orchestrator_mcp/agent_team/tech_lead.py — Erweiterung
from creative_services.storage import ContentStore, ContentItem, ContentRelation

async def plan_from_adr(adr_path: str) -> TaskPlan:
    plan = await _parse_and_plan(adr_path)
    store = ContentStore()
    item = await store.save(ContentItem(
        source_svc="agent-team",
        source_type="task_plan",
        source_id=f"adr:{adr_path}",
        tenant_id=None,  # plattformweit
        content=plan.model_dump_json(),
        content_hash=_sha256(plan.model_dump_json()),
        model_used="claude-opus-4",
        tags=["task_plan", "adr"],
        properties={"adr_path": adr_path, "task_count": len(plan.tasks)},
    ))
    await store.add_relation(ContentRelation(
        source_item=item.id,
        target_ref=f"adr:{adr_path}",
        relation_type="implements",
    ))
    return plan
```

### 4.6 Trigger-Bedingungen fuer Migration zu `content-hub`

Migration wird ausgeloest wenn **mindestens 2** der folgenden Bedingungen erfuellt sind:

| Trigger | Messgrösse | Monitoring |
|---|---|---|
| Consumer-Zahl | >= 5 aktive Services schreiben Content | `GROUP BY source_svc` |
| Volumen | > 5 GB im Schema | `pg_schema_size('content_store')` |
| DB-Last | > 25% aller Queries betreffen `content_store.*` | `pg_stat_statements` |
| Business-Logik | Approval-Workflows, Embargo, Lizenzierung | Manuell bewertet |
| Schema-Aenderungsrate | > 3 Migrationen in 4 Wochen | Git-Log |

**Migration ist trivial:** Das Datenbankschema `content_store.*` bleibt identisch — nur der Zugangspfad aendert sich von direktem asyncpg-Zugriff zu REST-API-Calls.

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Datum | Notizen |
|---|---|---|---|---|
| `platform` / `creative-services` | 1 — Schema + Storage-API | ⬜ Ausstehend | – | `storage/` + `graph/` Module, SQL-Schema |
| `platform` / `shared_contracts` | 1 — Event-Contracts | ⬜ Ausstehend | – | `content_events.py` |
| `mcp-hub` / `orchestrator_mcp` | 2 — Pilot Consumer A | ⬜ Ausstehend | – | Agent-Team: TaskPlan + ImpactReport |
| `mcp-hub` / `query_agent_mcp` | 2 — MCP-Tools | ⬜ Ausstehend | – | `find_decision_history`, `get_content_versions` |
| `travel-beat` | 3 — Consumer B | ⬜ Ausstehend | – | Story-Kapitel mit tenant_id |
| `bfagent` | 4 — Consumer C | ⬜ Ausstehend | – | Draft-Varianten via `bfagent_compat.py` |
| `mcp-hub` / `content_mcp` | 5 — MCP-Zugangsschicht | ⬜ Ausstehend | – | Erst nach Phase 2 stabil |
| `content-hub` (neues Repo) | 6 — Eigener Service | ⬜ Ausstehend | – | Nur wenn Trigger-Bedingungen (§4.6) erfuellt |

---

## 6. Consequences

### 6.1 Good

- **ADR-059 Context-Problem geloest**: Tech-Lead-Agent hat persistentes Gedaechtnis
- **Keine neue Infrastruktur**: Postgres-Schema in bestehender DB
- **Versionierung von Anfang an**: `parent_id`-Kette ermoeglicht vollstaendige Versionshistorie
- **Multi-Tenancy korrekt**: `tenant_id IS NULL` fuer plattformweit, `IS NOT NULL` fuer tenant-isoliert
- **Klarer Migrationspfad**: Trigger-Bedingungen fuer `content-hub` sind messbar

### 6.2 Bad

- **Shared DB**: Content-Store-Queries belasten dieselbe Postgres-Instanz — Monitoring erforderlich
- **Koordiniertes Versioning**: Schema-Aenderungen betreffen alle Consumer gleichzeitig
- **asyncpg-Dependency**: Direkter DB-Zugriff ohne Django ORM — erfordert Connection-Management

### 6.3 Nicht in Scope

- Eigenes `content-hub` Repo — erst wenn Trigger-Bedingungen (§4.6) erfuellt
- Elasticsearch oder dedizierter Vektor-Store — pgvector reicht fuer Phase 1–3
- Cross-Tenant-Graph — DSGVO-Konflikt, explizit ausgeschlossen
- Medien/Assets (Bilder, PDFs) — separates ADR

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|---|---|---|---|
| Shared DB wird zum Bottleneck | Mittel | Hoch | `pg_stat_statements` Monitoring, Trigger §4.6 |
| Schema-Aenderung bricht Consumer | Mittel | Hoch | Expand-Contract-Pattern: additive Aenderungen zuerst |
| `tenant_id IS NULL` versehentlich fuer tenant-gebundene Daten | Niedrig | Kritisch | Pydantic-Validator: TENANT_SERVICES erzwingt tenant_id |
| asyncpg Connection-Leak | Niedrig | Mittel | `asyncpg.create_pool()`, Context-Manager-Pattern |
| pgvector nicht installiert | Niedrig | Niedrig | `embedding`-Feld optional, Fallback auf Volltext |

---

## 8. Confirmation

1. **Schema-Existenz-Test (CI)**: `pytest` prueft ob `content_store.items` und `content_store.relations` existieren — blockiert Merge bei Fehler
2. **Tenant-Isolation-Test**: `test_should_not_leak_content_across_tenants` — zwei Tenants schreiben Content, keiner sieht den anderen
3. **Versionierungs-Test**: `test_should_create_new_version_on_save` — zweiter `save()` mit gleicher `source_id` inkrementiert `version`
4. **Null-Tenant-Test**: `test_should_allow_null_tenant_for_platform_content` — Agent-Team-Content mit `tenant_id=None` lesbar ohne Tenant-Kontext
5. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualitaet geprueft — Staleness-Schwelle: 12 Monate

---

## 9. More Information

- ADR-056: Multi-Tenancy Schema Isolation — `tenant_id`-Muster und Schema-Isolation-Strategie
- ADR-059: ADR-Drift-Detector — Confirmation-Mechanismus fuer dieses ADR
- ADR-014: AI-Native Development Teams — Kontext fuer Consumer A (Agent-Team)
- ADR-057: Platform Test Strategy — Test-Anforderungen §8
- [asyncpg Dokumentation](https://magicstack.github.io/asyncpg/)
- [pgvector](https://github.com/pgvector/pgvector)
- `packages/creative-services/README.md` — bestehende creative-services Architektur

---

## 10. Changelog

| Datum | Autor | Aenderung |
|---|---|---|
| 2026-02-22 | Achim Dehnert | Initial: Status Proposed |

---

<!--
  Drift-Detector-Felder (ADR-059):
  - staleness_months: 12
  - drift_check_paths:
      - platform/packages/creative-services/creative_services/storage/
      - platform/shared_contracts/content_events.py
      - mcp-hub/orchestrator_mcp/agent_team/
  - supersedes_check: true
-->
