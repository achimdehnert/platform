# 🎨 BF Agent Image Generation System

Professional multi-provider image generation system integrated with the BF Agent Handler Framework.

**Version:** 1.0.0  
**Author:** BF Agent Team  
**Status:** Production-Ready ✅

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Installation](#installation)
5. [Quick Start](#quick-start)
6. [Configuration](#configuration)
7. [Usage Examples](#usage-examples)
8. [Integration with BF Agent](#integration-with-bf-agent)
9. [Cost Estimation](#cost-estimation)
10. [API Reference](#api-reference)

---

## 🎯 Overview

This system provides a unified interface for generating images using multiple AI providers (OpenAI DALL-E 3, Stability AI). It follows the **BF Agent Handler Framework** three-phase pattern and includes:

- ✅ **Multi-Provider Support**: OpenAI & Stability AI (extensible)
- ✅ **Automatic Fallback**: Switch providers on failure
- ✅ **Cost Tracking**: Real-time cost monitoring
- ✅ **Transaction Safety**: Rollback on errors
- ✅ **Pydantic Validation**: Type-safe inputs/outputs
- ✅ **Batch Processing**: Generate multiple images efficiently
- ✅ **Style Consistency**: Perfect for book illustrations

---

## ⭐ Features

### Core Features

- **Multiple Providers**: OpenAI DALL-E 3, Stability AI SD3
- **Load Balancing**: Distribute requests across providers
- **Automatic Failover**: Seamless provider switching
- **Cost Optimization**: Always select cheapest option
- **Rate Limiting**: Respect API limits
- **Retry Logic**: Exponential backoff on failures

### Handler Types

1. **SingleImageHandler**: Generate single images
2. **BatchImageHandler**: Generate multiple images
3. **IllustrationGenerationHandler**: Book/document illustrations (BF Agent Educational System)

### Advanced Features

- **Prompt Enhancement**: Automatic style consistency
- **Character Consistency**: Maintain character appearances
- **Metadata Tracking**: Comprehensive logging
- **File Management**: Automatic saving & organization
- **Dry-Run Mode**: Test without API calls

---

## 🏗️ Architecture

```
image_generation/
├── handlers/                    # Handler implementations
│   ├── base_image_handler.py   # Abstract base (3-phase pattern)
│   ├── generic_image_handler.py # Single & batch handlers
│   └── illustration_handler.py  # Book illustration handler
│
├── providers/                   # Provider implementations
│   ├── base_provider.py         # Abstract provider interface
│   ├── openai_provider.py       # DALL-E 3 implementation
│   ├── stability_provider.py    # Stable Diffusion 3
│   └── provider_manager.py      # Multi-provider orchestration
│
├── schemas/                     # Pydantic schemas
│   ├── input_schemas.py         # Input validation
│   └── output_schemas.py        # Output formatting
│
├── config/                      # Configuration
│   ├── providers.yaml           # Provider settings
│   └── config_loader.py         # Config management
│
├── utils/                       # Utilities
│   ├── image_utils.py           # Image processing
│   ├── cost_tracker.py          # Cost monitoring
│   └── prompt_optimizer.py      # Prompt enhancement
│
└── tests/                       # Test suite
    ├── test_handlers.py
    ├── test_providers.py
    └── test_integration.py
```

### Three-Phase Handler Pattern

All handlers follow BF Agent's standard pattern:

```python
1. INPUT PHASE:    Validate with Pydantic schemas
2. PROCESSING PHASE: Execute core logic
3. OUTPUT PHASE:   Format & return results
```

---

## 📦 Installation

### Prerequisites

```bash
python >= 3.9
Django >= 4.0  # For BF Agent integration
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
openai>=1.0.0
requests>=2.28.0
pydantic>=2.0.0
structlog>=23.0.0
PyYAML>=6.0
pillow>=10.0.0  # For image processing
```

### Set Environment Variables

```bash
export OPENAI_API_KEY="sk-..."
export STABILITY_API_KEY="sk-..."
```

---

## 🚀 Quick Start

### 1. Basic Setup

```python
from image_generation.config import get_config
from image_generation.providers import (
    OpenAIProvider,
    StabilityAIProvider,
    ProviderManager,
    ProviderConfig,
    SelectionStrategy
)
from image_generation.handlers import SingleImageHandler

# Load configuration
config = get_config()

# Setup providers
openai_config = ProviderConfig(
    api_key=config.get_provider_config('openai')['api_key'],
    model="dall-e-3"
)
openai_provider = OpenAIProvider(openai_config)

stability_config = ProviderConfig(
    api_key=config.get_provider_config('stability')['api_key'],
    model="sd3"
)
stability_provider = StabilityAIProvider(stability_config)

# Create provider manager
manager = ProviderManager(
    providers=[openai_provider, stability_provider],
    strategy=SelectionStrategy.CHEAPEST,
    enable_fallback=True
)

# Create handler
handler = SingleImageHandler(provider_manager=manager)

# Generate image
result = handler.handle({
    'prompt': 'A beautiful sunset over mountains',
    'provider': 'auto',  # Automatic selection
    'size': '1024x1024',
    'quality': 'standard'
})

print(f"Image URL: {result['image']['url']}")
print(f"Cost: ${result['total_cost_cents']/100:.2f}")
```

### 2. Generate Book Illustrations (BF Agent Educational System)

```python
from image_generation.handlers import IllustrationGenerationHandler

# Create handler
illustration_handler = IllustrationGenerationHandler(
    provider_manager=manager,
    config={'save_images': True}
)

# Generate illustrations for chapter
result = illustration_handler.handle({
    'book_id': 1,
    'chapter_id': 1,
    'scene_descriptions': [
        'Max and Mia arriving at Brain Island',
        'Children solving a colorful puzzle',
        'Celebration with their companion Brainy'
    ],
    'illustration_style': 'watercolor children\'s book',
    'character_descriptions': {
        'Max': 'boy with brown hair, blue shirt, curious expression',
        'Mia': 'girl with blonde hair, red dress, excited smile',
        'Brainy': 'friendly blue owl with glasses'
    },
    'aspect_ratio': '16:9',
    'save_to_directory': '/output/illustrations/chapter_1',
    'provider': 'openai'
})

print(f"Generated {result['successful_illustrations']} illustrations")
print(f"Total cost: ${result['total_cost_cents']/100:.2f}")
print(f"Saved to: {result['illustration_directory']}")
```

---

## ⚙️ Configuration

### Edit `config/providers.yaml`

```yaml
providers:
  openai:
    enabled: true
    model: "dall-e-3"
    default_size: "1024x1024"
    default_quality: "standard"
    rate_limit_per_minute: 5
  
  stability:
    enabled: true
    model: "sd3"
    default_aspect_ratio: "1:1"
    rate_limit_per_minute: 10

manager:
  selection_strategy: "cheapest"  # or: fastest, priority, round_robin
  enable_fallback: true
  priority_order:
    - "openai"
    - "stability"

handlers:
  illustration:
    max_parallel: 3
    quality: "standard"
    default_provider: "openai"
```

---

## 💡 Usage Examples

### Example 1: Single Image with Custom Style

```python
result = handler.handle({
    'prompt': 'A futuristic city at night',
    'provider': 'stability',
    'style': 'cinematic',
    'negative_prompt': 'blurry, low quality',
    'quality': 'high',
    'save_to_path': './output/city.png'
})
```

### Example 2: Batch Generation

```python
from image_generation.handlers import BatchImageHandler

batch_handler = BatchImageHandler(provider_manager=manager)

result = batch_handler.handle({
    'prompts': [
        'A red apple',
        'A blue ocean',
        'A green forest',
        'A yellow sun'
    ],
    'distribute_load': True,  # Distribute across providers
    'save_to_directory': './output/batch',
    'naming_pattern': 'image_{index:03d}.png'
})

print(f"Success rate: {result['success_rate']}%")
print(f"Total cost: ${result['total_cost_cents']/100:.2f}")
```

### Example 3: Cost Estimation (Before Generation)

```python
# Estimate cost before generating
cost = manager.estimate_cost(
    num_images=36,
    provider_name='openai',
    size='1024x1024',
    quality='standard'
)

print(f"Estimated cost for 36 illustrations: ${cost/100:.2f}")
# Output: Estimated cost for 36 illustrations: $1.44
```

---

## 🔗 Integration with BF Agent

### Register Handler in Handler Catalog

```python
# In your Django app

from image_generation.handlers import IllustrationGenerationHandler
from apps.bfagent.models import HandlerRegistry

# Register handler
HandlerRegistry.objects.create(
    name="IllustrationGenerationHandler",
    class_path="image_generation.handlers.IllustrationGenerationHandler",
    category_id=1,  # Your category
    domain="educational_books",
    input_schema={
        "type": "object",
        "properties": {
            "book_id": {"type": "integer"},
            "scene_descriptions": {"type": "array"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "illustrations": {"type": "array"},
            "total_cost_cents": {"type": "number"}
        }
    },
    avg_duration_seconds=180,
    status="active"
)
```

### Use in Phase 5 of Educational Book Workflow

```python
# In your book template (domains/educational_book/template.py)

PhaseTemplate(
    phase_id="visualization",
    name="Phase 5: Visualization",
    description="Generate illustrations",
    actions=[
        ActionTemplate(
            action_id="generate_illustrations",
            name="Generate Illustrations",
            handler_class="IllustrationGenerationHandler",
            input_mapping={
                'book_id': 'context.book_id',
                'chapter_id': 'context.chapter_id',
                'scene_descriptions': 'output.phase4.scene_descriptions',
                'illustration_style': 'config.illustration_style'
            },
            estimated_duration_seconds=180
        )
    ]
)
```

---

## 💰 Cost Estimation

### Pricing (as of November 2025)

**OpenAI DALL-E 3:**
- 1024x1024 Standard: $0.040
- 1024x1024 HD: $0.080
- 1792x1024 Standard: $0.080
- 1792x1024 HD: $0.120

**Stability AI SD3:**
- Standard: $0.035 per image
- Turbo: $0.020 per image

### Example: Educational Book (36 Illustrations)

```python
# For your educational book system:
# 12 chapters × 3 illustrations = 36 images

# Option 1: OpenAI (Standard Quality)
cost_openai = 36 * 0.04  # = $1.44

# Option 2: Stability AI
cost_stability = 36 * 0.035  # = $1.26

# With automatic cheapest selection:
handler.estimate_cost(num_illustrations=36)
# → Returns: $1.26 (Stability AI selected)
```

---

## 📚 API Reference

### Handlers

#### `SingleImageHandler`
```python
handler.handle({
    'prompt': str,              # Required
    'provider': str,            # 'openai', 'stability', 'auto'
    'size': str,                # '1024x1024', etc.
    'quality': str,             # 'standard', 'hd'
    'style': str,               # 'vivid', 'natural', etc.
    'save_to_path': str         # Optional
})
```

#### `BatchImageHandler`
```python
handler.handle({
    'prompts': List[str],       # Required
    'provider': str,            # Default: 'auto'
    'distribute_load': bool,    # Default: True
    'save_to_directory': str    # Optional
})
```

#### `IllustrationGenerationHandler`
```python
handler.handle({
    'book_id': int,                           # Optional
    'chapter_id': int,                        # Optional
    'scene_descriptions': List[str],          # Required
    'illustration_style': str,                # Required
    'character_descriptions': Dict[str, str], # Optional
    'aspect_ratio': str,                      # Default: '16:9'
    'save_to_directory': str,                 # Required
    'provider': str                           # Default: 'openai'
})
```

### Provider Manager

```python
manager.generate_image(prompt, **kwargs)
manager.batch_generate(prompts, distribute=True)
manager.estimate_cost(num_images, provider_name=None)
manager.health_check()
manager.get_metrics()
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_handlers.py

# Run with coverage
pytest --cov=image_generation tests/
```

---

## 📊 Monitoring & Metrics

### Track Usage

```python
metrics = manager.get_metrics()

print(f"Total requests: {metrics['total_requests']}")
print(f"Success rate: {metrics['providers']['OpenAI']['success_rate']}%")
print(f"Total cost: ${metrics['total_cost_cents']/100:.2f}")
```

### Cost Alerts (configured in providers.yaml)

```yaml
monitoring:
  cost_alerts:
    daily_limit_cents: 1000  # Alert if >$10/day
    per_image_limit_cents: 20  # Alert if >$0.20/image
```

---

## 🛠️ Troubleshooting

### Common Issues

**1. API Key Not Found**
```bash
export OPENAI_API_KEY="sk-..."
```

**2. Rate Limit Exceeded**
- Adjust `rate_limit_per_minute` in config
- Enable automatic fallback

**3. Provider Unavailable**
- Check provider status: `manager.health_check()`
- Verify API key validity

---

## 🚀 Next Steps

1. ✅ **Done**: Core system implementation
2. ✅ **Done**: Multi-provider support
3. ✅ **Done**: Handler framework integration
4. 🔲 **TODO**: Add Replicate provider (optional)
5. 🔲 **TODO**: Local Stable Diffusion support
6. 🔲 **TODO**: Image editing/inpainting handlers
7. 🔲 **TODO**: Admin UI for handler management

---

## 📝 License

Proprietary - BF Agent Team  
© 2025 All Rights Reserved

---

## 🤝 Contributing

This is an internal BF Agent system. For questions or improvements, contact the BF Agent development team.

---

**Happy Image Generation! 🎨✨**
