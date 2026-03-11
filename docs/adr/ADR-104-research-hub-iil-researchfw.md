---
status: proposed
date: 2026-03-07
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
related: [ADR-105-iil-researchfw-extraction-plan.md]
---

# ADR-104: Research Hub und iil-researchfw — Zentralisierung der Research-Infrastruktur

---

## Kontext und Problemstellung

Research-Funktionalität ist derzeit in `bfagent/apps/research` implementiert und über `control-center.iil.pet/research-hub/` erreichbar. Die Plattform umfasst mittlerweile 25+ Repos, von denen mehrere eigenständigen Research-Bedarf haben:

- **bfagent**: Buchrecherche (Fakten, Quellen, akademische Zitate)
- **travel-beat**: Reise-Research (Orte, POIs, Reiseinformationen, Aktivitäten)
- **weltenhub**: Weltenbau-Research (historische Fakten, Geographie, Kulturen)
- **wissenschaftliches Schreiben**: Paper-Research, Literaturrecherche, Zitationsverwaltung
- **Allgemein**: Web Scraping, generische Suche, Faktenprüfung

Die aktuelle Lösung ist **bfagent-spezifisch** und nicht wiederverwendbar. Duplikation droht, wenn jedes Repo eigene Research-Lösungen implementiert.

---

## Entscheidungstreiber

1. **DRY-Prinzip**: Research-Core-Logik (Quellenverwaltung, Zitationen, Web-Suche, Scraping) soll nicht pro Repo dupliziert werden
2. **Cross-Domain-Bedarf**: travel-beat, weltenhub und bfagent benötigen ähnliche Kernfunktionen
3. **bfagent-Entlastung**: bfagent ist bereits sehr groß (23+ Apps) — weiteres Wachstum erhöht Komplexität
4. **PyPI-Wiederverwendung**: Erfolgsmodell von `iil-testkit` auf Research übertragen
5. **Eigenständiger Betrieb**: Research Hub als unabhängig deploybare Plattform

---

## Betrachtete Optionen

### Option A: Status quo — Research bleibt in bfagent
- Research-Logik verbleibt in `bfagent/apps/research`
- Andere Repos implementieren eigene Lösungen
- **Problem**: Duplikation, bfagent-Kopplung, keine Cross-Repo-Nutzung

### Option B: Direkte Integration in travel-beat
- Travel-Research in travel-beat einbauen
- **Problem**: Kein Cross-Repo-Nutzen, falsche Zuordnung

### Option C: research-hub (neues Django-Repo) + iil-researchfw (PyPI-Package) ✅
- Eigenständiges `research-hub`-Repo als Django-Applikation
- `iil-researchfw` als PyPI-Package für wiederverwendbare Core-Logik
- Andere Repos konsumieren das Package
- **Vorteil**: Klare Trennung, Wiederverwendung, unabhängige Skalierung

---

## Entscheidung

**Option C wird umgesetzt.**

Zweigleisige Architektur:
1. **`research-hub`** — eigenständiges Django-Repo mit UI, API und allen Research-Domains
2. **`iil-researchfw`** — PyPI-Package mit der wiederverwendbaren Core-Logik

---

## Architektur

### iil-researchfw (PyPI Package)

Enthält die domainunabhängige Research-Kernlogik. **Kein Django erforderlich** — pure Python.

```
iil_researchfw/
├── __init__.py
├── models/              # Dataclasses (nicht Django-Models)
│   ├── source.py        # ResearchSource, SourceType
│   ├── finding.py       # ResearchFinding, FindingType
│   └── result.py        # ResearchResult
├── search/              # Suchprovider-Abstraktionen
│   ├── base.py          # BaseSearchProvider (ABC)
│   ├── brave.py         # BraveSearchProvider (aus bfagent extrahiert)
│   ├── academic.py      # AcademicSearchProvider (Semantic Scholar, arXiv)
│   └── scraping.py      # WebScrapingProvider (BeautifulSoup/Playwright)
├── citations/           # Zitationsverwaltung
│   ├── formatter.py     # APA, MLA, Chicago, IEEE, Harvard (aus bfagent extrahiert)
│   └── bibtex.py        # BibTeX-Export
├── analysis/            # Analyse-Utilities
│   ├── relevance.py     # Relevanz-Scoring
│   ├── summary.py       # AI-Summary-Integration (LLM-agnostisch)
│   └── deduplication.py # Quellen-Deduplizierung
├── contrib/             # Optionale Domain-Extensions
│   ├── travel.py        # Travel-Research-Helpers
│   ├── academic.py      # Scientific-Writing-Helpers
│   └── worldbuilding.py # Weltenbau-Research-Helpers
└── py.typed
```

