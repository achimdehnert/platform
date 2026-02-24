---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-043: AI-Assisted Development — Context & Workflow Optimization

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-17 |
| **Author** | Achim Dehnert |
| **Reviewers** | — |
| **Supersedes** | ADR-043 v1, ADR-044 (merged) |
| **Related** | ADR-042 (Deploy Workflow), ADR-009 (Deployment Architecture) |

---

## 1. Context

### 1.1 Current State

The BF Agent Platform uses Windsurf Cascade as its primary AI development assistant across 7 applications. AI assistants are involved in the majority of code changes but suffer from systematic context loss between sessions.

| Application | Repository | Production URL |
|-------------|-----------|----------------|
| Travel-Beat (DriftTales) | `achimdehnert/travel-beat` | `https://drifttales.app` |
| BF Agent | `achimdehnert/bfagent` | `https://bfagent.iil.pet` |
| Risk-Hub (Schutztat) | `achimdehnert/risk-hub` | `https://demo.schutztat.de` |
| Weltenhub (Weltenforger) | `achimdehnert/weltenhub` | `https://weltenforger.com` |
| PPTX-Hub (Prezimo) | `achimdehnert/pptx-hub` | `https://prezimo.de` |
| Trading-Hub | `achimdehnert/trading-hub` | `https://trading-hub.iil.pet` |
| MCP-Hub | `achimdehnert/mcp-hub` | — (library, no web UI) |

### 1.2 Pain Points

| # | Pain Point | Frequency | Impact | Intervention |
|---|-----------|-----------|--------|-------------|
| 1 | AI generates wrong file paths, imports, settings module names | Every session | HIGH | Stratified Rules |
| 2 | Repeating multi-step processes (deploy, PR review, scaffolding) | ~5x/day | HIGH | Windsurf Workflows |
| 3 | Context-switching to pgAdmin, GitHub browser, Slack | ~10x/day | HIGH | MCP Server Stack |
| 4 | AI forgets workspace-specific knowledge between sessions | Every session | MEDIUM | Memory Curation |
| 5 | Architecture rule violations (wrong base classes, wrong patterns) | ~3x/session | HIGH | Always-On Global Rule |

### 1.3 Root Cause

LLMs are stateless between sessions. No persistent, machine-readable project knowledge exists that AI assistants can consume. Current mitigation (manual prompt instructions) is inconsistent, incomplete, and non-verifiable.

### 1.4 Requirements

| Requirement | Priority |
|-------------|----------|
| Architecture rules always available to AI at session start | CRITICAL |
| Correct file paths, settings, URLs injected per-file-type | CRITICAL |
| Multi-step processes as single `/command` invocations | HIGH |
| External tools (DB, GitHub) accessible without context-switch | HIGH |
| Persistent workspace knowledge across sessions | HIGH |
| Minimal token usage (12,000 char Windsurf limit) | HIGH |

---

## 2. Decision

### 2.1 Architecture Choice

**We adopt a 4-measure optimization strategy**, each addressing a specific pain point independently:

```text
Measure 1: Stratified Rules    -- Context-aware rule activation
Measure 2: Workflows           -- Repeatable multi-step processes
Measure 3: MCP Servers         -- External tool access (already active)
Measure 4: Memory Curation     -- Session-persistent knowledge
```

Measures are additive. Each can be implemented and validated in isolation. No new infrastructure services required.

### 2.2 Key Design Decision: Separation of Platform vs. Project Rules (K-01)

The Global Rule is **split into two Always-On files**:

| File | Scope | Content | Token Budget |
|------|-------|---------|-------------|
| `platform-principles.md` | **Platform-wide** (identical in all repos) | Architecture rules, naming conventions, service layer, settings structure | ~800 chars |
| `project-facts.md` | **Per-repo** (different content per repo) | Apps, AUTH_USER_MODEL, HTMX pattern, Docker, containers, middleware | ~1,200 chars |

