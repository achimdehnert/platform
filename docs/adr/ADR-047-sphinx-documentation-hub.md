---
status: superseded
date: 2026-02-21
decision-makers: Achim Dehnert
---

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

The system separates into seven single-responsibility components:

```text
┌──────────────────────────────────────────────────────────────┐
│                    sphinx.iil.pet (Nginx)                      │
│        Static HTML + Pagefind search from output/html/         │
└──────────────────────────────┬───────────────────────────────┘
                               │ reads
┌──────────────────────────────▼───────────────────────────────┐
│              sphinx-builder Container (Docker)                  │
│                                                                │
│  ┌──────────────┐                                              │
│  │ Orchestrator │── reads repos.yaml, delegates to:            │
│  └──────┬───────┘                                              │
│         │                                                      │
│  ┌──────▼───────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │  RepoSyncer  │  │DocsScaffolder│  │    SphinxBuilder      │ │
│  │  git pull    │  │ conf.py from │  │  build per repo       │ │
│  │  per repo    │  │ template     │  │  + atomic deploy      │ │
│  └──────────────┘  └──────────────┘  └───────────┬───────────┘ │
│                                                  │             │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────▼───────────┐ │
│  │ LLMEnricher  │  │SearchIndexer │  │      Reporter         │ │
│  │ docs-agent   │  │ pagefind     │  │  builds + coverage    │ │
│  │ → PR branch  │  │ cross-repo   │  │  → PostgreSQL         │ │
│  └──────┬───────┘  └──────────────┘  └───────────┬───────────┘ │
│         │ calls                                  │ writes      │
│  ┌──────▼───────┐                      ┌─────────▼───────────┐ │
│  │  llm_mcp     │                      │    PostgreSQL       │ │
│  │  gateway     │                      │    sphinx_hub DB    │ │
│  └──────────────┘                      └─────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

#### Component Responsibilities (SRP)

| Component | Responsibility | Input | Output |
| --------- | -------------- | ----- | ------ |
| `RepoSyncer` | `git clone` / `git pull` per repo | `repos.yaml` | Updated clones |
| `DocsScaffolder` | Generate `conf.py`, `index.rst` from templates | Repo source tree | `docs/` directory |
| `LLMEnricher` | Generate docstrings, push to PR branch | Repo clone, LLM gateway | Git branch + PR |
| `SphinxBuilder` | `sphinx-build` per repo + master index | `docs/` directory | HTML in staging dir |
| `SearchIndexer` | Build cross-repo Pagefind search index | HTML output dir | `_pagefind/` assets |
| `Reporter` | Build history, coverage trends → PostgreSQL | Build results, DB | DB rows + `health.json` |
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
│   │   ├── _pagefind/       # Cross-repo search index (Pagefind)
│   │   ├── bfagent/
│   │   ├── risk-hub/
│   │   └── ...
│   └── reports/             # Cached JSON (generated from DB)
│       └── health.json      # Aggregated status for /health endpoint
├── staging/                 # Atomic build staging area
│   └── html/
├── scripts/
│   ├── orchestrator.py      # Main entry point
│   ├── repo_syncer.py
│   ├── docs_scaffolder.py
│   ├── llm_enricher.py
│   ├── sphinx_builder.py
│   ├── search_indexer.py
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

### 5. Build Pipeline (6 Phases)

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

#### Phase 5: Search Indexing (SearchIndexer, no LLM)

After all repos are built, build a **cross-repo search index** using
[Pagefind](https://pagefind.app/) (static, zero-server, ~100KB JS+WASM):

```python
class SearchIndexer:
    """Build cross-repo Pagefind search index from HTML output."""

    def index(self) -> IndexResult:
        result = run([
            "pagefind",
            "--site", str(OUTPUT_HTML_DIR),
            "--glob", "**/*.html",
        ])
        return IndexResult(
            success=result.returncode == 0,
            pages_indexed=self._parse_page_count(result.stdout),
        )