**Installation:**
```bash
pip install iil-researchfw                    # Core
pip install iil-researchfw[brave]             # + Brave Search
pip install iil-researchfw[academic]          # + arXiv/Semantic Scholar
pip install iil-researchfw[scraping]          # + BeautifulSoup/Playwright
pip install iil-researchfw[travel]            # + Travel-Contrib
pip install iil-researchfw[all]               # Alles
```

### research-hub (Django Repo)

Eigenständiges Django-Repo, deployed unter `research.iil.pet`.

```
research-hub/
├── apps/
│   ├── core/              # Basisfunktionalität, Django-Models, gemeinsame Views
│   ├── general_research/  # Allgemeiner Research (Quick Facts, Deep Dive)
│   ├── scientific/        # Wissenschaftlicher Research (Papers, Zitate, Reviews)
│   ├── travel_research/   # Reise-Research (Orte, POIs, Aktivitäten, Wetter)
│   ├── web_scraping/      # Scraping-Engine, Crawler-Verwaltung
│   └── api/               # REST API für andere Repos (bfagent, travel-beat etc.)
├── requirements.txt
├── requirements-test.txt  # iil-testkit>=0.2.0
└── docker-compose.prod.yml
```

### Integration in bestehende Repos

Andere Repos konsumieren `iil-researchfw` direkt (kein API-Call nötig für einfache Fälle):

```python
# In travel-beat
from iil_researchfw.search.brave import BraveSearchProvider
from iil_researchfw.contrib.travel import TravelResearchHelper

# In bfagent
from iil_researchfw.citations.formatter import CitationFormatter
from iil_researchfw.search.academic import AcademicSearchProvider

# In weltenhub
from iil_researchfw.contrib.worldbuilding import WorldbuildingResearchHelper
```

Für komplexe Research-Workflows: REST API von `research-hub`.

---

## Migrationsstrategie aus bfagent

### Phase 1: iil-researchfw aufbauen (Code-Extraktion)

| bfagent Quelle | iil-researchfw Ziel | Anpassung |
|---|---|---|
| `services/brave_search_service.py` | `search/brave.py` | Django-Abhängigkeiten entfernen |
| `services/academic_search_service.py` | `search/academic.py` | Django-Abhängigkeiten entfernen |
| `models.py` (ResearchSource) | `models/source.py` | Django-Model → Dataclass |
| `models.py` (ResearchFinding) | `models/finding.py` | Django-Model → Dataclass |
| `services/citation_service.py` | `citations/formatter.py` | Direkt übertragbar |
| `services/ai_summary_service.py` | `analysis/summary.py` | LLM-agnostisch machen |
| `services/vector_store_service.py` | `analysis/relevance.py` | Anpassen |

**Was NICHT migriert wird:**
- Django-Models (ResearchProject, ResearchResult, ResearchTemplate) — bleiben in research-hub
- Views, URLs, Admin — bleiben in research-hub
- bfagent-spezifische Agents/Handlers — bleiben in bfagent

### Phase 2: research-hub Django-Repo erstellen
- Neues Repo `research-hub` mit Standard-Platform-Struktur (ADR-022)
- Django-Models aus bfagent übertragen (ResearchProject, ResearchSource etc.)
- REST API für andere Repos
- Deployment unter `research.iil.pet`

### Phase 3: bfagent migrieren
- `bfagent/apps/research/services/` auf `iil-researchfw` umstellen
- bfagent-spezifische Logik (Outline-Generator, Paper-Frameworks) bleibt in bfagent
- bfagent nutzt `research-hub` API für generische Operationen

### Phase 4: Andere Repos einbinden
- travel-beat: `iil-researchfw[travel]` in requirements
- weltenhub: `iil-researchfw[all]` in requirements
- Neue Repos starten direkt mit `iil-researchfw`

