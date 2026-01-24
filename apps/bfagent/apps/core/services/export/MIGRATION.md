# Export Service Migration Guide

## Overview

This guide helps migrate from existing export implementations to the consolidated Core Export Service.

## Existing Implementations

| Location | Class | Features | Migration Effort |
|----------|-------|----------|------------------|
| `bfagent/services/book_export.py` | `BookExportService` | DOCX/PDF/EPUB book exports | 10 min |
| `bfagent/services/handlers/output/markdown_file.py` | `MarkdownFileOutputHandler` | Markdown export | 5 min |

## Quick Migration

### 1. Import Changes

```python
# OLD
from apps.bfagent.services.book_export import BookExportService

# NEW
from apps.core.services.export import BookExporter, BookContent, ChapterContent
```

### 2. BookExportService Migration

**Before:**
```python
from apps.bfagent.services.book_export import BookExportService
from apps.bfagent.models import BookProjects

export_service = BookExportService()

# Export to DOCX
docx_path = export_service.export_to_docx(project)

# Export to PDF
pdf_path = export_service.export_to_pdf(project)

# Export to EPUB
epub_path = export_service.export_to_epub(project)

# Export all formats
results = export_service.export_all_formats(project)
```

**After:**
```python
from apps.core.services.export import (
    BookExporter, BookContent, ChapterContent
)

# Create book content from project
book = BookContent(
    title=project.title,
    author="BF Agent",
    genre=project.genre,
    chapters=[
        ChapterContent(
            number=idx,
            content=chapter_content
        )
        for idx, chapter_content in enumerate(chapters, 1)
    ]
)

exporter = BookExporter()

# Export to DOCX
result = exporter.export_to_docx(book)

# Export to PDF
result = exporter.export_to_pdf(book)

# Export to EPUB
result = exporter.export_to_epub(book)

# Export all formats
results = exporter.export_all_formats(book)
```

### 3. MarkdownFileOutputHandler Migration

**Before:**
```python
from apps.bfagent.services.handlers.output.markdown_file import MarkdownFileOutputHandler

handler = MarkdownFileOutputHandler({
    "output_dir": "/path/to/output",
    "filename_template": "chapter_{number}_{title}.md",
    "add_frontmatter": True
})
```

**After:**
```python
from apps.core.services.export import (
    export_markdown, DocumentMetadata
)

# Simple export
result = export_markdown(
    content="# Chapter 1\n\nContent here...",
    output_path="output/chapter_01.md",
    add_frontmatter=True,
    metadata=DocumentMetadata(
        title="Chapter 1",
        author="Author Name"
    )
)

# Or using the exporter directly
from apps.core.services.export import MarkdownExporter, ExportConfig

exporter = MarkdownExporter(ExportConfig(
    output_dir="/path/to/output",
    filename_template="{title}_{date}"
))

result = exporter.export(content, metadata=metadata)
```

## Feature Comparison

| Feature | Old Implementations | New Core Service |
|---------|---------------------|------------------|
| DOCX export | ✅ | ✅ |
| PDF export | ✅ | ✅ |
| EPUB export | ✅ | ✅ |
| Markdown export | ✅ | ✅ |
| HTML export | ❌ | ✅ |
| JSON export | ❌ | ✅ |
| CSV export | ❌ | ✅ |
| Frontmatter support | ✅ | ✅ |
| Metadata handling | Basic | ✅ Full |
| Error handling | Basic | ✅ Comprehensive |
| Backup files | ❌ | ✅ |

## Detailed Examples

### Simple Text Export

```python
from apps.core.services.export import export_to

# Export markdown content to DOCX
result = export_to(
    "docx",
    content="# My Document\n\nThis is the content.",
    output_path="output/document.docx"
)

if result.success:
    print(f"Exported to: {result.output_path}")
    print(f"File size: {result.file_size} bytes")
else:
    print(f"Export failed: {result.errors}")
```

### Export with Metadata

```python
from apps.core.services.export import (
    export_to, DocumentMetadata
)

metadata = DocumentMetadata(
    title="Annual Report",
    author="John Doe",
    subject="Financial Summary",
    language="en"
)

result = export_to(
    "pdf",
    content=report_content,
    output_path="exports/report.pdf",
    metadata=metadata
)
```

### Book Export

```python
from apps.core.services.export import (
    BookExporter, BookContent, ChapterContent
)

# Create book structure
book = BookContent(
    title="My Novel",
    author="Jane Author",
    genre="Fiction",
    chapters=[
        ChapterContent(
            number=1,
            title="The Beginning",
            content="It was a dark and stormy night..."
        ),
        ChapterContent(
            number=2,
            title="The Journey",
            content="The next morning..."
        ),
    ]
)

# Export to all formats
exporter = BookExporter(output_dir="exports/my-novel")
results = exporter.export_all_formats(book)

for format_name, result in results.items():
    if result.success:
        print(f"{format_name}: {result.output_path}")
    else:
        print(f"{format_name} failed: {result.errors}")
```

### Data Export (JSON/CSV)

```python
from apps.core.services.export import export_json, export_csv

# Export to JSON
data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
result = export_json(data, "output/users.json")

# Export to CSV
records = [
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 25}
]
result = export_csv(records, "output/users.csv")
```

### Custom Exporter

```python
from apps.core.services.export import (
    BaseExporter, ExportFormat, ExportResult
)

class XMLExporter(BaseExporter):
    format = ExportFormat.XML  # Would need to add to enum
    file_extension = "xml"
    
    def _export(self, content, output_path, metadata):
        # Custom XML generation logic
        xml_content = self._convert_to_xml(content)
        output_path.write_text(xml_content)
        return ExportResult(format=self.format)
```

## Content Conversion

```python
from apps.core.services.export import (
    markdown_to_html,
    html_to_markdown,
    add_frontmatter
)

# Markdown to HTML
html = markdown_to_html("# Title\n\nParagraph")

# HTML to Markdown
md = html_to_markdown("<h1>Title</h1><p>Paragraph</p>")

# Add YAML frontmatter
content_with_meta = add_frontmatter(
    "# My Document\n\nContent",
    {"title": "My Doc", "author": "Me"}
)
```

## Error Handling

```python
from apps.core.services.export import (
    export_to,
    ExportException,
    MissingDependencyError,
    is_export_error
)

try:
    result = export_to("pdf", content)
except MissingDependencyError as e:
    print(f"Missing library: {e.dependency}")
    print(f"Install with: {e.install_cmd}")
except ExportException as e:
    print(f"Export error: {e.message}")
    print(f"Details: {e.to_dict()}")
```

## Django Settings

```python
# Export Configuration
EXPORT_OUTPUT_DIR = BASE_DIR / "exports"
EXPORT_CREATE_BACKUP = True
EXPORT_TIMESTAMP_FILES = True
```

## Testing

```python
import pytest
from apps.core.services.export import (
    export_to, MarkdownExporter, ExportConfig, DocumentMetadata
)

def test_markdown_export(tmp_path):
    result = export_to(
        "md",
        content="# Test\n\nContent",
        output_path=tmp_path / "test.md"
    )
    
    assert result.success
    assert (tmp_path / "test.md").exists()

def test_book_export(tmp_path):
    from apps.core.services.export import BookExporter, BookContent
    
    book = BookContent(title="Test Book", chapters=[])
    exporter = BookExporter(output_dir=str(tmp_path))
    
    result = exporter.export_to_docx(book)
    assert result.success
```
