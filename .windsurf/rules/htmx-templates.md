---
trigger: always_on
---

# HTMX Templates — Rules

> Glob-Activated: `**/templates/**`, `**/*.html`
> ADR-048 — HTMX Playbook
> **Detection method is repo-specific — ALWAYS check `project-facts.md` first!**

## ALWAYS include all three (no exceptions)

```html
<!-- CORRECT -->
<button hx-post="/trips/"
        hx-target="#result"
        hx-swap="innerHTML"
        hx-indicator="#spinner"
        data-testid="create-trip-btn">
    Create
</button>

<!-- BANNED — AP-005/AP-006 CRITICAL: missing hx-indicator or data-testid -->
```

## Partials (HTMX responses)

```html
<!-- CORRECT partial — bare fragment only -->
<div id="result">
  <p>Trip created!</p>
</div>

<!-- BANNED in partials: -->
<!-- {% extends "base.html" %}   <- full page in partial -->
<!-- <html>...</html>            <- full page in partial -->
```

## HTMX Detection (repo-specific!)

```python
# If project-facts.md says django_htmx installed:
if request.htmx:  # CORRECT

# If project-facts.md says raw-headers:
if request.headers.get("HX-Request") == "true":  # CORRECT

# NEVER mix these up — check project-facts.md!
```

## BANNED Patterns

- `hx-boost` on forms
- `inline style=` mixed with `hx-*` attributes
- `onclick=` mixed with `hx-*`
- Missing `data-testid` on interactive elements
- `{% csrf_token %}` missing in `hx-post` forms
- Full `<html>` document in HTMX partial responses
