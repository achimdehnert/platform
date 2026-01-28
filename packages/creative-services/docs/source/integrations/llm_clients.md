# LLM Clients

Ready-to-use clients for popular LLM providers.

## OpenAI Client

```python
from creative_services.prompts.integration import OpenAIClient

client = OpenAIClient(
    api_key="sk-...",           # Or use OPENAI_API_KEY env var
    organization="org-...",      # Optional
    default_model="gpt-4o",
)

response = await client.generate(
    system_prompt="You are a helpful assistant.",
    user_prompt="Hello!",
    model="gpt-4o",              # Override default
    temperature=0.7,
    max_tokens=1000,
)

print(response.content)
print(f"Cost: ${response.cost_dollars:.4f}")
print(f"Tokens: {response.tokens_total}")
```

### Supported Models

| Model | Input $/1K | Output $/1K |
|-------|------------|-------------|
| gpt-4o | $0.005 | $0.015 |
| gpt-4o-mini | $0.00015 | $0.0006 |
| gpt-4-turbo | $0.01 | $0.03 |
| gpt-4 | $0.03 | $0.06 |
| gpt-3.5-turbo | $0.0005 | $0.0015 |

## Anthropic Client

```python
from creative_services.prompts.integration import AnthropicClient

client = AnthropicClient(
    api_key="sk-ant-...",       # Or use ANTHROPIC_API_KEY env var
    default_model="claude-3-sonnet-20240229",
)

response = await client.generate(
    system_prompt="You are a helpful assistant.",
    user_prompt="Hello!",
    temperature=0.7,
    max_tokens=1000,
)
```

### Supported Models

| Model | Input $/1K | Output $/1K |
|-------|------------|-------------|
| claude-3-opus-20240229 | $0.015 | $0.075 |
| claude-3-sonnet-20240229 | $0.003 | $0.015 |
| claude-3-haiku-20240307 | $0.00025 | $0.00125 |
| claude-3-5-sonnet-20240620 | $0.003 | $0.015 |

## Factory Function

Create client by provider name:

```python
from creative_services.prompts.integration import create_llm_client

# OpenAI
client = create_llm_client("openai", api_key="sk-...")

# Anthropic
client = create_llm_client("anthropic", api_key="sk-ant-...")
```

## Error Handling

```python
from creative_services.prompts import LLMError

try:
    response = await client.generate(...)
except LLMError as e:
    print(f"Provider: {e.provider}")
    print(f"Status: {e.status_code}")
    print(f"Retryable: {e.retryable}")
    
    if e.retryable:
        # Retry logic
        pass
```

## Custom Client

Implement the `LLMClient` protocol:

```python
from creative_services.prompts.execution import LLMClient, LLMResponse

class MyCustomClient:
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs,
    ) -> LLMResponse:
        # Your implementation
        result = await my_llm_api.call(...)
        
        return LLMResponse(
            content=result.text,
            model=model,
            provider="my_provider",
            tokens_input=result.input_tokens,
            tokens_output=result.output_tokens,
            cost_dollars=calculate_cost(...),
        )
```

## Using with Executor

```python
from creative_services.prompts import PromptExecutor, InMemoryRegistry
from creative_services.prompts.integration import OpenAIClient

executor = PromptExecutor(
    registry=InMemoryRegistry(),
    llm_client=OpenAIClient(),
    app_name="my_app",
)

result = await executor.execute(
    template_key="my.template.v1",
    variables={"name": "Alice"},
)
```
