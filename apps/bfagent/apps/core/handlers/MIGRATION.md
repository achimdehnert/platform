# Handler Migration Guide

## Overview

This guide helps migrate existing handler implementations to the consolidated Core handler system.

The new system consolidates handlers from:
- `apps/core/handlers/` (original simple version)
- `apps/bfagent/handlers/` (BFAgent handlers)
- `apps/bfagent/services/handlers/` (enhanced handlers)
- `apps/genagent/handlers/` (GenAgent handlers)

## Quick Migration Table

| Old Import | New Import |
|-----------|------------|
| `from apps.core.handlers.base import BaseHandler` | `from apps.core.handlers import BaseHandler` |
| `from apps.bfagent.handlers.base import BaseInputHandler` | `from apps.core.handlers import InputHandler` |
| `from apps.bfagent.services.handlers.base.processing import BaseProcessingHandler` | `from apps.core.handlers import ProcessingHandler` |
| `from apps.genagent.handlers import BaseHandler, register_handler` | `from apps.core.handlers import BaseHandler, register_handler` |

## Migration Steps

### Step 1: Update Imports

**Before (BFAgent services):**
```python
from apps.bfagent.services.handlers.base.input import BaseInputHandler
from apps.bfagent.services.handlers.base.processing import BaseProcessingHandler
from apps.bfagent.services.handlers.base.output import BaseOutputHandler
from apps.bfagent.services.handlers.exceptions import ProcessingHandlerException
from apps.bfagent.services.handlers.decorators import with_logging
```

**After:**
```python
from apps.core.handlers import (
    InputHandler,
    ProcessingHandler,
    OutputHandler,
    ProcessingError,
    with_logging
)
```

### Step 2: Update Class Definitions

**Before (BFAgent style):**
```python
class MyHandler(BaseProcessingHandler):
    handler_type: str = "processing"
    handler_name: str = "my_handler"
    handler_version: str = "2.0.0"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
    
    def validate_config(self) -> None:
        pass
    
    def process(self, input_data: Any, context: Dict[str, Any]) -> Any:
        return processed_data
```

**After:**
```python
from apps.core.handlers import ProcessingHandler, register_handler

@register_handler("my.handler", "2.0.0", domain="mydomain")
class MyHandler(ProcessingHandler):
    handler_name = "my.handler"
    handler_version = "2.0.0"
    description = "My handler description"
    domain = "mydomain"
    
    def validate_config(self) -> None:
        pass
    
    def process(self, data: Any, context: Dict[str, Any]) -> Any:
        return {'processed': data}
```

### Step 3: Update Exception Handling

**Before:**
```python
from apps.bfagent.services.handlers.exceptions import (
    InputHandlerException,
    ProcessingHandlerException,
    ConfigurationException
)

raise ProcessingHandlerException(
    "Processing failed",
    handler_name=self.handler_name
)
```

**After:**
```python
from apps.core.handlers import (
    InputHandlerException,
    ProcessingError,
    ConfigurationException
)

raise ProcessingError(
    "Processing failed",
    handler_name=self.handler_name,
    context={'additional': 'info'}
)
```

### Step 4: Update Registry Usage

**Before (GenAgent style):**
```python
from apps.genagent.handlers import register_handler, get_handler, HANDLER_REGISTRY

@register_handler
class MyHandler(BaseHandler):
    pass

handler = HANDLER_REGISTRY.get("path.to.MyHandler")
```

**After:**
```python
from apps.core.handlers import register_handler, get_handler

@register_handler("my.handler", "1.0.0", domain="mydomain")
class MyHandler(ProcessingHandler):
    pass

handler = get_handler("my.handler")
```

## Detailed Changes

### InputHandler Changes

**Method signature change:**

| Old | New |
|-----|-----|
| `collect(self, context) -> Dict` | `collect(self, context) -> Dict` (unchanged) |

**execute() now returns standardized format:**
```python
{
    'success': True,
    'data': {...}  # Result from collect()
}
```

### ProcessingHandler Changes

**Method signature change:**

| Old | New |
|-----|-----|
| `process(self, input_data, context)` | `process(self, data, context)` |

**execute() now handles:**
- Pydantic validation (if InputSchema/OutputSchema defined)
- Transaction management (if Django available)
- Standardized result format

### OutputHandler Changes

**Required methods:**

| Method | Purpose |
|--------|---------|
| `parse(processed_data)` | Convert to list of dicts |
| `apply(data)` | Persist single item |

**Optional methods:**

| Method | Purpose |
|--------|---------|
| `validate_output(parsed_data)` | Validate before persist |

### Decorator Changes

All decorators are now in `apps.core.handlers.decorators`:

```python
from apps.core.handlers import (
    with_logging,
    with_performance_monitoring,
    retry_on_failure,
    with_caching,
    validate_context,
    measure_tokens,
    deprecated
)
```

## Backward Compatibility

The following aliases are provided for backward compatibility:

```python
# These all work:
from apps.core.handlers import BaseInputHandler  # → InputHandler
from apps.core.handlers import BaseProcessingHandler  # → ProcessingHandler
from apps.core.handlers import BaseOutputHandler  # → OutputHandler
from apps.core.handlers import GenAgentBaseHandler  # → BaseHandler
```

## Domain-Specific Migration

### BFAgent Handlers

```python
# Old
from apps.bfagent.handlers.processing_handlers.enrichment_handler import EnrichmentHandler

# New - after migration
from apps.core.handlers import get_handler
handler = get_handler("bfagent.enrichment")
```

### GenAgent Handlers

```python
# Old
from apps.genagent.handlers import BaseHandler

class MyHandler(BaseHandler):
    def execute(self, context, test_mode=False):
        return {'success': True, 'output': result}

# New
from apps.core.handlers import ProcessingHandler

class MyHandler(ProcessingHandler):
    handler_name = "my.handler"
    
    def process(self, data, context):
        return {'output': result}
```

### MedTrans Handlers

```python
# MedTrans handlers should use ProcessingHandler:
from apps.core.handlers import ProcessingHandler, register_handler

@register_handler("medtrans.translate", "1.0.0", domain="medtrans")
class TranslateHandler(ProcessingHandler):
    def process(self, data, context):
        # Translation logic
        return {'translated': result}
```

## Testing

Run the consolidated handler tests:

```bash
pytest apps/core/handlers/tests/test_handlers.py -v
```

Test your migrated handlers:

```python
from apps.core.handlers import get_handler

def test_my_handler():
    handler = get_handler("my.handler")
    result = handler.execute({'input': 'test'})
    assert result['success'] is True
```

## Checklist

- [ ] Update all imports to use `apps.core.handlers`
- [ ] Change class inheritance to new base classes
- [ ] Update method signatures (`input_data` → `data`)
- [ ] Use `@register_handler` decorator for registration
- [ ] Update exception classes
- [ ] Add handler metadata (handler_name, domain, version)
- [ ] Update tests
- [ ] Remove old handler files after verification

## Support

If you encounter issues during migration:

1. Check the backward compatibility aliases
2. Review the test cases for usage examples
3. Verify your handler_name is unique
4. Ensure Pydantic schemas are compatible (if used)
