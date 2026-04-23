# Registry

Registries store and retrieve prompt templates. Multiple backends are supported.

## InMemoryRegistry

For testing and development:

```python
from creative_services.prompts import InMemoryRegistry

registry = InMemoryRegistry()

# Save template
registry.save(template)

# Get template
template = registry.get("my.template.v1")

# Check existence
exists = registry.exists("my.template.v1")

# List all keys
keys = registry.list_keys()

# Search
results = registry.search(query="character", category="writing")

# Delete
registry.delete("my.template.v1")
```

## FileRegistry

Store templates as YAML or JSON files:

```python
from creative_services.prompts import FileRegistry

# YAML format (default)
registry = FileRegistry(
    base_path="./templates",
    format="yaml",
)

# JSON format
registry = FileRegistry(
    base_path="./templates",
    format="json",
)
```

File structure:
```
templates/
├── writing/
│   ├── character.backstory.v1.yaml
│   └── chapter.generate.v1.yaml
└── analysis/
    └── review.content.v1.yaml
```

## DjangoRegistry

For Django projects with database-backed storage:

```python
from creative_services.prompts import DjangoRegistry

# With your Django model
from myapp.models import PromptTemplate

registry = DjangoRegistry.from_model(
    model_class=PromptTemplate,
    domain_code="writing",
)

# Or with custom adapter
registry = DjangoRegistry(adapter=MyCustomAdapter())
```

### Expected Model Fields

```python
class PromptTemplate(models.Model):
    template_key = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    system_prompt = models.TextField()
    user_prompt_template = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    required_variables = models.JSONField(default=list)
    optional_variables = models.JSONField(default=list)
    variable_defaults = models.JSONField(default=dict)
    max_tokens = models.IntegerField(null=True)
    temperature = models.FloatField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Async Support

```python
from creative_services.prompts import AsyncDjangoRegistry

registry = AsyncDjangoRegistry.from_model(PromptTemplate)

# Async operations
template = await registry.get("my.template.v1")
await registry.save(template)
keys = await registry.list_keys()
```

## RedisCache

For distributed caching of execution results:

```python
from creative_services.prompts import RedisCache

cache = RedisCache(
    host="localhost",
    port=6379,
    db=0,
    prefix="prompts:",
    default_ttl=3600,
)

# Use with executor
executor = PromptExecutor(
    registry=registry,
    llm_client=client,
    cache=cache,
)
```

### Async Redis

```python
from creative_services.prompts.execution import AsyncRedisCache

cache = AsyncRedisCache(
    url="redis://localhost:6379/0",
    prefix="prompts:",
)
```

## Custom Registry

Implement the `TemplateRegistry` protocol:

```python
from creative_services.prompts.registry import TemplateRegistry

class MyCustomRegistry:
    def get(self, template_key: str) -> PromptTemplateSpec | None:
        ...
    
    def save(self, template: PromptTemplateSpec) -> None:
        ...
    
    def delete(self, template_key: str) -> bool:
        ...
    
    def list_keys(self) -> list[str]:
        ...
    
    def exists(self, template_key: str) -> bool:
        ...
```
