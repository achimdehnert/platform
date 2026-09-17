---
id: ADR-303
title: "Vector-Store-Schema: ADR-171 als Single Source of Truth, tenant_id ist UUID"
status: accepted
decision_date: 2026-05-07
amended: 2026-09-16
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [Repo-Owner risk-hub, meiki-hub, bfagent, coach-hub, weltenhub]
supersedes: []
amends: []
related: [ADR-188, ADR-171, ADR-087, ADR-187, ADR-022, ADR-304, ADR-305, ADR-306]
repo: platform
implementation_status: partial
last_reviewed: 2026-09-16
staleness_months: 6
drift_check_paths:
  - mcp-hub/rag_mcp/db/schema.sql
---

# ADR-303: Vector-Store-Schema — ADR-171 als Single Source of Truth, `tenant_id` ist UUID

> **Herkunft:** Herausgelöst aus ADR-188 (Unified Vector Store) am 2026-09-16 —
> Owner-Entscheid „smallest-viable cut“ zu [#169](https://github.com/achimdehnert/platform/issues/169):
> sieben Entscheidungen in einem ADR, 426 Zeilen, drei Entscheidungsverben im Titel.
> Der Beschluss stammt vom 2026-05-07 (ADR-188 v1.0/v1.1) und ist **unverändert**;
> neu ist nur der Schnitt. ADR-188 bleibt das Hub-Dokument mit Kontext, Treibern,
> Alternativen, Phasen und Konsequenzen — dort steht das *Warum*, hier das *Was*.

## Entscheidung

### E1: Ein Schema — ADR-171 als Single Source of Truth

Das **ADR-171-Schema** (`rag_collections` / `rag_documents` / `rag_chunks`) wird zum **einzigen Vector-Store-Schema** der gesamten Plattform.

**Begründung:**
- BigAutoField-konform für PKs (ADR-022)
- Temporal-Semantik eingebaut (kritisch für meiki-hub Gesetze + risk-hub SDS)
- Supersession Chain für Versionierung
- DELETE-Trigger für Immutabilität (GefStoffV §14, BayArchivG)
- Soft-Delete separat von Versionierung

**ADR-087 `search_chunks`** und **ADR-187 `document_chunks`** werden NICHT implementiert. Stattdessen:
- ADR-087 Consumer (bfagent, weltenhub) migrieren auf `rag_chunks` via rag-mcp
- ADR-187 Chunk-Pipeline schreibt in `rag_chunks` via rag-mcp

### E6: tenant_id ist UUID — Klarstellung

> **ADR-022 betrifft Primary Keys. `tenant_id` ist kein Primary Key.**

| Fakt | Erläuterung |
|------|-------------|
| ADR-022 sagt | `DEFAULT_AUTO_FIELD = BigAutoField` — gilt für **Primärschlüssel** |
| ADR-022 sagt NICHT | "UUID-Felder sind verboten" |
| `tenant_id` ist | Referenzfeld auf externe Identität (Organization), **kein PK** |
| Alle Consumer-Repos nutzen | `tenant_id = models.UUIDField(db_index=True)` |
| Konvertierung wäre | ~20 Models ändern, Mapping-Tabelle, Zero Business Value |
| Performance-Differenz | 8 Bytes/Row bei ~4 KB Embedding = **0.13%** — irrelevant |

**Entscheidung:** `tenant_id UUID NOT NULL` in allen Vector-Store-Tabellen.

ADR-171 Schema wird entsprechend korrigiert (`BIGINT` → `UUID` für `tenant_id`).

```sql
-- KORREKT (ADR-188):
CREATE TABLE rag_chunks (
    id BIGSERIAL PRIMARY KEY,           -- ADR-022 ✅ BigAutoField für PK
    tenant_id UUID NOT NULL,            -- UUID ✅ kein PK, matcht alle Consumer-Repos
    ...
);
CREATE INDEX idx_chunks_tenant ON rag_chunks (tenant_id);
```

## Konsequenzen

- **Ein Schema** — kein Wildwuchs, keine Entscheidung pro Repo; Temporal-Semantik und Immutabilität (DELETE-Trigger) für meiki-hub-Gesetze und risk-hub-SDS inklusive.
- ADR-087-Consumer (bfagent, weltenhub) migrieren nach der Deprecation-Timeline in ADR-188 §3 (Zero Breaking Changes, min. 8 Wochen).
- Komplexeres Schema als `search_chunks` — abstrahiert durch die API aus ADR-305.

## Referenzen

ADR-188 (Hub) · ADR-171 (Schema) · ADR-087 (`search_chunks`, `superseded_by_planned`) · ADR-187 §E3 · ADR-022 (BigAutoField gilt für PKs)
