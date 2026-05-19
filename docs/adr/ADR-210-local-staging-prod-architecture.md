---
id: ADR-210
title: Local/Staging/Prod Architecture — three strictly separated layers with generated artifacts
status: proposed
date: 2026-05-19
deciders: [achim]
consulted: [cascade-advocatus-diabolus]
informed: [all-repos]
domains: [infrastructure, deployment, auth, drift-prevention]
supersedes: []
amends: [ADR-198]
depends_on: [ADR-022, ADR-142, ADR-157, ADR-198]
tags: [staging, oidc, authentik, cloudflare-tunnel, nginx, ssot, generated]
scope:
  include_paths:
    - "registry/repos.yaml"
    - "scripts/render_staging.py"
    - "scripts/checks/staging_*.sh"
    - "**/docker-compose.staging.yml"
    - "**/.env.staging.example"
    - "**/config/settings/staging.py"
drift_check_paths:
  - "registry/repos.yaml"
  - "scripts/checks/staging_*.sh"
---

# ADR-210 — Local/Staging/Prod Architecture (Generated-from-SSoT)

## Context

Inventory on 2026-05-19 revealed three structural inconsistencies:

1. **DNS dead-letters** — 22 `staging-{repo}.iil.pet` CNAMEs route through
   the bf-staging tunnel, whose endpoint server `staging-platform`
   (178.104.184.168) hosts only risk-hub. 21 of 22 hostnames have no upstream.
2. **Misplaced nginx vhosts** — vhosts for staging hostnames live on
   dev-desktop where nginx is **inactive** and the tunnel never points.
3. **Schema collision in OIDC** — 4 Authentik staging providers use the
   redirect pattern `{repo}-staging.iil.pet`; DNS uses `staging-{repo}.iil.pet`.
   Result: zero functional staging-OIDC logins.

