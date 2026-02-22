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

- **Kein Content-Memory**: `creative-services` ist ein reiner Execution-Layer — jeder LLM-Call ist stateless, generierter Content geht verloren
- **4 aktive Consumer** mit unterschiedlichen Anforderungen: AI-Agent-Team, DriftTales, bfagent, creative-services selbst
- **ADR-059 Context-Problem**: Der Tech-Lead-Agent hat ohne persistierten Content kein Gedächtnis
- **Keine Redundanz-Erkennung**: Doppelte Implementierungen und widersprüchliche ADR-Compliance werden nicht systematisch erkannt
- **Kein Change-Safety-Context**: Vor jeder Änderung ist unklar welche Dateien, Tests und ADRs betroffen sind
- **Multi-Tenancy von Anfang an**: Nachträgliches Einbauen von `tenant_id` ist die teuerste Migration (Erfahrung ADR-056)

---

## 1. Context and Problem Statement

### 1.1 Ist-Zustand

Das Platform-Package `creative-services` stellt einen vollständigen AI-Execution-Layer bereit. **Was fehlt:** Persistenz und Kontext. Es gibt keinen gemeinsamen Content-Store, keine Versionierung, keinen Code-Graphen und keine systematische ADR-Compliance-Verfolgung.

```
HEUTE — vollständige Isolation + kein Change-Safety-Context:

bfagent DB          travel-beat DB        agent-team (kein Store)
┌──────────────┐    ┌──────────────┐      ┌──────────────────────┐
│ drafts (raw) │    │ chapters(raw)│      │ TaskPlans:    weg    │
│ kein Kontext │    │ kein Kontext │      │ ImpactReports: weg   │
└──────────────┘    └──────────────┘      └──────────────────────┘

Vor jeder Änderung unklar:
  - Welche anderen Dateien importieren das geänderte Modul?
  - Welche Tests decken es ab?
  - Welche ADRs gelten dafür?
  - Gibt es redundante Implementierungen?
  - Sind pending Migrations vorhanden?
```

### 1.2 Consumer-Analyse

| Consumer | Content-Typ | Tenant | Versionierung | Graph | Volumen |
|---|---|---|---|---|---|
| **A: AI-Agent-Team** | DecisionContent — TaskPlans, ImpactReports | NEIN | JA (Audit-Trail) | JA | Niedrig |
| **B: DriftTales** | NarrativeContent — Story-Kapitel | JA (strikt) | JA | NEIN | Hoch |
| **C: bfagent** | DraftContent — Kapitel-Drafts, Varianten | NEIN | JA (A/B) | NEIN | Mittel |
| **D: creative-services** | ExecutionContent — LLM-Metadaten | BEIDES | NEIN | NEIN | Sehr hoch |

### 1.3 Warum jetzt

ADR-059 Agent-Team braucht persistenten Kontext. Zusätzlich: Jede Änderung soll auf dem aktuellen Stand aufsetzen und Redundanzen erkennen — das erfordert persistierten Kontext über Code, Infra und ADR-Compliance.

---

## 2. Considered Options

### Option A: Shared PostgreSQL Schema `content_store.*` in `creative-services` ✅

Erweiterung um `storage/`, `graph/`, `compliance/` und `snapshot/` Module. Kein neuer Service, kein neues Repo.

**Pros:** Keine neue Infrastruktur, direkter Upgrade-Pfad, ein Schema für plattformweite und tenant-isolierte Inhalte, klarer Migrationspfad zu eigenem Repo.

**Cons:** Shared DB-Last, koordiniertes Versioning nötig.

### Option B: Eigenes `content-hub` Repository

**Abgelehnt:** Trigger-Bedingungen heute nicht erfüllt. Wird als Migrationsziel mit expliziten Trigger-Bedingungen (§4.7) definiert.

### Option C: `content_mcp` als primärer Datenspeicher

**Abgelehnt:** MCP ist LLM-Tool-Protokoll, kein Service-to-Service-Protokoll. Bleibt Zugangsschicht (Phase 3).

### Option D: Event-basierter Index ohne zentralen Store

