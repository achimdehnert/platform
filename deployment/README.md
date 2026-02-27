# Deployment — BF Agent Platform

Production-grade CI/CD for Django + HTMX + Postgres on Hetzner VMs.

## Architecture

```
push main ──► CI (lint/test) ──► Build Image ──► GHCR
                                                   │
                auto (staging)                     │
                ┌──────────────────────────────────┘
                ▼
         deploy-remote.sh on VM
         ┌─────────────────────┐
         │ 1. Save state       │
         │ 2. DB backup        │
         │ 3. Pull new image   │
         │ 4. Migrate (expand) │ ◄── GATE: fail → stop, no restart
         │ 5. Restart service  │
         │ 6. Healthcheck loop │
         │ 7. Rollback on fail │
         └─────────────────────┘

tag v* ──► CI ──► Build ──► GHCR ──► Manual Approval ──► deploy-remote.sh
```

## Deliverables

| File | Purpose |
|------|---------|
| `scripts/deploy-remote.sh` | VM-side deploy script (SSH target) |
| `templates/docker-compose.prod.yml` | Reference Compose with healthchecks |
| `templates/django/healthz.py` | `/healthz/` + `/livez/` endpoints |
| `workflows/ci.yml` | App-level CI template |
| `workflows/deploy-staging.yml` | Auto-deploy on push to main |
| `workflows/deploy-prod.yml` | Manual-approval deploy on `v*` tag |

## Quick Start

```bash
# 1. Copy templates to your app repo
cp deployment/workflows/*.yml  <app>/.github/workflows/
cp deployment/scripts/deploy-remote.sh <app>/scripts/
cp deployment/templates/django/healthz.py <app>/apps/core/views/

# 2. Replace placeholders: [ORG], [APP], [DEPLOY_PATH]
# 3. Set up GitHub Environments (see below)
# 4. Push to main → staging auto-deploys
# 5. Tag v1.0.0 → prod deploys after approval
```

## (G) GitHub Secrets & Environment Variables

### Repository Secrets (shared across environments)

| Secret | Example | Required |
|--------|---------|----------|
| `DEPLOY_SSH_KEY` | Ed25519 private key | Yes |
| `DEPLOY_USER` | `deploy` | Yes |

### Environment: `staging`

| Secret/Variable | Example | Type |
|-----------------|---------|------|
| `STAGING_HOST` | `staging.example.com` | Secret |
| `DEPLOY_SSH_PORT` | `22` | Variable |

### Environment: `production`

| Secret/Variable | Example | Type |
|-----------------|---------|------|
| `PROD_HOST` | `prod1.example.com` | Secret |
| `DEPLOY_SSH_PORT` | `22` | Variable |
| `SLACK_WEBHOOK_URL` | `https://hooks.slack.com/...` | Secret |

Configure **Environment Protection Rules** for `production`:
- Required reviewers: 1+
- Wait timer: 0 (or 5 min for extra safety)
- Deployment branches: `main`, `v*` tags only

### Server-side `.env.prod` (on VM, never in git)

```bash
# App
SECRET_KEY=<django-secret>
ALLOWED_HOSTS=app.example.com
CSRF_TRUSTED_ORIGINS=https://app.example.com
DJANGO_SETTINGS_MODULE=config.settings.production

# Database
POSTGRES_DB=app_prod
POSTGRES_USER=app
POSTGRES_PASSWORD=<strong-password>
DATABASE_URL=postgresql://app:<pw>@postgres:5432/app_prod

# Redis
REDIS_URL=redis://redis:6379/0

# Container registry
GHCR_OWNER=achimdehnert
GHCR_REPO=bfagent/bfagent-web

# Image tag (overwritten by deploy-remote.sh)
BFAGENT_IMAGE_TAG=latest

# LLM (optional)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

## deploy-remote.sh — Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | — |
| 1 | General error (bad args, missing files) | Fix and retry |
| 2 | Healthcheck failed, rollback succeeded | Investigate logs |
| 3 | Rollback also failed | **Manual intervention** |
| 4 | Migration failed, containers NOT restarted | Fix migration, retry |

## Go-Live Checklist

### Before First Deploy

- [ ] VM provisioned, Docker + Compose installed
- [ ] `deploy` user created with Docker group access
- [ ] SSH key pair generated, public key on VM
- [ ] `/srv/<app>/` directory created, owned by `deploy`
- [ ] `docker-compose.prod.yml` + `.env.prod` on VM
- [ ] External Docker network created: `docker network create bf_platform_prod`
- [ ] Nginx/Caddy reverse proxy configured with TLS
- [ ] `deploy-remote.sh` copied to VM and `chmod +x`
- [ ] GitHub repo secrets configured (see above)
- [ ] GitHub environments created (staging, production)
- [ ] Production environment has required reviewers

### Before Each Release

- [ ] All tests pass on `main`
- [ ] Migrations are **expand-only** (additive columns, no drops)
- [ ] `/healthz/` endpoint returns 200 locally
- [ ] Docker image builds successfully
- [ ] Changelog / release notes prepared

### After Deploy

- [ ] `/healthz/` returns 200 with correct `git_sha`
- [ ] Check `deployments.jsonl` for audit entry
- [ ] Monitor logs: `docker logs <container> --tail 100`
- [ ] Smoke-test critical user flows

## Rollback Drill

Run this quarterly to verify rollback capability.

### Manual Rollback (on VM)

```bash
# 1. Check current state
cat /srv/<app>/.env.prod | grep IMAGE_TAG