```

Pagefind generates `output/html/_pagefind/` with a self-contained search
widget. The master landing page and each repo's Sphinx theme include the
Pagefind CSS/JS for unified cross-repo search.

#### Phase 6: Report (Reporter, PostgreSQL)

```python
class Reporter:
    """Persist build results to PostgreSQL and generate health.json."""

    def __init__(self, db: Connection) -> None:
        self.db = db

    def generate(
        self, build_id: int, results: list[BuildResult],
    ) -> None:
        for result in results:
            # Persist per-repo build result
            self._insert_build_result(build_id, result)

            # Persist coverage snapshot for trend tracking
            if result.success:
                coverage = self._scan_coverage(result)
                self._insert_coverage_snapshot(result.repo, coverage)

        # Generate health.json from DB (cached file for Nginx)
        health = self._build_health_from_db(build_id)
        self._write_json(REPORTS_DIR / "health.json", health)

    def _build_health_from_db(self, build_id: int) -> dict:
        """Query DB for current + trend data."""
        current = self.db.execute(
            "SELECT * FROM build_results WHERE build_id = %s",
            [build_id],
        ).fetchall()
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "ok" if all(r.success for r in current) else "degraded",
            "repos": {r.repo: self._repo_status(r) for r in current},
            "total_coverage": self._avg_coverage(build_id),
            "build_duration_seconds": self._build_duration(build_id),
            "trend_7d": self._coverage_trend(days=7),
        }
```

### 6. Orchestrator (Error Isolation + Filelock)

```python
class Orchestrator:
    """Coordinate pipeline steps with per-repo error isolation."""

    LOCK_FILE = Path("/opt/sphinx-hub/.build.lock")

    def run(self, trigger: str = "manual") -> None:
        # Prevent concurrent builds (cron + webhook race)
        with FileLock(self.LOCK_FILE, timeout=10):
            self._run_pipeline(trigger)

    def _run_pipeline(self, trigger: str) -> None:
        config = load_config(CONFIG_DIR / "repos.yaml")
        build_id = self.reporter.create_build(trigger, len(config.repos))
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
        self.search_indexer.index()  # Cross-repo Pagefind index
        self.reporter.generate(build_id, results)
```

### 7. Persistence Layer (PostgreSQL)

The existing PostgreSQL 16 on `88.198.191.108` hosts a dedicated `sphinx_hub`
database. This enables build history, coverage trends, and enrichment tracking
across runs -- capabilities impossible with flat JSON files.

#### Database: `sphinx_hub`

```sql
-- Build runs (one row per pipeline execution)
CREATE TABLE builds (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    trigger TEXT NOT NULL,  -- 'cron', 'webhook', 'manual'
    total_repos INTEGER NOT NULL,
    successful INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0
);

