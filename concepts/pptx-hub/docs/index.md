# PPTX-Hub

**Production-ready PowerPoint processing platform with multi-tenancy support.**

PPTX-Hub is a database-driven platform for processing, translating, and transforming PowerPoint presentations. Built for enterprise use with proper tenant isolation, audit trails, and scalable job processing.

## Features

- 🏢 **Multi-Tenant** – Full organization isolation with row-level security ready
- 🗄️ **Database-Driven** – PostgreSQL as single source of truth
- 🔄 **Pipeline Architecture** – Extract → Transform → Repackage workflow
- 📊 **Job Processing** – Async processing with retry and progress tracking
- 🌍 **Translation Ready** – Built-in DeepL integration
- 🔒 **Audit Trail** – Input snapshots for full reproducibility
- 📦 **Storage Backends** – Local, S3, MinIO support
- 🐍 **Django Integration** – Full Django app with REST API
- 🖥️ **CLI Tool** – Command-line interface for batch processing

## Quick Start

```bash
# Install
pip install pptx-hub[all]

# Extract text from a presentation
pptx-hub extract presentation.pptx --output texts.json

# Or use as a library
from pptx_hub import TextExtractor

extractor = TextExtractor()
result = extractor.extract("presentation.pptx")

for slide in result.slides:
    print(f"Slide {slide.number}: {slide.title}")
```

## Documentation

- [Installation](getting-started/installation.md) - How to install PPTX-Hub
- [Quick Start](getting-started/quickstart.md) - Get up and running quickly
- [Configuration](getting-started/configuration.md) - Configuration options
- [Guides](guides/multi-tenancy.md) - In-depth guides
- [API Reference](api-reference/) - Complete API documentation

## License

MIT License - see [LICENSE](https://github.com/YOUR_ORG/pptx-hub/blob/main/LICENSE) for details.