**Rationale**: The original v1 mixed travel-beat-specific facts into a "platform" rule. When loaded in bfagent (no HTMX) or weltenhub (uses `django_htmx`), these facts were **wrong**. Per-repo `project-facts.md` eliminates cross-contamination.

### 2.3 Rejected Alternatives

**Option A: RAG over Codebase** — Rejected. Infrastructure overhead (vector DB, embeddings). Project context is structured, not unstructured.

**Option B: `.context/*.yaml` + MCP Server + IDE Generator (ADR-043 v1)** — Rejected after review. 7 YAML files x 7 repos = 49 files to maintain. Examples contained factual errors. 3-layer architecture creates drift risk. Over-engineered for single-developer platform.

**Option C: Claude Projects / Cursor Rules Only** — Rejected. Vendor lock-in. Not portable.

---

## 3. Implementation

### 3.1 Measure 1: Stratified Rules Architecture

Windsurf enforces a **12,000-character combined limit** for rules. The stratified approach activates rules only when matching file context is active.

| Mode | Behavior | Use For |
|------|----------|---------|
| **Always On** | Every Cascade interaction | Critical principles (~2,000 chars) |
| **Glob Pattern** | When matching files are edited | File-type-specific conventions |
| **Manual** | Only via `@rule-name` mention | Rarely needed reference |

**Token budget:**

```text
12,000 chars total
  Global Rules (always loaded):     ~2,000 chars
    platform-principles.md          Always On  (~800 chars)
    project-facts.md                Always On  (~1,200 chars)
  Workspace Rules (context-aware):  ~8,000 chars
    django-conventions.md           Glob: apps/*/models.py, apps/*/views.py
    htmx-templates.md               Glob: **/templates/**
    url-routing.md                  Glob: apps/*/urls.py, */urls.py
    testing.md                      Glob: **/tests/**, **/test_*.py
    docker-deployment.md            Glob: Dockerfile, docker-compose*.yml
  Reserve:                          ~2,000 chars
```

#### Global Rule: `platform-principles.md` (Always On — identical in all repos)

```markdown
# Platform Principles (all repos)

## Settings Structure (verified across all repos)
- Settings: config.settings.base (or config.settings for single-file repos)
- Root URL conf: config.urls
- WSGI: config.wsgi.application
- DEFAULT_AUTO_FIELD: django.db.models.BigAutoField (NOT UUIDs)
- Templates: templates/ at project root (NOT per-app)

## Architecture Rules
- Service Layer: views.py -> services.py -> models.py
- Views handle HTTP only, services contain business logic
- Zero Breaking Changes: deprecate first, remove after 2 releases
- Spec vs. Derived: computed values are @property, never DB columns

## Naming Conventions
- Apps: apps.<app_name> (snake_case)
- URLs: path("<prefix>/", include("apps.<app>.urls", namespace="<app>"))
- Templates: templates/<app>/<model>_<action>.html
- Partials: templates/<app>/partials/<component>.html
- Tests: test_should_<expected_behavior>

## Infrastructure
- Server: 88.198.191.108
- Registry: ghcr.io/achimdehnert/<repo>:latest
- Compose: docker-compose.prod.yml at project root
- env_file: .env.prod (NEVER ${VAR} interpolation in compose environment:)
```

#### Global Rule: `project-facts.md` (Always On — per-repo, 4 variants shown)

**travel-beat:**
```markdown
# Project Facts: travel-beat (DriftTales)

## Apps (from config/settings/base.py LOCAL_APPS)
core, accounts, trips, locations, stories, worlds, ai_services

## Auth
- django-allauth (session-based)
- AUTH_USER_MODEL = "accounts.User"
- Login: /accounts/ (allauth URLs)

## HTMX
- NO django_htmx package installed
- Check: request.headers.get("HX-Request")
- DO NOT use request.htmx

## URL Namespace Map (from config/urls.py)
- "" -> trips | "stories/" -> stories | "locations/" -> locations
- "world/" -> worlds | "profile/" -> accounts | "ai/" -> ai_services

## Docker
- Dockerfile: docker/Dockerfile
- Container: travel_beat_web (gunicorn:8000)
- DB: travel_beat_db (postgres:15) | Redis: travel_beat_redis (redis:7)
- Celery: travel_beat_celery + travel_beat_celery_beat
- Production: https://drifttales.app
```

