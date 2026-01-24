# BF Agent Platform
Monorepo für BFAgent, Travel Beat und geteilte Packages.
## Struktur
\platform/
├── packages/           # Shared Python packages
│   ├── sphinx-export/  # Sphinx → Markdown Export
│   └── mcp-tools/      # MCP Server Utilities
├── apps/               # Django Applications
│   ├── bfagent/        # BF Agent (Writing Hub, etc.)
│   └── travel-beat/    # Travel Story Generator
├── docker/             # Shared Docker configs
└── docs/               # Platform documentation
\## Deployment
- https://bfagent.iil.pet
- https://travel-beat.iil.pet