**Abgelehnt als primäre Strategie:** Eventual Consistency löst das ADR-059 Context-Problem nicht.

---

## 3. Decision Outcome

**Gewählte Option: Option A — 4-Schichten-Architektur in `content_store.*`**

`creative-services` wird zum **Change-Safety-Context-System** erweitert:

| Schicht | Tabellen | Befüllt durch | Aktualität |
|---|---|---|---|
| **1 Content** | `items`, `relations` | LLM-Calls, Agent-Team | Bei Generierung |
| **2 Compliance** | `adr_compliance` | Drift-Detector (ADR-059) | Täglich |
| **3 Code-Graph** | `code_graph_nodes`, `code_graph_edges` | AST-Walker bei Git-Push | Bei jedem Push |
| **4 Infra-Snapshot** | `infra_snapshots` | Infra-Poller | Stündlich |

---

## 4. Implementation Details

### 4.1 Schicht 1: Content-Layer

```sql
CREATE SCHEMA IF NOT EXISTS content_store;

CREATE TABLE content_store.items (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    source_svc    TEXT        NOT NULL,
    source_type   TEXT        NOT NULL,
    source_id     TEXT        NOT NULL,
    tenant_id     UUID,                   -- NULL = plattformweit
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
    embedding     vector(1536)
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

CREATE INDEX ON content_store.items (source_svc, source_type, source_id);
CREATE INDEX ON content_store.items (tenant_id) WHERE tenant_id IS NOT NULL;
CREATE INDEX ON content_store.items (parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX ON content_store.items USING GIN (tags);
CREATE INDEX ON content_store.relations (source_item, relation_type);
CREATE INDEX ON content_store.relations (target_ref);

CREATE VIEW content_store.v_decisions AS
    SELECT * FROM content_store.items
    WHERE source_svc = 'agent-team' AND tenant_id IS NULL;

CREATE VIEW content_store.v_drafts AS
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY source_id ORDER BY version DESC
    ) AS version_rank
    FROM content_store.items WHERE source_svc = 'bfagent';
```

### 4.2 Schicht 2: Compliance-Layer

Befüllt durch den **ADR-Drift-Detector** (`mcp-hub/orchestrator_mcp/`) — der bereits existiert, aber Ergebnisse nur loggt. Erweiterung: Persistenz in `adr_compliance`.

```sql
CREATE TABLE content_store.adr_compliance (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    adr_id       TEXT        NOT NULL,    -- 'ADR-056'
    adr_status   TEXT        NOT NULL,    -- 'proposed' | 'accepted' | 'deprecated'
    repo         TEXT        NOT NULL,    -- 'travel-beat', 'bfagent'
    impl_status  TEXT        NOT NULL,    -- 'compliant' | 'pending' | 'violated' | 'n_a'
    drift_score  FLOAT       NOT NULL DEFAULT 0.0,
    checked_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    evidence     JSONB       NOT NULL DEFAULT '{}',
    checker      TEXT        NOT NULL    -- 'drift_detector' | 'ci_gate' | 'manual'
);

CREATE INDEX ON content_store.adr_compliance (adr_id, repo);
CREATE INDEX ON content_store.adr_compliance (impl_status) WHERE impl_status != 'compliant';
CREATE INDEX ON content_store.adr_compliance (checked_at DESC);

CREATE VIEW content_store.v_adr_current AS
    SELECT DISTINCT ON (adr_id, repo)
        adr_id, repo, adr_status, impl_status, drift_score, checked_at, evidence
    FROM content_store.adr_compliance
    ORDER BY adr_id, repo, checked_at DESC;

CREATE VIEW content_store.v_adr_violations AS
    SELECT * FROM content_store.v_adr_current
    WHERE impl_status = 'violated'
    ORDER BY drift_score DESC;
```

### 4.3 Schicht 3: Code-Graph-Layer

AST-Walker (Python stdlib `ast`, ~100 LOC). Befüllt bei jedem Git-Push via GitHub Actions.

