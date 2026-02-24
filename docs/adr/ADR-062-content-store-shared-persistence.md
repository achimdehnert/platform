---
status: "proposed"
date: 2026-02-15
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-037-chat-conversation-logging.md", "ADR-056-deployment-preflight-and-pipeline-hardening.md"]
---

# Adopt a shared PostgreSQL schema `content_store` for AI-generated content persistence

---

## Context and Problem Statement

Mehrere Platform-Apps (travel-beat, weltenhub, bfagent) generieren KI-Inhalte
(Reisegeschichten, Weltenbeschreibungen, Buchkapitel), die bisher ausschließlich im
jeweiligen App-Schema gespeichert werden. Dadurch sind Cross-App-Auswertung,
plattformweite Versionierung und ADR-Compliance-Tracking strukturell nicht möglich.

**Problem**: Es gibt keinen gemeinsamen, schema-isolierten Persistenzort für
KI-generierte Inhalte. Jede App verwaltet ihren eigenen Speicher ohne einheitliche
Schnittstelle, ohne Versionierung und ohne Tenant-Isolation auf Plattformebene.

---

## Decision Drivers

- **Cross-App-Auswertung**: Inhalte aus travel-beat, weltenhub und bfagent sollen
  vergleichbar und gemeinsam auswertbar sein
- **Versionierung**: Jede KI-Ausgabe braucht einen unveränderlichen Hash + Versionszähler
- **Tenant-Isolation**: Alle Inhalte und Compliance-Daten müssen per `tenant_id` isoliert sein
- **ADR-Compliance**: Drift-Detector soll Compliance-Ergebnisse persistieren können
- **Minimale Invasion**: Bestehende App-Schemas bleiben unverändert

---

## Considered Options

### Option 1 — Shared PostgreSQL Schema `content_store` (gewählt)

Ein dediziertes PostgreSQL-Schema `content_store` außerhalb aller Django-App-Schemas,
verwaltet via Alembic. Django-Apps konsumieren es über eine typisierte Python-API.

**Pro:**
- Einheitliche Schnittstelle für alle Apps
- Plattformweites Reporting ohne Cross-Schema-Joins im App-Code
- Schema-Isolation: App-Migrations berühren `content_store` nicht
- Alembic ermöglicht schema-level Migrations unabhängig von Django

**Contra:**
- Zwei parallele Migrations-Systeme (Django + Alembic) erhöhen Ops-Komplexität
- `CONTENT_STORE_DSN` muss in allen Repos als Secret gepflegt werden
- Async/Sync-Brücke in Django-Kontext erfordert sorgfältige Implementierung

---

### Option 2 — Separate Tabellen pro App-Schema

Jede App bekommt eigene `content_items`-Tabellen in ihrem Django-Schema.

**Pro:** Kein zusätzliches Infrastruktur-Setup, keine externe DSN

**Contra:**
- Cross-App-Queries erfordern Joins über Schema-Grenzen (nicht portabel)
- Keine einheitliche Versionierung oder Compliance-Tracking
- Duplizierter Code in jeder App

**Verworfen**: Löst das Cross-App-Problem strukturell nicht.

---

### Option 3 — Externe Dokumentendatenbank (MongoDB / Elasticsearch)

**Pro:** Flexibles Schema, gute Volltextsuche

**Contra:**
- Neuer Infrastruktur-Stack neben PostgreSQL (Betriebsaufwand, Kosten)
- Kein nativer Tenant-Isolation-Mechanismus
- Inkonsistenz mit Platform-Entscheidung für PostgreSQL (ADR-056)

**Verworfen**: Widerspricht Platform-Prinzip "PostgreSQL als einzige DB-Technologie".

---

### Option 4 — Nur In-Memory / kein Persistence-Layer

**Pro:** Kein Aufwand

**Contra:** Kein Audit-Trail, keine Versionierung, kein Compliance-Tracking möglich

**Verworfen**: Erfüllt keinen der Decision Drivers.

---

## Decision Outcome

**Gewählt: Option 1** — Shared PostgreSQL Schema `content_store` mit Alembic-Migrations.

Das Schema liegt außerhalb aller Django-App-Schemas und wird ausschließlich via Alembic
verwaltet. Django-Apps konsumieren es über `SyncContentStore` (synchroner Wrapper via
`asgiref.sync.async_to_sync`) oder `ContentStore` (async).

### Positive Consequences

- Einheitliche, typisierte Schnittstelle für alle Apps
- Plattformweites Reporting ohne Cross-Schema-Joins im App-Code
- ADR-Compliance-Daten zentral und tenant-isoliert verfügbar
- Versionierung und SHA-256-Hashing out-of-the-box

### Negative Consequences

- Zusätzliche Infrastruktur (Alembic neben Django-Migrations)
- `CONTENT_STORE_DSN` muss in allen Repos als Secret gesetzt werden
- Ops-Overhead: `alembic upgrade head` muss im Deploy-Workflow explizit aufgerufen werden

---

## Implementation Details

### Schema (PostgreSQL)