-- Per-repo build results (one row per repo per build)
CREATE TABLE build_results (
    id BIGSERIAL PRIMARY KEY,
    build_id BIGINT NOT NULL REFERENCES builds(id) ON DELETE CASCADE,
    repo TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    coverage_pct REAL,
    warnings INTEGER DEFAULT 0,
    error TEXT,
    commit_sha TEXT,
    duration_seconds REAL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_build_results_repo ON build_results(repo, created_at DESC);

-- Coverage time-series (one row per repo per successful build)
CREATE TABLE coverage_snapshots (
    id BIGSERIAL PRIMARY KEY,
    repo TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    total_items INTEGER NOT NULL,
    documented_items INTEGER NOT NULL,
    coverage_pct REAL NOT NULL,
    diataxis_tutorial INTEGER DEFAULT 0,
    diataxis_howto INTEGER DEFAULT 0,
    diataxis_reference INTEGER DEFAULT 0,
    diataxis_explanation INTEGER DEFAULT 0
);
CREATE INDEX idx_coverage_repo_time ON coverage_snapshots(repo, recorded_at DESC);

-- LLM enrichment tracking (one row per enrichment run per repo)
CREATE TABLE enrichment_runs (
    id BIGSERIAL PRIMARY KEY,
    build_id BIGINT REFERENCES builds(id) ON DELETE CASCADE,
    repo TEXT NOT NULL,
    branch TEXT,
    pr_number INTEGER,
    pr_status TEXT DEFAULT 'open',  -- 'open', 'merged', 'closed'
    items_generated INTEGER DEFAULT 0,
    items_skipped INTEGER DEFAULT 0,
    llm_model TEXT,
    llm_cost_usd REAL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_enrichment_repo ON enrichment_runs(repo, created_at DESC);
```

#### Key Queries

```sql
-- Coverage trend for a repo (last 30 days)
SELECT recorded_at::date AS day, coverage_pct
FROM coverage_snapshots
WHERE repo = 'bfagent' AND recorded_at > now() - INTERVAL '30 days'
ORDER BY recorded_at;

-- Which repos are declining?
SELECT repo,
       (SELECT coverage_pct FROM coverage_snapshots cs2
        WHERE cs2.repo = cs.repo ORDER BY recorded_at DESC LIMIT 1)
       - AVG(coverage_pct) AS trend_delta
FROM coverage_snapshots cs
WHERE recorded_at > now() - INTERVAL '7 days'
GROUP BY repo
HAVING AVG(coverage_pct) > 0;

-- Open enrichment PRs (avoid re-generating same items)
SELECT repo, branch, pr_number, items_generated
FROM enrichment_runs
WHERE pr_status = 'open';

-- Build failure history
SELECT br.repo, br.error, b.started_at
FROM build_results br
JOIN builds b ON b.id = br.build_id
WHERE br.success = false
ORDER BY b.started_at DESC
LIMIT 20;
```

#### Connection

The `sphinx-builder` container connects to the host PostgreSQL via
`DATABASE_URL` in `.env`:

```bash
DATABASE_URL=postgresql://sphinx_hub:***@host.docker.internal:5432/sphinx_hub
```

The database is created once via deployment-mcp:

```bash
# Via deployment-mcp database_manage
mcp5_database_manage(action="create", db_name="sphinx_hub", owner="sphinx_hub")
```

### 8. Global Search (Pagefind)

Every documentation hub lives or dies by its search. Sphinx's built-in search
is **per-project only** -- a developer searching for "TenantMiddleware" would
have to search 10 repos individually. This is unacceptable.

#### Solution: Pagefind

[Pagefind](https://pagefind.app/) is a static search library that:

- Indexes all HTML after build (zero server, ~100KB JS+WASM payload)
- Supports **cross-site indexing** (merges multiple output directories)
- Filters by `data-pagefind-meta` attributes (repo name, doc type)
- Works offline, no external service dependency

#### Integration

##### Step 1: Index after Sphinx build

```bash
pagefind --site /opt/sphinx-hub/output/html/ --glob "**/*.html"
# Creates /opt/sphinx-hub/output/html/_pagefind/
```

##### Step 2: Add metadata to Sphinx output

The `conf.py.j2` template adds Pagefind attributes via Furo's template
customization:

```python
# In conf.py.j2 -- Pagefind metadata for cross-repo filtering
html_theme_options = {
    "announcement": (
        '<a href="https://sphinx.iil.pet/">← Back to Hub</a>'
        ' | <a href="https://sphinx.iil.pet/#search">Search All Repos</a>'
    ),
}

# Pagefind metadata injected via html_context
html_context = {
    "pagefind_repo": "{{ repo.name }}",
    "pagefind_brand": "{{ repo.brand }}",
}
```

##### Step 3: Search widget on landing page

```html
<!-- In master.html.j2 -->
<div id="search" class="pagefind-ui-container">
    <link href="/_pagefind/pagefind-ui.css" rel="stylesheet">
    <script src="/_pagefind/pagefind-ui.js"></script>
    <div id="search-widget"></div>
    <script>
        new PagefindUI({
            element: "#search-widget",
            showSubResults: true,
            showImages: false,
        });
    </script>
</div>
```

##### Step 4: Per-repo Sphinx pages include search link

Via `html_theme_options["announcement"]` (set in Step 2), every Sphinx page
shows a persistent header bar with "← Back to Hub" and "Search All Repos"
links. This solves the navigation problem between repos.

#### Search Features

| Feature | How |
| ------- | --- |
| Cross-repo search | Single Pagefind index over all `output/html/` |
| Filter by repo | `data-pagefind-filter="repo:bfagent"` via Sphinx template |
| Filter by type | `data-pagefind-filter="type:api"` for API docs vs. guides |
| Highlight matches | Built-in Pagefind highlight |
| Zero server | Static JS+WASM, served by Nginx |

### 9. autodoc Mock Strategy

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

### 10. LLM Enrichment Rules (Persistent PR Workflow)

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

### 11. Automation Schedule

| Trigger | Action | Scope |
| ------- | ------ | ----- |
| Cron daily 03:00 UTC | Full pipeline (sync, scaffold, enrich, build, report) | All repos |
| GitHub webhook (push to main) | Sync + build (no LLM enrichment) | Changed repo only |
| Manual `sphinx-hub build` | Force full pipeline | All repos |
| Manual `sphinx-hub build <repo>` | Single-repo pipeline | One repo |

### 12. Docker Setup

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
    jinja2 pyyaml filelock psycopg2-binary

# Install Pagefind for cross-repo search indexing
RUN curl -sL https://github.com/CloudCannon/pagefind/releases/latest/download/pagefind-linux-x86_64.tar.gz \
    | tar xz -C /usr/local/bin/

WORKDIR /opt/sphinx-hub
```

```bash
# /opt/sphinx-hub/.env
DOCS_AGENT_LLM_URL=http://host.docker.internal:8100
DATABASE_URL=postgresql://sphinx_hub:***@host.docker.internal:5432/sphinx_hub
GITHUB_TOKEN=ghp_...
```

### 13. Nginx Configuration

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

    # Pagefind search assets (cross-repo index)
    location /_pagefind/ {
        alias /opt/sphinx-hub/output/html/_pagefind/;
        expires 1h;
        add_header Cache-Control "public, immutable";
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

### 14. Cross-Repo Features

- **Global search** via Pagefind cross-repo index (Section 8) -- single search
  box on landing page searches all 10 repos simultaneously
- **Intersphinx links** between all repos (auto-generated from `repos.yaml`)
- **Shared ADR index** in master landing page (all ADRs from `platform/`,
  rendered via `myst-parser` for Markdown compatibility)
- **Coverage trends** queryable from PostgreSQL (Section 7) -- 30-day trends,
  regression detection, per-repo and aggregate dashboards
- **Hub navigation** on every Sphinx page via Furo announcement bar:
  "← Back to Hub | Search All Repos" (Section 8, Step 4)
- **Edit on GitHub** links on every page via Furo's `source_repository`
  and `source_edit_link` theme options
- **Health endpoint** at `https://sphinx.iil.pet/health` with trend data

### 15. Monitoring and Health

The `/health` endpoint returns data generated from PostgreSQL, including
7-day coverage trends per repo:

```json
{
  "timestamp": "2026-02-18T03:15:42Z",
  "status": "degraded",
  "build_id": 142,
  "repos": {
    "bfagent": {
      "success": true,
      "coverage": 67.2,
      "coverage_7d_ago": 63.1,
      "trend": "+4.1",
      "warnings": 3
    },
    "risk-hub": {
      "success": true,
      "coverage": 54.1,
      "coverage_7d_ago": 54.1,
      "trend": "0.0",
      "warnings": 0
    },
    "travel-beat": {
      "success": false,
      "error": "conf.py SyntaxError",
      "last_successful_build": "2026-02-16T03:12:00Z"
    }
  },
  "total_coverage": 68.4,
  "total_coverage_7d_ago": 65.9,
  "build_duration_seconds": 312,
  "search_pages_indexed": 1847,
  "next_scheduled": "2026-02-19T03:00:00Z"
}
```

### 16. Implementation Plan

| Phase | Deliverable | Effort |
| ----- | ----------- | ------ |
| A | SSL cert + Nginx config for `sphinx.iil.pet` | 15 min |
| B | PostgreSQL: create `sphinx_hub` DB + run schema migration | 30 min |
| C | `repos.yaml` + Jinja2 templates (`conf.py.j2`, `index.rst.j2`) | 1h |
| D | `RepoSyncer` + `DocsScaffolder` | 1h |
| E | `SphinxBuilder` with atomic deploy + staging | 1.5h |
| F | `SearchIndexer` (Pagefind) + landing page search widget | 1h |
| G | `LLMEnricher` with PR workflow (branch, commit, push, PR) | 2h |
| H | `Reporter` with PostgreSQL persistence + `health.json` | 1.5h |
| I | `Orchestrator` with filelock + error isolation | 1h |
| J | Master landing page (repo tiles, search, ADR index, trends) | 1.5h |
| K | Dockerfile + docker-compose + cron | 30 min |
| L | Smoke test: build all 10 repos end-to-end | 1h |

Total estimated: approximately 12 hours

## Consequences

### Positive

- **Single source of truth** for all project documentation
- **Global cross-repo search** via Pagefind (zero-server, ~100KB)
- **Coverage trends** with 30-day history in PostgreSQL
- **Autonomous improvement** via LLM with human review gate (PRs)
- **Cross-repo discoverability** via intersphinx + Pagefind + master index
- **Error isolation** per repo (one failing repo does not block others)
- **Atomic deploys** prevent broken pages during builds
- **Declarative config** in `repos.yaml` (add a repo = add 5 lines)
- **Monitoring** via `/health` endpoint with trend data from DB
- **MCP-queryable** build history (deployment-mcp can query `sphinx_hub` DB)

### Negative

- **LLM costs** of approximately 500 calls/day (~$0.50/day with gpt-4o-mini)
- **Build time** of 5-10 min for full rebuild (10 repos)
- **PR review overhead** for LLM-generated docstrings
- **autodoc mock** may miss some type annotations from mocked packages
- **PostgreSQL dependency** adds operational complexity vs. flat files
- **Pagefind re-index** adds approximately 30s to each full build

### Mitigations

- `gpt-4o-mini` for cost efficiency, configurable per repo
- Incremental builds via webhook (only rebuild changed repo)
- PRs include coverage diff, making review fast
- `autodoc_mock_imports` is extensible per repo in `repos.yaml`
- PostgreSQL is already running for all other apps (zero new infra)
- Pagefind indexing is fast (~3s per 1000 pages) and only runs post-build
- Disk: approximately 200MB total, negligible on 100GB+ server

## Alternatives Considered

1. **MkDocs** -- Simpler but lacks `autodoc` for Python APIs
2. **Read the Docs** -- SaaS, no cross-repo linking, per-repo config
3. **Docusaurus** -- React-based, overkill for Python projects
4. **Manual docs only** -- Does not scale, docs rot quickly
5. **Direct commit (no PR)** -- Risky, LLM output needs human review
6. **Meilisearch/Typesense** -- Full search servers, overkill for static docs
7. **SQLite** -- Simpler but not queryable from other systems (MCP, monitoring)
8. **Flat JSON files** -- No trend tracking, no history, no cross-system queries

## Related

- **ADR-046**: Documentation Quality Standards (docs-agent specification)
- **ADR-042**: Dev Environment and Deploy Workflow
- **docs-agent v0.2.0**: The tool that powers the LLM enrichment pipeline