**bfagent:**
```markdown
# Project Facts: bfagent (Book Factory Agent)

## Apps (from config/settings/base.py INSTALLED_APPS)
core, bfagent, control_center, writing_hub, dlm_hub, medtrans, research,
expert_hub, presentation_studio, media_hub, ui_hub, mcp_hub, graph_core,
hub, genagent, workflow_system, api, sphinx_export

## Auth
- Django built-in auth (NO allauth)
- Default User model (auth.User) — no AUTH_USER_MODEL override
- Login: /login/ (django.contrib.auth views)

## HTMX
- NO HTMX usage in this project
- No django_htmx, no HX-Request checks

## URL Namespace Map (from config/urls.py)
- "bookwriting/" -> bfagent | "ui-hub/" -> ui_hub
- "control-center/" -> control_center | "expert-hub/" -> expert_hub
- "writing-hub/" -> writing_hub | "research/" -> research
- "dlm-hub/" -> dlm_hub | "media-hub/" -> media_hub
- "workflow/" -> workflow_system | "genagent/" -> genagent
- "graph/" -> graph_core | "medtrans/" -> medtrans
- "mcp-hub/" -> mcp_hub | "pptx-studio/" -> presentation_studio
- "" -> hub (catch-all, MUST be last)

## Docker
- Dockerfile: Dockerfile (project root — NOT docker/)
- Container: bfagent_web (gunicorn:8000)
- DB: bfagent_db (postgres:15)
- Production: https://bfagent.iil.pet
```

**weltenhub:**
```markdown
# Project Facts: weltenhub (Weltenforger)

## Apps (from config/settings/base.py LOCAL_APPS)
core, public, dashboard, tenants, lookups, governance, worlds, locations,
characters, scenes, stories, enrichment, location_research

## Auth
- django-allauth (session-based)
- Default User model (no AUTH_USER_MODEL override)
- Login: /accounts/ (allauth URLs)

## HTMX
- django_htmx IS installed and active
- HtmxMiddleware in MIDDLEWARE
- Use request.htmx (NOT raw header check)

## URL Namespace Map (from config/urls.py)
- "" -> public | "dashboard/" -> dashboard
- "enrichment/" -> enrichment
- API v1: "api/v1/tenants/" -> tenants | "api/v1/worlds/" -> worlds
- "api/v1/locations/" -> locations | "api/v1/characters/" -> characters
- "api/v1/scenes/" -> scenes | "api/v1/stories/" -> stories

## Multi-Tenancy
- TenantMiddleware: apps.core.middleware.tenant.TenantMiddleware
- platform_context.middleware.RequestContextMiddleware active

## Docker
- Dockerfile: Dockerfile (project root — NOT docker/)
- Container: weltenhub_web (gunicorn:8000)
- DB: weltenhub_db (postgres:15) | Redis: weltenhub_redis (redis:7)
- Celery: weltenhub_celery + weltenhub_celery_beat
- Production: https://weltenforger.com
```

