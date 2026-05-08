---
status: Proposed
date: 2026-05-07
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

# ADR-188: Unified Vector Store — Plattformweiter Dokumenten-VectorStore auf pgvector

| Metadaten | |
|-----------|---|
| **Status** | Proposed |
| **Datum** | 2026-05-07 |
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

| Aspekt | ADR-087 | ADR-171 | ADR-187 | **Konsolidierung (dieses ADR)** |
|--------|---------|---------|---------|------|
| **PK-Typ** | UUID | BigSerial (ADR-022 ✅) | BigSerial | **BigSerial** |
| **Embedding-Modell** | text-embedding-3-small (API) | multilingual-e5-large (lokal) | text-embedding-3-small (API) | **multilingual-e5-large** (Primär) |
| **Dimensionen** | 1536 | 1024 | 1536 | **1024** (Primär) + 1536 optional |
| **Temporal** | Nein | ✅ Ja (`valid_from/until`) | Nein | **✅ Ja** |
| **Versionierung** | Nein | ✅ Supersession Chain | Replace-Strategie | **✅ Supersession** |
| **Hybrid Search** | ✅ RRF | ✅ RRF | Nein | **✅ RRF** |
| **Chunking** | Extern | paragraph/sliding/semantic/code | Extern | **4 Strategien** |
| **FTS-Sprache** | `german` | `german` | Nein | **`german`** (+ `simple` Fallback) |
| **Soft-Delete** | Nein | ✅ `deleted_at` + DELETE-Trigger | DELETE+INSERT | **✅ Soft-Delete** |
| **Tenant-Isolation** | Row-Level (UUID) | Row-Level (bigint) | Row-Level (UUID) | **Row-Level (bigint)** |
| **API-Layer** | Django SearchService | rag-mcp (MCP) | Django direkt | **rag-mcp** |
| **DB-Location** | content_store DB | mcp_hub_db | mcp_hub_db | **mcp_hub_db** |

---

## 2. Entscheidung

### E1: Ein Schema — ADR-171 als Single Source of Truth

Das **ADR-171-Schema** (`rag_collections` / `rag_documents` / `rag_chunks`) wird zum **einzigen Vector-Store-Schema** der gesamten Plattform.

**Begründung:**
- BigAutoField-konform (ADR-022)
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

**Entscheidung:** `multilingual-e5-large` (1024 Dimensionen) als **Primärmodell**. OpenAI als **optionaler Fallback** (wenn lokaler Embedder-Service nicht verfügbar).

