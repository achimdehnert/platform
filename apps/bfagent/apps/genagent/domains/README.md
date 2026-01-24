# GenAgent Domain System

## Overview

The GenAgent Domain System provides a **Universal Domain Template Framework** for defining reusable, phase-based workflows across different domains (books, forensics, thesis, etc.).

## Architecture

```
apps/genagent/domains/
├── __init__.py           # Public API exports
├── base.py               # Core template classes
├── registry.py           # Domain template registry
├── installer.py          # Template→DB conversion
├── test_domains.py       # Test suite
├── run_tests.py          # Test runner
└── templates/            # Domain template definitions
    ├── __init__.py
    └── book.py          # Book writing domain
```

## Core Concepts

### 1. DomainTemplate
Defines a complete workflow for a specific domain:
- **domain_id**: Unique identifier (e.g., 'book', 'thesis')
- **display_name**: Human-readable name
- **phases**: List of PhaseTemplate objects
- **required_fields**: Context fields needed to start
- **handlers**: Handler class mappings

### 2. PhaseTemplate
Represents a logical grouping of actions:
- **name**: Phase name (e.g., "Planning", "Development")
- **actions**: List of ActionTemplate objects
- **execution_mode**: Sequential, parallel, or conditional
- **color**: UI color code

### 3. ActionTemplate
Atomic work unit within a phase:
- **name**: Action name
- **handler_class**: Full path to handler (e.g., `apps.genagent.handlers.demo_handlers.WelcomeHandler`)
- **config**: Handler configuration
- **dependencies**: Required previous actions

## Quick Start

### 1. Define a Domain Template

```python
# apps/genagent/domains/templates/my_domain.py
from apps.genagent.domains import (
    DomainTemplate,
    PhaseTemplate,
    ActionTemplate,
    DomainRegistry,
)

MY_DOMAIN = DomainTemplate(
    domain_id="my_domain",
    display_name="My Workflow",
    description="Custom workflow example",
    phases=[
        PhaseTemplate(
            name="Setup",
            description="Initial setup",
            order=0,
            actions=[
                ActionTemplate(
                    name="Validate Input",
                    handler_class="apps.genagent.handlers.demo_handlers.DataValidationHandler",
                    config={
                        "required_fields": ["title", "description"]
                    },
                ),
            ]
        ),
    ],
    required_fields=["title", "description"],
)

# Auto-register
DomainRegistry.register(MY_DOMAIN)
```

### 2. Use the Domain

```python
from apps.genagent.domains import DomainRegistry, install_domain

# Get template
template = DomainRegistry.get('my_domain')
print(f"Template: {template.display_name}")
print(f"Phases: {len(template.phases)}")

# Install to database (dry run)
context = {
    'title': 'My Project',
    'description': 'Project description'
}
install_domain('my_domain', context, dry_run=True)

# Real installation
phase_id = install_domain('my_domain', context, dry_run=False)
print(f"Created workflow starting at phase {phase_id}")
```

## Testing

### Run Tests

```bash
# Using Django shell
python manage.py shell -c "exec(open('apps/genagent/domains/test_domains.py', encoding='utf-8').read())"

# Or direct Python (recommended)
python apps/genagent/domains/run_tests.py
```

### Expected Output

```
======================================================================
TESTING GENAGENT DOMAIN SYSTEM
======================================================================

1. Testing Domain Template Import...
   [OK] Imports successful

2. Testing Domain Registry...
   [OK] Registry contains 1 templates
   [INFO] Available domains: book

3. Testing Book Template Retrieval...
   [OK] Retrieved template: Book Writing
   [INFO] Phases: 3
   [INFO] Total Actions: 5

4. Testing Template Validation...
   [OK] Template validation: True

5. Testing Template Statistics...
   [OK] Statistics:
      - Total Phases: 3
      - Total Actions: 5
      - Required Phases: 3
      - Est. Duration: 0.01 hours

6. Domain Registry Summary:
   [Shows detailed registry information]

7. Testing Domain Installer (Dry Run)...
   [OK] Installer dry run complete

[SUCCESS] ALL TESTS PASSED!
```

## Domain Registry API

### Registration

```python
from apps.genagent.domains import DomainRegistry

# Register template
DomainRegistry.register(template)

# Check if exists
if DomainRegistry.exists('book'):
    print("Book domain available")

# Get template
template = DomainRegistry.get('book')

# List all
templates = DomainRegistry.list_all()
domain_ids = DomainRegistry.list_ids()
```

### Search & Filter

