---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-049: Design Token System -- CSS Custom Properties + Tailwind Bridge

| Status | Proposed |
| ------ | -------- |
| Date | 2026-02-18 |
| Author | Achim Dehnert |
| Scope | Platform-wide (all Django apps with frontend) |
| Related | ADR-040 (Frontend Completeness Gate), ADR-041 (Component Pattern), ADR-048 (HTMX Playbook) |

## Context

CSS across our Django apps suffers from **inconsistent styling**:

| Problem | Impact |
| ------- | ------ |
| Hardcoded hex colors (`#2563eb`, `#ef4444`) scattered across templates | Impossible to change brand colors globally |
| Direct Tailwind color classes (`bg-blue-500`, `text-red-600`) | No semantic meaning, no runtime theming |
| Each app has slightly different spacing, shadows, radii | Inconsistent look and feel across the platform |
| No dark mode path | Cannot offer dark mode without rewriting all templates |
| App-specific accent colors require per-template overrides | Fragile, error-prone |

**Cost**: ~2h/week fixing visual inconsistencies, plus inability to offer
per-app branding or dark mode.

### Current State

All apps use Tailwind CSS for utility classes. There is no shared design
token system. Each app's `tailwind.config.js` is independent with no shared
color palette or spacing scale.

## Decision

### 1. Architecture: Two-Layer Token System

> **Naming**: The prefix `pui` stands for **Platform UI**. It avoids
> conflicts with third-party CSS variables (e.g., `--tw-*` from Tailwind,
> `--bs-*` from Bootstrap).

```text
┌─────────────────────────────────────────────────────┐
│               TOKEN ARCHITECTURE                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Layer 1: CSS Custom Properties (Runtime)           │
│  ──────────────────────────────────────              │
│  :root { --pui-primary: #2563eb; }                  │
│  [data-app="travel-beat"] { --pui-primary: ... }    │
│  [data-theme="dark"] { --pui-surface: ... }         │
│                                                     │
│  Layer 2: Tailwind Config (Build-Time)              │
│  ──────────────────────────────────────              │
│  colors: { primary: 'var(--pui-primary)' }          │
│  → Tailwind classes resolve to CSS variables        │
│  → bg-primary compiles to background: var(...)      │
│                                                     │
│  Result: Same Tailwind code, different runtime look │
└─────────────────────────────────────────────────────┘
```

Developers write standard Tailwind classes (`bg-primary`, `text-danger`,
`border-border`). At runtime, CSS Custom Properties resolve the actual
color values. This enables per-app branding and dark mode without changing
any template code.

### 2. Token Definitions

#### Primitive Tokens (raw values, never used directly in templates)

```css
/* static/platform/css/pui-tokens.css */

:root {
  /* === Primitive Tokens (internal only) === */
  --pui-blue-500: #2563eb;
  --pui-blue-600: #1d4ed8;
  --pui-gray-50:  #f9fafb;
  --pui-gray-100: #f3f4f6;
  --pui-gray-200: #e5e7eb;
  --pui-gray-500: #6b7280;
  --pui-gray-900: #111827;
  --pui-green-500: #22c55e;
  --pui-red-500:   #ef4444;
  --pui-amber-500: #f59e0b;
}
```

#### Semantic Tokens (the public API -- used via Tailwind classes)

```css
:root {
  /* === Semantic Tokens === */
  --pui-primary:       var(--pui-blue-500);
  --pui-primary-hover: var(--pui-blue-600);
  --pui-success:       var(--pui-green-500);
  --pui-danger:        var(--pui-red-500);
  --pui-warning:       var(--pui-amber-500);

  /* Text */
  --pui-foreground:  var(--pui-gray-900);
  --pui-muted:       var(--pui-gray-500);

  /* Surfaces */
  --pui-surface:     #ffffff;
  --pui-surface-alt: var(--pui-gray-50);

  /* Borders */
  --pui-border:        var(--pui-gray-200);
  --pui-border-strong: var(--pui-gray-500);

  /* Spacing (consistent scale across apps) */
  --pui-space-1: 0.25rem;   /* 4px */
  --pui-space-2: 0.5rem;    /* 8px */
  --pui-space-3: 0.75rem;   /* 12px */
  --pui-space-4: 1rem;      /* 16px */
  --pui-space-6: 1.5rem;    /* 24px */
  --pui-space-8: 2rem;      /* 32px */
  --pui-space-12: 3rem;     /* 48px */

  /* Layout */
  --pui-radius-sm: 0.25rem;
  --pui-radius-md: 0.375rem;
  --pui-radius-lg: 0.5rem;

  --pui-shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --pui-shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  --pui-shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);

  --pui-transition: 150ms cubic-bezier(0.4, 0, 0.2, 1);
}
```

