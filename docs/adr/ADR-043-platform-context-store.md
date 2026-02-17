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

### 2.2 Rejected Alternatives

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
    platform-principles.md          Always On
  Workspace Rules (context-aware):  ~8,000 chars
    django-conventions.md           Glob: apps/*/models.py, apps/*/views.py
    htmx-templates.md               Glob: **/templates/**
    url-routing.md                  Glob: apps/*/urls.py
    testing.md                      Glob: **/tests/**
    docker-deployment.md            Glob: Dockerfile, docker-compose*.yml
  Reserve:                          ~2,000 chars
```

#### Global Rule: `platform-principles.md` (Always On)

All facts verified against the actual codebase as of 2026-02-17.

```markdown
# BF Agent Platform — Core Principles

## Project Structure (verified)
- Settings: `config.settings.base` (split: base/development/production/test)
- Root URL conf: `config.urls`
- WSGI: `config.wsgi.application`
- DEFAULT_AUTO_FIELD: `django.db.models.BigAutoField` (NOT UUIDs)
- Auth: `django-allauth` (session-based, NOT DRF TokenAuthentication)
- Templates: `templates/` at project root (NOT per-app)
- Dockerfile: `docker/Dockerfile` (NOT project root)
- Compose: `docker-compose.prod.yml` at project root

## Apps (travel-beat — verified)
- `apps.core` — health checks, legal pages
- `apps.accounts` — User model (AUTH_USER_MODEL = "accounts.User")
- `apps.trips` — trips, stops, transport (namespace: "trips")
- `apps.locations` — location data (namespace: "locations")
- `apps.stories` — AI story generation (namespace: "stories")
- `apps.worlds` — characters, places (namespace: "worlds")
- `apps.ai_services` — LLM endpoints (namespace: "ai_services")

## HTMX (no django_htmx package)
- Check: `request.headers.get("HX-Request")` (NOT `request.htmx`)
- Partials: `templates/<app>/partials/<component>.html`
- Full pages extend `templates/base.html`

## Architecture Rules
- Zero Breaking Changes: Deprecate first, remove after 2 releases
- Spec vs. Derived: Computed values are @property, never DB columns
- Service Layer: views.py -> services.py -> models.py

## Multi-Tenancy Status
- RequestContextMiddleware active (sets request_id, user_id)
- RLS: NOT implemented in travel-beat (planned)
- travel-beat is single-tenant (user-scoped via request.user)

## Docker (travel-beat — verified)
- Image: ghcr.io/achimdehnert/travel-beat:latest
- Container: travel_beat_web (gunicorn port 8000)
- PostgreSQL 15: travel_beat_db
- Redis 7: travel_beat_redis
- Server: 88.198.191.108
```

#### Workspace Rule: `django-conventions.md` (Glob: `apps/*/models.py`, `apps/*/views.py`)

```markdown
# Django Conventions

## Models
- Inherit from django.db.models.Model (no custom base classes in travel-beat)
- DEFAULT_AUTO_FIELD is BigAutoField — IDs are integers, not UUIDs
- Foreign keys: on_delete=models.PROTECT by default
- Define class Meta: ordering = ["-created_at"] where applicable

## Views — HTMX Pattern
- Check HTMX: if request.headers.get("HX-Request"):
- Return partial: return render(request, "trips/partials/stop_card.html", ctx)
- DO NOT use request.htmx — django_htmx is not installed

## Service Layer
- views.py handles HTTP request/response only
- services.py contains business logic
- models.py defines data, not business logic
```

#### Workspace Rule: `htmx-templates.md` (Glob: `**/templates/**`)

```markdown
# HTMX Template Conventions

## Template Locations (verified)
- Full pages: templates/<app>/<model>_<action>.html (extend base.html)
- Partials: templates/<app>/partials/<component>.html (fragments)
- Shared includes: templates/includes/
- Account templates: templates/account/ (allauth overrides)

## Existing Partials (travel-beat)
- templates/trips/partials/stop_card.html
- templates/trips/partials/stop_form.html
- templates/trips/partials/stop_confirm_delete.html
- templates/trips/partials/traveler_card.html
- templates/trips/partials/traveler_form.html
- templates/stories/partials/chapter_plan.html
- templates/stories/partials/chapter_quality.html
- templates/worlds/partials/character_card.html
- templates/worlds/partials/place_card.html

## HTMX Attributes
- Target: hx-target="#section-content"
- Swap: hx-swap="innerHTML" (default), outerHTML for replace
- Delete: hx-delete="..." hx-confirm="Wirklich loeschen?"
- Empty response for delete: view returns HttpResponse("")
```

#### Workspace Rule: `url-routing.md` (Glob: `apps/*/urls.py`, `config/urls.py`)

```markdown
# URL Routing Conventions (travel-beat — verified)

