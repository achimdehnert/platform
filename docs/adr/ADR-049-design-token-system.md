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
/* static/platform/css/tokens.css */

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
  --pui-text-primary:   var(--pui-gray-900);
  --pui-text-secondary: var(--pui-gray-500);

  /* Surfaces */
  --pui-surface:     #ffffff;
  --pui-surface-alt: var(--pui-gray-50);

  /* Borders */
  --pui-border:        var(--pui-gray-200);
  --pui-border-strong: var(--pui-gray-500);

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
  --pui-text-primary:   var(--pui-gray-100);
  --pui-text-secondary: var(--pui-gray-500);
  --pui-surface:        #1f2937;
  --pui-surface-alt:    #111827;
  --pui-border:         #374151;
  --pui-border-strong:  #4b5563;
}
```

### 3. Shared Tailwind Config

Each app imports a shared config that maps semantic names to CSS variables:

```javascript
// packages/platform-tailwind/tailwind.config.shared.js

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
        "text-primary":  "var(--pui-text-primary)",
        "text-secondary":"var(--pui-text-secondary)",
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

**Per-app usage:**

```javascript
// travel-beat/tailwind.config.js
const shared = require("@platform/tailwind-config");

module.exports = {
  presets: [shared],
  content: ["./templates/**/*.html"],
};
```

### 4. Template Usage

```html
{# Developers write semantic Tailwind classes: #}
<div class="bg-surface border border-border rounded-lg p-5 hover:shadow-md">
  <h2 class="text-text-primary text-xl font-semibold">{{ title }}</h2>
  <p class="text-text-secondary text-sm mt-1">{{ description }}</p>
  <button class="bg-primary hover:bg-primary-hover text-white px-4 py-2 rounded">
    Action
  </button>
</div>
```

**The `<body>` tag sets the app identity:**

```html
{# In base.html #}
<body data-app="{{ APP_NAME }}" data-theme="light">
```

Where `APP_NAME` is set via Django settings:

```python
# config/settings/base.py
APP_NAME = "travel-beat"  # Used in templates via context processor
```

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
    "bg-blue-500": "bg-primary",
    "bg-blue-600": "bg-primary-hover",
    "text-gray-900": "text-text-primary",
    "text-gray-500": "text-text-secondary",
    "bg-red-500": "bg-danger",
    "bg-green-500": "bg-success",
    "bg-amber-500": "bg-warning",
    "border-gray-200": "border-border",
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

### 6. File Layout

```text
packages/platform-tailwind/
├── tailwind.config.shared.js    # Shared Tailwind config
├── tokens.css                   # CSS Custom Properties
└── package.json                 # npm package for cross-app sharing

# In each app:
<app>/static/<app>/css/
└── tokens.css → symlink or copy of packages/platform-tailwind/tokens.css
```

The `tokens.css` file is included in every app's `base.html`:

```html
<link rel="stylesheet" href="{% static 'platform/css/tokens.css' %}">
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
  (`bg-primary/50` won't work) -- use explicit `bg-primary bg-opacity-50`
- **Learning curve**: Developers must use semantic names instead of direct colors

### Mitigations

- Shared config is a simple npm preset, 1-line import per app
- Opacity limitation is minor -- only affects rare transparency use cases
- Semantic names are shorter and more readable than hex codes

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
