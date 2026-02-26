# platform-search

> Platform-wide hybrid search: pgvector + FTS with Reciprocal Rank Fusion (ADR-087)

## Overview

Combines PostgreSQL pgvector semantic search with full-text search (FTS),
merged via Reciprocal Rank Fusion (RRF). Optional MMR diversity filter
and temporal decay scoring.

## Installation

```bash
pip install -e packages/platform-search
```

## Usage

```python
from platform_search.service import SearchService

results = SearchService.search(
    query="Gefährdungsbeurteilung Arbeitsplatz",
    tenant_id="abc-123",
    source_types=["assessment"],
    top_k=10,
)
```

## Configuration

```python
# config/settings/base.py
PLATFORM_SEARCH = {
    "EMBEDDING_PROVIDER": "openai",
    "EMBEDDING_MODEL": "text-embedding-3-small",
    "EMBEDDING_DIMENSIONS": 1536,
    "VECTOR_WEIGHT": 0.6,
    "TEXT_WEIGHT": 0.4,
    "RRF_K": 60,
    "DEFAULT_TOP_K": 10,
}
```

Requires `OPENAI_API_KEY` in Django settings (ADR-045).

## Database

Migration creates `search_chunks` table in `content_store` DB (ADR-062).
Run: `python manage.py migrate platform_search --database=content_store`

## Related ADRs

- **ADR-087**: Hybrid Search Architecture
- **ADR-062**: Content Store
- **ADR-045**: Secret Management
- **ADR-072**: Schema Isolation (Row-Level deviation documented)
