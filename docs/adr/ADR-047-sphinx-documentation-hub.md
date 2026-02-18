# ADR-047: Sphinx Documentation Hub (sphinx.iil.pet)

| Status | Proposed |
| ------ | -------- |
| Date | 2026-02-18 |
| Author | Achim Dehnert |
| Scope | Platform-wide |

## Context

We have 10 repositories, each with code, APIs, models, ADRs, and deployment
docs. Documentation exists in scattered locations: README files, inline
docstrings, ADRs in `platform/docs/adr/`, and ad-hoc Markdown. There is no
single place where a developer (or an LLM agent) can browse the full
documentation.

With `docs-agent` v0.2.0 (ADR-046) we now have:

- AST-based docstring coverage scanning
- DIATAXIS classification (heuristic + LLM fallback)
- LLM-powered docstring generation
- Non-destructive code insertion via libcst

This ADR proposes a **centralized Sphinx Documentation Hub** at
`https://sphinx.iil.pet` that autonomously builds, enriches, and publishes
documentation for all repositories.

## Decision

### 1. Architecture Overview

```text
┌──────────────────────────────────────────────────────────┐
│                  sphinx.iil.pet (Nginx)                  │
│               Static HTML served from                    │
│          /var/www/sphinx.iil.pet/html/                   │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│              sphinx-hub Container (Docker)                │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │ git clone / │  │  docs-agent  │  │  sphinx-build   │ │
│  │ git pull    │──▶│  audit +     │──▶│  per-repo +    │ │
│  │ all repos   │  │  generate    │  │  master index   │ │
│  └─────────────┘  └──────────────┘  └─────────────────┘ │
│                          │                               │
│                   ┌──────▼──────┐                        │
│                   │  llm_mcp    │                        │
│                   │  gateway    │                        │
│                   └─────────────┘                        │
└──────────────────────────────────────────────────────────┘
```

### 2. Repository Coverage

| Repo | Brand | Type | Port | URL |
| ---- | ----- | ---- | ---- | --- |
| platform | Platform | Shared packages, ADRs | — | `/platform/` |
| bfagent | Book Factory | Django app | 8088 | `/bfagent/` |
| risk-hub | Schutztat | Django app | 8081 | `/risk-hub/` |
| travel-beat | DriftTales | Django app | 8090 | `/travel-beat/` |
| weltenhub | Weltenforger | Django app | 8091 | `/weltenhub/` |
| mcp-hub | MCP Servers | FastMCP collection | 8093 | `/mcp-hub/` |
| pptx-hub | Prezimo | Django app | 8089 | `/pptx-hub/` |
| trading-hub | AI Trades | Django app | — | `/trading-hub/` |
| odoo-hub | Odoo | Odoo modules | 8069 | `/odoo-hub/` |
| wedding-hub | Wedding | Django app | — | `/wedding-hub/` |

### 3. Per-Repo Documentation Structure

Each repo gets a Sphinx project with this standard layout:

```text
<repo>/docs/
├── conf.py              # Auto-generated from template
├── index.rst            # Auto-generated master index
├── quickstart.rst       # From README.md (auto-converted)
├── api/                 # autodoc from Python source
│   ├── models.rst
│   ├── views.rst
│   ├── services.rst
│   └── ...
├── architecture.rst     # ADRs relevant to this repo
├── deployment.rst       # From docker-compose + Dockerfile
└── changelog.rst        # From git tags + commit history
```

### 4. LLM-Autonomous Pipeline

The build pipeline runs in 4 phases:

#### Phase 1: Clone and Scan (no LLM)

```bash
# Clone/pull all repos
for repo in bfagent risk-hub travel-beat weltenhub mcp-hub pptx-hub ...; do
    git clone --depth 1 https://github.com/achimdehnert/$repo /opt/sphinx-hub/repos/$repo
done

# Scan docstring coverage per repo
docs-agent audit /opt/sphinx-hub/repos/$repo --output json > /opt/sphinx-hub/reports/$repo.json
```

