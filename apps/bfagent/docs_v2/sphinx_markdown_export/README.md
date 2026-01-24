# Sphinx Markdown Export

Konvertiert komplette Sphinx-Dokumentationsprojekte in eine einzelne Markdown-Datei.

## Features

- ✅ **Vollständige Konvertierung** - Alle Sphinx-Features werden unterstützt
- ✅ **Toctree-Reihenfolge** - Dokumente werden in der richtigen Reihenfolge kombiniert
- ✅ **Interne Links** - Werden automatisch zu Anchors konvertiert
- ✅ **Django-Integration** - Admin-Actions und Management Command
- ✅ **Standalone CLI** - Funktioniert auch ohne Django
- ✅ **Autodoc-Support** - Extrahiert Docstrings aus Python-Modulen
- ✅ **Intersphinx** - Links zu externen Dokumentationen

## Unterstützte Sphinx-Features

| Feature | Beschreibung | Markdown-Output |
|---------|--------------|-----------------|
| Admonitions | `.. note::`, `.. warning::`, etc. | Blockquotes mit Emoji |
| Code-Blocks | `.. code-block:: python` | Fenced Code-Blocks |
| Cross-References | `:ref:`, `:doc:`, `:class:` | Anchor-Links |
| Intersphinx | Externe Dokumentations-Links | URLs |
| Math | `:math:` und `.. math::` | LaTeX `$...$` |
| Images/Figures | `.. image::`, `.. figure::` | Markdown Images |
| Toctree | Inhaltsverzeichnis | Strukturiertes TOC |
| Autodoc | Docstring-Extraktion | API-Referenz |

## Installation

```bash
# Basis-Installation
pip install sphinx

# Optional: Verbesserte Qualität durch sphinx-markdown-builder
pip install sphinx-markdown-builder
```

### Django-Installation

```python
# settings.py
INSTALLED_APPS = [
    ...
    'sphinx_markdown_export',
]
```

```bash
# Migrationen
python manage.py makemigrations sphinx_markdown_export
python manage.py migrate
```

## Usage

### Standalone CLI

```bash
# Einfacher Export
python -m sphinx_markdown_export.cli /path/to/docs -o complete.md

# Mit Titel
python -m sphinx_markdown_export.cli ./docs --title "API Documentation"

# Mit API-Referenz aus Python-Source
python -m sphinx_markdown_export.cli ./docs --python-src src/mymodule

# Output auf stdout
python -m sphinx_markdown_export.cli ./docs --stdout | head -50

# Mit Intersphinx-Mapping
python -m sphinx_markdown_export.cli ./docs \
    --intersphinx python=https://docs.python.org/3 \
    --intersphinx django=https://docs.djangoproject.com/en/stable
```

### Python API

```python
from sphinx_markdown_export import sphinx_to_markdown

# Einfacher Export
success, path, metadata = sphinx_to_markdown(
    '/path/to/docs',
    output_path='complete.md',
    title="My Documentation"
)

if success:
    print(f"Exportiert: {path}")
    print(f"Seiten: {metadata.pages_count}")
    print(f"Wörter: {metadata.word_count}")
```

### Erweiterte Python API

```python
from sphinx_markdown_export import (
    SphinxToMarkdownService,
    ExportConfig,
)

config = ExportConfig(
    title="My Documentation",
    include_toc=True,
    include_api_reference=True,
    intersphinx_mapping={
        'python': 'https://docs.python.org/3',
        'django': 'https://docs.djangoproject.com/en/stable',
    },
    python_source_paths=['src/mymodule', 'src/utils'],
)

service = SphinxToMarkdownService(
    source_path=Path('/path/to/docs'),
    config=config
)

success, output_path, metadata = service.export()
```

### Django Management Command

