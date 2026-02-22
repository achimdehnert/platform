---
status: proposed
date: 2026-02-22
decision-makers: Achim Dehnert
consulted: –
informed: –
---

# ADR-062: Adopt Shared PostgreSQL Schema `content_store` for AI-Generated Content Persistence

## Metadaten

| Attribut       | Wert |
|----------------|------|
| **Status**     | Proposed |
| **Scope**      | platform-wide |
| **Erstellt**   | 2026-02-22 |
| **Autor**      | Achim Dehnert |
| **Relates to** | ADR-056 (Multi-Tenancy), ADR-059 (Agent-Team), ADR-014 (AI-Native Dev), ADR-045 (Secrets) |

## Repo-Zugehörigkeit

| Repo | Rolle | Pfade |
|---|---|---|
| `platform` | Primär | `packages/creative-services/creative_services/storage/` |
| `platform` | Primär | `shared_contracts/content_events.py` |
| `mcp-hub` | Sekundär | `orchestrator_mcp/agent_team/`, `query_agent_mcp/` |
| `travel-beat` | Consumer B | `apps/stories/services.py` (via Django-Adapter) |
| `bfagent` | Consumer C | `apps/bfagent/services/` (via Django-Adapter) |

---

## Decision Drivers

- **Kein Agent-Gedächtnis**: Tech-Lead-Agent (ADR-059) verliert TaskPlans nach jedem Run — kein Audit-Trail
- **ADR-Compliance-Drift unsichtbar**: Drift-Detector loggt nur, schreibt nichts persistent
- **Kein Change-Safety-Context**: Vor Änderungen unklar welche Dateien betroffen, welche ADRs gelten
- **4 Consumer mit unterschiedlichen Anforderungen**: Agent-Team, DriftTales, bfagent, creative-services
- **Multi-Tenancy von Anfang an**: Nachträgliches `tenant_id` ist teuerste Migration (ADR-056)

---

## Context and Problem Statement

`creative-services` ist ein reiner Execution-Layer — jeder LLM-Call ist stateless, Content geht verloren. Kein gemeinsamer Store, keine Versionierung, keine persistierte ADR-Compliance.

```
HEUTE:
Agent-Team       bfagent DB       travel-beat DB
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ TaskPlans:  │  │ drafts(raw) │  │ chapters    │
│   verloren  │  │ kein Kontext│  │ (raw)       │
└─────────────┘  └─────────────┘  └─────────────┘
ADR-Compliance: nur geloggt, nie persistent
```

**Drei Probleme in Priorität:**

| Problem | Schwere | Lösbar in |
|---|---|---|
| **P1** Agent-Team hat kein Gedächtnis | Akut | Phase 1 |
| **P2** ADR-Compliance-Drift nicht erkannt | Wichtig | Phase 2 |
| **P3** Kein Change-Safety-Context | Nice-to-have | Phase 3 (nach Gate) |

**Consumer-Analyse:**

| Consumer | Content-Typ | Tenant | Versionierung | Prio |
|---|---|---|---|---|
| **A: Agent-Team** | TaskPlans, ImpactReports | NEIN (plattformweit) | JA | 1 |
| **B: DriftTales** | Story-Kapitel | JA (strikt) | JA | 3 |
| **C: bfagent** | Kapitel-Drafts | NEIN (single-tenant) | JA | 4 |
| **D: creative-services** | LLM-Metadaten | BEIDES | NEIN | 2 |

---

## Considered Options

### Option A: Shared PostgreSQL Schema `content_store.*` in `creative-services` ✅
Erweiterung des bestehenden Package um `storage/` Modul. Alembic-verwaltetes Schema in bestehender Postgres-Instanz. Kein neues Repo, kein neuer Service.

### Option B: Eigenes `content-hub` Repository
Neues Repo mit eigenem Django-Service, eigener DB, eigenem Docker-Container.

### Option C: `content_mcp` als primärer Datenspeicher
MCP-Server als zentraler Content-Store, direkt von Agents konsumiert.

### Option D: Event-basierter Index ohne zentralen Store
Eventual-Consistent-Index via Celery-Events, kein persistenter Store.

---

## Decision Outcome

**Gewählte Option: Option A** — Shared PostgreSQL Schema `content_store.*` in `creative-services`.

**Begründung:** Keine neue Infrastruktur, direkter Upgrade-Pfad, `tenant_id IS NULL` für plattformweite und `IS NOT NULL` für tenant-isolierte Inhalte in einem Schema. Klarer Migrationspfad zu eigenem Repo.

