# ADR-021: Unified Deployment Architecture

**Status**: Accepted (Amended 2026-02-20)
**Date**: 2026-02-10
**Amended**: 2026-02-20
**Author**: Achim Dehnert
**Scope**: All platform projects
**Supersedes**: Per-project ad-hoc deployment setups

> **Amendment 2026-02-20**: Added §2.14 (`infra-deploy` repo as Agent-API), §2.15 (Fast-Deploy Override), §2.16 (Expand-Contract Migrations Convention), updated §2.3 (dev-hub added), §2.9 (port registry updated), §4 (current state updated).

---

## 1. Problem Statement

Five Django projects deploy to one Hetzner VM. Each evolved its own CI/CD pipeline independently, creating **unnecessary cognitive load** and **fragile, inconsistent automation**:

- 3 different Dockerfile locations, 2 compose-file locations, 3 health-endpoint paths
- Only 1 of 5 projects uses the existing platform reusable workflows
- 2 projects have no auto-deploy at all (risk-hub: build-only, weltenhub: stub)
- No documented rollback, no image-tagging strategy, no secrets inventory

**Cost of status quo**: Every deploy requires re-discovering project-specific details. AI assistants re-probe server layout on every invocation. Workflow bugs are fixed per-repo instead of once.

## 2. Decision

### 2.1 Infrastructure Constants

These values are identical across all projects and **MUST NOT be re-discovered**:

| Constant | Value |
| --- | --- |
| Server | `88.198.191.108` (Hetzner VM) |
| SSH user | `root` |
| Registry | `ghcr.io/achimdehnert/` |
| Reverse proxy | Nginx + Let's Encrypt |
| Deploy pattern | Build → Push GHCR → SSH pull → force-recreate |
| Internal app port | `8000` (Gunicorn) |
| Env file on server | `.env.prod` (never committed) |

### 2.2 Conventions (MUST for new projects, SHOULD for existing)

| Convention | Standard | Rationale |
| --- | --- | --- |
| Dockerfile | `docker/app/Dockerfile` | Separates infra from app code |
| Compose | `docker-compose.prod.yml` (root) | Predictable, one level |
| Health endpoints | `/livez/` (liveness) + `/healthz/` (readiness) | Matches `deploy-remote.sh` default + platform template |
| Image name | `ghcr.io/achimdehnert/<repo>:<tag>` | Flat; no nested sub-images |
| Image tags | `latest` + git SHA short (7 chars) | Rollback by SHA, default by latest |
| Server path | `/opt/<repo>` | Exception: bfagent → `/opt/bfagent-app` (legacy) |
| Service naming | `<repo>-web`, `<repo>-worker`, `<repo>-beat` | Compose services follow repo name |
| Container naming | `<repo_underscored>_web` | e.g. `risk_hub_web` |
| Non-root user | Required in Dockerfile | Security; `USER <appname>` |
| HEALTHCHECK | Required in Dockerfile | `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/livez/')"` |
| Multi-stage build | Recommended | Smaller images, no build tools in prod |

### 2.3 Per-Project Parameters (the only things that vary)

