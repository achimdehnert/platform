---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-031: Static Asset Versioning & Landing Page Registry

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2026-02-12 |
| **Author** | Cascade |
| **Scope** | Platform-wide |

## Context

On 2026-02-12 the `iil.pet` landing page was rewritten to add the Schutztat/Odoo
app card. In the process, **existing content was overwritten** without backup or
version control. Admin links that were previously present on the app cards were lost.

This is a systemic risk: static HTML assets served by nginx (`/var/www/*`) are not
under version control and have no deployment pipeline. Any `file_write` or `scp`
overwrites the live file with no rollback path.

## Decision

### 1. Git as Single Source of Truth

All static landing pages and web assets live in the `platform` repo under
`static-sites/<domain>/`. The server directory `/var/www/<domain>/` is a
**deployment target**, never the source of truth.

```
platform/
└── static-sites/
    ├── iil.pet/
    │   └── index.html          # Landing page
    ├── prezimo.com/             # (if applicable)
    └── deploy.sh               # rsync-based deploy script
```

### 2. Deployment via Script (not ad-hoc file_write)

```bash
# platform/static-sites/deploy.sh
#!/bin/bash
set -euo pipefail
SITE="${1:?Usage: deploy.sh <site-dir>}"
HOST="88.198.191.108"
rsync -avz --checksum "static-sites/${SITE}/" "root@${HOST}:/var/www/${SITE}/"
echo "Deployed ${SITE} → ${HOST}:/var/www/${SITE}/"
```

### 3. Landing Page App Registry

The landing page reads its app cards from a structured JSON registry instead of
hardcoded HTML. This ensures that adding/removing apps is a data change, not a
template rewrite.

```
platform/static-sites/iil.pet/
├── index.html          # Template that reads apps.json
└── apps.json           # App registry (single source of truth)
```

#### apps.json Schema

```json
[
  {
    "name": "Schutztat",
    "url": "https://schutztat.iil.pet",
    "admin_url": "https://schutztat.iil.pet/web#action=base.open_module_tree",
    "description": "Occupational safety & risk assessment platform.",
    "icon": "🛡️",
    "color": "orange",
    "tags": ["Odoo 18", "Django"],
    "status": "live"
  }
]
```

Each app entry has:
- **`url`** — public app URL
- **`admin_url`** — admin/backend URL (the missing piece!)
- **`tags`** — technology tags
- **`status`** — `live`, `staging`, `maintenance`

### 4. Pre-Deploy Checklist (Cascade Rule)

Before overwriting any file in `/var/www/`:

1. **Check if file exists** — if yes, back it up first
2. **Check if git-managed** — prefer editing in `platform/static-sites/`
3. **Never use `file_write` directly** for production web assets
4. **Always commit to git first**, then deploy from git

### 5. Backup on Deploy

The deploy script creates a timestamped backup before overwriting:

```bash
ssh root@${HOST} "cp -r /var/www/${SITE} /var/www/.backup/${SITE}-$(date +%Y%m%d-%H%M%S)" 2>/dev/null || true
```

## Consequences

- **Positive**: All static assets are version-controlled and auditable
- **Positive**: Rollback is trivial (`git revert` + deploy)
- **Positive**: App registry prevents manual HTML editing errors
- **Positive**: Admin links can never be "lost" again
- **Negative**: Slight overhead for simple text changes (commit → deploy)
- **Mitigated**: Deploy script makes it a one-liner

## Affected Systems

| System | Change |
|--------|--------|
| `platform` repo | New `static-sites/` directory |
| `88.198.191.108` | `/var/www/` becomes deploy target only |
| Cascade workflow | Must use git-first for static assets |
