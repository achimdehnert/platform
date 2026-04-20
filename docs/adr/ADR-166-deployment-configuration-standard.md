---
id: ADR-166
title: "Standardize deployment config via .ship.conf SSOT with /livez/ health checks"
status: accepted
date: 2026-04-20
amended: 2026-04-20
amends: ADR-120
decision-makers: [achimdehnert]
consulted: []
informed: []
scope: platform
implementation_status: implemented
implementation_evidence:
  - "18/18 repos: .ship.conf IMAGE corrected (2026-04-20)"
  - "18/18 repos: health URL standardized to /livez/ (2026-04-20)"
  - "18/18 repos: deploy.yml, catalog-info.yaml, .ship.conf consistent (2026-04-20)"
---

<!-- Drift-Detector-Felder
staleness_months: 6
drift_check_paths:
  - "*/.ship.conf"
  - "*/.github/workflows/deploy.yml"
  - "*/catalog-info.yaml"
supersedes_check: null
-->

# ADR-166: Standardize deployment config via .ship.conf SSOT with /livez/ health checks

## Context and Problem Statement

ADR-120 established the Unified Multi-Repo Deployment Pipeline with `.ship.conf` as SSOT
and `_deploy-unified.yml` as shared workflow. An audit across all 18 production repos
(April 2026) revealed significant inconsistencies:

- **IMAGE in .ship.conf** did not match the actual GHCR image in any repo (18/18 wrong)
- **Health check paths** were mixed between `/healthz/` (readiness) and `/livez/` (liveness)
- **Dockerfile paths** in deploy.yml were missing or incorrect for 4 repos
- **3 different GHCR naming patterns** in use across repos
- **Health URLs** differed between `.ship.conf`, `deploy.yml`, and `catalog-info.yaml`

How do we ensure deployment configuration stays consistent and verifiable across all repos?

## Decision Drivers

- `ship.sh` must work reliably without manual overrides
- Deploy health checks must not false-negative during DB startup
- New repo onboarding must be deterministic (copy template, fill values)
- Configuration drift must be detectable by automated audit scripts
- Port allocation per ADR-021 §2.9 must be respected

## Considered Options

