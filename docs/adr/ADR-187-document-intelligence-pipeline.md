---
status: accepted
date: 2026-05-07
amended: 2026-05-07
deciders: [Achim Dehnert]
consulted: [AI Engineering Squad]
informed: [Repo-Owner risk-hub, meiki-hub, coach-hub]
implementation_status: partial
implementation_evidence: "Phase 1 in risk-hub: pdfplumber Tabellenerkennung + Section Import-Modi (risk-hub ADR-046)."
---

# ADR-187: Document Intelligence Pipeline — Plattformweite Dokument-Analyse für Templates, RAG & VectorStore

- **Betroffene Repos:** Alle (risk-hub, meiki-hub, coach-hub, travel-beat, weltenhub, dms-hub, etc.)
- **Betroffene Packages:** `iil-ingest` (bestehend, ADR-170), `iil-concept-templates` (bestehend)
- **Abhängigkeiten:** ADR-170 (iil-ingest Package), ADR-009 (Platform Architecture), ADR-022 (Platform Consistency), ADR-027 (Shared Backend Services), ADR-079 (Temporal Workflow Engine)
- **Erweitert:** ADR-170 um VectorStore-Chunks, Multi-Tool Ensemble (camelot, Tiered OCR) und RAG-Vorbereitung
- **Siehe auch:** risk-hub ADR-046 (Phase 1 Implementierung)

## Kontext

Mehrere Plattform-Repos benötigen die Fähigkeit, aus PDF- und Office-Dokumenten strukturierte Daten zu extrahieren:

| Repo | Content-Typ | Ziel |
|------|-------------|------|
| **risk-hub** | Ex-Schutzdokumente, GBU, SDS | Template-Erstellung, KI-Dokumentgenerierung |
| **meiki-hub** | Wissensartikel, Anleitungen | Semantische Suche, RAG-Kontext |
| **coach-hub** | Coaching-Materialien, Übungen | Personalisierte Empfehlungen |
| **travel-beat** | Reisebeschreibungen, Guides | Content-Generierung |
| **weltenhub** | Weltenbau-Dokumente, Lore | Story-Konsistenz via RAG |

### Ist-Zustand

- **`iil-ingest`** (v0.1.0, ADR-170) existiert bereits auf PyPI mit PDF-Extraktion + Classifier (dms-hub Consumer)
- **risk-hub** hat eine zusätzliche lokale Implementierung in `doc_template_views.py` (pdfplumber + Section-Detection + Template-Struktur)
- **`iil-concept-templates`** (0.5.0) bietet text-basierte Strukturerkennung, aber keine echte Tabellenerkennung
- **Kein plattformweiter VectorStore** für Dokument-Chunks — pgvector ist nur für Agent-Memory (mcp-hub)
- `iil-ingest` hat aktuell nur Tier-1 (pdfminer/pdfplumber) — keine borderless-Tabellen, kein OCR-Fallback, keine Chunk-Pipeline

### Probleme

1. **iil-ingest hat keinen VectorStore-Output** — extrahiert Text + Metadaten, aber keine Chunk-Pipeline für RAG
2. **Einzeltool-Limitierung** — pdfplumber allein erkennt keine borderless-Tabellen und versagt bei gescannten PDFs
3. **risk-hub Logik nicht wiederverwendbar** — Template-Strukturerkennung (Sections, Tabellen-Mapping) ist lokal in Views, nicht im Package
4. **Keine Metadaten-Anreicherung** — extrahierte Sections wissen nicht, aus welchem Dokument/Seite/Kontext sie stammen

## Considered Options

### Option A: iil-ingest unverändert lassen + risk-hub lokal weiterentwickeln

- **Pro:** Kein Package-Aufwand, schnelle Iteration in risk-hub
- **Contra:** Keine Wiederverwendung, kein VectorStore, andere Repos haben nichts

### Option B: iil-ingest erweitern um Multi-Tool Ensemble + VectorStore-Chunks

Tiered Extraction mit mehreren spezialisierten Tools:

```
Tier 1: pdfplumber (schnell, Rahmen-Tabellen)
  ↓ Falls borderless-Tabellen vermutet
Tier 2: camelot Stream-Modus (borderless-Tabellen)
  ↓ Falls gescanntes PDF (kein Text extrahiert)
Tier 3: PyMuPDF + OCR (Tesseract)
```

- **Pro:** Beste Erkennungsqualität, plattformweit wiederverwendbar, VectorStore-ready, baut auf bestehendem Package auf
- **Contra:** Mehr Dependencies, höhere Komplexität, OpenCV für camelot nötig

### Option C: ML-basiert (marker-pdf / docling) als eigenständiges Package

- **Pro:** State-of-the-art Erkennung, Layout-Verständnis
- **Contra:** GPU-Abhängigkeit für Performance, große Model-Downloads, Overkill für strukturierte PDFs

