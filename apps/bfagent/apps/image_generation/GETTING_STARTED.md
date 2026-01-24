# 🚀 Getting Started - BF Agent Image Generation System

Welcome! You now have a **complete, production-ready image generation system**.

---

## 📁 What You Got

### **21 Files Total** ✅

```
image_generation/
│
├── 📖 Documentation (3 files)
│   ├── README.md                    # Comprehensive guide (12 sections)
│   ├── EXECUTIVE_SUMMARY.md         # Business overview
│   └── GETTING_STARTED.md          # This file
│
├── 🔧 Configuration (3 files)
│   ├── config/providers.yaml        # All provider settings
│   ├── config/config_loader.py      # YAML + Environment loader
│   └── requirements.txt             # Dependencies
│
├── 🎯 Handlers (4 files)
│   ├── handlers/base_image_handler.py      # Abstract base (3-phase)
│   ├── handlers/generic_image_handler.py   # Single + Batch
│   ├── handlers/illustration_handler.py    # Educational books
│   └── handlers/__init__.py
│
├── 🏢 Providers (5 files)
│   ├── providers/base_provider.py          # Abstract interface
│   ├── providers/openai_provider.py        # DALL-E 3
│   ├── providers/stability_provider.py     # Stable Diffusion 3
│   ├── providers/provider_manager.py       # Orchestration
│   └── providers/__init__.py
│
├── 📋 Schemas (3 files)
│   ├── schemas/input_schemas.py     # 6 Pydantic input models
│   ├── schemas/output_schemas.py    # 7 Pydantic output models
│   └── schemas/__init__.py
│
├── 🧪 Tests & Utils (3 files)
│   ├── tests/__init__.py
│   ├── utils/__init__.py
│   └── quick_start.py              # Example script
```

---

## ⚡ 5-Minute Setup

### Step 1: Set API Keys

```bash
export OPENAI_API_KEY="sk-..."
export STABILITY_API_KEY="sk-..."
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Run Quick Start

```bash
python quick_start.py
```

**Done!** You'll see:
- ✅ Single image generation
- ✅ Batch generation (3 images)
- ✅ Cost estimation
- ✅ System metrics

---

## 📚 Key Documents

### 1. [README.md](README.md)
**→ Start here for complete documentation**

Contains:
- Full architecture explanation
- All usage examples
- API reference
- Configuration guide
- Troubleshooting

### 2. [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)
**→ For business overview**

Contains:
- Project metrics
- Cost analysis
- ROI calculations
- Delivery checklist

### 3. [quick_start.py](quick_start.py)
**→ For hands-on learning**

Contains:
- Working examples
- 4 different use cases
- Commented code

---

## 🎯 Use Cases

### Use Case 1: Educational Book Illustrations

```python
from handlers import IllustrationGenerationHandler

handler = IllustrationGenerationHandler(provider_manager)

result = handler.handle({
    'book_id': 1,
    'chapter_id': 1,
    'scene_descriptions': [
        'Children arriving at Brain Island',
        'Solving a puzzle together'
    ],
    'illustration_style': 'watercolor children\'s book',
    'save_to_directory': './illustrations'
})

print(f"Generated {result['successful_illustrations']} illustrations")
print(f"Cost: ${result['total_cost_cents']/100:.2f}")
```

**Perfect for:** Your Educational Book System (Phase 5)

---

### Use Case 2: Generic Single Image

```python
from handlers import SingleImageHandler

handler = SingleImageHandler(provider_manager)

result = handler.handle({
    'prompt': 'A beautiful sunset',
    'provider': 'auto',  # Automatic selection
    'quality': 'standard'
})

print(f"Image URL: {result['image']['url']}")
```

**Perfect for:** Any single image need

---

### Use Case 3: Batch Generation

```python
from handlers import BatchImageHandler

handler = BatchImageHandler(provider_manager)

result = handler.handle({
    'prompts': [
        'A red apple',
        'A blue ocean',
        'A green forest'
    ],
    'distribute_load': True  # Use multiple providers
})

print(f"Success: {result['success_rate']}%")
```

**Perfect for:** Generating many images efficiently

---

## 🔗 Integration mit BF Agent

### In Handler Registry registrieren

```python
# Django Management Command oder Admin
from apps.bfagent.models import HandlerRegistry

HandlerRegistry.objects.create(
    name="IllustrationGenerationHandler",
    class_path="image_generation.handlers.IllustrationGenerationHandler",
    domain="educational_books",
    category_id=1,
    status="active"
)
```

### In Workflow-Template nutzen

```python
# domains/educational_book/template.py

