# chat-agent

Domain-agnostic Chat Agent with Tool-Use loop — platform package per ADR-034 §3.

## Core Components

- **ChatAgent**: Core Tool-Use loop (LLM → tool calls → execute → LLM)
- **DomainToolkit**: ABC for app-specific tool collections
- **SessionBackend**: Protocol for pluggable session storage (InMemory, Redis)
- **ToolkitRegistry**: Global registry for toolkit discovery

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

```python
from chat_agent import ChatAgent, InMemorySessionBackend

agent = ChatAgent(
    toolkit=MyToolkit(),
    completion=my_llm_client,
    session_backend=InMemorySessionBackend(),
    system_prompt="You are a helpful assistant.",
)

response = await agent.chat(
    session_id="user-123",
    user_message="How many rooms are on floor 2?",
    tenant_id="tenant-abc",
)
```
