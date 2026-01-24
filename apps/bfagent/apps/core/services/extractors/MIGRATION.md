# File Extractor Service Migration Guide

## Overview

This guide helps migrate from existing file extraction implementations to the consolidated Core File Extractor Service.

## Existing Implementations

| Location | Class | Features | Migration Effort |
|----------|-------|----------|------------------|
| `medtrans/services/xml_text_extractor.py` | `XMLTextExtractor` | PPTX text extraction | 10 min |
| `presentation_studio/handlers/pdf_content_extractor.py` | `PDFContentExtractor` | PDF to slides | 5 min |
| `presentation_studio/handlers/slide_extractor.py` | `SlideExtractor` | PPTX shapes | 5 min |

## Quick Migration

### 1. Import Changes

```python
# OLD
from apps.medtrans.services.xml_text_extractor import XMLTextExtractor
from apps.presentation_studio.handlers.pdf_content_extractor import PDFContentExtractor

# NEW
from apps.core.services.extractors import PPTXExtractor, PDFExtractor
```

### 2. XMLTextExtractor Migration

**Before:**
```python
from apps.medtrans.services.xml_text_extractor import XMLTextExtractor

extractor = XMLTextExtractor()
result = extractor.extract_texts_from_pptx(pptx_path)

if result['success']:
    for slide in result['slides']:
        print(f"Slide {slide['slide_number']}")
        for text in slide['texts']:
            print(f"  {text['original_text']}")
```

**After:**
```python
from apps.core.services.extractors import PPTXExtractor

extractor = PPTXExtractor()
result = extractor.extract(pptx_path)

if result.success:
    for slide in result.slides:
        print(f"Slide {slide.slide_number}: {slide.title}")
        for text in slide.texts:
            print(f"  {text['text']}")
```

### 3. PDFContentExtractor Migration

**Before:**
```python
from apps.presentation_studio.handlers.pdf_content_extractor import PDFContentExtractor

extractor = PDFContentExtractor()
result = extractor.extract_content(pdf_path)

if result['success']:
    for slide in result['slides']:
        print(f"Title: {slide['title']}")
        print(f"Content: {slide['content']}")
```

**After:**
```python
from apps.core.services.extractors import PDFExtractor

extractor = PDFExtractor()
result = extractor.extract(pdf_path)

if result.success:
    for text in result.texts:
        print(f"Page {text.page_number}:")
        print(text.text)
```

### 4. Simple Text Extraction

**Before (various implementations):**
```python
with open(file_path, 'r') as f:
    content = f.read()
```

**After:**
```python
from apps.core.services.extractors import extract_text

content = extract_text(file_path)  # Auto-detects format
```

## Feature Comparison

| Feature | Old Implementations | New Core Service |
|---------|---------------------|------------------|
| PDF extraction | ✅ Basic | ✅ Full + OCR |
| PPTX extraction | ✅ XML-based | ✅ XML-based |
| DOCX extraction | ❌ | ✅ Full |
| Excel extraction | ❌ | ✅ Full |
| CSV extraction | ❌ | ✅ Full |
| JSON extraction | ❌ | ✅ Full |
| Image OCR | ❌ | ✅ Optional |
| Table extraction | Partial | ✅ Full |
| Metadata extraction | Partial | ✅ Full |
| Unified API | ❌ | ✅ |

## Detailed Examples

### Auto-Detect Extraction

```python
from apps.core.services.extractors import extract_file

# Works with any supported file type
result = extract_file("document.pdf")
result = extract_file("spreadsheet.xlsx")
result = extract_file("presentation.pptx")
result = extract_file("data.json")

if result.success:
    print(f"Type: {result.file_type}")
    print(f"Text: {result.text[:500]}...")
    print(f"Words: {result.word_count}")
```

### PDF with OCR

```python
from apps.core.services.extractors import (
    PDFExtractor, ExtractorConfig
)

# Enable OCR for scanned documents
config = ExtractorConfig(
    ocr_enabled=True,
    ocr_language="deu"  # German
)

extractor = PDFExtractor(config)
result = extractor.extract("scanned_document.pdf")

# Or use convenience function
from apps.core.services.extractors import extract_pdf
result = extract_pdf("scanned.pdf", ocr=True)
```

### PowerPoint Slides