```sql
CREATE TABLE content_store.code_graph_nodes (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    repo         TEXT        NOT NULL,
    file_path    TEXT        NOT NULL,
    node_type    TEXT        NOT NULL,   -- 'module' | 'class' | 'function' | 'test'
    node_name    TEXT        NOT NULL,
    git_sha      TEXT        NOT NULL,
    properties   JSONB       NOT NULL DEFAULT '{}',
    scanned_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (repo, file_path, node_name, git_sha)
);

CREATE TABLE content_store.code_graph_edges (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node  UUID        NOT NULL REFERENCES content_store.code_graph_nodes(id) ON DELETE CASCADE,
    target_node  UUID        NOT NULL REFERENCES content_store.code_graph_nodes(id) ON DELETE CASCADE,
    edge_type    TEXT        NOT NULL,   -- 'imports' | 'calls' | 'tested_by' | 'inherits'
    repo         TEXT        NOT NULL,
    properties   JSONB       NOT NULL DEFAULT '{}'
);

CREATE INDEX ON content_store.code_graph_nodes (repo, file_path);
CREATE INDEX ON content_store.code_graph_nodes (node_type, repo);
CREATE INDEX ON content_store.code_graph_edges (source_node, edge_type);
CREATE INDEX ON content_store.code_graph_edges (target_node, edge_type);

-- Direkte Abhängigkeiten einer Datei (Pre-Change-Impact)
CREATE VIEW content_store.v_file_dependents AS
    SELECT
        src.file_path  AS changed_file,
        tgt.file_path  AS dependent_file,
        e.edge_type,
        src.repo
    FROM content_store.code_graph_edges e
    JOIN content_store.code_graph_nodes src ON e.source_node = src.id
    JOIN content_store.code_graph_nodes tgt ON e.target_node = tgt.id;

-- Redundanz-Kandidaten: gleicher Name, verschiedene Dateien
CREATE VIEW content_store.v_redundancy_candidates AS
    SELECT
        node_name, node_type, repo,
        COUNT(*) AS occurrences,
        ARRAY_AGG(file_path ORDER BY file_path) AS locations
    FROM content_store.code_graph_nodes
    WHERE node_type IN ('function', 'class')
    GROUP BY node_name, node_type, repo
    HAVING COUNT(*) > 1
    ORDER BY occurrences DESC;
```

### 4.4 Schicht 4: Snapshot-Layer

Stündliche Snapshots via Celery Beat. **Der Store ist immer Spiegel, nie Original** — das ist die korrekte Architektur für Infra-Zustand.

```sql
CREATE TABLE content_store.infra_snapshots (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_type TEXT       NOT NULL,   -- 'containers' | 'ssl' | 'migrations' | 'disk'
    target       TEXT        NOT NULL,   -- '88.198.191.108' | 'travel-beat'
    data         JSONB       NOT NULL,
    data_hash    TEXT        NOT NULL,   -- SHA-256 (Änderungserkennung)
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    collector    TEXT        NOT NULL
);

CREATE INDEX ON content_store.infra_snapshots (snapshot_type, target);
CREATE INDEX ON content_store.infra_snapshots (collected_at DESC);

CREATE VIEW content_store.v_infra_current AS
    SELECT DISTINCT ON (snapshot_type, target)
        snapshot_type, target, data, data_hash, collected_at
    FROM content_store.infra_snapshots
    ORDER BY snapshot_type, target, collected_at DESC;

-- Kritisch: Services mit pending Migrations
CREATE VIEW content_store.v_pending_migrations AS
    SELECT
        target AS service,
        (data->>'pending_count')::int AS pending_count,
        data->'pending_migrations' AS pending_migrations,
        collected_at
    FROM content_store.v_infra_current
    WHERE snapshot_type = 'migrations'
    AND (data->>'pending_count')::int > 0;
```

### 4.5 Change-Safety-Context: Pre-Change-Check

