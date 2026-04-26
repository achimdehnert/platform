---
status: Proposed
date: 2026-04-26
decision-makers:
  - Achim Dehnert
depends-on:
  - ADR-171 (Temporal RAG Infrastructure — Schema)
  - ADR-170 (iil-ingest — Text-Extraktion)
  - ADR-113 (pgvector — bestehende Infrastruktur)
  - ADR-010 (MCP Tool Governance)
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
| **Autor** | Achim Dehnert |
| **Reviewer** | — |
| **Depends On** | ADR-171 (Schema), ADR-170 (iil-ingest), ADR-010 (MCP Governance) |
| **Consumers** | meiki-hub (ADR-006), risk-hub, platform, bfagent |

### Änderungshistorie

| Version | Datum | Änderung |
|---------|-------|----------|
| 1.0 | 2026-04-26 | Initiale Version |

---

## Executive Summary

ADR-171 definiert das Datenbankschema für Temporal RAG. Dieses ADR definiert den
**MCP-Server** (`rag-mcp`), der die RAG-Operationen als standardisierte MCP-Tools
exponiert. Alle Repos konsumieren ausschließlich diese API — kein direkter DB-Zugriff.

Kernentscheidungen:
1. Neuer MCP-Server `rag-mcp` im `mcp-hub`-Repository
2. **iil-ingest** (ADR-170) als Text-Extraktions-Backend
3. **Paragraph-basiertes Chunking** für juristische Texte (§-Boundaries)
4. **Parent-Document Retrieval** Pattern für Kontext-Vollständigkeit
5. **Optionales Reranking** via BGE-Reranker-v2
6. **Soft-Delete-only Policy** (Compliance mit Archivgesetzen)

---

## 1. Kontext und Problemstellung

Ohne zentralisierte API würde jeder Consumer:
- Direkt SQL gegen pgvector schreiben (kein Governance)
- Eigene Chunking-Logik implementieren (Qualitätsdivergenz)
- Eigene Embedding-Calls verwalten (Kostenkontrolle unklar)
- Supersession-Transaktionen selbst implementieren (Fehlerrisiko)

`rag-mcp` ist die single API surface für alle RAG-Operationen —
analog wie `orchestrator-mcp` die single API für Agent-Memory ist.

---

## 2. API-Design (MCP Tools)

### 2.1 rag_ingest

```python
rag_ingest(
  repo:           str,          # "meiki-hub"
  collection:     str,          # "gesetze"
  document_id:    str,          # "BayBO-§55-Abs1" (stabile externe ID)
  content:        str,          # Volltext (bereits extrahiert via iil-ingest)
  valid_from:     date,         # Inkrafttreten / Ausgabedatum
  version:        str | None,   # "Fassung 2024-01-01" / "v2.1"
  valid_until:    date | None,  # None = aktuell gültig
  metadata:       dict | None,  # {"gesetz": "BayBO", "paragraph": "§55", ...}
  source_url:     str | None,
  chunk_strategy: str = "paragraph"  # paragraph | sliding | semantic
) -> IngestResult
# IngestResult: {chunk_count, document_id, version, valid_from}
```

### 2.2 rag_search

```python
rag_search(
  query:          str,          # Natürlichsprachliche Suchanfrage
  repo:           str | None,   # None = cross-repo-Search
  collection:     str | None,   # None = alle Collections des Repos
  top_k:          int = 10,
  as_of_date:     date | None,  # None = nur aktuell gültige Dokumente
  include_parents: bool = True, # Parent-Chunk als Kontext zurückgeben
  rerank:         bool = False  # BGE-Reranker aktivieren (langsamer, präziser)
) -> list[SearchResult]
# SearchResult: {document_id, version, valid_from, valid_until,
#                chunk_content, parent_content, score, metadata}
```

### 2.3 rag_supersede

```python
rag_supersede(
  repo:           str,
  document_id:    str,          # ID der zu ersetzenden Version
  new_content:    str,          # Inhalt der neuen Version
  new_version:    str,
  new_valid_from: date,         # setzt valid_until der alten = new_valid_from - 1 Tag
  revision_note:  str | None    # "§5 Abs.2 geändert durch VO 2024/12"
) -> SupersedeResult
# Atomar: UPDATE old + INSERT new in einer Transaktion
# SupersedeResult: {old_id, new_id, old_valid_until, new_valid_from}
```

### 2.4 rag_history

```python
rag_history(
  repo:        str,
  document_id: str
) -> list[VersionEntry]
# VersionEntry: {id, version, valid_from, valid_until, is_current,
#                revision_note, ingested_at, chunk_count}
# Sortiert: valid_from ASC
```

