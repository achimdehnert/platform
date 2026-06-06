---
status: accepted
date: 2026-02-10
amended: 2026-06-01
decision-makers: [Achim Dehnert]
consulted: []
informed: []
implementation_status: implemented
implementation_evidence:
  - "Base pipeline (Option 2+3, §2.1–2.16): implemented since 2026-02, in production on the Hetzner VM."
  - "§2.17 fail-loud (platform #391, main f29590a, 2026-06-01): _deploy-unified.yml hard-fails on absent docker-compose.prod.yml."
  - "§2.17 atomic sync + compose_sha verify (platform #399, main 891c803, 2026-06-01): CI writes .deploy-manifest.json; deploy.sh verifies sha256 before compose up (fail-closed)."
  - "§2.18 ownership labels (platform #395, main 0de5934, 2026-06-01): deploy.sh stamps iil.* labels on all containers."
  - "§2.19 prod COMPOSE_PROJECT_NAME pin (platform #398, main 0e979a5, 2026-06-01): explicit pin matches pre-existing implicit value (verified via docker compose ls on prod)."
  - "§2.20 intent-token + break-glass (platform #399, main 891c803, 2026-06-01): prod deploys require CI manifest; manual deploys need --break-glass with audit log."
  - "deploy.sh synced to /opt/scripts/deploy.sh on prod 88.198.191.108 (2026-06-01, md5 fc4da539)."
  - "Deferred (§5 backlog, not part of accepted amendment): atomic host-state reconcile / retire-tombstones (§2.20 REC-5)."
---

# Adopt unified single-service deployment pipeline for all platform projects

> **Amendment 2026-02-20**: Added §2.14 (`infra-deploy` repo as Agent-API), §2.15 (Fast-Deploy Override), §2.16 (Expand-Contract Migrations Convention), updated §2.3 (dev-hub added), §2.9 (port registry updated), §4 (current state updated).
> **Amendment 2026-02-22**: Added coach-hub to §2.3 (port 8007, domain kiohnerisiko.de), §4 current state updated.
> **Amendment 2026-06-01 (accepted; source KONZ-platform-001):** Added §2.17 (Verified Deploy-Bundle Contract — fail-closed config sync), §2.18 (Container Ownership Labels), §2.19 (Compose Project-Name Pinning for prod), §2.20 (Single Enforced Deploy Path). Closes the **silent-config-sync drift class**: `_deploy-unified.yml` syncs the compose file only `if hashFiles('docker-compose.prod.yml') != ''`; when absent the step is silently skipped and `deploy.sh` runs against the stale host compose — a service removed in the repo survives on prod (Discord-Bot crash-loop incident 2026-06-01).

---

## Context and Problem Statement

Five Django projects deploy to one Hetzner VM. Each evolved its own CI/CD pipeline independently, creating **unnecessary cognitive load** and **fragile, inconsistent automation**:

- 3 different Dockerfile locations, 2 compose-file locations, 3 health-endpoint paths
- Only 1 of 5 projects uses the existing platform reusable workflows
- 2 projects have no auto-deploy at all (risk-hub: build-only, weltenhub: stub)
- No documented rollback, no image-tagging strategy, no secrets inventory

**Cost of status quo**: Every deploy requires re-discovering project-specific details. AI assistants re-probe server layout on every invocation. Workflow bugs are fixed per-repo instead of once.

---

## Decision Drivers

* **Operational efficiency**: Reduce per-deploy cognitive load for a 1–3 person team
* **Consistency**: One rollback mechanism, one health-check convention, one secrets pattern
* **AI-agent compatibility**: Agents must find all deploy parameters without probing the server
* **Budget constraint**: Single Hetzner VPS — no Kubernetes, no expensive SaaS tooling
* **Security**: No secrets in code or config files; SSH-key auth only
* **Maintainability**: Fix a workflow bug once in `platform`, all projects benefit

---

## Considered Options

1. **Status quo** — keep per-project ad-hoc pipelines
2. **Unified platform reusable workflows** (`_ci-python.yml`, `_build-docker.yml`, `_deploy-hetzner.yml`) — all projects adopt the same three-stage pipeline
3. **`infra-deploy` central repository** — dedicated repo acts as deployment API for agents and cross-repo orchestration (extends Option 2)
4. **Kamal (formerly MRSK)** — Rails-ecosystem deploy tool, SSH-based, zero-downtime
5. **Traefik v3 as reverse proxy** — replace Nginx with automatic service discovery and Let's Encrypt

