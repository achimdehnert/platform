# ADR-020: Dokumentationsstrategie — Sphinx, DB-driven, ADR-basiert

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-06 |
| **Author** | Achim Dehnert |
| **Scope** | platform (all repos) |
| **Related** | ADR-015 (Governance), ADR-017 (DDL), ADR-018 (Weltenhub) |

---

## 1. Executive Summary

Einheitliche Dokumentationsstrategie für das gesamte BF Agent Ecosystem,
basierend auf **Sphinx** als Engine, **PostgreSQL** als Datenquelle und
**ADRs** als strukturgebendes Element.

**Kernidee:** Dokumentation wird nicht nur in `.rst`/`.md` Dateien gepflegt,
sondern zusätzlich aus der Datenbank generiert — ADRs, Business Cases,
Use Cases, Lookup-Tabellen und API-Schemas werden automatisch zu
Sphinx-Dokumentation konvertiert.

---

## 2. Problem Statement

| Problem | Impact |
|---------|--------|
| Doku verstreut über 5+ Repos (README, docs/, concepts/) | Kein Single Point of Truth |
| ADRs nur als Markdown-Dateien, nicht maschinenlesbar | Keine automatische Verlinkung |
| Governance-Daten (BC, UC, ADR) in DB, aber nicht in Doku | Doppelpflege nötig |
| Lookup-Tabellen (lkp_*) undokumentiert | Entwickler müssen DB abfragen |
| API-Doku (DRF Spectacular) separat von Arch-Doku | Kein Gesamtbild |
| Keine versionierte, buildbare Doku | Kein Review-Prozess für Doku |

---

## 3. Strategie

### 3.1 Drei Säulen

```text
┌─────────────────────────────────────────────────────────────────┐
│                    SPHINX DOCUMENTATION HUB                      │
├─────────────────┬──────────────────────┬────────────────────────┤
│   Säule 1       │    Säule 2           │    Säule 3             │
│   CODEBASE      │    DATABASE          │    ADR / GOVERNANCE    │
│                 │                      │                        │
│ • autodoc       │ • lkp_* Tabellen     │ • dom_adr → .rst       │
│ • viewcode      │ • DB-Schema → ERD    │ • dom_business_case    │
│ • napoleon      │ • Seed Data Docs     │ • dom_use_case         │
│ • type hints    │ • Enrichment Actions │ • Review History       │
│ • Django models │ • Governance Lookups │ • Status Tracking      │
└─────────────────┴──────────────────────┴────────────────────────┘
```

### 3.2 Säule 1: Codebase-Dokumentation (autodoc)

**Quelle:** Python Docstrings, Type Hints, Django Models

```python
# Automatisch aus Code generiert via sphinx.ext.autodoc
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',      # Google-style Docstrings
    'sphinx.ext.viewcode',      # Link zu Source
    'sphinx.ext.intersphinx',   # Cross-repo Links
    'sphinxcontrib.django',     # Django Model Dokumentation
]
```

**Generiert:**
- Model-Referenz (alle Felder, Constraints, Indices)
- Service-Referenz (enrich(), apply_preview(), etc.)
- View-Referenz (URL patterns, HTTP methods, permissions)
- Mixin-Referenz (TenantRequiredMixin, etc.)

### 3.3 Säule 2: Database-driven Dokumentation

**Quelle:** PostgreSQL Tabellen (live oder Dump)

#### Management Command: `generate_db_docs`

```python
# platform/packages/sphinx-export/management/commands/generate_db_docs.py

class Command(BaseCommand):
    """
    Generiert Sphinx .rst Dateien aus der Datenbank.

    Usage:
        python manage.py generate_db_docs --output docs/source/database/
    """

    def handle(self, *args, **options):
        self.generate_lookup_docs()      # lkp_* → lookup_tables.rst
        self.generate_schema_docs()      # pg_catalog → schema.rst
        self.generate_enrichment_docs()  # lkp_enrichment_action → enrichment.rst
        self.generate_governance_docs()  # dom_* → governance/
```

**Generierte Dateien:**

| Datei | Quelle | Inhalt |
|-------|--------|--------|
| `database/lookup_tables.rst` | `lkp_*` Tabellen | Alle Lookups mit Codes, Namen, Beschreibungen |
| `database/schema.rst` | `pg_catalog` | ER-Diagramm, Tabellen, Spalten, FKs |
| `database/enrichment_actions.rst` | `lkp_enrichment_action` | Alle AI-Aktionen mit Prompts |
| `governance/business_cases.rst` | `dom_business_case` | Alle BCs mit Status, Priority |
| `governance/use_cases.rst` | `dom_use_case` | Alle UCs mit Flows |
| `governance/adrs.rst` | `dom_adr` | Alle ADRs aus DB |

#### Beispiel: Lookup-Tabelle → RST

