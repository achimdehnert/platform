# BFA Agent

**Explosionsschutz-Agent mit OpenAI Agents SDK + OpenRouter**

Ein Multi-Agent System für Explosionsschutz-Analyse nach TRGS 720ff, ATEX und IECEx.

## Features

- 🤖 **Multi-Agent Architektur** - Spezialisierte Agents für verschiedene Aufgaben
- 🔄 **OpenRouter Integration** - 400+ Modelle über eine API
- 📦 **MCP Support** - Model Context Protocol für Tool-Integration
- 📚 **Research Hub** - Akademische Paper-Suche via paper-search-mcp
- ⚙️ **Presets** - Model-Konfiguration ohne Code-Änderung
- 🔧 **Function Tools** - CAD-Parsing, Zonenberechnung, Equipment-Prüfung
- 📊 **Structured Outputs** - Pydantic Models für typsichere Ergebnisse

## Installation

```bash
# Basis
pip install -e .

# Mit MCP Support
pip install -e ".[mcp]"

# Mit Research (Paper Search)
pip install -e ".[research]"

# Vollständig
pip install -e ".[full]"
```

## Quick Start

```python
from bfa_agent import setup_openrouter, triage_preset
from agents import Runner
import asyncio

# 1. OpenRouter initialisieren
setup_openrouter()

# 2. Agent ausführen
async def main():
    result = await Runner.run(
        triage_preset,
        "Klassifiziere einen Lackierraum mit 450m³ und Aceton"
    )
    print(result.final_output)

asyncio.run(main())
```

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                      BFA Agent System                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  User Request                                                │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────┐                                            │
│  │   Triage    │ @preset/bfa-triage                         │
│  │   Agent     │ (Gemini Flash - schnell)                   │
│  └──────┬──────┘                                            │
│         │                                                    │
│    ┌────┴────┬────────────┬────────────┬───────────┐        │
│    ▼         ▼            ▼            ▼           ▼        │
│ ┌──────┐ ┌──────┐   ┌──────────┐ ┌──────────┐ ┌────────┐   │
│ │ CAD  │ │ Zone │   │Equipment │ │  Report  │ │Research│   │
│ │Reader│ │Analyz│   │ Checker  │ │  Writer  │ │ Expert │   │
│ └──────┘ └──────┘   └──────────┘ └──────────┘ └────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    MCP Tools                          │  │
│  │  BFA: read_cad | calculate_zone | check_equipment    │  │
│  │  Research: search_arxiv | search_pubmed | download   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Agents

| Agent | Preset | Model | Aufgabe |
|-------|--------|-------|---------|
| Triage | `@preset/bfa-triage` | Gemini Flash | Routing |
| CAD Reader | `@preset/bfa-cad` | Gemini Flash | CAD-Parsing |
| Zone Analyzer | `@preset/bfa-analyzer` | Claude Sonnet | Ex-Zonen |
| Equipment Checker | `@preset/bfa-equipment` | Claude Sonnet | Eignung |
| Report Writer | `@preset/bfa-report` | GPT-4o | Berichte |
| Research Expert | `@preset/bfa-research` | Claude Sonnet | Paper-Suche |

## Research Hub

Paper-Suche über multiple akademische Quellen:

```python
from bfa_agent import research_agent, create_bfa_research_agent
from agents import Runner

# Einfache Paper-Suche
result = await Runner.run(
    research_agent,
    "Suche aktuelle Forschung zu Wasserstoff-Explosionsgrenzen"
)

# Kombiniert: BFA Tools + Research
bfa_research = create_bfa_research_agent()
result = await Runner.run(
    bfa_research,
    "Analysiere Aceton-Stoffdaten und recherchiere relevante Forschung"
)
```

**Verfügbare Quellen:**
- arXiv (Physik, Engineering)
- PubMed (Biomedizin, Arbeitsschutz)
- bioRxiv/medRxiv (Preprints)
- Semantic Scholar (Breit)
- Google Scholar

## Presets

Presets ermöglichen Model-Wechsel ohne Code-Deployment:

```python
# In OpenRouter UI anlegen, dann nutzen:
agent = Agent(model="@preset/bfa-analyzer")
```

Siehe [docs/PRESETS.md](docs/PRESETS.md) für Setup-Anleitung.

## MCP Tools

```python
from bfa_agent import MCPServers, MCPServerSets

# Einzelne Server
agent = Agent(mcp_servers=[MCPServers.bfa_cad()])
agent = Agent(mcp_servers=[MCPServers.paper_search()])

# Kombiniert
agent = Agent(mcp_servers=MCPServerSets.bfa_full())
```

**BFA Tools:**
- `read_cad_file` - DXF/IFC/STEP Parser
- `calculate_zone_extent` - TRGS 721 Berechnung
- `check_equipment_for_zone` - ATEX Eignungsprüfung
- `get_substance_data` - Stoffdatenbank
- `analyze_ventilation` - TRGS 722 Lüftungsanalyse

**Research Tools (paper-search-mcp):**
- `search_arxiv`, `search_pubmed`, `search_semantic_scholar`
- `download_arxiv`, `download_pubmed`, `download_biorxiv`

## Beispiele

```bash
# Basis-Nutzung
python examples/basic_usage.py

# MCP Integration
python examples/mcp_usage.py

# Presets
python examples/preset_usage.py

# Research Hub
python examples/research_usage.py
```

## Konfiguration

```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-...
```

## Lizenz

MIT

## Links

- [OpenRouter Docs](https://openrouter.ai/docs)
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)
- [paper-search-mcp](https://github.com/openags/paper-search-mcp)
- [TRGS 720](https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRGS/TRGS-720.html)