#### App-Specific Overrides

```css
/* Per-app accent color via data attribute on <body> */
[data-app="travel-beat"] {
  --pui-primary:       #0ea5e9;  /* Sky Blue */
  --pui-primary-hover: #0284c7;
}

[data-app="risk-hub"] {
  --pui-primary:       #8b5cf6;  /* Purple */
  --pui-primary-hover: #7c3aed;
}

[data-app="weltenhub"] {
  --pui-primary:       #10b981;  /* Emerald */
  --pui-primary-hover: #059669;
}
```

#### Dark Mode (opt-in)

```css
[data-theme="dark"] {
  --pui-foreground:  var(--pui-gray-100);
  --pui-muted:       var(--pui-gray-500);
  --pui-surface:        #1f2937;
  --pui-surface-alt:    #111827;
  --pui-border:         #374151;
  --pui-border-strong:  #4b5563;
}
```

### 3. Shared Tailwind Config

Each app imports a shared config that maps semantic names to CSS variables:

```javascript
// shared/tailwind/tailwind.config.shared.js

module.exports = {
  theme: {
    extend: {
      colors: {
        primary:         "var(--pui-primary)",
        "primary-hover": "var(--pui-primary-hover)",
        surface:         "var(--pui-surface)",
        "surface-alt":   "var(--pui-surface-alt)",
        success:         "var(--pui-success)",
        danger:          "var(--pui-danger)",
        warning:         "var(--pui-warning)",
        foreground:      "var(--pui-foreground)",
        muted:           "var(--pui-muted)",
        border:          "var(--pui-border)",
        "border-strong": "var(--pui-border-strong)",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: ['"JetBrains Mono"', '"Fira Code"', "monospace"],
      },
      borderRadius: {
        DEFAULT: "var(--pui-radius-md)",
        sm: "var(--pui-radius-sm)",
        lg: "var(--pui-radius-lg)",
      },
      boxShadow: {
        sm: "var(--pui-shadow-sm)",
        md: "var(--pui-shadow-md)",
        lg: "var(--pui-shadow-lg)",
      },
    },
  },
};
```

**Per-app usage** (see Section 6 for distribution options).

### 4. Template Usage

```html
{# Developers write semantic Tailwind classes: #}
<div class="bg-surface border border-border rounded-lg p-5 hover:shadow-md">
  <h2 class="text-foreground text-xl font-semibold">{{ title }}</h2>
  <p class="text-muted text-sm mt-1">{{ description }}</p>
  <button class="bg-primary hover:bg-primary-hover text-white px-4 py-2 rounded">
    Action
  </button>
</div>
```

> **Why `text-foreground` not `text-text-primary`?** The Tailwind prefix
> `text-` combined with a color named `text-primary` would produce the
> redundant class `text-text-primary`. Using `foreground` / `muted` as
> color names yields clean classes: `text-foreground`, `text-muted`.

**The `<body>` tag sets the app identity:**

```html
{# In base.html #}
<body data-app="{{ APP_NAME }}" data-theme="light">
```

Where `APP_NAME` is set via Django settings and injected by a context
processor:

```python
# config/settings/base.py
APP_NAME = "travel-beat"

# config/context_processors.py
def app_metadata(request):
    """Inject APP_NAME into every template context."""
    from django.conf import settings
    return {
        "APP_NAME": getattr(settings, "APP_NAME", ""),
    }
```

```python
# config/settings/base.py (TEMPLATES)
TEMPLATES = [{
    "OPTIONS": {
        "context_processors": [
            # ... existing processors ...
            "config.context_processors.app_metadata",
        ],
    },
}]
```

#### Dark Mode Preference Storage

The `data-theme` toggle requires user preference persistence:

- **Default**: `localStorage.getItem("pui-theme")` — client-side, no
  backend dependency, survives page reloads