---

## Decision Outcome

**Chosen option: Option 2 + Option 3 (combined)**, because:

- Option 2 eliminates per-project CI/CD drift with minimal migration effort (~30 min/project).
- Option 3 adds a stable API surface for AI agents and manual overrides without replacing the existing CI/CD flow.
- Option 4 (Kamal) introduces a Ruby dependency and opinionated conventions that conflict with existing Docker Compose setup.
- Option 5 (Traefik) is deferred — Nginx is already working and the migration risk is not justified at current scale (see §2.10).

The two options are **additive**: `_deploy-hetzner.yml` handles push-triggered CI/CD; `infra-deploy` handles agent-triggered and manual deploys.

### Confirmation

Compliance is verified by:

1. **CI check**: Each service repo's `ci-cd.yml` references `achimdehnert/platform/.github/workflows/_ci-python.yml@v1` — reviewable in GitHub Actions tab.
2. **Migration table**: §5 tracks each project's migration status; items are closed when the PR merges.
3. **Health endpoint test**: `curl -sf https://<domain>/healthz/` returns `{"status": "ok"}` — verified post-deploy by `deploy-remote.sh`.
4. **Architecture Guardian** (`.github/workflows/guardian.yml`): checks new workflow files for platform-workflow usage on every PR.

### Consequences

* Good, because a single platform workflow fix propagates to all projects automatically.
* Good, because AI agents find all deploy parameters in §2.3 without server probing.
* Good, because rollback is consistent and tested across all projects.
* Good, because new projects are onboarded in ~30 min (copy template + fill 6 parameters).
* Bad, because a platform workflow bug now affects all projects simultaneously — mitigated by `@v1` version pinning.
* Bad, because the one-time migration effort per project (~30 min) must be scheduled.
* Bad, because shared DB between weltenhub and bfagent creates concurrent-migration risk — mitigated by deploy-remote.sh file locking (per-app only).

---

## Pros and Cons of the Options

### Option 1 — Status quo (per-project ad-hoc pipelines)

* Good, because zero migration effort.
* Good, because project-specific quirks are already handled.
* Bad, because every workflow bug must be fixed in 5+ places.
* Bad, because AI agents must re-probe server layout on every invocation.
* Bad, because no consistent rollback mechanism exists.

### Option 2 — Unified platform reusable workflows

* Good, because single source of truth for CI/CD logic.
* Good, because rollback, health checks, and image tagging are standardised.
* Good, because secrets are managed once (org-level GitHub secrets).
* Bad, because projects with non-standard layouts (bfagent, travel-beat) require migration.
* Bad, because reusable workflow limitations (no `env:` block passthrough) require workarounds.

### Option 3 — `infra-deploy` central repository (extends Option 2)

* Good, because agents and manual operators have a single entry point.
* Good, because secrets (SSH key) are isolated in one repo, not scattered across 5+.
* Good, because `repository_dispatch` enables cross-repo orchestration.
* Bad, because adds one more repo to maintain.
* Bad, because self-hosted runner on dev-server must stay registered and healthy.

### Option 4 — Kamal

* Good, because zero-downtime blue-green deploys out of the box.
* Good, because simple CLI interface.
* Bad, because requires Ruby runtime on CI and server.
* Bad, because opinionated conventions conflict with existing Docker Compose setup.
* Bad, because team has no Ruby expertise — operational risk at 3 AM.

### Option 5 — Traefik v3 as reverse proxy

* Good, because automatic TLS and service discovery reduce manual Nginx config.
* Good, because native Docker label-based routing fits compose setup.
* Bad, because Nginx is already working and battle-tested on this server.
* Bad, because migration risk is not justified at current scale.
* Bad, because Traefik's dynamic config model requires learning curve for small team.

---

## More Information

- **Related ADRs**: ADR-008 (infrastructure), ADR-022 (code quality tooling), ADR-042 (dev environment deploy workflow), ADR-045 (secrets/SOPS)
- **Traefik decision**: Deferred to a future ADR. Nginx retained consciously (see §2.10).
- **SSH as root**: Conscious decision documented in §2.1.
- **Migration tracking**: §5 lists all open migration tasks with priority.

