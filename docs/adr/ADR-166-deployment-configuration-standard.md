---
id: ADR-166
title: "Deployment Configuration Standard — .ship.conf, Health Checks, Image Naming"
status: accepted
date: 2026-04-20
amends: ADR-120
decision-makers: [achimdehnert]
consulted: []
informed: []
scope: platform
---

# ADR-166: Deployment Configuration Standard

## Context

ADR-120 established the Unified Multi-Repo Deployment Pipeline with `.ship.conf` as SSOT
and `_deploy-unified.yml` as shared workflow. An audit across all 18 production repos
(April 2026) revealed significant inconsistencies:

- **IMAGE in .ship.conf** did not match the actual GHCR image in any repo
- **Health check paths** were mixed between `/healthz/` (readiness) and `/livez/` (liveness)
- **Dockerfile paths** in deploy.yml were missing or incorrect for 4 repos
- **3 different GHCR naming patterns** in use across repos
- **Health URLs** differed between `.ship.conf`, `deploy.yml`, and `catalog-info.yaml`

All inconsistencies were fixed as part of this ADR's acceptance.

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

### Positive

- Single grep/script can validate configuration across all 18 repos
- `ship.sh` works reliably across all repos without manual overrides
- Deploy health checks never false-negative on DB startup delays
- New repo onboarding has clear, verifiable checklist

### Negative

- 4 legacy repos have nested GHCR image names (migration requires compose + server changes)
- Existing CI runs may trigger due to deploy.yml changes

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

## Related

- ADR-120: Unified Multi-Repo Deployment Pipeline
- ADR-021: Health Check Endpoints
- ADR-160: Platform Health Dashboard
