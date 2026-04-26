---
status: Proposed
date: 2026-04-26
amended: 2026-04-26
decision-makers:
  - Achim Dehnert
reviewed-by: Principal IT-Architect
depends-on:
  - ADR-171 (Temporal RAG Infrastructure — Schema)
  - ADR-170 (iil-ingest — Text-Extraktion)
  - ADR-113 (pgvector — bestehende Infrastruktur)
  - ADR-010 (MCP Tool Governance)
  - ADR-022 (BigAutoField Platform Standard)
repo: platform
implementation_status: none
staleness_months: 6
drift_check_paths:
  - mcp-hub/rag_mcp/
---

# ADR-172: rag-mcp Server — Platform-Wide RAG API

| Metadaten | |
|-----------|---|
| **Status** | Proposed |
| **Datum** | 2026-04-26 |
| **Amended** | 2026-04-26 (v1.1 — Review-Fixes) |
| **Autor** | Achim Dehnert |
| **Reviewer** | Principal IT-Architect |
| **Depends On** | ADR-171, ADR-170, ADR-010, ADR-022 |
| **Consumers** | meiki-hub (ADR-006), risk-hub, platform, bfagent |

### Änderungshistorie

| Version | Datum | Änderung |
|---------|-------|----------|
| 1.0 | 2026-04-26 | Initiale Version |
| 1.1 | 2026-04-26 | Review-Fixes: tenant_id in allen Signaturen (B1), Auth via authentik/read_secret (B2), Celery-Async für Ingest+Supersede+Sync + rag_status Tool (B3), idempotency_key (B4), ASGI/async_to_sync (B5), Service-Layer-Trennung (K1), read_secret() für DB-Credentials (K2), Rate-Limiting (K3), Reranker als separater HTTP-Service (K4), OpenTelemetry (K5), as_of als timestamptz (K6), confirm_all_revisions (K7), Pydantic-v2-Output-Models (Alternative C) |

---

## Executive Summary

ADR-171 definiert das Datenbankschema. Dieses ADR definiert den **MCP-Server** (`rag-mcp`), der alle RAG-Operationen als standardisierte MCP-Tools exponiert. Kein Consumer greift direkt auf die DB zu.

Kernentscheidungen v1.1:
1. `tenant_id` als **Pflicht-Parameter** in jedem Tool
2. **Celery-Async** für Ingest/Supersede/Sync + `rag_status`-Tool für Polling
3. **idempotency_key** für alle schreibenden Operationen
4. **Auth** via authentik / mTLS (ADR-010)
5. **Reranker als separater HTTP-Service** (Modell-Hosting unabhängig vom MCP-Prozess)
6. **OpenTelemetry Tracing** durchgehend
7. **Pydantic v2** für typsichere Tool-Outputs

---

## 1. Kontext

Ohne zentralisierte API würde jeder Consumer Chunking, Embedding, Supersession und Temporal-Queries selbst implementieren. `rag-mcp` ist die single API surface — analog wie `orchestrator-mcp` für Agent-Memory.

---

## 2. Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│  rag-mcp Server (FastMCP, async, ASGI)                            │
│  tools/         →  services/      →  db/ (psycopg[async])         │
│  (dünne Adapter)   (Business-Logik)                                │
│        │              ↓                                            │
│        │         Celery dispatch (acks_late=True)                  │
│        │              ↓                                            │
│        │         rag-worker (Celery Worker)                        │
│        │         Chunking, Supersession-Transaktion                │
│        │              ↓                                            │
│        ↓         Embedder-Service (HTTP, separater Container)       │
│   authentik/mTLS  /embed  (multilingual-e5-large)                  │
│                   /rerank (BGE-Reranker-v2-m3)                     │
│                                                                    │
│   pgvector (mcp_hub_db, Port 15435 — bestehend)                    │
│   OpenTelemetry Tracing: tools → services → db, embedder, celery  │
└─────────────────────────────────────────────────────────────────┘

Kerntrennung:
  rag-mcp:          dünner MCP-Adapter, validiert, dispatched, auth
  rag-worker:       Embedding, Chunking, Supersession-Transaktionen
  embedder-service: Modell-Hosting (kann GPU-Node sein), lazy-start