---

## 2. Implementation Details

### 2.1 Infrastructure Constants

| Constant | Value |
| --- | --- |
| Server | `88.198.191.108` (Hetzner VM) |
| SSH user | `root` |
| Registry | `ghcr.io/achimdehnert/` |
| Reverse proxy | Nginx + Let's Encrypt |
| Deploy pattern | Build → Push GHCR → SSH pull → force-recreate |
| Internal app port | `8000` (Gunicorn) |
| Env file on server | `.env.prod` (never committed) |

> **SSH as root — conscious decision**: The Hetzner VM is a single-tenant server. Using `root` avoids `sudo` complexity in deploy scripts. Risk is mitigated by: SSH-key-only auth (password disabled), firewall restricting port 22 to known IPs. A future ADR may introduce a dedicated `deploy` user if the team grows.

### 2.2 Conventions (MUST for new projects, SHOULD for existing)

| Convention | Standard | Rationale |
| --- | --- | --- |
| Dockerfile | `docker/app/Dockerfile` | Separates infra from app code |
| Compose | `docker-compose.prod.yml` (root) | Predictable, one level |
| Health endpoints | `/livez/` + `/healthz/` | Matches `deploy-remote.sh` default + platform template |
| Image name | `ghcr.io/achimdehnert/<repo>:<tag>` | Flat; no nested sub-images |
| Image tags | `latest` + git SHA short (7 chars) | Rollback by SHA, default by latest |
| Server path | `/opt/<repo>` | Exception: bfagent → `/opt/bfagent-app` (legacy) |
| Service naming | `<repo>-web`, `<repo>-worker`, `<repo>-beat` | Compose services follow repo name |
| Container naming | `<repo_underscored>_web` | e.g. `risk_hub_web` |
| Non-root user | Required in Dockerfile | Security; `USER <appname>` |
| HEALTHCHECK | Required in Dockerfile | `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/livez/')"` |
| Multi-stage build | Recommended | Smaller images, no build tools in prod |
| SSH known hosts | Use `ssh-keyscan` | Never use `StrictHostKeyChecking=no` — use `ssh-keyscan 88.198.191.108 >> ~/.ssh/known_hosts` |

### 2.3 Per-Project Parameters (the only things that vary)

| Parameter | bfagent | risk-hub | travel-beat | weltenhub | pptx-hub | dev-hub | coach-hub |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `deploy_via` | `_deploy-hetzner.yml` | `_deploy-hetzner.yml` | `_deploy-hetzner.yml` | `_deploy-hetzner.yml` | `_deploy-hetzner.yml` | `infra-deploy` | `_deploy-hetzner.yml` |
| `deploy_path` | `/opt/bfagent-app` | `/opt/risk-hub` | `/opt/travel-beat` | `/opt/weltenhub` | `/opt/pptx-hub` | `/opt/dev-hub` | `/opt/coach-hub` |
| `dockerfile` | `Dockerfile` ¹ | `docker/app/Dockerfile` | `docker/Dockerfile` ¹ | `Dockerfile` ¹ | `docker/app/Dockerfile` | `docker/Dockerfile` | `docker/app/Dockerfile` |
| `compose_file` | `docker-compose.prod.yml` | `docker-compose.prod.yml` | `deploy/docker-compose.prod.yml` ¹ | `docker-compose.prod.yml` | `docker-compose.prod.yml` | `docker-compose.prod.yml` | `docker-compose.prod.yml` |
| `health_url` | `https://bfagent.iil.pet/healthz/` | `https://demo.schutztat.de/healthz/` ² | `https://drifttales.com/healthz/` ² | `https://weltenforger.com/healthz/` ² | *not deployed* | `https://devhub.iil.pet/livez/` | `https://kiohnerisiko.de/healthz/` |
| `web_service` | `bfagent-web` | `risk-hub-web` | `web` ¹ | `weltenhub-web` | `web` | `devhub-web` | `coach-hub-web` |
| `extra_services` | — | `risk-hub-worker` | `celery` | `weltenhub-celery weltenhub-beat` | `worker` | `devhub-celery devhub-beat` | `coach-hub-worker coach-hub-beat` |
| `container` | `bfagent_web` | `risk_hub_web` | `travelbeat_web` | `weltenhub_web` | `pptx_hub_web` | `devhub_web` | `coach_hub_web` |
| `host_port` | 8091 | 8090 | 8002 | 8081 | 8020 | 8085 | 8007 |
| `database` | shared (`bfagent_db`) | own stack | own stack | shared (`bfagent_db`) | own stack | shared (`bfagent_db`) | own stack |
| `python` | 3.11 | 3.12 | 3.12 | 3.12 | 3.12 | 3.12 | 3.12 |
| `source_dir` | `.` | `src` | `apps` | `apps` | `src` | `.` | `apps` |
| `settings_module` | `config.settings` | `config.settings` | `config.settings` | `config.settings.base` | `tests.settings` | `config.settings.base` | `config.settings.base` |