```sql
CREATE SCHEMA IF NOT EXISTS content_store;

CREATE TABLE content_store.items (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    source      TEXT NOT NULL,   -- 'travel-beat' | 'weltenhub' | 'bfagent'
    type        TEXT NOT NULL,   -- 'story' | 'chapter' | 'world' | 'adr'
    ref_id      TEXT NOT NULL,
    content     TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    version     INT  NOT NULL DEFAULT 1,
    meta        JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Performance: alle Queries filtern nach tenant_id
CREATE INDEX idx_items_tenant_id ON content_store.items (tenant_id);
CREATE INDEX idx_items_tenant_source ON content_store.items (tenant_id, source);

CREATE TABLE content_store.adr_compliance (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    adr_id          TEXT NOT NULL,
    checked_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    drift_score     FLOAT NOT NULL,
    status          TEXT NOT NULL,  -- 'compliant' | 'warning' | 'violation'
    details         JSONB
);

CREATE INDEX idx_adr_compliance_tenant_id ON content_store.adr_compliance (tenant_id);
```

### Pydantic Models (`creative_services/storage/models.py`)

```python
class ContentItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: UUID
    source: Literal["travel-beat", "weltenhub", "bfagent"]
    type: Literal["story", "chapter", "world", "adr"]
    ref_id: str = Field(description="App-seitige ID des Quellobjekts")
    content: str
    sha256: str = Field(default="")  # auto-computed on save
    version: int = Field(default=1, ge=1)
    meta: dict[str, Any] = Field(default_factory=dict)
```

### API (`creative_services/storage/store.py`)

```python
class ContentStore:
    """Async-first API. Für Django-Kontext: SyncContentStore verwenden."""
    async def save(self, item: ContentItem) -> UUID: ...
    async def get(self, item_id: UUID) -> ContentItem | None: ...
    async def add_relation(self, relation: ContentRelation) -> None: ...

class SyncContentStore:
    """Synchroner Wrapper via asgiref.sync.async_to_sync (ASGI-sicher)."""
    def save(self, item: ContentItem) -> UUID:
        return async_to_sync(self._store.save)(item)
    def get(self, item_id: UUID) -> ContentItem | None:
        return async_to_sync(self._store.get)(item_id)
```

> **Wichtig**: `asgiref.sync.async_to_sync` statt `asyncio.run()` — verhindert
> Deadlocks in ASGI-Kontexten (Daphne/Uvicorn).

### Rollback-Strategie

| Szenario | Verhalten | Mitigation |
|----------|-----------|-----------|
| `CONTENT_STORE_DSN` fehlt | `ContentStoreUnavailableError` bei Init | Apps fangen Exception, loggen Warning, fahren ohne Persistenz fort |
| Schema-Migration fehlgeschlagen | `alembic upgrade head` bricht Deploy ab | `alembic downgrade -1` im Deploy-Workflow als Rollback-Schritt |
| Korruptes Schema | Queries schlagen fehl | `pg_dump content_store` vor jeder Migration als Backup |

### Alembic Migrations

| Migration | Inhalt |
|-----------|--------|
| `0001_create_content_store` | Schema + `items` + `relations` Tabellen + Indizes |
| `0002_add_adr_compliance` | `adr_compliance` Tabelle + `tenant_id` + Index |

### Drift Detector Integration

`orchestrator_mcp/drift_detector.py` persistiert Compliance-Ergebnisse via `--persist`
Flag direkt in `content_store.adr_compliance` (mit `tenant_id` aus Konfiguration).

---

## Migration Tracking

| Schritt | Status | Datum |
|---------|--------|-------|
| Alembic-Setup in `creative-services` | ✅ done | 2026-02-15 |
| Migration 0001 (items + relations + Indizes) | ✅ done | 2026-02-15 |
| Migration 0002 (adr_compliance + tenant_id + Index) | ✅ done | 2026-02-15 |
| Schema auf Prod deployed (88.198.191.108) | ✅ done | 2026-02-22 |
| `CONTENT_STORE_DSN` in allen Repos gesetzt | ✅ done | 2026-02-22 |
| Drift Detector implementiert | ✅ done | 2026-02-15 |
| `SyncContentStore` auf `asgiref.async_to_sync` umgestellt | ✅ done | 2026-02-24 |

---

## Consequences

### Risks

| Risiko | Schwere | Mitigation |
|--------|---------|-----------|
| Schema-Drift (Alembic + Django parallel) | MEDIUM | `alembic upgrade head` im Deploy-Workflow als Pflichtschritt |
| DSN-Abhängigkeit | LOW | Lazy-Init mit `ContentStoreUnavailableError`; Apps degradieren graceful |
| Async/Sync-Mismatch in ASGI | HIGH | `asgiref.sync.async_to_sync` statt `asyncio.run()` |
| Fehlende Tenant-Isolation in `adr_compliance` | HIGH | Behoben: `tenant_id` + Index in Migration 0002 |

### Confirmation

- `alembic upgrade head` im CI/CD-Workflow verifiziert Schema-Stand
- `compliance-check.yml` läuft bei jedem Push auf `platform/main`
- Drift-Score-Schwellwert: `> 0.5` = Warning, `> 0.8` = Violation (blockiert Merge)
- Alle `adr_compliance`-Queries filtern auf `tenant_id`
- `SyncContentStore` nutzt `async_to_sync` — kein `asyncio.run()`

---

## Drift-Detector Governance Note

```yaml
paths:
  - packages/creative-services/creative_services/storage/
  - orchestrator_mcp/drift_detector.py
  - .github/workflows/compliance-check.yml
gate: NOTIFY
```
