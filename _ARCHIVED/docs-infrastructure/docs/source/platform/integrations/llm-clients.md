# LLM Clients

Fertige Clients für populäre LLM-Provider.

## OpenAI Client

```python
from creative_services.prompts.integration import OpenAIClient

client = OpenAIClient(
    api_key="sk-...",           # Oder OPENAI_API_KEY env var
    default_model="gpt-4o",
)

response = await client.generate(
    system_prompt="You are a helpful assistant.",
    user_prompt="Hello!",
    temperature=0.7,
    max_tokens=1000,
)

print(response.content)
print(f"Cost: ${response.cost_dollars:.4f}")
```

### Unterstützte Models

| Model | Input $/1K | Output $/1K |
|-------|------------|-------------|
| gpt-4o | $0.005 | $0.015 |
| gpt-4o-mini | $0.00015 | $0.0006 |
| gpt-4-turbo | $0.01 | $0.03 |
| gpt-3.5-turbo | $0.0005 | $0.0015 |

## Anthropic Client

```python
from creative_services.prompts.integration import AnthropicClient

client = AnthropicClient(
    api_key="sk-ant-...",
    default_model="claude-3-sonnet-20240229",
)

response = await client.generate(
    system_prompt="You are a helpful assistant.",
    user_prompt="Hello!",
)
```

### Unterstützte Models

| Model | Input $/1K | Output $/1K |
|-------|------------|-------------|
| claude-3-opus | $0.015 | $0.075 |
| claude-3-sonnet | $0.003 | $0.015 |
| claude-3-haiku | $0.00025 | $0.00125 |

## Factory Function

```python
from creative_services.prompts.integration import create_llm_client

client = create_llm_client("openai", api_key="sk-...")
client = create_llm_client("anthropic", api_key="sk-ant-...")
```

## Custom Client

Implementiere das `LLMClient` Protocol:

```python
from creative_services.prompts.execution import LLMClient, LLMResponse

class MyCustomClient:
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> LLMResponse:
        result = await my_api.call(...)
        return LLMResponse(
            content=result.text,
            model="my-model",
            provider="my_provider",
            tokens_input=result.input_tokens,
            tokens_output=result.output_tokens,
            cost_dollars=calculate_cost(...),
        )
```