A prior session (PR #209) established **evidence discipline** as a meta-rule:
every architectural claim must be falsifiable by a cheap, idempotent check
(≤2s, single command, deterministic exit code).

## Decision

**Three strictly separated hosting layers, with all per-repo artifacts
GENERATED from a single source of truth (`registry/repos.yaml`).** Hand-edits
to generated files are forbidden; drift is structurally prevented, not
detected after the fact.

### Layers

| Layer   | Host                                | Container Name        | Hostname                            | OIDC                       | Tunnel       |
|---------|-------------------------------------|-----------------------|-------------------------------------|----------------------------|--------------|
| LOCAL   | dev-desktop / WSL                   | `{repo}_local_*`      | `localhost:80xx`                    | disabled (Django auth)     | —            |
| STAGING | `staging-platform` (178.104.184.168)| `{repo}_staging_*`    | `staging-{repo}.iil.pet`            | `{repo}-staging` provider  | bf-staging   |
| PROD    | `ubuntu-8gb-nbg1-1` (88.198.191.108)| `{repo}_*`            | `{repo}.iil.pet` (+ public domains) | `{repo}` provider          | bf-platform  |

### Binding Rules + cheapest-checks

Every rule below is paired with an executable verification at
`scripts/checks/staging_<rule>.sh`. CI calls `make verify-staging-strategy`.
A rule without a passing check is a **strategy violation**.

| # | Rule | Check (file in `scripts/checks/`) |
|---|---|---|
| R1 | Staging DNS schema is exactly `staging-{repo}.iil.pet` | `staging_dns_schema.sh` — queries CF API, asserts no `*-staging.iil.pet` records exist |
| R2 | All staging containers run on `staging-platform` only | `staging_host_locality.sh` — SSH all known hosts, fails if `*_staging_*` containers found outside staging-platform |
| R3 | Staging container naming is `{repo}_staging_{role}` | `staging_naming.sh` — parses `docker ps`, regex-asserts |
| R4 | Staging port = `19000 + index(repo)` from `repos.yaml` (dedicated range, collision-free) | `staging_port_range.sh` — asserts every staging port ∈ `[19000..19999]` and unique |
| R5 | bf-staging tunnel ingress is catch-all `https://localhost:443` | `staging_tunnel_ingress.sh` — SSH staging-platform, parses cloudflared config |
| R6 | Each staging Authentik provider has redirect `https://staging-{repo}.iil.pet/oidc/callback/` | `staging_oidc_redirects.sh` — Authentik API, asserts all `*-staging` providers match |
| R7 | `docker-compose.staging.yml`, `nginx-staging-vhost.conf`, `.env.staging.example` are byte-identical to renderer output | `staging_generated_drift.sh` — re-renders, diffs, exits 1 on diff |
| R8 | dev-desktop has no `staging-*.conf` in nginx and no `*_staging_*` containers | `staging_devdesktop_clean.sh` — SSH check |

### Single Source of Truth

`platform/registry/repos.yaml` (existing file) gains per-repo `staging:` and
`oidc:` blocks:

```yaml
- name: risk-hub
  repo: risk-hub
  deploy:                       # PROD (existing)
    server_path: /opt/risk-hub
    web_container: risk_hub_web
    port: 8090
  staging:                      # NEW — STAGING
    server_path: /opt/risk-hub-staging
    web_container: risk_hub_staging_web
    port: 19001                 # MUST be in [19000..19999], unique across repos
    hostnames:
      - staging.schutztat.de
      - staging-riskhub.iil.pet     # MUST match `staging-{repo}.iil.pet` for iil.pet hostnames (R1)
  oidc:                         # NEW — IDENTITY
    prod_app_slug: risk-hub
    prod_redirect: https://schutztat.com/oidc/callback/
    staging_app_slug: risk-hub-staging
    staging_redirect: https://staging.schutztat.de/oidc/callback/
```

### Generated Artifacts (no hand-edits)

`scripts/render_staging.py <repo-name>` writes:

- `<repo>/docker-compose.staging.yml`
- `<repo>/.env.staging.example`
- `staging-platform:/etc/nginx/sites-available/staging-{repo}.iil.pet.conf`
- `<repo>/config/settings/staging.py` (or staging block in single-file settings)

Every generated file starts with:

```
# GENERATED by scripts/render_staging.py — DO NOT EDIT
# SSoT: platform/registry/repos.yaml
# Re-render: make render-staging REPO=<name>
```

A pre-commit hook (`.pre-commit-hooks/render-staging.yaml`) re-renders on
any change to `registry/repos.yaml` and fails the commit if generated
files drift.

### Migration

Migration is tracked as **GitHub Issues**, not as a linear plan in this ADR.
Each issue has an executable acceptance test (e.g. `curl -fsS
https://staging-{repo}.iil.pet/livez/`).

**Pilot inversion** — the first verification deliberately targets one of the
21 currently-dead staging CNAMEs (e.g. `staging-devhub.iil.pet`), **not**
risk-hub. risk-hub already works; piloting the working case proves
nothing. Lifting a dead hostname to a 200-OK end-to-end (DNS → tunnel →
nginx → container → OIDC) is the architecture's actual falsification
gate.

Open issues at time of writing:

- `infra: staging dev-hub pilot — lift first dead CNAME to live` (this ADR's first verification)
- `infra: 4 misnamed Authentik providers — fix redirect URIs`
- `infra: staging-platform vhost rollout per repo` (1 issue per repo with `staging:` block)
- `infra: dev-desktop cleanup (S8)`
- `infra: provision *.iil.pet wildcard cert via DNS-01` (replaces 22-cert plan)

## Consequences

### Positive
- **Drift is structurally impossible**, not merely detected. Hand-editing a
  generated file is caught at pre-commit AND CI.
- Every binding rule has a 2-second falsification command — review #209
  meta-rule honored.
- Agents can derive deployment topology from `repos.yaml` deterministically;
  no guessing across three potential hosts.
- ADR-198 (two tunnels) remains valid; this ADR adds the hosting model that
  makes it actionable.

### Negative / Costs
- ~3h initial renderer + checks scaffolding
- ~3h initial DNS-01 ACME setup (acme.sh / lego, cron, deploy hook) for the wildcard cert
- Each repo: one `staging:` + `oidc:` block in registry, one render run,
  one staging deploy, one Authentik provider — ~30 min/repo

### TLS strategy
- **One** wildcard certificate `*.iil.pet` via DNS-01 (Cloudflare API token already provisioned in `~/.secrets/cloudflare_*`) covers prod + staging + future hostnames. LE rate-limit class eliminated. No per-host renewal monitoring required.
- Per-customer prod domains (e.g. `schutztat.com`, `staging.schutztat.de`) keep individual HTTP-01 certs.

### Out-of-scope (intentional)
- Backup strategy for staging databases (separate ADR)
- CI/CD trigger choreography for staging deploys (separate ADR)
- Staging seed-data strategy (separate ADR)

## Falsification Test (operationalized)

This ADR is **falsified** if any of the following holds after the
dev-hub-staging pilot (see *Pilot inversion* above) goes live:

- `make verify-staging-strategy` exits non-zero with no open
  remediation issue
- a hand-edit to a generated file passes the **CI gate** (pre-commit is
  DX-only, not the contract)
- `https://staging-devhub.iil.pet/livez/` returns non-200 for >5min
  without a deploy in progress
- a request with `Host: staging-*.iil.pet` is observed reaching the
  `bf-platform` (prod) tunnel — cross-layer leak falsifies the layer model

If falsified, this ADR is **revised**, not silently degraded.

## Alternatives Considered

- **Single tunnel for prod+staging** — rejected: traffic separation
  hardens prod blast-radius (ADR-198).
- **CF Access instead of Authentik** — rejected: Authentik is already SSoT
  for identity; vendor coupling against ADR-142.
- **Hand-maintained per-repo configs** — rejected by review #209 §3.1:
  drift detection is a worse pattern than drift prevention.
- **Hosting mix dev-desktop + staging-platform** — rejected: agents need
  deterministic locality.

## References

- ADR-022 — Repository Consistency Standards
- ADR-142 — Authentik OIDC SSoT
- ADR-157 — *(referenced by review #209 — evidence discipline lineage)*
- ADR-198 — Staging Edge: Second Cloudflare Tunnel + Subdomain Convention
- PR #209 — Evidence Discipline + SSoT Enforcement (review-driven design input)