1. **Strict .ship.conf SSOT with /livez/** — single source of truth, all files derived
2. **Derive config from docker-compose.prod.yml** — compose as SSOT, generate .ship.conf
3. **Central registry in platform repo** — one YAML file with all 18 app configs

## Decision Outcome

Chosen option: **1. Strict .ship.conf SSOT with /livez/**

- `.ship.conf` is the simplest, most portable format (bash-sourceable)
- Every repo is self-contained — no cross-repo dependency for deployment
- Compliance is verifiable with a single bash loop
- `/livez/` as deploy health check is safer than `/healthz/` (no DB dependency)

## Decision

### 1. `.ship.conf` Format (SSOT)

Every repo MUST have a `.ship.conf` at the repository root with these fields:

```bash
# .ship.conf — Deployment SSOT (ADR-120, ADR-166)
APP_NAME="<repo-name>"
IMAGE="ghcr.io/achimdehnert/<image-name>"
DOCKERFILE="docker/app/Dockerfile"
WEB_SERVICE="<compose-service-name>"
SERVER="root@88.198.191.108"
COMPOSE_PATH="/opt/<repo-name>"
COMPOSE_FILE="docker-compose.prod.yml"
HEALTH_URL="https://<primary-domain>/livez/"
MIGRATE_CMD="python manage.py migrate --no-input"
```

`ship.sh` reads exclusively from `.ship.conf`. All other files MUST be consistent.

### 2. Health Check Endpoints

Every Django app MUST implement three endpoints:

| Endpoint | Purpose | Checks | Use Case |
|----------|---------|--------|----------|
| `/livez/` | Liveness probe | Process alive only | **Deploy verification**, Docker HEALTHCHECK |
| `/healthz/` | Readiness probe | DB + Redis + Migrations | Load balancer readiness |
| `/readyz/` | Alias for `/healthz/` | Same as healthz | K8s compatibility |

**Deploy verification** (`HEALTH_URL` in `.ship.conf` and `deploy.yml`) MUST use `/livez/`:
- Fast response (no DB roundtrip)
- No false-negatives during DB startup
- Consistent across all repos

### 3. GHCR Image Naming

**Standard format**: `ghcr.io/achimdehnert/<repo-name>:latest`

The `_deploy-unified.yml` workflow builds and pushes images using this flat format.

**Legacy exceptions** (to be migrated incrementally):

| Repo | Current Image | Reason |
|------|--------------|--------|
| 137-hub | `ghcr.io/achimdehnert/137-hub/hub137-web` | Pre-standard naming |
| pptx-hub | `ghcr.io/achimdehnert/pptx-hub/pptx-hub-web` | Pre-standard naming |
| risk-hub | `ghcr.io/achimdehnert/risk-hub/risk-hub-web` | Pre-standard naming |
| bfagent | `ghcr.io/achimdehnert/bfagent-web` | No sub-path but -web suffix |

New repos MUST use the flat format.

### 4. Dockerfile Location

**Standard**: `docker/app/Dockerfile`

- If a repo uses a non-standard location, `deploy.yml` MUST explicitly set `dockerfile_path:`
- Root `Dockerfile` is accepted for legacy repos
- `.ship.conf` DOCKERFILE field MUST match the actual file used by CI

### 5. Consistency Rule

These files MUST contain identical values for IMAGE, HEALTH_URL, and DOCKERFILE:

1. `.ship.conf` — SSOT
2. `.github/workflows/deploy.yml` — CI/CD
3. `catalog-info.yaml` — Service catalog
4. `docker-compose.prod.yml` — Container orchestration

## Consequences

- Good, because a single grep/script can validate configuration across all 18 repos
- Good, because `ship.sh` works reliably across all repos without manual overrides
- Good, because deploy health checks never false-negative on DB startup delays
- Good, because new repo onboarding has a clear, verifiable checklist
- Bad, because 4 legacy repos have nested GHCR image names (migration requires compose + server changes)
- Bad, because existing CI runs may trigger due to deploy.yml changes

### Confirmation

Compliance is verified by running the audit script below. All 18 repos must show `OK`.
The MCP health dashboard (`deployment_mcp/tools/system_tools.py`) uses `/livez/` for all apps.

### Legacy Image Migration Tracking

| Repo | Current Image | Target Image | Status |
|------|--------------|--------------|--------|
| 137-hub | `137-hub/hub137-web` | `137-hub` | ⬜ Pending |
| pptx-hub | `pptx-hub/pptx-hub-web` | `pptx-hub` | ⬜ Pending |
| risk-hub | `risk-hub/risk-hub-web` | `risk-hub` | ⬜ Pending |
| bfagent | `bfagent-web` | `bfagent` | ⬜ Pending |

### Compliance Verification

Run audit across all repos:

```bash
for repo in /home/devuser/github/*/; do
  [ -f "$repo/.ship.conf" ] || continue
  name=$(basename "$repo")
  ship_health=$(grep "^HEALTH_URL=" "$repo/.ship.conf" | cut -d= -f2 | tr -d '"')
  deploy_health=$(grep "health_check_url:" "$repo/.github/workflows/deploy.yml" 2>/dev/null | head -1 | sed 's/.*health_check_url: *//' | tr -d '"')
  [ "$ship_health" = "$deploy_health" ] && echo "OK $name" || echo "MISMATCH $name: $ship_health vs $deploy_health"
done
```

## Pros and Cons of the Options

### Option 1: Strict .ship.conf SSOT with /livez/

- Good, because bash-sourceable — works in CI, local scripts, and MCP tools
- Good, because self-contained per repo — no central registry dependency
- Good, because `/livez/` never fails on slow DB startup
- Bad, because values must be kept in sync across 4 files manually

### Option 2: Derive config from docker-compose.prod.yml

- Good, because compose is already the runtime truth
- Bad, because compose YAML parsing in bash is fragile
- Bad, because compose files vary significantly across repos (build vs image, env vars)

### Option 3: Central registry in platform repo

- Good, because single file to audit
- Bad, because cross-repo dependency — platform repo must be cloned/accessible
- Bad, because merge conflicts when multiple repos update simultaneously

## More Information

- ADR-120: Unified Multi-Repo Deployment Pipeline
- ADR-021: Health Check Endpoints (port allocation table §2.9)
- ADR-160: Platform Health Dashboard