```python
# Search by query
results = DomainRegistry.search(query='writing')

# Filter by category
creative_domains = DomainRegistry.get_by_category('creative')

# Filter by tags
ai_domains = DomainRegistry.search(tags=['ai-assisted'])

# Get statistics
stats = DomainRegistry.get_statistics()
print(f"Total templates: {stats['total_templates']}")
```

### Import/Export

```python
from pathlib import Path

# Export single template
DomainRegistry.export_to_json(
    Path('exports/book.json'),
    domain_id='book'
)

# Export all templates
DomainRegistry.export_to_json(
    Path('exports/all_domains.json')
)

# Import templates
imported = DomainRegistry.import_from_json(
    Path('exports/book.json')
)
```

## Domain Installer API

### Basic Installation

```python
from apps.genagent.domains import DomainInstaller

installer = DomainInstaller(dry_run=False)

# Install from registry
phase_id = installer.install_from_registry(
    'book',
    initial_context={'title': 'My Novel', 'genre': 'fantasy'}
)

# Install specific template
phase_id = installer.install_template(template, context)
```

### Batch Installation

```python
# Install multiple domains
results = installer.batch_install(
    domain_ids=['book', 'thesis', 'report'],
    initial_contexts=[
        {'title': 'Novel'},
        {'title': 'PhD Thesis'},
        {'title': 'Report'}
    ]
)

for domain_id, phase_id in results.items():
    if phase_id:
        print(f"✓ {domain_id}: phase {phase_id}")
    else:
        print(f"✗ {domain_id}: failed")
```

## Creating Custom Handlers

Handlers must inherit from `BaseHandler`:

```python
from apps.genagent.handlers import BaseHandler, register_handler

@register_handler
class MyCustomHandler(BaseHandler):
    """Custom handler for my workflow"""
    
    def execute(self, context: Dict[str, Any], test_mode: bool = False) -> Dict[str, Any]:
        """Execute the handler"""
        # Access configuration
        my_setting = self.config.get('my_setting', 'default')
        
        # Read from context
        input_value = context.get('input_field')
        
        # Process
        output = f"Processed: {input_value} with {my_setting}"
        
        # Return result
        return {
            'success': True,
            'output': output,
            'metadata': {'processed_at': datetime.now()}
        }
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "type": "object",
            "properties": {
                "my_setting": {
                    "type": "string",
                    "default": "default",
                    "description": "My setting description"
                }
            }
        }
```

## Best Practices

### 1. Template Design
- Use descriptive domain_ids (lowercase, underscores)
- Group related actions into phases
- Define clear dependencies
- Provide meaningful descriptions

### 2. Handler Selection
- Reuse existing handlers when possible
- Create domain-specific handlers when needed
- Keep handlers focused (single responsibility)
- Always validate inputs

### 3. Context Fields
- Document required fields in template
- Use meaningful field names
- Validate context before installation
- Provide sensible defaults

### 4. Testing
- Test templates with `dry_run=True` first
- Validate all handlers are registered
- Check dependencies are correct
- Test with various context values

## Integration with Existing System

The domain system integrates seamlessly with the existing GenAgent infrastructure:

1. **Phase/Action Models**: Templates install directly to existing DB models
2. **Handler Registry**: Uses existing handler registration system
3. **Execution Engine**: Installed phases execute through standard engine
4. **UI**: Can be integrated with existing workflow UI

## Troubleshooting

### Template Not Found
```python
# Check registration
print(DomainRegistry.list_ids())

# Ensure import
from apps.genagent.domains.templates import book  # noqa: F401
```

### Handler Not Available
```python
# Verify handler path
handler_class = "apps.genagent.handlers.demo_handlers.WelcomeHandler"

# Check registration
from apps.genagent.handlers import HandlerRegistry
print(HandlerRegistry.list_all())
```

### Validation Errors
```python
# Validate template
try:
    template.validate()
    print("Valid!")
except ValueError as e:
    print(f"Validation error: {e}")

# Check context
missing = template.validate_required_fields(context)
if missing:
    print(f"Missing fields: {missing}")
```

## Next Steps

1. **Create more domains**: Add templates for different workflows
2. **Custom handlers**: Develop domain-specific handlers
3. **UI Integration**: Connect templates to workflow UI
4. **Advanced features**: Implement branching, async execution
5. **Testing**: Comprehensive test coverage

## API Reference

See inline documentation in:
- `apps/genagent/domains/base.py` - Core classes
- `apps/genagent/domains/registry.py` - Registry API
- `apps/genagent/domains/installer.py` - Installer API

## Version

**v1.0.0** - Initial implementation of Hybrid-Ansatz Evolution Foundation