#### Phase 2: LLM Enrichment (autonomous)

```bash
# Generate missing docstrings (batch, max 50 per repo per run)
docs-agent generate /opt/sphinx-hub/repos/$repo --apply --max-items 50

# Classify documentation files
docs-agent audit /opt/sphinx-hub/repos/$repo --scope diataxis --refine --output json
```

#### Phase 3: Sphinx Build (per-repo + master)

```bash
# Build each repo's docs
sphinx-build -b html /opt/sphinx-hub/repos/$repo/docs /var/www/sphinx.iil.pet/html/$repo

# Build master index (links to all repos)
sphinx-build -b html /opt/sphinx-hub/master /var/www/sphinx.iil.pet/html/
```

#### Phase 4: Report and Notify

- Generate quality dashboard (coverage %, DIATAXIS distribution)
- Compare with previous run (trend tracking)
- Log results to `/opt/sphinx-hub/reports/`

### 5. Master Index (Landing Page)

The root `https://sphinx.iil.pet/` shows a dashboard:

```text
┌─────────────────────────────────────────────────────┐
│           Platform Documentation Hub                 │
│              sphinx.iil.pet                          │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  bfagent    │  │  risk-hub   │  │ travel-beat  │ │
│  │  Coverage:  │  │  Coverage:  │  │  Coverage:   │ │
│  │  67%        │  │  54%        │  │  72%         │ │
│  │  ▶ Docs     │  │  ▶ Docs     │  │  ▶ Docs      │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  weltenhub  │  │  mcp-hub    │  │  platform    │ │
│  │  Coverage:  │  │  Coverage:  │  │  Coverage:   │ │
│  │  61%        │  │  78%        │  │  85%         │ │
│  │  ▶ Docs     │  │  ▶ Docs     │  │  ▶ Docs      │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
│                                                      │
│  ADRs: 47 │ Total Coverage: 68% │ Last Build: 2h ago│
└─────────────────────────────────────────────────────┘
```

### 6. Automation Schedule

| Trigger | Action |
| ------- | ------ |
| Cron daily 03:00 UTC | Full rebuild (clone, scan, enrich, build) |
| GitHub webhook (push to main) | Incremental rebuild (pull + build affected repo) |
| Manual `/deploy sphinx` | Force full rebuild |

### 7. Docker Setup

```yaml
# /opt/sphinx-hub/docker-compose.yml
services:
  sphinx-builder:
    image: python:3.12-slim
    volumes:
      - sphinx-repos:/opt/sphinx-hub/repos
      - sphinx-html:/var/www/sphinx.iil.pet/html
      - sphinx-reports:/opt/sphinx-hub/reports
    environment:
      - DOCS_AGENT_LLM_URL=http://host.docker.internal:8100
      - GITHUB_TOKEN=${GITHUB_TOKEN}
    command: python /opt/sphinx-hub/scripts/build_all.py
    # Runs on cron, not always-on

volumes:
  sphinx-repos:
  sphinx-html:
  sphinx-reports:
```

### 8. Nginx Configuration

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name sphinx.iil.pet;

    ssl_certificate /etc/letsencrypt/live/sphinx.iil.pet/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sphinx.iil.pet/privkey.pem;

    root /var/www/sphinx.iil.pet/html;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    # Per-repo docs
    location ~ ^/(bfagent|risk-hub|travel-beat|weltenhub|mcp-hub|pptx-hub|platform|trading-hub|odoo-hub|wedding-hub)/ {
        try_files $uri $uri/ =404;
    }

    # Reports API (JSON)
    location /api/reports/ {
        alias /opt/sphinx-hub/reports/;
        autoindex on;
        types { application/json json; }
    }
}
```

### 9. conf.py Template (Auto-Generated)

```python
# Template for each repo's docs/conf.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

