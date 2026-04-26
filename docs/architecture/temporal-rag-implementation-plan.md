# Temporal RAG — Implementierungsplan (Phase 3–6 des Reviews)

| Metadaten | |
|-----------|---|
| **Bezug** | ADR-171 v1.1, ADR-172 v1.1, ADR-006 v1.1 |
| **Stand** | 2026-04-26 |
| **Review-Phase** | 3/6: Implementierungsplan + Dateistruktur |
| **Status** | Draft |

---

## Phase 3: Implementierungsplan + Dateistruktur

### 3.1 Vollständige Dateistruktur: mcp-hub/rag_mcp/

```
mcp-hub/
├── rag_mcp/
│   ├── __init__.py
│   ├── server.py                  # FastMCP, Auth-Middleware, OTel-Init
│   ├── models.py                  # Pydantic v2: alle Input/Output-Models
│   ├── config.py                  # decouple.config() + read_secret()
│   ├── worker.py                  # Celery App (acks_late=True, result_backend=redis)
│   ├── tools/                     # Dünne MCP-Adapter (Validierung + Dispatch)
│   │   ├── __init__.py
│   │   ├── ingest.py              # @mcp.tool() rag_ingest
│   │   ├── status.py              # @mcp.tool() rag_status
│   │   ├── search.py              # @mcp.tool() rag_search
│   │   ├── supersede.py           # @mcp.tool() rag_supersede
│   │   ├── delete.py              # @mcp.tool() rag_delete
│   │   ├── history.py             # @mcp.tool() rag_history
│   │   ├── sync.py                # @mcp.tool() rag_sync
│   │   └── list.py                # @mcp.tool() rag_list
│   ├── services/                  # Business-Logik (testbar ohne MCP-Stack)
│   │   ├── __init__.py
│   │   ├── ingest_service.py      # Chunking-Dispatch, DB-Insert, Celery-Task
│   │   ├── search_service.py      # Hybrid Search + echtes RRF
│   │   ├── supersede_service.py   # Atomare Supersession-Transaktion
│   │   ├── delete_service.py      # Soft-Delete + Audit
│   │   ├── history_service.py
│   │   ├── sync_service.py
│   │   ├── idempotency_service.py # idempotency_key lookup + insert
│   │   └── rate_limiter.py        # Pro-Tenant Quota (RPM, Tokens, MB)
│   ├── chunking/
│   │   ├── __init__.py
│   │   ├── base.py                # ChunkerProtocol(content, lang) -> list[Chunk]
│   │   ├── paragraph.py           # §/Art./Abs./Anlage-Split (Regex erw.)
│   │   ├── sliding.py             # 400 Tokens, 20% Overlap
│   │   ├── semantic.py            # Markdown Heading-Split
│   │   └── code.py                # AST-basiert (ast.parse)
│   ├── embedding/
│   │   ├── __init__.py
│   │   ├── base.py                # EmbedderProtocol
│   │   └── client.py              # HTTP-Client -> embedder-service /embed
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py          # psycopg[async], read_secret()
│   │   ├── schema.sql             # CREATE TABLE (ADR-171 v1.1)
│   │   ├── queries/
│   │   │   ├── search.sql         # Hybrid RRF Query
│   │   │   ├── history.sql
│   │   │   └── supersede.sql      # UPDATE + INSERT in einer TX
│   │   └── migrations/            # Alembic
│   │       ├── env.py
│   │       └── versions/
│   │           └──  001_initial_rag_schema.py
│   └── tracing.py                 # OTel Tracer init
├── embedder_service/              # Separater Container (multilingual-e5-large)
│   ├── main.py                    # FastAPI: POST /embed, POST /rerank, GET /health
│   ├── models.py                  # e5-large + BGE-Reranker (lazy load)
│   └── Dockerfile
├── tests/
│   ├── rag_mcp/
│   │   ├── unit/
│   │   │   ├── test_chunking.py   # paragraph, sliding, semantic, code
│   │   │   ├── test_rrf.py        # RRF-Formel korrekt
│   │   │   ├── test_idempotency.py
│   │   │   └── test_rate_limiter.py
│   │   ├── integration/
│   │   │   ├── test_ingest_search.py  # Roundtrip-Test
│   │   │   ├── test_supersession.py   # Temporal Correctness
│   │   │   ├── test_soft_delete.py
│   │   │   └── test_concurrent.py     # Concurrent Supersede → UNIQUE-Verletzung
│   │   └── e2e/
│   │       └── test_meiki_pilot.py    # as_of=2022 → BayBO Fassung 2020
│   └── conftest.py                # pytest-fixtures: test-pgvector, mock-embedder
└── docker-compose.prod.yml       # rag-mcp + embedder-service + Redis (Celery)
```

---

## Phase 4: Test-Strategie (Test-Pyramide)

### 4.1 Test-Pyramide

```
              E2E (2 Tests)
           ▲ meiki_pilot: as_of correctness
          ▲▲▲ Smoke: rag-mcp health
        Integration (6 Tests)
      ▲ ingest_search_roundtrip
      ▲ supersession_atomic
      ▲ soft_delete
      ▲ concurrent_supersede
      ▲ idempotency_key_dedup
      ▲ rate_limit_exceeded
    Unit (12+ Tests)
  ▲ paragraph_chunker (BayBO, GemO, AVOs)
  ▲ sliding_chunker (overlap korrekt)
  ▲ rrf_formula (Cormack k=60)
  ▲ idempotency_service
  ▲ rate_limiter_quota
  ▲ soft_delete_semantik
```

