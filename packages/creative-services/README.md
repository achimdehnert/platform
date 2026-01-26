# Creative Services

Shared AI-powered creative writing services for **BF Agent**, **Travel Beat**, and other platform apps.

## Overview

This package provides modular, reusable creative AI services:

- **LLM Client** - Unified client for OpenAI, Anthropic, Groq, Ollama
- **LLM Registry** - DB-driven LLM configuration (switch models without code changes)
- **Dynamic Client** - Tier-based LLM selection (economy/standard/premium)
- **Usage Tracker** - Token and cost tracking
- **Character Service** - Generate characters with personality, motivation, background
- **World Service** - Create and expand fictional worlds or real location profiles
- **Story Service** - Generate outlines, write chapters, review content

## Installation

```bash
# Basic installation
pip install -e ../platform/packages/creative-services

# With OpenAI support
pip install -e ../platform/packages/creative-services[openai]

# With all LLM providers
pip install -e ../platform/packages/creative-services[all]
```

## Quick Start

### Simple Usage (Environment Variables)

```python
from creative_services import DictRegistry, DynamicLLMClient, LLMTier
import asyncio

# Create registry from environment variables
registry = DictRegistry.from_env()
client = DynamicLLMClient(registry)

# Generate with tier-based selection
async def main():
    response = await client.generate(
        prompt="Write a short story about a traveler",
        system_prompt="You are a creative writer",
        tier=LLMTier.STANDARD,  # Uses GPT-4o-mini or Claude Sonnet
    )
    print(response.content)

asyncio.run(main())
```

### Django Integration (BFAgent/TravelBeat)

```python
from creative_services.adapters import DjangoLLMRegistry, BFAgentLLMBridge
from apps.bfagent.models import Llms

# Option 1: Use Django-backed registry
registry = DjangoLLMRegistry(Llms)
client = DynamicLLMClient(registry)

# Option 2: Use compatibility bridge (no code changes needed)
bridge = BFAgentLLMBridge.with_django_registry(Llms)
result = bridge.generate_text("Hello", tier="premium")
```

### Backward Compatibility (Drop-in Replacement)

```python
# Replace existing BFAgent imports:
# from apps.bfagent.services.llm_client import generate_text

# With:
from creative_services.adapters import generate_text

# Same API, uses new infrastructure
result = generate_text("Hello", tier="standard")
```

## Architecture

```
creative_services/
├── core/
│   ├── llm_client.py      # Unified LLM client (OpenAI, Anthropic, Groq, Ollama)
│   ├── llm_registry.py    # DB-driven LLM configuration & tier selection
│   ├── usage_tracker.py   # Token and cost tracking
│   ├── base_handler.py    # Base class for all handlers
│   └── context.py         # Context classes for handlers
├── adapters/
│   ├── django_adapter.py  # Django ORM integration
│   └── bfagent_compat.py  # BFAgent backward compatibility
├── character/             # Character generation
├── world/                 # World building & location profiles
└── story/                 # Outlines, chapters, structures
```

## LLM Tiers

| Tier | Models | Use Case |
|------|--------|----------|
| **ECONOMY** | GPT-3.5, Claude Haiku, Groq Llama | Simple tasks, high volume |
| **STANDARD** | GPT-4o-mini, Claude Sonnet | Balanced quality/cost |
| **PREMIUM** | GPT-4o, Claude Opus | Complex tasks, best quality |
| **LOCAL** | Ollama (Llama, Mistral) | Offline, privacy-sensitive |

## Supported LLM Providers

- **OpenAI** (GPT-4o, GPT-4o-mini, GPT-3.5)
- **Anthropic** (Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku)
- **Groq** (Llama 3.3 70B - fast & free)
- **Ollama** (Local models)

## Migration Guide

### For BFAgent

1. Install creative-services: `pip install -e ../platform/packages/creative-services`
2. Existing code continues to work (no changes needed)
3. New code can use `DynamicLLMClient` directly
4. Gradually migrate old code to new API

### For TravelBeat

1. Install creative-services
2. Replace direct OpenAI calls with `DynamicLLMClient`
3. Use `LLMTier.STANDARD` for story generation

## License

MIT