## Root URL Config
- File: config/urls.py
- ROOT_URLCONF = "config.urls"
- Health checks: /livez/ (liveness), /healthz/ (readiness), /health/ (compat)
- Admin: /admin/
- Auth: /accounts/ (django-allauth)

## App URL Registration Pattern
Every app URL file follows this pattern:
  from django.urls import path
  from . import views
  app_name = "<app_name>"
  urlpatterns = [...]

Root urls.py includes apps via:
  path("<prefix>/", include("apps.<app>.urls", namespace="<app>"))

## Namespace Map (from config/urls.py)
- "" -> trips (root, no prefix)
- "stories/" -> stories
- "locations/" -> locations
- "world/" -> worlds (NOTE: prefix is "world", namespace is "worlds")
- "profile/" -> accounts
- "ai/" -> ai_services

## reverse() Usage
- Always use namespace: reverse("trips:trip_detail", kwargs={"pk": pk})
- In templates: {% url "trips:trip_detail" pk=trip.pk %}
- NEVER use bare names: reverse("trip_detail") will FAIL

## URL Naming Convention
- List: <model>_list (e.g., trip_list)
- Detail: <model>_detail
- Create: <model>_create
- Edit: <model>_edit
- Delete: <model>_delete
- HTMX partials: <model>_add, <model>_edit (same name, different HTTP method)

## HTMX Partial URLs
- Nested under parent: trips/<int:pk>/stops/add/
- Standalone edit: stops/<int:pk>/edit/
- API endpoints: trips/api/segment-fields/
```

#### Workspace Rule: `testing.md` (Glob: `**/tests/**`, `**/test_*.py`)

```markdown
# Testing Conventions (travel-beat — verified)

## Framework
- pytest with pytest-django
- Config: pytest.ini at project root
- DJANGO_SETTINGS_MODULE = config.settings.test
- addopts: -v --tb=short
- testpaths: apps tests

## Test File Locations
- App tests: apps/<app>/tests/test_<module>.py
- Integration tests: tests/test_<feature>.py
- NO conftest.py exists yet — create if shared fixtures needed

## Test Naming
- Functions: test_should_<expected_behavior> (e.g., test_should_create_trip)
- Classes: Test<Feature> (e.g., TestStoryExport)

## Running Tests
- All: python -m pytest
- Single app: python -m pytest apps/stories/
- Single file: python -m pytest apps/stories/tests/test_services.py
- Pattern: python -m pytest -k "test_should_export"

## Test Patterns
- Use @pytest.mark.django_db for DB access
- Mock external services (LLM calls, HTTP)
- Factory Boy for test data (if installed)
- Max 5 assertions per test, max 30 lines per test function

## Existing Test Files (travel-beat)
- apps/stories/tests/test_services.py, test_export.py, test_handlers.py,
  test_integration.py, test_regeneration.py, test_review.py,
  test_chapter_planner.py, test_editing_service.py, test_storyline_schemas.py
- apps/trips/tests/test_csv_scene_stops.py, test_enrichment.py
- tests/test_chat_views.py, test_creative_services.py, test_csv_parser.py,
  test_llm_service.py, test_story_toolkit.py, test_toolkit.py, test_trip_agent.py
```

#### Workspace Rule: `docker-deployment.md` (Glob: `Dockerfile`, `docker-compose*.yml`, `.env*`)

```markdown
# Docker & Deployment Conventions (verified)