**risk-hub:**
```markdown
# Project Facts: risk-hub (Schutztat)

## Apps (from src/config/settings.py INSTALLED_APPS)
NOTE: Apps have NO "apps." prefix — use bare names
common, tenancy, identity, permissions, audit, outbox, risk, actions,
documents, reporting, explosionsschutz, substances, notifications,
dashboard, approvals, ai_analysis, dsb

## Auth
- Django built-in auth (NO allauth)
- AUTH_USER_MODEL = "identity.User"
- Login: /accounts/login/ (django.contrib.auth views)

## HTMX
- django_htmx IS installed and active
- HtmxMiddleware in MIDDLEWARE
- Use request.htmx (NOT raw header check)

## Settings
- SINGLE file: src/config/settings.py (NOT split base/dev/prod)
- Source in src/ subdirectory

## URL Namespace Map (from src/config/urls.py)
- "" -> home | "dashboard/" -> dashboard
- "risk/" -> risk | "documents/" -> documents | "actions/" -> actions
- "ex/" -> explosionsschutz (HTML) | "api/ex/" -> explosionsschutz (API)
- "substances/" -> substances (HTML) | "api/substances/" -> substances (API)
- "notifications/" -> notifications | "audit/" -> audit | "dsb/" -> dsb
- "api/v1/" -> Django Ninja API

## Multi-Tenancy
- SubdomainTenantMiddleware: common.middleware.SubdomainTenantMiddleware
- RequestContextMiddleware: common.middleware.RequestContextMiddleware

## Docker
- Dockerfile: docker/app/Dockerfile
- Container: risk_hub_web
- DB: risk_hub_db (postgres:16) | Redis: risk_hub_redis (redis:7)
- Production: https://demo.schutztat.de
```

#### Workspace Rule: `django-conventions.md` (Glob: `apps/*/models.py`, `apps/*/views.py`, `*/models.py`, `*/views.py`)

```markdown
# Django Conventions

## Models
- Inherit from django.db.models.Model (no custom base classes)
- DEFAULT_AUTO_FIELD is BigAutoField — IDs are integers, not UUIDs
- Foreign keys: on_delete=models.PROTECT by default
- Define class Meta: ordering = ["-created_at"] where applicable

## Service Layer
- views.py handles HTTP request/response only
- services.py contains business logic
- models.py defines data, not business logic
```

#### Workspace Rule: `htmx-templates.md` (Glob: `**/templates/**`)

**travel-beat variant (no django_htmx):**
```markdown
# HTMX Template Conventions

## HTMX Detection (travel-beat: raw headers)
- Check: if request.headers.get("HX-Request"):
- DO NOT use request.htmx — django_htmx is NOT installed
- Partial: return render(request, "<app>/partials/<component>.html", ctx)
- Full page: return render(request, "<app>/<model>_<action>.html", ctx)

## Template Locations (verified)
- Full pages: templates/<app>/<model>_<action>.html (extend base.html)
- Partials: templates/<app>/partials/<component>.html (fragments, no extends)
- Shared includes: templates/includes/
- Account templates: templates/account/ (allauth overrides)

## HTMX Attributes
- Target: hx-target="#section-content"
- Swap: hx-swap="innerHTML" (default), outerHTML for replace
- Delete: hx-delete="..." hx-confirm="Wirklich loeschen?"
- Empty response for delete: view returns HttpResponse("")
```

**weltenhub/risk-hub variant (with django_htmx):**
```markdown
# HTMX Template Conventions

## HTMX Detection (django_htmx installed)
- Check: if request.htmx:
- Partial: return render(request, "<app>/partials/<component>.html", ctx)
- Full page: return render(request, "<app>/<model>_<action>.html", ctx)
- Access headers: request.htmx.target, request.htmx.trigger

## Template Locations
- Full pages: templates/<app>/<model>_<action>.html (extend base.html)
- Partials: templates/<app>/partials/<component>.html (fragments, no extends)

## HTMX Attributes
- Target: hx-target="#section-content"
- Swap: hx-swap="innerHTML" (default), outerHTML for replace
- Delete: hx-delete="..." hx-confirm="Wirklich loeschen?"
- Empty response for delete: view returns HttpResponse("")
```

#### Workspace Rule: `url-routing.md` (Glob: `apps/*/urls.py`, `*/urls.py`, `config/urls.py`)

