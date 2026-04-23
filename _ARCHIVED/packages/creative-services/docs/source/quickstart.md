# Quick Start

## Installation

```bash
pip install -e packages/creative-services
```

## Basic Usage

### 1. Create a Template

```python
from creative_services.prompts import (
    PromptTemplateSpec,
    PromptVariable,
    LLMConfig,
)

template = PromptTemplateSpec(
    template_key="greeting.simple.v1",
    domain_code="examples",
    name="Simple Greeting",
    system_prompt="You are a friendly assistant.",
    user_prompt="Say hello to {{ name }} in a {{ style }} way.",
    variables=[
        PromptVariable(name="name", required=True),
        PromptVariable(name="style", required=False, default="friendly"),
    ],
    llm_config=LLMConfig(
        tier="standard",
        temperature=0.7,
        max_tokens=100,
    ),
)
```

### 2. Save to Registry

```python
from creative_services.prompts import InMemoryRegistry

registry = InMemoryRegistry()
registry.save(template)
```

### 3. Execute with LLM

```python
from creative_services.prompts import PromptExecutor
from creative_services.prompts.integration import OpenAIClient

# Create executor
client = OpenAIClient()
executor = PromptExecutor(
    registry=registry,
    llm_client=client,
    app_name="my_app",
)

# Execute
result = await executor.execute(
    template_key="greeting.simple.v1",
    variables={"name": "Alice"},
)

print(result.content)
# Output: "Hello Alice! It's wonderful to meet you!"
```

## BFAgent Integration

For BFAgent projects, use the pre-configured executor:

```python
from creative_services.prompts.integration import create_bfagent_executor

executor = create_bfagent_executor()

result = await executor.execute(
    template_key="character.backstory.v1",
    variables={"name": "Elara", "genre": "fantasy"},
)
```

## Key Features

- **Type-safe schemas** with Pydantic
- **Injection detection** for security
- **Multiple registries** (Memory, File, Django ORM, Redis)
- **Caching** with TTL support
- **Retry logic** with exponential backoff
- **Prometheus metrics** for observability
