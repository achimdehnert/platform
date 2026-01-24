# Migration Guide v1.0 → v2.0

## What's New in v2.0

### Major Improvements

1. **Pydantic Validation** - Type-safe configurations
2. **Structured Logging** - Comprehensive logging with structlog
3. **Error Handling** - Custom exception hierarchy
4. **Transaction Safety** - Automatic rollback
5. **Performance Monitoring** - Built-in metrics

### Breaking Changes

#### Configuration Validation

**Old:**
```python
handler = ChapterDataHandler({"limit": "5"})  # String accepted
```

**New:**
```python
handler = ChapterDataHandler({"limit": 5})  # Must be int
```

#### Exception Types

**Old:**
```python
except Exception as e:
    print(f"Error: {e}")
```

**New:**
```python
from apps.bfagent.services.handlers.exceptions import InputHandlerException

try:
    result = handler.collect(context)
except InputHandlerException as e:
    logger.error("Collection failed", error=e.to_dict())
```

## Migration Steps

### Step 1: Install Dependencies
```bash
pip install pydantic structlog
```

### Step 2: Update Imports

**Old:**
```python
from apps.bfagent.services.handlers.input.chapter_data import ChapterDataHandler
```

**New:**
```python
from apps.bfagent.services.handlers.input import ChapterDataHandler
from apps.bfagent.services.handlers.exceptions import InputHandlerException
```

### Step 3: Update Exception Handling

Replace generic exceptions with specific types.

### Step 4: Test Migration
```bash
python examples/complete_pipeline_example.py
pytest tests/ -v
```

## Rollback Plan

Old handlers remain available temporarily:
```python
from apps.bfagent.services.handlers.input.chapter_data_v1 import ChapterDataHandler
```

---

**Last Updated:** 2025-01-16