```markdown
# URL Routing Conventions

## Root URL Config
- File: config/urls.py (ROOT_URLCONF = "config.urls")
- Health checks: /livez/ (liveness), /healthz/ (readiness), /health/ (compat)

## App URL Registration
- Every app: app_name = "<app_name>" in urls.py
- Root: path("<prefix>/", include("apps.<app>.urls", namespace="<app>"))
- reverse() ALWAYS with namespace: reverse("trips:trip_detail", kwargs={"pk": pk})
- Templates: {% url "trips:trip_detail" pk=trip.pk %}
- NEVER bare names: reverse("trip_detail") will FAIL

## URL Naming Convention
- List: <model>_list | Detail: <model>_detail
- Create: <model>_create | Edit: <model>_edit | Delete: <model>_delete
```

#### Workspace Rule: `testing.md` (Glob: `**/tests/**`, `**/test_*.py`)

```markdown
# Testing Conventions

## Framework
- pytest with pytest-django
- DJANGO_SETTINGS_MODULE = config.settings.test (or config.settings for risk-hub)
- Run all: python -m pytest
- Run app: python -m pytest apps/<app>/
- Run file: python -m pytest apps/<app>/tests/test_<module>.py

## Test Structure
- App tests: apps/<app>/tests/test_<module>.py
- Integration: tests/test_<feature>.py

## Test Patterns
- @pytest.mark.django_db for DB access
- Functions: test_should_<expected_behavior>
- Max 5 assertions per test, max 30 lines per function
- Mock external services (LLM, HTTP)
```

#### Workspace Rule: `docker-deployment.md` (Glob: `Dockerfile`, `docker-compose*.yml`, `.env*`)

```markdown
# Docker & Deployment Conventions

## Dockerfile Location (varies per repo)
- Target standard: docker/app/Dockerfile (per User Rules)
- travel-beat: docker/Dockerfile
- bfagent: Dockerfile (project root)
- weltenhub: Dockerfile (project root)
- risk-hub: docker/app/Dockerfile
- Base: python:3.12-slim | Non-root user | EXPOSE 8000

## Docker Compose
- File: docker-compose.prod.yml | env_file: .env.prod
- Image: ghcr.io/achimdehnert/<app>:${IMAGE_TAG:-latest}
- NEVER commit .env.prod to git

## Deploy Flow (ADR-042)
1. git push origin main
2. GitHub Actions: docker build + push to GHCR
3. SSH 88.198.191.108: docker compose pull + up -d --force-recreate
4. Health check: /livez/ returns 200
```

### 3.2 Measure 2: Windsurf Workflows

Workflows are markdown files in `.windsurf/workflows/` invoked via `/command`. All workflows include error handling: if any step returns non-zero exit code, STOP and report the error.

| Workflow | Purpose |
|----------|---------|
| `/deploy-check` | Pre-deployment verification (git, tests, lint, migrations, bf status) |
| `/pr-review` | Checkout PR, read comments, address each via GitHub MCP |
| `/adr-create` | Create ADR from template with auto-numbering |
| `/new-django-app` | Scaffold app with correct conventions |
| `/htmx-view` | Create view + template + partial + URL |

#### Workflow: `/deploy-check`

```markdown
---
description: Pre-deployment verification checklist
---
1. Check git status:
   // turbo
   git status --short
   If uncommitted changes exist, STOP and list them.

2. Run test suite:
   // turbo
   python -m pytest --tb=short -q
   If exit code != 0, STOP and report failures.

3. Run linting:
   // turbo
   ruff check .
   If exit code != 0, STOP and report lint errors.

4. Check for pending migrations:
   // turbo
   python manage.py showmigrations --list | grep "\[ \]"
   If unapplied migrations found, STOP and ask for confirmation.

5. Check deploy status:
   // turbo
   bf status
   If bf is not installed, SKIP this step and note it in the report.

6. Print deployment readiness report with pass/fail per step.
```