| Parameter | bfagent | risk-hub | travel-beat | weltenhub | pptx-hub | dev-hub |
| --- | --- | --- | --- | --- | --- | --- |
| `deploy_path` | `/opt/bfagent-app` | `/opt/risk-hub` | `/opt/travel-beat` | `/opt/weltenhub` | `/opt/pptx-hub` | `/opt/dev-hub` |
| `dockerfile` | `Dockerfile` ¹ | `docker/app/Dockerfile` | `docker/Dockerfile` ¹ | `Dockerfile` ¹ | `docker/app/Dockerfile` | `docker/Dockerfile` |
| `compose_file` | `docker-compose.prod.yml` | `docker-compose.prod.yml` | `deploy/docker-compose.prod.yml` ¹ | `docker-compose.prod.yml` | `docker-compose.prod.yml` | `docker-compose.prod.yml` |
| `health_url` | `https://bfagent.iil.pet/healthz/` | `https://demo.schutztat.de/healthz/` ² | `https://drifttales.com/healthz/` ² | `https://weltenforger.com/healthz/` ² | *not deployed* | `https://devhub.iil.pet/livez/` |
| `web_service` | `bfagent-web` | `risk-hub-web` | `web` ¹ | `weltenhub-web` | `web` | `devhub-web` |
| `extra_services` | — | `risk-hub-worker` | `celery` | `weltenhub-celery weltenhub-beat` | `worker` | `devhub-celery devhub-beat` |
| `container` | `bfagent_web` | `risk_hub_web` | `travelbeat_web` | `weltenhub_web` | `pptx_hub_web` | `devhub_web` |
| `host_port` | 8088 | 8090 | 8002 | 8081 | 8020 | 8085 |
| `database` | shared (`bfagent_db`) | own stack | own stack | shared (`bfagent_db`) | own stack | shared (`bfagent_db`) |
| `python` | 3.11 | 3.12 | 3.12 | 3.12 | 3.12 | 3.12 |
| `source_dir` | `.` | `src` | `apps` | `apps` | `src` | `.` |
| `settings_module` | `config.settings` | `config.settings` | `config.settings` | `config.settings.base` | `tests.settings` | `config.settings.base` |

> ¹ Deviates from convention — migration tracked in §5.
> ² Health endpoint migration to `/healthz/` tracked in §5.

### 2.4 deploy-remote.sh Defaults

The deploy script lives at `platform/deployment/scripts/deploy-remote.sh` and is synced to the VM by `_deploy-hetzner.yml`. Key defaults that projects must be aware of:

| Parameter | Default | Override flag |
| --- | --- | --- |
| `DEPLOY_DIR` | `/srv/<app>` ⚠️ (not `/opt/`) | `--deploy-dir` (always pass explicitly!) |
| `HEALTH_ENDPOINT` | `/healthz/` | `--health-endpoint` |
| `WEB_SERVICE` | `<app>-web` | `--web-service` |
| `COMPOSE_FILE` | `docker-compose.prod.yml` | `--compose-file` |
| `ENV_FILE` | `.env.prod` | `--env-file` |
| `HEALTH_RETRIES` | 12 | `--health-retries` |
| `HEALTH_INTERVAL` | 5s | `--health-interval` |

**Worker restart**: The script auto-restarts `<app>-worker` if it exists, but does **NOT** restart beat or custom services like `weltenhub-celery`, `weltenhub-beat`. These must be handled via compose dependency chains or manual restart.

### 2.5 CI/CD: Three-Stage Platform Pipeline

Every project uses the same three reusable workflows from `achimdehnert/platform`:

```yaml
# .github/workflows/ci-cd.yml — canonical template
name: CI/CD Pipeline

permissions:
  contents: read
  packages: write

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      skip_tests:
        description: "Skip tests (emergency only)"
        required: false
        default: false
        type: boolean

jobs:
  ci:
    name: "CI"
    uses: achimdehnert/platform/.github/workflows/_ci-python.yml@v1
    with:
      python_version: "3.12"          # per-project
      source_dir: "src"               # per-project
      django_settings_module: "config.settings"  # per-project
      coverage_threshold: 0
      skip_tests: ${{ inputs.skip_tests || false }}
    secrets: inherit

  build:
    name: "Build"
    needs: [ci]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    uses: achimdehnert/platform/.github/workflows/_build-docker.yml@v1
    with:
      dockerfile: "docker/app/Dockerfile"  # per-project
      scan_image: true
    secrets: inherit

  deploy:
    name: "Deploy"
    needs: [build]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    uses: achimdehnert/platform/.github/workflows/_deploy-hetzner.yml@v1
    with:
      app_name: "risk-hub"            # per-project
      deploy_path: "/opt/risk-hub"    # per-project
      health_url: "https://demo.schutztat.de/health/"  # per-project
      compose_file: "docker-compose.prod.yml"
      web_service: "risk-hub-web"     # per-project
      run_migrations: true
      enable_rollback: true
    secrets:
      HETZNER_HOST: ${{ secrets.DEPLOY_HOST }}
      HETZNER_USER: ${{ secrets.DEPLOY_USER }}
      HETZNER_SSH_KEY: ${{ secrets.DEPLOY_SSH_KEY }}
```

