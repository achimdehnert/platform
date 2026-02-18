# ADR-047: Sphinx Documentation Hub (sphinx.iil.pet)

| Status | Proposed |
| ------ | -------- |
| Date   | 2026-02-18 |
| Author | Achim Dehnert |
| Scope  | Platform-wide |

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

The system separates into five single-responsibility components:

```text
┌───────────────────────────────────────────────────────────┐
│                  sphinx.iil.pet (Nginx)                    │
│          Static HTML from /opt/sphinx-hub/output/html/     │
└───────────────────────────┬───────────────────────────────┘
                            │ reads
┌───────────────────────────▼───────────────────────────────┐
│            sphinx-builder Container (Docker)                │
│                                                            │
│  ┌──────────────┐                                          │
│  │ Orchestrator │ reads repos.yaml, runs steps per repo    │
│  └──────┬───────┘                                          │
│         │ delegates to                                     │
│  ┌──────▼───────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  RepoSyncer  │  │ DocsScaffold │  │  SphinxBuilder  │  │
│  │  git pull    │  │ conf.py from │  │  build per repo  │  │
│  │  per repo    │  │ template     │  │  + master index  │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
│                                                            │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ LLMEnricher  │  │   Reporter   │                        │
│  │ docs-agent   │  │ coverage %,  │                        │
│  │ → PR branch  │  │ health.json  │                        │
│  └──────┬───────┘  └──────────────┘                        │
│         │ calls                                            │
│  ┌──────▼───────┐                                          │
│  │  llm_mcp     │                                          │
│  │  gateway     │                                          │
│  └──────────────┘                                          │
└────────────────────────────────────────────────────────────┘
```

#### Component Responsibilities (SRP)

| Component | Responsibility | Input | Output |
| --------- | -------------- | ----- | ------ |
| `RepoSyncer` | `git clone` / `git pull` per repo | `repos.yaml` | Updated clones |
| `DocsScaffolder` | Generate `conf.py`, `index.rst` from templates | Repo source tree | `docs/` directory |
| `LLMEnricher` | Generate docstrings, push to PR branch | Repo clone, LLM gateway | Git branch + PR |
| `SphinxBuilder` | `sphinx-build` per repo + master index | `docs/` directory | HTML in staging dir |
| `Reporter` | Coverage trends, DIATAXIS stats, `health.json` | Build results | JSON reports |
| `Orchestrator` | Coordinate steps, error isolation per repo | `repos.yaml` | Aggregated status |

### 2. Declarative Repo Configuration

All repos are configured in a single YAML file. No hardcoded repo lists.

```yaml
# /opt/sphinx-hub/config/repos.yaml
defaults:
  type: django
  settings_module: config.settings.base
  llm_enrichment: true
  max_llm_items_per_run: 50

repos:
  - name: bfagent
    brand: Book Factory Agent
    url: git@github.com:achimdehnert/bfagent.git
    source_dirs: [apps, config]
    autodoc_mock_imports:
      - psycopg2
      - redis
      - celery
      - django_extensions

  - name: risk-hub
    brand: Schutztat
    url: git@github.com:achimdehnert/risk-hub.git
    source_dirs: [apps, config]
    autodoc_mock_imports:
      - psycopg2
      - redis
      - celery

  - name: travel-beat
    brand: DriftTales
    url: git@github.com:achimdehnert/travel-beat.git
    source_dirs: [apps, config]
    autodoc_mock_imports:
      - psycopg2
      - redis
      - celery

  - name: weltenhub
    brand: Weltenforger
    url: git@github.com:achimdehnert/weltenhub.git
    source_dirs: [apps, config]
    autodoc_mock_imports:
      - psycopg2
      - redis
      - celery
      - django_htmx

  - name: mcp-hub
    brand: MCP Servers
    url: git@github.com:achimdehnert/mcp-hub.git
    type: fastmcp
    source_dirs: [modules]
    settings_module: null
    autodoc_mock_imports: []

  - name: pptx-hub
    brand: Prezimo
    url: git@github.com:achimdehnert/pptx-hub.git
    source_dirs: [apps, config]
    autodoc_mock_imports:
      - psycopg2
      - python_pptx

  - name: platform
    brand: Platform
    url: git@github.com:achimdehnert/platform.git
    type: library
    source_dirs: [packages]
    settings_module: null
    autodoc_mock_imports: []

  - name: trading-hub
    brand: AI Trades
    url: git@github.com:achimdehnert/trading-hub.git
    source_dirs: [apps, config]
    autodoc_mock_imports:
      - psycopg2

  - name: odoo-hub
    brand: Odoo Hub
    url: git@github.com:achimdehnert/odoo-hub.git
    type: odoo
    llm_enrichment: false
    autodoc_mock_imports: []

  - name: wedding-hub
    brand: Wedding Hub
    url: git@github.com:achimdehnert/wedding-hub.git
    source_dirs: [apps, config]
    autodoc_mock_imports:
      - psycopg2
```

