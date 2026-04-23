# MCP Hub

```{toctree}
:maxdepth: 2

overview
servers/index
development
```

## Übersicht

MCP Hub ist eine Sammlung von Model Context Protocol (MCP) Servern für AI-gestützte Entwicklung, Research und Automation.

## Verfügbare Server

::::{grid} 2
:gutter: 3

:::{grid-item-card} 🤖 LLM MCP
:link: servers/llm-mcp
:link-type: doc

LLM Integration (OpenAI, Anthropic, Local)
:::

:::{grid-item-card} 📚 BFAgent MCP
:link: servers/bfagent-mcp
:link-type: doc

BF Agent Integration (Requirements, Feedback)
:::

:::{grid-item-card} 🚀 Deployment MCP
:link: servers/deployment-mcp
:link-type: doc

GitHub Actions & Deployment Tools
:::

:::{grid-item-card} 🔍 Research MCP
:link: servers/research-mcp
:link-type: doc

Research & Web Search Tools
:::

:::{grid-item-card} ✈️ Travel MCP
:link: servers/travel-mcp
:link-type: doc

Travel Beat Integration
:::

:::{grid-item-card} 🎨 Illustration MCP
:link: servers/illustration-mcp
:link-type: doc

AI Image Generation Tools
:::

::::

## Quick Start

```bash
# Clone repository
git clone https://github.com/achimdehnert/mcp-hub.git
cd mcp-hub

# Install specific server
cd llm_mcp
pip install -e .
```

## Status

| Server | Status |
|--------|--------|
| `llm_mcp` | ✅ Production |
| `bfagent_mcp` | ✅ Production |
| `deployment_mcp` | ✅ Production |
| `research_mcp` | ✅ Production |
| `travel_mcp` | ✅ Production |
| `illustration_mcp` | ✅ Production |
| `book_writing_mcp` | ✅ Production |
| `german_tax_mcp` | 🔧 Beta |
| `ifc_mcp` | 🔧 Beta |
| `cad_mcp` | 🔧 Beta |