### 2.6 Required GitHub Secrets (per repository)

| Secret | Source | Notes |
| --- | --- | --- |
| `GITHUB_TOKEN` | Automatic | GHCR push (packages:write) |
| `DEPLOY_HOST` | `88.198.191.108` | Same for all repos |
| `DEPLOY_USER` | `root` | Same for all repos |
| `DEPLOY_SSH_KEY` | SSH private key | Same key, shared across repos |

> All three `DEPLOY_*` secrets should be set as **organization-level secrets** to avoid per-repo duplication.

### 2.7 Rollback Strategy

| Scenario | Action | Command |
| --- | --- | --- |
| Health check fails after deploy | `deploy-remote.sh` auto-rollback | Automatic (keeps previous image digest) |
| Bad deploy discovered later | Redeploy previous SHA | `docker compose pull && up -d` with previous tag |
| Database migration broke | Manual rollback migration | `docker exec <container> python manage.py migrate <app> <previous_migration>` |

The `_deploy-hetzner.yml` workflow already supports `enable_rollback: true`, which saves the current image digest before deploying and restores it if the health check fails.

### 2.8 Image Tagging Strategy

| Tag | When applied | Purpose |
| --- | --- | --- |
| `latest` | Every push to `main` | Default pull target |
| `<sha7>` | Every push to `main` | Immutable; rollback target |
| `v1.2.3` | Semver git tag | Release marker |

The `_build-docker.yml` workflow auto-generates all three tags via `docker/metadata-action`.

### 2.9 Port Allocation Registry

All projects bind to `127.0.0.1:<port>` on the host. Nginx/Caddy forwards from 443.

| Port | Project | Service |
| --- | --- | --- |
| 8002 | travel-beat | Gunicorn (direct) |
| 8020 | pptx-hub | Gunicorn (planned) |
| 8081 | weltenhub | Gunicorn |
| 8085 | dev-hub | Gunicorn |
| 8088 | bfagent | Caddy → Gunicorn |
| 8089 | travel-beat | Caddy |
| 8090 | risk-hub | Gunicorn |
| 8100 | bfagent | LLM Gateway (internal) |

**Rule**: New projects pick the next available port in the 80xx range. Update this table.

### 2.10 Compose Hardening (MUST for all projects)

The reference template is at `platform/deployment/templates/docker-compose.prod.yml`. All production compose files MUST include:

| Requirement | Why | Example |
| --- | --- | --- |
| `logging.driver: json-file` with `max-size` + `max-file` | Prevents disk-full from unbounded logs | `max-size: "20m"`, `max-file: "5"` |
| `deploy.resources.limits.memory` | Prevents OOM killing other services | `512M` for web, `384M` for worker |
| `healthcheck` on all services | Docker restart + deploy-remote.sh probing | See template |
| `restart: unless-stopped` | Auto-recovery after host reboot | — |
| `shm_size: 128m` for postgres | Prevents "could not resize shared memory" | — |

**Current gaps**: risk-hub, travel-beat, weltenhub, pptx-hub compose files are missing log rotation and/or memory limits. Migration tracked in §5.

### 2.11 Platform Reference Templates

The `platform/deployment/` directory contains production-ready templates:

| File | Purpose |
| --- | --- |
| `templates/docker-compose.prod.yml` | Full compose template with all hardening |
| `templates/django/healthz.py` | `/livez/` + `/healthz/` views (DB, Redis, disk, migrations) |
| `scripts/deploy-remote.sh` | Atomic deploy with backup, migration gate, rollback |
| `workflows/ci.yml` | CI template |
| `workflows/deploy-prod.yml` | Deploy template |

New projects should copy these, not reinvent.

### 2.12 Manual Deploy via MCP Tools

