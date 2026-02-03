# 🎯 PPTX-Hub

[![PyPI version](https://badge.fury.io/py/pptx-hub.svg)](https://badge.fury.io/py/pptx-hub)
[![Python](https://img.shields.io/pypi/pyversions/pptx-hub.svg)](https://pypi.org/project/pptx-hub/)
[![Django](https://img.shields.io/badge/django-5.0%20%7C%206.0-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/YOUR_ORG/pptx-hub/workflows/CI/badge.svg)](https://github.com/YOUR_ORG/pptx-hub/actions)
[![codecov](https://codecov.io/gh/YOUR_ORG/pptx-hub/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_ORG/pptx-hub)

**Production-ready PowerPoint processing platform with multi-tenancy support.**

PPTX-Hub is a database-driven platform for processing, translating, and transforming PowerPoint presentations. Built for enterprise use with proper tenant isolation, audit trails, and scalable job processing.

---

## ✨ Features

- 🏢 **Multi-Tenant** – Full organization isolation with row-level security ready
- 🗄️ **Database-Driven** – PostgreSQL as single source of truth
- 🔄 **Pipeline Architecture** – Extract → Transform → Repackage workflow
- 📊 **Job Processing** – Async processing with retry and progress tracking
- 🌍 **Translation Ready** – Built-in DeepL integration
- 🔒 **Audit Trail** – Input snapshots for full reproducibility
- 📦 **Storage Backends** – Local, S3, MinIO support
- 🐍 **Django Integration** – Full Django app with REST API
- 🖥️ **CLI Tool** – Command-line interface for batch processing

---

## 🚀 Quick Start

### Installation

```bash
# Core package only
pip install pptx-hub

# With Django support
pip install pptx-hub[django]

# With translation support
pip install pptx-hub[translation]

# Full installation (recommended)
pip install pptx-hub[all]
```

### Basic Usage (Standalone)

```python
from pptx_hub.core.services import TextExtractor, Repackager

# Extract text from presentation
extractor = TextExtractor()
result = extractor.extract("presentation.pptx")

print(f"Found {len(result.slides)} slides")
for slide in result.slides:
    print(f"  Slide {slide.number}: {slide.title}")
    for text in slide.texts:
        print(f"    - {text.content[:50]}...")

# Repackage with modifications
repackager = Repackager()
repackager.repackage(
    source="presentation.pptx",
    output="modified.pptx",
    replacements={"Old Text": "New Text"}
)
```

### Django Integration

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'django_filters',
    'pptx_hub.django',
]

PPTX_HUB = {
    'STORAGE_BACKEND': 'local',  # or 's3', 'minio'
    'STORAGE_ROOT': BASE_DIR / 'media' / 'pptx_hub',
    
    # S3 Settings (if using S3)
    'S3_BUCKET': 'my-bucket',
    'S3_ACCESS_KEY': '...',
    'S3_SECRET_KEY': '...',
    
    # Job Processing
    'JOB_TIMEOUT': 600,  # 10 minutes
    'JOB_MAX_RETRIES': 3,
}
```

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    # ...
    path('api/v1/pptx-hub/', include('pptx_hub.django.urls')),
]
```

```bash
# Run migrations
python manage.py migrate pptx_hub

# Start worker (for async jobs)
python manage.py qcluster
```

### CLI Usage

```bash
# Extract text from presentation
pptx-hub extract presentation.pptx --output texts.json

# Translate presentation
pptx-hub translate presentation.pptx --target de --output translated.pptx

# Analyze presentation
pptx-hub analyze presentation.pptx --format json
```

---

## 📖 Documentation

Full documentation is available at [pptx-hub.readthedocs.io](https://pptx-hub.readthedocs.io)

- [Installation Guide](https://pptx-hub.readthedocs.io/getting-started/installation/)
- [Quick Start](https://pptx-hub.readthedocs.io/getting-started/quickstart/)
- [Configuration](https://pptx-hub.readthedocs.io/getting-started/configuration/)
- [Multi-Tenancy Guide](https://pptx-hub.readthedocs.io/guides/multi-tenancy/)
- [Storage Backends](https://pptx-hub.readthedocs.io/guides/storage-backends/)
- [Job Processing](https://pptx-hub.readthedocs.io/guides/job-processing/)
- [API Reference](https://pptx-hub.readthedocs.io/api-reference/)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PPTX-HUB                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  REST API   │    │    CLI      │    │  Python API │         │
│  │  (Django)   │    │  (Typer)    │    │   (Core)    │         │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘         │
│         └──────────────────┴──────────────────┘                 │
│                            │                                    │
│  ┌─────────────────────────┴─────────────────────────┐         │
│  │                    Core Services                   │         │
│  │  TextExtractor │ Translator │ Repackager │ Analyzer│         │
│  └─────────────────────────┬─────────────────────────┘         │
│                            │                                    │
│  ┌──────────────┐  ┌───────┴───────┐  ┌──────────────┐         │
│  │   Storage    │  │   Job Queue   │  │   Database   │         │
│  │ Local/S3     │  │  Django-Q2    │  │  PostgreSQL  │         │
│  └──────────────┘  └───────────────┘  └──────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Core Concepts

| Concept | Description |
|---------|-------------|
| **Presentation** | A PowerPoint file with metadata and version history |
| **Slide** | Individual slide with extracted content |
| **Job** | Async processing task (translate, enhance, etc.) |
| **Organization** | Tenant for multi-tenancy isolation |

---

## 🔌 Integrations

### Translation Providers

```python
# DeepL (built-in)
from pptx_hub.contrib.deepl import DeepLTranslator

translator = DeepLTranslator(api_key="your-key")
result = translator.translate(texts, target_lang="DE")

# OpenAI (built-in)
from pptx_hub.contrib.openai import OpenAITranslator

translator = OpenAITranslator(api_key="your-key")
result = translator.translate(texts, target_lang="German")
```

### Storage Backends

```python
from pptx_hub.core.storage import LocalStorage, S3Storage

# Local filesystem
storage = LocalStorage(base_path="/data/presentations")

# S3/MinIO
storage = S3Storage(
    bucket="my-bucket",
    endpoint_url="https://s3.amazonaws.com",  # or MinIO URL
)
```

---

## 🧪 Development

### Setup

```bash
# Clone repository
git clone https://github.com/YOUR_ORG/pptx-hub.git
cd pptx-hub

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install with dev dependencies
pip install -e ".[dev,all]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov --cov-report=html

# Run specific tests
pytest tests/core/test_extractor.py -v
```

### Code Quality

```bash
# Linting
ruff check src tests

# Formatting
ruff format src tests

# Type checking
mypy src
```

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) first.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [python-pptx](https://github.com/scanny/python-pptx) – Core PPTX manipulation library
- [Django](https://www.djangoproject.com/) – Web framework
- [Django REST Framework](https://www.django-rest-framework.org/) – API toolkit
- [Django-Q2](https://django-q2.readthedocs.io/) – Task queue

---

## 📊 Project Status

| Component | Status |
|-----------|--------|
| Core Library | 🟡 Alpha |
| Django Integration | 🟡 Alpha |
| CLI | 🟡 Alpha |
| Documentation | 🟡 In Progress |
| PyPI Release | 🔴 Not Yet |

---

Made with ❤️ by [Your Organization](https://github.com/YOUR_ORG)
