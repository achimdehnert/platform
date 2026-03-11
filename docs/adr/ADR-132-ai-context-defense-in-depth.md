---
status: "accepted"
date: 2026-02-27
amended: 2026-03-11
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-043-ai-assisted-development.md", "ADR-048-htmx-playbook.md", "ADR-072-multi-tenancy-schema-isolation.md", "ADR-090-cicd-pipeline-python-postgres.md"]
implementation_status: implemented
implementation_evidence:
  - "Phase 0 ✅: generate_project_facts.py committed + --all flag"
  - "Phase 1 ✅: windsurf-rules/ (9 Dateien) deployed to 18 repos via CI"
  - "Phase 2 ✅: platform_context_mcp live (4 tools, 10 rules, 14 repos, graph expanded 2026-03-11)"
  - "Windsurf mcp_config.json registered, active in every session"
---

# ADR-132: AI Context Defense-in-Depth

> **Amended 2026-03-11**: Review-Bereinigung — Zahlen korrigiert (14→Repos Graph, 18→Deploy,
> 9→Rule-Dateien, 10→Rules), MADR 4.0 Frontmatter, Layer 2 Tabelle vervollständigt,
> Knowledge Graph um 6 Repos erweitert (billing-hub, dev-hub, 137-hub, wedding-hub, writing-hub, research-hub).
>
> *Umnummeriert von ADR-094 (Nummernkonflikt mit ADR-094-django-migration-conflict-resolution).*
> *Erweitert ADR-043 (AI-Assisted Development) um 4-Layer Context-Strategie.*

---

## Context

Die IIL-Plattform umfasst 18+ Django-basierte Hub-Projekte. AI coding agents (Cascade/Windsurf)
lose architectural context between sessions, leading to:

| Problem | Frequency | Impact |
|---|---|---|
| Wrong imports/settings paths | Every new session | Blocks development immediately |
| Business logic in views (Service Layer violations) | ~3×/session | 15–30 min refactoring per violation |
| HTMX anti-patterns | ~2×/session | DOM breakage, untestable code |
| Wrong DB conventions (UUID, JSONField) | ~1×/session | Migration rollback, schema inconsistency |
| Wrong HTMX detection per repo | Every new session | `request.htmx` in travel-beat → RuntimeError |
| Context re-explanations | ~5–8×/day | ~45 min/day productivity loss |

## Decision

Implement a **4-layer defense-in-depth** strategy for persistent AI context:

```
Layer 0: project-facts.md     — Episodic Memory (repo-specific, auto-generated)
Layer 1: platform-principles  — Always-On Rules (mandatory for every session)
Layer 2: Glob-Activated Rules — File-type context (loaded on-demand by Windsurf)
Layer 3: platform_context_mcp — Knowledge Graph MCP (structural traversal)
```

## Architecture

### Layer 0 — project-facts.md (Episodic Memory)

Auto-generated per repo via `platform/scripts/generate_project_facts.py`:
- Django settings introspection via subprocess (`DJANGO_SETTINGS_MODULE`)
- Detects: HTMX method, app prefixes, container/port, multi-tenancy, AUTH_USER_MODEL
- Output: `.windsurf/rules/project-facts.md` in each repo

**CI trigger:** `update-project-facts.yml` — fires on settings/config changes + `workflow_dispatch`

### Layer 1 — Always-On Windsurf Rules

`platform/windsurf-rules/platform-principles.md` — loaded for every Windsurf session:
- Mandatory architecture rules (service layer, naming, HTMX)
- Settings module per repo (meist `config.settings.base`, Ausnahmen via project-facts.md)
- Multi-tenancy rules (tenant_id = UUIDField)
- Infrastructure principles (Docker, CI/CD)

### Layer 2 — Glob-Activated Rules

Loaded only when matching files are opened (9 Dateien):

