# LLM Service Migration Guide

## Overview

This guide helps migrate existing LLM implementations to the consolidated Core LLM service.

The new service consolidates:
- `apps/bfagent/domains/book_writing/services/llm_service.py`
- `apps/bfagent/agents/handler_generator/llm_client.py`
- `apps/bfagent/services/llm_client.py`
- `apps/bfagent/services/handlers/processing/llm_processor.py`
- `apps/bfagent/services/project_enrichment.py` (LLM-related parts)

## Quick Migration Table

| Old Import | New Import |
|-----------|------------|
| `from apps.bfagent.domains.book_writing.services.llm_service import LLMService` | `from apps.core.services.llm import get_client` |
| `from apps.bfagent.agents.handler_generator.llm_client import StructuredLLMClient` | `from apps.core.services.llm import get_client` |
| `from apps.bfagent.services.llm_client import generate_text, LlmRequest` | `from apps.core.services.llm import generate, LLMRequest` |

## Migration Examples

### Book Writing LLMService

**Before:**
```python
from apps.bfagent.domains.book_writing.services.llm_service import LLMService

llm = LLMService(provider='openai', model='gpt-4')
result = llm.generate_chapter_content(
    prompt="Write chapter 1",
    max_tokens=2000,
    temperature=0.7
)

if result['success']:
    content = result['content']
    usage = result['usage']
```

**After:**
```python
from apps.core.services.llm import get_client

client = get_client("openai", model="gpt-4")
response = client.generate(
    prompt="Write chapter 1",
    max_tokens=2000,
    temperature=0.7
)

if response.success:
    content = response.content
    usage = response.usage  # TokenUsage object
```

### Structured LLM Client

**Before:**
```python
from apps.bfagent.agents.handler_generator.llm_client import StructuredLLMClient
from pydantic import BaseModel

class HandlerSpec(BaseModel):
    name: str
    description: str

client = StructuredLLMClient(provider="anthropic")
result = client.generate_structured(
    prompt="Generate a handler spec",
    response_model=HandlerSpec
)
```

**After:**
```python
from apps.core.services.llm import get_client
from pydantic import BaseModel

class HandlerSpec(BaseModel):
    name: str
    description: str

client = get_client("anthropic")
result = client.generate_structured(
    prompt="Generate a handler spec",
    response_model=HandlerSpec
)
# result is already a HandlerSpec instance
```

### HTTP-based LLM Client

**Before:**
```python
from apps.bfagent.services.llm_client import generate_text, LlmRequest

request = LlmRequest(
    provider="openai",
    api_endpoint="https://api.openai.com/v1",
    api_key=settings.OPENAI_API_KEY,
    model="gpt-4",
    system="You are helpful",
    prompt="Hello"
)

result = generate_text(request)
if result['ok']:
    text = result['text']
```

**After:**
```python
from apps.core.services.llm import get_client

client = get_client("openai", model="gpt-4")
response = client.generate(
    prompt="Hello",
    system_prompt="You are helpful"
)

if response.success:
    text = response.content
```

### LLM Handler Processor

**Before:**
```python
from apps.bfagent.services.handlers.processing.llm_processor import LLMProcessorHandler

handler = LLMProcessorHandler(config={'llm_id': 1})
result = handler.process({'prompt': 'Generate content'}, context)
```

**After:**
```python
from apps.core.services.llm import get_client
from apps.core.handlers import ProcessingHandler, register_handler

@register_handler("llm.process", domain="bfagent")
class LLMProcessor(ProcessingHandler):
    handler_name = "llm.process"
    
    def __init__(self, config=None):
        super().__init__(config)
        self.client = get_client()  # Auto-detect from settings
    
    def process(self, data, context):
        response = self.client.generate(data.get('prompt'))
        return {
            'success': response.success,
            'content': response.content,
            'usage': response.usage.to_dict() if response.usage else None
        }
```

## Cost Tracking

**Before (manual):**
```python
# Various manual cost calculation implementations
costs = {
    'gpt-4': {'input': 0.03 / 1000, 'output': 0.06 / 1000}
}
cost = usage['prompt_tokens'] * costs[model]['input'] + ...
```

**After:**
```python
from apps.core.services.llm import CostTracker, get_client

tracker = CostTracker(budget_limit=10.0)  # $10 budget
client = get_client("openai", model="gpt-4")

response = client.generate("Hello")
cost = tracker.record(response, provider="openai", model="gpt-4")

print(f"This request cost: ${cost:.4f}")
print(f"Total spent: ${tracker.get_total_cost():.4f}")
print(f"Remaining budget: ${tracker.get_remaining_budget():.4f}")
```

## Token Estimation

**Before:**
```python
def estimate_tokens(text):
    return len(text) // 4
```

**After:**
```python
from apps.core.services.llm import estimate_tokens, truncate_to_tokens

# Estimate tokens (uses tiktoken if available)
tokens = estimate_tokens(text, model="gpt-4")

# Truncate to fit context
truncated = truncate_to_tokens(text, max_tokens=4000)
```

## Streaming

**Before:**
```python
# Various streaming implementations
response = client.chat.completions.create(stream=True, ...)
for chunk in response:
    ...
```

**After:**
```python
from apps.core.services.llm import get_client

client = get_client("openai")

for chunk in client.generate_stream("Tell me a story"):
    print(chunk, end="", flush=True)
```

## Error Handling

**Before:**
```python
try:
    result = llm.generate(prompt)
except Exception as e:
    if 'rate_limit' in str(e):
        # handle rate limit
    elif 'authentication' in str(e):
        # handle auth error
```

**After:**
```python
from apps.core.services.llm import (
    get_client,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMConnectionError
)

client = get_client()

try:
    response = client.generate(prompt)
except LLMRateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
except LLMAuthenticationError as e:
    print("Invalid API key")
except LLMConnectionError as e:
    print("Network error")
```

## Django Settings

Add to your settings:

```python
# LLM Configuration
LLM_PROVIDER = "openai"  # or "anthropic"
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")

# Optional model defaults
LLM_MODEL = "gpt-4"
LLM_DEFAULT_TEMPERATURE = 0.7
LLM_DEFAULT_MAX_TOKENS = 4096
```

## Checklist

- [ ] Update all imports to use `apps.core.services.llm`
- [ ] Replace `LLMService` with `get_client()`
- [ ] Replace `StructuredLLMClient` with `client.generate_structured()`
- [ ] Replace `generate_text()` with `client.generate()`
- [ ] Update response handling (`result['content']` → `response.content`)
- [ ] Use CostTracker for cost tracking
- [ ] Add proper exception handling
- [ ] Update Django settings
- [ ] Remove old LLM service files after verification
