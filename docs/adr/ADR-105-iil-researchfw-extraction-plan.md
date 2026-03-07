# ADR-105: iil-researchfw — Code-Extraktion und Implementierungsplan

**Status:** Accepted  
**Datum:** 2026-03-07  
**Kontext:** Umsetzung von ADR-104 (Research Hub + iil-researchfw)  
**Abhängigkeit:** ADR-104-research-hub-iil-researchfw.md

---

## Kontext

ADR-104 hat die Architektur entschieden: `iil-researchfw` wird ein eigenständiges PyPI-Package.
Dieser ADR dokumentiert die **genaue Code-Extraktion** aus `bfagent/apps/research/services/`
nach einer vollständigen Analyse der bestehenden Services.

---

## Code-Analyse: bfagent/apps/research/services/

### Inventar der bestehenden Services

| Datei | Größe | Django-Abh. | Direkt extrahierbar |
|---|---|---|---|
| `citation_service.py` | 710 Zeilen | ❌ keine | ✅ 1:1 |
| `academic_search_service.py` | 632 Zeilen | ❌ keine | ✅ minimal anpassen |
| `brave_search_service.py` | 274 Zeilen | ⚠️ `django.conf.settings` | ✅ mit Adapter |
| `ai_summary_service.py` | 261 Zeilen | ⚠️ `apps.bfagent.services.llm_client` | ✅ LLM-agnostisch machen |
| `research_service.py` | 300 Zeilen | ❌ keine | ✅ direkt |
| `export_service.py` | 329 Zeilen | ⚠️ `project.findings.all()` (ORM) | ⚠️ Interface anpassen |
| `vector_store_service.py` | 295 Zeilen | ⚠️ ORM-Zugriff auf Django-Models | ❌ bleibt in research-hub |
| `outline_generator.py` | 662 Zeilen | ⚠️ `apps.core.models.Agent`, LLM | ❌ bleibt in bfagent |
| `paper_frameworks.py` | ~500 Zeilen | ❌ keine | ❌ buchspezifisch, bleibt in bfagent |

---

## Detailanalyse: Was wird wie migriert

### ✅ citation_service.py → `iil_researchfw/citations/`

**Kein Refactoring nötig.** Reines Python, keine Django-Imports.

Enthält:
- `CitationStyle` (Enum): APA, MLA, Chicago, Harvard, IEEE, Vancouver
- `SourceType` (Enum): JOURNAL, BOOK, CHAPTER, CONFERENCE, THESIS, WEBSITE, PREPRINT, REPORT
- `Author` (dataclass): family, given, suffix, orcid + format_apa/mla/ieee()
- `Citation` (dataclass): alle Metadaten + format(), format_in_text(), to_bibtex(), to_ris()
- `CitationService`: from_doi() via CrossRef API, from_url(), format_bibliography(), export_bibtex(), export_ris()

**Externe Abhängigkeiten:** `requests` (lazy import) → auf `httpx` migrieren

**Zieldatei:** `iil_researchfw/citations/formatter.py`

---

### ✅ academic_search_service.py → `iil_researchfw/search/academic.py`

**Minimale Anpassung nötig.** Keine Django-Imports.

Enthält:
- `AcademicPaper` (dataclass): title, authors, abstract, url, source, doi, arxiv_id, ...
- `AcademicSearchService`:
  - `search()` — unified über alle Quellen
  - `_search_arxiv()` — arXiv XML API (kein API-Key)
  - `_search_semantic_scholar()` — Semantic Scholar API (kostenlos)
  - `_search_pubmed()` — NCBI E-utilities XML API
  - `_search_openalex()` — OpenAlex API (kostenlos)
  - `_search_google_scholar()` — via scholarly (optional)
  - `_search_biorxiv()` — bioRxiv API
  - `get_paper_by_doi()` — CrossRef lookup
  - `get_paper_by_arxiv_id()` — arXiv lookup

**Externe Abhängigkeiten:** `requests` → auf `httpx` migrieren

**Zieldatei:** `iil_researchfw/search/academic.py`

---

### ✅ brave_search_service.py → `iil_researchfw/search/brave.py`

**Adapter für API-Key-Konfiguration nötig.**

Aktuell: Liest `BRAVE_API_KEY` aus `django.conf.settings` oder `decouple.config` oder `config.secrets`.
iil-researchfw: API-Key wird im Konstruktor übergeben oder via Umgebungsvariable gelesen.

Enthält:
- `SearchResult` (dataclass)
- `BraveSearchService`:
  - `search()` — Web Search
  - `local_search()` — Local Business Search
  - `_search_via_api()` — direkte Brave API
  - LLM-Fallback → wird **entfernt** (Django-spezifisch)
  - Mock-Fallback bleibt

**Änderung:**
```python
# Vorher (Django-spezifisch)
api_key = getattr(settings, "BRAVE_API_KEY", None)

# Nachher (iil-researchfw)
class BraveSearchService:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("BRAVE_API_KEY", "")
```