Implementierung in **3 Phasen mit expliziten Gates:**

| Phase | Inhalt | Gate | Löst |
|---|---|---|---|
| **1** | `items` + `relations` + Agent-Team-Pilot | — | P1 |
| **2** | `adr_compliance` + Drift-Detector-Persistenz | Phase 1 ≥1 Woche stabil | P2 |
| **3** | `code_graph_*` + `pre_change_check()` | Phase 1+2 ≥4 Wochen, explizite Entscheidung | P3 |

**Nicht in diesem ADR:** Infra-Snapshots, OpenClaw-Integration, `content-hub`-Repo.

---

## Pros and Cons of the Options

### Option A ✅
- **Pro:** Keine neue Infrastruktur, kein neuer SPOF
- **Pro:** `creative-services` bereits in `bfagent` + `travel-beat` installiert
- **Pro:** Ein Schema, zwei Modi (`tenant_id IS NULL` / `IS NOT NULL`)
- **Pro:** Alembic — sauberes Schema-Deployment mit Rollback
- **Con:** Shared DB — Content-Store-Queries belasten dieselbe Postgres-Instanz
- **Con:** Schema-Änderungen betreffen alle Consumer (Expand-Contract Pflicht)

### Option B
- **Pro:** Vollständige Isolation, eigene Skalierung
- **Con:** Neuer SPOF, Trigger-Bedingungen heute nicht erfüllt, Overengineering
- **Abgelehnt** — als Migrationsziel mit messbaren Trigger-Bedingungen definiert

### Option C
- **Pro:** Direkt von Agents konsumierbar
- **Con:** MCP ist LLM-Tool-Protokoll, kein Service-to-Service-Protokoll; Django-Apps können MCP nicht direkt aufrufen
- **Abgelehnt** — MCP bleibt Zugangsschicht (Phase 3), nicht Datenspeicher

### Option D
- **Pro:** Lose Kopplung
- **Con:** Eventual Consistency löst P1 nicht — Agent braucht synchronen Zugriff
- **Abgelehnt als primäre Strategie**

---

## Implementation Details

### R2: Schema-Deployment via Alembic (nicht Django-Migrations)

`creative-services` ist kein Django-App — das Schema wird via **Alembic** verwaltet:

```
packages/creative-services/
  creative_services/storage/
    alembic/
      env.py
      versions/
        0001_create_content_store.py   ← Phase 1
        0002_add_adr_compliance.py     ← Phase 2
        0003_add_code_graph.py         ← Phase 3
    models.py
    store.py
    django_adapter.py                  ← R3
```

```bash
alembic upgrade head    # Deployment
alembic downgrade -1    # Rollback (additive-only → kein Datenverlust)
alembic current         # CI-Check: schlägt fehl wenn nicht auf head
```

### Phase 1: Content-Layer

```sql
CREATE SCHEMA IF NOT EXISTS content_store;

CREATE TABLE content_store.items (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    source_svc    TEXT        NOT NULL,
    source_type   TEXT        NOT NULL,
    source_id     TEXT        NOT NULL,
    tenant_id     UUID,
    content       TEXT        NOT NULL,
    content_hash  TEXT        NOT NULL,
    prompt_key    TEXT,
    model_used    TEXT        NOT NULL,
    version       INT         NOT NULL DEFAULT 1,
    parent_id     UUID        REFERENCES content_store.items(id) ON DELETE SET NULL,
    tags          TEXT[]      NOT NULL DEFAULT '{}',
    properties    JSONB       NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    embedding     vector(1536)
);

CREATE TABLE content_store.relations (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    source_item   UUID        NOT NULL REFERENCES content_store.items(id) ON DELETE CASCADE,
    target_ref    TEXT        NOT NULL,
    relation_type TEXT        NOT NULL,
    tenant_id     UUID,
    weight        FLOAT       NOT NULL DEFAULT 1.0,
    properties    JSONB       NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ON content_store.items (source_svc, source_type, source_id);
CREATE INDEX ON content_store.items (tenant_id) WHERE tenant_id IS NOT NULL;
CREATE INDEX ON content_store.items USING GIN (tags);
CREATE INDEX ON content_store.relations (source_item, relation_type);
CREATE INDEX ON content_store.relations (target_ref);

CREATE VIEW content_store.v_decisions AS
    SELECT * FROM content_store.items WHERE source_svc = 'agent-team' AND tenant_id IS NULL;

CREATE VIEW content_store.v_drafts AS
    SELECT *, ROW_NUMBER() OVER (PARTITION BY source_id ORDER BY version DESC) AS version_rank
    FROM content_store.items WHERE source_svc = 'bfagent';
```