### 2.5 rag_delete

```python
rag_delete(
  repo:        str,
  document_id: str,
  version:     str | None = None,  # None = alle Versionen
  reason:      str                  # PFLICHT — wird in revision_note gespeichert
) -> DeleteResult
# Implementierung: NUR SOFT-DELETE
# → SET is_current = false, revision_note = "FEHLER: " + reason
# → KEIN physisches DELETE (Archivgesetz-Compliance)
# DeleteResult: {affected_chunks, document_id}
```

### 2.6 rag_sync

```python
rag_sync(
  repo:       str,
  collection: str,
  force:      bool = False  # Re-embed auch wenn content_hash unverändert
) -> SyncResult
# Re-Ingest aller Dokumente einer Collection (z.B. nach Embedding-Modell-Update)
# SyncResult: {synced, skipped, errors}
```

### 2.7 rag_list

```python
rag_list(
  repo:       str | None = None
) -> list[CollectionInfo]
# CollectionInfo: {repo, collection, doc_count, chunk_count,
#                  latest_ingest, embed_model, description}
```

---

## 3. Chunking-Strategien

### 3.1 paragraph (Default für juristische Texte)

```
Gesetz → Split bei: §, Abs., Nr., Satz (Regex: r'(?=§\s*\d+|Absatz\s*\d+|Abs\.\s*\d+)')
Parent-Chunk: vollständiger § (bis 800 Tokens)
Child-Chunks: einzelne Absätze (bis 200 Tokens)
Overlap: 0 (§-Grenzen sind harte semantische Grenzen)
```

### 3.2 sliding (für Fließtexte, Berichte)

```
Chunk-Größe: 400 Tokens
Overlap: 80 Tokens (20%)
Parent-Chunk: 3× Child-Chunks (1200 Tokens)
```

### 3.3 semantic (für Code, strukturierte Docs)

```
Split bei: Funktionsdefinitionen, Klassen, Markdown-Headings
Parent-Chunk: gesamte Klasse / gesamter Abschnitt
Child-Chunks: einzelne Methoden / Unterabschnitte
```

---

## 4. Parent-Document Retrieval Pattern

```
Ingest:
  §55 BayBO (Parent, 600 Tokens) → embedding gespeichert, parent_id=NULL
  §55 Abs.1 (Child, 150 Tokens)  → embedding gespeichert, parent_id=parent_uuid
  §55 Abs.2 (Child, 180 Tokens)  → embedding gespeichert, parent_id=parent_uuid

Search:
  1. Similarity Search gegen Child-Embeddings (präzises Matching)
  2. Für jeden Child-Match: Parent-Content laden
  3. LLM bekommt Parent-Content als Kontext (vollständiger §55)
```

Vorteil: Kleine Chunks → präziseres Vector-Matching.
Parent-Kontext → vollständiger Rechtstext für LLM.

---

## 5. Optionales Reranking (BGE-Reranker-v2)

Für high-precision Queries (Rechtsgutachten, Compliance-Checks):

```
rag_search(query, top_k=20, rerank=True)
  → Vector+BM25 → Top-20 Kandidaten
  → BGE-Reranker-v2-m3 (Cross-Encoder) → Re-scored
  → Top-10 (präziser als Bi-Encoder allein)
```

Default: `rerank=False` (Latenz-sensitiv). Nur für Offline-/Batch-Queries empfohlen.

---

## 6. Implementierung: mcp-hub Integration

```
mcp-hub/
├── rag_mcp/
│   ├── __init__.py
│   ├── server.py          # FastMCP server definition
│   ├── tools/
│   │   ├── ingest.py      # rag_ingest
│   │   ├── search.py      # rag_search (Hybrid + RRF)
│   │   ├── supersede.py   # rag_supersede (atomar)
│   │   ├── history.py     # rag_history
│   │   ├── delete.py      # rag_delete (soft-delete only)
│   │   ├── sync.py        # rag_sync
│   │   └── list.py        # rag_list
│   ├── chunking/
│   │   ├── paragraph.py   # §-basiertes Splitting
│   │   ├── sliding.py     # Sliding Window
│   │   └── semantic.py    # Struktur-basiertes Splitting
│   ├── embedding/
│   │   ├── base.py        # EmbedderProtocol
│   │   ├── e5.py          # multilingual-e5-large (sentence-transformers)
│   │   └── openai.py      # text-embedding-3-small (optional)
│   ├── reranking/
│   │   └── bge.py         # BGE-Reranker-v2-m3 (optional)
│   └── db/
│       ├── schema.sql     # CREATE TABLE statements (ADR-171)
│       └── migrations/    # Alembic oder plain SQL
```