**Zieldatei:** `iil_researchfw/search/brave.py`

---

### ✅ ai_summary_service.py → `iil_researchfw/analysis/summary.py`

**LLM-agnostisch machen.** Aktuell hardcoded auf `apps.bfagent.services.llm_client`.

Enthält:
- `AISummaryService`:
  - `summarize_findings()` — Findings → Summary (3 Stile: academic, executive, bullet_points)
  - `summarize_sources()` — Quellen → thematische Analyse
  - `extract_key_points()` — Text → Key Points
  - `generate_research_questions()` — Topic → Forschungsfragen
  - Fallback-Implementierungen (ohne LLM)

**Änderung — LLM-agnostischer Adapter:**
```python
from typing import Callable, Protocol

class LLMCallable(Protocol):
    def __call__(self, prompt: str, max_tokens: int = 500) -> str: ...

class AISummaryService:
    def __init__(self, llm_fn: LLMCallable | None = None):
        self._llm_fn = llm_fn  # Injiziert, kein Django nötig
    
    # Fallback ohne LLM bleibt automatisch aktiv wenn llm_fn=None
```

**Zieldatei:** `iil_researchfw/analysis/summary.py`

---

### ✅ research_service.py → `iil_researchfw/core/service.py`

**Direkt extrahierbar.** Keine Django-Imports.

Enthält:
- `ResearchContext` (dataclass): query, domain, max_sources, language, filters
- `ResearchOutput` (dataclass): success, sources, findings, summary, metadata, errors
- `ResearchService` — zentraler Orchestrator:
  - `research()` — vollständiger Workflow
  - `quick_search()` — schnelle Suche
  - `fact_check()` — Claim-Verifikation

**Zieldatei:** `iil_researchfw/core/service.py`

---

### ⚠️ export_service.py → `iil_researchfw/export/`

**Interface-Anpassung nötig.** Aktuell nimmt `export_markdown(project)` ein Django-Model.

**Änderung — Protocol statt Django-Model:**
```python
from typing import Protocol

class ResearchProjectProtocol(Protocol):
    name: str
    query: str
    description: str
    created_at: datetime
    
    @property
    def findings(self): ...  # iterable
    
    @property  
    def sources(self): ...  # iterable
```

Enthält:
- `export_markdown()` — Markdown-Export
- `export_latex()` — LaTeX-Dokument (BibLaTeX)
- `export_docx()` — Word-Export (python-docx)
- `export_bibtex()` — BibTeX-Referenzliste

**Zieldatei:** `iil_researchfw/export/service.py`

---

### ❌ vector_store_service.py → bleibt in research-hub

Greift direkt auf Django-ORM zu (`project.findings.all()`, `project.sources.all()`).
Optional: abstrahierte Interface-Version für iil-researchfw v0.2.0.

---

### ❌ outline_generator.py → bleibt in bfagent

Harte Django-Abhängigkeit (`apps.core.models.Agent.objects.filter(...)`).
Buchspezifische Logik. Kein Cross-Repo-Nutzen.

---

### ❌ paper_frameworks.py → bleibt in bfagent

Buchspezifische akademische Paper-Frameworks (IMRAD, APA, Nature, etc.).
Kann langfristig in `iil_researchfw/contrib/academic.py` extrahiert werden.

---

## Ziel-Paketstruktur iil-researchfw v0.1.0

```
iil_researchfw/
├── __init__.py               # Version, __all__
├── py.typed
│
├── core/
│   ├── __init__.py
│   ├── models.py             # ResearchContext, ResearchOutput (Dataclasses)
│   └── service.py            # ResearchService — Hauptorchestrator
│
├── search/
│   ├── __init__.py
│   ├── base.py               # BaseSearchProvider (ABC)
│   ├── brave.py              # BraveSearchService (aus bfagent extrahiert)
│   └── academic.py           # AcademicSearchService (arXiv, Semantic Scholar, PubMed, OpenAlex)
│
├── citations/
│   ├── __init__.py
│   └── formatter.py          # CitationStyle, Citation, Author, CitationService (710 Zeilen, 1:1)
│
├── analysis/
│   ├── __init__.py
│   ├── summary.py            # AISummaryService (LLM-agnostisch via Protocol)
│   └── relevance.py          # Relevanz-Scoring (neu)
│
├── export/
│   ├── __init__.py
│   └── service.py            # ResearchExportService (Protocol-Interface)
│
└── contrib/                  # Optionale Domain-Extensions
    ├── __init__.py
    ├── travel.py             # Travel-Research-Helpers (neu)
    ├── academic.py           # Scientific-Writing-Helpers (neu)
    └── worldbuilding.py      # Weltenbau-Research-Helpers (neu)
```

---

## pyproject.toml

