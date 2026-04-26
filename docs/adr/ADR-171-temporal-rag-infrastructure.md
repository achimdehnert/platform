---
status: Proposed
date: 2026-04-26
decision-makers:
  - Achim Dehnert
depends-on:
  - ADR-113 (pgvector Agent Memory Store)
  - ADR-161 (Two-Layer-Schema with Supersession Chain for SDS)
  - ADR-170 (iil-ingest Document Ingestion Package)
repo: platform
implementation_status: none
staleness_months: 6
drift_check_paths:
  - mcp-hub/rag_mcp/db/schema.sql
  - mcp-hub/rag_mcp/db/migrations/
---

# ADR-171: Temporal RAG Infrastructure — Bitemporal Vector Storage on pgvector

| Metadaten | |
|-----------|---|
| **Status** | Proposed |
| **Datum** | 2026-04-26 |
| **Autor** | Achim Dehnert |
| **Reviewer** | — |
| **Depends On** | ADR-113 (pgvector), ADR-161 (Supersession Chain), ADR-170 (iil-ingest) |
| **Implements** | ADR-172 (rag-mcp) nutzt dieses Schema |
| **Repos** | `platform`, `mcp-hub`, alle Consumer-Repos |

### Änderungshistorie

| Version | Datum | Änderung |
|---------|-------|----------|
| 1.0 | 2026-04-26 | Initiale Version |

---

## Executive Summary

Mehrere Repos der Plattform (meiki-hub, risk-hub, platform, bfagent) benötigen
SemanticSearch über versionierte Dokumente: Bayerische Gesetze mit Gültigkeitszeiträumen,
Sicherheitsdatenblätter mit Revisionshistorie, ADRs mit Statustransitionen.

Dieses ADR entscheidet:
1. **pgvector** als Vector-Backend (bereits auf Prod, kein neues Deployment)
2. **Supersession Chain** als Versioning-Pattern (konsequente Erweiterung von ADR-161)
3. **Bitemporal Schema** mit `valid_from`/`valid_until` für zeitpunkt-genaue Queries
4. **Hybrid Search** (Dense Vector + BM25/tsvector) für deutsche Rechtstexte
5. **multilingual-e5-large** als Embedding-Modell (1024 Dims, German-optimiert, Open Source)

---

## 1. Kontext und Problemstellung

### 1.1 Use Cases

| Repo | Dokument-Typ | Temporale Anforderung |
|------|-----------|-----------------------|
| `meiki-hub` | Bayerische Gesetze (BayBO, BayDSG, ...) | "Was galt am Stichtag 2024-03-15?" |
| `meiki-hub` | Ausführungsverordnungen (AVOs) | Inkrafttreten, Außerkrafttreten |
| `risk-hub` | Sicherheitsdatenblätter (SDS) | Welche Version war beim Unfall gültig? |
| `platform` | ADRs | Status-Verlauf (Proposed→Accepted→Superseded) |
| `platform` | .windsurf Workflows/Rules | Zeitpunkt der letzten Änderung |
| `bfagent` | Prompt-Templates | Versionen nach Deployment-Tag |

### 1.2 Kernproblem: Versionierung + Löschverbot

Juristische und Compliance-Dokumente dürfen **niemals physisch gelöscht** werden:
- GefStoffV §14: 40-Jahre-Aufbewahrung für CMR-Stoffe
- Bayerische Archivgesetze: Dokumente mit rechtlicher Wirkung immutabel
- Audit-Trails: Welche Version war bei Entscheidung X bekannt?

Stattdessen: **Supersession Chain** — jede neue Version *ersetzt* logisch die alte,
behält aber die alte als historischen Datensatz.

### 1.3 Warum nicht eine neue Vector-Datenbank?

| Option | Operativer Aufwand | Temporal Queries | Hybrid Search | Entscheidung |
|--------|-------------------|-----------------|--------------|-------------|
| **pgvector** (bestehend) | ✅ null | ✅ native SQL | ✅ + tsvector | **Gewählt** |
| Qdrant | neuer Container + Port | ⚠️ payload filter | ✅ built-in | Abgelehnt |
| Weaviate | JVM-Container, komplex | ✅ native | ✅ built-in | Abgelehnt |
| Pinecone | Managed, API-Kosten | ⚠️ metadata only | ❌ | Abgelehnt |

pgvector läuft bereits auf Prod (`mcp_hub_db`, Port 15435). SQL-Mächtigkeit
übertrifft jede dedizierte Vector-DB für bitemporal-komplexe Queries.