project = "{repo_display_name}"
copyright = "2026, Achim Dehnert"
author = "Achim Dehnert"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]

html_theme = "furo"
html_title = "{repo_display_name} Documentation"
autodoc_member_order = "bysource"
autodoc_typehints = "description"
napoleon_google_docstring = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    # Cross-link between repos
    "platform": ("https://sphinx.iil.pet/platform/", None),
}
```

### 10. Build Script (build_all.py)

Core logic of the autonomous builder:

```python
async def build_all():
    repos = load_repo_config()

    for repo in repos:
        # Phase 1: Clone/Pull
        clone_or_pull(repo)

        # Phase 2: Scaffold docs if missing
        if not (repo.path / "docs" / "conf.py").exists():
            scaffold_sphinx_docs(repo)

        # Phase 3: LLM enrichment (optional, needs gateway)
        if llm_available():
            run_docs_agent_generate(repo, max_items=50)

        # Phase 4: Sphinx build
        sphinx_build(repo)

    # Phase 5: Master index
    build_master_index(repos)
    generate_quality_report(repos)
```

### 11. Cross-Repo Features

- **Intersphinx links** between repos (e.g., `weltenhub` can link to
  `platform` ADRs)
- **Shared ADR index** — all ADRs from `platform/docs/adr/` appear in
  the master index
- **Global search** — Sphinx search index across all repos
- **Quality trends** — JSON reports tracking coverage over time

### 12. LLM Enrichment Rules

The LLM enrichment is **additive only** — it never deletes or modifies
existing documentation:

1. Only generate docstrings for items with `has_docstring = False`
2. Only generate Google-style docstrings
3. Generated docstrings are committed to a `docs/auto-generated` branch
   (not main) for review
4. DIATAXIS reclassification is read-only (reporting, no file changes)
5. Max 50 items per repo per daily run (cost control)
6. Temperature: 0.3 (deterministic output)

### 13. Implementation Plan

| Phase | Deliverable | Effort |
| ----- | ----------- | ------ |
| A | SSL cert + Nginx config for sphinx.iil.pet | 15 min |
| B | Build script (`build_all.py`) + conf.py template | 2h |
| C | Master index (Jinja2 landing page) | 1h |
| D | Docker compose + cron job | 30 min |
| E | Per-repo docs scaffolding (all 10 repos) | 2h |
| F | LLM enrichment integration | 1h |
| G | Quality dashboard + reports | 1h |

Total estimated: approximately 8 hours

## Consequences

### Positive

- **Single source of truth** for all project documentation
- **Autonomous improvement** via LLM — coverage increases over time
- **Cross-repo discoverability** — search across all projects
- **CI integration** — PRs can check if docs coverage drops
- **Intersphinx** enables rich cross-linking between repos
- **Low maintenance** — cron-driven, self-healing

### Negative

- **LLM costs** — ~50 items x 10 repos x daily = ~500 LLM calls/day
  (~$0.50/day with gpt-4o-mini)
- **Build time** — full rebuild takes 5-10 minutes
- **Server disk** — ~200MB for all HTML outputs
- **Generated docstrings** need human review before merging to main

### Mitigations

- Use `gpt-4o-mini` for cost efficiency
- Incremental builds via webhook (only rebuild changed repo)
- Generated docstrings go to separate branch, not auto-merged
- Disk usage is negligible on current server (100GB+ free)

## Alternatives Considered

1. **MkDocs** — Simpler but lacks autodoc for Python APIs
2. **Read the Docs** — SaaS, but no cross-repo linking and requires
   per-repo config
3. **Docusaurus** — React-based, overkill for Python projects
4. **Manual docs only** — Does not scale, docs rot quickly

## Related

- **ADR-046**: Documentation Quality Standards (docs-agent specification)
- **ADR-042**: Dev Environment and Deploy Workflow
- **docs-agent v0.2.0**: The tool that powers the LLM enrichment pipeline