```rst
Lookup: Genre (lkp_genre)
=========================

.. list-table::
   :header-rows: 1
   :widths: 20 40 20 20

   * - Code
     - Name (DE)
     - Icon
     - Active
   * - fantasy
     - Fantasy
     - bi-stars
     - ✅
   * - scifi
     - Science Fiction
     - bi-rocket
     - ✅
```

### 3.4 Säule 3: ADR/Governance-Dokumentation

**Quelle:** `platform.dom_adr` + Markdown-Dateien in `docs/adr/`

#### Bidirektionaler Sync

```text
Markdown (docs/adr/*.md)
        ↕  sync_service.py
Database (platform.dom_adr)
        ↓  generate_db_docs
Sphinx RST (docs/source/governance/adrs.rst)
        ↓  sphinx-build
HTML (docs/_build/html/)
```

**Features:**
- ADRs aus DB werden zu Sphinx-Seiten mit Metadaten-Tabelle
- Automatische Verlinkung: ADR → Use Cases → Business Cases
- Status-Badge generierung (Proposed, Accepted, Deprecated)
- Dependency Graph (welche ADRs referenzieren welche)

---

## 4. Projektstruktur

```text
platform/
├── docs/
│   ├── source/                    # Sphinx source
│   │   ├── conf.py                # Master config
│   │   ├── index.rst              # Root toctree
│   │   │
│   │   ├── architecture/          # Säule 1: Codebase
│   │   │   ├── weltenhub.rst      # Auto-generated from weltenhub/
│   │   │   ├── bfagent.rst
│   │   │   ├── travel-beat.rst
│   │   │   └── models/            # autodoc model references
│   │   │
│   │   ├── database/              # Säule 2: DB-driven
│   │   │   ├── schema.rst         # Generated from pg_catalog
│   │   │   ├── lookup_tables.rst  # Generated from lkp_*
│   │   │   ├── enrichment.rst     # Generated from enrichment actions
│   │   │   └── _generated/        # Auto-generated files (gitignored)
│   │   │
│   │   ├── governance/            # Säule 3: ADR/DDL
│   │   │   ├── overview.rst
│   │   │   ├── business_cases.rst # Generated from dom_business_case
│   │   │   ├── use_cases.rst      # Generated from dom_use_case
│   │   │   ├── adrs.rst           # Generated from dom_adr
│   │   │   └── reviews.rst        # Generated from dom_review
│   │   │
│   │   ├── api/                   # API Reference
│   │   │   ├── weltenhub.rst      # From DRF Spectacular schema
│   │   │   └── endpoints.rst
│   │   │
│   │   └── deployment/            # Ops documentation
│   │       ├── infrastructure.rst
│   │       ├── docker.rst
│   │       └── monitoring.rst
│   │
│   ├── Makefile                   # sphinx-build shortcuts
│   ├── requirements.txt           # Sphinx dependencies
│   └── _build/                    # Build output (gitignored)
│
├── packages/
│   └── sphinx-export/             # Existing package (enhanced)
│       ├── management/commands/
│       │   ├── generate_db_docs.py    # NEW: DB → RST generator
│       │   ├── sync_adrs.py           # NEW: ADR sync (MD ↔ DB)
│       │   └── sphinx_to_markdown.py  # Existing
│       └── ...
```

---

## 5. conf.py (Master Configuration)

```python
# docs/source/conf.py

project = 'BF Agent Platform'
copyright = '2026, Achim Dehnert'
author = 'Achim Dehnert'
release = '1.0.0'

extensions = [
    # Säule 1: Codebase
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinxcontrib.django',

    # Säule 2: Database
    'sphinxcontrib.plantuml',       # ER-Diagramme
    'sphinx_tabs.tabs',             # Tabbed content

    # Säule 3: ADR/Governance
    'myst_parser',                  # Markdown support
    'sphinx.ext.todo',              # TODO tracking
    'sphinx_design',                # Cards, grids, badges

    # Export
    'sphinx_markdown_builder',      # MD export
]

# MyST: Allow Markdown files
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "tasklist",
    "fieldlist",
]

# Theme
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
}

# Intersphinx: Cross-repo links
intersphinx_mapping = {
    'django': ('https://docs.djangoproject.com/en/5.0/', None),
    'python': ('https://docs.python.org/3/', None),
}

# Django settings for autodoc
import django
import os
os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE', 'config.settings.base'
)
django.setup()

# Napoleon: Google-style docstrings
napoleon_google_docstring = True
napoleon_include_init_with_doc = True
napoleon_use_param = True
```

---

## 6. Build Pipeline

### 6.1 Lokaler Build

```bash
# 1. Generate DB-driven docs
python manage.py generate_db_docs --output docs/source/database/
python manage.py sync_adrs --direction db-to-rst

# 2. Build Sphinx
cd docs && make html

# 3. Preview
python -m http.server -d _build/html 8090
```

### 6.2 CI/CD (GitHub Actions)

