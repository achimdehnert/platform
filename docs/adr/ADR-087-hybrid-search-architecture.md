---
status: accepted
date: 2026-02-26
decision-makers: [Platform Team]
---

<!-- Drift-Detector-Felder: staleness_months: 12, drift_check_paths: platform/packages/platform-search/**, supersedes_check: none -->

# ADR-087: Adopt pgvector + FTS Hybrid Search as Platform-wide Semantic Search Engine

> **Scope:** `platform`, `bfagent`, `dev-hub`, `risk-hub`, `weltenhub`  
> **Inspiriert von:** OpenClaw `src/memory/` (MIT-Lizenz) — Konzeptübernahme, kein Code-Port  

---

## Context and Problem Statement

Mehrere Plattform-Apps benötigen semantische Suche über große Textmengen:

| App | Use Case | Datenvolumen |
|-----|----------|--------------|
| **bfagent** | Kapitel, Szenen, Charaktere in Büchern durchsuchen | 10k–100k Chunks |
| **dev-hub** | TechDocs über alle Repos durchsuchen | 1k–10k Docs |
| **risk-hub** | Gefährdungsbeurteilungen semantisch finden | 1k–50k Einträge |
| **weltenhub** | Story-Universen: Orte, Figuren, Handlungsstränge | 5k–50k Chunks |

Aktuelle Suche ist keyword-basiert (Django ORM `__icontains` / `__search`). Das reicht nicht für:
- Synonyme ("Gefahr" ≈ "Risiko" ≈ "Bedrohung")
- Semantische Ähnlichkeit ("Held rettet Prinzessin" ≈ "Ritter befreit Gefangene")
- Cross-Language-Suche (DE↔EN)

## Decision Drivers

- **Semantische Suche** über heterogene Textmengen (Bücher, Docs, Assessments, Stories)
- **Kein zusätzlicher Infra-Service** — PostgreSQL bereits vorhanden
- **Multi-Tenant-Isolation** — jeder Tenant sieht nur eigene Daten
- **Wiederverwendbarkeit** als Shared Platform-Package
- **Kosteneffizienz** — OpenAI Embeddings sind günstig ($0.02/1M Tokens)
- **Erweiterbarkeit** — MMR, Temporal Decay, Faceted Search nachträglich addierbar

## Considered Options

1. **pgvector + FTS Hybrid Search** (gewählt)
2. **Elasticsearch / OpenSearch**
3. **SQLite + sqlite-vec** (OpenClaw-Ansatz)
4. **Nur Vector Search** (pgvector ohne FTS)
5. **Nur Full-Text Search** (PostgreSQL tsvector)
6. **ChromaDB / Pinecone** (Managed Vector DB)

## Decision Outcome

**Chosen option: "pgvector + FTS Hybrid Search"**, because:
- Nutzt bestehende PostgreSQL-Infrastruktur (kein neuer Service)
- Kombiniert semantische Ähnlichkeit (Embeddings) mit exakter Keyword-Suche (FTS)
- Reciprocal Rank Fusion (RRF) merged beide Ergebnismengen robust
- Tenant-Isolation via `WHERE tenant_id = ...` (Row-Level, siehe §ADR-072 Abweichung)
- Alle Apps profitieren über ein Shared Package

### ADR-072 Schema-Isolation — Begründete Abweichung

ADR-072 fordert Schema-Isolation für Multi-Tenancy. `search_chunks` nutzt stattdessen **Row-Level Isolation** (`WHERE tenant_id = ...`), weil:
- Die `search_chunks` Tabelle ist eine **zentrale Cross-App-Ressource** — Schema-Isolation würde pgvector-Indizes pro Tenant duplizieren (Memory-Overhead bei HNSW)
- Embedding-Indizes skalieren besser als einzelne Tabelle (HNSW `ef_construction` bezieht sich auf Gesamtdatenvolumen)
- Cross-Tenant-Suche ist **nicht erforderlich** — alle Queries filtern immer nach `tenant_id`
- Der `idx_chunks_tenant` B-Tree-Index auf `tenant_id` gewährleistet performante Isolation

Dies ist eine bewusste Ausnahme, dokumentiert in Übereinstimmung mit ADR-072 §Exceptions.

### DB-Zuordnung

Die `search_chunks` Tabelle wird in der **Content Store DB** (`content_store`, vgl. ADR-062) angelegt:
- Content Store ist bereits für AI-generierte/verarbeitete Inhalte vorgesehen
- `CONTENT_STORE_DSN` ist bereits als Secret konfiguriert (ADR-045)
- Apps connecten über `SearchService` → Content Store DB (read/write via Service-Layer)

### Schema-Evolution (Expand-Contract)

Zukünftige Schema-Änderungen (z.B. Dimensions-Wechsel bei Embedding-Modell-Upgrade) folgen dem Expand-Contract-Pattern (ADR-021 §2.16):
1. **Expand**: Neue Column `embedding_v2 vector(N)` hinzufügen, parallel befüllen
2. **Migrate**: Celery-Task re-embedded alle Chunks mit neuem Modell (tracking via `embedding_model`)
3. **Contract**: Alte `embedding` Column entfernen nach vollständigem Re-Indexing

## Architektur

```
Query
  ├── Vector Search (pgvector, Cosine Similarity)
  │     → Top-K semantisch ähnliche Chunks
  ├── Full-Text Search (PostgreSQL tsvector + ts_rank)
  │     → Top-K keyword-matched Chunks
  └── Reciprocal Rank Fusion (RRF)
        → Merged + Re-Ranked Results
              └── Optional: MMR Diversity Filter
                    └── Optional: Temporal Decay
```

### Komponenten

#### 1. Vector Store (pgvector)

```sql
-- Deployed in content_store DB (ADR-062)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE search_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    embedding_model VARCHAR(100) NOT NULL DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('german', content)
    ) STORED
);

CREATE INDEX idx_chunks_embedding ON search_chunks
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_chunks_fts ON search_chunks USING gin(search_vector);
CREATE INDEX idx_chunks_tenant ON search_chunks (tenant_id);
CREATE INDEX idx_chunks_source ON search_chunks (source_type, source_id);
CREATE INDEX idx_chunks_model ON search_chunks (embedding_model);
```

#### 2. Embedding Service

```python
# platform/packages/platform-search/embeddings.py
import httpx
from pydantic import BaseModel, ConfigDict, Field

class EmbeddingConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    provider: str = Field(default="openai", description="openai | local")
    model: str = Field(default="text-embedding-3-small", description="Embedding model")
    dimensions: int = Field(default=1536, description="Vector dimensions")
    batch_size: int = Field(default=100, description="Chunks per API call")

def embed_texts(
    texts: list[str],
    config: EmbeddingConfig | None = None,
) -> list[list[float]]:
    """Embed texts via configured provider (sync — safe for Django views + Celery)."""
    if config is None:
        config = EmbeddingConfig()
    # httpx sync client for OpenAI Embeddings API
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {_get_api_key()}"},
            json={"input": texts, "model": config.model},
        )
        response.raise_for_status()
        data = response.json()
    return [item["embedding"] for item in data["data"]]

def _get_api_key() -> str:
    """Load OPENAI_API_KEY from Django settings (ADR-045)."""
    from django.conf import settings
    return settings.OPENAI_API_KEY
```

#### 3. Search Service (Service-Layer)

```python
# platform/packages/platform-search/service.py
from dataclasses import dataclass
from django.db import connections

@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    source_type: str
    source_id: str
    content: str
    score: float
    vector_rank: int | None = None
    text_rank: int | None = None

class SearchService:
    """Platform-wide hybrid search service.
    
    All methods are sync — safe for Django views and Celery tasks.
    Uses content_store DB connection (ADR-062).
    """
    
    DB_ALIAS = "content_store"
    
    @classmethod
    def search(
        cls,
        query: str,
        tenant_id: str,
        source_types: list[str] | None = None,
        top_k: int = 10,
        vector_weight: float = 0.6,
        text_weight: float = 0.4,
    ) -> list[SearchResult]:
        """Sync hybrid search — safe for Django views."""
        vector_results = cls._vector_search(query, tenant_id, source_types, top_k)
        text_results = cls._text_search(query, tenant_id, source_types, top_k)
        return reciprocal_rank_fusion(
            vector_results, text_results,
            vector_weight=vector_weight,
            text_weight=text_weight,
        )
    
    @classmethod
    def _vector_search(
        cls,
        query: str,
        tenant_id: str,
        source_types: list[str] | None,
        top_k: int,
    ) -> list[SearchResult]:
        """Embed query and find nearest neighbors via pgvector."""
        from platform_search.embeddings import embed_texts
        query_embedding = embed_texts([query])[0]
        with connections[cls.DB_ALIAS].cursor() as cursor:
            cursor.execute(
                "SELECT id, source_type, source_id, content, "
                "embedding <=> %s::vector AS distance "
                "FROM search_chunks WHERE tenant_id = %s "
                + ("AND source_type = ANY(%s) " if source_types else "")
                + "ORDER BY distance LIMIT %s",
                [query_embedding, tenant_id]
                + ([source_types] if source_types else [])
                + [top_k],
            )
            return [
                SearchResult(
                    chunk_id=str(row[0]), source_type=row[1],
                    source_id=str(row[2]), content=row[3],
                    score=1.0 - row[4],
                )
                for row in cursor.fetchall()
            ]
    
    @classmethod
    def _text_search(
        cls,
        query: str,
        tenant_id: str,
        source_types: list[str] | None,
        top_k: int,
    ) -> list[SearchResult]:
        """Full-text search via PostgreSQL tsvector."""
        with connections[cls.DB_ALIAS].cursor() as cursor:
            cursor.execute(
                "SELECT id, source_type, source_id, content, "
                "ts_rank(search_vector, plainto_tsquery('german', %s)) AS rank "
                "FROM search_chunks WHERE tenant_id = %s "
                "AND search_vector @@ plainto_tsquery('german', %s) "
                + ("AND source_type = ANY(%s) " if source_types else "")
                + "ORDER BY rank DESC LIMIT %s",
                [query, tenant_id, query]
                + ([source_types] if source_types else [])
                + [top_k],
            )
            return [
                SearchResult(
                    chunk_id=str(row[0]), source_type=row[1],
                    source_id=str(row[2]), content=row[3],
                    score=row[4],
                )
                for row in cursor.fetchall()
            ]
    
    @classmethod
    def health_check(cls) -> dict[str, bool | str]:
        """Check pgvector availability for /healthz/ endpoint."""
        try:
            with connections[cls.DB_ALIAS].cursor() as cursor:
                cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
                row = cursor.fetchone()
                if row:
                    return {"healthy": True, "pgvector_version": row[0]}
                return {"healthy": False, "error": "pgvector extension not installed"}
        except Exception as exc:
            return {"healthy": False, "error": str(exc)}


def reciprocal_rank_fusion(
    vector_results: list[SearchResult],
    text_results: list[SearchResult],
    vector_weight: float = 0.6,
    text_weight: float = 0.4,
    k: int = 60,
) -> list[SearchResult]:
    """Merge vector + text results via Reciprocal Rank Fusion.
    
    Score = vector_weight * 1/(k + vector_rank) + text_weight * 1/(k + text_rank)
    
    Reference: Cormack et al. (2009), OpenClaw src/memory/hybrid.ts
    """
    scores: dict[str, float] = {}
    results_map: dict[str, SearchResult] = {}
    
    for rank, result in enumerate(vector_results, 1):
        scores[result.chunk_id] = scores.get(result.chunk_id, 0.0)
        scores[result.chunk_id] += vector_weight * (1.0 / (k + rank))
        results_map[result.chunk_id] = result
    
    for rank, result in enumerate(text_results, 1):
        scores[result.chunk_id] = scores.get(result.chunk_id, 0.0)
        scores[result.chunk_id] += text_weight * (1.0 / (k + rank))
        results_map[result.chunk_id] = result
    
    sorted_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    return [
        SearchResult(
            chunk_id=cid,
            source_type=results_map[cid].source_type,
            source_id=results_map[cid].source_id,
            content=results_map[cid].content,
            score=scores[cid],
        )
        for cid in sorted_ids
    ]
```

#### 4. MMR Diversity Filter (Optional)

```python
# platform/packages/platform-search/mmr.py
import numpy as np

def maximal_marginal_relevance(
    query_embedding: list[float],
    result_embeddings: list[list[float]],
    results: list[SearchResult],
    lambda_param: float = 0.7,
    top_k: int = 10,
) -> list[SearchResult]:
    """Re-rank results for diversity via MMR.
    
    MMR = lambda * sim(q, d) - (1-lambda) * max(sim(d, d_selected))
    
    Reference: Carbonell & Goldstein (1998), OpenClaw src/memory/mmr.ts
    """
    ...
```

#### 5. Temporal Decay (Optional)

```python
# platform/packages/platform-search/decay.py
import math
from datetime import datetime, timezone

def apply_temporal_decay(
    results: list[SearchResult],
    half_life_days: float = 90.0,
    decay_weight: float = 0.1,
) -> list[SearchResult]:
    """Boost recent results via exponential decay.
    
    decay = exp(-ln(2) * age_days / half_life)
    final_score = (1 - decay_weight) * score + decay_weight * decay
    
    Reference: OpenClaw src/memory/temporal-decay.ts
    """
    ...
```

### Integration pro App

| App | Chunk-Quelle | Trigger |
|-----|-------------|--------|
| **bfagent** | `Chapter.content`, `Scene.text` | Post-Save Signal → Celery Task |
| **dev-hub** | TechDocs Markdown-Dateien | Git-Webhook → Re-Index |
| **risk-hub** | `RiskAssessment.description` | Post-Save Signal → Celery Task |
| **weltenhub** | `ContentBlock.body` | Post-Save Signal → Celery Task |

### Konfiguration

```python
# config/settings/base.py
PLATFORM_SEARCH = {
    "EMBEDDING_PROVIDER": "openai",
    "EMBEDDING_MODEL": "text-embedding-3-small",
    "EMBEDDING_DIMENSIONS": 1536,
    "VECTOR_WEIGHT": 0.6,
    "TEXT_WEIGHT": 0.4,
    "RRF_K": 60,
    "MMR_LAMBDA": 0.7,
    "TEMPORAL_DECAY_HALF_LIFE_DAYS": 90,
    "DEFAULT_TOP_K": 10,
}
```

### Graceful Degradation

- **pgvector nicht installiert**: `SearchService.search()` fällt auf reine FTS zurück, loggt Warning
- **Embedding-API nicht erreichbar**: Nur FTS-Ergebnisse werden geliefert, `vector_results = []`
- **Content Store DB nicht erreichbar**: `SearchServiceUnavailableError` wird geworfen, App degradiert graceful (wie ADR-062 Content Store Pattern)

## Pros and Cons of the Options

### Option 1: pgvector + FTS Hybrid Search (gewählt)

- Good, because it nutzt bestehende PostgreSQL-Infrastruktur
- Good, because it kombiniert semantische + keyword-basierte Suche
- Good, because it ist tenant-isoliert und wiederverwendbar als Package
- Good, because kein zusätzlicher Service zu betreiben
- Bad, because Embedding-Kosten (OpenAI API) — ca. $0.02/1M Tokens
- Bad, because initiales Indexing bei großen Datenmengen zeitaufwändig
- Bad, because pgvector Extension muss auf Server installiert werden

### Option 2: Elasticsearch / OpenSearch

- Good, because bewährte Volltextsuchmaschine mit Vector-Support
- Good, because exzellente Performance bei >10M docs
- Bad, because separate Infrastruktur (JVM, Cluster, RAM)
- Bad, because massiver Overhead für unsere Datenvolumen (1k–100k Docs)
- Bad, because zusätzliche Ops-Last

### Option 3: SQLite + sqlite-vec (OpenClaw-Ansatz)

- Good, because zero-dependency, embedded
- Good, because OpenClaw-Referenzimplementierung vorhanden
- Bad, because wir haben bereits PostgreSQL
- Bad, because kein Multi-User-Support, keine Tenant-Isolation

### Option 4: Nur Vector Search

- Good, because einfacher — nur ein Suchpfad
- Bad, because keyword-Matches (exakte Begriffe, IDs) gehen verloren
- Bad, because schlechtere Ergebnisse bei fachspezifischen Begriffen

### Option 5: Nur Full-Text Search

- Good, because kein Embedding-Provider nötig, keine API-Kosten
- Bad, because keine semantische Ähnlichkeit
- Bad, because Cross-Language-Suche nicht möglich

### Option 6: ChromaDB / Pinecone

- Good, because managed Service, wenig Ops
- Bad, because externe Abhängigkeit, Vendor Lock-in
- Bad, because kein Self-Hosting (DSGVO-Risiko)

## Consequences

- Good, because semantische + keyword-Suche in einer Query
- Good, because kein zusätzlicher Service (pgvector = PostgreSQL Extension)
- Good, because tenant-isoliert (WHERE tenant_id = ...)
- Good, because wiederverwendbar als Platform-Package
- Good, because Graceful Degradation bei Service-Ausfällen
- Bad, because Embedding-Kosten (OpenAI API) — ca. $0.02/1M Tokens
- Bad, because initiales Indexing bei großen Datenmengen
- Bad, because pgvector Extension muss auf Server installiert werden

### Risks

- HNSW-Index Memory-Overhead bei >1M rows — dann IVFFlat evaluieren
- Embedding-Modell-Wechsel erfordert Re-Indexing (Expand-Contract, siehe oben)

### Confirmation

Compliance wird verifiziert durch:
1. **pytest-Suite**: Mindestens 3 Known-Good-Queries pro App mit erwarteten Ergebnissen
2. **Health-Check**: `SearchService.health_check()` integriert in `/healthz/` Endpoint jeder App
3. **Re-Indexing-Tracking**: `embedding_model` Column erlaubt Identifikation veralteter Embeddings
4. **Graceful Degradation Test**: Test dass FTS-Fallback funktioniert wenn Embedding-API unavailable

## Open Questions

| # | Frage | Status | Empfehlung |
|---|-------|--------|------------|
| Q1 | **Chunk-Größe**: Wie groß sollten Chunks sein? | Offen | 512–1024 Tokens, mit 128-Token Overlap |
| Q2 | **Overlap-Strategie**: Sliding Window vs. Paragraph-basiert? | Offen | Paragraph-basiert für narrative Texte, Sliding Window für technische Docs |
| Q3 | **HNSW vs. IVFFlat**: Ab welcher Datenmenge wechseln? | Offen | HNSW bis 1M rows, dann IVFFlat evaluieren |
| Q4 | **Re-Indexing-Prozess**: Wie wird bei Modell-Wechsel re-indexed? | Offen | Celery-Task iteriert über Chunks mit altem `embedding_model`, batched re-embed |
| Q5 | **FTS-Sprache**: Nur `german` oder auch `english` + `simple`? | Offen | `german` als Default, `simple` als Fallback für Mixed-Content |
| Q6 | **MMR/Temporal Decay Aktivierung**: Wann werden optionale Features aktiviert? | Deferred | Nach Phase 3 evaluieren basierend auf User-Feedback |

## Implementierungsplan

1. **Phase 1**: `platform/packages/platform-search/` Grundstruktur + SearchService
2. **Phase 2**: pgvector auf Prod-Server installieren (`apt install postgresql-16-pgvector`)
3. **Phase 3**: Integration in bfagent (Proof of Concept)
4. **Phase 4**: Integration in dev-hub + risk-hub + weltenhub

## More Information

### Related ADRs

- **ADR-021**: Platform Infrastructure — Expand-Contract Migration (§2.16)
- **ADR-035**: Shared Django Tenancy Package — `TenantModel` base class
- **ADR-045**: Secret Management — `OPENAI_API_KEY` via SOPS
- **ADR-062**: Content Store — DB-Zuordnung für `search_chunks`
- **ADR-072**: Multi-Tenancy Schema-Isolation — begründete Abweichung (Row-Level)

### External References

- [pgvector](https://github.com/pgvector/pgvector) — PostgreSQL vector extension
- [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) — Cormack et al. 2009
- OpenClaw `src/memory/hybrid.ts` — Hybrid merge implementation (MIT)
- OpenClaw `src/memory/mmr.ts` — MMR diversity filter (MIT)
- OpenClaw `src/memory/temporal-decay.ts` — Temporal decay scoring (MIT)
