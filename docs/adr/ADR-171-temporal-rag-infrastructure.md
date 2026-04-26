---
status: Proposed
date: 2026-04-26
amended: 2026-04-26
decision-makers:
  - Achim Dehnert
reviewed-by: Principal IT-Architect
depends-on:
  - ADR-113 (pgvector Agent Memory Store)
  - ADR-161 (Two-Layer-Schema with Supersession Chain for SDS)
  - ADR-170 (iil-ingest Document Ingestion Package)
  - ADR-022 (BigAutoField Platform Standard)
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
| **Amended** | 2026-04-26 (v1.1 — Review-Fixes) |
| **Autor** | Achim Dehnert |
| **Reviewer** | Principal IT-Architect |
| **Depends On** | ADR-113, ADR-161, ADR-170, ADR-022 |
| **Implements** | ADR-172 (rag-mcp) nutzt dieses Schema |

### Änderungshistorie

| Version | Datum | Änderung |
|---------|-------|----------|
| 1.0 | 2026-04-26 | Initiale Version |
| 1.1 | 2026-04-26 | Review-Fixes: BigAutoField+public_id (B1), tenant_id durchgehend (B2), deleted_at (B3), HNSW statt ivfflat (B4), UNIQUE Partial Index is_current (B5), 2-Tabellen-Design rag_documents+rag_chunks (K1), embed_model_version auf Chunk-Level (H1), echtes RRF (K3), content_hash UNIQUE (K4), revision_no (K5), CHECK-Constraints (H2/H3), lang-Spalte (H4), DELETE-Trigger (H5) |

---

## Executive Summary

Mehrere Repos (meiki-hub, risk-hub, platform, bfagent) benötigen Semantic Search über versionierte Dokumente. Dieses ADR entscheidet:

1. **pgvector** als Vector-Backend (bereits auf Prod — kein neues Deployment)
2. **3-Tabellen-Design**: `rag_collections` / `rag_documents` (Versionierung) / `rag_chunks` (Embeddings)
3. **Supersession Chain** mit `revision_no` + Partial-UNIQUE-Index auf `is_current=true`
4. **HNSW** Index (pgvector ≥0.5.0, Standard seit Sep 2023)
5. **Echtes RRF** (Cormack et al. 2009) für Hybrid Search
6. **multilingual-e5-large** (1024 Dims, Open Source)

---

## 1. Kontext und Problemstellung

### 1.1 Use Cases

| Repo | Dokument-Typ | Temporale Anforderung |
|------|-----------|-----------------------|
| `meiki-hub` | Bayerische Gesetze (BayBO, BayDSG) | "Was galt am Stichtag 2024-03-15?" |
| `meiki-hub` | Ausführungsverordnungen (AVOs) | Inkrafttreten, Außerkrafttreten |
| `risk-hub` | Sicherheitsdatenblätter (SDS) | Welche Version war beim Unfall gültig? |
| `platform` | ADRs, Workflows | Status-Verlauf, Zeitpunkt der Änderung |
| `bfagent` | Prompt-Templates | Versionen nach Deployment-Tag |

### 1.2 Kernproblem

Juristische und Compliance-Dokumente dürfen **niemals physisch gelöscht** werden (GefStoffV §14, BayArchivG Art. 3). Gleichzeitig braucht es **zeitpunkt-genaue Queries** (`as_of`) und saubere **Soft-Delete-Semantik** (Versionierung ≠ Löschung — beides muss unabhängig steuerbar sein).

### 1.3 Warum pgvector?

| Option | Ops-Aufwand | Temporal | DSGVO | Entscheidung |
|--------|------------|----------|-------|--------------|
| **pgvector** (bestehend) | ✅ null | ✅ SQL | ✅ tenant_id | **Gewählt** |
| Qdrant | neuer Container | ⚠️ payload | ⚠️ eigene Impl. | Abgelehnt |
| Weaviate | JVM, 2GB RAM | ✅ | ✅ | Abgelehnt |

