---
status: Accepted
date: 2026-04-23
amended: 2026-04-23
amendment_1: 2026-04-23 — OCR-Nicht-Entscheidung revidiert: iil-ingest[ocr] als optionales Extra (Tesseract Fallback)
decision-makers: Achim Dehnert
implementation_status: full
implementation_evidence:
  - "iil-ingest v0.1.0 auf PyPI publiziert (pip install iil-ingest[pdf])"
  - "58 Tests, 91% Coverage — CI grün (GitHub Actions)"
  - "dms-hub/apps/benefits/classifier.py importiert ProfileClassifier + PDFExtractor aus ingest.*"
  - "dms-hub/apps/accounting/extractor.py importiert PDFExtractor aus ingest.extractors.pdf"
  - "dms-hub/pyproject.toml: iil-ingest[pdf] als Dependency eingetragen"
  - "iil-ingest[ocr] implementiert: PDFExtractor(ocr_fallback=True) via Tesseract + pdf2image"
consulted: []
informed: []
<!-- Drift-Detector-Felder
staleness_months: 6
drift_check_paths:
  - iil-ingest/ingest/classifier.py
  - iil-ingest/ingest/extractors/pdf.py
  - iil-ingest/ingest/extractors/ocr.py
  - dms-hub/src/apps/benefits/classifier.py
  - dms-hub/src/apps/accounting/extractor.py
supersedes_check: null
-->
---

# ADR-170: Adopt iil-ingest as Reusable Document Ingestion Package (Tier 3)

## Context and Problem Statement

Mehrere Hubs der IIL-Platform müssen hochgeladene Dokumente verarbeiten: Inhalt
extrahieren, Typ klassifizieren, strukturierte Daten speichern und für
Downstream-Prozesse (Anzeige, Suche, Enrichment) bereitstellen.

**Status quo — dms-hub hat das Problem bereits gelöst, aber isoliert:**

| Komponente | Datei | Was sie tut | Problem |
|---|---|---|---|
| PDF-Classifier | `apps/benefits/classifier.py` | Keyword-Profile-Scoring, 10+ Dokumenttypen | Nur in dms-hub nutzbar |
| Receipt-Extraktor | `apps/accounting/extractor.py` | Betrag, Datum, Lieferant, Steuersatz aus PDF | Nur in dms-hub nutzbar |
| Archive-Model | `apps/archive/models.py` | DmsArchiveRecord + Status-Machine | Django-gebunden |

**Dasselbe Problem tritt in anderen Hubs auf:**

| Hub | Dokument-Bedarf | Aktueller Stand |
|---|---|---|
| risk-hub | SDS-PDFs parsen → H/P-Codes, physik. Werte | eigene ad-hoc Regex |
| research-hub | Artikel, Berichte, Papers → Text + Metadaten | keine Lösung |
| ausschreibungs-hub | Ausschreibungs-PDFs → Titel, Fristen, Anforderungen | keine Lösung |
| cad-hub | Technische Zeichnungen → Metadaten, Stücklisten | keine Lösung |

**Konsequenz ohne Entscheidung:** Jeder Hub reimplementiert Extraktion und
Klassifikation — unterschiedliche Qualität, keine Wiederverwendung, hoher
Maintenance-Aufwand.

## Decision Drivers

- **DRY-Verletzung**: dms-hub's `classifier.py` + `extractor.py` sind nicht
  importierbar außerhalb des dms-hub Django-Prozesses
- **Wachsender Bedarf**: research-hub, risk-hub, ausschreibungs-hub benötigen
  identische Basislogik
- **Bewährtes Vorbild**: iil-enrichment (ADR-169) zeigt exakt das richtige
  Pattern: Pure Python Core + Provider-Pattern + optionale Django-Integration
- **Paperless-NGX läuft bereits**: klare Trennung von ARCHIVE (Paperless) und
  PROCESSING (iil-ingest) vermeidet Overlap
- **Testbarkeit**: Extraktoren und Classifier müssen ohne Django-Kontext
  testbar sein

## Considered Options

### Option A: iil-ingest als neues Tier-3 Package (empfohlen)

Pure Python Package nach dem iil-enrichment-Pattern. Core-Logik aus dms-hub
extrahieren und verallgemeinern. Hubs registrieren eigene Profile.

### Option B: Logik in dms-hub belassen, andere Hubs importieren dms-hub

`dms-hub` als Dependency für alle Hubs → schafft falsche Abhängigkeit.
Ein "Document Management System" als Basis-Library ist architektonisch falsch.
**Abgelehnt.**