**DSGVO-Vorteil:** Für meiki-hub (personenbezogene Fallakten) und risk-hub (Gefahrstoff-Betriebsgeheimnisse) ist lokales Embedding Pflicht.

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
# projects/models.py — Erweiterung
class ProjectDocumentLink(models.Model):
    """Verknüpft Bibliotheks-Dokument mit Projekt (M:N)."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="library_links")
    collection = models.CharField(max_length=100)  # "risk:bibliothek"
    document_key = models.CharField(max_length=500)  # stabile ID im VectorStore
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

**RAG-Kontext für AI-Prefill:**
```python
# projects/rag_service.py
class ProjectRAGService:
    @staticmethod
    async def get_context_for_section(project, section, top_k=5):
        """Sucht relevante Chunks aus Bibliothek + Projekt-Docs."""
        # 1. Bibliotheks-Collections des Projekts
        collections = project.library_links.values_list("collection", flat=True).distinct()
        # 2. rag_search über alle verknüpften Collections
        results = await rag_mcp.rag_search(
            tenant_id=project.tenant_id,
            query=f"{section.title} {section.ai_context_hint}",
            collection=list(collections),
            top_k=top_k,
        )
        return "\n---\n".join(r.chunk_content for r in results.results)
```

---

## 3. Migration bestehender ADRs

| ADR | Aktion | Timeline |
|-----|--------|----------|
| **ADR-087** | Status → `Superseded by ADR-188`. `search_chunks`-Schema wird durch `rag_chunks` ersetzt. `platform-search` Package → Thin Client für rag-mcp. | Phase 2 |
| **ADR-113** | Bleibt für Agent Memory (`agent_memory_entries`). Separate Tabelle, separater Zweck. | Keine Änderung |
| **ADR-171** | Bleibt unverändert — wird zum Single Schema. | Phase 1 |
| **ADR-172** | Bleibt unverändert — wird zur Single API. | Phase 1 |
| **ADR-187 §E3** | VectorStore-Schema wird gestrichen. `iil-ingest[vectorstore]` schreibt via rag-mcp statt direkt in DB. | Phase 2 |

---

## 4. Betrachtete Alternativen

### Option A: Drei Schemata beibehalten
- ❌ Wildwuchs, jedes Repo entscheidet selbst
- ❌ Unterschiedliche Embedding-Modelle → Cross-Repo-Search unmöglich
- **Abgelehnt**

### Option B: ADR-087 als Basis, Temporal nachrüsten
- ⚠️ UUID-PKs widersprechen ADR-022
- ⚠️ Kein Supersession-Konzept, nachträgliche Migration teuer
- **Abgelehnt**

### Option C: ADR-171 als Basis + Konsolidierung (gewählt)
- ✅ BigAutoField-konform
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

## 5. Implementierungsphasen

| Phase | Aufgabe | Verantwortlich | Abhängigkeit |
|-------|---------|---------------|-------------|
| **0** | ADR-188 akzeptieren, ADR-087/187 markieren | Achim | — |
| **1** | ADR-171 Schema deployen (mcp_hub_db) | Platform | pgvector Extension |
| **1** | ADR-172 rag-mcp implementieren (MVP: ingest + search) | Platform | Phase 1 Schema |
| **1** | Embedder-Service deployen (multilingual-e5-large) | Platform | Docker |
| **2** | meiki-hub Pilot: BayBO + BayArchivG (ADR-006) | meiki-hub | Phase 1 |
| **2** | risk-hub: SDS + Bibliothek via rag-mcp | risk-hub | Phase 1 |
| **2** | bfagent/weltenhub: Migration search_chunks → rag_chunks | bfagent | Phase 1 |
| **3** | iil-ingest[vectorstore]: ChunkWriter via rag-mcp | Package | Phase 1 |
| **3** | risk-hub: ProjectDocumentLink + RAG-Prefill | risk-hub | Phase 2 |
| **4** | Reranker-Service (BGE-Reranker-v2-m3) | Platform | Phase 2 |
| **4** | Cross-Repo-Search (z.B. platform ADRs + risk-hub Normen) | Platform | Phase 2 |

---

## 6. Konsequenzen

### Positiv

| + | Konsequenz |
|---|------------|
| + | **Ein Schema** — kein Wildwuchs, keine Entscheidung pro Repo |
| + | **Ein Embedding-Modell** — Cross-Repo-Search möglich |
| + | **DSGVO** — lokales Embedding, tenant_id auf jeder Row |
| + | **Temporal** — meiki-hub Gesetze + risk-hub SDS-Versionen |
| + | **Immutabilität** — DELETE-Trigger für Compliance |
| + | **Kosten** — kein OpenAI-API-Verbrauch für Embeddings |
| + | **Offline** — funktioniert ohne Internet (lokal, Hetzner) |

### Trade-offs

| - | Trade-off | Mitigation |
|---|-----------|------------|
| - | Embedder-Service = neuer Container (~1.5 GB RAM) | Lazy-Loading, CPU-only default |
| - | ADR-087 Consumers müssen migrieren | Thin-Wrapper bleibt, Backend wechselt |
| - | Komplexeres Schema als einfache `search_chunks` | Komplexität wird durch rag-mcp abstrahiert |
| - | multilingual-e5-large langsamer als API | Batch-Ingest via Celery, nicht Request-kritisch |

---

## 7. Confirmation

| # | Check | Methode |
|---|-------|--------|
| 1 | ADR-171 Schema deployed | `\d rag_chunks` in mcp_hub_db |
| 2 | rag-mcp erreichbar | `rag_list(tenant_id=1)` → leere Liste |
| 3 | Ingest-Roundtrip | `rag_ingest` BayBO §55 → `rag_search` findet Treffer |
| 4 | meiki-hub Pilot | 50-Fragen-Goldstandard Recall@5 ≥ 0.85 |
| 5 | risk-hub Bibliothek | Dokument verknüpft → RAG-Prefill nutzt Chunks |
| 6 | Cross-Repo | `rag_search(repo=None)` findet Treffer aus 2+ Repos |
| 7 | ADR-087 superseded | `search_chunks` Tabelle nicht mehr genutzt |

---

## 8. Referenzen

- [ADR-087: Hybrid Search Architecture](./ADR-087-hybrid-search-architecture.md) — superseded
- [ADR-113: pgvector Agent Memory Store](./ADR-113-telegram-gateway-pgvector-memory.md) — bleibt
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
