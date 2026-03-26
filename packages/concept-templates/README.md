# iil-concept-templates

Shared schemas, frameworks and extraction for structured concept templates.

**ADR-147** — see `docs/adr/ADR-147-v2-concept-templates-package.md`

## Installation

```bash
# Core (schemas, frameworks, registry, validators, export)
pip install iil-concept-templates

# With PDF extraction
pip install iil-concept-templates[pdf]

# With LLM analysis (via outlinefw)
pip install iil-concept-templates[llm]

# Everything
pip install iil-concept-templates[full]
```

## Quick Start

```python
from concept_templates import ConceptScope, ConceptTemplate
from concept_templates.registry import get_framework, list_frameworks
from concept_templates.export import to_markdown

# List available frameworks
frameworks = list_frameworks()
# {'brandschutz_mbo': ..., 'exschutz_trgs720': ..., 'ausschreibung_vob': ...}

# Get a specific framework
template = get_framework("brandschutz_mbo")

# Export as Markdown
print(to_markdown(template))

# Register a custom framework
from concept_templates.registry import register_framework

custom = ConceptTemplate(
    name="Mein Konzept",
    scope=ConceptScope.BRANDSCHUTZ,
    framework="custom_bs",
)
register_framework("custom_bs", custom)
```

## Built-in Frameworks

| Key | Name | Scope | Sections |
|-----|------|-------|----------|
| `brandschutz_mbo` | Brandschutzkonzept §14 MBO | brandschutz | 6 |
| `exschutz_trgs720` | Explosionsschutzkonzept TRGS 720ff | explosionsschutz | 7 |
| `ausschreibung_vob` | Ausschreibung nach VOB/A | ausschreibung | 8 |

## File Validation

```python
from concept_templates.validators import validate_upload_file, FileValidationError

try:
    validate_upload_file("plan.pdf", size_bytes=1_000_000)
except FileValidationError as e:
    print(f"Invalid: {e}")
```

Allowed: `.pdf`, `.docx`, `.doc`, `.xlsx`, `.xls`, `.dxf`, `.dwg`, `.jpg`, `.jpeg`, `.png`, `.tiff`, `.txt`, `.csv`
Max size: 50 MB

## Development

```bash
pip install -e ".[dev]"
pytest -v --cov=concept_templates
ruff check .
```