### Option C: Logik in `platform`-Package

`platform/packages/` hat bereits `docs-agent`, `platform-context`. Wäre
möglich, aber widerspricht dem Prinzip: Platform-Packages sind für
Platform-Infrastruktur, nicht für Business-Logik.
**Abgelehnt.**

### Option D: Paperless-NGX API als Ingestion-Layer

Paperless übernimmt Upload + OCR + Klassifikation. Hubs konsumieren Paperless
API.

- ✅ OCR bereits implementiert (Tesseract)
- ❌ Paperless klassifiziert nach eigenen Regeln (Tags), nicht nach Hub-Logik
- ❌ Kein strukturiertes Extrakt (nur Text + Tags)
- ❌ Jeder Hub müsste Paperless-API-Aufrufe implementieren
- ❌ Paperless ist Archive, nicht Processing-Pipeline

**Abgelehnt** als alleinige Lösung. Paperless bleibt ARCHIVE-Layer.

## Decision Outcome

**Gewählte Option: Option A — neues Tier-3 Package `iil-ingest`** nach dem iil-enrichment-Pattern (ADR-169).

Die bestehende Logik aus `dms-hub/apps/benefits/classifier.py` und
`dms-hub/apps/accounting/extractor.py` wird extrahiert, verallgemeinert und
als Pure-Python-Core in `iil-ingest` bereitgestellt. dms-hub wird zum
Consumer.

### Confirmation

Compliance wird wie folgt verifiziert:

- `pip install iil-ingest[pdf]` ist erfolgreich (Package auf PyPI publiziert)
- `IngestPipeline.run(bytes, filename)` → `IngestedDocument` (Smoke-Test)
- `pytest tests/` läuft komplett ohne Django-Kontext durch (≥30 Tests, ≥85% Coverage)
- dms-hub: alle bestehenden Tests grün nach Migration auf iil-ingest
- `dms-hub/apps/benefits/classifier.py` und `dms-hub/apps/accounting/extractor.py`
  importieren aus `ingest.*` (kein lokaler Duplikat-Code)
- `catalog-info.yaml` im Root des iil-ingest Repos vorhanden
  (`spec.type: library`, `spec.lifecycle: experimental`)

## Pros and Cons of the Options

### Option A: iil-ingest als neues Tier-3 Package

- ✅ Pure Python — testbar ohne Django
- ✅ Exaktes Pattern wie iil-enrichment (ADR-169) — keine Lernkurve
- ✅ dms-hub-Logik sofort wiederverwendbar
- ✅ Hubs registrieren eigene Profile → erweiterbar
- ❌ Migration dms-hub erforderlich (~2-3h)
- ❌ Neue Dependency für alle Consumer-Hubs

### Option B: Logik in dms-hub belassen, andere Hubs importieren dms-hub

- ✅ Kein neues Repo, kein Migrations-Aufwand
- ❌ Falsche Abhängigkeit: DMS-System als Basis-Library
- ❌ Circular Imports möglich (risk-hub → dms-hub → risk-hub)
- ❌ Django-Kontext als transitive Pflicht für alle Consumer
- ❌ Skaliert nicht: jeder neue Hub zieht das komplette dms-hub mit

### Option C: Logik in `platform`-Package

- ✅ Zentral, keine neue Repo-Infrastruktur
- ❌ Platform-Packages sind für Infrastruktur, nicht Business-Logik
- ❌ Würde Platform-Package mit Dokumenten-Domäne vermischen
- ❌ Kein klares Ownership

### Option D: Paperless-NGX API als Ingestion-Layer

- ✅ OCR (Tesseract) bereits eingebaut
- ✅ Kein neues Package
- ❌ Paperless klassifiziert nach eigenen Tag-Regeln, nicht Hub-Logik
- ❌ Kein strukturiertes Extrakt (nur Plaintext + Tags)
- ❌ Jeder Hub: eigene Paperless-API-Anbindung
- ❌ Paperless ist ARCHIVE-Layer, kein PROCESSING-Layer

---

## Architecture

### Package-Struktur

