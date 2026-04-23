# iil-platform — IIL Platform Foundation

Umbrella package that bundles the core IIL Platform packages into a single dependency.

## Installation

```bash
# Core (platform-context + tenancy)
pip install iil-platform

# With Module Shop
pip install "iil-platform[shop]"

# With Django Commons (health, middleware, logging)
pip install "iil-platform[commons]"

# With Notifications
pip install "iil-platform[notifications]"

# Everything
pip install "iil-platform[full]"
```

## What's included

| Extra | Package | Import Path |
|-------|---------|-------------|
| *(core)* | iil-platform-context | `from platform_context import ...` |
| *(core)* | iil-django-tenancy | `from django_tenancy import ...` |
| `[commons]` | iil-django-commons | `from iil_commons import ...` |
| `[shop]` | iil-django-module-shop | `from django_module_shop import ...` |
| `[notifications]` | iil-platform-notifications | `from platform_notifications import ...` |

## Note

This is an **umbrella/meta-package** — it contains no code of its own.
Sub-packages are developed and versioned independently in `platform/packages/`.
Import paths remain stable and unchanged.

See [ADR-146](https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-146-package-consolidation-strategy.md) for the consolidation strategy.
