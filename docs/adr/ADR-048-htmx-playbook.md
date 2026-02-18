# ADR-048: HTMX Playbook -- Canonical Patterns for Django-HTMX

| Status | Proposed |
| ------ | -------- |
| Date | 2026-02-18 |
| Author | Achim Dehnert |
| Scope | Platform-wide (all HTMX-enabled Django apps) |
| Related | ADR-040 (Frontend Completeness Gate), ADR-041 (Component Pattern) |

## Context

Six of our ten repositories use HTMX for dynamic interactions. Development
suffers from **recurring errors** due to missing canonical patterns:

| Error Pattern | Frequency | Root Cause |
| ------------- | --------- | ---------- |
| Missing `hx-indicator` for loading states | High | No default behavior defined |
| Inconsistent `hx-target` / `hx-swap` combos | High | No enforced pattern catalog |
| Broken HTMX events (bubbling, `htmx:afterSwap`) | Medium | Complex event chains |
| No error handling in HTMX responses | High | No standard error pattern |
| `hx-boost` on forms causing double-submit | Medium | Anti-pattern not banned |
| Missing `data-testid` on interactive elements | High | AI tools skip test IDs |

**Cost of status quo**: ~30-40% dev time spent on HTMX debugging and rework.

### HTMX Stack Differences Across Repos

| Repo | HTMX | Detection Method | Notes |
| ---- | ---- | ---------------- | ----- |
| weltenhub | Yes | `request.htmx` (django_htmx) | Full middleware support |
| travel-beat | Yes | `request.headers.get("HX-Request")` | No django_htmx package |
| risk-hub | Yes | `request.headers.get("HX-Request")` | Moderate usage |
| pptx-hub | Yes | `request.headers.get("HX-Request")` | Light usage |
| wedding-hub | Yes | `request.headers.get("HX-Request")` | Light usage |
| trading-hub | Yes | `request.headers.get("HX-Request")` | Light usage |
| bfagent | **No** | N/A | No HTMX at all |

This ADR defines **six canonical patterns** (HP-001..006), **seven banned
anti-patterns** (AP-001..007), and a **portable error middleware** that works
regardless of whether `django_htmx` is installed.

## Decision

### 1. HTMX Request Detection (Portable)

Because only weltenhub uses `django_htmx`, all shared code MUST use the
raw header check for portability:

```python
def is_htmx_request(request) -> bool:
    """Portable HTMX detection. Works with or without django_htmx."""
    return request.headers.get("HX-Request") == "true"
```

Apps that have `django_htmx` installed MAY use `request.htmx` in
app-specific code, but shared middleware and mixins MUST NOT depend on it.

### 2. Canonical Patterns (HP-001 through HP-006)

#### HP-001: Partial Response (Basis)

Every HTMX view returns a **partial template** for HTMX requests and a
**full template** for normal requests:

```python
# Pattern: HTMX-aware view
def trip_list(request):
    trips = Trip.objects.filter(user=request.user)
    context = {"trips": trips}
    if is_htmx_request(request):
        return render(request, "trips/partials/_trip_list.html", context)
    return render(request, "trips/trip_list.html", context)
```

```html
{# trips/partials/_trip_list.html #}
<div id="trip-list" data-testid="trip-list">
  {% for trip in trips %}
    <div data-testid="trip-{{ trip.id }}">{{ trip.title }}</div>
  {% empty %}
    {% include "core/partials/_empty_state.html" with message="No trips yet." %}
  {% endfor %}
</div>
```

**Mandatory attributes on the trigger element:**

```html
<div hx-get="{% url 'trips:list' %}"
     hx-target="#trip-list"
     hx-swap="outerHTML"
     hx-indicator="#trip-list-spinner">
```

| Attribute | Required | Why |
| --------- | -------- | --- |
| `hx-get` or `hx-post` | Yes | The request |
| `hx-target` | Yes | Never rely on implicit `this` |
| `hx-swap` | Yes | Explicit swap strategy |
| `hx-indicator` | Yes | Loading feedback for users |

#### HP-002: CRUD Inline (Delete, Inline-Edit)

```html
{# Delete with confirmation #}
<button hx-delete="{% url 'trips:delete' trip.id %}"
        hx-confirm="Delete '{{ trip.title }}'?"
        hx-target="closest .trip-row"
        hx-swap="outerHTML swap:500ms"
        hx-indicator="#delete-spinner-{{ trip.id }}"
        data-testid="trip-delete-{{ trip.id }}">
  Delete
</button>
```

