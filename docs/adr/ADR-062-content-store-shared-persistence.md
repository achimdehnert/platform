---
status: proposed
date: 2026-02-22
decision-makers: Achim Dehnert
consulted: –
informed: –
---

# ADR-062: Content Store — Shared PostgreSQL Schema für AI-generierten Content

## Metadaten

| Attribut          | Wert |
|-------------------|------|
| **Status**        | Proposed |
| **Scope**         | platform-wide |
| **Erstellt**      | 2026-02-22 |
| **Autor**         | Achim Dehnert |
| **Relates to**    | ADR-056 (Multi-Tenancy), ADR-059 (Agent-Team), ADR-014 (AI-Native Dev) |

## Repo-Zugehörigkeit

| Repo | Rolle | Pfade |
|---|---|---|
| `platform` | Primär | `packages/creative-services/creative_services/storage/` |
| `platform` | Primär | `shared_contracts/content_events.py` |
| `mcp-hub` | Sekundär | `orchestrator_mcp/agent_team/`, `query_agent_mcp/` |
| `travel-beat` | Consumer B | `apps/stories/services.py` |
| `bfagent` | Consumer C | `apps/bfagent/services/` |

---

## 1. Problem

### 1.1 Drei ungelöste Probleme

**Problem 1 — Kein Agent-Gedächtnis (akut):**
Der Tech-Lead-Agent (ADR-059) plant Tasks, generiert ImpactReports, trifft Entscheidungen — und verliert alles nach jedem Run. Kein Audit-Trail, kein Kontext für Folge-Runs.

**Problem 2 — ADR-Compliance-Drift nicht erkannt (wichtig):**
ADRs werden geschrieben, Implementierungen driften ab. Heute: kein systematischer, persistierter Compliance-Check. Der Drift-Detector (ADR-059) existiert, loggt aber nur — schreibt nichts persistent.

**Problem 3 — Kein Change-Safety-Context (nice-to-have):**
Vor einer Änderung ist unklar: Welche Dateien sind betroffen? Welche ADRs gelten? Gibt es Redundanzen? Sind Migrations pending?

```
HEUTE:
Agent-Team     bfagent DB      travel-beat DB
┌──────────┐   ┌────────────┐  ┌────────────┐
│TaskPlans:│   │drafts(raw) │  │chapters    │
│  verloren│   │kein Kontext│  │(raw)       │
└──────────┘   └────────────┘  └────────────┘
     ↑ Problem 1    ↑ Problem 3     ↑ Problem 3
ADR-Compliance: nur geloggt, nie persistent → Problem 2
```

### 1.2 Consumer mit unterschiedlichen Anforderungen

| Consumer | Content-Typ | Tenant | Versionierung | Priorität |
|---|---|---|---|---|
| **A: Agent-Team** | TaskPlans, ImpactReports, Reviews | NEIN (plattformweit) | JA (Audit) | **1 — sofort** |
| **B: DriftTales** | Story-Kapitel, Reisebeschreibungen | JA (strikt) | JA | 3 |
| **C: bfagent** | Kapitel-Drafts, Varianten | NEIN (single-tenant) | JA (A/B) | 4 |
| **D: creative-services** | LLM-Metadaten, Scores | BEIDES | NEIN | 2 |

---

## 2. Entscheidung

**Shared PostgreSQL Schema `content_store.*` in `creative-services`** — kein neues Repo, keine neue Infrastruktur.

Implementierung in **3 Phasen mit expliziten Gates**:

| Phase | Was | Gate | Wert |
|---|---|---|---|
| **Phase 1** | `items` + `relations` + Agent-Team-Integration | Agent-Team-TaskPlans persistent | Problem 1 gelöst |
| **Phase 2** | `adr_compliance` + ereignisgesteuerter Drift-Detector | ADR-Violations in DB, Delta <1min | Problem 2 gelöst |
| **Phase 3** | `code_graph_*` + `pre_change_check()` | Nur wenn Phase 1+2 stabil ≥4 Wochen | Problem 3 gelöst |

**Nicht in diesem ADR:** Infra-Snapshots, OpenClaw-Integration, `content-hub`-Repo — separate Entscheidungen mit eigenen ADRs.