```
iil-ingest/
├── ingest/
│   ├── __init__.py          # public API
│   ├── types.py             # ExtractedContent, IngestedDocument, DocumentKind
│   ├── detector.py          # MIME-Erkennung (mimetypes + magic bytes)
│   ├── pipeline.py          # IngestPipeline: detect → extract → classify
│   ├── classifier.py        # ProfileClassifier (domain-agnostic engine)
│   ├── registry.py          # IngestRegistry (analog EnrichmentRegistry)
│   ├── extractors/
│   │   ├── base.py          # ExtractorProtocol
│   │   ├── pdf.py           # pdfplumber → text + tables + metadata
│   │   ├── excel.py         # openpyxl → DataFrames + sheet names
│   │   ├── csv.py           # stdlib csv → rows + schema detection
│   │   └── docx.py          # python-docx → text + headings + tables
│   ├── profiles/
│   │   └── german_hr.py     # GermanHRDocumentProfile (aus dms-hub migriert)
│   └── django/
│       ├── __init__.py
│       └── mixins.py        # IngestMixin für Django FileField-Models
├── pyproject.toml
└── tests/
```

### Core Types

```python
@dataclass
class ExtractedContent:
    raw_bytes: bytes
    text: str                          # vollständiger Plaintext
    tables: list[list[list[str]]]      # pages → rows → cells
    metadata: dict[str, Any]           # title, author, created, pages, ...
    mime_type: str
    page_count: int
    extraction_errors: list[str]

@dataclass
class IngestedDocument:
    source_name: str                   # Dateiname
    content: ExtractedContent
    doc_type: str                      # aus Classifier
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    score: float
    matched_profiles: list[str]
    extra: dict[str, Any]             # Extractor-spezifische Felder
                                      # z.B. {"amount": "40.00", "date": "2026-04-23"}
```

### Protocol Layer

```python
class ExtractorProtocol(Protocol):
    """Wandelt rohe Bytes in ExtractedContent um."""
    supported_mimes: frozenset[str]
    def extract(self, data: bytes) -> ExtractedContent: ...

class ClassifierProfile(Protocol):
    """Definiert ein Dokumentmuster für den ProfileClassifier."""
    name: str                                   # z.B. "KONTOAUSZUG"
    patterns: list[tuple[str, int]]             # (regex, weight)
    min_score: int                              # Mindest-Score für Confidence LOW

class ContentStore(Protocol):
    """Hub-spezifischer Storage-Backend. NICHT in iil-ingest implementiert."""
    def save(self, doc: IngestedDocument) -> str: ...  # gibt Location/ID zurück
```

### ProfileClassifier (verallgemeinert aus dms-hub)

Der bestehende `classifier.py` aus `dms-hub/apps/benefits/` implementiert
bereits den richtigen Algorithmus:

```python
# dms-hub (heute) — wird zu:
class ProfileClassifier:
    """Domain-agnostic keyword-profile classifier."""

    def __init__(self, profiles: list[ClassifierProfile], min_score: int = 10):
        self._profiles = profiles
        self._min_score = min_score

    def classify(self, text: str) -> ClassificationResult:
        text_lower = text.lower()
        scores: dict[str, int] = {}
        for profile in self._profiles:
            score = sum(
                weight * min(len(re.findall(pattern, text_lower)), 3)
                for pattern, weight in profile.patterns
            )
            scores[profile.name] = score
        best = max(scores, key=scores.get)
        ...
```

### Pipeline

```python
pipeline = IngestPipeline(
    extractors=[PDFExtractor(), ExcelExtractor()],
    classifier=ProfileClassifier(profiles=[GermanHRDocumentProfile()]),
)
doc: IngestedDocument = pipeline.run(file_bytes, filename="rechnung.pdf")
# doc.doc_type      → "KONTOAUSZUG"
# doc.confidence    → "HIGH"
# doc.content.text  → vollständiger Plaintext
# doc.extra         → {"amount": "2340.00", "date": "2026-03-01"}
```

## Abgrenzung zu bestehenden Systemen

| System | Rolle | Überschneidung |
|---|---|---|
| **paperless-docs** (Paperless-NGX) | ARCHIVE: OCR, Speichern, Suchen, Abrufen | Keine — komplementär. iil-ingest → klassifiziert. Paperless → archiviert. |
| **iil-enrichment** (ADR-169) | ENRICH: Record → externe API → Anreicherung | Keine — sequenziell. ingest → classify SDS → enrich mit PubChem. |
| **dms-hub** | DMS-Integration (d.velop), Buchhaltung, Benefits | dms-hub wird Consumer von iil-ingest. |
| **iil-reflex** | UC-Methodik, REFLEX-Zyklus, UI/TDD | Keine Überschneidung. |

## Migration: dms-hub

Nach Fertigstellung von iil-ingest:

```
dms-hub/apps/benefits/classifier.py   →  ingest/profiles/german_hr.py (in iil-ingest)
dms-hub/apps/accounting/extractor.py  →  ingest/extractors/pdf.py (erweitert)
dms-hub/pyproject.toml                →  add "iil-ingest[pdf]>=0.1"
```

