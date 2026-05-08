---
status: Proposed
date: 2026-05-07
amended: 2026-05-08
decision-makers:
  - Achim Dehnert
consulted:
  - AI Engineering Squad
informed:
  - Repo-Owner risk-hub, meiki-hub, bfagent, coach-hub, weltenhub
depends-on:
  - ADR-087 (Hybrid Search Architecture — platform-search Package)
  - ADR-113 (pgvector Agent Memory Store)
  - ADR-171 (Temporal RAG Infrastructure — Schema)
  - ADR-172 (rag-mcp Server — Platform-Wide RAG API)
  - ADR-170 (iil-ingest — Document Ingestion Package)
  - ADR-187 (Document Intelligence Pipeline)
  - ADR-173 (Document Intake Routing Pattern)
  - ADR-022 (BigAutoField Platform Standard)
consolidates:
  - ADR-087 (search_chunks Tabelle)
  - ADR-171 (rag_collections / rag_documents / rag_chunks)
  - ADR-187 §E3 (document_chunks Tabelle)
repo: platform
implementation_status: none
staleness_months: 6
drift_check_paths:
  - mcp-hub/rag_mcp/db/schema.sql
  - platform/packages/platform-search/
---

<!-- Drift-Detector-Felder: staleness_months: 6, drift_check_paths: mcp-hub/rag_mcp/db/schema.sql, platform/packages/platform-search/**, supersedes_check: ADR-087 -->

# ADR-188: Adopt ADR-171 Schema with multilingual-e5-large as Platform-Wide Unified Vector Store

| Metadaten | |
|-----------|---|
| **Status** | Proposed |
| **Datum** | 2026-05-07 |
| **Geändert** | 2026-05-08 (v1.1 — Review-Fixes: UUID-Klarstellung, Decision Drivers, Open Questions, Glossar, Deprecation-Timeline, SPOF-Mitigation, DSGVO-Policy) |
| **Autor** | Achim Dehnert |
| **Scope** | Alle Repos (platform-weit) |
| **Consumers** | meiki-hub, risk-hub, bfagent, coach-hub, weltenhub, travel-beat, dms-hub |

---

## Executive Summary

Aktuell existieren **drei parallele Vector-Store-Definitionen** auf der Plattform:

| ADR | Tabelle(n) | Embedding-Modell | Dimensionen | Status |
|-----|-----------|------------------|-------------|--------|
| ADR-087 | `search_chunks` | text-embedding-3-small (OpenAI) | 1536 | ✅ Implemented |
| ADR-171 | `rag_collections` / `rag_documents` / `rag_chunks` | multilingual-e5-large (lokal) | 1024 | Proposed |
| ADR-187 §E3 | `document_chunks` | text-embedding-3-small (OpenAI) | 1536 | Planned |

**Problem:** Drei Schemata, zwei Embedding-Modelle, keine einheitliche API. Consumer-Repos müssten entscheiden welches Schema sie nutzen — oder alle drei kennen.

**Dieses ADR konsolidiert** die drei Ansätze zu einem **Unified Vector Store** mit einer einheitlichen API (rag-mcp), einem Schema (ADR-171), und einem klar definierten Embedding-Modell.

---

## Decision Drivers

| ID | Treiber | Gewichtung |
|----|---------|------------|
| D-1 | Kein Schema-Wildwuchs — Consumer-Repos sollen genau 1 API nutzen | Kritisch |
| D-2 | DSGVO — personenbezogene Daten (meiki-hub Fallakten, risk-hub SDS) dürfen nicht an Cloud-APIs | Kritisch |
| D-3 | Temporal-Semantik — Gültigkeitsdaten bei Gesetzen und SDS-Versionen | Kritisch |
| D-4 | Tenant-Isolation — jeder Tenant sieht nur eigene Daten, UUID-basiert | Kritisch |
| D-5 | Bestehende Infra nutzen — pgvector bereits deployed (kein neuer Service) | Hoch |
| D-6 | Cross-Repo-Suche perspektivisch möglich (ein Embedding-Modell für alle) | Mittel |
| D-7 | Kosten — kein laufender API-Verbrauch für Embeddings | Mittel |

---

## 1. Kontext und Problemstellung

### 1.1 Repo-übergreifende Anforderungen (Recherche-Ergebnis)

| Repo | Dokumenttyp | Spezifische Anforderung | Quelle |
|------|-------------|------------------------|--------|
| **meiki-hub** | Bayerische Gesetze (BayBO, BayDSG) | Temporal: `as_of_date`, Gültigkeitsdauer, Paragraph-Split | ADR-006 |
| **meiki-hub** | Fallakten-Scans | Metadaten-Zuordnung, Fuzzy-Match auf Personendaten | ADR-011 |
| **risk-hub** | SDS, Ex-Schutz-Dokumente, GBU | Versionierung, Template-Prefill via RAG | ADR-046, ADR-187 |
| **risk-hub** | Projekt-Dokumente | Bibliothek + projekt-spezifische Uploads, Cross-Modul | Neu (P3.12) |
| **bfagent** | Kapitel, Szenen, Charaktere | Semantische Suche über Story-Universen | ADR-087 |
| **weltenhub** | Weltenbau-Dokumente, Lore | Story-Konsistenz via RAG | ADR-087 |
| **coach-hub** | Coaching-Materialien | Personalisierte Empfehlungen | ADR-187 |
| **platform** | ADRs, Workflows, Docs | Status-Verlauf, Versionierung | ADR-171 |
| **mcp-hub** | Agent Memory | Session-Summaries, Decisions, Error-Patterns | ADR-113 |

### 1.2 Kern-Widersprüche der aktuellen ADRs

| Aspekt | ADR-087 | ADR-171 | ADR-187 | **Konsolidierung** |
|--------|---------|---------|---------|------|
| **PK-Typ** | UUID | BigSerial ✅ | BigSerial | **BigSerial** (PK) |
| **tenant_id** | UUID | BIGINT ⚠️ | UUID | **UUID** (siehe §2 E6) |
| **Embedding-Modell** | text-embedding-3-small | multilingual-e5-large | text-embedding-3-small | **multilingual-e5-large** |
| **Dimensionen** | 1536 | 1024 | 1536 | **1024** |
| **Temporal** | Nein | ✅ (`valid_from/until`) | Nein | **✅ Ja** |
| **Versionierung** | Nein | ✅ Supersession Chain | Replace | **✅ Supersession** |
| **Hybrid Search** | ✅ RRF | ✅ RRF | Nein | **✅ RRF** |
| **Soft-Delete** | Nein | ✅ `deleted_at` | DELETE+INSERT | **✅ Soft-Delete** |
| **API-Layer** | Django SearchService | rag-mcp (MCP) | Django direkt | **rag-mcp** |

---

## 2. Entscheidung

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

### E2: Ein Embedding-Modell — multilingual-e5-large (Primär)

| Kriterium | multilingual-e5-large | text-embedding-3-small |
|-----------|----------------------|----------------------|
| **Kosten** | ✅ Open Source, lokal | ❌ $0.02/1M Tokens |
| **Offline** | ✅ | ❌ |
| **Deutsch** | ✅ Exzellent | ✅ Gut |
| **Dimensionen** | 1024 | 1536 |
| **Vendor Lock-in** | ✅ Keiner | ❌ OpenAI-Abhängigkeit |
| **Latenz** | ⚠️ ~50ms/Chunk (CPU) | ✅ ~10ms/Chunk (API) |
| **DSGVO** | ✅ Daten bleiben lokal | ⚠️ Daten an OpenAI |
| **RAM** | ⚠️ ~3 GB (Model + Runtime) | ✅ Kein lokaler RAM |

**Entscheidung:** `multilingual-e5-large` (1024 Dimensionen) als **Primärmodell**. OpenAI als **optionaler Fallback** nur für Collections ohne DSGVO-Restriktion (siehe E7).

> **Wichtig:** E5-Modelle erfordern Prefix `"query: "` bei Search-Queries und `"passage: "` bei Ingest-Texten für optimale Retrieval-Qualität. Ohne Prefix: ~15% Recall-Verlust. Die rag-mcp API setzt diese Prefixes automatisch.

### E3: Eine API — rag-mcp als Single Access Point

```
Consumer-Repos                   rag-mcp (ADR-172)              pgvector (ADR-171)
┌─────────────┐                ┌──────────────────┐           ┌──────────────┐
│ meiki-hub   │──rag_ingest───▶│                  │──INSERT──▶│ rag_chunks   │
│ risk-hub    │──rag_search───▶│  Tools (MCP)     │──SELECT──▶│ rag_documents│
│ bfagent     │──rag_supersede▶│  Services        │──UPDATE──▶│ rag_collects │
│ weltenhub   │──rag_history──▶│  Celery Worker   │           │              │
│ platform    │──rag_list─────▶│  Embedder Svc    │           │ mcp_hub_db   │
└─────────────┘                └──────────────────┘           └──────────────┘
```

**Kein Consumer greift direkt auf die DB zu.** Auch Django-Repos nutzen rag-mcp Tools.

> **ADR-075 Abgrenzung:** `rag_ingest` und `rag_supersede` sind **Daten-Operationen** (vergleichbar mit DB-INSERT), keine Deployment-/Infrastruktur-Operationen. ADR-075 Write-Op-Restriktion betrifft nur infrastrukturelle Aktionen (migrate, deploy, backup). Daten-CRUD via MCP ist explizit erlaubt.

### E4: Collection-Namenskonvention (platform-weit)

| Repo | Collection | Dokumenttyp | Chunking-Strategie |
|------|-----------|-------------|-------------------|
| `meiki-hub` | `meiki:gesetze` | Bayerische Gesetze | `paragraph` (§/Art.) |
| `meiki-hub` | `meiki:avos` | Ausführungsverordnungen | `paragraph` |
| `meiki-hub` | `meiki:fallakten` | Gescannte Fallakten-Docs | `sliding` |
| `risk-hub` | `risk:sds` | Sicherheitsdatenblätter | `sliding` |
| `risk-hub` | `risk:exdoc` | Ex-Schutz-Dokumente | `semantic` (Markdown) |
| `risk-hub` | `risk:gbu` | Gefährdungsbeurteilungen | `semantic` |
| `risk-hub` | `risk:bibliothek` | Allgemeine Dokumente (Normen etc.) | `sliding` |
| `bfagent` | `bfagent:stories` | Kapitel, Szenen | `sliding` |
| `weltenhub` | `welten:lore` | Weltenbau-Dokumente | `sliding` |
| `coach-hub` | `coach:materials` | Coaching-Materialien | `sliding` |
| `platform` | `platform:adrs` | Architecture Decision Records | `semantic` |
| `platform` | `platform:docs` | Workflows, Runbooks | `semantic` |

**Naming:** `{repo_prefix}:{domain}` — eindeutig, sortierbar, filterbar.

### E5: Dokument-Bibliothek für risk-hub Projekte

Aufbauend auf dem Unified Vector Store bekommt risk-hub eine **Dokumentenbibliothek**:

```python
class ProjectDocumentLink(models.Model):
    """Verknüpft Bibliotheks-Dokument mit Projekt (M:N)."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="library_links")
    collection = models.CharField(max_length=100)
    document_key = models.CharField(max_length=500)
    relevance_note = models.CharField(max_length=255, blank=True, default="")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "collection", "document_key"],
                name="uq_project_doc_link",
            ),
        ]
```

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

### E7: DSGVO-Fallback-Policy (collection-spezifisch)

Der OpenAI-Fallback darf **NICHT automatisch** für alle Collections greifen. Policy pro Collection:

```python
EMBEDDING_POLICY = {
    # DSGVO-kritisch: NUR lokales Embedding. Bei Embedder-Ausfall → Fehler, kein Fallback.
    "meiki:fallakten": {"allow_cloud": False},
    "meiki:gesetze":   {"allow_cloud": False},   # Amtliche Werke = unkritisch, aber lokal bevorzugt
    "risk:sds":        {"allow_cloud": False},    # Betriebsgeheimnisse
    "risk:gbu":        {"allow_cloud": False},

    # Unkritisch: Cloud-Fallback erlaubt wenn lokaler Embedder unavailable.
    "bfagent:stories": {"allow_cloud": True},
    "welten:lore":     {"allow_cloud": True},
    "platform:adrs":   {"allow_cloud": True},
    "coach:materials":  {"allow_cloud": True},
}
```

**Verhalten bei Embedder-Ausfall:**
- `allow_cloud: False` → `EmbeddingUnavailableError` → Ingest schlägt fehl, Search degradiert auf FTS-only
- `allow_cloud: True` → Transparenter Fallback auf OpenAI API

---

## 3. Deprecation-Timeline für ADR-087 (Zero Breaking Changes)

ADR-087 ist `implementation_status: implemented`. Superseding erfordert eine kontrollierte Transition:

| Phase | Aktion | Zustand | Frühestens |
|-------|--------|---------|-----------|
| **D-1** | rag-mcp deployed, `rag_chunks` parallel verfügbar | ADR-087 aktiv, ADR-188 parallel | Phase 1 done |
| **D-2** | Consumer migrieren einzeln (bfagent, weltenhub) | Dual-Read: SearchService fragt rag-mcp, Fallback auf search_chunks | Phase 2 |
| **D-3** | `platform-search` Package: Deprecation-Warning in Logs | Alle Consumer auf rag-mcp | Phase 2 + 4 Wochen |
| **D-4** | `search_chunks` Tabelle: read-only, dann DROP | ADR-087 Status → `Superseded by ADR-188` | Phase 3 (frühestens 8 Wochen nach D-3) |

**Kein Consumer verliert Funktionalität zu keinem Zeitpunkt.**

---

## 4. SPOF-Mitigation (mcp_hub_db)

`mcp_hub_db` wird zentrale Vector-DB. Ausfallschutz:

| Maßnahme | Implementierung | Phase |
|----------|----------------|-------|
| **Automated Backup** | `pg_dump --format=custom` via Cron (täglich, 30 Tage Retention) | Phase 1 |
| **Graceful Degradation** | rag-mcp unavailable → Consumer-Apps degradieren auf FTS-only (keyword-basiert, ohne Embeddings) | Phase 1 |
| **Health Monitoring** | rag-mcp `/livez/` + `/healthz/` (DB-Connection + Embedding-Service) | Phase 1 |
| **Read-Replica** | Optional: Streaming Replication für Search-Queries bei >500k Chunks | Phase 4 |

---

## 5. Betrachtete Alternativen

### Option A: Drei Schemata beibehalten
- ❌ Wildwuchs, jedes Repo entscheidet selbst
- ❌ Unterschiedliche Embedding-Modelle → Cross-Repo-Search unmöglich
- **Abgelehnt**

### Option B: ADR-087 als Basis, Temporal nachrüsten
- ⚠️ UUID-PKs widersprechen ADR-022 (PKs!)
- ⚠️ Kein Supersession-Konzept, nachträgliche Migration teuer
- **Abgelehnt**

### Option C: ADR-171 als Basis + Konsolidierung (gewählt)
- ✅ BigAutoField-konform (PKs)
- ✅ Temporal eingebaut
- ✅ Supersession Chain
- ✅ Soft-Delete + DELETE-Trigger
- ✅ HNSW statt IVFFlat
- **Gewählt**

### Option D: Externe Vector-DB (Qdrant, Weaviate, Pinecone)
- ❌ Neuer Container, neues Ops-Wissen
- ❌ Keine SQL-Transaktionen mit Django-Daten
- ❌ Kein Row-Level-Security mit tenant_id
- **Abgelehnt** (konsistent mit ADR-087, ADR-171)

---

## 6. Implementierungsphasen

| Phase | Aufgabe | Verantwortlich | Abhängigkeit |
|-------|---------|---------------|-------------|
| **0** | ADR-188 akzeptieren, ADR-171 tenant_id→UUID korrigieren | Achim | — |
| **1** | ADR-171 Schema deployen (mcp_hub_db) | Platform | pgvector Extension |
| **1** | ADR-172 rag-mcp implementieren (MVP: ingest + search) | Platform | Phase 1 Schema |
| **1** | Embedder-Service deployen (multilingual-e5-large, ~3 GB RAM) | Platform | Docker |
| **1** | Backup-Cron + Health-Endpoints für rag-mcp | Platform | Phase 1 |
| **2** | meiki-hub Pilot: BayBO + BayArchivG (ADR-006) | meiki-hub | Phase 1 |
| **2** | risk-hub: SDS + Bibliothek via rag-mcp | risk-hub | Phase 1 |
| **2** | bfagent/weltenhub: Migration search_chunks → rag_chunks | bfagent | Phase 1 |
| **3** | iil-ingest[vectorstore]: ChunkWriter via rag-mcp | Package | Phase 1 |
| **3** | risk-hub: ProjectDocumentLink + RAG-Prefill | risk-hub | Phase 2 |
| **3** | ADR-087 `search_chunks` DROP (nach 8 Wochen Deprecation) | Platform | Phase 2 complete |
| **4** | Reranker-Service (BGE-Reranker-v2-m3) | Platform | Phase 2 |
| **4** | Cross-Repo-Search (z.B. platform ADRs + risk-hub Normen) | Platform | Phase 2 |

---

## 7. Konsequenzen

### Positiv

| + | Konsequenz |
|---|------------|
| + | **Ein Schema** — kein Wildwuchs, keine Entscheidung pro Repo |
| + | **Ein Embedding-Modell** — Cross-Repo-Search möglich |
| + | **DSGVO** — lokales Embedding, collection-spezifische Policy |
| + | **Temporal** — meiki-hub Gesetze + risk-hub SDS-Versionen |
| + | **Immutabilität** — DELETE-Trigger für Compliance |
| + | **Kosten** — kein OpenAI-API-Verbrauch für Embeddings |
| + | **Offline** — funktioniert ohne Internet (lokal, Hetzner) |
| + | **Zero Breaking Changes** — Deprecation-Timeline, kein harter Cutover |

### Trade-offs

| - | Trade-off | Mitigation |
|---|-----------|------------|
| - | Embedder-Service = neuer Container (~3 GB RAM) | Lazy-Loading, CPU-only default |
| - | ADR-087 Consumers müssen migrieren | Deprecation-Timeline D-1→D-4 (min. 8 Wochen) |
| - | Komplexeres Schema als einfache `search_chunks` | Komplexität wird durch rag-mcp abstrahiert |
| - | multilingual-e5-large langsamer als API | Batch-Ingest via Celery, nicht Request-kritisch |
| - | SPOF mcp_hub_db | Backup + Graceful Degradation (FTS-only Fallback) |

---

## 8. Open Questions

| # | Frage | Entscheidung bis | Verantwortlich |
|---|-------|-----------------|----------------|
| Q-1 | Soll ADR-171 separat akzeptiert werden oder inline in ADR-188 aufgehen? | Phase 0 | Achim |
| Q-2 | Embedder-Service: eigener Container oder Sidecar im mcp-hub Compose? | Phase 1 | Platform |
| Q-3 | Embedding-Modell-Upgrade-Strategie: Parallele Columns oder vollständiges Re-Embedding? | Phase 2 | Platform |
| Q-4 | Cross-Repo-Search (Phase 4): Benötigt das ein explizites Opt-in pro Tenant? | Phase 4 | Achim |
| Q-5 | SLA für rag-mcp: Welche Verfügbarkeit/Latenz wird garantiert? | Phase 1 | Platform |

---

## 9. Confirmation

| # | Check | Methode |
|---|-------|--------|
| 1 | ADR-171 Schema deployed (mit UUID tenant_id) | `\d rag_chunks` in mcp_hub_db |
| 2 | rag-mcp erreichbar | `rag_list(tenant_id=<uuid>)` → leere Liste |
| 3 | Ingest-Roundtrip | `rag_ingest` BayBO §55 → `rag_search` findet Treffer |
| 4 | DSGVO-Policy aktiv | `rag_ingest(collection="meiki:fallakten")` mit Embedder down → Fehler (kein Cloud-Fallback) |
| 5 | meiki-hub Pilot | 50-Fragen-Goldstandard Recall@5 ≥ 0.85 |
| 6 | risk-hub Bibliothek | Dokument verknüpft → RAG-Prefill nutzt Chunks |
| 7 | Graceful Degradation | rag-mcp down → Consumer-App zeigt Keyword-Suche (kein Crash) |
| 8 | ADR-087 superseded | `search_chunks` Tabelle nicht mehr genutzt (nach D-4) |

---

## 10. Glossar

| Begriff | Erläuterung |
|---------|-------------|
| **Chunk** | Ein Textabschnitt (100–500 Wörter), der als kleinste Sucheinheit im Vector Store liegt |
| **Collection** | Logische Gruppierung von Dokumenten (z.B. alle Gesetze eines Repos) |
| **Embedding** | Numerische Repräsentation (Zahlenvektor) eines Textes, die dessen Bedeutung codiert |
| **FTS** | Full-Text Search — klassische Keyword-Suche über PostgreSQL `tsvector` |
| **HNSW** | Hierarchical Navigable Small World — schneller Nearest-Neighbor-Index für Vektoren |
| **Hybrid Search** | Kombination aus semantischer Vektorsuche und klassischer Keyword-Suche |
| **pgvector** | PostgreSQL-Extension für Vektor-Ähnlichkeitssuche |
| **rag-mcp** | MCP-Server der die Vector-Store-API bereitstellt (ingest, search, supersede) |
| **RRF** | Reciprocal Rank Fusion — Algorithmus der Ergebnisse aus zwei Suchverfahren zusammenführt |
| **Supersession Chain** | Versionskette: Neues Dokument ersetzt altes, altes bleibt für historische Queries erhalten |
| **Temporal** | Zeitbezogene Suche: "Was galt am Stichtag X?" statt nur "Was gilt jetzt?" |
| **tenant_id** | Eindeutige Kennung (UUID) eines Mandanten — isoliert Daten zwischen Organisationen |

---

## 11. Referenzen

- [ADR-087: Hybrid Search Architecture](./ADR-087-hybrid-search-architecture.md) — wird superseded (Phase D-4)
- [ADR-113: pgvector Agent Memory Store](./ADR-113-telegram-gateway-pgvector-memory.md) — bleibt separat
- [ADR-170: iil-ingest](./ADR-170-iil-ingest-document-ingestion-package.md)
- [ADR-171: Temporal RAG Infrastructure](./ADR-171-temporal-rag-infrastructure.md) — Single Schema
- [ADR-172: rag-mcp Server](./ADR-172-rag-mcp-server.md) — Single API
- [ADR-173: Document Intake Routing](./ADR-173-document-intake-routing-pattern.md)
- [ADR-187: Document Intelligence Pipeline](./ADR-187-document-intelligence-pipeline.md)
- [meiki-hub ADR-006: Temporal RAG Pilot](https://github.com/meiki-lra/meiki-hub/blob/main/docs/adr/ADR-006-temporal-rag-pilot.md)
- [meiki-hub ADR-011: Fallakten-Matching](https://github.com/meiki-lra/meiki-hub/blob/main/docs/adr/ADR-011-fallakten-matching-identifikationslogik.md)
- multilingual-e5-large: https://huggingface.co/intfloat/multilingual-e5-large
- pgvector HNSW: https://github.com/pgvector/pgvector#hnsw
- RRF: Cormack et al. 2009