For Windsurf/Cascade-driven deploys outside of CI:

```bash
# 1. Build + Push (local)
docker build -f docker/app/Dockerfile -t ghcr.io/achimdehnert/<repo>:latest .
docker push ghcr.io/achimdehnert/<repo>:latest

# 2. Deploy (via deployment-mcp ssh_manage or direct SSH)
ssh root@88.198.191.108 '
  cd /opt/<repo> &&
  docker compose -f docker-compose.prod.yml pull <web_service> &&
  docker compose -f docker-compose.prod.yml up -d --force-recreate <web_service> <extra_services> &&
  sleep 5 &&
  curl -sf http://127.0.0.1:<host_port>/health/ &&
  docker logs <container> --tail 10
'
```

Substitute parameters from the table in §2.3.

### 2.13 Monitoring After Deploy

| Check | Tool | Interval |
| --- | --- | --- |
| Docker HEALTHCHECK | Built into Dockerfile | 30s |
| HTTP external | Nginx → Gunicorn | On request |
| Container restart policy | `restart: unless-stopped` | Automatic |
| Log inspection | `docker logs` / `deployment-mcp` | On demand |

**Missing (future)**: Uptime monitoring (e.g. Uptime Kuma), centralized logging (e.g. Loki), alerting.

### 2.14 `infra-deploy` Repository — Deployment API for Agents and Humans

**Decision (2026-02-20):** A dedicated `achimdehnert/infra-deploy` repository serves as the single entry point for all deployments — callable by humans, Cascade, and autonomous agents alike.

**Rationale:**

- Isolates deployment secrets (SSH keys, GHCR token) to one repo — not duplicated across all service repos
- Provides a stable `workflow_dispatch` + `repository_dispatch` API that agents can call without code changes
- Enables autonomous rollback: an agent detecting errors can trigger `rollback.yml` without human intervention
- Creates a single audit trail (`deploy.log`) across all services

**Repository structure:**

```text
infra-deploy/
├── .github/workflows/
│   ├── deploy-service.yml      # Trigger: repository_dispatch (from CI) or workflow_dispatch (manual/agent)
│   └── rollback.yml            # Trigger: workflow_dispatch — inputs: service, environment, target_tag
├── scripts/
│   ├── deploy.sh               # Atomic deploy: pull → migrate → up → health-check → rollback on failure
│   └── rollback.sh             # Explicit rollback to previous or named tag
└── README.md
```

**Server state directory** (on 88.198.191.108, gitignored):

```text
/opt/deploy/production/.deployed/
├── <service>.tag               # Currently active image tag
├── <service>.tag.prev          # Previous tag (rollback target)
└── deploy.log                  # Append-only: timestamp | service | old→new | SUCCESS/ROLLBACK
```

**`deploy-service.yml`** — unified trigger:

```yaml
on:
  repository_dispatch:
    types: [deploy-service]     # Triggered by _deploy-trigger.yml from service repos
  workflow_dispatch:
    inputs:
      service:    { required: true }
      image_tag:  { required: true }
      has_migrations: { default: "false" }

concurrency:
  group: deploy-production-${{ github.event.client_payload.service || inputs.service }}
  cancel-in-progress: false     # Never cancel a running deploy

jobs:
  deploy:
    runs-on: [self-hosted, dev-server]
    steps:
      - name: Deploy
        run: |
          ssh -o StrictHostKeyChecking=no root@88.198.191.108 \
            "bash /opt/infra-deploy/scripts/deploy.sh \
              ${{ github.event.client_payload.service || inputs.service }} \
              ${{ github.event.client_payload.image_tag || inputs.image_tag }} \
              ${{ github.event.client_payload.has_migrations || inputs.has_migrations }}"
```

**Relationship to existing `_deploy-hetzner.yml`:**
The existing reusable workflow `_deploy-hetzner.yml` (§2.5) deploys directly via SSH from GitHub-hosted runners. `infra-deploy` is an **additional** entry point — not a replacement. Both coexist:

