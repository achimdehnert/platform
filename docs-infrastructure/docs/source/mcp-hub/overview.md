# Übersicht

## Was ist MCP?

Das **Model Context Protocol (MCP)** ist ein Standard für die Kommunikation zwischen AI-Systemen und externen Tools/Datenquellen.

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI Assistant (Cascade/Claude)                 │
└─────────────────────────────────────────────────────────────────┘
         │ MCP Protocol (JSON-RPC)
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                       MCP Server                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  Tools   │  │Resources │  │ Prompts  │  │    Sampling      │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  External Systems (APIs, Databases, Files, Services)            │
└─────────────────────────────────────────────────────────────────┘
```

## MCP Hub Architektur

```
mcp-hub/
├── llm_mcp/              # LLM Integration (OpenAI, Anthropic)
├── bfagent_mcp/          # BF Agent Tools (Requirements, Feedback)
├── bfagent_sqlite_mcp/   # SQLite Database Access
├── deployment_mcp/       # GitHub Actions & Deployment
├── research_mcp/         # Web Search & Research
├── travel_mcp/           # Travel Beat Integration
├── illustration_mcp/     # AI Image Generation
├── book_writing_mcp/     # Writing Assistance
├── german_tax_mcp/       # Tax Calculations
├── ifc_mcp/              # BIM/IFC Processing
├── cad_mcp/              # CAD File Tools
├── dlm_mcp/              # Document Management
├── physicals_mcp/        # Physical Calculations
├── mcp_runner_ui/        # Web UI for Testing
└── ui_hub/               # Shared UI Components
```

## Kernkonzepte

### Tools

Tools sind Funktionen, die der AI-Assistent aufrufen kann:

```python
@mcp.tool()
async def search_web(query: str) -> str:
    """Search the web for information."""
    results = await perform_search(query)
    return format_results(results)
```

### Resources

Resources sind Daten, die der AI-Assistent lesen kann:

```python
@mcp.resource("config://settings")
async def get_settings() -> str:
    """Get current configuration."""
    return json.dumps(settings)
```

### Prompts

Prompts sind vordefinierte Prompt-Templates:

```python
@mcp.prompt("analyze-code")
async def analyze_code_prompt(code: str) -> str:
    """Prompt for code analysis."""
    return f"Analyze this code:\n\n{code}"
```

## Integration mit BF Agent

MCP Hub ist eng mit BF Agent integriert:

```
BF Agent Django App
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  bfagent_mcp                                                     │
│  - Requirements Management                                       │
│  - Feedback System                                               │
│  - Workflow Integration                                          │
│  - Domain Knowledge                                              │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  bfagent_sqlite_mcp                                              │
│  - Direct Database Access                                        │
│  - Query Execution                                               │
│  - Schema Inspection                                             │
└─────────────────────────────────────────────────────────────────┘
```

## Vorteile

1. **Modularität** - Jeder Server ist unabhängig
2. **Erweiterbarkeit** - Einfach neue Server hinzufügen
3. **Standardisiert** - MCP Protocol für alle
4. **Testbar** - Isolierte Funktionalität
5. **Wiederverwendbar** - Zwischen Projekten teilbar