## Dockerfile
- Location varies per repo:
  travel-beat: docker/Dockerfile
  bfagent: Dockerfile (project root)
  weltenhub: Dockerfile (project root)
  risk-hub: docker/app/Dockerfile
  pptx-hub: docker/app/Dockerfile
- Target standard (per User Rules): docker/app/Dockerfile
- Base image: python:3.12-slim
- Non-root user: groupadd + useradd per app name
- HEALTHCHECK via python urllib (no curl): /livez/
- EXPOSE 8000

## Docker Compose (production)
- File: docker-compose.prod.yml at project root
- env_file: .env.prod (NEVER use ${VAR} interpolation in environment: section)
- Image: ghcr.io/achimdehnert/<app>:${IMAGE_TAG:-latest}
- Container naming: <app_snake>_web, <app_snake>_db, <app_snake>_redis
- Networks: app-specific + external bfagent_platform
- Resource limits: memory per service
- Logging: json-file driver, max-size 10-20m

## Services Pattern (travel-beat example)
- travel-beat-web: gunicorn on 0.0.0.0:8000 (4 workers, gthread)
- travel-beat-caddy: reverse proxy on 127.0.0.1:8089
- travel-beat-celery: celery -A config worker
- travel-beat-celery-beat: celery -A config beat
- travel-beat-db: postgres:15-alpine
- travel-beat-redis: redis:7-alpine (128mb, allkeys-lru)

## Deployment Flow (ADR-042)
1. git push origin main
2. bf deploy <app> (triggers workflow_dispatch)
3. GitHub Actions: docker build + push to GHCR
4. SSH to 88.198.191.108: docker compose pull + up -d --force-recreate
5. Health check: /livez/ returns 200

## CRITICAL: .env.prod
- Never commit .env.prod to git
- Contains: SECRET_KEY, DATABASE_URL, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS
- DJANGO_SETTINGS_MODULE=config.settings.production
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
   - Check HTMX: if request.headers.get("HX-Request"):
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

**Verified memories to set (travel-beat workspace):**

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
4. Verify remaining memories match current `config/settings/base.py`

---

## 4. Migration Plan

### Phase 1: Quick Wins (Week 1)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Create `platform-principles.md` global rule | `.windsurf/rules/platform-principles.md` |
| 1 | Create 5 workspace rules (django, templates, URLs, testing, docker) | `.windsurf/rules/*.md` |
| 2 | Set verified memories for travel-beat workspace | Curated memories |
| 2 | Create `/deploy-check` + `/adr-create` workflows | `.windsurf/workflows/*.md` |
| 3 | Create `/new-django-app` + `/htmx-view` + `/pr-review` workflows | 3 workflow files |
| 4 | Test all rules and workflows on travel-beat | Validation pass |
| 5 | Rollout rules to bfagent + weltenhub repos (adapt per-repo facts) | Adapted rules |

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

- **Correct paths and settings from session start** via Always-On rule
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

---

## 6. Success Criteria

### 6.1 Binary (pass/fail)

- [ ] `platform-principles.md` rule active in all workspaces
- [ ] Cascade generates correct `config.urls` (not `travel_beat.urls`) in new session
- [ ] Cascade uses `request.headers.get("HX-Request")` (not `request.htmx`)
- [ ] Cascade creates templates in `templates/<app>/` (not `apps/<app>/templates/`)
- [ ] `/deploy-check` workflow runs all steps without manual intervention
- [ ] `/new-django-app` scaffolds correct structure with `BigAutoField`
- [ ] `/pr-review` fetches and addresses all review comments
- [ ] `/adr-create` generates correctly numbered ADR from template
- [ ] `/htmx-view` creates view + template + partial + URL in one invocation

### 6.2 Qualitative

- [ ] All 7 repos have `.windsurf/rules/` with platform-principles
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
| 2026-02-17 | Achim Dehnert | v2.1: K-03 fix — all 5 rules and 5 workflows fully defined; K-04 idempotency guards; K-05 error handling |