- **Authenticated users** (future): Optional `User.theme_preference`
  CharField, synced via a one-line JS snippet on login
- **Server-side rendering**: SSR always renders `data-theme="light"`;
  a `<script>` in `<head>` (before paint) reads `localStorage` and
  sets the attribute to avoid FOUC (flash of unstyled content)

### 5. Token Compliance Check

A simple checker enforces that templates use semantic tokens instead of
hardcoded values. This integrates with ADR-040's completeness checker.

```python
# tools/check_design_tokens.py
"""Check templates for hardcoded colors/values that bypass design tokens."""

import re
import sys
from pathlib import Path

# Direct Tailwind color classes that should use semantic alternatives
DIRECT_COLORS = re.compile(
    r"\b(?:bg|text|border)-(?:blue|red|green|gray|amber|sky|purple)"
    r"-\d{2,3}\b"
)

# Hardcoded hex colors in CSS or style attributes
HARDCODED_HEX = re.compile(
    r"(?:color|background|border-color)\s*:\s*#[0-9a-fA-F]{3,8}"
)

# Inline style attributes (also banned by ADR-048 AP-004)
INLINE_STYLE = re.compile(r'\bstyle\s*=\s*"[^"]*"')

SEMANTIC_MAP = {
    # Primary
    "bg-blue-500": "bg-primary",
    "bg-blue-600": "bg-primary-hover",
    "text-blue-500": "text-primary",
    "text-blue-600": "text-primary",
    "border-blue-500": "border-primary",
    # Text
    "text-gray-900": "text-foreground",
    "text-gray-500": "text-muted",
    "text-gray-400": "text-muted",
    # Surfaces
    "bg-gray-50": "bg-surface-alt",
    "bg-gray-100": "bg-surface-alt",
    "bg-white": "bg-surface",
    # Status
    "bg-red-500": "bg-danger",
    "text-red-500": "text-danger",
    "text-red-600": "text-danger",
    "bg-green-500": "bg-success",
    "text-green-500": "text-success",
    "bg-amber-500": "bg-warning",
    "text-amber-500": "text-warning",
    # Borders
    "border-gray-200": "border-border",
    "border-gray-300": "border-border",
    "border-gray-500": "border-border-strong",
}


def check_file(path: Path) -> list[str]:
    """Check a single file for token violations."""
    content = path.read_text(encoding="utf-8")
    errors: list[str] = []

    for match in DIRECT_COLORS.finditer(content):
        suggestion = SEMANTIC_MAP.get(match.group(), "a semantic token")
        errors.append(
            f"  {path}: Direct color '{match.group()}'"
            f" -- use '{suggestion}' instead"
        )

    for match in HARDCODED_HEX.finditer(content):
        errors.append(
            f"  {path}: Hardcoded color '{match.group()}'"
            f" -- use --pui-* token"
        )

    return errors


def main() -> int:
    files = [Path(f) for f in sys.argv[1:]]
    all_errors: list[str] = []
    for f in files:
        if f.exists() and f.suffix in (".html", ".css"):
            all_errors.extend(check_file(f))
    for error in all_errors:
        print(error)
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
```

### 6. File Layout and Distribution

**No npm package infrastructure required.** The shared config lives in
the `platform` repo and is distributed via `collectstatic` or git
subpath checkout:

```text
platform/
├── static/platform/css/
│   └── pui-tokens.css                # CSS Custom Properties (canonical)
└── shared/tailwind/
    └── tailwind.config.shared.js     # Shared Tailwind config

# Distribution to each app (choose ONE):

# Option A: Git subpath (recommended for CI)
# In each app's Makefile or CI:
#   curl -sL https://raw.githubusercontent.com/achimdehnert/platform/main/\
#     static/platform/css/pui-tokens.css > static/platform/css/pui-tokens.css

# Option B: Django collectstatic (if platform is an installed package)
# INSTALLED_APPS = ["platform_core", ...]
# collectstatic gathers static/platform/css/ automatically

# Option C: Symlink (local dev only)
# ln -s ../../platform/static/platform/css/pui-tokens.css \
#   static/platform/css/pui-tokens.css
```

The `pui-tokens.css` file is included in every app's `base.html`:

```html
<link rel="stylesheet" href="{% static 'platform/css/pui-tokens.css' %}">
```