**Rules:**

- Delete MUST use `hx-delete` (not `hx-post`)
- Delete MUST have `hx-confirm`
- Target MUST use `closest` to remove the correct DOM element
- Swap MUST include transition delay (`swap:500ms`) for visual feedback

#### HP-003: Live Search

```html
<input type="search"
       name="q"
       hx-get="{% url 'trips:search' %}"
       hx-trigger="keyup changed delay:300ms, search"
       hx-target="#search-results"
       hx-swap="innerHTML"
       hx-indicator="#search-spinner"
       data-testid="trip-search-input"
       placeholder="Search trips...">

<div id="search-spinner" class="htmx-indicator">
  {% include "core/partials/_loading_spinner.html" %}
</div>

<div id="search-results" data-testid="search-results">
  {# Results swapped in here #}
</div>
```

**Rules:**

- `delay:300ms` to debounce keystrokes
- `search` event for clearing the input
- Always show a loading indicator

#### HP-004: Infinite Scroll

```html
{# Last item in the list triggers next page load #}
{% if page_obj.has_next %}
  <div hx-get="?page={{ page_obj.next_page_number }}"
       hx-trigger="revealed"
       hx-swap="afterend"
       hx-indicator="#scroll-spinner"
       data-testid="infinite-scroll-trigger">
    <span id="scroll-spinner" class="htmx-indicator">
      Loading more...
    </span>
  </div>
{% endif %}
```

**Rules:**

- Use `revealed` trigger (not `intersect` -- simpler, sufficient)
- Swap `afterend` (append after the trigger element)
- The trigger element is replaced by the next page's content
- View must return the next page's items + a new trigger element

#### HP-005: Error Response (Middleware)

HTMX errors must NOT break the DOM. The middleware intercepts 4xx/5xx
responses for HTMX requests and converts them to toast notifications:

```python
import json

class HtmxErrorMiddleware:
    """Convert 4xx/5xx into HTMX-safe responses with toast notifications.

    Works without django_htmx -- uses raw header detection.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not request.headers.get("HX-Request") == "true":
            return response

        if response.status_code == 422:
            # Validation error: let the form partial swap normally (HP-006)
            return response

        if response.status_code >= 400:
            # Prevent DOM corruption: don't swap anything
            response["HX-Reswap"] = "none"
            response["HX-Trigger"] = json.dumps({
                "showToast": {
                    "level": "error" if response.status_code >= 500 else "warning",
                    "message": self._error_message(response.status_code),
                }
            })

        return response

    @staticmethod
    def _error_message(status_code: int) -> str:
        messages = {
            403: "Permission denied.",
            404: "Resource not found.",
            429: "Too many requests. Please wait.",
            500: "Internal server error. Please try again.",
        }
        return messages.get(status_code, "An error occurred.")
```

