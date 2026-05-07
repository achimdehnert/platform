---
status: proposed
date: 2026-05-07
deciders: [Achim Dehnert]
consulted: []
informed: []
implementation_status: partial
implementation_evidence: "Phase 1 in risk-hub: pdfplumber Tabellenerkennung + Section Import-Modi (risk-hub ADR-046)."
---

# ADR-187: Document Intelligence Pipeline — Plattformweite Dokument-Analyse für Templates, RAG & VectorStore

- **Status:** Proposed
- **Datum:** 2026-05-07
- **Entscheider:** Achim Dehnert
- **Betroffene Repos:** Alle (risk-hub, meiki-hub, coach-hub, travel-beat, weltenhub, etc.)
- **Betroffene Packages:** `iil-concept-templates` (bestehend), `iil-ingestfw` (neu geplant)
- **Abhängigkeiten:** ADR-009 (Platform Architecture), ADR-022 (Platform Consistency), ADR-027 (Shared Backend Services)
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

- **risk-hub** hat eine lokale Implementierung in `doc_template_views.py` (pdfplumber + Section-Detection)
- **`iil-concept-templates`** (0.5.0) bietet text-basierte Strukturerkennung, aber keine echte Tabellenerkennung
- **Kein plattformweiter VectorStore** für Dokument-Chunks — pgvector ist nur für Agent-Memory (mcp-hub)
- Jedes Repo, das PDF-Parsing braucht, müsste die Logik neu implementieren

### Probleme

1. **Kein Shared Package** für Dokument-Ingestion — risk-hub hat lokale Implementierung, andere Repos haben nichts
2. **Einzeltool-Limitierung** — pdfplumber allein erkennt keine borderless-Tabellen und versagt bei gescannten PDFs
3. **Keine VectorStore-Integration** — extrahierte Inhalte werden nur als Template-JSON gespeichert, nicht als durchsuchbare Chunks
4. **Keine Metadaten-Anreicherung** — extrahierte Sections wissen nicht, aus welchem Dokument/Seite/Kontext sie stammen

## Considered Options

### Option A: Einzeltool (pdfplumber only) — Status quo

- **Pro:** Einfach, bereits implementiert, keine neuen Dependencies
- **Contra:** Keine borderless-Tabellen, keine OCR, kein VectorStore, nicht plattformweit

### Option B: Multi-Tool Ensemble als PyPI-Package (`iil-ingestfw`)

Tiered Extraction mit mehreren spezialisierten Tools:

```
Tier 1: pdfplumber (schnell, Rahmen-Tabellen)
  ↓ Falls borderless-Tabellen vermutet
Tier 2: camelot Stream-Modus (borderless-Tabellen)
  ↓ Falls gescanntes PDF (kein Text extrahiert)
Tier 3: PyMuPDF + OCR (Tesseract)
```

- **Pro:** Beste Erkennungsqualität, plattformweit wiederverwendbar, VectorStore-ready
- **Contra:** Mehr Dependencies, höhere Komplexität, OpenCV für camelot nötig

### Option C: ML-basiert (marker-pdf / docling)

- **Pro:** State-of-the-art Erkennung, Layout-Verständnis
- **Contra:** GPU-Abhängigkeit für Performance, große Model-Downloads, Overkill für strukturierte PDFs

## Entscheidung

**Option B: Multi-Tool Ensemble als `iil-ingestfw` Package** mit optionalen Tier-2/3-Extras.

### E1: Package-Architektur (`iil-ingestfw`)

```python
from iil_ingestfw import IngestPipeline
from iil_ingestfw.extractors import PDFExtractor

pipeline = IngestPipeline(extractor=PDFExtractor())

# Use Case 1: Template-Struktur (risk-hub)
result = pipeline.extract_structure(pdf_bytes)
# → {"sections": [...], "tables": [...], "metadata": {...}}

# Use Case 2: VectorStore-Chunks (meiki-hub, alle Repos)
chunks = pipeline.extract_chunks(pdf_bytes)
# → [Chunk(text="...", metadata={section, page, type, table_headers, ...}), ...]

# Use Case 3: Nur Text (einfachster Fall)
text = pipeline.extract_text(pdf_bytes)
```

### E2: Tiered Extraction