### 3. Directory Layout

Single base directory. No split between `/opt/` and `/var/www/`:

```text
/opt/sphinx-hub/
├── config/
│   ├── repos.yaml           # Declarative repo configuration
│   └── templates/
│       ├── conf.py.j2       # Sphinx conf.py Jinja2 template
│       ├── index.rst.j2     # Per-repo index template
│       └── master.html.j2   # Landing page template
├── repos/                   # Git clones (ephemeral, gitignored)
│   ├── bfagent/
│   ├── risk-hub/
│   └── ...
├── output/
│   ├── html/                # Sphinx build output (Nginx root)
│   │   ├── index.html       # Master landing page
│   │   ├── bfagent/
│   │   ├── risk-hub/
│   │   └── ...
│   └── reports/             # JSON quality reports
│       ├── health.json      # Aggregated build status
│       ├── bfagent.json
│       └── ...
├── staging/                 # Atomic build staging area
│   └── html/
├── scripts/
│   ├── orchestrator.py      # Main entry point
│   ├── repo_syncer.py
│   ├── docs_scaffolder.py
│   ├── llm_enricher.py
│   ├── sphinx_builder.py
│   └── reporter.py
└── docker-compose.yml
```

### 4. Per-Repo Documentation Structure

Each repo gets a Sphinx project with this standard layout:

```text
<repo>/docs/
├── conf.py              # Auto-generated from conf.py.j2
├── index.rst            # Auto-generated from index.rst.j2
├── quickstart.rst       # Converted from README.md (m2r2)
├── api/                 # autodoc from Python source
│   ├── models.rst
│   ├── views.rst
│   ├── services.rst
│   └── ...
├── architecture.rst     # ADRs relevant to this repo
├── deployment.rst       # From docker-compose + Dockerfile
└── changelog.rst        # From git tags + commit history
```

### 5. Build Pipeline (5 Phases)

#### Phase 1: Sync (RepoSyncer, no LLM)

```python
class RepoSyncer:
    """Clone or pull repos from repos.yaml. One repo at a time."""

    def sync(self, repo: RepoConfig) -> SyncResult:
        repo_path = REPOS_DIR / repo.name
        if repo_path.exists():
            run(["git", "pull", "--ff-only"], cwd=repo_path)
        else:
            run(["git", "clone", "--depth", "1", repo.url, str(repo_path)])
        return SyncResult(repo=repo.name, commit=get_head_sha(repo_path))
```

#### Phase 2: Scaffold (DocsScaffolder, no LLM)

```python
class DocsScaffolder:
    """Generate docs/ skeleton from Jinja2 templates if missing."""

    def scaffold(self, repo: RepoConfig) -> None:
        docs_dir = REPOS_DIR / repo.name / "docs"
        if (docs_dir / "conf.py").exists():
            return  # Repo has its own docs, respect them

        docs_dir.mkdir(exist_ok=True)
        self._render_template("conf.py.j2", docs_dir / "conf.py", repo)
        self._render_template("index.rst.j2", docs_dir / "index.rst", repo)
        self._generate_api_stubs(repo)
```

#### Phase 3: LLM Enrichment (LLMEnricher, persistent PR workflow)