**Tailwind config sharing** uses a simple file copy or `require()` with
a relative path — no npm registry or workspace setup needed:

```javascript
// travel-beat/tailwind.config.js
// Option A: relative require (monorepo / symlink)
const shared = require("../platform/shared/tailwind/tailwind.config.shared");

// Option B: copied file in repo
// const shared = require("./tailwind.config.shared");

module.exports = {
  presets: [shared],
  content: ["./templates/**/*.html"],
};
```

## Consequences

### Positive

- **Consistent look** across all apps via shared semantic tokens
- **Per-app branding** via `data-app` attribute (zero template changes)
- **Dark mode ready** via `data-theme` attribute (opt-in per app)
- **AI-friendly**: Cascade uses `bg-primary` not `bg-blue-500` -- always correct
- **Enforceable**: Token compliance checker catches violations in CI
- **No new runtime dependency**: CSS Custom Properties are native browser API
- **Tailwind stays**: No migration away from Tailwind, just better configuration

### Negative

- **Tailwind config must be shared**: Adds a cross-app dependency
- **Color opacity**: `var()` in Tailwind doesn't support opacity modifiers
  (`bg-primary/50` won't work). Workaround: use `color-mix()` in CSS
  (e.g., `color-mix(in srgb, var(--pui-primary) 50%, transparent)`)
  or define explicit `-light` token variants. Note: `bg-opacity-50`
  is deprecated in Tailwind v4.
- **Learning curve**: Developers must use semantic names instead of direct colors
- **No per-tenant DB-driven branding** (yet): Token values are static CSS.
  Future: a TenantBranding model could inject `--pui-primary` via
  inline `<style>` in `base.html`, but this is out of scope for v1.

### Mitigations

- Shared config is a plain JS file, 1-line import per app (no npm registry)
- Opacity limitation is minor -- only affects rare transparency use cases
- Semantic names are shorter and more readable than hex codes

### Migration Strategy

Existing templates use direct Tailwind colors (`bg-blue-500`, etc.).
Migration path:

1. **Week 1**: Deploy `pui-tokens.css` + shared Tailwind config to all apps
2. **Week 2-3**: Run `check_design_tokens.py` in warning mode (CI reports
   violations but does not block)
3. **Week 4+**: Enable blocking mode in CI (`--strict` flag)
4. **Auto-fix** (future): A `sed`-based script or codemod using the
   `SEMANTIC_MAP` dictionary to batch-replace direct colors

## Migration Tracking

| Item | Status | Datum | Notizen |
|------|--------|-------|--------|
| `pui-tokens.css` erstellen (platform_context/static/) | ✅ done | 2026-02-24 | Layer 1-4 + Utility-Klassen |
| `travel-beat/base.html` — pui-tokens.css einbinden | ✅ done | 2026-02-24 | bereits vorhanden + data-app="{{ APP_NAME }}" |
| `risk-hub/base.html` — pui-tokens.css + data-app | ✅ done | 2026-02-24 | data-app="risk-hub" → Purple accent |
| `cad-hub/base.html` — pui-tokens.css + data-app | ✅ done | 2026-02-24 | Lokale Kopie in apps/core/static/ |
| `shared/tailwind/tailwind.config.shared.js` — semantische Farbnamen | ✅ done | pre-2026 | bereits vorhanden |
| CI-Lint: `check_design_tokens.py` — Violations reporten | ⬜ Ausstehend | — | warning-mode erst, dann strict |
| Per-App Tailwind-Config mit shared preset (wenn Build-Step vorhanden) | ⬜ Ausstehend | — | CDN-Apps: nur pui-tokens.css nötig |

---

## Alternatives Considered

1. **Only CSS Custom Properties (no Tailwind bridge)** -- Loses Tailwind
   productivity, requires custom CSS classes for everything
2. **Only Tailwind theme** -- No runtime theming, no per-app branding,
   requires rebuild for every color change
3. **CSS-in-JS (Styled Components, Emotion)** -- Wrong stack, we use
   server-rendered Django templates
4. **Sass variables** -- Build-time only, no runtime theming, adds Sass
   compilation step
5. **Design token libraries (Style Dictionary, Theo)** -- Overkill for
   10 semantic colors + a few layout tokens