| File | Glob Pattern |
|---|---|
| `django-models-views.md` | `*/models.py`, `*/views.py` |
| `htmx-templates.md` | `**/templates/**`, `**/*.html` |
| `testing.md` | `**/tests/**`, `**/test_*.py` |
| `docker-deployment.md` | `Dockerfile`, `docker-compose*.yml`, `.github/**` |
| `aifw-integration.md` | `**/services/**`, `**/llm*` |
| `authoringfw-integration.md` | `**/authoring*`, `**/planning*` |
| `promptfw-integration.md` | `**/prompt*` |
| `iil-packages.md` | `**/requirements*.txt`, `**/pyproject.toml` |
| `platform-principles.md` | Always-On (kein Glob) |

### Layer 3 — platform_context_mcp (Knowledge Graph)

MCP server at `mcp-hub/platform_context_mcp/` with 4 tools:

| Tool | Purpose |
|---|---|
| `get_context_for_task(repo, file_type)` | Returns applicable rules with severity |
| `check_violations(code_snippet, file_type)` | Detects banned patterns |
| `get_project_facts(repo)` | Returns repo metadata (HTMX, settings, container) |
| `get_banned_patterns(context)` | Returns all banned patterns for a file type |

Graph: 10 rules, 14 repos, validated 4/4 (syntactic, referential, orphan, coverage).

## CI/CD Automation

| Workflow | Repo | Trigger | Action |
|---|---|---|---|
| `update-project-facts.yml` | 14 app repos (Graph) | push (settings/config) + self | Regenerate `project-facts.md` |
| `receive-windsurf-rules.yml` | 18 repos (all Hubs) | `repository_dispatch` + self | Sync rules from platform |
| `deploy-windsurf-rules.yml` | platform | push to `windsurf-rules/` | Dispatch to 18 repos |

**Secret:** `PLATFORM_DEPLOY_TOKEN` (Fine-grained PAT, Contents+Actions Write) in platform repo.

## Implementation

### Phase 0 ✅ — generate_project_facts.py
- Committed: `platform/scripts/generate_project_facts.py`
- Supports: `--all` flag, `--settings` override, `src/` prefix detection (risk-hub), `.env.prod` parsing

### Phase 1 ✅ — Windsurf Rules
- Committed: `platform/windsurf-rules/` (9 files)
- Deployed to 18 repos via `deploy-windsurf-rules.yml`

### Phase 2 ✅ — platform_context_mcp
- Committed: `mcp-hub/platform_context_mcp/`
- `server.py`, `traversal.py`, `graph/` (rules/repos/adrs/file_types/edges JSON)
- `validate_graph()` PASSED 4/4
- Registered in Windsurf `mcp_config.json` (WSL wrapper pattern)

## Consequences

**Positive:**
- Repo-specific context always available from session start
- Rule violations caught before code is written (not after)
- Zero manual context re-explanation overhead
- Rules update automatically across 18 repos when platform changes

**Negative:**
- One-time setup: `PLATFORM_DEPLOY_TOKEN` PAT required
- `platform_context_mcp` requires WSL + bfagent venv on local machine
- `generate_project_facts.py` degrades gracefully if `django.setup()` fails in CI

## Verification

Live demo on dev-server (2026-02-27):

```python
# travel-beat / views.py → correct rules
get_context_for_task("travel-beat", "views.py")
# → [CRITICAL] SL-001: No ORM calls in views.py
# → [HIGH] HX-001: htmx_detection = request.headers.get('HX-Request') == 'true'
# → [HIGH] NM-001: ROOT_URLCONF must be config.urls

# bfagent / templates → no HTMX rules (correct)
get_context_for_task("bfagent", "templates")
# → (empty — bfagent has no HTMX)

# Violation detection
check_violations("books = Book.objects.filter(active=True)", "views.py")
# → ['.filter(']  ← CAUGHT
```

## References

- ADR-043: AI-Assisted Development — Context & Workflow Optimization (erweitert durch dieses ADR)
- ADR-048: HTMX Playbook
- ADR-072: Multi-Tenancy Schema Isolation
- ADR-090: CI/CD Pipeline Python + PostgreSQL
- `platform/windsurf-rules/` — 9 rule source files
- `mcp-hub/platform_context_mcp/` — MCP server implementation (4 tools, 10 rules, 14 repos)