---

## 2. Entscheidungstreiber

| ID | Treiber | Gewichtung |
|----|---------|------------|
| D-1 | Kein neues Deployment — pgvector bereits auf Prod | Hoch |
| D-2 | Zeitpunkt-genaue Queries (`as_of`) | Kritisch |
| D-3 | Immutabilität + Soft-Delete-Trennung | Kritisch |
| D-4 | DSGVO-konforme Tenant-Isolation | Kritisch |
| D-5 | Hybrid Search für deutsche Rechtstexte | Hoch |
| D-6 | BigAutoField-Konformität (ADR-022) | Hoch |

---

## 3. Schema (v1.1 — vollständig korrigiert)

```sql
-- Extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- =========================================================================
-- Collections-Registry
-- =========================================================================
CREATE TABLE rag_collections (
    id                  bigserial    PRIMARY KEY,
    public_id           uuid         NOT NULL UNIQUE DEFAULT gen_random_uuid(),

    tenant_id           bigint       NOT NULL,
    repo                varchar(100) NOT NULL,
    collection          varchar(100) NOT NULL,
    description         jsonb        NOT NULL DEFAULT '{}'::jsonb,
    embed_model         varchar(100) NOT NULL DEFAULT 'multilingual-e5-large',
    embed_model_version varchar(50)  NOT NULL DEFAULT '1.0',
    embed_dimension     int          NOT NULL DEFAULT 1024,
    chunk_strategy      varchar(50)  NOT NULL DEFAULT 'paragraph',

    created_at          timestamptz  NOT NULL DEFAULT now(),
    updated_at          timestamptz  NOT NULL DEFAULT now(),
    deleted_at          timestamptz  NULL,

    CONSTRAINT rag_collections_tenant_repo_collection_uniq
        UNIQUE (tenant_id, repo, collection),
    CONSTRAINT rag_collections_description_is_object
        CHECK (jsonb_typeof(description) = 'object'),
    CONSTRAINT rag_collections_dimension_valid
        CHECK (embed_dimension IN (384, 512, 768, 1024, 1536, 3072, 4096))
);

CREATE INDEX rag_collections_tenant_idx
    ON rag_collections (tenant_id) WHERE deleted_at IS NULL;

-- =========================================================================
-- Logical Documents (Versionierungs-Einheit)
-- =========================================================================
CREATE TABLE rag_documents (
    id              bigserial    PRIMARY KEY,
    public_id       uuid         NOT NULL UNIQUE DEFAULT gen_random_uuid(),

    tenant_id       bigint       NOT NULL,
    collection_id   bigint       NOT NULL REFERENCES rag_collections(id),

    document_key    varchar(500) NOT NULL,       -- stabile externe ID
    revision_no     int          NOT NULL,        -- 1, 2, 3 ... (monoton)
    version_label   varchar(100),                -- "Fassung 2024-01-01"

    valid_from      date         NOT NULL,
    valid_until     date         NULL,            -- NULL = aktuell gültig
    is_current      boolean      NOT NULL DEFAULT true,
    superseded_by   bigint       NULL REFERENCES rag_documents(id),
    revision_note   text         NULL,

    content_hash    varchar(64)  NOT NULL,        -- SHA-256 für Dedup
    source_url      text         NOT NULL DEFAULT '',
    metadata        jsonb        NOT NULL DEFAULT '{}'::jsonb,
    lang            varchar(5)   NOT NULL DEFAULT 'de',

    ingested_at     timestamptz  NOT NULL DEFAULT now(),
    ingested_by     varchar(100) NOT NULL,
    updated_at      timestamptz  NOT NULL DEFAULT now(),
    deleted_at      timestamptz  NULL,            -- Soft-Delete (≠ Versionierung)

    CONSTRAINT rag_documents_revision_positive
        CHECK (revision_no >= 1),
    CONSTRAINT rag_documents_validity_order
        CHECK (valid_until IS NULL OR valid_until >= valid_from),
    CONSTRAINT rag_documents_current_no_until
        CHECK (NOT (is_current = true AND valid_until IS NOT NULL)),
    CONSTRAINT rag_documents_metadata_object
        CHECK (jsonb_typeof(metadata) = 'object'),
    CONSTRAINT rag_documents_revision_unique
        UNIQUE (tenant_id, collection_id, document_key, revision_no)
);

-- Kerngarantie der Supersession Chain: max. 1 aktive Version pro Document
CREATE UNIQUE INDEX rag_documents_one_current_idx
    ON rag_documents (tenant_id, collection_id, document_key)
    WHERE is_current = true AND deleted_at IS NULL;

CREATE UNIQUE INDEX rag_documents_content_dedup_idx
    ON rag_documents (tenant_id, collection_id, document_key, content_hash)
    WHERE deleted_at IS NULL;

CREATE INDEX rag_documents_history_idx
    ON rag_documents (tenant_id, collection_id, document_key, valid_from DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX rag_documents_temporal_idx
    ON rag_documents (tenant_id, valid_from, valid_until) WHERE deleted_at IS NULL;

CREATE INDEX rag_documents_tenant_active_idx
    ON rag_documents (tenant_id, collection_id, is_current)
    WHERE is_current = true AND deleted_at IS NULL;

-- =========================================================================
-- Physical Chunks (Embedding-Einheit — abgeleitet von rag_documents)
-- =========================================================================
CREATE TABLE rag_chunks (
    id              bigserial    PRIMARY KEY,
    public_id       uuid         NOT NULL UNIQUE DEFAULT gen_random_uuid(),

    tenant_id       bigint       NOT NULL,
    document_id     bigint       NOT NULL REFERENCES rag_documents(id) ON DELETE RESTRICT,

    parent_chunk_id bigint       NULL REFERENCES rag_chunks(id) ON DELETE RESTRICT,
    chunk_index     int          NOT NULL DEFAULT 0,

    content         text         NOT NULL,
    content_hash    varchar(64)  NOT NULL,
    token_count     int          NULL,

    embedding       vector(1024) NOT NULL,        -- multilingual-e5-large
    embed_model     varchar(100) NOT NULL,
    embed_model_version varchar(50) NOT NULL,     -- Re-Embedding ohne Schema-Migration

    content_tsv     tsvector GENERATED ALWAYS AS (to_tsvector('german', content)) STORED,
    metadata        jsonb    NOT NULL DEFAULT '{}'::jsonb,

    created_at      timestamptz  NOT NULL DEFAULT now(),
    deleted_at      timestamptz  NULL,

    CONSTRAINT rag_chunks_metadata_object  CHECK (jsonb_typeof(metadata) = 'object'),
    CONSTRAINT rag_chunks_chunk_index_nonneg CHECK (chunk_index >= 0),
    CONSTRAINT rag_chunks_token_count_pos CHECK (token_count IS NULL OR token_count > 0)
);

-- HNSW statt ivfflat: kein Re-Index bei Wachstum, bessere Recall (pgvector ≥0.5.0)
CREATE INDEX rag_chunks_embedding_hnsw_idx
    ON rag_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX rag_chunks_tsv_idx    ON rag_chunks USING gin (content_tsv);
CREATE INDEX rag_chunks_document_idx ON rag_chunks (document_id, chunk_index) WHERE deleted_at IS NULL;
CREATE INDEX rag_chunks_parent_idx ON rag_chunks (parent_chunk_id) WHERE parent_chunk_id IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX rag_chunks_tenant_idx ON rag_chunks (tenant_id) WHERE deleted_at IS NULL;
CREATE INDEX rag_chunks_metadata_idx ON rag_chunks USING gin (metadata jsonb_path_ops);

-- =========================================================================
-- Trigger
-- =========================================================================
CREATE OR REPLACE FUNCTION rag_set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at := now(); RETURN NEW; END; $$;

CREATE TRIGGER rag_collections_updated_at
    BEFORE UPDATE ON rag_collections FOR EACH ROW EXECUTE FUNCTION rag_set_updated_at();
CREATE TRIGGER rag_documents_updated_at
    BEFORE UPDATE ON rag_documents FOR EACH ROW EXECUTE FUNCTION rag_set_updated_at();

CREATE OR REPLACE FUNCTION rag_block_delete() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Physical DELETE forbidden on % (use soft-delete via deleted_at). ADR-171.',
        TG_TABLE_NAME USING ERRCODE = 'insufficient_privilege';
END; $$;

CREATE TRIGGER rag_documents_no_delete BEFORE DELETE ON rag_documents FOR EACH ROW EXECUTE FUNCTION rag_block_delete();
CREATE TRIGGER rag_chunks_no_delete    BEFORE DELETE ON rag_chunks    FOR EACH ROW EXECUTE FUNCTION rag_block_delete();
```