```python
# orchestrator_mcp/agent_team/guardian.py
async def pre_change_check(file_path: str, repo: str) -> ChangeSafetyReport:
    store = ContentStore()
    dependents  = await store.query_view("v_file_dependents",
                      changed_file=file_path, repo=repo)
    adrs        = await store.query_view("v_adr_current", repo=repo)
    redundancies= await store.query_view("v_redundancy_candidates", repo=repo)
    pending     = await store.query_view("v_pending_migrations", service=repo)

    return ChangeSafetyReport(
        file_path=file_path,
        repo=repo,
        affected_files=[d["dependent_file"] for d in dependents],
        relevant_adrs=adrs,
        redundancies=redundancies,
        pending_migrations=pending,
        safe_to_proceed=(
            len(pending) == 0
            and all(a["impl_status"] != "violated" for a in adrs)
        ),
    )
```

### 4.6 Aktualitäts-Mechanismen

| Mechanismus | Trigger | Granularität | Schicht |
|---|---|---|---|
| **M1: Git-Webhook** | Jeder Push auf `main` | Sofort | Code-Graph |
| **M2: Drift-Detector** | Täglich, Celery Beat | 24h | ADR-Compliance |
| **M3: Infra-Poller** | Stündlich, Celery Beat | 1h | Infra-Snapshots |

### 4.7 Trigger-Bedingungen für Migration zu `content-hub`

| Trigger | Messgröße |
|---|---|
| Consumer-Zahl | >= 5 aktive Services |
| Volumen | > 5 GB im Schema |
| DB-Last | > 25% aller Queries |
| Business-Logik | Approval-Workflows, Lizenzierung |
| Schema-Änderungsrate | > 3 Migrationen in 4 Wochen |

Migration ausgelöst wenn **mindestens 2** erfüllt. Schema bleibt identisch — nur Zugangspfad ändert sich.

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Datum | Notizen |
|---|---|---|---|---|
| `platform` / `creative-services` | 1 — Alle 4 Schichten SQL-Schema | ⬜ Ausstehend | – | `storage/`, `graph/`, `compliance/`, `snapshot/` |
| `platform` / `shared_contracts` | 1 — Event-Contracts | ⬜ Ausstehend | – | `content_events.py` |
| `mcp-hub` / `orchestrator_mcp` | 2 — Pilot Consumer A | ⬜ Ausstehend | – | Agent-Team + adr_compliance Persistenz |
| `mcp-hub` / `query_agent_mcp` | 2 — AST-Walker + Code-Graph | ⬜ Ausstehend | – | Git-Push-Trigger, `ast_walker.py` |
| `mcp-hub` / `orchestrator_mcp` | 2 — Infra-Poller | ⬜ Ausstehend | – | Stündlicher Celery-Beat-Job |
| `mcp-hub` / `orchestrator_mcp` | 2 — Guardian Pre-Change-Check | ⬜ Ausstehend | – | `pre_change_check()` |
| `travel-beat` | 3 — Consumer B | ⬜ Ausstehend | – | Story-Kapitel mit tenant_id |
| `bfagent` | 4 — Consumer C | ⬜ Ausstehend | – | Draft-Varianten via `bfagent_compat.py` |
| `mcp-hub` / `content_mcp` | 5 — MCP-Zugangsschicht | ⬜ Ausstehend | – | `pre_change_check`, `find_redundancies` Tools |
| `content-hub` (neues Repo) | 6 — Eigener Service | ⬜ Ausstehend | – | Nur wenn Trigger-Bedingungen (§4.7) erfüllt |

---

## 6. Consequences

### 6.1 Good

- **Change-Safety**: Vor jeder Änderung vollständiger Kontext — betroffene Dateien, ADR-Compliance, Redundanzen, pending Migrations
- **Redundanz-Erkennung**: `v_redundancy_candidates` liefert sofort alle doppelten Implementierungen
- **ADR-Compliance messbar**: `v_adr_violations` zeigt welche ADRs in welchen Repos verletzt sind
- **Infra-Zustand abrufbar**: Pending Migrations, SSL-Ablauf, Container-Status als Snapshot
- **Kein neuer Service**: Alle 4 Schichten im bestehenden Postgres-Schema
- **Aktualitäts-SLAs**: Code-Graph sofort, Infra 1h, ADR-Compliance 24h

### 6.2 Bad