```yaml
name: Documentation
on:
  push:
    branches: [main]
    paths: ['docs/**', 'apps/**/models.py', 'apps/**/views.py']

jobs:
  build-docs:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: platform
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r docs/requirements.txt
      - run: python manage.py migrate
      - run: python manage.py loaddata seed_lookups
      - run: python manage.py generate_db_docs
      - run: python manage.py sync_adrs --direction db-to-rst
      - run: cd docs && make html
      - uses: peaceiris/actions-gh-pages@v4
        with:
          publish_dir: docs/_build/html
```

### 6.3 Pre-commit Hook

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: check-docstrings
      name: Check Google-style docstrings
      entry: python -m pydocstyle --convention=google
      language: python
      types: [python]
      files: ^apps/
```

---

## 7. DB-Dokumentation: generate_db_docs Command

### 7.1 Implementierungsplan

```python
# Pseudocode für generate_db_docs

class Command(BaseCommand):
    help = "Generate Sphinx RST from database content"

    def add_arguments(self, parser):
        parser.add_argument('--output', default='docs/source/database/')
        parser.add_argument('--include', nargs='*',
                            default=['lookups', 'schema', 'enrichment', 'governance'])

    def handle(self, *args, **options):
        output = Path(options['output'])
        output.mkdir(parents=True, exist_ok=True)

        if 'lookups' in options['include']:
            self._generate_lookups(output)
        if 'schema' in options['include']:
            self._generate_schema(output)
        if 'enrichment' in options['include']:
            self._generate_enrichment(output)
        if 'governance' in options['include']:
            self._generate_governance(output)

    def _generate_lookups(self, output):
        """Query all lkp_* tables → lookup_tables.rst"""
        from apps.lookups.models import Genre, Mood, ...
        from apps.governance.models import LookupDomain, LookupChoice

        # For each lookup model, generate a table
        for model in [Genre, Mood, ConflictLevel, ...]:
            entries = model.objects.filter(is_active=True)
            rst = self._render_table(model, entries)
            (output / f"lookup_{model._meta.db_table}.rst").write_text(rst)

    def _generate_schema(self, output):
        """Query pg_catalog → schema.rst with PlantUML ERD"""
        from django.apps import apps
        models = apps.get_models()
        # Generate PlantUML entity-relationship diagram
        # Generate table/column reference

    def _generate_enrichment(self, output):
        """Query lkp_enrichment_action → enrichment.rst"""
        from apps.enrichment.models import EnrichmentAction
        actions = EnrichmentAction.objects.filter(is_active=True)
        # Generate action reference with prompts, fields, configs

    def _generate_governance(self, output):
        """Query dom_* → governance/*.rst"""
        from apps.governance.models import BusinessCase, UseCase, ADR
        # Generate BC/UC/ADR pages with status, links, history
```

---

## 8. Vorteile

| Vorteil | Beschreibung |
|---------|-------------|
| **Single Source of Truth** | DB ist die Quelle, Doku wird generiert |
| **Immer aktuell** | CI/CD regeneriert bei jedem Push |
| **Kein Doppelpflege** | Lookups, ADRs, Enrichment-Actions nur in DB pflegen |
| **Versioniert** | Sphinx-Source in Git, Build reproduzierbar |
| **Suchbar** | Sphinx generiert Suchindex |
| **Cross-referenziert** | ADR → UC → BC automatisch verlinkt |
| **Exportierbar** | HTML, PDF, Markdown (via sphinx-export) |
| **Erweiterbar** | Neue DB-Tabellen → neuer Generator |

---

## 9. Dependencies (requirements.txt)

```text
sphinx>=7.0
sphinx-rtd-theme>=2.0
sphinx-design>=0.5
sphinx-tabs>=3.4
sphinx-markdown-builder>=0.6
sphinxcontrib-django>=2.5
sphinxcontrib-plantuml>=0.27
myst-parser>=3.0
pydocstyle>=6.3
```

---

## 10. Implementierungs-Roadmap

| Phase | Aufwand | Beschreibung |
|-------|---------|-------------|
| P1 | 2h | `conf.py` erstellen, Projektstruktur, `make html` lauffähig |
| P2 | 4h | `generate_db_docs` Command (Lookups + Schema) |
| P3 | 3h | ADR-Sync (Markdown ↔ DB ↔ RST) |
| P4 | 2h | autodoc für weltenhub + bfagent Models |
| P5 | 2h | CI/CD Pipeline (GitHub Actions → GitHub Pages) |
| P6 | 1h | Enrichment Actions Docs + API Reference |

**Gesamt: ~14h für vollständige Implementierung**

---

## 11. Decision

**Accepted**: Sphinx als zentrale Doku-Engine mit drei Säulen
(Codebase, Database, Governance). Die bestehende `sphinx-export`
Infrastruktur in `packages/sphinx-export/` wird um `generate_db_docs`
und `sync_adrs` Commands erweitert.