---

## 7. Delete-Policy

> **Physisches DELETE ist verboten.** Keine Ausnahme.

| Aktion | Implementierung | Erlaubt für |
|--------|----------------|-------------|
| Dokument veraltet | `rag_supersede()` | alle |
| Fehlimport rückgängig | `rag_delete(reason=...)` → soft-delete | alle |
| Physisches DELETE | Nicht implementiert | niemand |
| Physisches DELETE (Emergency) | Nur DB-Admin direkt + ADR-Amendment | Platform-Admin |

Begründung: GefStoffV §14 (40 Jahre CMR), BayArchivG Art. 3, Audit-Trail-Pflicht.

---

## 8. Betrachtete Alternativen

### Option A: LlamaIndex / LangChain als RAG-Framework
- ✅ Reichhaltige Abstraktion (VectorStoreIndex, TemporalDocument)
- ❌ Schwergewichtig (500+ Deps), eigene pgvector-Integration unterschiedlich gut
- ❌ Versionierung nicht nativ — eigene Implementierung ohnehin nötig
- ❌ MCP-Integration erfordert Wrapper-Layer
- **Abgelehnt** — Eigenimplementierung mit pgvector direkter und kontrollierbarer

### Option B: Extension der orchestrator-mcp
- ✅ Kein neuer MCP-Server
- ❌ orchestrator-mcp ist für Agent-Koordination, nicht für Dokument-RAG
- ❌ Semantische Vermischung — agent_memory ≠ rag_documents
- ❌ orchestrator-mcp würde zu groß und schlecht wartbar
- **Abgelehnt**

### Option C: Dedizierter rag-mcp (gewählt)
- ✅ Klare Verantwortung (Single Responsibility)
- ✅ Eigenständig deploybar, testbar, upgradable
- ✅ Folgt MCP-Governance (ADR-010)
- ❌ Neuer Server — einmalige Setup-Kosten (~1 Tag)
- **Gewählt**

---

## 9. Konsequenzen

### 9.1 Positiv

| # | Konsequenz |
|---|------------|
| + | Einheitliche RAG-API für alle Repos — kein Wildwuchs |
| + | Chunking-Qualität zentral gesteuert (§-Splitting für Gesetze) |
| + | iil-ingest (ADR-170) als wiederverwendeter Extraktions-Layer |
| + | Soft-Delete garantiert Compliance ohne Produktivitätsverlust |
| + | Reranking als opt-in für Präzisions-Queries |

### 9.2 Trade-offs

| # | Trade-off | Mitigation |
|---|-----------|------------|
| - | multilingual-e5-large: ~560MB Modell-Download | Einmalig; danach gecacht |
| - | Batch-Embedding langsam ohne GPU | Background-Job via Queue |
| - | Neuer MCP-Server: zusätzlicher Port + systemd Service | Standard-Muster in mcp-hub |

---

## 10. Confirmation

| # | Check | Methode |
|---|-------|--------|
| 1 | `rag_ingest` + `rag_search` Roundtrip | Integration-Test: ingest §55, search "Baugenehmigung" → §55 in Top-3 |
| 2 | Supersession atomar | Concurrent-Test: kein doppeltes `is_current=true` |
| 3 | as_of_date korrekt | Test: `as_of_date=2023-06-01` → v1, `as_of_date=today` → v2 |
| 4 | Soft-Delete | Test: `rag_delete` setzt `is_current=false`, `rag_search` findet Dokument nicht mehr |
| 5 | Hybrid Search überlegen | Benchmark: §-Referenz-Query, Hybrid ≥ 20% besserer Recall vs. pure Vector |
| 6 | BGE-Reranker verbessert Precision | A/B-Test: rerank=True vs False auf 50 Gold-Queries |

---

## 11. Referenzen

- [ADR-171: Temporal RAG Infrastructure](./ADR-171-temporal-rag-infrastructure.md)
- [ADR-170: iil-ingest](./ADR-170-iil-ingest-document-ingestion-package.md)
- [ADR-010: MCP Tool Governance](./ADR-010-mcp-tool-governance.md)
- FastMCP: https://github.com/jlowin/fastmcp
- sentence-transformers multilingual-e5-large: https://huggingface.co/intfloat/multilingual-e5-large
- BGE-Reranker-v2-m3: https://huggingface.co/BAAI/bge-reranker-v2-m3
- Parent Document Retrieval (LangChain Docs): https://python.langchain.com/docs/how_to/parent_document_retriever/
- RRF (Reciprocal Rank Fusion): Cormack et al., 2009