---

## Was bleibt in bfagent

Nicht alles aus `bfagent/apps/research` wird migriert. Buchspezifische Logik verbleibt:

- `agents/outline_agents.py` — Buchgliederungs-Agent
- `services/outline_generator.py` — Buchgliederungs-Generator
- `services/paper_frameworks.py` — Akademische Paper-Frameworks (32KB, sehr buchspezifisch)
- Handlers und MCP-Tools für Buchworkflow

---

## PyPI Package: iil-researchfw

**Repo:** `achimdehnert/researchfw`  
**Package:** `iil-researchfw`  
**Versionierung:** Semantic Versioning, startet mit `0.1.0`

### Abhängigkeiten (Core)
```toml
dependencies = [
    "httpx>=0.27",          # HTTP-Requests
    "pydantic>=2.0",        # Datenvalidierung
]

[project.optional-dependencies]
brave = ["httpx>=0.27"]
academic = ["httpx>=0.27", "xmltodict>=0.13"]
scraping = ["beautifulsoup4>=4.12", "playwright>=1.40"]
travel = []  # nur contrib-Helpers, keine extra Deps
all = ["iil-researchfw[brave,academic,scraping,travel]"]
```

### Verhältnis zu iil-testkit

| Aspekt | iil-testkit | iil-researchfw |
|---|---|---|
| Zweck | Test-Infrastruktur | Research-Infrastruktur |
| Django-Abhängigkeit | Optional (fixtures) | Nein (Core ist Django-frei) |
| Contrib-Pattern | `contrib/tenants` | `contrib/travel`, `contrib/academic` |
| Zielgruppe | Alle Platform-Repos | Repos mit Research-Bedarf |

---

## Konsequenzen

### Positiv
- **Einheitliche Research-API** über alle Repos
- **bfagent entlastet** — Research-Core ausgelagert
- **travel-beat profitiert sofort** von Travel-Research-Helpers
- **Erweiterbar** — neue Domains via `contrib/`-Pattern
- **Testbar** — pure Python Core ist einfach zu testen (kein Django nötig)
- **PyPI-Verteilung** — Erfolgsmodell iil-testkit wiederholt

### Negativ / Risiken
- **Migrationsaufwand** — bfagent/apps/research ist produktiv, Migration braucht Zeit
- **Weiteres Repo** — 26. Repo in der Plattform (Managementaufwand)
- **API-Overhead** — bei komplexen Workflows müssen andere Repos ggf. research-hub API aufrufen

### Mitigation
- Migration ist **inkrementell** — bfagent bleibt vollständig funktionsfähig während der Migration
- research-hub startet **fresh** (kein Big-Bang-Migration)
- iil-researchfw v0.1.0 enthält nur extrahierten, bewährten Code

---

## Implementierungsreihenfolge

```
[x] ADR-104 schreiben (dieser ADR)
[ ] Phase 1: researchfw-Repo erstellen + iil-researchfw v0.1.0
    [ ] brave.py aus bfagent extrahieren
    [ ] academic.py aus bfagent extrahieren
    [ ] citations/formatter.py aus bfagent extrahieren
    [ ] models/source.py + finding.py als Dataclasses
    [ ] CI + PyPI publish
[ ] Phase 2: research-hub Django-Repo
    [ ] Standard-Platform-Struktur (ADR-022)
    [ ] Django-Models aus bfagent portieren
    [ ] REST API (research.iil.pet)
    [ ] Deployment
[ ] Phase 3: bfagent auf iil-researchfw umstellen
[ ] Phase 4: travel-beat + weltenhub einbinden
```

---

## Referenzen

- [ADR-100: iil-testkit](ADR-100-iil-testkit-shared-test-factory-package.md) — Analoges PyPI-Package-Modell
- [ADR-022: Platform Consistency Standard](ADR-022-platform-consistency-standard.md) — Repo-Struktur
- [bfagent/apps/research/models.py](https://github.com/achimdehnert/bfagent/blob/main/apps/research/models.py) — Bestehendes Datenmodell
- [bfagent/apps/research/services/](https://github.com/achimdehnert/bfagent/tree/main/apps/research/services) — Bestehende Services
