# 🏗️ BF Agent Platform

Monorepo für BFAgent, Travel Beat und geteilte Packages.

## 🆕 Latest Update (Januar 2026)

### Hetzner Deployment Concepts
- **Auto-Healer** - Self-healing deployment scripts for Hetzner Cloud
- **GitHub Workflow** - Self-healing CI/CD pipeline
- **Deployment Prompts** - AI-assisted deployment configuration

## 📁 Struktur

```
platform/
├── packages/           # Shared Python packages
│   ├── sphinx-export/  # Sphinx → Markdown Export
│   └── mcp-tools/      # MCP Server Utilities
├── apps/               # Django Applications
│   ├── bfagent/        # BF Agent (Writing Hub, etc.)
│   └── travel-beat/    # Travel Story Generator
├── concepts/           # Deployment & Infrastructure Concepts
│   ├── hetzner_auto_healer.py
│   ├── hetzner_deployment_prompt.md
│   └── github-workflow-self-healing.yml
├── docker/             # Shared Docker configs
└── docs/               # Platform documentation
```

## 🚀 Deployment

| Service | URL | Status |
|---------|-----|--------|
| BF Agent | https://bfagent.iil.pet | ✅ Production |
| Travel Beat | https://travel-beat.iil.pet | ✅ Production |

## 🔗 Related Repositories

- **[BF Agent](https://github.com/achimdehnert/bfagent)** - AI Book Writing Platform
- **[Travel Beat](https://github.com/achimdehnert/travel-beat)** - Travel Story Generator  
- **[MCP Hub](https://github.com/achimdehnert/mcp-hub)** - MCP Server Collection

## 📝 License

MIT License