> ¹ Deviates from convention — migration tracked in §5.
> ² Health endpoint migration to `/healthz/` tracked in §5.

### 2.4 deploy-remote.sh Defaults

| Parameter | Default | Override flag |
| --- | --- | --- |
| `DEPLOY_DIR` | `/srv/<app>` ⚠️ (not `/opt/`) | `--deploy-dir` (always pass explicitly!) |
| `HEALTH_ENDPOINT` | `/healthz/` | `--health-endpoint` |
| `WEB_SERVICE` | `<app>-web` | `--web-service` |
| `COMPOSE_FILE` | `docker-compose.prod.yml` | `--compose-file` |
| `ENV_FILE` | `.env.prod` | `--env-file` |
| `HEALTH_RETRIES` | 12 | `--health-retries` |
| `HEALTH_INTERVAL` | 5s | `--health-interval` |

### 2.5 Three-Stage CI/CD Pipeline

```yaml
# .github/workflows/ci-cd.yml (per-project)
jobs:
  ci:
    uses: achimdehnert/platform/.github/workflows/_ci-python.yml@v1
  build:
    needs: [ci]
    uses: achimdehnert/platform/.github/workflows/_build-docker.yml@v1
  deploy:
    needs: [build]
    uses: achimdehnert/platform/.github/workflows/_deploy-hetzner.yml@v1
```

### 2.6 Secrets Inventory

| Secret | Scope | Used by |
| --- | --- | --- |
| `DEPLOY_SSH_KEY` | Org-level (target) | `_deploy-hetzner.yml` |
| `DEPLOY_HOST` | Org-level | `_deploy-hetzner.yml` |
| `DEPLOY_USER` | Org-level | `_deploy-hetzner.yml` |
| `GHCR_TOKEN` / `GITHUB_TOKEN` | Auto (Actions) | `_build-docker.yml` |

### 2.7 Rollback Procedure

```bash
# 1. Identify last good SHA
docker images ghcr.io/achimdehnert/<repo> --format "{{.Tag}}"

# 2. Deploy specific SHA
cd /opt/<repo>
IMAGE_TAG=sha-abc1234 docker compose -f docker-compose.prod.yml up -d --force-recreate <web_service>

# 3. Verify
curl -sf http://127.0.0.1:<host_port>/healthz/
```

### 2.8 DeployLock Safety

Each deploy acquires a file lock at `/tmp/deploy-<app>.lock` to prevent concurrent deploys of the same app. Lock is released on exit (success or failure).

### 2.9 Port Registry

| Port | App | Domain |
| --- | --- | --- |
| 8007 | coach-hub | coach-hub.iil.pet |
| 8017 | coach-hub (staging) | staging.coach-hub.iil.pet |
| 8020 | pptx-hub | prezimo.de |
| 8081 | weltenhub | weltenforger.com |
| 8085 | dev-hub | devhub.iil.pet |
| 8088 | trading-hub | trading-hub.iil.pet |
| 8089 | travel-beat | drifttales.com |
| 8090 | risk-hub | schutztat.de |
| 8091 | bfagent | bfagent.iil.pet |
| 8092 | billing-hub | billing.iil.pet |
| 8093 | wedding-hub | wedding-hub.iil.pet |
| 8094 | cad-hub | nl2cad.de |
| 8095 | 137-hub | 137herz.de |
| 8096 | illustration-hub | illustration.iil.pet |
| 8097 | writing-hub | writing.iil.pet |
| 8098 | writing-hub (staging) | staging.writing.iil.pet |
| 8099 | tax-hub | tax.iil.pet |
| 8100 | learn-hub | learn.iil.pet |
| 8101 | ausschreibungs-hub | bieterpilot.de |
| 8102 | doc-hub (paperless) | docs.iil.pet |
| 8103 | recruiting-hub | hr.iil.pet |
| 8104 | research-hub | research.iil.pet |
| 8107 | dms-hub | dms.iil.pet |
| 8108 | onboarding-hub (Schulungspass) | schulungspass.de |