| Tier | Tool | Wann | Was |
|------|------|------|-----|
| **1** | pdfplumber | Immer (Standard) | Text + Tabellen mit Rahmen |
| **2** | camelot (Stream) | Optional, wenn borderless-Tabellen vermutet | Borderless-Tabellen |
| **3** | PyMuPDF + Tesseract | Optional, wenn kein Text extrahiert (Scan) | OCR für gescannte PDFs |

Tier 2 und 3 sind **optionale Extras** (`pip install iil-ingestfw[tables]`, `iil-ingestfw[ocr]`).

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

Die VectorStore-Anbindung nutzt den bestehenden pgvector-Stack (mcp-hub DB) und `aifw` für Embeddings.

### E4: Migration von risk-hub

Die lokale Implementierung in `risk-hub/doc_template_views.py` wird schrittweise durch `iil-ingestfw` ersetzt:

1. Package veröffentlichen mit Tier-1-Funktionalität (pdfplumber)
2. `doc_template_views.py` auf `iil-ingestfw.extract_structure()` umstellen
3. `iil-concept-templates` als Thin-Wrapper auf `iil-ingestfw` migrieren

## Phasenplan

| Phase | Inhalt | Wo | Status |
|-------|--------|----|--------|
| **P1** | pdfplumber Tabellenerkennung + Section Import-Modi | risk-hub lokal | ✅ Done (ADR-046) |
| **P2** | `iil-ingestfw` Package scaffolden, Tier-1 (pdfplumber) extrahieren | platform / PyPI | ⏳ Geplant |
| **P3** | Tier-2: camelot Stream für borderless-Tabellen | iil-ingestfw | ⏳ Geplant |
| **P4** | VectorStore-Chunk-Pipeline + pgvector-Integration | iil-ingestfw + mcp-hub | ⏳ Geplant |
| **P5** | risk-hub + meiki-hub auf `iil-ingestfw` migrieren | risk-hub, meiki-hub | ⏳ Geplant |
| **P6** | Tier-3: OCR für gescannte PDFs (PyMuPDF + Tesseract) | iil-ingestfw | ⏳ Idee |
| **P7** | ML-basierte Layout-Analyse (marker/docling) als Tier-4 | iil-ingestfw | ⏳ Idee |

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

1. `iil-ingestfw` auf PyPI veröffentlicht ist (≥ 0.1.0)
2. risk-hub `doc_template_views.py` auf `iil-ingestfw.extract_structure()` umgestellt ist
3. Mindestens ein weiteres Repo (meiki-hub) `iil-ingestfw.extract_chunks()` nutzt
4. VectorStore-Chunks in pgvector gespeichert und per Semantic Search abrufbar sind

## Glossar

| Begriff | Erklärung |
|---------|-----------|
| **pdfplumber** | Python-Library zur PDF-Analyse; extrahiert Text und Tabellen anhand von Zellgrenzen (Linien) |
| **camelot** | Python-Library spezialisiert auf Tabellenerkennung in PDFs; "Lattice"-Modus (mit Rahmen) und "Stream"-Modus (ohne Rahmen) |
| **PyMuPDF (fitz)** | Schnelle PDF-Library mit Layout-Analyse und optionaler OCR-Integration |
| **Tesseract** | Open-Source OCR-Engine (Optical Character Recognition) für gescannte Dokumente |
| **VectorStore** | Datenbank für Vektoren (Embeddings); ermöglicht semantische Ähnlichkeitssuche |
| **pgvector** | PostgreSQL-Extension für Vektor-Speicherung und -Suche; bereits im mcp-hub Stack |
| **RAG** | Retrieval-Augmented Generation — KI-Technik, die relevante Dokument-Chunks als Kontext für LLM-Antworten nutzt |
| **Chunk** | Ein semantisch zusammenhängender Textabschnitt mit Metadaten (Quelle, Seite, Typ) |
| **Tiered Extraction** | Stufenweiser Einsatz von Tools — einfache Tools zuerst, aufwändigere nur bei Bedarf |
| **borderless-Tabelle** | Tabelle ohne sichtbare Rahmenlinien; schwerer zu erkennen als Tabellen mit Gitternetz |
| **Section-Mapping** | Zuordnung extrahierter Tabellen/Inhalte zu den erkannten Dokumentabschnitten |
| **iil-ingestfw** | Geplantes PyPI-Package für plattformweite Dokument-Ingestion |
| **concept_templates** | Bestehendes iil-Package für Template-Strukturerkennung aus Text |