#### Workflow: `/new-django-app`

```markdown
---
description: Scaffold a new Django app with Platform conventions
---
Inputs: App name (snake_case), brief description.

1. Check if app already exists:
   // turbo
   ls apps/{app_name}/ 2>/dev/null
   If directory exists, STOP and report: "App already exists."

2. Create directory structure:
   mkdir -p apps/{app_name}/tests
   mkdir -p templates/{app_name}/partials
   touch apps/{app_name}/__init__.py
   touch apps/{app_name}/models.py
   touch apps/{app_name}/views.py
   touch apps/{app_name}/urls.py
   touch apps/{app_name}/forms.py
   touch apps/{app_name}/admin.py
   touch apps/{app_name}/services.py
   touch apps/{app_name}/tests/__init__.py

3. Create apps.py with default_auto_field = "django.db.models.BigAutoField"
   and name = "apps.{app_name}"

4. Create urls.py with app_name = "{app_name}" and empty urlpatterns

5. Register in config/settings/base.py LOCAL_APPS:
   Add "apps.{app_name}" ONLY IF not already present in the list.

6. Register in config/urls.py:
   Add path("{app_name}/", include("apps.{app_name}.urls", namespace="{app_name}"))
   ONLY IF not already present.

7. Create initial migration:
   python manage.py makemigrations {app_name}

8. Verify:
   // turbo
   python manage.py check
   If exit code != 0, report the error.
```

#### Workflow: `/pr-review`

```markdown
---
description: Review and address PR comments using GitHub MCP
---
Inputs: PR number.

1. Fetch PR details using GitHub MCP:
   Use mcp7_get_pull_request to get PR title, body, base/head branches.
   Print summary of the PR.

2. Fetch changed files:
   Use mcp7_get_pull_request_files to list all changed files.
   Print file list with additions/deletions count.

3. Fetch review comments:
   Use mcp7_get_pull_request_comments to get all review comments.
   If no comments, report "No review comments found" and STOP.

4. For each review comment:
   a. Read the referenced file at the commented line.
   b. Understand the reviewer's request.
   c. Implement the requested change using the edit tool.
   d. After fixing, print: "Fixed: <file>:<line> — <summary>"

5. After all comments addressed:
   // turbo
   python -m pytest --tb=short -q
   If tests fail, report which tests broke and suggest fixes.

6. Stage and summarize all changes:
   // turbo
   git diff --stat
   Print a commit message suggestion following: fix: address PR #<number> review comments
```

#### Workflow: `/adr-create`

```markdown
---
description: Create new ADR with automatic scope detection and proper structure
---
Inputs: Title (short), context description.

1. Determine next ADR number:
   // turbo
   ls docs/adr/ADR-0*.md | sort -t- -k2 -n | tail -1
   Extract the highest number and increment by 1.

2. Generate filename: ADR-{NNN}-{title-kebab-case}.md

3. Create the ADR file with this template:
   # ADR-{NNN}: {Title}

   | Metadata | Value |
   |----------|-------|
   | **Status** | Proposed |
   | **Date** | {today YYYY-MM-DD} |
   | **Author** | Achim Dehnert |
   | **Reviewers** | — |
   | **Supersedes** | — |
   | **Related** | {detect related ADRs from context} |

   ---

   ## 1. Context
   {User-provided context description}

   ## 2. Decision
   {To be filled}

   ## 3. Implementation
   {To be filled}

   ## 4. Consequences
   ### 4.1 Positive
   ### 4.2 Negative
   ### 4.3 Mitigation

   ## 5. Changelog
   | Date | Author | Change |
   |------|--------|--------|
   | {today} | Achim Dehnert | Initial draft |

4. Open the created file for editing.

5. Print: "Created ADR-{NNN} at docs/adr/{filename}"
```

#### Workflow: `/htmx-view`

