# Installation

## Requirements

- Python 3.10+
- Pydantic 2.0+

## Basic Installation

```bash
pip install -e packages/creative-services
```

## Optional Dependencies

### OpenAI Support

```bash
pip install -e packages/creative-services[openai]
```

### Anthropic Support

```bash
pip install -e packages/creative-services[anthropic]
```

### Redis Cache Support

```bash
pip install -e packages/creative-services[redis]
```

### All Features

```bash
pip install -e packages/creative-services[all]
```

## Development Installation

```bash
# Clone the repository
git clone https://github.com/your-org/platform.git
cd platform/packages/creative-services

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/
```

## Sphinx Documentation

```bash
# Install docs dependencies
pip install sphinx furo myst-parser sphinx-autodoc-typehints

# Build documentation
cd docs
make html

# View at docs/_build/html/index.html
```