```

---

## 3. API-Design (v1.1 — alle Signaturen korrigiert)

```python
# ========================
# 3.1 rag_ingest — async via Celery
# ========================
async def rag_ingest(
    *,
    tenant_id:       int,                    # PFLICHT — aus platform_context
    idempotency_key: str,                    # PFLICHT — UUID4 vom Consumer
    repo:            str,
    collection:      str,
    document_key:    str,                    # stabile externe ID
    content:         str,                    # Volltext (via iil-ingest extrahiert)
    valid_from:      date,
    version_label:   str | None = None,
    valid_until:     date | None = None,
    metadata:        dict | None = None,
    source_url:      str = "",
    lang:            str = "de",
    chunk_strategy:  Literal["paragraph", "sliding", "semantic", "code"] = "paragraph",
    actor:           str,                    # PFLICHT — Audit-Trail
) -> IngestJobAccepted:                      # job_id für rag_status-Polling
    ...

# ========================
# 3.2 rag_status — synchron, Polling
# ========================
async def rag_status(
    *,
    tenant_id: int,
    job_id:    str,
) -> JobStatus:  # PENDING | RUNNING | SUCCEEDED | FAILED | RETRY
    ...

# ========================
# 3.3 rag_search — synchron (Latenz ~200ms)
# ========================
async def rag_search(
    *,
    tenant_id:           int,
    query:               str,
    repo:                str | None = None,      # None = cross-repo
    collection:          str | None = None,
    top_k:               Annotated[int, Field(ge=1, le=50)] = 10,
    as_of:               datetime | None = None, # timestamptz; None = nur aktuell
    include_parents:     bool = True,
    rerank:              bool = False,           # BGE-Reranker opt-in
    max_response_tokens: int = 8000,             # Token-Budget für Response
    metadata_filter:     dict | None = None,     # JSONB-Filterausdruck
) -> SearchResponse:  # list[SearchResult] + query_metadata
    ...

# ========================
# 3.4 rag_supersede — async via Celery, idempotent
# ========================
async def rag_supersede(
    *,
    tenant_id:        int,
    idempotency_key:  str,
    repo:             str,
    collection:       str,
    document_key:     str,
    new_content:      str,
    new_version_label: str,
    new_valid_from:   date,
    revision_note:    str,
    actor:            str,
) -> SupersedeJobAccepted:
    ...

# ========================
# 3.5 rag_delete — soft-delete only
# ========================
async def rag_delete(
    *,
    tenant_id:              int,
    idempotency_key:        str,
    repo:                   str,
    collection:             str,
    document_key:           str,
    revision_no:            int | None = None,   # None = alle Revisionen
    confirm_all_revisions:  bool = False,         # PFLICHT wenn revision_no=None
    reason:                 Annotated[str, Field(min_length=10)],
    actor:                  str,
) -> DeleteResult:
    ...

# ========================
# 3.6 rag_history — synchron
# ========================
async def rag_history(
    *,
    tenant_id:    int,
    repo:         str,
    collection:   str,
    document_key: str,
) -> list[VersionEntry]:
    ...

# ========================
# 3.7 rag_sync — async via Celery
# ========================
async def rag_sync(
    *,
    tenant_id:          int,
    idempotency_key:    str,
    repo:               str,
    collection:         str,
    target_embed_model: str | None = None,
    force:              bool = False,
    actor:              str,
) -> SyncJobAccepted:
    ...

# ========================
# 3.8 rag_list — synchron
# ========================
async def rag_list(
    *,
    tenant_id: int,
    repo:      str | None = None,
) -> list[CollectionInfo]:
    ...
```

---

## 4. Pydantic-v2-Response-Models

```python
class SearchResult(BaseModel):
    chunk_public_id:  UUID
    document_key:     str
    revision_no:      int
    version_label:    str | None
    score:            float
    chunk_content:    str
    parent_content:   str | None
    valid_from:       date
    valid_until:      date | None
    chunk_metadata:   dict[str, Any]
    doc_metadata:     dict[str, Any]

class SearchResponse(BaseModel):
    results:          list[SearchResult]
    query_metadata:   dict[str, Any]     # {"elapsed_ms": 142, "reranked": false}

class IngestJobAccepted(BaseModel):
    job_id:           str
    idempotency_key:  str
    status:           Literal["ACCEPTED"]

