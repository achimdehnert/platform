# BF Agent MCP Server

Model Context Protocol Server for BF Agent - AI-powered development assistant.

## Features

- 🤖 **AI-Powered Handlers** - Generate code with LLM integration
- 📋 **Domain Management** - Organize handlers by domain
- ✅ **Validation** - Built-in code validation
- 🔧 **Django Integration** - Full ORM support
- 🚀 **MCP Protocol** - Standard protocol for AI tools

## Installation

```bash
pip install -e .
```

## Usage

### Start Server (STDIO)
```bash
python -m bfagent_mcp.server
# or
bfagent-mcp
```

### Start with Debug
```bash
bfagent-mcp --debug
```

### Use in Python
```python
from bfagent_mcp import create_services

# Create service instances
domain_service, handler_service, validation_service = create_services(use_django=True)

# List domains
domains = await domain_service.list_domains()
```

## Architecture

- **Clean Architecture** - Separation of concerns
- **Repository Pattern** - Data access abstraction
- **Service Layer** - Business logic
- **MCP Server** - Protocol handling

## Requirements

- Python 3.11+
- Django 5.2+
- Pydantic 2.0+

## License

MIT