---

## 2. Entscheidungstreiber

| ID | Treiber | Gewichtung |
|----|---------|------------|
| D-1 | Kein neues Deployment — pgvector bereits auf Prod | Hoch |
| D-2 | Zeitpunkt-genaue Queries (`as_of_date`) | Kritisch |
| D-3 | Immutabilität (Löschverbot für Rechtsdokumente) | Kritisch |
| D-4 | Hybrid Search für deutsche Rechtstexte (§-Nummern, Abkürzungen) | Hoch |
| D-5 | Cross-Repo-Search (eine Infrastruktur für alle Repos) | Hoch |
| D-6 | Konsistenz mit ADR-161 Supersession-Pattern | Mittel |
| D-7 | Open-Source Embedding (kein API-Kostenpfad) | Mittel |

---

## 3. Architektur-Entscheidung

### 3.1 Gewählt: pgvector + Supersession Chain + Hybrid Search

```
┌─────────────────────────────────────────────────────────────────┐
│  pgvector Instance (mcp_hub_db — bereits auf Prod)              │
│                                                                  │
│  agent_memory (ADR-113)     rag_documents (ADR-171)              │
│  Agent-Kontext, Sessions    Versionierte Dokumente               │
│  Entscheidungen             Gesetze, SDS, ADRs, Prompts          │
│                                                                  │
│  rag_collections            Collections-Registry                 │
│  (meiki-hub:gesetze, ...)                                        │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Vollständiges Datenbankschema

```sql
-- Collections-Registry
CREATE TABLE rag_collections (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  repo            varchar(100) NOT NULL,
  collection      varchar(100) NOT NULL,
  description     text,
  embed_model     varchar(100) NOT NULL DEFAULT 'multilingual-e5-large',
  chunk_strategy  varchar(50)  NOT NULL DEFAULT 'paragraph',
  created_at      timestamptz  NOT NULL DEFAULT now(),
  UNIQUE(repo, collection)
);

-- Dokumente (immutable append-only — NIEMALS physisch löschen)
CREATE TABLE rag_documents (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Zuordnung
  repo            varchar(100) NOT NULL,
  collection      varchar(100) NOT NULL,
  document_id     varchar(500) NOT NULL,   -- stabile ext. ID: "BayBO-§55-Abs1"

  -- Hierarchisches Chunking (Parent-Document Retrieval)
  parent_id       uuid REFERENCES rag_documents(id),   -- NULL = Parent-Chunk
  chunk_index     int  NOT NULL DEFAULT 0,
  chunk_total     int,
  content         text NOT NULL,
  content_hash    varchar(64),             -- SHA-256 für Dedup bei Re-Ingest

  -- Embeddings
  embedding       vector(1024),            -- multilingual-e5-large

  -- Hybrid Search (German BM25)
  content_tsv     tsvector GENERATED ALWAYS AS
                    (to_tsvector('german', content)) STORED,

  -- Bitemporal Dimension (KERNFEATURE)
  version         varchar(100),            -- "Fassung 2024-01-01" / "v2.1"
  valid_from      date         NOT NULL,   -- Inkrafttreten / Ausgabedatum
  valid_until     date,                    -- NULL = aktuell gültig
  is_current      boolean      NOT NULL DEFAULT true,
  superseded_by   uuid         REFERENCES rag_documents(id),
  revision_note   text,                    -- "§5 Abs.2 geändert durch VO 2024/12"

  -- Herkunft
  source_url      text,
  metadata        jsonb        NOT NULL DEFAULT '{}',

  -- Audit (unveränderlich)
  ingested_at     timestamptz  NOT NULL DEFAULT now(),
  ingested_by     varchar(100)
);

-- Performance-Indexes
CREATE INDEX rag_docs_embedding_idx
  ON rag_documents
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE INDEX rag_docs_active_idx
  ON rag_documents (repo, collection, is_current)
  WHERE is_current = true;           -- Partial Index — häufigster Query-Pfad

CREATE INDEX rag_docs_history_idx
  ON rag_documents (document_id, valid_from DESC);

CREATE INDEX rag_docs_tsv_idx
  ON rag_documents USING GIN (content_tsv);

CREATE INDEX rag_docs_metadata_idx
  ON rag_documents USING GIN (metadata);

CREATE INDEX rag_docs_temporal_idx
  ON rag_documents (valid_from, valid_until)
  WHERE is_current = false;          -- Partial Index für History-Queries