**Pydantic-Modelle** (`creative_services/storage/models.py`):

```python
from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field

SourceService = Literal["agent-team", "bfagent", "travel-beat", "creative-services"]
SourceType = Literal[
    "task_plan", "impact_report", "code_review", "adr_analysis",
    "chapter", "story", "scene", "character_description",
    "draft", "draft_variant", "llm_execution", "prompt_result",
]

class ContentItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: UUID = Field(default_factory=uuid4)
    source_svc: SourceService
    source_type: SourceType
    source_id: str
    tenant_id: UUID | None = Field(default=None)
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
    relation_type: Literal["implements","references","derived_from","tested_by","appears_in","located_in"]
    tenant_id: UUID | None = None
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: dict[str, Any] = Field(default_factory=dict)
```

### R3: Django-Adapter für Consumer B+C

`asyncpg` ist nicht Django-ORM-kompatibel. `bfagent` und `travel-beat` brauchen einen synchronen Wrapper:

```python
# creative_services/storage/django_adapter.py
import asyncio
from .store import ContentStore
from .models import ContentItem, ContentRelation

class SyncContentStore:
    """Synchroner Wrapper fuer Django-Apps (bfagent, travel-beat).
    WARNUNG: Nicht in async Django-Views verwenden (ASGI-Konflikt).
    """
    def __init__(self) -> None:
        self._store = ContentStore()

    def save(self, item: ContentItem) -> ContentItem:
        return asyncio.run(self._store.save(item))

    def latest(self, source_svc: str, source_id: str) -> ContentItem | None:
        return asyncio.run(self._store.latest(source_svc, source_id))

    def add_relation(self, relation: ContentRelation) -> ContentRelation:
        return asyncio.run(self._store.add_relation(relation))
```

### Phase 2: Compliance-Layer (Gate: Phase 1 ≥1 Woche stabil)

```sql
CREATE TABLE content_store.adr_compliance (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    adr_id      TEXT        NOT NULL,
    adr_status  TEXT        NOT NULL,
    repo        TEXT        NOT NULL,
    impl_status TEXT        NOT NULL,
    drift_score FLOAT       NOT NULL DEFAULT 0.0,
    checked_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    evidence    JSONB       NOT NULL DEFAULT '{}',
    checker     TEXT        NOT NULL
);

CREATE INDEX ON content_store.adr_compliance (adr_id, repo);
CREATE INDEX ON content_store.adr_compliance (impl_status) WHERE impl_status != 'compliant';
CREATE INDEX ON content_store.adr_compliance (checked_at DESC);

CREATE VIEW content_store.v_adr_current AS
    SELECT DISTINCT ON (adr_id, repo)
        adr_id, repo, adr_status, impl_status, drift_score, checked_at, evidence
    FROM content_store.adr_compliance ORDER BY adr_id, repo, checked_at DESC;

CREATE VIEW content_store.v_adr_violations AS
    SELECT * FROM content_store.v_adr_current WHERE impl_status = 'violated';
```

### R4: GitHub Actions mit `permissions:`

```yaml
# .github/workflows/compliance-check.yml
name: ADR Compliance Check
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  compliance:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2
      - name: Get changed files
        id: diff
        run: |
          echo "files=$(git diff --name-only HEAD~1 HEAD | tr '\n' ',')" >> $GITHUB_OUTPUT
      - name: Run drift detector with persistence
        run: |
          python -m orchestrator_mcp.drift_detector \
            --repo ${{ github.event.repository.name }} \
            --changed-files "${{ steps.diff.outputs.files }}" \
            --persist
        env:
          CONTENT_STORE_DSN: ${{ secrets.CONTENT_STORE_DSN }}
```

**Secret:** `CONTENT_STORE_DSN` als **org-level Secret** (ADR-045-konform), nicht per-repo.

### Phase 3: Code-Graph-Layer (Gate: Phase 1+2 ≥4 Wochen, explizite Entscheidung)

