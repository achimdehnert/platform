# 🤖 BF Agent MCP Server v2.0

**Universal MCP Server mit MetaPrompter Gateway und Standards Enforcement**

## 🚀 Installation

```bash
# Mit pip
pip install bfagent-mcp

# Mit uv
uv add bfagent-mcp

# Development
pip install -e ".[dev]"

# Mit Django Support
pip install -e ".[django]"
```

## ⚡ Quick Start

```bash
# Server starten
python -m bfagent_mcp.mcp_server

# Oder als Script
bfagent-mcp
```

## 🌊 Windsurf IDE Setup

1. Config öffnen: `~/.codeium/windsurf/mcp_config.json`
2. Server hinzufügen:

```json
{
  "mcpServers": {
    "bfagent": {
      "command": "python",
      "args": ["-m", "bfagent_mcp.mcp_server"],
      "env": {
        "PYTHONPATH": "/path/to/bfagent_mcp"
      }
    }
  }
}
```

3. In Windsurf: MCP Panel → Refresh
4. Nutzen: `@bfagent Hilfe`

**Ausführliche Anleitung:** [WINDSURF_SETUP.md](WINDSURF_SETUP.md)

## 🎯 Features

- ✅ **Universal Gateway** - Ein Tool für ALLE Anfragen
- ✅ **Natural Language** - Sprich einfach natürlich  
- ✅ **Standards Enforcement** - 100% konformer Code garantiert
- ✅ **Smart Defaults** - Fehlende Parameter werden ergänzt
- ✅ **Django Integration** - Echte Daten aus Datenbank
- ✅ **IDE Ready** - Windsurf, Cursor, Claude Desktop

## 📁 Struktur

```
bfagent_mcp/
├── __init__.py
├── mcp_server.py         # FastMCP Server (Haupteinstieg)
├── django_orm.py         # Django Integration
├── metaprompter/         # Natural Language Processing
│   ├── gateway.py        # Universal Gateway
│   ├── intent.py         # Intent Classifier
│   └── enricher.py       # Context Enricher
├── standards/            # Standards Enforcement
│   ├── __init__.py       # Knowledge Base (12 Standards)
│   ├── validator.py      # Code Validator
│   └── enforcer.py       # Template Enforcer
├── examples/
│   └── mcp_config.json   # Beispiel Windsurf Config
├── pyproject.toml
├── README.md
└── WINDSURF_SETUP.md
```

## 🛠️ MCP Tools

| Tool | Beschreibung |
|------|--------------|
| `bfagent` | Universal Interface - versteht natürliche Sprache |
| `bfagent_generate_handler` | Generiert standard-konformen Handler |
| `bfagent_validate_code` | Validiert Code gegen Standards |
| `bfagent_list_standards` | Zeigt alle Standards |

## 💬 Beispiele

```
# In Windsurf Cascade:

@bfagent Zeig alle Domains

@bfagent Erstelle einen IFC Parser für CAD

@bfagent Validiere diesen Code:
class MyHandler:
    def process(self):
        pass

@bfagent Best Practices für Handler
```

## 🔒 Standards (12 definiert)

| ID | Name | Severity |
|----|------|----------|
| H001 | BaseHandler Inheritance | Error |
| H002 | Three-Phase Pattern | Error |
| H003 | HandlerResult Return | Error |
| H004 | Handler Metadata | Error |
| S001 | Pydantic Input Schema | Error |
| S002 | Pydantic Output Schema | Error |
| S003 | Field Descriptions | Warning |
| E001 | Try-Except in process() | Error |
| L001 | Logger Usage | Warning |
| D001 | Class Docstring | Error |
| N001 | Handler Suffix | Error |
| T001 | Test Class | Warning |

## 🔄 Architektur

```
User Input
    │
    ▼
┌─────────────────────────┐
│   MetaPrompter Gateway  │
│   ├── Intent Detection  │
│   ├── Entity Extraction │
│   └── Context Enrichment│
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  Standards Enforcement  │
│   ├── Template Enforcer │
│   └── Code Validator    │
└─────────────────────────┘
    │
    ▼
✅ 100% Standard-konformer Output
```

## 🐍 Python API

```python
import asyncio
from bfagent_mcp.server import BFAgentMCPServer

async def main():
    server = BFAgentMCPServer()
    
    # Natural language
    result = await server.bfagent("Erstelle einen IFC Parser")
    print(result)

asyncio.run(main())
```

## 🗄️ Django Integration

```python
from bfagent_mcp.django_orm import DjangoORM

orm = DjangoORM()

# Liste Domains
domains = orm.list_domains()

# Liste Handler
handlers = orm.list_handlers("cad_analysis")

# Statistiken
stats = orm.get_statistics()
```

## 📝 License

MIT