class JobStatus(BaseModel):
    job_id:           str
    status:           Literal["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "RETRY"]
    detail:           str | None
    chunk_count:      int | None         # bei SUCCEEDED

class VersionEntry(BaseModel):
    id:               int
    public_id:        UUID
    revision_no:      int
    version_label:    str | None
    valid_from:       date
    valid_until:      date | None
    is_current:       bool
    revision_note:    str | None
    ingested_at:      datetime
    chunk_count:      int
```

---

## 5. Chunking-Strategien

### paragraph (Default — bayerische Gesetze)
```
Split-Regex: r'(?=\u00a7+\s*\d+|Art\.\s*\d+|Absatz\s*\d+|Abs\.\s*\d+|Anlage\s*\d+)'
→ behandelt: §, §§, Art., Abs., Anlage, Abschnitt
Parent-Chunk: vollständiger § (max. 800 Tokens)
Child-Chunks: einzelne Absätze (max. 200 Tokens)
Overlap: 0 (§-Grenzen = harte semantische Grenzen)
```

### sliding (Fließtexte, Berichte)
```
Chunk-Größe: 400 Tokens | Overlap: 80 Tokens
Parent-Chunk: 3× Child-Chunks (1200 Tokens)
```

### semantic (Markdown-Strukturdokumente, ADRs)
```
Split: Markdown-Headings (H1/H2/H3)
Parent: gesamter Abschnitt | Child: Unterabschnitte
```

### code (Source-Code, AST-basiert)
```
Split: Funktions-/Klassen-Definitionen (via AST)
Parent: gesamte Klasse | Child: einzelne Methoden
```

---

## 6. Auth, Credentials, Rate-Limiting

### 6.1 Authentifizierung (ADR-010)
```python
# mTLS zwischen MCP-Client und rag-mcp (authentik CA)
# Alternativ: API-Key via authentik Service Account

from iil_secrets import read_secret

db_password       = read_secret("rag_db_password")
embedder_api_key  = read_secret("embedder_api_key")  # falls Embedder-Service auth
```

### 6.2 Rate-Limiting (pro Tenant)
```python
# Konfigurierbar in rag_collections oder zentral in billing-hub
RAG_INGEST_DAILY_LIMIT_MB  = config("RAG_INGEST_DAILY_LIMIT_MB",  default=500)
RAG_SEARCH_RPM_LIMIT       = config("RAG_SEARCH_RPM_LIMIT",       default=120)
RAG_EMBED_TOKENS_DAILY     = config("RAG_EMBED_TOKENS_DAILY",     default=5_000_000)
```

---

## 7. Reranker-Service (separater Container)

```yaml
# docker-compose.prod.yml
embedder-service:
  image: ghcr.io/achimdehnert/rag-embedder-service:latest
  environment:
    - EMBED_MODEL=intfloat/multilingual-e5-large
    - RERANK_MODEL=BAAI/bge-reranker-v2-m3
    - GPU_ENABLED=false     # true auf GPU-Node
  ports:
    - "127.0.0.1:8765:8765"
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8765/health"]
```

- **Lazy-Loading**: Modelle werden beim ersten Request geladen, nicht beim Container-Start
- **Pre-Warming** optional: `PRELOAD_ON_START=true` für latenzktritische Deployments
- **GPU-Unabhängigkeit**: rag-mcp läuft auf CPU-Node, Embedder optional auf GPU-Node

---

## 8. OpenTelemetry Tracing

```python
from opentelemetry import trace

tracer = trace.get_tracer("rag-mcp")

@tracer.start_as_current_span("rag_search")
async def rag_search(...):
    with tracer.start_as_current_span("embed_query"):
        embedding = await embedder.embed(query)
    with tracer.start_as_current_span("db_hybrid_search"):
        results = await db.hybrid_search(...)
    if rerank:
        with tracer.start_as_current_span("reranker"):
            results = await reranker.rerank(query, results)
    return results

# Exportiert nach: Jaeger (lokal) / OTLP Collector (Prod)
# Latenz-Breakdown: embed_ms + db_ms + rerank_ms sichtbar
```

---

## 9. Implementierungs-Dateistruktur

```
mcp-hub/rag_mcp/
├── server.py              # FastMCP server, Auth-Middleware, OTel-Init
├── tools/                 # dünne Adapter (Validierung + Dispatch)
│   ├── ingest.py          # -> IngestService, Celery dispatch
│   ├── status.py          # -> JobStore
│   ├── search.py          # -> SearchService (sync)
│   ├── supersede.py       # -> SupersedeService, Celery dispatch
│   ├── delete.py          # -> DeleteService (soft-delete)
│   ├── history.py         # -> HistoryService
│   ├── sync.py            # -> SyncService, Celery dispatch
│   └── list.py            # -> ListService
├── services/              # Business-Logik (testbar ohne Tools)
│   ├── ingest.py
│   ├── search.py          # Hybrid Search + RRF
│   ├── supersede.py       # atomare Supersession-Transaktion
│   ├── delete.py
│   ├── history.py
│   ├── rate_limiter.py
│   └── idempotency.py
├── chunking/
│   ├── paragraph.py       # §/Art./Anlage-Split
│   ├── sliding.py
│   ├── semantic.py
│   └── code.py            # AST-basiert
├── models.py              # Pydantic v2 Input/Output Models
├── worker.py              # Celery Worker (acks_late=True)
├── db/
│   ├── connection.py      # psycopg[async], read_secret()
│   ├── schema.sql         # ADR-171 CREATE TABLE Statements
│   └── migrations/        # Alembic
└── embedder_client.py     # HTTP-Client für Embedder-Service
```

---

## 10. Deployment

```yaml
# systemd: rag-mcp.service (analog orchestrator-mcp)
# Docker Compose: eingebunden in mcp-hub/docker-compose.prod.yml
# Deploy: via ADR-075 ship-workflow.sh
# Port: 8766 (intern, nicht public)
# Secrets: read_secret("rag_db_password"), read_secret("embedder_api_key")
# OTel Exporter: OTLP via env OTEL_EXPORTER_OTLP_ENDPOINT
```

---

## 11. Betrachtete Alternativen

### Option A: LlamaIndex / LangChain
- ❌ Schwergewichtig, pgvector-Integration unterschiedlich gut
- ❌ MCP-Integration = zusätzlicher Wrapper
- **Abgelehnt**

### Option B: Extension der orchestrator-mcp
- ❌ agent_memory ≠ rag_documents (falsche Semantik)
- ❌ orchestrator-mcp zu groß
- **Abgelehnt**

### Option C: Outbox-Pattern statt Celery
- ✅ Crash-sicher (exactly-once)
- ❌ Komplexer (Outbox-Table, Relay-Worker, Migration)
- **Nicht gewählt in v1 — nachrüstbar wenn Celery-Reliability nicht ausreicht**

### Option D: Dedizierter rag-mcp (gewählt)
- ✅ Single Responsibility, eigenes Deployment
- ✅ Folgt MCP-Governance (ADR-010)
- ❌ Neuer Server (~1 Tag Setup)
- **Gewählt**

---

## 12. Konsequenzen

| + | Konsequenz |
|---|------------|
| + | Einheitliche RAG-API — kein Wildwuchs in Repos |
| + | DSGVO: tenant_id in jeder Operation erzwungen |
| + | Idempotency: sichere Retries bei Network-Glitches |
| + | Celery: Ingest blockiert keine MCP-Connection |
| + | Reranker-Service: entkoppeltes Modell-Hosting (GPU optional) |
| + | OTel: Latenz-Breakdown embed+db+rerank sichtbar |

| - | Trade-off | Mitigation |
|---|-----------|------------|
| - | Celery + Redis als neue Infrastruktur | Standard-Plattform (ADR-022) |
| - | Embedder-Service: zusätzlicher Container | Lazy-start, CPU-only default |
| - | idempotency_keys: zusätzliche Tabelle | Automatisches TTL-Cleanup |

---

## 13. Confirmation

| # | Check | Methode |
|---|-------|--------|
| 1 | Ingest-Roundtrip | Integration-Test: ingest §55 → rag_status(SUCCEEDED) → rag_search findet Treffer |
| 2 | Idempotency | Gleicher idempotency_key 2× → gleiche job_id, kein Duplikat |
| 3 | Supersession atomar | Concurrent supersede → kein doppeltes is_current=true |
| 4 | Soft-Delete | rag_delete → rag_search findet nicht mehr, rag_history zeigt noch |
| 5 | Auth | Request ohne Token → 401 |
| 6 | Rate-Limit | >RPM_LIMIT Requests/Minute → 429 |
| 7 | OTel | Jaeger zeigt Span rag_search mit embed_ms + db_ms |

---

## 14. Referenzen

- [ADR-171: Temporal RAG Infrastructure](./ADR-171-temporal-rag-infrastructure.md)
- [ADR-170: iil-ingest](./ADR-170-iil-ingest-document-ingestion-package.md)
- [ADR-010: MCP Tool Governance](./ADR-010-mcp-tool-governance.md)
- [ADR-022: Platform Standard](./ADR-022-platform-consistency-standard.md)
- FastMCP: https://github.com/jlowin/fastmcp
- multilingual-e5-large: https://huggingface.co/intfloat/multilingual-e5-large
- BGE-Reranker-v2-m3: https://huggingface.co/BAAI/bge-reranker-v2-m3
- OpenTelemetry Python: https://opentelemetry-python.readthedocs.io/
- Celery acks_late: https://docs.celeryq.dev/en/stable/userguide/tasks.html#Task.acks_late
