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

### 3.2 Measure 2: Windsurf Workflows

Workflows are markdown files in `.windsurf/workflows/` invoked via `/command`.

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

2. Run test suite:
   // turbo
   python -m pytest --tb=short -q
   If tests fail, STOP and report failures.

3. Run linting:
   // turbo
   ruff check .

4. Check for pending migrations:
   // turbo
   python manage.py showmigrations --list | grep "\[ \]"

5. Check deploy status:
   // turbo
   bf status

6. Print deployment readiness report with pass/fail per step.
```

#### Workflow: `/new-django-app`

```markdown
---
description: Scaffold a new Django app with Platform conventions
---
Inputs: App name (snake_case), brief description.

1. Create directory structure:
   mkdir -p apps/{app_name}/tests
   mkdir -p templates/{app_name}/partials

2. Create apps.py with default_auto_field = "django.db.models.BigAutoField"
   and name = "apps.{app_name}"

3. Create urls.py with app_name = "{app_name}" and empty urlpatterns

4. Register in config/settings/base.py LOCAL_APPS

5. Register in config/urls.py

6. Create initial migration:
   python manage.py makemigrations {app_name}

7. Verify:
   // turbo
   python manage.py check
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
| 1 | Create 3 workspace rules (django, templates, URLs) | `.windsurf/rules/*.md` |
| 2 | Set verified memories for travel-beat workspace | Curated memories |
| 2 | Create `/deploy-check` workflow | `.windsurf/workflows/deploy-check.md` |
| 3 | Create `/new-django-app` + `/htmx-view` workflows | 2 workflow files |
| 4 | Test all rules and workflows on travel-beat | Validation pass |
| 5 | Rollout rules to bfagent + weltenhub repos | Copied + adapted rules |

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
| `/pr-review` + `/adr-create` workflows | Workflow files |
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

---

## 6. Success Criteria

### 6.1 Binary (pass/fail)

- [ ] `platform-principles.md` rule active in all workspaces
- [ ] Cascade generates correct `config.urls` (not `travel_beat.urls`) in new session
- [ ] Cascade uses `request.headers.get("HX-Request")` (not `request.htmx`)
- [ ] Cascade creates templates in `templates/<app>/` (not `apps/<app>/templates/`)
- [ ] `/deploy-check` workflow runs all steps without manual intervention
- [ ] `/new-django-app` scaffolds correct structure with `BigAutoField`

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