- `_deploy-hetzner.yml`: used by service repos for standard CI/CD push-triggered deploys
- `infra-deploy/deploy-service.yml`: used by agents, manual overrides, and cross-service orchestration

### 2.15 Fast-Deploy Override Mechanism

**Decision (2026-02-20):** Fast-Deploy (`git pull` + `docker cp` + `gunicorn reload`, ~6s) is retained as an explicit **emergency override** mechanism alongside the standard image-build flow.

**When to use:**

| Scenario | Mechanism | Latency |
| --- | --- | --- |
| Normal push to `main` | CI → Build → `_deploy-hetzner.yml` | ~3-5 min |
| Emergency hotfix (template/view only) | Fast-Deploy via `workflow_dispatch` | ~6s |
| Agent-triggered rollback | `infra-deploy/rollback.yml` | ~15s |
| Manual MCP deploy | `deploy-remote.sh` via SSH | ~30s |

**Fast-Deploy is NOT suitable for:**

- Migrations (no image versioning → no rollback possible)
- Dependency changes (new packages not in container)
- Any change requiring a new Docker image

**Implementation:** Fast-Deploy runs on the self-hosted runner (dev-server, 46.225.113.1) via `workflow_dispatch` only — never auto-triggered on push. Script: `/opt/scripts/deploy.sh <service>`.

### 2.16 Expand-Contract Migrations Convention

**Decision (2026-02-20):** All database migrations MUST follow the Expand-Contract pattern. This is a **convention enforced via PR checklist**, not a CI linter.

**Rule:** Never delete or rename a column in the same release where the code stops referencing it.

| Allowed in one release | NOT allowed in one release |
| --- | --- |
| Add new column (nullable or with default) | DROP COLUMN |
| Add new table | RENAME COLUMN |
| Add/remove index | NOT NULL without default on existing column |
| Data migrations (RunPython) | Type change on existing column |

**Two-release pattern:**

- Release 1: Add `email_v2`, code uses both `email` and `email_v2`
- Release 2: Remove `email`, code uses only `email_v2`

**PR checklist** (add to `.github/pull_request_template.md` in each service repo):

```markdown
- [ ] DB migrations follow Expand-Contract (no DROP/RENAME in same release as code change)
- [ ] `python manage.py makemigrations --check` shows no missing migrations
- [ ] Migration is backwards-compatible (old code works with new DB schema)
```

**Rationale:** The `KeyError: 'last_verified'` incident (2026-02-20, dev-hub) was caused by a container-generated migration removing a field that the repo migration chain still referenced. Expand-Contract prevents this class of error.

## 3. What Is Legitimately Project-Specific

Not every difference is an inconsistency. These vary by design:

| Aspect | Example | Why |
| --- | --- | --- |
| System deps | risk-hub/travel-beat need WeasyPrint (pango, cairo) | PDF rendering |
| Reverse proxy sidecar | bfagent/travel-beat include Caddy in compose | Static files, auto-TLS for subdomains |
| Worker process | Celery (travel-beat, weltenhub), django-q2 (pptx-hub), Celery (risk-hub) | Async architecture choice |
| Shared vs own DB | weltenhub shares `bfagent_db`; others self-contained | Coupling decision |
| Python version | bfagent still on 3.11 | Migration planned |
| Extra build steps | bfagent builds Sphinx docs in Docker | Documentation delivery |

## 4. Current State (as of 2026-02-20)

| Project | CI/CD via platform workflows | Auto-deploy | Fast-Deploy | Windsurf `/deploy` |
| --- | --- | --- | --- | --- |
| bfagent | ❌ custom (3 workflow files) | ✅ on push to main | ❌ | ✅ |
| risk-hub | ✅ migrated | ✅ on push to main | ❌ | ✅ |
| travel-beat | ✅ reference implementation | ✅ on push to main | ❌ | ✅ |
| weltenhub | ✅ migrated | ✅ on push to main | ❌ | ✅ |
| pptx-hub | ❌ CI-only (test + PyPI) | ❌ not deployed | ❌ | ✅ created |
| dev-hub | ✅ fast-deploy only (§2.15) | ✅ on push to main | ✅ (~6s) | ✅ |

