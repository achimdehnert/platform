# BF Agent Handler System

## 🎯 Overview

Handler-first architecture for modular, testable, and reusable business logic.

## 📁 Structure

```
handlers/
├── base.py                      # Base handler classes
├── registry.py                  # Central handler registry
├── processing_handlers/         # Business logic handlers
│   ├── enrichment_handler.py    # AI enrichment
│   └── ...
├── input_handlers/              # Input validation (TODO)
└── output_handlers/             # Output persistence (TODO)
```

## 🔧 Handler Types

### 1. **Input Handlers**
Validate and prepare incoming data.

```python
class ProjectInputHandler(BaseInputHandler):
    def validate(self, data: Dict[str, Any]) -> bool:
        # Validate project data
        pass
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Clean and prepare data
        pass
```

### 2. **Processing Handlers**
Execute business logic and AI operations.

```python
class EnrichmentHandler(BaseProcessingHandler):
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Execute AI enrichment
        pass
```

### 3. **Output Handlers**
Persist results to database or files.

```python
class ProjectOutputHandler(BaseOutputHandler):
    def save(self, data: Dict[str, Any]) -> Any:
        # Save to database
        pass
```

## 🚀 Usage Example

### Register Handler:
```python
from apps.bfagent.handlers import HandlerRegistry
from apps.bfagent.handlers.processing_handlers import EnrichmentHandler

registry = HandlerRegistry()
registry.register_processing_handler('enrichment', EnrichmentHandler())
```

### Use Handler in View:
```python
def project_enrich(request, pk):
    registry = HandlerRegistry()
    handler = registry.get_processing_handler('enrichment')
    
    context = {
        'action': 'generate_character_cast',
        'project_id': pk,
        'parameters': request.POST.dict()
    }
    
    result = handler.execute(context)
    return JsonResponse(result)
```

## ✅ Benefits

1. **Modularity** - Each handler has single responsibility
2. **Testability** - Easy to unit test individual handlers
3. **Reusability** - Handlers can be used in multiple contexts
4. **Consistency** - Same pattern across all domains
5. **Integration** - Works with GenAgent handler system

## 📊 Migration Strategy

### Phase 1: Foundation (✅ DONE)
- [x] Base handler classes
- [x] Handler registry
- [x] EnrichmentHandler proof of concept

### Phase 2: Core Handlers (IN PROGRESS)
- [ ] ProjectInputHandler
- [ ] CharacterInputHandler
- [ ] ProjectOutputHandler
- [ ] CharacterOutputHandler

### Phase 3: View Integration
- [ ] Migrate enrichment views to handlers
- [ ] Migrate CRUD views to handlers
- [ ] Update templates

### Phase 4: Complete Migration
- [ ] All services as handlers
- [ ] Unified pipeline system
- [ ] Complete test coverage

## 🎓 Best Practices

1. **Keep handlers focused** - Single responsibility
2. **Use type hints** - Better IDE support
3. **Log operations** - Track handler execution
4. **Handle errors** - Use custom exceptions
5. **Test thoroughly** - Unit tests for each handler

## 🔗 Related Systems

- **GenAgent Handlers** - `/apps/genagent/handlers/`
- **MedTrans Handlers** - `/apps/medtrans/handlers/`
- **Control Center Tools** - `/apps/control_center/`

## 📝 Next Steps

1. Create input handlers for validation
2. Create output handlers for persistence
3. Integrate with existing enrichment system
4. Add comprehensive tests
5. Migrate views to use handlers
