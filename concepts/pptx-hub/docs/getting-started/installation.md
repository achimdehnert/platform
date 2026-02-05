# Installation

## Requirements

- Python 3.11 or higher
- pip or uv package manager

## Basic Installation

Install the core package:

```bash
pip install pptx-hub
```

## Installation with Extras

### Django Support

For Django integration with REST API:

```bash
pip install pptx-hub[django]
```

### S3 Storage

For S3/MinIO storage backend:

```bash
pip install pptx-hub[storage]
```

### Translation Support

For DeepL translation integration:

```bash
pip install pptx-hub[translation]
```

### CLI Tool

For command-line interface:

```bash
pip install pptx-hub[cli]
```

### Full Installation

Install everything:

```bash
pip install pptx-hub[all]
```

## Development Installation

For contributing to PPTX-Hub:

```bash
git clone https://github.com/YOUR_ORG/pptx-hub.git
cd pptx-hub
pip install -e ".[dev,all]"
```

## Verify Installation

```bash
# Check version
python -c "import pptx_hub; print(pptx_hub.__version__)"

# Or with CLI
pptx-hub --version
```
