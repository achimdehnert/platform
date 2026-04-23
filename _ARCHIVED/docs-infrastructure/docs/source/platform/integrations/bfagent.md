# BFAgent Integration

Fertige Integration für BFAgent Django-Projekte.

## Quick Start

```python
from creative_services.prompts.integration import create_bfagent_executor

executor = create_bfagent_executor()

result = await executor.execute(
    template_key="character.backstory.v1",
    variables={"name": "Elara", "genre": "fantasy"},
)

print(result.content)
```

## Komponenten

### BFAgentRegistry

Nutzt BFAgents `PromptTemplate` Django Model:

```python
from creative_services.prompts.integration import BFAgentRegistry

registry = BFAgentRegistry()
template = registry.get("character.backstory.v1")
```

### BFAgentLLMClient

Nutzt BFAgents LLM-Infrastruktur:

```python
from creative_services.prompts.integration import BFAgentLLMClient

client = BFAgentLLMClient()
response = await client.generate(
    system_prompt="You are a creative writer.",
    user_prompt="Write a character backstory.",
)
```

## Migration von Legacy

### Vorher (Legacy)

```python
from apps.bfagent.services.llm_client import generate_text

result = generate_text(
    provider="openai",
    model="gpt-4",
    system_prompt="You are helpful.",
    user_prompt="Hello!",
)
```

### Nachher (Neues System)

```python
from creative_services.prompts.integration import create_bfagent_executor

executor = create_bfagent_executor()
result = await executor.execute(
    template_key="greeting.v1",
    variables={"name": "World"},
)
```

## Template Adapter

Konvertierung zwischen Django Models und PromptTemplateSpec:

```python
from creative_services.prompts.migration import (
    BFAgentTemplateAdapter,
    convert_bfagent_template,
)

# Django Model → PromptTemplateSpec
spec = convert_bfagent_template(django_template)
```