**Canonical source**: `platform/infra/ports.yaml`. Next free port: **8109**.

**Rule**: New projects pick the next available port in the 80xx range. Update `ports.yaml` first, then this table.

### 2.10 Reverse Proxy: Nginx (Conscious Decision)

**Decision**: Nginx is retained. Traefik v3 was evaluated but deferred.

**Rationale**: Nginx is already operational with Let's Encrypt TLS on all domains. Migration to Traefik would require reconfiguring all virtual hosts — significant risk for a small team with no downtime budget. If the service count grows beyond ~10 or multi-VM deployment is needed, Traefik v3 should be re-evaluated in a dedicated ADR.

### 2.11 Compose Hardening (MUST for all projects)

| Requirement | Why | Example |
| --- | --- | --- |
| `logging.driver: json-file` with `max-size` + `max-file` | Prevents disk-full | `max-size: "20m"`, `max-file: "5"` |
| `deploy.resources.limits.memory` | Prevents OOM | `512M` for web, `384M` for worker |
| `healthcheck` on all services | Docker restart + deploy probing | See platform template |
| `restart: unless-stopped` | Auto-recovery after host reboot | — |
| `shm_size: 128m` for postgres | Prevents shared memory errors | — |

### 2.12 Manual Deploy via MCP Tools

```bash
# 1. Build + Push (local)
docker build -f docker/app/Dockerfile -t ghcr.io/achimdehnert/<repo>:latest .
docker push ghcr.io/achimdehnert/<repo>:latest

# 2. Deploy via SSH
ssh root@88.198.191.108 '
  cd /opt/<repo> &&
  docker compose -f docker-compose.prod.yml pull <web_service> &&
  docker compose -f docker-compose.prod.yml up -d --force-recreate <web_service> &&
  sleep 5 &&
  curl -sf http://127.0.0.1:<host_port>/healthz/ &&
  docker logs <container> --tail 10
'
```

### 2.13 Monitoring After Deploy

| Check | Tool | Interval |
| --- | --- | --- |
| Docker HEALTHCHECK | Built into Dockerfile | 30s |
| HTTP external | Nginx → Gunicorn | On request |
| Container restart policy | `restart: unless-stopped` | Automatic |
| Log inspection | `docker logs` / `deployment-mcp` | On demand |

### 2.14 `infra-deploy` Repository as Deployment API

**Decision (2026-02-20):** A dedicated `achimdehnert/infra-deploy` repository acts as the single entry point for agent-triggered and manually-orchestrated deployments.

**Repository structure:**

```text
achimdehnert/infra-deploy/
├── .github/workflows/
│   ├── deploy-service.yml
│   └── rollback.yml
├── scripts/
│   ├── deploy.sh
│   └── rollback.sh
└── README.md
```

**`deploy-service.yml`:**

```yaml
on:
  repository_dispatch:
    types: [deploy-service]
  workflow_dispatch:
    inputs:
      service:    { required: true }
      image_tag:  { required: true }
      has_migrations: { default: "false" }

concurrency:
  group: deploy-production-${{ github.event.client_payload.service || inputs.service }}
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: [self-hosted, dev-server]
    steps:
      - name: Add server to known hosts
        run: ssh-keyscan 88.198.191.108 >> ~/.ssh/known_hosts

      - name: Deploy
        run: |
          ssh root@88.198.191.108 \
            "bash /opt/infra-deploy/scripts/deploy.sh \
              ${{ github.event.client_payload.service || inputs.service }} \
              ${{ github.event.client_payload.image_tag || inputs.image_tag }} \
              ${{ github.event.client_payload.has_migrations || inputs.has_migrations }}"
```

