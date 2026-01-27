# Schemas

Alle Schemas sind Pydantic Models mit `frozen=True` für Immutabilität.

## PromptTemplateSpec

Die Haupt-Template-Definition:

```python
from creative_services.prompts import PromptTemplateSpec

template = PromptTemplateSpec(
    # Pflichtfelder
    template_key="domain.purpose.v1",
    domain_code="writing",
    name="My Template",
    system_prompt="You are...",
    user_prompt="Generate {{ x }}",
    
    # Optional
    description="Template description",
    variables=[...],
    llm_config=LLMConfig(...),
    is_active=True,
    tags=["tag1", "tag2"],
    
    # Security
    check_injection=True,
    sanitize_user_input=True,
    max_variable_length=10000,
)
```

## PromptVariable

Definiert eine Template-Variable:

```python
from creative_services.prompts import PromptVariable, VariableType

variable = PromptVariable(
    name="character_name",
    var_type=VariableType.STRING,
    required=True,
    default=None,
    description="Name of the character",
    min_length=1,
    max_length=100,
    pattern=r"^[A-Za-z ]+$",
    check_injection=True,
    sanitize=True,
)
```

## LLMConfig

Konfiguration für LLM-Ausführung:

```python
from creative_services.prompts import LLMConfig, RetryConfig

config = LLMConfig(
    tier="standard",
    provider="openai",
    model="gpt-4o",
    temperature=0.7,
    max_tokens=1000,
    timeout_seconds=60.0,
    retry=RetryConfig(
        max_attempts=3,
        initial_delay_seconds=1.0,
        max_delay_seconds=30.0,
    ),
)
```

## PromptExecution

Record einer Ausführung (automatisch erstellt):

```python
execution.execution_id      # UUID
execution.template_key      # "my.template.v1"
execution.status           # SUCCESS, FAILED, CACHED
execution.response_text    # LLM-Antwort
execution.tokens_total     # Input + Output
execution.cost_dollars     # Kosten
execution.duration_seconds # Dauer
```
