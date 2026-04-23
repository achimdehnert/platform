# BFAgent Integration

Ready-to-use integration for BFAgent Django projects.

## Quick Start

```python
from creative_services.prompts.integration import create_bfagent_executor

# Create executor with BFAgent's infrastructure
executor = create_bfagent_executor()

# Execute a template
result = await executor.execute(
    template_key="character.backstory.v1",
    variables={"name": "Elara", "genre": "fantasy"},
)

print(result.content)
```

## Components

### BFAgentRegistry

Uses BFAgent's `PromptTemplate` Django model:

```python
from creative_services.prompts.integration import BFAgentRegistry

# Automatically uses apps.bfagent.models.PromptTemplate
registry = BFAgentRegistry()

# Get template
template = registry.get("character.backstory.v1")

# Search templates
templates = registry.search(category="character", active_only=True)
```

### BFAgentLLMClient

Uses BFAgent's LLM infrastructure:

```python
from creative_services.prompts.integration import BFAgentLLMClient

client = BFAgentLLMClient()

# Uses BFAgent's generate_text function
response = await client.generate(
    system_prompt="You are a creative writer.",
    user_prompt="Write a character backstory.",
    model="gpt-4",
    temperature=0.7,
)

print(response.content)
print(response.cost_dollars)
```

## Migration from Legacy

### Before (Legacy BFAgent)

```python
from apps.bfagent.services.llm_client import generate_text

result = generate_text(
    provider="openai",
    model="gpt-4",
    system_prompt="You are helpful.",
    user_prompt="Hello!",
)
```

### After (New System)

```python
from creative_services.prompts.integration import create_bfagent_executor

executor = create_bfagent_executor()

# Define template once
template = PromptTemplateSpec(
    template_key="greeting.v1",
    domain_code="general",
    name="Greeting",
    system_prompt="You are helpful.",
    user_prompt="Hello {{ name }}!",
    variables=[PromptVariable(name="name", required=True)],
)
registry.save(template)

# Execute with variables
result = await executor.execute(
    template_key="greeting.v1",
    variables={"name": "World"},
)
```

## BFAgent Template Adapter

Convert between BFAgent Django models and PromptTemplateSpec:

```python
from creative_services.prompts.migration import (
    BFAgentTemplateAdapter,
    convert_bfagent_template,
    convert_to_bfagent_format,
)

# Django model → PromptTemplateSpec
adapter = BFAgentTemplateAdapter()
spec = adapter.from_django_model(django_template)

# PromptTemplateSpec → Django model dict
data = adapter.to_django_model(spec)

# Convenience functions
spec = convert_bfagent_template(django_template)
data = convert_to_bfagent_format(spec)
```

## Configuration

### Custom LLM Selection

```python
from creative_services.prompts.integration import BFAgentLLMClient

client = BFAgentLLMClient(
    default_llm_id=5,  # Use specific LLM from database
)
```

### Cache Settings

```python
executor = create_bfagent_executor(
    app_name="writing_hub",
    enable_cache=True,
    cache_ttl=3600,  # 1 hour
)
```

## Best Practices

1. **Use template_key naming convention**: `domain.purpose.version`
   - `character.backstory.v1`
   - `chapter.generate.v2`
   - `world.description.v1`

2. **Store templates in database**: Use BFAgent admin to manage templates

3. **Enable caching**: Reduces LLM costs for repeated queries

4. **Track executions**: Use `user_id` for analytics

5. **Handle errors gracefully**:
   ```python
   try:
       result = await executor.execute(...)
   except TemplateNotFoundError:
       # Template doesn't exist
   except InjectionDetectedError:
       # Security issue
   except ExecutionError:
       # LLM or other error
   ```