---

## 3. Implementation

### 3.1 Phase 1: Content-Layer (Woche 1–2)

```sql
CREATE SCHEMA IF NOT EXISTS content_store;

CREATE TABLE content_store.items (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    source_svc    TEXT        NOT NULL,   -- 'agent-team' | 'bfagent' | 'travel-beat'
    source_type   TEXT        NOT NULL,   -- 'task_plan' | 'chapter' | 'draft'
    source_id     TEXT        NOT NULL,
    tenant_id     UUID,                   -- NULL = plattformweit (Agent-Team)
    content       TEXT        NOT NULL,
    content_hash  TEXT        NOT NULL,   -- SHA-256, Deduplizierung
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
    target_ref    TEXT        NOT NULL,   -- "adr:ADR-059" | "file:apps/trips/models.py"
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
CREATE INDEX ON content_store.items USING GIN (tags);
CREATE INDEX ON content_store.relations (source_item, relation_type);
CREATE INDEX ON content_store.relations (target_ref);

-- Consumer-Views
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
    "draft", "draft_variant",
    "llm_execution", "prompt_result",
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
    relation_type: Literal[
        "implements", "references", "derived_from",
        "tested_by", "appears_in", "located_in",
    ]
    tenant_id: UUID | None = None
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: dict[str, Any] = Field(default_factory=dict)
```

**ContentStore API** (`creative_services/storage/store.py`):

```python
class ContentStore:
    """Asyncpg-basiert, kein Django ORM."""

    async def save(self, item: ContentItem) -> ContentItem: ...
    async def get(self, item_id: UUID) -> ContentItem | None: ...
    async def get_versions(self, source_svc: str, source_id: str) -> list[ContentItem]: ...
    async def latest(self, source_svc: str, source_id: str) -> ContentItem | None: ...
    async def add_relation(self, relation: ContentRelation) -> ContentRelation: ...
    async def find_by_ref(self, target_ref: str, ...) -> list[ContentItem]: ...
    async def search(self, query: str, ...) -> list[ContentItem]: ...
```

**Pilot: Agent-Team** (`orchestrator_mcp/agent_team/tech_lead.py`):

```python
async def plan_from_adr(adr_path: str) -> TaskPlan:
    plan = await _parse_and_plan(adr_path)
    store = ContentStore()
    item = await store.save(ContentItem(
        source_svc="agent-team",
        source_type="task_plan",
        source_id=f"adr:{adr_path}",
        tenant_id=None,
        content=plan.model_dump_json(),
        content_hash=_sha256(plan.model_dump_json()),
        model_used="claude-opus-4",
        tags=["task_plan", "adr"],
    ))
    await store.add_relation(ContentRelation(
        source_item=item.id,
        target_ref=f"adr:{adr_path}",
        relation_type="implements",
    ))
    return plan
```

### 3.2 Phase 2: Compliance-Layer (Woche 3–4)

**Gate für Phase 2:** Phase 1 läuft ≥1 Woche stabil, Agent-Team-TaskPlans sind in DB.

```sql
CREATE TABLE content_store.adr_compliance (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    adr_id       TEXT        NOT NULL,
    adr_status   TEXT        NOT NULL,   -- 'proposed' | 'accepted' | 'deprecated'
    repo         TEXT        NOT NULL,
    impl_status  TEXT        NOT NULL,   -- 'compliant' | 'pending' | 'violated' | 'n_a'
    drift_score  FLOAT       NOT NULL DEFAULT 0.0,
    checked_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    evidence     JSONB       NOT NULL DEFAULT '{}',
    checker      TEXT        NOT NULL    -- 'drift_detector' | 'ci_gate' | 'manual'
);

CREATE INDEX ON content_store.adr_compliance (adr_id, repo);
CREATE INDEX ON content_store.adr_compliance (impl_status) WHERE impl_status != 'compliant';
CREATE INDEX ON content_store.adr_compliance (checked_at DESC);

-- Aktuellster Stand pro ADR+Repo
CREATE VIEW content_store.v_adr_current AS
    SELECT DISTINCT ON (adr_id, repo)
        adr_id, repo, adr_status, impl_status, drift_score, checked_at, evidence
    FROM content_store.adr_compliance
    ORDER BY adr_id, repo, checked_at DESC;

-- Alle verletzten ADRs (für pre_change_check)
CREATE VIEW content_store.v_adr_violations AS
    SELECT * FROM content_store.v_adr_current
    WHERE impl_status = 'violated'
    ORDER BY drift_score DESC;
```

