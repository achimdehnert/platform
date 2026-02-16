# chat-agent

Shared chat agent framework for building domain-specific AI assistants
with tool-based interactions across platform apps.

**Package**: `platform/packages/chat-agent`
**Version**: 0.1.0
**Python**: ≥ 3.11

## Architecture

```text
chat_agent/
├── agent.py         # ChatAgent — core agent loop
├── composite.py     # CompositeToolkit (merge multiple DomainToolkits)
├── toolkit.py       # DomainToolkit base class
├── session.py       # Session backend (memory/Redis)
└── __init__.py      # Public API exports
```

## Core Components

### ChatAgent

Core agent that processes user messages, dispatches to tools, and
manages conversation sessions.

### DomainToolkit

Base class for domain-specific tool collections:

```python
from chat_agent import DomainToolkit

class MyToolkit(DomainToolkit):
    name = "my-domain"
    tools = [...]
```

### CompositeToolkit

Merges multiple toolkits into a single agent:

```python
from chat_agent import CompositeToolkit

toolkit = CompositeToolkit([
    TravelBeatToolkit(),
    StoryToolkit(),
])
agent = ChatAgent(toolkit=toolkit)
```

## Usage in Apps

- **travel-beat**: `TravelBeatToolkit` + `StoryToolkit` via `CompositeToolkit`
- **bfagent**: Chapter/Story agent tools (planned)

See [ADR-036: Chat-Agent Ecosystem](../governance/adrs.md) for design decisions.
