# iil-doc-templates

Reusable Django document template system — create, edit, fill templates with PDF extraction and LLM prefill.

## Installation

```bash
pip install iil-doc-templates
```

With optional dependencies:
```bash
pip install iil-doc-templates[pdf]   # pdfplumber for PDF extraction
pip install iil-doc-templates[llm]   # iil-aifw for LLM prefill
pip install iil-doc-templates[all]   # everything
```

## Quick Start

```python
# settings.py
INSTALLED_APPS = [
    ...
    "doc_templates",
]

# urls.py
path("doc-templates/", include("doc_templates.urls")),
```

Then run migrations:
```bash
python manage.py migrate doc_templates
```

## Features

- **DocumentTemplate** — Reusable document templates with JSON structure (sections + fields)
- **DocumentInstance** — Filled-out documents based on templates
- **PDF Upload** — Extract structure from PDF using `iil-concept-templates`
- **Interactive Editor** — Drag & drop sections, CRUD fields, table columns
- **LLM Prefill** — AI-powered field completion via `iil-aifw`
- **PDF Export** — Generate PDF from filled documents via `concept_templates.document_renderer`
- **Multi-Tenant** — All queries filter by `tenant_id`

## Architecture

```
iil-concept-templates (Pure Python)      iil-doc-templates (Django)
├── Pydantic Schemas                     ├── Django Models
├── PDF Structure Extraction     ──►     ├── CRUD Views + URLs
├── Analysis, Prefill, Export            ├── HTML Templates (6)
└── No Django dependency                 ├── Admin Integration
                                         └── Uses concept_templates internally
```

## Field Types

| Type | Description |
|------|-------------|
| `textarea` | Multi-line text (default) |
| `text` | Single-line text |
| `number` | Numeric input |
| `date` | Date picker |
| `boolean` | Yes/No toggle |
| `table` | Table with configurable columns |

## URL Patterns

| URL | View | Description |
|-----|------|-------------|
| `/` | `template-list` | List all templates + instances |
| `/create/` | `template-create` | Create empty template |
| `/upload/` | `template-upload` | Create template from PDF |
| `/<pk>/edit/` | `template-edit` | Interactive template editor |
| `/<pk>/delete/` | `template-delete` | Delete template |
| `/<pk>/instance/create/` | `instance-create` | Create document from template |
| `/instance/<pk>/edit/` | `instance-edit` | Edit document fields |
| `/instance/<pk>/delete/` | `instance-delete` | Delete document |
| `/instance/<pk>/prefill/` | `instance-prefill` | LLM prefill endpoint |
| `/instance/<pk>/pdf/` | `instance-pdf` | PDF export |

## Dependencies

- **Required**: Django ≥ 4.2, iil-concept-templates ≥ 0.4.0
- **Optional**: pdfplumber (PDF extraction), iil-aifw (LLM prefill)
