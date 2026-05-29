---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
implementation_status: implemented
implementation_evidence:
  - "all hubs: static asset versioning active"
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

## Addendum 2026-05-29 — Härtung (externe Review-Befunde)

Ergänzt die ursprüngliche Entscheidung um vier Härtungsmaßnahmen aus einer externen ADR-Review
(GPT-5.5 via `/adr-handoff-extern`; Befunde durch das Step-5-Rückfluss-Gate als `[valid]` bestätigt).
**Kein Reversal** der Kernentscheidung — Git als SSoT, Script-Deploy und `apps.json` bleiben.

1. **Backup-Retention (AD-3).** `/var/www/.backup/` wächst sonst unbegrenzt. Regel: die letzten
   **30 Deployments oder 90 Tage** behalten, Älteres räumt das Deploy-Script auf.
2. **`apps.json`-Schema + Validierung (REC-2).** Pflichtfelder (`name`, `url`, `admin_url`,
   `status`) als JSON-Schema festschreiben; der Deploy **bricht bei Schema-/URL-Fehler ab**.
3. **Atomarer Deploy (AD-4).** Statt in-place-`rsync` nach `/var/www/<site>/`: in ein temporäres
   Verzeichnis deployen und per **Verzeichnis-Swap** atomar aktivieren — kein inkonsistenter
   Zwischenzustand für Nutzer während des Deploys.
4. **Git-Checkout-Guard (AD-2 / REC-4).** Die menschliche Pre-Deploy-Checkliste wird **technisch
   erzwungen**: `deploy.sh` bricht ab, wenn nicht aus einem sauberen Git-Checkout deployt wird
   (kein dirty working tree, kein Deploy ungetrackter Assets).

**Bewusst NICHT übernommen:** Landingpage in den Django-Stack ziehen (Out-of-Box-Alternative) —
für rein statische Seiten zu schwergewichtig; der Minimal-Ansatz bleibt (settled). „Script statt
Pipeline" bleibt ebenfalls (AD-7, out-of-scope) — Validierung wird innerhalb des Scripts aufgerufen.

_Umsetzung in `static-sites/deploy.sh` + `apps.schema.json` als Folge-Arbeit; dieses Addendum hält
die Entscheidung fest._