# 2. Rollback to previous known-good tag
/srv/<app>/scripts/deploy-remote.sh \
  --app <app> \
  --tag <previous-tag> \
  --rollback-to <previous-tag> \
  --skip-migrate

# 3. Verify
curl -sf https://<domain>/healthz/ | jq .
```

### Via GitHub Actions

```bash
# Trigger prod deploy with explicit old tag
gh workflow run deploy-prod.yml \
  -f image_tag=<previous-tag>
```

### Rollback Drill Steps

1. Deploy a known-good tag to staging
2. Deploy a deliberately failing tag (e.g., `bad-healthcheck`)
3. Verify automatic rollback triggers (exit code 2)
4. Verify `deployments.jsonl` contains rollback entry
5. Manually rollback production to previous tag
6. Verify healthcheck passes
7. Document drill date and results

## Service-spezifische Deploy-Besonderheiten

### coach-hub (KI ohne Risiko) — Manuelles SSH-Deploy

coach-hub hat **keinen GitHub Actions Runner** und wird manuell via SSH deployed.

**Build-Server:** `root@88.198.191.108` (Produktionsserver)  
**Build-Verzeichnis:** `/tmp/coach-hub-build`  
**Compose:** `/opt/coach-hub/docker-compose.prod.yml`  
**URL:** `https://kiohnerisiko.de` (Port `127.0.0.1:8007:8000`)

#### Deploy-Ablauf

```bash
# 1. SSH auf Produktionsserver
ssh root@88.198.191.108

# 2. Build-Verzeichnis aktualisieren
cd /tmp/coach-hub-build
git pull origin main

# 3. Image bauen und deployen
docker compose -f /opt/coach-hub/docker-compose.prod.yml pull
docker compose -f /opt/coach-hub/docker-compose.prod.yml up -d --build

# 4. Health-Check (intern — kein öffentlicher /livez!)
curl -s http://127.0.0.1:8007/livez/
```

#### Kritische Besonderheiten

- **KEIN HEALTHCHECK im Dockerfile** — nur in `docker-compose.prod.yml` pro Service (ADR-078)
- **Beat-Volume Permission:** `chown -R appuser:appgroup /celerybeat` im `entrypoint.sh` vor `exec` (Beat-Container schlägt sonst mit Permission denied fehl)
- **Worker/Beat Healthcheck:** `pidof python3.12 || exit 1` (nicht `celery inspect ping`)
- **Port nicht öffentlich:** `127.0.0.1:8007:8000` — Nginx auf `88.198.191.108` proxied zu `46.225.113.1:8007`
- **Auth:** django-allauth (nicht Django built-in) → Login unter `/accounts/`

#### Runner einrichten (Zukunft)

Wenn coach-hub einen Runner bekommen soll:

```bash
# Auf dev-server (46.225.113.1) als root:
TOKEN=$(curl -s -X POST -H "Authorization: Bearer <PAT>" \
  "https://api.github.com/repos/achimdehnert/coach-hub/actions/runners/registration-token" \
  | python3 -c "import json,sys; print(json.load(sys.stdin).get('token',''))")
sudo mkdir -p /home/github-runner/runner-achimdehnert-coach-hub
sudo tar xzf /home/github-runner/actions-runner/actions-runner-linux-x64-2.331.0.tar.gz \
  -C /home/github-runner/runner-achimdehnert-coach-hub
sudo chown -R github-runner:github-runner /home/github-runner/runner-achimdehnert-coach-hub
sudo -u github-runner bash -c "cd /home/github-runner/runner-achimdehnert-coach-hub && \
  ./config.sh --url https://github.com/achimdehnert/coach-hub --token $TOKEN \
  --name dev-hetzner --labels 'self-hosted,hetzner,dev' --work '_work' --unattended --replace"
sudo bash -c "cd /home/github-runner/runner-achimdehnert-coach-hub && ./svc.sh install github-runner"
sudo bash -c "cd /home/github-runner/runner-achimdehnert-coach-hub && ./svc.sh start"
```

---

## Expand/Contract Migration Pattern

```
Phase 1 (EXPAND):  Deploy adds new columns/tables (backward compatible)
  ├── New code reads old + new columns
  ├── Old code still works (no breaking changes)
  └── deploy-remote.sh runs `migrate --noinput` BEFORE restart

Phase 2 (MIGRATE DATA): Backfill data in new columns
  └── Management command or data migration

Phase 3 (CONTRACT): Remove old columns (separate deploy)
  ├── Only after all code uses new columns
  └── Requires its own deploy cycle
```

**Rule:** Never deploy destructive migrations (DROP COLUMN, rename)
in the same deploy as the code that stops using them.