**Ereignisgesteuerter Drift-Detector** (Self-Hosted Runner auf `88.198.191.108`):

```yaml
# .github/workflows/compliance-check.yml
name: ADR Compliance Check
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  compliance:
    runs-on: self-hosted        # Direkter Zugriff auf Postgres + lokale LLMs
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2

      - name: Get changed files
        id: diff
        run: |
          echo "files=$(git diff --name-only HEAD~1 HEAD | tr '\n' ',')" \
            >> $GITHUB_OUTPUT

      - name: Run drift detector
        run: |
          python -m orchestrator_mcp.drift_detector \
            --repo ${{ github.event.repository.name }} \
            --changed-files "${{ steps.diff.outputs.files }}" \
            --persist                    # NEU: schreibt in content_store statt nur loggen
        env:
          CONTENT_STORE_DSN: ${{ secrets.CONTENT_STORE_DSN }}
```

**Drift-Detector-Erweiterung** (bestehender Code, ~10 LOC Änderung):

```python
# orchestrator_mcp/drift_detector.py — bestehend, nur Persistenz ergänzen
async def run_compliance_check(adr_id: str, repo: str) -> ComplianceResult:
    result = await _check_adr_compliance(adr_id, repo)  # bestehende Logik

    if args.persist:                                      # NEU: Flag aus CLI
        store = ContentStore()
        await store.save_compliance(AdrCompliance(
            adr_id=adr_id,
            repo=repo,
            impl_status=result.impl_status,
            drift_score=result.drift_score,
            evidence=result.evidence,
            checker="drift_detector",
        ))
    return result
```

**Ergebnis:** ADR-Compliance-Delta sinkt von 24h auf <1 Minute.

**Optionale LLM-Enrichment-Stufe** (nur wenn regelbasierter Check stabil):

```python
# Stufe 1 (immer): Regelbasierter Drift-Detector → content_store
# Stufe 2 (optional): OpenAI-kompatibler Client für kontextuelle Bewertung
from openai import AsyncOpenAI

_llm = AsyncOpenAI(
    base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
    api_key=os.getenv("LLM_API_KEY", "ollama"),
)
# Modell via ENV wechselbar: Ollama lokal → Claude/GPT-4 cloud — gleicher Code
```

### 3.3 Phase 3: Code-Graph-Layer (nach Gate)

**Gate für Phase 3:** Phase 1+2 laufen ≥4 Wochen stabil. Explizite Entscheidung erforderlich.

```sql
CREATE TABLE content_store.code_graph_nodes (
    id         UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
    repo       TEXT  NOT NULL,
    file_path  TEXT  NOT NULL,
    node_type  TEXT  NOT NULL,   -- 'class' | 'function' | 'test'
    node_name  TEXT  NOT NULL,
    git_sha    TEXT  NOT NULL,
    is_stale   BOOL  NOT NULL DEFAULT FALSE,  -- Dirty-Flag: sofort bei Push gesetzt
    properties JSONB NOT NULL DEFAULT '{}',
    scanned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (repo, file_path, node_name, git_sha)
);

CREATE TABLE content_store.code_graph_edges (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node UUID NOT NULL REFERENCES content_store.code_graph_nodes(id) ON DELETE CASCADE,
    target_node UUID NOT NULL REFERENCES content_store.code_graph_nodes(id) ON DELETE CASCADE,
    edge_type   TEXT NOT NULL,   -- 'imports' | 'calls' | 'tested_by' | 'inherits'
    repo        TEXT NOT NULL,
    properties  JSONB NOT NULL DEFAULT '{}'
);

-- Redundanz-Kandidaten: gleicher Name, verschiedene Dateien
CREATE VIEW content_store.v_redundancy_candidates AS
    SELECT node_name, node_type, repo,
           COUNT(*) AS occurrences,
           ARRAY_AGG(file_path ORDER BY file_path) AS locations
    FROM content_store.code_graph_nodes
    WHERE node_type IN ('function', 'class')
    GROUP BY node_name, node_type, repo
    HAVING COUNT(*) > 1;

-- Direkte Abhängigkeiten einer Datei
CREATE VIEW content_store.v_file_dependents AS
    SELECT src.file_path AS changed_file,
           tgt.file_path AS dependent_file,
           e.edge_type, src.repo
    FROM content_store.code_graph_edges e
    JOIN content_store.code_graph_nodes src ON e.source_node = src.id
    JOIN content_store.code_graph_nodes tgt ON e.target_node = tgt.id;
```

