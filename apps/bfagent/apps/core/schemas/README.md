# Core Schemas Package

Unified Pydantic schemas for consistent validation across the BF Agent project.

## 🎯 Purpose

Consolidates scattered validation logic and schema definitions into a single, well-organized package.

### Before (Scattered)
```
apps/genagent/core/schemas.py
apps/bfagent/services/handlers/schemas.py
apps/image_generation/schemas/
... validation logic spread across 20+ files
```

### After (Unified)
```
apps/core/schemas/
├── base.py        # Base models, mixins, enums
├── validators.py  # Validation utilities
├── handlers.py    # Handler-specific schemas
└── __init__.py    # Public API
```

## 📦 Installation

Already included in `apps.core` app.

## 🚀 Quick Start

### Basic Models

```python
from apps.core.schemas import BaseInput, BaseOutput

class MyServiceInput(BaseInput):
    name: str
    email: str
    age: int

class MyServiceOutput(BaseOutput):
    user_id: int
    message: str
```

### Validators

```python
from apps.core.schemas import validate_email, validate_url, validate_file_extension

# Email validation
result = validate_email("user@example.com")
if not result.is_valid:
    print(result.errors)

# URL validation
result = validate_url("https://example.com", require_https=True)

# File validation
result = validate_file_extension(
    "document.pdf",
    allowed_types=['document']
)
```

### Handler Schemas

```python
from apps.core.schemas import HandlerInput, HandlerOutput, LLMProcessorConfig

class MyHandlerInput(HandlerInput):
    prompt: str
    config: LLMProcessorConfig

class MyHandlerOutput(HandlerOutput):
    generated_text: str
    tokens_used: int
```

## 📚 Components

### Base Models

- **BaseConfigModel** - Flexible config (allows extra fields)
- **StrictConfigModel** - Strict config (forbids extra fields)
- **BaseInput** - Standard input with metadata
- **BaseOutput** - Standard output with success/errors
- **PaginatedOutput** - Paginated responses

### Mixins

- **TimestampMixin** - `created_at`, `updated_at` fields
- **IdentifiableMixin** - `id`, `slug` fields

### Enums

- **ProcessingStatus** - pending, running, completed, failed, etc.
- **Priority** - low, medium, high, critical

### Validators

#### String Validators
- `validate_email(email)` - RFC-compliant email validation
- `validate_url(url, require_https=False)` - URL format validation
- `validate_slug(slug)` - URL-safe slug validation
- `validate_json_string(json_str)` - JSON format validation

#### File Validators
- `validate_file_extension(filename, allowed_types, allowed_extensions)`
- `validate_file_size(file_size, max_size_mb, min_size_kb)`

#### Numeric Validators
- `validate_range(value, min_value, max_value)`

#### List Validators
- `validate_list_length(items, min_length, max_length)`
- `validate_unique_items(items)`

#### Combined
- `validate_all(*results)` - Combine multiple validation results

### Handler Schemas

Pre-built schemas for common handler patterns:

- **LLMProcessor** - LLM processing handlers
- **TemplateRenderer** - Template rendering
- **Validation** - Data validation handlers
- **FileProcessor** - File processing
- **BatchProcessor** - Batch operations

## 🎨 Usage Patterns

### Pattern 1: Simple Validation

```python
from apps.core.schemas import validate_email, ValidationResult

def register_user(email: str) -> ValidationResult:
    result = validate_email(email)
    if not result.is_valid:
        return result
    
    # ... process valid email
    return result
```

### Pattern 2: Complex Validation

```python
from apps.core.schemas import validate_all, validate_email, validate_url

def validate_user_data(email, website):
    results = validate_all(
        validate_email(email),
        validate_url(website, require_https=True)
    )
    
    if not results.is_valid:
        print(f"Errors: {results.errors}")
    
    return results
```

### Pattern 3: Handler with Config

```python
from apps.core.schemas import HandlerInput, HandlerOutput, HandlerConfig
from typing import Dict, Any

class MyHandlerConfig(HandlerConfig):
    custom_setting: str = "default"

class MyHandlerInput(HandlerInput):
    data: Dict[str, Any]
    config: MyHandlerConfig

class MyHandlerOutput(HandlerOutput):
    result: str
```

### Pattern 4: Paginated Response

```python
from apps.core.schemas import PaginatedOutput

def list_items(page=1, page_size=20):
    items = fetch_items(page, page_size)
    total = count_total_items()
    
    return PaginatedOutput(
        success=True,
        data={'items': items},
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size,
        has_next=page * page_size < total,
        has_previous=page > 1
    )
```

## 🔧 Extending Schemas

### Custom Base Model

```python
from apps.core.schemas import BaseConfigModel

class MyCustomModel(BaseConfigModel):
    """Your custom model with validation."""
    name: str
    value: int
    
    @field_validator('value')
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError('Value must be positive')
        return v
```

### Custom Validator

```python
from apps.core.schemas import ValidationResult

def validate_custom_format(data: str) -> ValidationResult:
    """Your custom validation logic."""
    result = ValidationResult(is_valid=True)
    
    if not data.startswith('PREFIX_'):
        result.add_error("Data must start with 'PREFIX_'")
    
    return result
```

## 📊 Migration Guide

### Migrating from Old Schemas

**Before:**
```python
from apps.bfagent.services.handlers.schemas import HandlerConfig
```

**After:**
```python
from apps.core.schemas import HandlerConfig
```

**Before:**
```python
# Custom email validation
import re
EMAIL_REGEX = re.compile(...)
if not EMAIL_REGEX.match(email):
    raise ValueError("Invalid email")
```

**After:**
```python
from apps.core.schemas import validate_email

result = validate_email(email)
if not result.is_valid:
    # Handle errors
    print(result.errors)
```

## ✅ Benefits

| Aspect | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Schema Locations** | 10+ files | 1 package | -90% |
| **Validation Code** | Duplicated 20+ times | Centralized | -95% |
| **Import Paths** | Inconsistent | `apps.core.schemas` | ✅ Unified |
| **Type Safety** | Mixed | Full Pydantic | ✅ Enhanced |
| **Error Messages** | Inconsistent | Standardized | ✅ Consistent |

## 🧪 Testing

```bash
# Test imports
python -c "from apps.core.schemas import BaseInput, validate_email; print('OK')"

# Test validators
python -c "from apps.core.schemas import validate_slug; print(validate_slug('my-project').is_valid)"
```

## 📖 API Reference

See docstrings in each module for detailed API documentation:

- `base.py` - Base models and mixins
- `validators.py` - Validation functions
- `handlers.py` - Handler-specific schemas

## 🔗 Related

- **Core Handlers** - `apps.core.handlers`
- **Core Services** - `apps.core.services`
- **Migration Tool** - `python manage.py migrate_to_core`

## 📝 Version

Current version: **1.0.0**

Created: December 2024
Status: Production Ready ✅