### 4.2 Kritische Test-Cases

```python
# test_supersession.py
async def test_temporal_correctness(db, embedder_mock):
    """Kern-Test: as_of-Query gibt historisch korrekte Version zurück."""
    # BayBO §55 Fassung 2020 (valid_from=2020-01-01)
    await ingest_v1(valid_from=date(2020, 1, 1))
    # BayBO §55 Fassung 2024 (superseded v1)
    await supersede(new_valid_from=date(2024, 1, 1))

    # Stichtag 2022: muss v1 zurückgeben
    r_2022 = await search(as_of=datetime(2022, 6, 1, tzinfo=utc))
    assert r_2022[0].revision_no == 1
    assert r_2022[0].version_label == "Fassung 2020"

    # Heute: muss v2 zurückgeben
    r_now = await search(as_of=None)
    assert r_now[0].revision_no == 2
    assert r_now[0].version_label == "Fassung 2024"

# test_concurrent.py
async def test_concurrent_supersede_prevents_double_current(db):
    """UNIQUE Partial Index muss doppeltes is_current=true verhindern."""
    task1 = asyncio.create_task(supersede(new_valid_from=date(2025, 1, 1)))
    task2 = asyncio.create_task(supersede(new_valid_from=date(2025, 6, 1)))
    results = await asyncio.gather(task1, task2, return_exceptions=True)
    # Genau einer muss Erfolg, einer UniqueViolation haben
    successes = [r for r in results if not isinstance(r, Exception)]
    assert len(successes) == 1
```

### 4.3 Coverage-Ziel

| Schicht | Ziel |
|---------|------|
| Unit | ≥90% |
| Integration | ≥80% |
| E2E | Alle Confirmation-Checks aus ADR-171/172 |

---

## Phase 5: Benchmark-Plan (halfvec vs. vector)

### 5.1 Ablauf

```
Schritt 1: 100k Chunks ingestieren (BayBO + BayDSG + DSGVO vollständig)
Schritt 2: Recall@10 messen
           → 50 Gold-Queries (bayerische Rechtsfragen + historische as_of-Queries)
           → Manuell bewertet: "Ist das erwartete Gesetz in Top-10?"
Schritt 3: Storage messen
           SELECT pg_size_pretty(pg_total_relation_size('rag_chunks'));
Schritt 4: Migration zu halfvec(1024)
           ALTER TABLE rag_chunks ALTER COLUMN embedding TYPE halfvec(1024);
           DROP INDEX rag_chunks_embedding_hnsw_idx;
           CREATE INDEX rag_chunks_embedding_hnsw_idx
               ON rag_chunks USING hnsw (embedding halfvec_cosine_ops)
               WITH (m=16, ef_construction=64);
Schritt 5: Recall@10 erneut messen (gleiche 50 Gold-Queries)
Schritt 6: Entscheidungsmatrix
```

### 5.2 Entscheidungsmatrix

| Szenario | Recall-Diff | Storage-Diff | Entscheidung |
|----------|------------|-------------|---------------|
| halfvec ≥ vector Recall | beliebig | ≥30% gespart | `halfvec` — ADR-Amendment |
| halfvec < vector -2% | ≤2% Verlust | beliebig | `vector` behalten |
| halfvec < vector >2% | >2% Verlust | beliebig | `vector` behalten |

---

## Phase 6: Rollout-Sequenz

```
┌────────────────────────────────────────────────────────┐
│  Woche 1-2: Infrastructure                              │
│  ✔ ADR-171 Schema deployen (pgvector auf Prod)          │
│  ✔ embedder-service (multilingual-e5-large, CPU)        │
│  ✔ rag-mcp Server deployen (mcp-hub)                   │
│  ✔ Redis (Celery Backend)                              │
└────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────┐
│  Woche 3-4: Pilot meiki-hub (ADR-006)                   │
│  ✔ BayBO + BayDSG + DSGVO + KI-VO ingestieren          │
│  ✔ as_of-Tests bestanden                               │
│  ✔ Supersession-Workflow getestet                      │
│  ✔ Benchmark Phase 5 durchgeführt                     │
└────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────┐
│  Woche 5-6: risk-hub (SDS Collection)                   │
│  ✔ SDS-PDFs via iil-ingest + rag_ingest                │
│  ✔ Supersession analog ADR-161 Workflow                │
└────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────┐
│  Woche 7+: platform ADRs + bfagent Prompts              │
└────────────────────────────────────────────────────────┘
```

---

## Offene Fragen + nächste ADRs

| # | Frage | Antwort-Format |
|---|-------|----------------|
| OQ-1 | LLM-Rechtsauskunft (Generation) nach RAG? | ADR-007 (meiki-hub) |
| OQ-2 | Feedback-Radar (HITL-Korrekturen für Classifier)? | ADR-007 oder eigenständig |
| OQ-3 | KI-VO Hochrisiko-KI: Audit-Log-Schema ausreichend? | Prüfung durch Legal |
| OQ-4 | Bayern-Recht-Online Crawler: rechtlich zulässig? | Klärung mit BY-Justizministerium |
| OQ-5 | halfvec Entscheidung | Phase 5 Benchmark |
| OQ-6 | Partitioning bei >1M Chunks | Monitoring-Alert |