```sql
CREATE TABLE content_store.code_graph_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo TEXT NOT NULL, file_path TEXT NOT NULL,
    node_type TEXT NOT NULL, node_name TEXT NOT NULL,
    git_sha TEXT NOT NULL, is_stale BOOL NOT NULL DEFAULT FALSE,
    properties JSONB NOT NULL DEFAULT '{}',
    scanned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (repo, file_path, node_name, git_sha)
);

CREATE TABLE content_store.code_graph_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node UUID NOT NULL REFERENCES content_store.code_graph_nodes(id) ON DELETE CASCADE,
    target_node UUID NOT NULL REFERENCES content_store.code_graph_nodes(id) ON DELETE CASCADE,
    edge_type TEXT NOT NULL, repo TEXT NOT NULL, properties JSONB NOT NULL DEFAULT '{}'
);

CREATE VIEW content_store.v_redundancy_candidates AS
    SELECT node_name, node_type, repo, COUNT(*) AS occurrences,
           ARRAY_AGG(file_path ORDER BY file_path) AS locations
    FROM content_store.code_graph_nodes WHERE node_type IN ('function','class')
    GROUP BY node_name, node_type, repo HAVING COUNT(*) > 1;

CREATE VIEW content_store.v_file_dependents AS
    SELECT src.file_path AS changed_file, tgt.file_path AS dependent_file, e.edge_type, src.repo
    FROM content_store.code_graph_edges e
    JOIN content_store.code_graph_nodes src ON e.source_node = src.id
    JOIN content_store.code_graph_nodes tgt ON e.target_node = tgt.id;
```

---

## Technology Perspectives (Future Scope)

### OpenClaw als Human-Gate-Layer (Phase 4, eigenes ADR)

