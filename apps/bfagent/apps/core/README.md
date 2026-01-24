# Core Module - Consolidated Services

Central service layer for the BF Agent Framework providing unified, production-ready implementations.

## Overview

| Service | Description | Location |
|---------|-------------|----------|
| **Handlers** | Unified handler framework | `handlers/` |
| **LLM** | Multi-provider AI integration | `services/llm/` |
| **Cache** | Multi-backend caching | `services/cache/` |
| **Storage** | Unified file storage | `services/storage/` |
| **Export** | Document export (7 formats) | `services/export/` |
| **Extractors** | File content extraction (8 types) | `services/extractors/` |

## Quick Start

### Installation

```python
# settings.py
INSTALLED_APPS = [
    ...
    'apps.core',
]
```

### Usage Examples

```python
# LLM Service
from apps.core.services.llm import LLMService
llm = LLMService()
response = llm.complete("Explain quantum computing")

# Cache Service
from apps.core.services.cache import CacheService
cache = CacheService()
cache.set("user:123", user_data, ttl=3600)

# Storage Service
from apps.core.services.storage import StorageService
storage = StorageService()
path = storage.save("docs/report.pdf", content)

# Export Service
from apps.core.services.export import export_to
result = export_to("docx", markdown_content, "report.docx")

# File Extractors
from apps.core.services.extractors import extract_file
result = extract_file("document.pdf")
print(result.text)
```

---

## Services Reference

### 1. LLM Service (`services/llm/`)

Multi-provider LLM integration with automatic fallback.

**Providers:**
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude 3.5, Claude 3)
- Azure OpenAI
- Local (Ollama)

**Features:**
- Automatic provider fallback
- Response caching
- Token tracking
- Streaming support
- Retry logic with backoff

```python
from apps.core.services.llm import LLMService, LLMConfig

# Basic usage
llm = LLMService()
response = llm.complete("Hello!")

# With config
config = LLMConfig(
    provider="anthropic",
    model="claude-3-5-sonnet-20241022",
    temperature=0.7,
    max_tokens=1000
)
llm = LLMService(config)
response = llm.complete(prompt, system="You are helpful.")

# Streaming
for chunk in llm.stream(prompt):
    print(chunk, end="")
```

### 2. Cache Service (`services/cache/`)

Multi-backend caching with consistent API.

**Backends:**
- Redis (recommended for production)
- In-Memory (development)
- File-based (simple deployments)
- Django Cache (wrapper)

**Features:**
- TTL support
- Key prefixing
- Serialization (JSON, Pickle)
- Cache decorators
- Batch operations

```python
from apps.core.services.cache import CacheService, cached

# Basic operations
cache = CacheService()
cache.set("key", value, ttl=3600)
value = cache.get("key")
cache.delete("key")

# Decorator
@cached(ttl=300, key_prefix="api")
def expensive_api_call(user_id):
    return fetch_data(user_id)

# Batch
cache.set_many({"k1": v1, "k2": v2})
values = cache.get_many(["k1", "k2"])
```

### 3. Storage Service (`services/storage/`)

Unified file storage abstraction.

**Backends:**
- Local filesystem
- AWS S3
- Google Cloud Storage
- Azure Blob Storage

**Features:**
- Consistent API across backends
- Automatic directory creation
- Content type detection
- Signed URLs
- Metadata support

```python
from apps.core.services.storage import StorageService

storage = StorageService()

# Save file
path = storage.save("reports/q4.pdf", content)

# Load file
content = storage.load("reports/q4.pdf")

# Check existence
if storage.exists("reports/q4.pdf"):
    ...

# List files
files = storage.list_files("reports/")

# Delete
storage.delete("reports/old.pdf")

# Get URL (for cloud storage)
url = storage.get_url("reports/q4.pdf")
```

### 4. Export Service (`services/export/`)

Document export with 7 format support.

**Formats:**
| Format | Extension | Library |
|--------|-----------|---------|
| DOCX | .docx | python-docx |
| PDF | .pdf | reportlab |
| EPUB | .epub | ebooklib |
| Markdown | .md | Built-in |
| HTML | .html | Built-in |
| JSON | .json | Built-in |
| CSV | .csv | Built-in |

```python
from apps.core.services.export import (
    export_to, export_markdown, export_pdf,
    BookExporter, BookContent, ChapterContent
)

# Simple export
result = export_to("docx", markdown_content, "report.docx")

# Book export
book = BookContent(
    title="My Novel",
    author="Jane Doe",
    chapters=[
        ChapterContent(number=1, title="Beginning", content="..."),
        ChapterContent(number=2, title="Middle", content="..."),
    ]
)
exporter = BookExporter()
results = exporter.export_all_formats(book)
```

### 5. File Extractors (`services/extractors/`)

Content extraction from 8 file types.