## 5. Remaining Migration Tasks

### Priority 0 — Amendment 2026-02-20 (new)

- [ ] Create `achimdehnert/infra-deploy` repo with `deploy-service.yml`, `rollback.yml`, `deploy.sh`, `rollback.sh` (§2.14)
- [ ] Add `_deploy-trigger.yml` reusable workflow to `platform/.github/workflows/` (§2.14)
- [ ] Add `.github/pull_request_template.md` with Expand-Contract checklist to all service repos (§2.16)
- [ ] dev-hub: Migrate Fast-Deploy to `workflow_dispatch`-only trigger; add standard CI/CD build flow (§2.15)

### Priority 1 — Functional gaps

- [ ] **Health endpoints**: All projects must implement `/livez/` + `/healthz/` using `platform/deployment/templates/django/healthz.py`
- [ ] **risk-hub**: Add `/healthz/` endpoint (currently `/` returns HTML, not JSON health)
- [ ] **travel-beat**: Rename `/health/` → `/healthz/`
- [ ] **weltenhub**: Rename `/health/` → `/healthz/`
- [ ] bfagent: Migrate 3 workflow files → single `ci-cd.yml` using platform workflows
- [ ] pptx-hub: First server deployment (provision `/opt/pptx-hub`, Nginx config)

### Priority 2 — Compose hardening (operational risk)

- [ ] risk-hub: Add `logging` (json-file with rotation) to all services
- [ ] risk-hub: Add `deploy.resources.limits.memory` to all services
- [ ] travel-beat: Add `logging` + `deploy.resources` to compose
- [ ] weltenhub: Add `logging` + `deploy.resources` to compose
- [ ] pptx-hub: Add `logging` + `deploy.resources` to compose
- [ ] deploy-remote.sh: Change default `DEPLOY_DIR` from `/srv/` to `/opt/`
- [ ] deploy-remote.sh: Add `--extra-services` flag for beat/celery restart

### Priority 3 — Convention alignment (non-breaking)

- [ ] bfagent: Move `Dockerfile` → `docker/app/Dockerfile`
- [ ] weltenhub: Move `Dockerfile` → `docker/app/Dockerfile`
- [ ] travel-beat: Move `deploy/docker-compose.prod.yml` → root
- [ ] travel-beat: Rename compose service `web` → `travel-beat-web`
- [ ] bfagent + risk-hub: Add non-root user to Dockerfile
- [ ] All: Adopt multi-stage build pattern (weltenhub is reference)

### Priority 4 — Platform improvements

- [ ] Move `DEPLOY_*` secrets to GitHub organization level
- [ ] Add Uptime Kuma monitoring for all `/healthz/` endpoints
- [ ] Create `platform/deployment/templates/Dockerfile` as reference
- [ ] Formalize Nginx config management (currently manual on server)

## 6. Consequences

**Benefits**:

- **Single source of truth**: Platform workflows updated once, all projects benefit
- **Zero re-discovery**: AI assistants and developers find all parameters in §2.3
- **Consistent rollback**: Same mechanism across all projects
- **Faster onboarding**: New project = copy template + fill 6 parameters

**Trade-offs**:

- **Coupling**: Platform workflow bug affects all projects → mitigated by `@v1` version pinning
- **Migration effort**: ~30min per project for CI workflow swap (one-time)

**Risks**:

- GitHub Actions reusable workflow limitations (e.g. cannot pass `env:` blocks) → already handled by `secrets: inherit`
- Server single point of failure → out of scope for this ADR; see ADR-008
- **Shared DB risk**: weltenhub shares `bfagent_db` — concurrent migrations from separate deploys could conflict. Mitigation: deploy-remote.sh uses file locking, but only per-app.
- **Zero-downtime gap**: `force-recreate` causes ~2-5s of downtime. Acceptable for current scale. For future: consider blue-green via compose profiles.