```python
class LLMEnricher:
    """Generate missing docstrings and open PRs for review."""

    BRANCH_PREFIX = "docs/auto-enrich"

    def enrich(self, repo: RepoConfig) -> EnrichResult:
        if not repo.llm_enrichment:
            return EnrichResult(repo=repo.name, skipped=True)

        repo_path = REPOS_DIR / repo.name
        branch = f"{self.BRANCH_PREFIX}/{date.today().isoformat()}"

        # 1. Create enrichment branch from main
        run(["git", "checkout", "-B", branch, "origin/main"], cwd=repo_path)

        # 2. Run docs-agent generate (writes docstrings into source)
        result = run([
            "docs-agent", "generate", str(repo_path),
            "--apply",
            "--max-items", str(repo.max_llm_items_per_run),
        ])

        # 3. If changes exist, commit + push + open PR
        if has_uncommitted_changes(repo_path):
            run(["git", "add", "-A"], cwd=repo_path)
            run(["git", "commit", "-m",
                 f"docs: auto-generate docstrings ({result.count} items)"],
                cwd=repo_path)
            run(["git", "push", "origin", branch, "--force"], cwd=repo_path)
            self._open_or_update_pr(repo, branch)

        # 4. Return to main for Sphinx build
        run(["git", "checkout", "main"], cwd=repo_path)
        return EnrichResult(repo=repo.name, items=result.count, branch=branch)

    def _open_or_update_pr(self, repo: RepoConfig, branch: str) -> None:
        """Create or update a GitHub PR via gh CLI or GitHub API."""
        # Title: "docs: Auto-generated docstrings (2026-02-18)"
        # Body: Coverage report + list of enriched items
        # Labels: ["documentation", "auto-generated"]
        # Auto-assign: repo maintainer
        ...
```

#### Phase 4: Sphinx Build (SphinxBuilder, no LLM)

Builds into a **staging directory**, then does an **atomic swap**:

```python
class SphinxBuilder:
    """Build Sphinx HTML per repo with atomic deploy."""

    def build(self, repo: RepoConfig) -> BuildResult:
        source_dir = REPOS_DIR / repo.name / "docs"
        staging_dir = STAGING_DIR / repo.name
        output_dir = OUTPUT_HTML_DIR / repo.name

        # Build into staging (not live)
        staging_dir.mkdir(parents=True, exist_ok=True)
        result = run([
            "sphinx-build", "-b", "html",
            "-D", f"autodoc_mock_imports={repo.autodoc_mock_imports}",
            str(source_dir), str(staging_dir),
        ])

        if result.returncode == 0:
            # Atomic swap: rename staging -> live
            backup = output_dir.with_suffix(".bak")
            if output_dir.exists():
                output_dir.rename(backup)
            staging_dir.rename(output_dir)
            if backup.exists():
                shutil.rmtree(backup)

        return BuildResult(
            repo=repo.name,
            success=result.returncode == 0,
            warnings=count_warnings(result.stderr),
        )

    def build_master_index(self, results: list[BuildResult]) -> None:
        """Render the landing page from Jinja2 template."""
        ...
```

#### Phase 5: Report (Reporter, no LLM)

```python
class Reporter:
    """Generate quality reports and health status."""

    def generate(self, results: list[BuildResult]) -> None:
        # Per-repo reports (coverage, DIATAXIS)
        for result in results:
            report = self._scan_repo(result)
            self._write_json(REPORTS_DIR / f"{result.repo}.json", report)

        # Aggregated health status
        health = HealthStatus(
            timestamp=datetime.utcnow().isoformat(),
            repos={r.repo: r.success for r in results},
            total_coverage=self._calc_total_coverage(results),
        )
        self._write_json(REPORTS_DIR / "health.json", health)
```

### 6. Orchestrator (Error Isolation + Filelock)