---

## 4. Hybrid Search — echtes RRF (Cormack et al. 2009)

```sql
-- $1=query_embedding, $2=tenant_id, $3=repo, $4=collection,
-- $5=as_of (timestamptz|NULL), $6=query_text, $7=top_k, $8=rrf_k (default 60)
WITH active_documents AS (
    SELECT d.id AS document_id
    FROM rag_documents d
    JOIN rag_collections c ON c.id = d.collection_id
    WHERE d.tenant_id = $2 AND d.deleted_at IS NULL
      AND ($3::varchar IS NULL OR c.repo       = $3)
      AND ($4::varchar IS NULL OR c.collection = $4)
      AND (CASE WHEN $5::timestamptz IS NULL
                THEN d.is_current = true
                ELSE d.valid_from <= $5::date
                 AND (d.valid_until IS NULL OR d.valid_until > $5::date)
           END)
),
vector_ranked AS (
    SELECT ch.id, ROW_NUMBER() OVER (ORDER BY ch.embedding <=> $1::vector) AS rank
    FROM rag_chunks ch JOIN active_documents ad ON ad.document_id = ch.document_id
    WHERE ch.deleted_at IS NULL
    ORDER BY ch.embedding <=> $1::vector LIMIT 50
),
keyword_ranked AS (
    SELECT ch.id,
           ROW_NUMBER() OVER (ORDER BY ts_rank(ch.content_tsv, plainto_tsquery('german', $6)) DESC) AS rank
    FROM rag_chunks ch JOIN active_documents ad ON ad.document_id = ch.document_id
    WHERE ch.deleted_at IS NULL AND ch.content_tsv @@ plainto_tsquery('german', $6)
    LIMIT 50
),
fused AS (
    SELECT COALESCE(v.id, k.id) AS chunk_id,
           COALESCE(1.0 / ($8 + v.rank), 0) + COALESCE(1.0 / ($8 + k.rank), 0) AS rrf_score
    FROM vector_ranked v FULL OUTER JOIN keyword_ranked k ON v.id = k.id
)
SELECT ch.id, ch.public_id, d.document_key, d.revision_no, d.version_label,
       d.valid_from, d.valid_until, ch.content AS chunk_content, p.content AS parent_content,
       ch.metadata, d.metadata AS doc_metadata, f.rrf_score
FROM fused f
JOIN rag_chunks ch     ON ch.id = f.chunk_id
JOIN rag_documents d   ON d.id  = ch.document_id
LEFT JOIN rag_chunks p ON p.id  = ch.parent_chunk_id
ORDER BY f.rrf_score DESC LIMIT $7;
```