```

### 3.3 Hybrid Search Query (Reciprocal Rank Fusion)

```sql
WITH vector_search AS (
  SELECT id, content, metadata, parent_id,
    1 - (embedding <=> $1::vector) AS vector_score
  FROM rag_documents
  WHERE repo = $2
    AND ($3::varchar IS NULL OR collection = $3)
    AND (
      CASE WHEN $4::date IS NULL   -- as_of_date=NULL → nur aktuell
           THEN is_current = true
           ELSE valid_from <= $4
             AND (valid_until IS NULL OR valid_until > $4)
      END
    )
  ORDER BY embedding <=> $1::vector
  LIMIT 20
),
keyword_search AS (
  SELECT id, content, metadata, parent_id,
    ts_rank(content_tsv, plainto_tsquery('german', $5)) AS text_score
  FROM rag_documents
  WHERE repo = $2
    AND ($3::varchar IS NULL OR collection = $3)
    AND is_current = true
    AND content_tsv @@ plainto_tsquery('german', $5)
  LIMIT 20
),
fused AS (
  SELECT
    COALESCE(v.id, k.id) AS id,
    COALESCE(v.content, k.content) AS content,
    COALESCE(v.metadata, k.metadata) AS metadata,
    COALESCE(v.parent_id, k.parent_id) AS parent_id,
    COALESCE(v.vector_score, 0) * 0.7
      + COALESCE(k.text_score, 0) * 0.3 AS rrf_score
  FROM vector_search v
  FULL OUTER JOIN keyword_search k ON v.id = k.id
)
SELECT f.*, p.content AS parent_content
FROM fused f
LEFT JOIN rag_documents p ON p.id = f.parent_id
ORDER BY rrf_score DESC
LIMIT $6;
-- $1=query_embedding, $2=repo, $3=collection, $4=as_of_date, $5=query_text, $6=top_k
```

### 3.4 Embedding-Modell: multilingual-e5-large

| Kriterium | multilingual-e5-large | text-embedding-3-small | jina-v3 |
|-----------|----------------------|----------------------|---------|
| Dimensionen | 1024 | 1536 | 1024 |
| Deutsch | ✅ exzellent | ✅ gut | ✅ sehr gut |
| Kosten | ✅ Open Source | ❌ OpenAI API-Kosten | ✅ Open Source |
| Offline-fähig | ✅ | ❌ | ✅ |
| Lizenz | MIT | proprietär | Apache 2.0 |

multilingual-e5-large wird gewählt. Fallback: jina-embeddings-v3.
text-embedding-3-small als zusätzliche Option wenn OpenAI-Budget vorhanden.

### 3.5 Supersession Chain (extended from ADR-161)

```
Version 1 [valid_from: 2020-01-01, valid_until: 2023-12-31, is_current: false]
    │
    └── superseded_by ──► Version 2 [valid_from: 2024-01-01, valid_until: NULL, is_current: true]