**Relationship to `_deploy-hetzner.yml`**: Both coexist and are additive. `_deploy-hetzner.yml` handles push-triggered CI/CD; `infra-deploy` handles agent-triggered and manual deploys.

### 2.15 Fast-Deploy Override Mechanism

**Decision (2026-02-20):** Fast-Deploy is retained as an explicit **emergency override** mechanism.

| Scenario | Mechanism | Latency |
| --- | --- | --- |
| Normal push to `main` | CI → Build → `_deploy-hetzner.yml` | ~3-5 min |
| Emergency hotfix (template/view only) | Fast-Deploy via `workflow_dispatch` | ~6s |
| Agent-triggered rollback | `infra-deploy/rollback.yml` | ~15s |
| Manual MCP deploy | `deploy-remote.sh` via SSH | ~30s |

**Fast-Deploy is NOT suitable for**: migrations, dependency changes, or any change requiring a new Docker image. Runs on self-hosted runner via `workflow_dispatch` only — never auto-triggered on push.

### 2.16 Expand-Contract Migrations Convention

**Decision (2026-02-20):** All DB migrations MUST follow the Expand-Contract pattern. Enforced via PR checklist, not CI linter.

| Allowed in one release | NOT allowed in one release |
| --- | --- |
| Add new column (nullable or with default) | DROP COLUMN |
| Add new table | RENAME COLUMN |
| Add/remove index | NOT NULL without default on existing column |
| Data migrations (RunPython) | Type change on existing column |

**PR checklist** (add to `.github/pull_request_template.md`):

```markdown
- [ ] DB migrations follow Expand-Contract (no DROP/RENAME in same release as code change)
- [ ] `python manage.py makemigrations --check` shows no missing migrations
- [ ] Migration is backwards-compatible (old code works with new DB schema)
```

---

### 2.17 Verified Deploy-Bundle Contract (Amendment 2026-06-01)

> Closes the silent-config-sync drift class. Source: KONZ-platform-001 REC-1'.

The deployed compose state on the host MUST be a verified copy of the CI-built artifact — never "whatever stale file is on the server".

- **One shared resolution.** The reusable workflow and `deploy.sh` MUST select the compose file via the **same** resolution logic. Divergent fallbacks are forbidden.
- **No silent fallback in prod.** A prod deploy REQUIRES an explicit `docker-compose.prod.yml` (staging: `docker-compose.staging.yml`). If it is absent, the deploy **fails loud** — it MUST NOT silently fall back to the host's existing compose file. (Current bug: `_deploy-unified.yml` sync step is guarded by `if hashFiles('docker-compose.prod.yml') != ''`, which silently no-ops.) Staging and prod topologies MAY legitimately differ; each environment resolves its own env-specific file and fails loud if that file is absent — never cross-falling-back to the other or to the bare `docker-compose.yml`. *(External review round 2, AD-12.)*
- **Transition / fallback policy (gated rollout).** The fail-loud switch MUST NOT break repos that currently rely on the `docker-compose.yml` fallback in prod. Before flipping enforcement: (1) a migration sweep adds an explicit `docker-compose.prod.yml` to every prod-deploying repo (tracked in §5), OR (2) the rollout explicitly decides the bare `docker-compose.yml` remains a permitted prod source and is then *synced like* the env-specific file (same bundle contract). Enforcement is gated on that decision + the sweep — not flipped unilaterally. *(External review round 2, AD-2 — the one finding beyond round 1.)*
- **Atomic sync.** Upload to a temp path → verify `sha256` → atomic `rename`. No partial/in-place overwrite.
- **Fail-closed host verify.** Before `docker compose up`, `deploy.sh` MUST verify the on-host compose `sha256` equals the `compose_sha` of the current CI bundle. Mismatch ⇒ abort (fail-closed), no deploy.
- **Bundle completeness.** Referenced side-artifacts (`env_file`, override/include/profile files, build context) are part of the bundle, OR the bundle manifest marks each explicitly as host-owned.

### 2.18 Container Ownership Labels (Amendment 2026-06-01)

> Source: KONZ-platform-001 REC-NEU-A. Makes the host auditable without name-guessing.

