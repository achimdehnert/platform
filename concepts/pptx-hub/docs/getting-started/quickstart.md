# Quick Start

This guide will help you get started with PPTX-Hub in minutes.

## Standalone Usage (No Django)

### Extract Text from a Presentation

```python
from pptx_hub import TextExtractor

# Create extractor
extractor = TextExtractor()

# Extract text
result = extractor.extract("presentation.pptx")

# Check result
if result.success:
    print(f"Found {result.total_slides} slides")
    
    for slide in result.slides:
        print(f"Slide {slide.number}: {slide.title}")
        for text in slide.texts:
            print(f"  - {text.content}")
else:
    print(f"Errors: {result.errors}")
```

### Analyze a Presentation

```python
from pptx_hub import SlideAnalyzer

analyzer = SlideAnalyzer()
analysis = analyzer.analyze("presentation.pptx")

print(f"Slides: {analysis.slide_count}")
print(f"Words: {analysis.total_word_count}")
print(f"Images: {analysis.slides_with_images}")
```

### Repackage with Modifications

```python
from pptx_hub import Repackager

repackager = Repackager()

# Replace text
stats = repackager.repackage(
    source="original.pptx",
    output="modified.pptx",
    replacements={"Hello": "Hallo", "World": "Welt"}
)

print(f"Modified {stats['texts_replaced']} texts")
```

## Django Integration

### 1. Install and Configure

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'pptx_hub.django',
]

PPTX_HUB = {
    'STORAGE_BACKEND': 'local',
    'STORAGE_ROOT': BASE_DIR / 'media' / 'pptx_hub',
}
```

### 2. Run Migrations

```bash
python manage.py migrate pptx_hub
```

### 3. Include URLs

```python
# urls.py
urlpatterns = [
    path('api/pptx-hub/', include('pptx_hub.django.urls')),
]
```

### 4. Use the API

```bash
# List presentations
curl -X GET http://localhost:8000/api/pptx-hub/presentations/

# Upload a presentation
curl -X POST http://localhost:8000/api/pptx-hub/presentations/ \
  -F "file=@presentation.pptx" \
  -F "org_id=YOUR_ORG_ID"
```

## CLI Usage

```bash
# Extract text
pptx-hub extract presentation.pptx --output texts.json

# Analyze
pptx-hub analyze presentation.pptx

# Repackage
pptx-hub repackage input.pptx output.pptx --replacements replacements.json
```

## Next Steps

- [Configuration](configuration.md) - Configure storage, multi-tenancy, and more
- [Multi-Tenancy Guide](../guides/multi-tenancy.md) - Set up organization isolation
- [API Reference](../api-reference/) - Complete API documentation