```markdown
---
description: Create an HTMX view with template, partial, and URL registration
---
Inputs: App name, model name, action (list/detail/create/edit/delete).

1. Check that the app exists:
   // turbo
   ls apps/{app_name}/views.py
   If not found, STOP and suggest running /new-django-app first.

2. Create or update the view function in apps/{app_name}/views.py:
   - For list/detail/create/edit: standard view with form handling
   - HTMX detection: use project-facts.md to determine pattern
     (request.htmx for django_htmx repos, request.headers.get("HX-Request") otherwise)
   - HTMX: return render(request, "{app_name}/partials/{model}_{action}.html", ctx)
   - Non-HTMX: return render(request, "{app_name}/{model}_{action}.html", ctx)
   - Add @login_required decorator

3. Create the full-page template:
   templates/{app_name}/{model}_{action}.html
   Must extend base.html with {% extends "base.html" %}
   Include the partial via {% include "{app_name}/partials/{model}_{action}.html" %}

4. Create the partial template:
   templates/{app_name}/partials/{model}_{action}.html
   Standalone HTML fragment (no extends, no base)

5. Register URL in apps/{app_name}/urls.py:
   Add path for the view ONLY IF not already registered.
   Follow naming: name="{model}_{action}"

6. Verify:
   // turbo
   python manage.py check
   If exit code != 0, report the error.

7. Print summary: "Created: view, template, partial, URL for {app_name}.{model}_{action}"
```

### 3.3 Measure 3: MCP Server Stack

These MCP servers are **already configured and active** in the current Windsurf setup:

| MCP Server | Purpose | Status |
|------------|---------|--------|
| `postgres` | Schema inspection, query execution | Active |
| `github` | PRs, issues, commits, branches | Active |
| `deployment-mcp` | Server management, Docker, SSH, CI/CD | Active |
| `filesystem` | Remote file operations | Active |
| Per-app DB servers | Direct DB access per application | Active |

No new MCP servers needed for Phase 1. A `platform-context` MCP server is deferred to Phase 2 contingent on Phase 1 effectiveness.

### 3.4 Measure 4: Memory Curation Strategy

**Verified memories to set (per workspace):**

Memories should match `project-facts.md` for each repo. Example for travel-beat:

```text
Settings module: config.settings.base (split: base/development/production/test)
Root URL conf: config.urls — NOT travel_beat.urls
Apps: core, accounts, trips, locations, stories, worlds, ai_services
Auth: django-allauth. AUTH_USER_MODEL = "accounts.User"
Templates at project root: templates/<app>/<model>_<action>.html
HTMX: request.headers.get("HX-Request") — NO django_htmx
Dockerfile: docker/Dockerfile. Compose: docker-compose.prod.yml
DEFAULT_AUTO_FIELD: BigAutoField (integer PKs, NOT UUIDs)
Production domain: drifttales.app. Server: 88.198.191.108
```

**Weekly cleanup ritual:**

1. Open Windsurf Settings > Manage Memories
2. Delete memories referencing refactored files/patterns
3. Delete duplicate memories
4. Verify remaining memories match current `project-facts.md`

---

## 4. Migration Plan

### Phase 1: Quick Wins (Week 1)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Create `platform-principles.md` + `project-facts.md` | `.windsurf/rules/` (2 Always-On files per repo) |
| 1 | Create 5 workspace rules (django, templates, URLs, testing, docker) | `.windsurf/rules/*.md` |
| 2 | Set verified memories per workspace | Curated memories |
| 2 | Create `/deploy-check` + `/adr-create` workflows | `.windsurf/workflows/*.md` |
| 3 | Create `/new-django-app` + `/htmx-view` + `/pr-review` workflows | 3 workflow files |
| 4 | Test all rules and workflows on travel-beat | Validation pass |
| 5 | Rollout adapted rules to bfagent, weltenhub, risk-hub | Per-repo `project-facts.md` |

### Phase 2: MCP Context Server (Week 2-3, if Phase 1 effective)