```toml
[project]
name = "iil-researchfw"
version = "0.1.0"
description = "Platform research framework — search, citations, analysis, export"
requires-python = ">=3.11"

dependencies = [
    "httpx>=0.27,<1",       # HTTP (ersetzt requests)
    "pydantic>=2.0,<3",     # Validierung
]

[project.optional-dependencies]
academic = []
# academic_search_service nutzt nur stdlib xml + requests — schon in httpx abgedeckt

scraping = [
    "beautifulsoup4>=4.12",
    "playwright>=1.40",
]

export = [
    "python-docx>=1.1",     # DOCX-Export
    "markdown>=3.5",        # Markdown-Rendering
]

travel = []  # contrib/travel.py hat keine extra Deps

all = [
    "iil-researchfw[scraping,export,travel]",
]
```

---

## Migration: requests → httpx

Beide Services (`citation_service.py`, `academic_search_service.py`) nutzen `requests.Session`.
In iil-researchfw wird auf `httpx` umgestellt (bereits Platform-Standard in requirements/base.txt).

```python
# Vorher
import requests
session = requests.Session()
response = session.get(url, timeout=10)

# Nachher
import httpx
client = httpx.Client(timeout=10.0)
response = client.get(url)
```

---

## Konsumenten und ihr Benefit

| Repo | Nutzt | Konkreter Nutzen |
|---|---|---|
| **bfagent** | `citations`, `search.academic`, `search.brave`, `analysis.summary` | Direkte Ablösung der eigenen Services |
| **travel-beat** | `search.brave`, `contrib.travel` | Orte-Research, POI-Suche, Aktivitäten |
| **weltenhub** | `search.brave`, `contrib.worldbuilding` | Historische Fakten, Kulturen, Geographie |
| **pptx-hub** | `search.brave`, `analysis.summary` | Content-Research für Präsentationen |
| **research-hub** | alle Module | Django-Layer darüber |

---

## contrib/travel.py — Scope

Helper-Klassen für travel-beat und research-hub:

```python
class TravelResearchHelper:
    """High-level API für Reise-Research."""
    
    def search_destination(self, city: str, country: str) -> dict:
        """Fakten, POIs, Aktivitäten für ein Reiseziel."""
    
    def search_activities(self, location: str, category: str = "all") -> list[dict]:
        """Aktivitäten an einem Ort (Sport, Kultur, Essen, Natur)."""
    
    def research_local_culture(self, country: str) -> dict:
        """Lokale Kultur, Sitten, Bräuche."""
    
    def get_travel_facts(self, destination: str) -> dict:
        """Praktische Reisetipps (Visum, Währung, Klima, Sprache)."""
```

---

## Implementierungsreihenfolge v0.1.0

```
Phase 1 — Core (Woche 1)
[ ] Repo achimdehnert/researchfw erstellen
[ ] pyproject.toml mit iil-researchfw
[ ] citations/formatter.py (1:1 aus bfagent, requests→httpx)
[ ] search/academic.py (requests→httpx)
[ ] search/brave.py (Django-Abhängigkeit entfernen)
[ ] core/models.py + core/service.py
[ ] Tests (>80% Coverage)
[ ] CI-Pipeline
[ ] PyPI publish v0.1.0

Phase 2 — Analysis + Export (Woche 2)
[ ] analysis/summary.py (LLM-agnostisch via Protocol)
[ ] analysis/relevance.py (neu)
[ ] export/service.py (Protocol-Interface)
[ ] contrib/travel.py
[ ] PyPI publish v0.2.0

Phase 3 — bfagent Migration (Woche 3)
[ ] bfagent requirements: iil-researchfw>=0.1.0
[ ] bfagent/apps/research/services/ auf iil-researchfw umstellen
[ ] bfagent-spezifische Logik isolieren

Phase 4 — Consumer-Repos (Woche 4)
[ ] travel-beat: iil-researchfw[travel]
[ ] weltenhub: iil-researchfw
[ ] pptx-hub: iil-researchfw
```

---

## Referenzen

- [ADR-104: Research Hub + iil-researchfw](ADR-104-research-hub-iil-researchfw.md)
- [ADR-100: iil-testkit](ADR-100-iil-testkit-shared-test-factory-package.md) — analoges Package-Modell
- `bfagent/apps/research/services/citation_service.py` — 710 Zeilen, produktiv
- `bfagent/apps/research/services/academic_search_service.py` — 632 Zeilen, arXiv + Semantic Scholar + PubMed + OpenAlex
- `bfagent/apps/research/services/brave_search_service.py` — 274 Zeilen, Brave Search API
- `bfagent/apps/research/services/ai_summary_service.py` — 261 Zeilen, LLM-Summary
- `bfagent/apps/research/services/research_service.py` — 300 Zeilen, Orchestrator
- `bfagent/apps/research/services/export_service.py` — 329 Zeilen, Markdown/LaTeX/DOCX
