# Installation

## Anforderungen

- Python 3.10+
- pip oder poetry

## Basic Installation

```bash
pip install -e packages/creative-services
```

## Mit optionalen Dependencies

```bash
# OpenAI Support
pip install -e "packages/creative-services[openai]"

# Anthropic Support
pip install -e "packages/creative-services[anthropic]"

# Redis Cache
pip install -e "packages/creative-services[redis]"

# Alle Features
pip install -e "packages/creative-services[all]"
```

## Development Installation

```bash
# Repository klonen
git clone https://github.com/achimdehnert/platform.git
cd platform/packages/creative-services

# Mit Dev-Dependencies
pip install -e ".[dev]"

# Tests ausführen
pytest tests/ -v
```

## Dokumentation lokal bauen

```bash
# Docs-Dependencies installieren
pip install -r docs-infrastructure/docs/requirements.txt

# HTML bauen
sphinx-build -W -b html docs-infrastructure/docs/source docs-infrastructure/docs/_build/html

# Live-Preview
sphinx-autobuild docs-infrastructure/docs/source docs-infrastructure/docs/_build/html --port 8000
```