| Task | Deliverable |
|------|-------------|
| `platform-context` MCP server with project fact Resources | `mcp-hub/platform_context_mcp/` |
| Tools: `get_url_pattern`, `find_file`, `get_setting` | MCP Tools |
| Integration test with Windsurf session | Validated workflow |

### Phase 3: Hardening (Week 3-4)

| Task | Deliverable |
|------|-------------|
| CI validation: rules match actual settings/URLs | GitHub Action |
| Retrospective + ADR finalization | Status -> Accepted |

---

## 5. Consequences

### 5.1 Positive

- **Correct paths and settings from session start** via Always-On rules
- **No cross-repo contamination** — `project-facts.md` is per-repo
- **Repeatable processes as `/command`** compress 10-min tasks to single invocation
- **Minimal token waste** via Glob-pattern activation
- **No new infrastructure** — rules and workflows are markdown files
- **Verified facts only** — every statement traceable to actual `grep` results

### 5.2 Negative

- **Maintenance**: Rules must be updated when settings/URLs change
- **Windsurf-specific**: Workflows and rule activation are Windsurf features
- **Memory staleness**: Even with curation, memories can become outdated

### 5.3 Mitigation

| Risk | Mitigation |
|------|------------|
| Rule drift from actual code | CI validation in Phase 3; rules reviewed in PRs |
| Workflow drift from process | Workflows are markdown — review alongside code |
| Memory staleness | Weekly cleanup; prefer rules over memories |
| Windsurf lock-in | Rule content is plain markdown (portable); MCP is standard |
| Rules degrade Cascade behavior | Rollback: delete `.windsurf/rules/` to restore pre-ADR state |
| Cross-repo contamination | project-facts.md is per-repo; platform-principles.md has NO repo-specific content |

---

## 6. Success Criteria

### 6.1 Binary (pass/fail)

- [ ] `platform-principles.md` identical in all repos
- [ ] `project-facts.md` correct per repo (verified against settings.py)
- [ ] Cascade generates correct `config.urls` (not `travel_beat.urls`) in new session
- [ ] Cascade uses correct HTMX pattern per repo (raw headers vs. django_htmx)
- [ ] Cascade creates templates in `templates/<app>/` (not `apps/<app>/templates/`)
- [ ] `/deploy-check` workflow runs all steps without manual intervention
- [ ] `/new-django-app` scaffolds correct structure with `BigAutoField`
- [ ] `/pr-review` fetches and addresses all review comments
- [ ] `/adr-create` generates correctly numbered ADR from template
- [ ] `/htmx-view` creates view + template + partial + URL in one invocation

### 6.2 Qualitative

- [ ] All 4 main repos have `.windsurf/rules/` with adapted project-facts
- [ ] Developer reports: "Cascade knows my project without re-explaining"

---

## 7. References

- [Windsurf Workflows](https://docs.windsurf.com/windsurf/cascade/workflows)
- [Windsurf Rules & Activation Modes](https://docs.windsurf.com/windsurf/cascade/rules)
- [Windsurf MCP Integration](https://docs.windsurf.com/windsurf/cascade/mcp)
- [ADR-042: Dev Environment & Deploy Workflow](./ADR-042-dev-environment-deploy-workflow.md)
- [PLATFORM_ARCHITECTURE_MASTER](../PLATFORM_ARCHITECTURE_MASTER.md)

---

## 8. Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-02-17 | Achim Dehnert | v1: Initial draft (Platform Context Store) |
| 2026-02-17 | Achim Dehnert | v2: Merged ADR-043 + ADR-044, corrected all codebase facts, reduced scope |
| 2026-02-17 | Achim Dehnert | v2.1: K-03 — all 5 rules and 5 workflows fully defined |
| 2026-02-17 | Achim Dehnert | v2.2: K-01 — split Global Rule into platform-principles.md + project-facts.md per repo; 4 repo variants defined |
