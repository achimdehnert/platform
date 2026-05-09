---
status: proposed
date: 2026-05-09
decision-makers:
  - Achim Dehnert
depends-on:
  - ADR-190 (iil-adrfw Tooling Framework)
  - ADR-009 (Service Layer Architecture)
  - ADR-048 (HTMX Playbook)
  - ADR-056 (Deployment Pre-Flight Validation)
  - ADR-010 (MCP Tool Governance)
repo: platform
consumers:
  - dev-hub
  - travel-beat
  - bfagent
  - risk-hub
  - weltenhub
  - wedding-hub
  - coach-hub
domains:
  - django/views
  - django/models
  - htmx
  - deployment
  - mcp
implementation_status: none
staleness_months: 6
last_reviewed: 2026-05-09
drift_check_paths:
  - platform/orchestrator_mcp/
  - platform/shared_contracts/
---

# ADR-191: Extend platform-context MCP with AST-Based Code Compliance Tools

| Metadaten | |
|-----------|---|
| **Status** | Proposed |
| **Datum** | 2026-05-09 |
| **Autor** | Achim Dehnert |
| **Depends On** | ADR-190, ADR-009, ADR-048, ADR-056, ADR-010 |
| **Consumers** | dev-hub, travel-beat, bfagent, risk-hub, weltenhub, wedding-hub, coach-hub |

---

## Context

The IIL Platform enforces architectural standards through three mechanisms:

1. **Windsurf Rules** (`.windsurf/rules/`) — Agent instructions loaded into Cascade sessions. Effective but only enforced during AI-assisted coding, not in CI or manual edits.
2. **platform-context MCP** (4 tools) — `check_violations` performs string-pattern matching against banned patterns like `Model.objects.` in views.py. Cannot detect structural violations.
3. **iil-reflex** (CLI) — Regex-based scanner over 19 repos. Catches file-level issues (missing HEALTHCHECK, env interpolation) but cannot perform AST analysis.

None of these tools can answer structural questions such as:
- "Does every view function in `apps/trips/views.py` delegate to a service function?"
- "Do all HTMX elements in `templates/` have `hx-target` + `hx-swap` + `hx-indicator` + `data-testid`?"
- "Does `docker-compose.prod.yml` use `env_file` instead of `environment:` with `${VAR}` interpolation?"

These violations are currently caught only during manual PR reviews — or not at all. With iil-adrfw (ADR-190) successfully demonstrating the MCP-first governance approach, the same pattern should be applied to code compliance.

## Decision

We extend the existing `platform-context` MCP server with 4 new AST-based compliance tools. This leverages the existing MCP infrastructure, repo-facts knowledge graph, and workflow integration. If the tools grow beyond ~1500 LOC or require a separate release cycle, they will be extracted into a standalone `iil-codeguard` PyPI package (same pattern as iil-adrfw extraction from platform).

### New MCP Tools

| Tool | Input | Output | Checks |
|------|-------|--------|--------|
| `check_service_layer` | `repo`, `app` | Violations list | Every view function must call a `services.py` function; no ORM in views |
| `check_templates` | `repo`, `path` | Violations list | HTMX: hx-target + hx-swap + hx-indicator + data-testid; no hx-boost; no inline onclick |
| `check_compose` | `repo` | Violations list | env_file not environment; HEALTHCHECK present; memory limits; image tag format |
| `audit_repo` | `repo` | Aggregated report | All checks combined + severity scoring + ADR references |

### Analysis Methods

| Check | Method | Library |
|-------|--------|---------|
| Service-layer | Python `ast` module — parse views.py, extract function calls, match against services.py exports | stdlib `ast` |
| HTMX templates | `html.parser` — find elements with `hx-*` attributes, verify required set | stdlib `html.parser` |
| Compose | `pyyaml` — parse docker-compose.prod.yml, check structure | `pyyaml` |
| Dockerfile | Line-by-line — check for HEALTHCHECK, USER, multi-stage FROM | regex |

## Consequences

### Positive
- Catches structural violations that string-matching misses (service-layer completeness, HTMX attribute sets)
- Integrates into existing `session-start` and `pr-review` workflows without new MCP server
- Uses only stdlib (`ast`, `html.parser`) + `pyyaml` — no heavy dependencies
- Immediate feedback in Cascade sessions via MCP
- Repo-specific behavior driven by existing `project-facts.md` (HTMX detection method, multi-tenancy)

### Negative
- `platform-context` grows from 4 to 8 tools — risk of "god server"
- AST analysis for Django is inherently limited (dynamic imports, metaclasses, decorator magic)
- False positives possible for complex view patterns (class-based views, mixins)
- No CI integration initially (MCP-only) — CI would require separate CLI entry point

## Alternatives Considered

1. **New `iil-codeguard` package from scratch** — Higher modularity but 8-12 days vs 4-6 days. Deferred as extraction target if complexity grows.
2. **Extend iil-reflex with AST checks** — REFLEX is regex-based; adding AST would require architectural rework. Better to keep REFLEX for file-level checks.
3. **Ruff custom rules** — Ruff is fast but its plugin system doesn't support Django-specific structural analysis (service-layer pattern, template scanning).
4. **Do nothing, rely on PR reviews** — Current state. Error-prone, reviewer-dependent, not scalable across 19 repos.

## Implementation Plan

| Phase | Scope | Aufwand |
|-------|-------|---------|
| Phase 1 | `check_compose` + `check_templates` (YAML/HTML parsing, simpler) | 2 Tage |
| Phase 2 | `check_service_layer` (Python AST) | 2 Tage |
| Phase 3 | `audit_repo` (aggregation) + Workflow-Integration | 1 Tag |
| Phase 4 | Extraction to `iil-codeguard` if >1500 LOC | Bei Bedarf |

## Open Questions

- **OQ-1**: Should class-based views (CBV) be supported in Phase 1, or only function-based views (FBV)?
- **OQ-2**: Should the template scanner also check for `{% csrf_token %}` in `hx-post` forms?
- **OQ-3**: What severity should missing `data-testid` have — warning or error?