### Option D: Neues Package `iil-ingestfw` parallel zu iil-ingest

- **Pro:** Kein Breaking Change an bestehendem Package
- **Contra:** Verwirrung durch zwei ähnliche Packages, DRY-Verletzung, dms-hub profitiert nicht
- **Abgelehnt**

## Entscheidung

**Option B: iil-ingest erweitern** — Multi-Tool Ensemble + VectorStore-Chunks als neue Extras.

### E1: Erweiterte Package-Architektur (`iil-ingest` v0.2+)

Das bestehende `iil-ingest` Package (ADR-170) wird um neue Extras und Module erweitert:

```python
from ingest import IngestPipeline
from ingest.extractors.pdf import PDFExtractor
from ingest.chunkers import SemanticChunker      # NEU
from ingest.vectorstore import ChunkWriter        # NEU

pipeline = IngestPipeline(extractor=PDFExtractor())

# Use Case 1: Bestehend (ADR-170) — Dokument-Extraktion + Klassifikation
result = pipeline.run(pdf_bytes, filename="doc.pdf")
# → IngestedDocument(text, metadata, doc_type)

# Use Case 2: NEU — Template-Struktur (risk-hub)
result = pipeline.extract_structure(pdf_bytes)
# → {"sections": [...], "tables": [...], "metadata": {...}}

# Use Case 3: NEU — VectorStore-Chunks (meiki-hub, alle Repos)
chunks = pipeline.extract_chunks(pdf_bytes)
# → [Chunk(text="...", metadata={section, page, type, table_headers, ...}), ...]
```

**Neue Extras (pip install):**

| Extra | Was | Dependencies |
|-------|-----|-------------|
| `iil-ingest[pdf]` | Bestehend (ADR-170) | pdfplumber, pdfminer.six |
| `iil-ingest[tables]` | **NEU:** camelot Stream für borderless-Tabellen | camelot-py, opencv |
| `iil-ingest[ocr]` | Bestehend (ADR-170) | tesseract, pdf2image |
| `iil-ingest[vectorstore]` | **NEU:** Chunk-Pipeline + pgvector-Writer | pgvector, aifw |
| `iil-ingest[structure]` | **NEU:** Section-Detection + Template-Mapping | (pure Python) |

### E2: Tiered Extraction

| Tier | Tool | Wann | Was |
|------|------|------|-----|
| **1** | pdfplumber | Immer (Standard) | Text + Tabellen mit Rahmen |
| **2** | camelot (Stream) | Optional, wenn borderless-Tabellen vermutet | Borderless-Tabellen |
| **3** | PyMuPDF + Tesseract | Optional, wenn kein Text extrahiert (Scan) | OCR für gescannte PDFs |

Tier 2 und 3 sind **optionale Extras** (`pip install iil-ingest[tables]`, `iil-ingest[ocr]`).

**System-Dependencies für Tier 2/3 (Dockerfile-Impact):**

| Extra | System-Packages | Dockerfile-Änderung |
|-------|----------------|--------------------|
| `[tables]` (camelot) | `ghostscript`, `libopencv-dev` | `RUN apt-get install -y ghostscript python3-opencv` |
| `[ocr]` (Tesseract) | `tesseract-ocr`, `tesseract-ocr-deu` | `RUN apt-get install -y tesseract-ocr tesseract-ocr-deu` |

### E3: VectorStore-Integration

Extrahierte Chunks enthalten strukturierte Metadaten für pgvector:

```python
@dataclass
class Chunk:
    text: str
    chunk_type: str          # "heading", "paragraph", "table", "list"
    metadata: dict           # section_label, page, source_file, tenant_id
    embedding: list[float]   # Optional, via aifw
```

**VectorStore-Schema (pgvector):**