```bash
# Export eines Projekts
python manage.py sphinx_to_markdown myproject -o docs/complete.md

# Export mit Record in Datenbank
python manage.py sphinx_to_markdown myproject --save-record

# Export aller aktiven Projekte
python manage.py sphinx_to_markdown all -o /output/dir/

# Direkt von Pfad (ohne Datenbank)
python manage.py sphinx_to_markdown --path /path/to/docs --title "Docs"
```

### Django Admin

1. Navigiere zu **Admin → Dokumentationsprojekte**
2. Erstelle ein neues Projekt mit dem Sphinx Source-Pfad
3. Wähle das Projekt aus und nutze die Action **"📄 Exportiere als Single Markdown"**

## Projekt-Struktur

```
sphinx_markdown_export/
├── __init__.py              # Package exports
├── apps.py                  # Django app config
├── models.py                # Django models (Project, Export)
├── admin.py                 # Admin configuration mit Actions
├── export_service.py        # Haupt-Export-Service
├── sphinx_converter.py      # RST→MD Feature-Konverter
├── cli.py                   # Standalone CLI
└── management/
    └── commands/
        └── sphinx_to_markdown.py  # Django management command
```

## Konfiguration (Django)

### DocumentationProject Model

| Feld | Beschreibung |
|------|--------------|
| `name` | Projektname |
| `slug` | URL-freundlicher Bezeichner |
| `source_path` | Relativer Pfad zum docs/ Verzeichnis |
| `intersphinx_mapping` | JSON: `{"python": "https://..."}` |
| `python_source_paths` | JSON: `["src/module", ...]` |
| `include_toc` | Inhaltsverzeichnis generieren |
| `include_api_reference` | API-Referenz aus Docstrings |

### ExportConfig

```python
@dataclass
class ExportConfig:
    title: Optional[str] = None           # Dokumenttitel
    include_toc: bool = True              # Inhaltsverzeichnis
    include_metadata: bool = True         # Header mit Datum/Quelle
    include_api_reference: bool = True    # Docstring-Extraktion
    intersphinx_mapping: dict = {}        # Externe Dokumentationen
    python_source_paths: list = []        # Pfade für Autodoc
    heading_offset: int = 0               # Heading-Levels erhöhen
    add_horizontal_rules: bool = True     # Trennlinien zwischen Docs
```

## Export-Metadaten

```python
@dataclass
class ExportMetadata:
    pages_count: int        # Anzahl der kombinierten Dokumente
    word_count: int         # Wörter im Gesamt-Dokument
    char_count: int         # Zeichen
    duration_seconds: float # Export-Dauer
    features_used: list     # ['sphinx-markdown-builder', 'autodoc', ...]
    warnings: list          # Warnungen während des Exports
    errors: list            # Fehler (falls nicht erfolgreich)
```

## Beispiel-Output

```markdown
# My Documentation

> 📚 Generiert am 2025-01-23 14:30
> 📁 Quelle: `/path/to/docs`

---

## 📑 Inhaltsverzeichnis

- [Introduction](#introduction)
- [Installation](#installation)
- [API Reference](#api-reference)

---

# Introduction

Welcome to the documentation...

---

# Installation

## Requirements

> 📝 **Note**
>
> Python 3.10 or higher is required.

```bash
pip install mypackage
```

---

# API Reference

## Modul `mymodule`

### class `MyClass(BaseClass)`

A sample class that does something.

**Attribute:**
- `name`: str
- `value`: int

**Methoden:**

#### `process(data: dict) -> Result`

Process the input data.

**Parameter:**
- `data` (dict): The input data to process

**Rückgabe:**
- `Result`: The processed result
```

## Abhängigkeiten

### Erforderlich
- Python 3.9+
- Django 4.0+ (nur für Django-Integration)

### Optional (verbessert Qualität)
- `sphinx` - Für Projekt-Validierung
- `sphinx-markdown-builder` - Native Sphinx→MD Konvertierung

## License

MIT License - siehe LICENSE Datei.

## Author

BF Agent Framework
