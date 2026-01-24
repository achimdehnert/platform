# 🤖 BF Agent MCP Server v2.0

**Universal MCP Server mit MetaPrompter Gateway und Standards Enforcement**

## 🎯 Features

- ✅ **Universal Gateway** - Ein Tool für ALLE Anfragen
- ✅ **Natural Language** - Sprich einfach natürlich
- ✅ **Standards Enforcement** - 100% konformer Code garantiert
- ✅ **Smart Defaults** - Fehlende Parameter werden ergänzt
- ✅ **Rückfragen** - Bei Unklarheiten wird nachgefragt

## 📁 Struktur

```
bfagent_mcp/
├── __init__.py           # Package entry
├── server.py             # MCP Server
├── metaprompter/         # Natural Language Processing
│   ├── __init__.py
│   ├── gateway.py        # Universal Gateway
│   ├── intent.py         # Intent Classifier
│   └── enricher.py       # Context Enricher
├── standards/            # Standards Enforcement
│   ├── __init__.py       # Knowledge Base (12 Standards)
│   ├── validator.py      # Code Validator
│   └── enforcer.py       # Template Enforcer
└── tools/                # MCP Tool Definitions
```

## 🚀 Usage

```python
from bfagent_mcp.server import BFAgentMCPServer
import asyncio

async def main():
    server = BFAgentMCPServer()
    
    # Natural language requests
    result = await server.bfagent("Erstelle einen IFC Parser für CAD")
    print(result)
    
    result = await server.bfagent("Liste Räume aus building.ifc")
    print(result)

asyncio.run(main())
```

## 📊 Erkannte Intents

| Intent | Beispiel |
|--------|----------|
| `generate_handler` | "Erstelle einen IFC Parser" |
| `list_domains` | "Zeig alle Domains" |
| `cad_list_rooms` | "Liste Räume aus building.ifc" |
| `cad_get_dimensions` | "Wie groß ist das Wohnzimmer?" |
| `validate_code` | "Validiere diesen Code" |
| `best_practices` | "Best Practices für Pydantic" |

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

## 🔄 Workflow

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

## 🧪 Test

```bash
cd /home/claude
python -c "
import asyncio
from bfagent_mcp.server import BFAgentMCPServer

async def test():
    server = BFAgentMCPServer()
    result = await server.bfagent('Hilfe')
    print(result)

asyncio.run(test())
"
```

## 📝 Next Steps

1. **MCP SDK Integration** - mcp.server.Server einbinden
2. **Django ORM** - Echte Daten statt Mock
3. **CAD Parser** - IfcOpenShell/ezdxf integrieren
4. **IDE Setup** - Cursor/Windsurf Konfiguration