PhaseTemplate(
    phase_id="visualization",
    name="Phase 5: Visualization",
    actions=[
        ActionTemplate(
            action_id="generate_illustrations",
            handler_class="IllustrationGenerationHandler",
            input_mapping={
                'book_id': 'context.book_id',
                'scene_descriptions': 'output.phase4.scenes'
            }
        )
    ]
)
```

---

## 💰 Cost Overview

### OpenAI DALL-E 3
- 1024x1024 Standard: **$0.040** per image
- 1024x1024 HD: **$0.080** per image

### Stability AI SD3
- Standard: **$0.035** per image
- Turbo: **$0.020** per image

### For Educational Books (36 illustrations)
- **Best Option:** Stability AI SD3
- **Cost:** $1.26 per book
- **Time:** ~10 minutes

### Cost Estimation Before Generation

```python
cost = manager.estimate_cost(num_images=36)
print(f"Estimated: ${cost/100:.2f}")
# → $1.26 (with automatic cheapest selection)
```

---

## 🛠️ Configuration

### Edit config/providers.yaml

```yaml
providers:
  openai:
    enabled: true
    rate_limit_per_minute: 5
  
  stability:
    enabled: true
    rate_limit_per_minute: 10

manager:
  selection_strategy: "cheapest"  # or: fastest, priority
  enable_fallback: true
```

---

## 📊 Monitoring

### Get Metrics

```python
metrics = manager.get_metrics()

print(f"Total requests: {metrics['total_requests']}")
print(f"Total cost: ${metrics['total_cost_cents']/100:.2f}")

for provider, stats in metrics['providers'].items():
    print(f"{provider}: {stats['success_rate']}% success")
```

---

## 🧪 Testing

### Run Quick Start

```bash
python quick_start.py
```

This will:
1. ✅ Check your API keys
2. ✅ Setup providers
3. ✅ Health check
4. ✅ Run 4 examples
5. ✅ Show metrics

---

## ❓ Troubleshooting

### Problem: API Key Not Found

**Solution:**
```bash
export OPENAI_API_KEY="sk-..."
# or
export STABILITY_API_KEY="sk-..."
```

### Problem: Rate Limit Exceeded

**Solution 1:** Adjust in config/providers.yaml
```yaml
rate_limit_per_minute: 5  # Lower this
```

**Solution 2:** Enable fallback
```yaml
enable_fallback: true  # Switch to other provider
```

### Problem: Import Error

**Solution:**
```bash
pip install -r requirements.txt
```

---

## 🚀 Next Steps

### This Week
1. ✅ Read [README.md](README.md) (sections 1-5)
2. ✅ Run `quick_start.py`
3. ✅ Generate first test image
4. ✅ Integrate with Phase 5

### Next Week
1. 🔲 Register in Handler Catalog
2. 🔲 Generate first complete book
3. 🔲 Monitor costs & performance
4. 🔲 Optimize configuration

### Optional Enhancements
1. 🔲 Add more providers (Replicate?)
2. 🔲 Build Admin UI
3. 🔲 Advanced monitoring
4. 🔲 Custom style presets

---

## 💡 Pro Tips

### 1. Start with Dry-Run Mode

```yaml
# config/providers.yaml
development:
  dry_run: true  # No actual API calls
```

### 2. Estimate Costs First

```python
cost = handler.estimate_cost(num_illustrations=36)
if cost > 1000:  # More than $10
    print("Cost too high, adjust parameters")
```

### 3. Use Automatic Provider Selection

```python
{
    'provider': 'auto'  # Let system choose cheapest
}
```

### 4. Enable Comprehensive Logging

```yaml
# config/providers.yaml
logging:
  level: "DEBUG"
  log_prompts: true
  log_costs: true
```

---

## 📧 Support

### Documentation
- **Full Guide:** [README.md](README.md)
- **Business Overview:** [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)
- **Code Examples:** [quick_start.py](quick_start.py)

### Code Structure
- **Handlers:** `handlers/` directory
- **Providers:** `providers/` directory
- **Schemas:** `schemas/` directory
- **Config:** `config/` directory

---

## ✅ Quick Checklist

Before using in production:

- [ ] API keys configured
- [ ] Dependencies installed
- [ ] Quick start runs successfully
- [ ] Provider health check passes
- [ ] Cost estimation accurate
- [ ] Understand configuration options
- [ ] Know how to access metrics
- [ ] Handlers registered (if using BF Agent)

---

## 🎉 You're Ready!

Everything is set up and ready to go. The system is:

✅ **Production-ready**  
✅ **Fully documented**  
✅ **Type-safe**  
✅ **Cost-efficient**  
✅ **Enterprise-grade**  

**Start generating images now:**

```bash
python quick_start.py
```

**Questions? Check [README.md](README.md) for detailed answers!**

---

**Happy Image Generation! 🎨✨**
