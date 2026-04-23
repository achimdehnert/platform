# Registry

Registries speichern und laden Prompt-Templates. Mehrere Backends werden unterstützt.

## InMemoryRegistry

Für Tests und Entwicklung:

```python
from creative_services.prompts import InMemoryRegistry

registry = InMemoryRegistry()
registry.save(template)
template = registry.get("my.template.v1")
keys = registry.list_keys()
```

## FileRegistry

Templates als YAML/JSON-Dateien:

```python
from creative_services.prompts import FileRegistry

registry = FileRegistry(
    base_path="./templates",
    format="yaml",
)
```

## DjangoRegistry

Für Django-Projekte mit Datenbank-Backend:

```python
from creative_services.prompts import DjangoRegistry

registry = DjangoRegistry.from_model(
    model_class=PromptTemplate,
    domain_code="writing",
)
```

## RedisCache

Für verteiltes Caching:

```python
from creative_services.prompts import RedisCache

cache = RedisCache(
    host="localhost",
    port=6379,
    prefix="prompts:",
    default_ttl=3600,
)
```

## Custom Registry

Implementiere das `TemplateRegistry` Protocol:

```python
class MyCustomRegistry:
    def get(self, template_key: str) -> PromptTemplateSpec | None: ...
    def save(self, template: PromptTemplateSpec) -> None: ...
    def delete(self, template_key: str) -> bool: ...
    def list_keys(self) -> list[str]: ...
```