```python
from apps.core.services.extractors import PPTXExtractor

extractor = PPTXExtractor()
result = extractor.extract("presentation.pptx")

if result.success:
    print(f"Total slides: {len(result.slides)}")
    
    for slide in result.slides:
        print(f"\nSlide {slide.slide_number}")
        print(f"  Title: {slide.title}")
        print(f"  Text elements: {len(slide.texts)}")
        
        for text in slide.texts:
            print(f"    [{text['id']}] {text['text']}")
```

### Excel Spreadsheets

```python
from apps.core.services.extractors import ExcelExtractor, extract_excel

# Full control
extractor = ExcelExtractor()
result = extractor.extract("data.xlsx")

for table in result.tables:
    print(f"Sheet: {table.sheet_name}")
    print(f"Rows: {table.row_count}")
    print(f"Headers: {table.headers}")

# Or specific sheets only
result = extract_excel("data.xlsx", sheets=["Summary", "Data"])
```

### Tables from Any Source

```python
from apps.core.services.extractors import extract_tables

# Works with PDF, Excel, CSV
tables = extract_tables("report.pdf")

for table in tables:
    print(f"Headers: {table.headers}")
    for row in table.rows:
        print(row)
```

### Working with Results

```python
from apps.core.services.extractors import extract_file

result = extract_file("document.pdf")

# Check success
if not result.success:
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")

# Access content
print(result.text)           # All text combined
print(result.word_count)     # Total words
print(result.page_count)     # Number of pages

# Access metadata
print(result.metadata.title)
print(result.metadata.author)
print(result.metadata.to_dict())

# Access structured content
for text in result.texts:
    print(f"Page {text.page_number}: {text.text[:100]}...")

for table in result.tables:
    print(f"Table with {table.row_count} rows")

for slide in result.slides:
    print(f"Slide {slide.slide_number}: {slide.title}")

# Convert to dict for serialization
data = result.to_dict()
```

## Error Handling

```python
from apps.core.services.extractors import (
    extract_file,
    ExtractorException,
    MissingDependencyError,
    PasswordRequiredError,
    is_extractor_error
)

try:
    result = extract_file("document.pdf")
except MissingDependencyError as e:
    print(f"Missing: {e.dependency}")
    print(f"Install: {e.install_cmd}")
except PasswordRequiredError:
    print("File is password-protected")
except ExtractorException as e:
    print(f"Extraction error: {e.message}")
    print(f"Details: {e.to_dict()}")
```

## Configuration Options

```python
from apps.core.services.extractors import ExtractorConfig

config = ExtractorConfig(
    # Text processing
    preserve_formatting=True,
    
    # Metadata
    extract_metadata=True,
    
    # Images
    extract_images=False,
    
    # OCR
    ocr_enabled=False,
    ocr_language="eng",
    
    # Page/Sheet selection
    page_range=[1, 2, 3],      # Specific pages
    sheet_names=["Summary"],   # Specific sheets
    
    # Text encoding
    encoding="utf-8",
    
    # Limits
    max_file_size=100 * 1024 * 1024,  # 100 MB
)
```

## Django Integration

```python
# views.py
from django.http import JsonResponse
from apps.core.services.extractors import extract_file

def extract_document(request):
    if request.method == 'POST':
        uploaded_file = request.FILES['document']
        
        # Save temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            for chunk in uploaded_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        
        # Extract
        result = extract_file(tmp_path)
        
        # Clean up
        import os
        os.unlink(tmp_path)
        
        return JsonResponse(result.to_dict())
```

## Testing

```python
import pytest
from apps.core.services.extractors import (
    extract_file, PDFExtractor, ExtractorConfig
)

def test_pdf_extraction(tmp_path):
    # Create test PDF (or use fixture)
    pdf_path = tmp_path / "test.pdf"
    # ... create PDF ...
    
    result = extract_file(pdf_path)
    
    assert result.success
    assert result.file_type.value == "pdf"
    assert len(result.text) > 0

def test_extractor_config():
    config = ExtractorConfig(ocr_enabled=True)
    extractor = PDFExtractor(config)
    
    assert extractor.config.ocr_enabled is True
```

## Compatibility with Existing Code

The new extractors maintain compatibility with the result structures expected by existing code:

```python
# For medtrans compatibility
result = pptx_extractor.extract(pptx_path)
legacy_format = {
    'success': result.success,
    'slides': [slide.to_dict() for slide in result.slides],
    'total_texts': sum(len(s.texts) for s in result.slides),
    'errors': result.errors
}
```