```python
class Orchestrator:
    """Coordinate pipeline steps with per-repo error isolation."""

    LOCK_FILE = Path("/opt/sphinx-hub/.build.lock")

    def run(self) -> None:
        # Prevent concurrent builds (cron + webhook race)
        with FileLock(self.LOCK_FILE, timeout=10):
            self._run_pipeline()

    def _run_pipeline(self) -> None:
        config = load_config(CONFIG_DIR / "repos.yaml")
        results: list[BuildResult] = []

        for repo in config.repos:
            if not repo.enabled:
                continue
            try:
                self.syncer.sync(repo)
                self.scaffolder.scaffold(repo)
                self.enricher.enrich(repo)
                result = self.builder.build(repo)
                results.append(result)
            except Exception as exc:
                logger.error("Build failed for %s: %s", repo.name, exc)
                results.append(BuildResult(
                    repo=repo.name, success=False, error=str(exc),
                ))
                continue  # Next repo, don't abort pipeline

        self.builder.build_master_index(results)
        self.reporter.generate(results)
```

### 7. autodoc Mock Strategy

Django apps cannot be imported without dependencies. Each repo declares
`autodoc_mock_imports` in `repos.yaml`. The generated `conf.py` includes:

```python
# Auto-generated from conf.py.j2
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock heavy dependencies so autodoc can import modules
autodoc_mock_imports = {{ repo.autodoc_mock_imports | tojson }}

# Minimal Django setup for autodoc
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{{ repo.settings_module }}")

import django
try:
    django.setup()
except Exception:
    pass  # Best-effort; autodoc_mock_imports handles missing deps

project = "{{ repo.brand }}"
copyright = "2026, Achim Dehnert"
author = "Achim Dehnert"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]

html_theme = "furo"
html_title = "{{ repo.brand }} Documentation"
autodoc_member_order = "bysource"
autodoc_typehints = "description"
napoleon_google_docstring = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
{% for other in all_repos if other.name != repo.name %}
    "{{ other.name }}": ("https://sphinx.iil.pet/{{ other.name }}/", None),
{% endfor %}
}
```

### 8. LLM Enrichment Rules (Persistent PR Workflow)

The LLM enrichment creates **reviewable Pull Requests**, never commits
directly to `main`:

1. Create branch `docs/auto-enrich/YYYY-MM-DD` from `origin/main`
2. Run `docs-agent generate --apply --max-items 50`
3. Commit changes with message `docs: auto-generate docstrings (N items)`
4. Force-push branch (one active PR per repo at a time)
5. Create or update PR with title, coverage diff, and item list
6. Labels: `documentation`, `auto-generated`
7. PR body includes before/after coverage comparison
8. **Human merges PR after review** (never auto-merge)
9. DIATAXIS reclassification is reporting-only (no file changes)
10. Temperature: 0.3 (deterministic output)
11. Model: `gpt-4o-mini` (cost-efficient)

### 9. Automation Schedule

| Trigger | Action | Scope |
| ------- | ------ | ----- |
| Cron daily 03:00 UTC | Full pipeline (sync, scaffold, enrich, build, report) | All repos |
| GitHub webhook (push to main) | Sync + build (no LLM enrichment) | Changed repo only |
| Manual `sphinx-hub build` | Force full pipeline | All repos |
| Manual `sphinx-hub build <repo>` | Single-repo pipeline | One repo |

### 10. Docker Setup

```yaml
# /opt/sphinx-hub/docker-compose.yml
services:
  sphinx-builder:
    build:
      context: .
      dockerfile: Dockerfile
    volumes:
      - /opt/sphinx-hub/config:/opt/sphinx-hub/config:ro
      - /opt/sphinx-hub/repos:/opt/sphinx-hub/repos
      - /opt/sphinx-hub/output:/opt/sphinx-hub/output
      - /opt/sphinx-hub/staging:/opt/sphinx-hub/staging
      - /opt/sphinx-hub/scripts:/opt/sphinx-hub/scripts:ro
    env_file: /opt/sphinx-hub/.env
    user: "1000:1000"
    command: python /opt/sphinx-hub/scripts/orchestrator.py
```

```dockerfile
# /opt/sphinx-hub/Dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir \
    sphinx furo sphinx-intersphinx-inv \
    docs-agent \
    jinja2 pyyaml filelock

WORKDIR /opt/sphinx-hub
```

