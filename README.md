# 🏗️ BF Agent Platform

Shared packages and deployment concepts for the BF Agent ecosystem.

## 🆕 Latest Update (Januar 2026)

### Packages
- **creative-services** - Shared LLM client with tier system, usage tracking, and adapters
- **sphinx-export** - Sphinx → Markdown Export utility

### Deployment Concepts
- **Auto-Healer** - Self-healing deployment scripts for Hetzner Cloud
- **GitHub Workflow** - Self-healing CI/CD pipeline

## 📁 Struktur

```
platform/
├── packages/                    # Shared Python packages
│   ├── creative-services/       # LLM Client, Registry, Usage Tracker
│   │   ├── creative_services/
│   │   │   ├── core/            # LLMClient, LLMRegistry, UsageTracker
│   │   │   ├── adapters/        # Django, BFAgent adapters
│   │   │   ├── character/       # Character generation
│   │   │   ├── scene/           # Scene generation
│   │   │   ├── story/           # Story generation
│   │   │   └── world/           # World building
│   │   └── pyproject.toml
│   └── sphinx-export/           # Sphinx → Markdown Export
├── concepts/                    # Deployment & Infrastructure Concepts
├── docs/                        # Sphinx documentation
└── README.md
```

## 📦 Installation

```bash
# Install creative-services
pip install -e packages/creative-services

# With optional providers
pip install -e "packages/creative-services[openai,anthropic]"
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
