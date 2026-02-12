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

```text
platform/
└── static-sites/
    ├── iil.pet/
    │   ├── index.html      # Landing page template
    │   └── apps.json       # App registry (single source of truth)
    └── deploy.sh           # rsync-based deploy script
```

### 2. Deployment via Script (not ad-hoc file_write)

```bash
# From platform repo root:
bash static-sites/deploy.sh iil.pet
```

The script creates a timestamped backup before overwriting.

### 3. Landing Page App Registry

The landing page reads its app cards from `apps.json` instead of
hardcoded HTML. Adding/removing apps is a data change, not a template rewrite.

Each app entry has:

- **`url`** — public app URL
- **`admin_url`** — admin/backend URL
- **`tags`** — technology tags
- **`status`** — `live`, `staging`, `maintenance`

### 4. Pre-Deploy Checklist (Cascade Rule)

Before overwriting any file in `/var/www/`:

1. **Check if file exists** — if yes, back it up first
2. **Check if git-managed** — prefer editing in `platform/static-sites/`
3. **Never use `file_write` directly** for production web assets
4. **Always commit to git first**, then deploy from git

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