dms-hub's `classify_pdf()` wird zu:
```python
from ingest import IngestPipeline
from ingest.profiles.german_hr import GermanHRDocumentProfile

pipeline = IngestPipeline(
    classifier=ProfileClassifier([GermanHRDocumentProfile()])
)
```

## Optional-Extras (pyproject.toml)

```toml
[project.optional-dependencies]
pdf   = ["pdfplumber>=0.11"]
excel = ["openpyxl>=3.1"]
docx  = ["python-docx>=1.1"]
csv   = []                        # stdlib, kein extra
ocr    = ["pytesseract>=0.3", "pdf2image>=1.17"]
all    = ["iil-ingest[pdf,excel,docx,ocr]"]
django = ["django>=5.0"]
```

## Bewusste Nicht-Entscheidungen

- **OCR**: ~~Nicht in iil-ingest~~ → **Revidiert (2026-04-23):** `iil-ingest[ocr]` bietet
  optionalen Tesseract-Fallback via `PDFExtractor(ocr_fallback=True)`. Wird nur
  aktiviert wenn pdfplumber leeren Text liefert (gescannte PDFs). Consumer
  entscheidet explizit. Paperless bleibt ARCHIVE-Layer für bereits-OCR'd Dokumente.
  System-Abhängigkeiten: `tesseract-ocr` + `poppler-utils` (apt).
- **Async**: Nicht in iil-ingest — Hub-Verantwortung (Celery-Task wrapping).
- **Storage**: Nicht in iil-ingest — `ContentStore` ist Protocol, Hub implementiert.
- **LLM-Klassifikation**: Nicht in v0.1 — Profile-Scoring reicht für bekannte
  Dokumenttypen. LLM-Extension in v0.2+ (siehe ADR-17x, geplant).
- **Versionierung**: Nicht in iil-ingest — Hub-spezifische SHA256-Dedup analog
  risk-hub's SDS-Versioning.

## Consequences

### Positiv

- **Wiederverwendung**: classifier.py + extractor.py aus dms-hub sofort nutzbar
  für risk-hub, research-hub, ausschreibungs-hub
- **Testbarkeit**: Pure Python — kein Django-Kontext für Unit-Tests nötig
- **Erweiterbarkeit**: neue Profile per `ClassifierProfile`-Implementation,
  neue Extraktoren per `ExtractorProtocol`
- **Konsistenz**: gleiches Pattern wie iil-enrichment (ADR-169) — keine neue
  Lernkurve für Entwickler

### Negativ / Risiken

- **Migration dms-hub**: bestehender Code muss refaktoriert werden (~2-3h)
- **neue Dependency**: Hubs, die iil-ingest einbinden, bekommen pdfplumber etc.
  als transitive Dependency → Größe beachten

## Implementierungsplan

| Phase | Aufgabe | Aufwand |
|---|---|---|
| 0 | Repo erstellen, pyproject.toml, CI, `catalog-info.yaml` | 30min |
| 1 | `types.py`, `detector.py`, `ExtractorProtocol` | 1h |
| 2 | `extractors/pdf.py` (aus dms-hub extrahiert) | 1h |
| 3 | `classifier.py` + `ProfileClassifier` (aus dms-hub extrahiert) | 1h |
| 4 | `profiles/german_hr.py` (aus dms-hub migriert) | 30min |
| 5 | `pipeline.py` + `registry.py` | 1h |
| 6 | Tests (≥30, analog iil-enrichment) | 2h |
| 7 | dms-hub: Migration auf iil-ingest — `classifier.py` + `extractor.py` durch iil-ingest-Imports ersetzen, dann löschen | 2h |
| 8 | `extractors/excel.py`, `csv.py`, `docx.py` | 2h |

**Gesamt: ~10-11h** — verteilt über 2-3 Sessions.

## More Information

- **ADR-169**: iil-enrichment — Pattern-Vorbild (Provider, Registry, Pure Python Core)
- **ADR-163**: Three-Tier Quality Standard (Tier-3 Package-Anforderungen)
- **ADR-077**: catalog-info.yaml Standard (Backstage-Format, Pflichtfelder)
- **GitHub Issue #42** (platform): Implementierungsplan iil-ingest
- **dms-hub Source**: `apps/benefits/classifier.py`, `apps/accounting/extractor.py`
- **iil-enrichment Reference**: `enrichment/provider.py`, `enrichment/registry.py`
- **Outline**: https://knowledge.iil.pet/doc/adr-170-iil-ingest-reusable-document-ingestion-package-xlwe1dffX9