OpenClaw (https://github.com/openclaw/openclaw) ist ein selbst-gehosteter Personal AI Assistant mit Channels (Telegram, Slack), Agent-to-Agent-Koordination und Skills-Registry. Läuft auf `88.198.191.108` — direkter Zugriff auf `content_store.*`. Guardian-Agent kann `v_adr_violations` als Trigger für Telegram-Notifications nutzen. **Voraussetzung:** Phase 1+2+3 stabil. Eigenes ADR.

### Infra-Snapshots (Phase 4, eigenes ADR)

Stündliche Snapshots via `deployment_mcp`. Erst sinnvoll wenn Phase 3 stabil.

### Migration zu `content-hub` (Phase 5)

Eigenes Repo wenn **mindestens 2** erfüllt: ≥5 Consumer, >5 GB, >25% DB-Last, Business-Logik. Schema bleibt identisch — Zugangspfad ändert sich.

---

## Migration Tracking

| Phase | Komponente | Status | Gate |
|---|---|---|---|
| **1** | Alembic-Setup + `0001_create_content_store.py` | ⬜ | — |
| **1** | `creative_services/storage/models.py` | ⬜ | — |
| **1** | `creative_services/storage/store.py` | ⬜ | — |
| **1** | `creative_services/storage/django_adapter.py` | ⬜ | — |
| **1** | `shared_contracts/content_events.py` | ⬜ | — |
| **1** | Agent-Team Pilot: `tech_lead.py` | ⬜ | Schema live |
| **2** | Alembic `0002_add_adr_compliance.py` | ⬜ | Phase 1 ≥1 Woche stabil |
| **2** | Drift-Detector: `--persist` Flag | ⬜ | Schema live |
| **2** | `.github/workflows/compliance-check.yml` | ⬜ | Self-Hosted Runner aktiv |
| **2** | `CONTENT_STORE_DSN` org-level Secret | ⬜ | ADR-045-konform |
| **3** | Alembic `0003_add_code_graph.py` | ⬜ | Phase 1+2 ≥4 Wochen stabil |
| **3** | `query_agent_mcp/ast_walker.py` | ⬜ | Schema live |
| **3** | Guardian `pre_change_check()` | ⬜ | Code-Graph befüllt |
| **4** | OpenClaw Human-Gate | ⬜ | Eigenes ADR |
| **5** | `content-hub` Repo | ⬜ | Trigger-Bedingungen erfüllt |

---

## Consequences

### Good

- **P1 sofort lösbar**: Phase 1 ~2 Tage, sofort messbarer Wert
- **P2 in Woche 3–4**: ~10 LOC Drift-Detector + 1 GitHub Action
- **Keine neue Infrastruktur**: Postgres-Schema in bestehender DB
- **Alembic**: Sauberes Schema-Deployment, Rollback via `downgrade`, CI-Check via `current`
- **Django-Adapter**: Consumer B+C vollständig abgedeckt via `SyncContentStore`
- **Klare Gates**: Phase 3 nur nach expliziter Entscheidung
- **OpenClaw-Pfad offen**: Dokumentiert, nicht verbaut, nicht erzwungen
- **LLM-Provider-agnostisch**: `AsyncOpenAI(base_url=...)` — Ollama lokal oder Cloud

### Bad

- **Shared DB**: `pg_stat_statements` Monitoring Pflicht ab Phase 2
- **`SyncContentStore` + ASGI**: `asyncio.run()` in async Django-Views → Deadlock-Risiko; Linting-Rule erforderlich
- **AST-Walker unvollständig**: Dynamische Imports nicht erkannt — explizit dokumentiert
- **Alembic neben Django-Migrations**: Zweites Migration-Tool, Schulungsaufwand

### Nicht in diesem ADR

- Live-Monitoring, OpenClaw, Infra-Snapshots, Cross-Tenant-Graph, Medien/Assets

---

## Risks

| Risiko | W'keit | Impact | Mitigation |
|---|---|---|---|
| Phase-3-Gate ignoriert | Mittel | Hoch | Gate: explizite Entscheidung in ADR dokumentieren |
| Shared DB Bottleneck | Mittel | Hoch | `pg_stat_statements`, Trigger §Migration |
| `SyncContentStore` in async View → Deadlock | Niedrig | Hoch | Linting-Rule: `asyncio.run()` in Views verboten |
| Alembic nicht applied → Schema-Drift | Niedrig | Hoch | CI: `alembic current` schlägt fehl wenn nicht auf `head` |
| `tenant_id IS NULL` für tenant-gebundene Daten | Niedrig | Kritisch | Pydantic-Validator: TENANT_SERVICES erzwingt tenant_id |
| OpenClaw zu früh → Komplexität ohne Basis | Mittel | Mittel | Gate: erst wenn Phase 1+2+3 stabil |

---

## Confirmation

1. **Alembic-CI-Check**: `alembic current` in CI — blockiert Merge wenn Schema nicht auf `head`
2. **Tenant-Isolation**: `test_should_not_leak_content_across_tenants`
3. **Versionierungs-Test**: `test_should_create_new_version_on_save`
4. **Null-Tenant-Test**: `test_should_allow_null_tenant_for_platform_content`
5. **Django-Adapter-Test**: `test_should_save_via_sync_store_from_django_service`
6. **Compliance-Persistenz**: `test_should_persist_drift_detector_results` (Phase 2)
7. **Redundanz-Erkennung**: `test_should_detect_duplicate_function_names` (Phase 3)
8. **Drift-Detector**: Staleness-Schwelle 12 Monate

---

## More Information

- ADR-056: Multi-Tenancy Schema Isolation — `tenant_id`-Muster und Erfahrungen
- ADR-059: Agent-Team — Consumer A, Drift-Detector-Erweiterung
- ADR-045: Secrets Management — `CONTENT_STORE_DSN` org-level Secret
- ADR-014: AI-Native Development — Kontext für Consumer A
- [asyncpg Dokumentation](https://magicstack.github.io/asyncpg/)
- [Alembic Dokumentation](https://alembic.sqlalchemy.org/)
- [pgvector](https://github.com/pgvector/pgvector)
- [OpenClaw](https://github.com/openclaw/openclaw) — Phase-4-Perspektive

---

## Changelog

| Datum | Autor | Änderung |
|---|---|---|
| 2026-02-22 | Achim Dehnert | Initial: Content-Layer |
| 2026-02-22 | Achim Dehnert | Amendment 1: 4-Schichten-Architektur |
| 2026-02-22 | Achim Dehnert | Amendment 2: Delta-Minimierung, ereignisgesteuert |
| 2026-02-22 | Achim Dehnert | Final: 3 Phasen mit Gates, OpenClaw Phase-4-Perspektive |
| 2026-02-22 | Achim Dehnert | Review-Fix: MADR-4.0-konform (R1–R4), Alembic, Django-Adapter, permissions |

---

<!--
  Drift-Detector-Felder (ADR-059):
  - staleness_months: 12
  - drift_check_paths:
      - platform/packages/creative-services/creative_services/storage/
      - platform/shared_contracts/content_events.py
      - mcp-hub/orchestrator_mcp/agent_team/
      - mcp-hub/query_agent_mcp/ast_walker.py
  - supersedes_check: true
-->