---

## 5. Embedding-Modell: multilingual-e5-large

| Kriterium | multilingual-e5-large | text-embedding-3-small | jina-v3 |
|-----------|----------------------|----------------------|---------|
| Dimensionen | 1024 | 1536 | 1024 |
| Deutsch | ✅ exzellent | ✅ gut | ✅ sehr gut |
| Kosten | ✅ Open Source | ❌ API-Kosten | ✅ Open Source |
| Offline | ✅ | ❌ | ✅ |

`vector(1024)` initial. Migration auf `halfvec(1024)` nach Benchmark (Recall@10 + Storage-Vergleich auf 100k Chunks) als ADR-Amendment.

---

## 6. Offene Entscheidungen

| # | Frage | Status |
|---|-------|--------|
| OE-1 | `vector(1024)` vs `halfvec(1024)` | Benchmark nach erster Ingest-Charge |
| OE-2 | Partitioning bei >1M Chunks (Range auf `repo`, Hash auf `tenant_id`) | Monitoring-Trigger setzen |
| OE-3 | Multi-Language `content_tsv` (aktuell nur `german`) | Bei Bedarf Spalte je Sprache |

---

## 7. Betrachtete Alternativen (Summary)

- **Qdrant**: neuer Container, keine SQL-Transaktionen → Abgelehnt
- **Weaviate**: JVM 2GB, GraphQL-Lernkurve → Abgelehnt
- **agent_memory (ADR-113) erweitern**: falsches Semantik-Modell, kein ivfflat/HNSW → Abgelehnt
- **pgvector + neue Tabellen**: ✅ Gewählt