Every container created by `deploy.sh` MUST carry labels: `iil.repo`, `iil.service`, `iil.environment`, `iil.commit_sha`, `iil.compose_sha`, `iil.deploy_run_id`, `iil.deployed_at`. Audits, health checks and any future reconcile MUST key on these labels — never on container-name heuristics (the name-only heuristic is exactly what hid the orphaned Discord-Bot).

### 2.19 Compose Project-Name Pinning for Prod (Amendment 2026-06-01)

> Source: KONZ-platform-001 REC-NEU-B.

`--remove-orphans` only removes containers of the **same** `COMPOSE_PROJECT_NAME`. `deploy.sh` currently sets `COMPOSE_PROJECT_NAME` only for staging (`staging-${APP_NAME}`); prod relies on the implicit directory-derived name. **Prod MUST pin `COMPOSE_PROJECT_NAME` explicitly** (e.g. `${APP_NAME}`) and the script MUST fail if the running project name diverges from the expected one — otherwise a path/project-name change strands old containers despite a fresh compose.

### 2.20 Single Enforced Deploy Path (Amendment 2026-06-01)

> Source: KONZ-platform-001 REC-3'. Convention alone is insufficient (a manual SSH deploy bypasses Branch Protection).

- The canonical reusable workflow is the **only** sanctioned prod deploy path. Bespoke per-repo deploy jobs are retired, OR lifted into a **certified multi-service profile** — which MUST define: allowed compose files, project-name rule, service ownership, retire process, health checks, and a **re-certification expiry** (no permanent exception drawer).
- **Host-side enforcement:** `deploy.sh` runs prod only with a fresh CI-issued deploy-intent (`commit` + `run_id` + `compose_sha`). Manual deploys require `--break-glass` with a reason, expiry and audit-log entry.
- **Explicitly out of scope:** a standalone drift-detection dashboard (it would become a second source of truth competing with the host). **Deferred:** continuous host-state reconcile (an `expected-services` set *derived* from the last accepted bundle, never hand-maintained) — see KONZ-platform-001 REC-5' and its Kill-Gate.

**Implementation note (v1 spine first):** §2.17 + §2.18 + §2.19 are the structural v1; §2.20 host-intent-token and the broadened state safety-net follow; reconcile/tombstones stay deferred. Status of this amendment: **Accepted 2026-06-01**; implementation pending (§5 Priority-0).

---

## 3. What Is Legitimately Project-Specific

| Aspect | Example | Why |
| --- | --- | --- |
| System deps | risk-hub/travel-beat need WeasyPrint | PDF rendering |
| Reverse proxy sidecar | bfagent/travel-beat include Caddy | Static files, auto-TLS |
| Worker process | Celery (travel-beat, weltenhub, risk-hub, coach-hub), django-q2 (pptx-hub) | Async architecture choice |
| Shared vs own DB | weltenhub shares `bfagent_db`; others self-contained | Coupling decision |
| Python version | bfagent still on 3.11 | Migration planned |
| Extra build steps | bfagent builds Sphinx docs in Docker | Documentation delivery |

---

## 4. Current State (as of 2026-02-22)

| Project | CI/CD via platform workflows | Auto-deploy | Fast-Deploy | Windsurf `/deploy` |
| --- | --- | --- | --- | --- |
| bfagent | ❌ custom (3 workflow files) | ✅ on push to main | ❌ | ✅ |
| risk-hub | ✅ migrated | ✅ on push to main | ❌ | ✅ |
| travel-beat | ✅ reference implementation | ✅ on push to main | ❌ | ✅ |
| weltenhub | ✅ migrated | ✅ on push to main | ❌ | ✅ |
| pptx-hub | ❌ CI-only (test + PyPI) | ❌ not deployed | ❌ | ✅ created |
| dev-hub | ✅ fast-deploy only (§2.15) | ✅ on push to main | ✅ (~6s) | ✅ |
| coach-hub | ⬜ not started | ⬜ not started | ❌ | ⬜ pending |

### `_deploy-hetzner.yml` → `infra-deploy` Migration Tracking

