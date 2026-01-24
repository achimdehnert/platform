# Pipeline Handler System

## 📦 Package Structure

```
handlers/
├── __init__.py              # Package exports
├── registries.py            # Handler registries
│
├── input/                   # INPUT Stage Handlers
│   ├── __init__.py
│   ├── base.py             # BaseInputHandler
│   ├── project_fields.py   # TODO
│   ├── characters.py       # TODO
│   └── previous_actions.py # TODO
│
├── processing/              # PROCESSING Stage Handlers
│   ├── __init__.py
│   ├── base.py             # BaseProcessingHandler
│   ├── template_renderer.py # TODO
│   ├── llm_call.py         # TODO
│   └── json_parser.py      # TODO
│
└── output/                  # OUTPUT Stage Handlers
    ├── __init__.py
    ├── base.py             # BaseOutputHandler
    ├── characters.py       # TODO
    ├── chapters.py         # TODO
    └── text_field.py       # TODO
```

## 🚀 Quick Start

### Creating a New Input Handler

```python
from apps.bfagent.services.handlers.input.base import BaseInputHandler
from apps.bfagent.services.handlers.registries import InputHandlerRegistry

@InputHandlerRegistry.register
class MyInputHandler(BaseInputHandler):
    handler_name = "my_input"
    description = "Collects my custom data"
    
    def validate_config(self):
        # Validate self.config
        pass
    
    def collect(self, context):
        # Collect and return data
        return {"my_data": "value"}
    
    def get_schema(self):
        return {
            "type": "object",
            "fields": {
                "my_data": {"type": "string"}
            }
        }
```

### Creating a New Processing Handler

```python
from apps.bfagent.services.handlers.processing.base import BaseProcessingHandler
from apps.bfagent.services.handlers.registries import ProcessingHandlerRegistry

@ProcessingHandlerRegistry.register
class MyProcessingHandler(BaseProcessingHandler):
    handler_name = "my_processor"
    description = "Processes data in my way"
    
    def validate_config(self):
        pass
    
    def process(self, input_data, context):
        # Transform input_data
        return processed_data
```

### Creating a New Output Handler

```python
from apps.bfagent.services.handlers.output.base import BaseOutputHandler
from apps.bfagent.services.handlers.registries import OutputHandlerRegistry

@OutputHandlerRegistry.register
class MyOutputHandler(BaseOutputHandler):
    handler_name = "my_output"
    description = "Stores data in my way"
    supports_multiple_objects = True
    
    def validate_config(self):
        pass
    
    def parse(self, processed_data):
        # Parse into list of dicts
        return [{"field": "value"}]
    
    def validate(self, parsed_data):
        # Validate data
        return {"valid": True, "errors": [], "warnings": []}
    
    def create_enrichment_responses(self, parsed_data, project, agent):
        # Create EnrichmentResponse objects
        return [...]
    
    def apply(self, enrichment_response):
        # Actually create/update database objects
        return created_object
```

## 📋 Using Handlers

### Get Handler from Registry

```python
from apps.bfagent.services.handlers.registries import InputHandlerRegistry

# Get handler class
HandlerClass = InputHandlerRegistry.get("my_input")

# Initialize with config
handler = HandlerClass(config={"some": "config"})

# Use handler
data = handler.collect(context)
```

### List All Handlers

```python
from apps.bfagent.services.handlers.registries import get_all_handlers

all_handlers = get_all_handlers()
# Returns:
# {
#     "input": [...],
#     "processing": [...],
#     "output": [...]
# }
```

## 🎯 Handler Lifecycle

### Input Handler Lifecycle

```
1. __init__(config)
2. validate_config()
3. collect(context) → data
```

### Processing Handler Lifecycle

```
1. __init__(config)
2. validate_config()
3. process(input_data, context) → processed_data
```

### Output Handler Lifecycle

```
1. __init__(config)
2. validate_config()
3. parse(processed_data) → parsed_data
4. validate(parsed_data) → validation_result
5. create_enrichment_responses(parsed_data, project, agent) → responses
6. (User approval)
7. apply(enrichment_response) → created_object
```

## ✅ Best Practices

### 1. Always Define handler_name

```python
class MyHandler(BaseInputHandler):
    handler_name = "my_handler"  # REQUIRED!
```

### 2. Validate Configuration

```python
def validate_config(self):
    if 'required_field' not in self.config:
        raise ValueError("Missing required_field in config")
```

### 3. Provide Good Error Messages

```python
def collect(self, context):
    if 'project' not in context:
        raise ValueError("Missing 'project' in context. Cannot collect data.")
    # ...
```

### 4. Return Consistent Data Structures

```python
# Input handlers: always return dict
def collect(self, context):
    return {"key": "value"}

# Output handlers parse(): always return list
def parse(self, processed_data):
    return [{"obj1": "data"}, {"obj2": "data"}]
```

### 5. Document Your Handler

```python
class MyHandler(BaseInputHandler):
    handler_name = "my_handler"
    description = "Clear description of what this handler does"
    handler_version = "1.0.0"
```

## 🧪 Testing Handlers

```python
import pytest
from apps.bfagent.services.handlers.input.my_handler import MyHandler

def test_my_handler():
    config = {"field": "value"}
    handler = MyHandler(config)
    
    context = {"project": project_instance}
    data = handler.collect(context)
    
    assert "expected_key" in data
```

## 📚 See Also

- `/docs/PIPELINE_HANDLER_SYSTEM.md` - Complete architecture documentation
- `/docs/CONTEXT_BUILDER_CONCEPT.md` - Original concept
- PipelineOrchestrator - Orchestrates the complete pipeline

## 🎊 Status

**Phase 1**: ✅ COMPLETED
- Base Handler Classes
- Handler Registries
- Package Structure

**Phase 2**: ⏳ IN PROGRESS  
- Concrete Handler Implementations
- Pipeline Orchestrator
- ActionTemplate Integration

**Phase 3**: 📋 PLANNED
- UI Integration
- API Endpoints
- Advanced Handlers
