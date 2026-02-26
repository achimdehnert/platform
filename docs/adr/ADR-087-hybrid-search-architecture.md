# ADR-087: Hybrid Search Architecture — pgvector + FTS + Reciprocal Rank Fusion

> **Status:** Proposed  
> **Datum:** 2026-02-26  
> **Autor:** Platform Team  
> **Scope:** `platform`, `bfagent`, `dev-hub`, `risk-hub`  
> **Inspiriert von:** OpenClaw `src/memory/` (MIT-Lizenz) — Konzeptübernahme, kein Code-Port  

---

## Kontext

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

## Entscheidung

Wir implementieren ein **Hybrid Search System** als Platform-Package, das zwei Suchstrategien kombiniert:

### Architektur

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
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE search_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    source_type VARCHAR(50) NOT NULL,   -- 'book_chapter', 'tech_doc', 'risk_assessment'
    source_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),             -- OpenAI text-embedding-3-small
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    -- FTS column
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('german', content)
    ) STORED
);

CREATE INDEX idx_chunks_embedding ON search_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_chunks_fts ON search_chunks USING gin(search_vector);
CREATE INDEX idx_chunks_tenant ON search_chunks (tenant_id);
CREATE INDEX idx_chunks_source ON search_chunks (source_type, source_id);
```

#### 2. Embedding Service

```python
# platform/packages/platform-search/embeddings.py
from pydantic import BaseModel, ConfigDict, Field

class EmbeddingConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    provider: str = Field(default="openai", description="openai | local")
    model: str = Field(default="text-embedding-3-small", description="Embedding model")
    dimensions: int = Field(default=1536, description="Vector dimensions")
    batch_size: int = Field(default=100, description="Chunks per API call")

async def embed_texts(
    texts: list[str],
    config: EmbeddingConfig,
) -> list[list[float]]:
    """Embed texts via configured provider."""
    ...
```

#### 3. Hybrid Search mit RRF

```python
# platform/packages/platform-search/hybrid.py
from dataclasses import dataclass

@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    source_type: str
    source_id: str
    content: str
    score: float
    vector_rank: int | None = None
    text_rank: int | None = None

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

## Alternativen (verworfen)

| Alternative | Warum verworfen |
|-------------|----------------|
| **Elasticsearch** | Separate Infrastruktur, Overhead für unsere Größe |
| **SQLite + sqlite-vec** (OpenClaw-Ansatz) | Wir haben bereits PostgreSQL; pgvector ist nativer |
| **Nur Vector Search** | Keyword-Matches (exakte Begriffe, IDs) gehen verloren |
| **Nur FTS** | Keine semantische Ähnlichkeit |
| **ChromaDB / Pinecone** | Externe Abhängigkeit, Kosten, kein Self-Hosting |

## Konsequenzen

### Positiv
- Semantische + Keyword-Suche in einer Query
- Kein zusätzlicher Service (pgvector = PostgreSQL Extension)
- Tenant-isoliert (WHERE tenant_id = ...)
- Wiederverwendbar als Platform-Package

### Negativ
- Embedding-Kosten (OpenAI API) — ca. $0.02/1M Tokens
- Initiales Indexing bei großen Datenmengen
- pgvector Extension muss auf Server installiert werden

### Risiken
- pgvector IVFFlat-Index erfordert Re-Build bei signifikantem Datenwachstum
- Embedding-Modell-Wechsel erfordert vollständiges Re-Indexing

## Implementierungsplan

1. **Phase 1**: `platform/packages/platform-search/` Grundstruktur
2. **Phase 2**: pgvector auf Prod-Server installieren (`apt install postgresql-16-pgvector`)
3. **Phase 3**: Integration in bfagent (Proof of Concept)
4. **Phase 4**: Integration in dev-hub + risk-hub

## Referenzen

- [pgvector](https://github.com/pgvector/pgvector) — PostgreSQL vector extension
- [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) — Cormack et al. 2009
- OpenClaw `src/memory/hybrid.ts` — Hybrid merge implementation (MIT)
- OpenClaw `src/memory/mmr.ts` — MMR diversity filter (MIT)
- OpenClaw `src/memory/temporal-decay.ts` — Temporal decay scoring (MIT)
