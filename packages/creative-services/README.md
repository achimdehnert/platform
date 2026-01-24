# Creative Services

Shared AI-powered creative writing services for **BF Agent** and **Travel Beat**.

## Overview

This package provides modular, reusable creative AI services:

- **Character Service** - Generate characters with personality, motivation, background
- **World Service** - Create and expand fictional worlds or real location profiles
- **Story Service** - Generate outlines, write chapters, review content
- **Scene Service** - Analyze text for visual scene extraction
- **Illustration Service** - Style configuration and image generation
- **Quality Service** - Review and score written content

## Installation

```bash
# Basic installation
pip install creative-services

# With OpenAI support
pip install creative-services[openai]

# With all LLM providers
pip install creative-services[all]
```

## Quick Start

```python
from creative_services.character import CharacterService, CharacterContext

# Initialize service
service = CharacterService()

# Generate a character
result = service.generate(
    context=CharacterContext(
        genre="fantasy",
        role="protagonist",
        traits=["brave", "curious"],
    )
)

print(result.character.name)
print(result.character.description)
```

## Architecture

```
creative_services/
├── core/           # Base classes, LLM client, contexts
├── character/      # Character generation
├── world/          # World building & location profiles
├── story/          # Outlines, chapters, structures
├── scene/          # Scene analysis for illustrations
├── illustration/   # Style config & image generation
└── quality/        # Content review & scoring
```

## Supported LLM Providers

- **OpenAI** (GPT-4, GPT-4o-mini)
- **Anthropic** (Claude 3.5 Sonnet)
- **Groq** (Llama 3.3 70B)
- **Ollama** (Local models)

## License

MIT