---

## 8. Konsequenzen

| + | Konsequenz |
|---|------------|
| + | Single-Infrastruktur für alle Repos — kein neues Deployment |
| + | Zeitpunkt-genaue Suche: `as_of` für Gesetze/SDS/ADRs |
| + | DSGVO: `tenant_id` auf jeder Tabelle |
| + | Immutabilität via DELETE-Trigger erzwungen |
| + | Supersession-Garantie via UNIQUE Partial Index |
| + | Re-Embedding ohne Migration: `embed_model_version` auf Chunk-Level |

| - | Trade-off | Mitigation |
|---|-----------|------------|
| - | HNSW Build-Zeit höher als ivfflat | Batch-Build vor Produktivstart |
| - | `embed_model_version` erhöht Chunk-Row-Größe | Vernachlässigbar (~50B/Row) |
| - | Partitioning erst bei >1M Chunks | Monitoring-Alert konfigurieren |

---

## 9. Confirmation

| # | Check | Methode |
|---|-------|--------|
| 1 | Schema valid | `\d rag_documents`, `\d rag_chunks` |
| 2 | HNSW-Index vorhanden | `\di rag_chunks_embedding_hnsw_idx` |
| 3 | Supersession atomar | Test: concurrent supersede → kein doppeltes `is_current=true` (Partial UNIQUE greift) |
| 4 | as_of-Query korrekt | Test: v1 auf `as_of=2021-01-01`, v2 auf `as_of=today` |
| 5 | DELETE-Trigger | `DELETE FROM rag_documents WHERE id=1` → `insufficient_privilege` |
| 6 | content_hash Dedup | Gleicher Hash → `UNIQUE`-Violation bei Re-Ingest |

---

## 10. Referenzen

- [ADR-022: BigAutoField Platform Standard](./ADR-022-platform-consistency-standard.md)
- [ADR-113: pgvector Agent Memory Store](./ADR-113-pgvector-agent-memory-store.md)
- [ADR-161: Supersession Chain](./ADR-161-shared-sds-library.md)
- [ADR-170: iil-ingest](./ADR-170-iil-ingest-document-ingestion-package.md)
- [ADR-172: rag-mcp Server](./ADR-172-rag-mcp-server.md)
- pgvector HNSW: https://github.com/pgvector/pgvector#hnsw
- Cormack et al. 2009: Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods
- GefStoffV §14 (40-Jahre-Aufbewahrung CMR-Stoffe)
- BayArchivG Art. 3 (Aufbewahrungspflicht)
