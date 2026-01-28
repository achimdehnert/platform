# Schemas

All schemas are Pydantic models with `frozen=True` for immutability.

## PromptTemplateSpec

The main template definition schema.

```python
from creative_services.prompts import PromptTemplateSpec

template = PromptTemplateSpec(
    # Required
    template_key="domain.purpose.v1",  # Unique identifier
    domain_code="writing",              # Domain grouping
    name="My Template",                 # Human-readable name
    system_prompt="You are...",         # System prompt (Jinja2)
    user_prompt="Generate {{ x }}",     # User prompt (Jinja2)
    
    # Optional
    description="Template description",
    category="generation",
    schema_version=1,
    variables=[...],                    # Variable definitions
    llm_config=LLMConfig(...),          # LLM settings
    is_active=True,
    tags=["tag1", "tag2"],
    
    # Security
    check_injection=True,               # Enable injection detection
    sanitize_user_input=True,           # Sanitize variables
    max_variable_length=10000,          # Max chars per variable
)
```

## PromptVariable

Defines a template variable with type and validation.

```python
from creative_services.prompts import PromptVariable, VariableType

variable = PromptVariable(
    name="character_name",
    var_type=VariableType.STRING,       # STRING, INTEGER, FLOAT, BOOLEAN, LIST, OBJECT
    required=True,
    default=None,                       # Default value if not required
    description="Name of the character",
    
    # Validation
    min_length=1,
    max_length=100,
    pattern=r"^[A-Za-z ]+$",            # Regex pattern
    
    # Security
    check_injection=True,               # Check this variable for injection
    sanitize=True,                      # Sanitize this variable
)
```

### Variable Types

| Type | Python Type | Example |
|------|-------------|---------|
| `STRING` | `str` | `"Hello"` |
| `INTEGER` | `int` | `42` |
| `FLOAT` | `float` | `3.14` |
| `BOOLEAN` | `bool` | `True` |
| `LIST` | `list` | `["a", "b"]` |
| `OBJECT` | `dict` | `{"key": "value"}` |

## LLMConfig

Configuration for LLM execution.

```python
from creative_services.prompts import LLMConfig, RetryConfig

config = LLMConfig(
    # Tier-based selection (recommended)
    tier="standard",                    # fast, standard, quality, premium
    
    # Or direct model override
    provider="openai",
    model="gpt-4o",
    
    # Generation parameters
    temperature=0.7,
    max_tokens=1000,
    top_p=1.0,
    frequency_penalty=0.0,
    presence_penalty=0.0,
    
    # Timeout
    timeout_seconds=60.0,
    
    # Retry configuration
    retry=RetryConfig(
        max_attempts=3,
        initial_delay_seconds=1.0,
        max_delay_seconds=30.0,
        exponential_base=2.0,
    ),
)
```

## PromptExecution

Record of a single execution (created automatically).

```python
from creative_services.prompts import PromptExecution, ExecutionStatus

# Automatically created by PromptExecutor
execution = PromptExecution(
    execution_id=uuid4(),
    template_key="my.template.v1",
    app_name="my_app",
    user_id="user_123",
    
    # Input
    variables_provided={"name": "Alice"},
    rendered_system_prompt="You are...",
    rendered_user_prompt="Hello Alice...",
    
    # Output
    status=ExecutionStatus.SUCCESS,     # PENDING, SUCCESS, FAILED, CACHED
    response_text="Hello! Nice to meet you, Alice!",
    
    # LLM Info
    llm_provider="openai",
    llm_model="gpt-4o",
    
    # Metrics
    tokens_input=50,
    tokens_output=20,
    cost_dollars=0.001,
    duration_seconds=1.5,
    
    # Cache
    from_cache=False,
    
    # Timestamps
    started_at=datetime.now(timezone.utc),
    completed_at=datetime.now(timezone.utc),
)

# Computed properties
execution.tokens_total      # 70
execution.is_success        # True
execution.is_complete       # True
```

## ExecutionResult

Returned by `PromptExecutor.execute()`.

```python
result = await executor.execute(...)

result.success          # bool - Was execution successful?
result.content          # str - LLM response text
result.execution        # PromptExecution - Full execution record
result.from_cache       # bool - Was response from cache?
result.error            # Optional[str] - Error message if failed
```
