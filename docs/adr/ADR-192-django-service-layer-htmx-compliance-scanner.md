---
status: proposed
date: 2026-05-09
decision-makers:
  - Achim Dehnert
depends-on:
  - ADR-191 (platform-context MCP Code Compliance)
  - ADR-009 (Service Layer Architecture)
  - ADR-048 (HTMX Playbook)
  - ADR-043 (Database-First Conventions)
  - ADR-057 (Four-Level Test Strategy)
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
  - testing
implementation_status: none
staleness_months: 6
last_reviewed: 2026-05-09
drift_check_paths:
  - "*/views.py"
  - "*/services.py"
  - "*/templates/**/*.html"
---

# ADR-192: Django Service-Layer and HTMX Template Compliance Scanner

| Metadaten | |
|-----------|---|
| **Status** | Proposed |
| **Datum** | 2026-05-09 |
| **Autor** | Achim Dehnert |
| **Depends On** | ADR-191, ADR-009, ADR-048, ADR-043, ADR-057 |
| **Consumers** | dev-hub, travel-beat, bfagent, risk-hub, weltenhub, wedding-hub, coach-hub |

---

## Context

ADR-009 mandates the three-tier pattern: `views.py` → `services.py` → `models.py`. ADR-048 mandates HTMX attributes: every element with `hx-*` must include `hx-target`, `hx-swap`, `hx-indicator`, and `data-testid`. These are the two most frequently violated platform rules — found in PR reviews across all 7 consumer repos.

**Current enforcement gap:**

| Rule | Enforcement | Gap |
|------|------------|-----|
| No ORM in views (ADR-009) | `platform-context` string-match on `.objects.`, `.filter(` | Misses: `queryset = Trip.objects` (no method call on same line), context manager patterns |
| Service delegation (ADR-009) | Windsurf rules (agent instruction only) | **No automated check at all** — reviewer must verify manually |
| HTMX triple (ADR-048) | Windsurf rules | **No automated check** — templates never scanned systematically |
| `data-testid` (ADR-048) | None | **Not checked anywhere** |

A structural scanner using Python's `ast` module for views and `html.parser` for templates would close these gaps with zero false negatives for the common patterns.

## Decision

We implement two scanner modules as part of ADR-191's `platform-context` MCP extension:

### 1. Service-Layer Scanner (`check_service_layer`)

```
Input:  repo name + optional app name
Output: list of violations with file, line, function, violation type
```

**Analysis approach (Python `ast`):**

1. Parse `views.py` → extract all function definitions (FBV) and class methods (CBV)
2. For each view function, walk the AST to find:
   - **Direct ORM calls**: `Name.Attribute` where Attribute ∈ {`objects`, `filter`, `exclude`, `get`, `create`, `update`, `delete`, `save`, `bulk_create`}
   - **Missing service import**: Check if the view module imports from a `services` module
   - **No service call**: View function body contains no call to a function from `services.py`
3. Parse `services.py` → extract exported function names for cross-reference

**Violation types:**

| ID | Severity | Description |
|----|----------|-------------|
| `SL-001` | critical | Direct ORM call in view function |
| `SL-002` | error | View function does not call any service function |
| `SL-003` | warning | View function imports model directly (potential bypass) |
| `SL-004` | info | `services.py` missing for app with views |

### 2. HTMX Template Scanner (`check_templates`)

```
Input:  repo name + optional template path
Output: list of violations with file, line, element, violation type
```

**Analysis approach (`html.parser`):**

1. Recursively find all `.html` files in `templates/`
2. Parse each file, find elements with any `hx-*` attribute
3. For each HTMX element, verify:
   - `hx-target` present
   - `hx-swap` present
   - `hx-indicator` present
   - `data-testid` present
4. Additionally check for banned patterns:
   - `hx-boost` on any element
   - `onclick=` on elements with `hx-*`
   - `style=` inline on elements with `hx-*`

**Violation types:**

| ID | Severity | Description |
|----|----------|-------------|
| `HX-001` | error | HTMX element missing `hx-target` |
| `HX-002` | error | HTMX element missing `hx-swap` |
| `HX-003` | warning | HTMX element missing `hx-indicator` |
| `HX-004` | warning | HTMX element missing `data-testid` |
| `HX-005` | critical | `hx-boost` used (banned by ADR-048) |
| `HX-006` | error | `onclick=` mixed with `hx-*` |
| `HX-007` | info | `hx-post` form without `{% csrf_token %}` in same parent |
| `HX-008` | error | Partial template contains `{% extends %}` (should be fragment) |

## Consequences

### Positive
- Catches the #1 and #2 most common PR review findings automatically
- Zero-dependency implementation (stdlib `ast` + `html.parser`)
- Violation IDs (`SL-001`, `HX-001`) create a shared vocabulary for team communication
- Directly usable in `/pr-review` workflow: "2 SL-001 violations found → [BLOCK]"
- Template scanner works on any HTML — not Django-template specific

### Negative
- AST analysis cannot follow dynamic dispatch (e.g., `getattr(model, 'objects')`)
- `html.parser` cannot evaluate Django template tags ({% if %} blocks may hide HTMX elements)
- CBV analysis is significantly more complex than FBV — Phase 1 may produce false positives for mixins
- Template inheritance (`{% include %}`, `{% block %}`) makes partial analysis incomplete

## Alternatives Considered

1. **pylint/flake8 custom plugin** — Tied to linter ecosystem, harder to integrate with MCP. AST approach is more flexible.
2. **Semgrep rules** — Powerful but adds a heavy dependency. Custom `ast` analysis is simpler for our specific patterns.
3. **Manual checklists in PR template** — Current approach. Does not scale, easily overlooked.
4. **Django system check framework** — Runs at startup, not at PR review time. Cannot check templates.

## Implementation Priorities

| Priority | Check | Expected findings across 19 repos |
|----------|-------|-----------------------------------|
| P0 | `SL-001` Direct ORM in views | ~50-100 violations |
| P0 | `HX-001/002` Missing hx-target/hx-swap | ~20-40 violations |
| P1 | `SL-002` Missing service delegation | ~30-60 violations |
| P1 | `HX-003/004` Missing indicator/testid | ~100+ violations |
| P2 | `HX-005` hx-boost usage | ~5-10 violations |
| P2 | `SL-003` Direct model import in views | ~20-30 violations |