**Supported Types:**
| Type | Extractor | Features |
|------|-----------|----------|
| PDF | PDFExtractor | Text, tables, OCR |
| DOCX | DOCXExtractor | Paragraphs, tables |
| PPTX | PPTXExtractor | Slides, text IDs |
| Excel | ExcelExtractor | Multi-sheet |
| CSV | CSVExtractor | Auto-delimiter |
| JSON | JSONExtractor | Nested data |
| Text/MD | TextExtractor | Frontmatter |
| Images | ImageExtractor | OCR |

```python
from apps.core.services.extractors import (
    extract_file, extract_text, extract_pdf,
    PDFExtractor, PPTXExtractor
)

# Auto-detect and extract
result = extract_file("document.pdf")
print(result.text)
print(f"Pages: {result.page_count}")
print(f"Words: {result.word_count}")

# PDF with OCR
result = extract_pdf("scanned.pdf", ocr=True)

# PowerPoint slides
result = PPTXExtractor().extract("presentation.pptx")
for slide in result.slides:
    print(f"Slide {slide.slide_number}: {slide.title}")
```

---

## Migration Guide

### From Old Imports

Run the migration command:

```bash
# Preview changes
python manage.py migrate_to_core --dry-run

# Apply changes
python manage.py migrate_to_core --apply

# Migrate specific app
python manage.py migrate_to_core --app bfagent --apply
```

### Manual Migration

| Old Import | New Import |
|------------|------------|
| `from apps.bfagent.services.llm_service import ...` | `from apps.core.services.llm import ...` |
| `from apps.bfagent.services.cache_service import ...` | `from apps.core.services.cache import ...` |
| `from apps.bfagent.services.content_storage import ...` | `from apps.core.services.storage import ...` |
| `from apps.bfagent.services.book_export import ...` | `from apps.core.services.export import ...` |
| `from apps.medtrans.services.xml_text_extractor import ...` | `from apps.core.services.extractors import ...` |

---

## Configuration

### Django Settings

```python
# settings.py

# LLM Configuration
CORE_LLM_CONFIG = {
    'default_provider': 'openai',
    'default_model': 'gpt-4',
    'api_keys': {
        'openai': os.environ.get('OPENAI_API_KEY'),
        'anthropic': os.environ.get('ANTHROPIC_API_KEY'),
    },
    'cache_responses': True,
    'cache_ttl': 3600,
}

# Cache Configuration
CORE_CACHE_CONFIG = {
    'backend': 'redis',  # redis, memory, file, django
    'redis_url': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    'key_prefix': 'bfagent',
    'default_ttl': 3600,
}

# Storage Configuration
CORE_STORAGE_CONFIG = {
    'backend': 'local',  # local, s3, gcs, azure
    'local_path': BASE_DIR / 'storage',
    's3_bucket': os.environ.get('S3_BUCKET'),
    's3_region': os.environ.get('S3_REGION'),
}
```

---

## Testing

Run tests:

```bash
# All core tests
pytest apps/core/tests/ -v

# Specific service
pytest apps/core/services/llm/tests/ -v
pytest apps/core/services/cache/tests/ -v

# Integration tests
pytest apps/core/tests/test_integration.py -v
```

---

## Architecture

```
apps/core/
├── __init__.py
├── apps.py                    # Django app config
├── handlers/                  # Handler framework
│   ├── __init__.py
│   ├── base.py               # BaseHandler, BaseHandlerV2
│   ├── registry.py           # Handler registry
│   └── schemas.py            # Pydantic schemas
├── services/
│   ├── llm/                  # LLM Service
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── providers.py
│   │   ├── service.py
│   │   └── exceptions.py
│   ├── cache/                # Cache Service
│   │   ├── __init__.py
│   │   ├── backends.py
│   │   ├── service.py
│   │   └── decorators.py
│   ├── storage/              # Storage Service
│   │   ├── __init__.py
│   │   ├── backends.py
│   │   └── service.py
│   ├── export/               # Export Service
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── exporters.py
│   │   └── base.py
│   └── extractors/           # File Extractors
│       ├── __init__.py
│       ├── models.py
│       ├── extractors.py
│       └── base.py
├── management/
│   └── commands/
│       └── migrate_to_core.py
└── tests/
    ├── test_llm.py
    ├── test_cache.py
    ├── test_storage.py
    ├── test_export.py
    ├── test_extractors.py
    └── test_integration.py
```

---

## Dependencies

```txt
# Core (always required)
pydantic>=2.0

# LLM Service
openai>=1.0
anthropic>=0.18

# Cache Service
redis>=4.0  # for Redis backend

# Export Service
python-docx>=0.8
reportlab>=4.0
ebooklib>=0.18

# Extractors
pdfplumber>=0.9
openpyxl>=3.1
pytesseract>=0.3  # for OCR
pillow>=10.0  # for OCR
```

---

## Contributing

1. All new services should follow the existing patterns
2. Include comprehensive tests
3. Update this README
4. Add migration mappings if replacing old code

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12 | Initial consolidation (6 services) |