**Installation** (in each app's `config/settings/base.py`):

```python
MIDDLEWARE = [
    # ... after SecurityMiddleware, SessionMiddleware, etc.
    "apps.core.middleware.HtmxErrorMiddleware",
    # ...
]
```

**Client-side toast listener** (in `base.html`):

```html
<script>
document.addEventListener("showToast", function(event) {
    const {level, message} = event.detail;
    // Minimal toast implementation (or use any toast library)
    const toast = document.createElement("div");
    toast.className = `toast toast-${level}`;
    toast.textContent = message;
    document.getElementById("toast-container").appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
});
</script>
<div id="toast-container" class="fixed top-4 right-4 z-50 space-y-2"></div>
```

#### HP-006: Form Validation

```python
def trip_create(request):
    form = TripForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            trip = form.save(commit=False)
            trip.user = request.user
            trip.save()
            if is_htmx_request(request):
                response = HttpResponse(status=204)
                response["HX-Trigger"] = "tripCreated"
                response["HX-Redirect"] = reverse("trips:detail", args=[trip.id])
                return response
            return redirect("trips:detail", pk=trip.id)
        else:
            if is_htmx_request(request):
                # 422: re-render form with errors, HTMX swaps it in
                return render(
                    request,
                    "trips/partials/_trip_form.html",
                    {"form": form},
                    status=422,
                )
    return render(request, "trips/trip_create.html", {"form": form})
```

**Rules:**

- Valid form: return `204 No Content` + `HX-Trigger` event + `HX-Redirect`
- Invalid form: return `422` + re-rendered form partial (HP-005 skips 422)
- Never return `200` with error content (HTMX cannot distinguish)

### 3. Banned Anti-Patterns (AP-001 through AP-007)

| ID | Anti-Pattern | Why Banned | Enforcement |
| -- | ------------ | ---------- | ----------- |
| AP-001 | `hx-swap="innerHTML"` without `hx-target` | Swaps into trigger element, breaks layout | Pre-commit grep |
| AP-002 | `hx-boost` on `<form>` elements | Causes double-submit, breaks CSRF | Pre-commit grep |
| AP-003 | `onclick=` combined with `hx-*` attributes | Dual event handling, unpredictable | Pre-commit grep |
| AP-004 | Inline `style=` on any element | Bypasses design tokens (see ADR-049) | Pre-commit grep |
| AP-005 | `hx-get`/`hx-post` without `hx-indicator` | No loading feedback, user clicks again | CI manifest check |
| AP-006 | Interactive element without `data-testid` | Untestable by Playwright (ADR-040) | CI manifest check |
| AP-007 | Hardcoded hex colors in templates | Bypasses design token system | CI token check |

### 4. Pre-Commit Enforcement

```yaml
# .pre-commit-config.yaml (addition)
repos:
  - repo: local
    hooks:
      - id: htmx-anti-patterns
        name: "HTMX Anti-Pattern Check (AP-001..004)"
        entry: python -m tools.check_htmx_patterns
        language: python
        files: '\.html$'
        pass_filenames: true
```

```python
# tools/check_htmx_patterns.py
"""Pre-commit hook for HTMX anti-pattern detection (AP-001..004)."""

import re
import sys
from pathlib import Path

PATTERNS: dict[str, tuple[str, str]] = {
    "AP-001": (
        r'hx-swap\s*=\s*"innerHTML"(?![^>]*hx-target)',
        "hx-swap='innerHTML' without hx-target",
    ),
    "AP-002": (
        r'<form[^>]*hx-boost\s*=\s*"true"',
        "hx-boost on <form> element",
    ),
    "AP-003": (
        r'onclick\s*=\s*"[^"]*"[^>]*hx-|hx-[^>]*onclick\s*=',
        "onclick combined with HTMX attribute",
    ),
    "AP-004": (
        r'style\s*=\s*"[^"]*(?:color|background|margin|padding)',
        "Inline style with layout/color property",
    ),
}


def check_file(path: Path) -> list[str]:
    """Check a single file for anti-patterns."""
    content = path.read_text(encoding="utf-8")
    errors = []
    for ap_id, (pattern, message) in PATTERNS.items():
        if re.search(pattern, content, re.DOTALL | re.IGNORECASE):
            errors.append(f"  {path}: {ap_id}: {message}")
    return errors


def main() -> int:
    files = [Path(f) for f in sys.argv[1:] if f.endswith(".html")]
    all_errors = []
    for f in files:
        if f.exists():
            all_errors.extend(check_file(f))
    for error in all_errors:
        print(error)
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
```

## Consequences

### Positive

- **Six canonical patterns** eliminate guesswork for HTMX interactions
- **Portable middleware** works across all apps (no django_htmx dependency)
- **Pre-commit enforcement** catches anti-patterns before they reach CI
- **Error handling** prevents DOM corruption on server errors
- **Form validation** pattern (422 + re-render) is a proven Django-HTMX idiom
- **AI-friendly**: `.windsurfrules` can reference HP-001..006 by ID

### Negative

- **Learning curve** for developers unfamiliar with the pattern catalog
- **Pre-commit overhead** adds ~2s to commits touching `.html` files
- **Middleware ordering** must be correct (after auth, before response)

### Mitigations

- Pattern catalog is short (6 patterns) and each has a copy-paste example
- Pre-commit is fast (regex-only, no AST parsing)
- Middleware installation is documented per-app

## Alternatives Considered

1. **No standard patterns** -- Status quo, leads to recurring errors
2. **django-htmx as mandatory** -- Forces package on all apps, overkill for light usage
3. **Client-side error handling only** -- JS `htmx:responseError` event is fragile
4. **Full UI framework (Stimulus, Alpine)** -- Additional JS dependency, not needed