---

## 4. Technologie-Perspektiven (Future Scope)

### 4.1 OpenClaw als Human-Gate-Layer (Phase 4, eigenes ADR)

OpenClaw (https://github.com/openclaw/openclaw) ist ein selbst-gehosteter Personal AI Assistant mit Channels (Telegram, Slack, Signal), Agent-to-Agent-Koordination und Skills-Registry.

**Relevanz für dieses System:** OpenClaw löst das Human-Gate-Problem aus ADR-059 elegant — der Guardian-Agent meldet ADR-Violations via Telegram, der Mensch approvet den Auto-Fix. Das ist **kein Teil von ADR-062**, sondern eine eigenständige Entscheidung die auf einem funktionierenden `content_store` aufbaut.

```
Voraussetzung für OpenClaw-Integration:
  Phase 1 live → Phase 2 live → ADR-059 Agent-Team operativ
  → Dann: OpenClaw als Notification + Human-Gate-Layer evaluieren
```

**Konkrete Synergie:** OpenClaw läuft auf `88.198.191.108` (Self-Hosted), hat direkten Zugriff auf `content_store.*` und kann `v_adr_violations` als Trigger für Telegram-Notifications nutzen. Skills (`pre_change_check`, `find_redundancies`) können im ClawHub registriert werden.

### 4.2 Infra-Snapshots (Phase 4, eigenes ADR)

Stündliche Snapshots von Container-Status, SSL-Ablauf und pending Migrations via `deployment_mcp`. Separate Tabelle `content_store.infra_snapshots`. Erst sinnvoll wenn Code-Graph (Phase 3) stabil — sonst fehlt der Kontext für sinnvolle Interpretation.

### 4.3 Migration zu `content-hub` (Phase 5)

Eigenes Repo wenn **mindestens 2** erfüllt:

| Trigger | Messgröße |
|---|---|
| Consumer-Zahl | >= 5 aktive Services |
| Volumen | > 5 GB im Schema |
| DB-Last | > 25% aller Queries |
| Business-Logik | Approval-Workflows, Lizenzierung |

Schema bleibt identisch — nur Zugangspfad ändert sich. Migration ist trivial.

---

## 5. Migration Tracking

| Phase | Komponente | Status | Gate |
|---|---|---|---|
| **1** | SQL-Schema `items` + `relations` | ⬜ Ausstehend | — |
| **1** | `creative_services/storage/models.py` | ⬜ Ausstehend | — |
| **1** | `creative_services/storage/store.py` | ⬜ Ausstehend | — |
| **1** | `shared_contracts/content_events.py` | ⬜ Ausstehend | — |
| **1** | Agent-Team Pilot: `tech_lead.py` | ⬜ Ausstehend | Schema live |
| **2** | SQL-Schema `adr_compliance` + Views | ⬜ Ausstehend | Phase 1 ≥1 Woche stabil |
| **2** | Drift-Detector: `--persist` Flag | ⬜ Ausstehend | Schema live |
| **2** | GitHub Actions `compliance-check.yml` | ⬜ Ausstehend | Self-Hosted Runner konfiguriert |
| **3** | SQL-Schema `code_graph_*` + Views | ⬜ Ausstehend | Phase 1+2 ≥4 Wochen stabil |
| **3** | `query_agent_mcp/ast_walker.py` | ⬜ Ausstehend | Schema live |
| **3** | Guardian `pre_change_check()` | ⬜ Ausstehend | Code-Graph befüllt |
| **4** | OpenClaw Human-Gate | ⬜ Ausstehend | Eigenes ADR, Phase 3 stabil |
| **4** | Infra-Snapshots | ⬜ Ausstehend | Eigenes ADR |
| **5** | `content-hub` Repo | ⬜ Ausstehend | Trigger-Bedingungen §4.3 |

---

## 6. Consequences

### 6.1 Good

- **Problem 1 sofort lösbar**: Phase 1 ist 2 Tage Arbeit, liefert sofort Wert
- **Problem 2 in Woche 3–4**: Drift-Detector-Erweiterung ist ~10 LOC Änderung + 1 GitHub Action
- **Keine neue Infrastruktur**: Postgres-Schema in bestehender DB
- **Klare Gates**: Kein Scope-Creep — Phase 3 startet nur wenn 1+2 stabil
- **OpenClaw-Pfad offen**: Perspektive ist dokumentiert, nicht verbaut, nicht erzwungen
- **LLM-Provider-agnostisch**: `AsyncOpenAI(base_url=...)` — Ollama lokal oder Cloud, gleicher Code

### 6.2 Bad

- **Shared DB**: Monitoring via `pg_stat_statements` Pflicht ab Phase 2
- **AST-Walker unvollständig**: Dynamische Imports (`__import__`, `importlib`) nicht erkannt — explizit dokumentiert
- **asyncpg-Dependency**: Kein Django ORM — Connection-Management erforderlich

### 6.3 Explizit nicht in diesem ADR

- Live-Monitoring (Prometheus/Grafana) — Ops-Tool, separates ADR
- OpenClaw-Integration — Phase 4, eigenes ADR
- Infra-Snapshots — Phase 4, eigenes ADR
- Cross-Tenant-Graph — DSGVO-Konflikt, ausgeschlossen
- Medien/Assets — separates ADR

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|---|---|---|---|
| Phase-3-Gate wird ignoriert → Scope-Creep | Mittel | Hoch | Gate explizit: Entscheidung dokumentieren wenn Phase 1+2 <4 Wochen stabil |
| Shared DB Bottleneck | Mittel | Hoch | `pg_stat_statements`, Trigger §4.3 |
| Drift-Detector schreibt nicht persistent | Niedrig | Hoch | CI-Gate: `v_adr_current` muss Einträge haben |
| `tenant_id IS NULL` für tenant-gebundene Daten | Niedrig | Kritisch | Pydantic-Validator: TENANT_SERVICES erzwingt tenant_id |
| OpenClaw-Integration zu früh → Komplexität ohne Basis | Mittel | Mittel | Gate: erst wenn Phase 1+2+3 stabil |

---

## 8. Confirmation

1. **Schema-Test (CI)**: `content_store.items` + `content_store.relations` existieren — blockiert Merge
2. **Tenant-Isolation**: `test_should_not_leak_content_across_tenants`
3. **Versionierungs-Test**: `test_should_create_new_version_on_save`
4. **Null-Tenant-Test**: `test_should_allow_null_tenant_for_platform_content`
5. **Compliance-Persistenz**: `test_should_persist_drift_detector_results` (Phase 2)
6. **Redundanz-Erkennung**: `test_should_detect_duplicate_function_names` (Phase 3)
7. **Drift-Detector**: Staleness-Schwelle 12 Monate

---

## 9. Changelog

| Datum | Autor | Änderung |
|---|---|---|
| 2026-02-22 | Achim Dehnert | Initial: Content-Layer (Schicht 1) |
| 2026-02-22 | Achim Dehnert | Amendment 1: 4-Schichten-Architektur |
| 2026-02-22 | Achim Dehnert | Amendment 2: Delta-Minimierung, ereignisgesteuert |
| 2026-02-22 | Achim Dehnert | Final: Konsolidiert — 3 Phasen mit Gates, OpenClaw als Phase-4-Perspektive |

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