| Service | Currently uses | Target | Status | Notes |
| --- | --- | --- | --- | --- |
| bfagent | custom 3-file workflow | `_deploy-hetzner.yml` | 🔴 Not started | Migrate CI first (Priority 1) |
| risk-hub | `_deploy-hetzner.yml` | `_deploy-hetzner.yml` | ✅ Done | No change needed |
| travel-beat | `_deploy-hetzner.yml` | `_deploy-hetzner.yml` | ✅ Done | No change needed |
| weltenhub | `_deploy-hetzner.yml` | `_deploy-hetzner.yml` | ✅ Done | No change needed |
| pptx-hub | CI-only | `_deploy-hetzner.yml` | 🔴 Not started | Needs server provisioning first |
| dev-hub | fast-deploy | `infra-deploy` | 🟡 In progress | ADR-021 §2.14 target |
| coach-hub | — | `_deploy-hetzner.yml` | 🔴 Not started | New project — onboarding pending |

---

## 5. Remaining Migration Tasks

### Priority 0 — Amendment 2026-02-20 (new)

- [ ] Create `achimdehnert/infra-deploy` repo with `deploy-service.yml`, `rollback.yml`, `deploy.sh`, `rollback.sh` (§2.14)
- [ ] Add `_deploy-trigger.yml` reusable workflow to `platform/.github/workflows/` (§2.14)
- [ ] Add `.github/pull_request_template.md` with Expand-Contract checklist to all service repos (§2.16)
- [ ] dev-hub: Migrate Fast-Deploy to `workflow_dispatch`-only trigger; add standard CI/CD build flow (§2.15)

### Priority 0 — Amendment 2026-02-22 (new)

- [ ] coach-hub: Provision `/opt/coach-hub` on server
- [ ] coach-hub: Nginx config + SSL for `kiohnerisiko.de`
- [ ] coach-hub: CI/CD pipeline setup (`ci-cd.yml`)
- [ ] coach-hub: Register in Windsurf `/deploy` workflow

### Priority 0 — Amendment 2026-06-01 (new — Verified Deploy-Bundle Contract)

> v1 spine first (§2.17 + §2.18 + §2.19); §2.20 host-intent-token follows. Source: KONZ-platform-001.

- [ ] **Migration sweep (gate for fail-loud, §2.17):** add an explicit `docker-compose.prod.yml` to every prod-deploying repo, OR decide per-repo that the bare `docker-compose.yml` stays a permitted, synced prod source. mcp-hub first (it has none → triggered the Discord-Bot incident).
- [ ] `_deploy-unified.yml`: replace the silent `if hashFiles('docker-compose.prod.yml')` skip with fail-loud when the required env compose is absent (§2.17)
- [ ] `_deploy-unified.yml` + `deploy.sh`: one shared compose-resolution; atomic sync (temp → sha256 verify → rename) (§2.17)
- [ ] `deploy.sh`: fail-closed host verify — on-host compose `sha256` must equal the CI bundle's `compose_sha` before `docker compose up` (§2.17)
- [ ] `deploy.sh`: stamp ownership labels `iil.{repo,service,environment,commit_sha,compose_sha,deploy_run_id,deployed_at}` on every container (§2.18)
- [ ] `deploy.sh`: pin `COMPOSE_PROJECT_NAME` for **prod** (currently staging-only) + fail on project-name mismatch (§2.19)
- [ ] §2.20 (follow-up): host-side deploy-intent token + `--break-glass`; broadened `docker inspect` state safety-net

### Priority 1 — Functional gaps

- [ ] **Health endpoints**: All projects must implement `/livez/` + `/healthz/`
- [ ] **risk-hub**: Add `/healthz/` endpoint
- [ ] **travel-beat**: Rename `/health/` → `/healthz/`
- [ ] **weltenhub**: Rename `/health/` → `/healthz/`
- [ ] bfagent: Migrate 3 workflow files → single `ci-cd.yml` using platform workflows
- [ ] pptx-hub: First server deployment (provision `/opt/pptx-hub`, Nginx config)

### Priority 2 — Compose hardening (operational risk)

- [ ] risk-hub: Add `logging` (json-file with rotation) + `deploy.resources.limits.memory`
- [ ] travel-beat: Add `logging` + `deploy.resources`
- [ ] weltenhub: Add `logging` + `deploy.resources`
- [ ] pptx-hub: Add `logging` + `deploy.resources`
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

---

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