```

Bei `rag_supersede(document_id, new_version, new_valid_from)`:
1. `UPDATE rag_documents SET valid_until = new_valid_from - 1, is_current = false, superseded_by = new_id WHERE document_id = X AND is_current = true`
2. `INSERT INTO rag_documents ... (neue Version, is_current = true)`
→ Transaktion — atomar

---

## 4. Betrachtete Alternativen

### Option A: Qdrant als dedizierte Vector-DB
- ✅ Built-in Hybrid Search, native payload filtering
- ❌ Neuer Container (Port, Reverse-Proxy, Monitoring)
- ❌ Keine SQL-Joins für komplexe bitemporal-Queries
- ❌ Kein Transaktions-Support für atomare Supersession
- **Abgelehnt** — Operativer Overhead nicht gerechtfertigt

### Option B: Weaviate
- ✅ Cross-References nativ (Supersession-Links)
- ✅ Multi-tenancy built-in
- ❌ JVM-basiert — hoher Memory-Footprint (min. 2GB)
- ❌ GraphQL-Lernkurve für Team
- ❌ Komplexe Upgrade-Pfade (breaking changes in v4)
- **Abgelehnt** — Overkill für bestehende pgvector-Infrastruktur

### Option C: agent_memory (ADR-113) Tabelle erweitern
- ✅ Kein neues Schema, kein neues Deployment
- ❌ agent_memory ist für Agent-Kontext (Sessions, Decisions) designt
- ❌ Kein `valid_from/valid_until`, kein `parent_id`, kein hierarchisches Chunking
- ❌ ivfflat-Index fehlt — Performance bei RAG-Queries unakzeptabel
- ❌ Semantic Overlap: RAG-Dokumente ≠ Agent-Memory-Entries
- **Abgelehnt** — Falsches Tool für den Job

### Option D: pgvector + neue Tabellen (gewählt)
- ✅ Selbe Infrastruktur (Port 15435, SSH-Tunnel, mcp_hub_db)
- ✅ Volle SQL-Mächtigkeit für bitemporal Queries
- ✅ Atomare Supersession-Transaktionen
- ✅ GIN-Index auf tsvector für BM25-Hybrid-Search
- ✅ Konsistenz mit ADR-161 Supersession-Pattern
- ❌ ivfflat erfordert Re-Index bei >1M Rows (bekanntes pgvector Limit)
- **Gewählt**

---

## 5. Konsequenzen

### 5.1 Positiv

| # | Konsequenz |
|---|------------|
| + | Single-Infrastruktur für alle Repos — kein neues Deployment |
| + | Zeitpunkt-genaue Suche: `as_of_date` für Gesetze/SDS/ADRs |
| + | Immutabilität: Compliance mit GefStoffV §14 und bayerischen Archivgesetzen |
| + | Hybrid Search: Paragraphen-Referenzen ("§55 Abs.1 BayBO") werden korrekt gefunden |
| + | Cross-Repo-Search: eine Query über meiki-hub + risk-hub + platform |
| + | Parent-Document Retrieval: präzises Chunk-Matching + vollständiger Kontext |
| + | Erweiterbar: neue Collection per `INSERT INTO rag_collections` |

### 5.2 Trade-offs

| # | Trade-off | Mitigation |
|---|-----------|------------|
| - | ivfflat Limit bei >1M Vectors | HNSW-Migration wenn nötig (pgvector 0.6+) |
| - | multilingual-e5-large benötigt GPU für schnelles Batch-Embedding | `rag_sync` als Background-Job (Celery/Queue) |
| - | pgvector kein Multi-tenancy nativ | `repo`+`collection` als logische Isolation (ausreichend) |
| - | Kein physisches Delete | Gewünscht — `rag_delete` = soft-delete (is_current=false) |

### 5.3 Nicht in Scope

- Chunking-Logik und Embedding-Erzeugung → ADR-172 (rag-mcp)
- Consumer-spezifische Collections → jeweiliges Repo-ADR (z.B. ADR-006 meiki-hub)
- LLM-Integration (Retrieval → Generation) → zukünftiges ADR
- Re-Ranking (Cross-Encoder) → ADR-172

---

## 6. Confirmation (Verifikation)

| # | Check | Methode |
|---|-------|--------|
| 1 | Schema existiert auf Prod | `\d rag_documents` in psql |
| 2 | ivfflat-Index vorhanden | `\di rag_docs_embedding_idx` |
| 3 | Bitemporal Query korrekt | Integration-Test: `as_of_date=2023-06-01` returnt v1, `as_of_date=today` returnt v2 |
| 4 | Supersession atomar | Test: concurrent supersede → keine doppelten `is_current=true` |
| 5 | Hybrid Search performant | Benchmark: Top-10 in <200ms bei 100k Docs |
| 6 | Immutabilität erzwungen | DB-Constraint: kein DELETE-Grant auf `rag_documents` für App-User |

---

## 7. Referenzen

- [ADR-113: pgvector Agent Memory Store](./ADR-113-pgvector-agent-memory-store.md)
- [ADR-161: Two-Layer-Schema with Supersession Chain for SDS](./ADR-161-shared-sds-library.md) — Supersession-Pattern-Vorbild
- [ADR-170: iil-ingest Document Ingestion Package](./ADR-170-iil-ingest-document-ingestion-package.md) — Text-Extraktion
- [ADR-172: rag-mcp Server](./ADR-172-rag-mcp-server.md) — MCP API auf diesem Schema
- pgvector Documentation: https://github.com/pgvector/pgvector
- multilingual-e5-large: https://huggingface.co/intfloat/multilingual-e5-large
- BEIR Benchmark (Retrieval Benchmarks): https://github.com/beir-cellar/beir
- GefStoffV §14 (40-Jahre-Aufbewahrung CMR-Stoffe)
- Bayerisches Archivgesetz (BayArchivG) Art. 3