- **Shared DB**: 4 Schichten erhöhen die Query-Last — Monitoring via `pg_stat_statements` Pflicht
- **AST-Walker-Komplexität**: Import-Graph ist nie 100% vollständig (dynamische Imports, `__import__`)
- **Snapshot-Latenz**: Infra-Zustand ist max. 1h veraltet — kein Live-Monitoring
- **Koordiniertes Versioning**: Schema-Änderungen betreffen alle Consumer gleichzeitig

### 6.3 Nicht in Scope

- Live-Monitoring (Prometheus/Grafana) — das ist ein Ops-Tool, kein Entwicklungs-Kontext-System
- Eigenes `content-hub` Repo — erst wenn Trigger-Bedingungen (§4.7) erfüllt
- Cross-Tenant-Graph — DSGVO-Konflikt, explizit ausgeschlossen
- Medien/Assets (Bilder, PDFs) — separates ADR

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|---|---|---|---|
| Shared DB wird zum Bottleneck | Mittel | Hoch | `pg_stat_statements` Monitoring, Trigger §4.7 |
| AST-Walker erkennt dynamische Imports nicht | Hoch | Niedrig | Explizit dokumentiert — kein falsches Sicherheitsgefühl |
| Snapshot veraltet → falscher Change-Safety-Check | Mittel | Mittel | SLA-Anzeige im Report: "Code-Graph: 2h alt" |
| Schema-Änderung bricht Consumer | Mittel | Hoch | Expand-Contract-Pattern: additive Änderungen zuerst |
| `tenant_id IS NULL` versehentlich für tenant-gebundene Daten | Niedrig | Kritisch | Pydantic-Validator erzwingt tenant_id für TENANT_SERVICES |
| Drift-Detector schreibt nicht in content_store | Niedrig | Hoch | CI-Gate: `v_adr_current` muss Einträge haben nach Drift-Check |

---

## 8. Confirmation

1. **Schema-Existenz-Test (CI)**: Alle 4 Schichten müssen existieren — blockiert Merge bei Fehler
2. **Tenant-Isolation-Test**: `test_should_not_leak_content_across_tenants`
3. **Redundanz-Erkennungs-Test**: `test_should_detect_duplicate_function_names` — zwei identisch benannte Funktionen in verschiedenen Dateien → `v_redundancy_candidates` zeigt sie
4. **Pre-Change-Check-Test**: `test_should_report_affected_files_on_change` — Änderung an `models.py` → alle importierenden Dateien im Report
5. **ADR-Compliance-Test**: `test_should_persist_drift_detector_results` — Drift-Detector-Run → Eintrag in `adr_compliance`
6. **Snapshot-Aktualitäts-Test**: `test_should_flag_stale_infra_snapshot` — Snapshot älter als 2h → `collected_at`-Warnung im Report
7. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualität geprüft — Staleness-Schwelle: 12 Monate

---

## 9. More Information

- ADR-056: Multi-Tenancy Schema Isolation — `tenant_id`-Muster
- ADR-059: ADR-Drift-Detector — wird um `adr_compliance`-Persistenz erweitert
- ADR-014: AI-Native Development Teams — Kontext für Consumer A
- ADR-057: Platform Test Strategy — Test-Anforderungen §8
- [asyncpg Dokumentation](https://magicstack.github.io/asyncpg/)
- [pgvector](https://github.com/pgvector/pgvector)
- Python `ast` stdlib — AST-Walker ohne externe Dependency

---

## 10. Changelog

| Datum | Autor | Änderung |
|---|---|---|
| 2026-02-22 | Achim Dehnert | Initial: Status Proposed — Content-Layer (Schicht 1) |
| 2026-02-22 | Achim Dehnert | Amendment: 4-Schichten-Architektur — Compliance, Code-Graph, Infra-Snapshot, Change-Safety |

---

<!--
  Drift-Detector-Felder (ADR-059):
  - staleness_months: 12
  - drift_check_paths:
      - platform/packages/creative-services/creative_services/storage/
      - platform/shared_contracts/content_events.py
      - mcp-hub/orchestrator_mcp/agent_team/
      - mcp-hub/query_agent_mcp/ast_walker.py
      - mcp-hub/orchestrator_mcp/infra_poller.py
  - supersedes_check: true
-->