```bash
# /opt/sphinx-hub/.env
DOCS_AGENT_LLM_URL=http://host.docker.internal:8100
GITHUB_TOKEN=ghp_...
```

### 11. Nginx Configuration

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name sphinx.iil.pet;

    ssl_certificate /etc/letsencrypt/live/sphinx.iil.pet/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sphinx.iil.pet/privkey.pem;

    root /opt/sphinx-hub/output/html;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location /reports/ {
        alias /opt/sphinx-hub/output/reports/;
        autoindex on;
        add_header Content-Type application/json;
    }

    # Health check endpoint
    location = /health {
        alias /opt/sphinx-hub/output/reports/health.json;
        add_header Content-Type application/json;
    }
}
```

### 12. Cross-Repo Features

- **Intersphinx links** between all repos (auto-generated from `repos.yaml`)
- **Shared ADR index** in master landing page (all ADRs from `platform/`)
- **Global search** via Sphinx search index per repo
- **Quality trends** via JSON reports tracking coverage over time
- **Health endpoint** at `https://sphinx.iil.pet/health`

### 13. Monitoring and Health

The `/health` endpoint returns:

```json
{
  "timestamp": "2026-02-18T03:15:42Z",
  "status": "ok",
  "repos": {
    "bfagent": {"success": true, "coverage": 67.2, "warnings": 3},
    "risk-hub": {"success": true, "coverage": 54.1, "warnings": 0},
    "travel-beat": {"success": false, "error": "conf.py SyntaxError"}
  },
  "total_coverage": 68.4,
  "build_duration_seconds": 312,
  "next_scheduled": "2026-02-19T03:00:00Z"
}
```

### 14. Implementation Plan

| Phase | Deliverable | Effort |
| ----- | ----------- | ------ |
| A | SSL cert + Nginx config for sphinx.iil.pet | 15 min |
| B | `repos.yaml` + Jinja2 templates (`conf.py.j2`, `index.rst.j2`) | 1h |
| C | `RepoSyncer` + `DocsScaffolder` | 1h |
| D | `SphinxBuilder` with atomic deploy + staging | 1.5h |
| E | `LLMEnricher` with PR workflow (branch, commit, push, PR) | 2h |
| F | `Orchestrator` with filelock + error isolation | 1h |
| G | `Reporter` + health.json + master landing page | 1h |
| H | Dockerfile + docker-compose + cron | 30 min |
| I | Smoke test: build all 10 repos end-to-end | 1h |

Total estimated: approximately 9 hours

## Consequences

### Positive

- **Single source of truth** for all project documentation
- **Autonomous improvement** via LLM with human review gate (PRs)
- **Cross-repo discoverability** via intersphinx + master landing page
- **Error isolation** per repo (one failing repo does not block others)
- **Atomic deploys** prevent broken pages during builds
- **Declarative config** in `repos.yaml` (add a repo = add 5 lines)
- **Monitoring** via `/health` endpoint and JSON reports

### Negative

- **LLM costs** of approximately 500 calls/day (~$0.50/day with gpt-4o-mini)
- **Build time** of 5-10 min for full rebuild (10 repos)
- **PR review overhead** for LLM-generated docstrings
- **autodoc mock** may miss some type annotations from mocked packages

### Mitigations

- `gpt-4o-mini` for cost efficiency, configurable per repo
- Incremental builds via webhook (only rebuild changed repo)
- PRs include coverage diff, making review fast
- `autodoc_mock_imports` is extensible per repo in `repos.yaml`
- Disk: approximately 200MB total, negligible on 100GB+ server

## Alternatives Considered

1. **MkDocs** -- Simpler but lacks `autodoc` for Python APIs
2. **Read the Docs** -- SaaS, no cross-repo linking, per-repo config
3. **Docusaurus** -- React-based, overkill for Python projects
4. **Manual docs only** -- Does not scale, docs rot quickly
5. **Direct commit (no PR)** -- Risky, LLM output needs human review

## Related

- **ADR-046**: Documentation Quality Standards (docs-agent specification)
- **ADR-042**: Dev Environment and Deploy Workflow
- **docs-agent v0.2.0**: The tool that powers the LLM enrichment pipeline