```sql
CREATE TABLE document_chunks (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       UUID NOT NULL,
    source_document VARCHAR(500) NOT NULL,     -- Dateiname / URL
    source_hash     VARCHAR(64) NOT NULL,      -- SHA-256 des Quelldokuments
    chunk_index     INTEGER NOT NULL,          -- Position im Dokument
    chunk_type      VARCHAR(50) NOT NULL,      -- heading, paragraph, table, list
    content         TEXT NOT NULL,
    metadata        JSONB DEFAULT '{}',        -- section_label, page, table_headers, ...
    embedding       vector(1536),              -- OpenAI text-embedding-3-small
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source_hash, chunk_index)
);

CREATE INDEX idx_chunks_tenant ON document_chunks(tenant_id);
CREATE INDEX idx_chunks_source ON document_chunks(source_hash);
CREATE INDEX idx_chunks_embedding ON document_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Embedding-Strategie:** `text-embedding-3-small` (1536 Dimensionen) via `aifw`. Fallback auf lokale Modelle (768 Dim) für Offline-Nutzung — dann `vector(768)` Spalte parallel.

**Chunk-Versionierung:** Bei Re-Upload eines Dokuments werden alle Chunks mit gleichem `source_hash` gelöscht und neu erstellt (Replace-Strategie). Der `source_hash` ändert sich nur bei inhaltlicher Änderung.

Die VectorStore-Anbindung nutzt den bestehenden pgvector-Stack (mcp-hub DB) und `aifw` für Embeddings.

### E5: Ingestion-Trigger

Die Pipeline wird ausgelöst durch:

| Trigger | Wann | Implementierung |
|---------|------|----------------|
| **Upload-View** | User lädt PDF hoch | Synchron in Request (< 5 Seiten) oder Celery-Task (> 5 Seiten) |
| **Celery-Task** | Batch-Import, Re-Indexierung | `ingest_document.delay(doc_id, tenant_id)` |
| **Management Command** | Initial-Import, Migration | `python manage.py ingest_documents --all` |
| **Temporal Workflow** (Phase 7+) | Komplexe Multi-Step-Pipelines | Orchestriert OCR → Parse → Chunk → Embed |

### E6: Security — PDF-Upload-Härtung

| Risiko | Maßnahme |
|--------|----------|
| **Malicious PDF** (Code Execution) | Parsing in Sandbox: nur pdfplumber/PyMuPDF, kein JavaScript-Rendering |
| **Zip Bomb / Decompression Bomb** | Max-Filesize (50 MB), Max-Pages (500), Timeout (60s) |
| **Path Traversal** | Dateiname wird sanitized (`slugify`), nur Basename gespeichert |
| **Content Injection** | Extrahierter Text wird vor Embedding HTML-escaped |
| **Tenant-Isolation** | Alle Queries filtern `WHERE tenant_id = %s` — kein Cross-Tenant-Zugriff |

### E4: Migration von risk-hub

Die lokale Implementierung in `risk-hub/doc_template_views.py` wird schrittweise durch `iil-ingest[structure]` ersetzt:

1. `iil-ingest` um `[structure]` Extra erweitern (Section-Detection, Tabellen-Mapping)
2. `doc_template_views.py` auf `ingest.extract_structure()` umstellen
3. `iil-concept-templates` als Thin-Wrapper auf `iil-ingest[structure]` migrieren

## Phasenplan

| Phase | Inhalt | Wo | Status |
|-------|--------|----|--------|
| **P1** | pdfplumber Tabellenerkennung + Section Import-Modi | risk-hub lokal | ✅ Done (ADR-046) |
| **P2** | `iil-ingest` v0.2: `[structure]` + `[tables]` Extras hinzufügen | iil-ingest / PyPI | ⏳ Geplant |
| **P3** | Tier-2: camelot Stream für borderless-Tabellen | iil-ingest[tables] | ⏳ Geplant |
| **P4** | `iil-ingest[vectorstore]`: Chunk-Pipeline + pgvector-Writer | iil-ingest + mcp-hub | ⏳ Geplant |
| **P5** | risk-hub + meiki-hub auf `iil-ingest[structure]` migrieren | risk-hub, meiki-hub | ⏳ Geplant |
| **P6** | Tier-3: OCR-Verbesserung (PyMuPDF Layout + Tesseract) | iil-ingest[ocr] | ⏳ Idee |
| **P7** | Temporal-Workflow für komplexe Ingestion-Pipelines | iil-ingest + Temporal | ⏳ Idee |
| **P8** | ML-basierte Layout-Analyse (marker/docling) als Tier-4 | iil-ingest | ⏳ Idee |

## Open Questions

| # | Frage | Kontext | Vorläufige Antwort |
|---|-------|---------|-------------------|
| 1 | **Wo lebt die VectorStore-Tabelle?** | mcp-hub DB hat bereits pgvector; eigene DB wäre Overhead | Gleiche DB (`mcp_hub_db`), eigenes Schema `ingest` |
| 2 | **Wie werden Chunks bei Re-Upload aktualisiert?** | Dokument ändert sich → alte Chunks ungültig | Replace-Strategie: DELETE WHERE source_hash + INSERT neu |
| 3 | **Wer triggert die Ingestion?** | Upload-View ist synchron, Batch braucht async | Hybrid: sync < 5 Seiten, Celery-Task > 5 Seiten |
| 4 | **Multi-Tenant-Isolation bei Chunks?** | Alle Repos nutzen pgvector → Tenant-Trennung Pflicht | `tenant_id` als NOT NULL + Index, alle Queries gefiltert |
| 5 | **Embedding-Dimension?** | OpenAI = 1536, lokale Modelle = 768 | Start mit 1536 (text-embedding-3-small), Parallel-Spalte für 768 bei Bedarf |
| 6 | **Publish-Workflow für neue Version?** | iil-ingest hat bereits `publish.yml` | Bestehenden Workflow nutzen, neue Extras testen |
| 7 | **Verhältnis zu iil-concept-templates?** | Überlappung bei Strukturerkennung | concept_templates wird Thin-Wrapper auf `iil-ingest[structure]` (Adapter-Pattern) |

## Konsequenzen

### Positiv

- **Plattformweite Wiederverwendung** — jedes Repo kann PDF/Dokumente analysieren ohne eigene Implementierung
- **VectorStore-ready** — extrahierte Chunks mit Metadaten fließen direkt in pgvector für RAG
- **Iterativ erweiterbar** — Tier-System erlaubt schrittweises Hinzufügen neuer Extraktoren
- **PyPI-First** — konsistent mit dem iil-Package-Ökosystem (ADR-022)
- **Bessere Tabellenerkennung** — Ensemble eliminiert Schwächen einzelner Tools

### Negativ / Risiken

- **Dependency-Wachstum** — camelot braucht OpenCV, Tesseract braucht System-Packages
- **Komplexität** — Multi-Tool-Orchestrierung und Ergebnis-Merge sind nicht trivial
- **Wartung** — mehr Tools = mehr potenzielle Breaking Changes bei Updates

### Neutral

- Bestehende risk-hub Implementierung bleibt funktional bis Migration (P5)
- `iil-concept-templates` wird nicht sofort deprecated, sondern schrittweise abgelöst

## Confirmation

Die Entscheidung gilt als erfolgreich umgesetzt wenn:

1. `iil-ingest` v0.2+ auf PyPI mit `[structure]` und `[vectorstore]` Extras
2. risk-hub `doc_template_views.py` auf `ingest.extract_structure()` umgestellt ist
3. Mindestens ein weiteres Repo (meiki-hub) `ingest.extract_chunks()` nutzt
4. VectorStore-Chunks in pgvector gespeichert und per Semantic Search abrufbar sind

## Glossar

| Begriff | Erklärung |
|---------|-----------|
| **borderless-Tabelle** | Tabelle ohne sichtbare Rahmenlinien; schwerer zu erkennen als Tabellen mit Gitternetz |
| **camelot** | Python-Library spezialisiert auf Tabellenerkennung in PDFs; "Lattice"-Modus (Rahmen) und "Stream"-Modus (ohne Rahmen) |
| **Chunk** | Ein semantisch zusammenhängender Textabschnitt mit Metadaten (Quelle, Seite, Typ); typische Größe: 200–1000 Tokens |
| **concept_templates** | Bestehendes iil-Package (`iil-concept-templates`) für Template-Strukturerkennung aus Text |
| **Embedding** | Numerische Vektordarstellung eines Textes; semantisch ähnliche Texte haben ähnliche Vektoren |
| **iil-ingest** | Bestehendes PyPI-Package für Dokument-Ingestion (ADR-170); dieses ADR erweitert es um VectorStore + Structure |
| **IVFFlat** | Index-Typ in pgvector für approximate nearest neighbor Suche; schneller als exakte Suche bei großen Datenmengen |
| **Lattice-Modus** | Tabellenerkennung anhand von Linien/Rahmen im PDF (camelot); funktioniert bei Tabellen mit sichtbarem Gitter |
| **OCR** | Optical Character Recognition — Texterkennung in Bildern/gescannten Dokumenten |
| **pdfplumber** | Python-Library zur PDF-Analyse; extrahiert Text und Tabellen anhand von Zellgrenzen (Linien) |
| **pgvector** | PostgreSQL-Extension für Vektor-Speicherung und -Suche; bereits im mcp-hub Stack |
| **PyMuPDF (fitz)** | Schnelle PDF-Library mit Layout-Analyse und optionaler OCR-Integration |
| **PyPI** | Python Package Index — zentrales Repository für Python-Packages (pypi.org) |
| **RAG** | Retrieval-Augmented Generation — KI-Technik, die relevante Dokument-Chunks als Kontext für LLM-Antworten nutzt |
| **Section-Mapping** | Zuordnung extrahierter Tabellen/Inhalte zu den erkannten Dokumentabschnitten |
| **Stream-Modus** | Tabellenerkennung ohne Linien (camelot); erkennt Spalten anhand von Textausrichtung |
| **Temporal** | Workflow-Engine für langlebige, zuverlässige Prozesse (ADR-079); potenzieller Orchestrator für komplexe Ingestion |
| **Tesseract** | Open-Source OCR-Engine für gescannte Dokumente; unterstützt 100+ Sprachen |
| **Tiered Extraction** | Stufenweiser Einsatz von Tools — einfache zuerst, aufwändigere nur bei Bedarf |
| **VectorStore** | Datenbank für Vektoren (Embeddings); ermöglicht semantische Ähnlichkeitssuche |
