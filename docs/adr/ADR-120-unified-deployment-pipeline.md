---
status: accepted
date: 2026-03-11
updated: 2026-03-11
decision-makers: Achim Dehnert
supersedes: ADR-009 (GitHub Actions Reusable Workflows) — wird erweitert
related: ADR-009, ADR-022, ADR-102 (Cloudflare DNS), ADR-103 (bieterpilot)
implementation_status: implemented
implementation_evidence:
  - "all 18 Django hubs: deploy.yml via reusable workflows"
---

# ADR-120: Unified Multi-Repo Deployment Pipeline mit Staging

## Status

Accepted — v1.1 (2026-03-11, Review-Fixes aus Input-Report + Eigenreview, implementiert)

## Context

Die IIL-Plattform läuft auf 3 Hetzner-Servern:

| Server | Typ | IP | Rolle |
|--------|-----|-----|-------|
| ubuntu-8gb-nbg1-1 | CPX52 (8 vCPU, 16 GB) | 88.198.191.108 | **PROD** — alle Hub-Apps |
| odoo-prod | CPX32 (4 vCPU, 8 GB) | 46.225.127.211 | **PROD** — Odoo ERP |
| dev-server | CCX33 (8 vCPU, 32 GB) | 46.225.113.1 | **DEV** + **Staging** |

### Aktuelle Probleme

- 🔴 **Kein einheitliches Deployment** über 20+ Repos — jedes Repo hat eigene, inkonsistente Workflow-Logik
- 🔴 **Kein Staging** — Änderungen landen direkt in Production ohne vorherige Verifikation
- 🔴 **Push-auf-main = Prod-Deploy** — kein explizites Gate, keine Versionierung
- 🔴 **`:latest`-Images** in Production — kein Rollback-Marker
- 🟡 **Kein automatischer Health-Check** nach Deploy (ADR-022: `/healthz/` ist Pflicht)
- 🟡 **Kein strukturierter Rollback-Prozess**

### Entscheidungstreiber

1. Einheitlichkeit über alle 20+ Repos — ein zentraler Workflow, alle Repos als thin Caller
2. Explizites Staging-Gate vor jedem Production-Deploy
3. Reproduzierbare, auditierbare Builds (Image-Tag = Git-Tag)
4. Rollback in < 2 Minuten durch Image-Tag-Wechsel
5. Minimale Zusatzkosten (0 € — dev-server als Staging)
6. Cloudflare Access für Staging-Schutz ist bereits vorbereitet

### TLS-Strategie für Staging (QUESTION aus Review)

Für `staging.*.iil.pet` Domains auf dem dev-server:
- **Cloudflare Proxy (empfohlen):** DNS-Records mit Proxy-Modus → Cloudflare stellt TLS bereit.
  Kein Certbot nötig. Cloudflare Access Zero Trust schützt automatisch.
- **Fallback:** Certbot mit `--dns-cloudflare` Plugin für Wildcard-Cert `*.iil.pet`.
  Nur nötig falls Proxy-Modus nicht gewünscht.

## Betrachtete Optionen

### Option A: dev-server als Staging (gewählt) ✅

- Staging-Container laufen auf CCX33 (dev-server, 32 GB RAM — genug Headroom)
- Staging-Domains: `staging.<hub>.iil.pet` via Cloudflare Access geschützt
- Kosten: 0 € zusätzlich
- Eskalation zu Option B wenn Platform wächst

### Option B: Separater Staging-Server

- Neuer CPX21/CPX31 nur für Staging
- Kosten: ~15–25 €/Monat
- Vorteil: vollständige Isolation
- **Aufgeschoben** — erst bei Ressourcen-Konkurrenz auf dev-server

### Option C: Staging auf Prod-Server (zweite Compose-Instanz)

- Staging neben Production auf 88.198.191.108
- **Abgelehnt** — Staging-Fehler können Prod-Performance beeinträchtigen

## Decision

### Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────────────┐
│                    achimdehnert/platform                             │
│                  (Central Reusable Workflows)                       │
│                                                                     │
│   .github/workflows/                                                │
│   ├── _deploy-unified.yml    ← Zentrales Deploy-Workflow            │
│   └── _ci-python.yml         ← Zentrales CI-Workflow (besteht)      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ uses: achimdehnert/platform/.github/workflows/
                           │
        ┌──────────────────┼──────────────────────┐
        │                  │                      │
   risk-hub            travel-beat           billing-hub
   .github/             .github/              .github/
   workflows/           workflows/            workflows/
   └─deploy.yml         └─deploy.yml          └─deploy.yml
     (30 Zeilen)         (30 Zeilen)           (30 Zeilen)
```

### Trigger-Strategie

```
Feature-Branch
     │
     ▼ PR öffnen
     │
     ▼ CI läuft (test + lint + build-check)
     │
     ▼ PR Merge → main
     │
     ├─► Build Image :main-<7-char-sha>
     │
     ├─► Deploy STAGING (automatisch)
     │   dev-server (46.225.113.1)
     │   staging.<hub>.iil.pet
     │   (Cloudflare Access: nur @iil.gmbh)
     │
     │   ── Testen auf Staging ──
     │
     ▼ Manueller Schritt: git tag v1.2.3 && git push --tags
     │
     ├─► Build Image :v1.2.3
     │
     └─► Deploy PRODUCTION (automatisch)
         prod-server (88.198.191.108)
         <hub>.iil.pet / <domain>.de
         Health-Check auf /healthz/ (ADR-022)
```

### Image-Tagging-Strategie (GHCR)

| Umgebung | Image-Tag Muster | Beispiel |
|----------|-----------------|----------|
| Staging | `:main-<7-char-sha>` | `risk-hub:main-a3f9d12` |
| Production | `:v<semver>` | `risk-hub:v1.4.2` |
| Verboten | `:latest` | ❌ niemals in PROD |

### GitHub Environments

Jedes Repo bekommt zwei GitHub Environments:

**`staging`**
- Required Reviewers: keine (auto-deploy)
- Deployment Branch: `main`
- Secrets: `STAGING_SSH_KEY`, `STAGING_HOST`, `STAGING_USER`

**`production`**
- Required Reviewers: optional (kann 1 sein für kritische Repos)
- Deployment Branch: Tags `v*`
- Secrets: `PROD_SSH_KEY`, `PROD_HOST`, `PROD_USER`

**Shared Secrets** (Organization-Level oder pro Repo):
- `GHCR_TOKEN` — GitHub PAT mit `packages:read`
- `DISCORD_WEBHOOK` — Deploy-Notifications

### Per-Repo Caller-Template

```yaml
# <repo>/.github/workflows/deploy.yml — 30 Zeilen, 3 Felder anpassen
name: "Deploy"

on:
  push:
    branches: ["main"]
    tags: ["v*.*.*"]
  workflow_dispatch:
    inputs:
      image_tag_override:
        description: "Rollback auf Image-Tag (z.B. v1.2.1)"
        required: false
        default: ""

jobs:
  ci:
    uses: achimdehnert/platform/.github/workflows/_ci-python.yml@v1
    # CI nur bei push auf main und workflow_dispatch — bei Tags ist CI bereits gelaufen
    if: startsWith(github.ref, 'refs/heads/')

  deploy:
    needs: [ci]
    if: always() && (needs.ci.result == 'success' || needs.ci.result == 'skipped')
    uses: achimdehnert/platform/.github/workflows/_deploy-unified.yml@v1
    with:
      app_name: "risk-hub"                              # ← ANPASSEN
      app_path: "/opt/risk-hub"                         # ← ANPASSEN
      health_check_url: "https://schutztat.de/healthz/" # ← ANPASSEN (ADR-022!)
      image_tag_override: ${{ inputs.image_tag_override || '' }}
      notify_discord: true
    secrets: inherit
```

> **Wichtig:** `health_check_url` MUSS auf `/healthz/` enden (ADR-022), nicht `/health`.
> **CI bei Tags:** Bei `git tag v*` wird CI übersprungen (`if: startsWith(github.ref, 'refs/heads/')`) —
> der Code wurde bereits auf `main` getestet.

### Zentrales Reusable Workflow

```yaml
# achimdehnert/platform/.github/workflows/_deploy-unified.yml
name: "🚀 Deploy (Reusable)"

on:
  workflow_call:
    inputs:
      app_name:
        required: true
        type: string
      app_path:
        required: true
        type: string
      health_check_url:
        required: false
        type: string
        default: ""
      image_tag_override:
        required: false
        type: string
        default: ""
      notify_discord:
        required: false
        type: boolean
        default: true
    secrets:
      GHCR_TOKEN:
        required: true
      STAGING_SSH_KEY:
        required: false  # nicht alle Repos brauchen Staging
      STAGING_HOST:
        required: false
      STAGING_USER:
        required: false
      PROD_SSH_KEY:
        required: true
      PROD_HOST:
        required: true
      PROD_USER:
        required: true
      DISCORD_WEBHOOK:
        required: false

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository_owner }}/${{ inputs.app_name }}

jobs:
  # ── JOB 1: Environment + Image-Tag bestimmen ──
  resolve:
    name: "🔍 Resolve"
    runs-on: ubuntu-latest
    outputs:
      environment: ${{ steps.env.outputs.environment }}
      image_tag: ${{ steps.tag.outputs.image_tag }}
      deploy_staging: ${{ steps.env.outputs.deploy_staging }}
      deploy_prod: ${{ steps.env.outputs.deploy_prod }}
    steps:
      - name: Resolve environment
        id: env
        run: |
          if [[ "${{ github.ref }}" == refs/tags/v* ]]; then
            echo "environment=production" >> "$GITHUB_OUTPUT"
            echo "deploy_staging=false"   >> "$GITHUB_OUTPUT"
            echo "deploy_prod=true"       >> "$GITHUB_OUTPUT"
          elif [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "environment=staging"    >> "$GITHUB_OUTPUT"
            echo "deploy_staging=true"    >> "$GITHUB_OUTPUT"
            echo "deploy_prod=false"      >> "$GITHUB_OUTPUT"
          else
            if [[ "${{ inputs.image_tag_override }}" == v* ]]; then
              echo "environment=production" >> "$GITHUB_OUTPUT"
              echo "deploy_staging=false"   >> "$GITHUB_OUTPUT"
              echo "deploy_prod=true"       >> "$GITHUB_OUTPUT"
            else
              echo "environment=staging"    >> "$GITHUB_OUTPUT"
              echo "deploy_staging=true"    >> "$GITHUB_OUTPUT"
              echo "deploy_prod=false"      >> "$GITHUB_OUTPUT"
            fi
          fi

      - name: Resolve image tag
        id: tag
        run: |
          if [[ -n "${{ inputs.image_tag_override }}" ]]; then
            echo "image_tag=${{ inputs.image_tag_override }}" >> "$GITHUB_OUTPUT"
          elif [[ "${{ github.ref }}" == refs/tags/v* ]]; then
            echo "image_tag=${{ github.ref_name }}" >> "$GITHUB_OUTPUT"
          else
            SHA="${{ github.sha }}"
            echo "image_tag=main-${SHA:0:7}" >> "$GITHUB_OUTPUT"
          fi

  # ── JOB 2: Build & Push Docker Image ──
  build:
    name: "🐳 Build"
    runs-on: ubuntu-latest
    needs: resolve
    if: inputs.image_tag_override == ''
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GHCR_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ needs.resolve.outputs.image_tag }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            BUILD_DATE=${{ github.event.head_commit.timestamp }}
            GIT_SHA=${{ github.sha }}
            APP_VERSION=${{ needs.resolve.outputs.image_tag }}

  # ── JOB 3a: Deploy to Staging ──
  deploy-staging:
    name: "🧪 Staging"
    runs-on: ubuntu-latest
    needs: [resolve, build]
    if: |
      always() &&
      needs.resolve.outputs.deploy_staging == 'true' &&
      (needs.build.result == 'success' || needs.build.result == 'skipped')
    concurrency:
      group: deploy-${{ inputs.app_name }}-staging
      cancel-in-progress: false
    environment:
      name: staging
      url: https://staging.${{ inputs.app_name }}.iil.pet
    steps:
      - name: Deploy
        uses: appleboy/ssh-action@v1.0.3
        timeout-minutes: 15
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          fingerprint: ${{ secrets.STAGING_SSH_FINGERPRINT }}
          script: |
            set -euo pipefail
            /opt/scripts/deploy.sh \
              "${{ inputs.app_name }}" \
              "${{ inputs.app_path }}" \
              "${{ needs.resolve.outputs.image_tag }}" \
              "staging" \
              "${{ inputs.health_check_url }}"

  # ── JOB 3b: Deploy to Production ──
  deploy-production:
    name: "🚀 Production"
    runs-on: ubuntu-latest
    needs: [resolve, build]
    if: |
      always() &&
      needs.resolve.outputs.deploy_prod == 'true' &&
      (needs.build.result == 'success' || needs.build.result == 'skipped')
    concurrency:
      group: deploy-${{ inputs.app_name }}-production
      cancel-in-progress: false
    environment:
      name: production
    steps:
      - name: Deploy
        uses: appleboy/ssh-action@v1.0.3
        timeout-minutes: 15
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          fingerprint: ${{ secrets.PROD_SSH_FINGERPRINT }}
          script: |
            set -euo pipefail
            /opt/scripts/deploy.sh \
              "${{ inputs.app_name }}" \
              "${{ inputs.app_path }}" \
              "${{ needs.resolve.outputs.image_tag }}" \
              "production" \
              "${{ inputs.health_check_url }}"

  # ── JOB 4: Discord Notification ──
  notify:
    name: "📣 Notify"
    runs-on: ubuntu-latest
    needs: [resolve, deploy-staging, deploy-production]
    if: always() && inputs.notify_discord
    steps:
      - name: Send notification
        env:
          DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK }}
        run: |
          if [[ -z "$DISCORD_WEBHOOK" ]]; then exit 0; fi

          ENV="${{ needs.resolve.outputs.environment }}"
          TAG="${{ needs.resolve.outputs.image_tag }}"
          APP="${{ inputs.app_name }}"

          STAGING_RESULT="${{ needs.deploy-staging.result }}"
          PROD_RESULT="${{ needs.deploy-production.result }}"

          if [[ "$ENV" == "staging" && "$STAGING_RESULT" == "success" ]]; then
            COLOR=3066993; STATUS="✅ Staging deploy erfolgreich"
          elif [[ "$ENV" == "production" && "$PROD_RESULT" == "success" ]]; then
            COLOR=3066993; STATUS="✅ Production deploy erfolgreich"
          else
            COLOR=15158332; STATUS="❌ Deploy fehlgeschlagen"
          fi

          curl -sf --max-time 10 -X POST "$DISCORD_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"embeds\":[{\"title\":\"$STATUS\",\"color\":$COLOR,\"fields\":[{\"name\":\"App\",\"value\":\"$APP\",\"inline\":true},{\"name\":\"Version\",\"value\":\"$TAG\",\"inline\":true},{\"name\":\"Env\",\"value\":\"$ENV\",\"inline\":true}]}]}"
```

### Server-seitiges Deploy-Script

```bash
#!/usr/bin/env bash
# /opt/scripts/deploy.sh — auf PROD und DEV/Staging
set -euo pipefail

APP_NAME="${1:?'APP_NAME fehlt'}"
APP_PATH="${2:?'APP_PATH fehlt'}"
IMAGE_TAG="${3:?'IMAGE_TAG fehlt'}"
ENVIRONMENT="${4:?'ENVIRONMENT fehlt (staging|production)'}"
HEALTH_CHECK_URL="${5:-}"

LOG_DIR="/var/log/iil-deploys"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/${APP_NAME}_$(date +%Y%m%d_%H%M%S)_$$.log"
exec > >(tee -a "$LOG_FILE") 2>&1

# Validierung
[[ "$ENVIRONMENT" =~ ^(staging|production)$ ]] || { echo "FEHLER: ENVIRONMENT ungültig" >&2; exit 1; }
[[ -d "$APP_PATH" ]] || { echo "FEHLER: $APP_PATH existiert nicht" >&2; exit 2; }
[[ -f "$APP_PATH/docker-compose.yml" || -f "$APP_PATH/docker-compose.prod.yml" ]] || { echo "FEHLER: Kein Compose-File" >&2; exit 3; }

# Vorherigen Tag für Rollback speichern
PREVIOUS_TAG=""
if [[ -f "$APP_PATH/.env" ]]; then
  PREVIOUS_TAG=$(grep "^IMAGE_TAG=" "$APP_PATH/.env" | cut -d= -f2 || true)
fi

# Rollback-Funktion
rollback() {
  local ec=$?
  if [[ -n "$PREVIOUS_TAG" && "$PREVIOUS_TAG" != "$IMAGE_TAG" ]]; then
    echo "❌ Deploy fehlgeschlagen — Rollback auf $PREVIOUS_TAG"
    cd "$APP_PATH"
    export IMAGE_TAG="$PREVIOUS_TAG"
    docker compose -f "$COMPOSE_FILE" up -d --force-recreate 2>&1 || {
      echo "KRITISCH: Rollback fehlgeschlagen! Manuell: IMAGE_TAG=$PREVIOUS_TAG" >&2
      exit 10
    }
    echo "⚠️ Rollback auf $PREVIOUS_TAG erfolgreich"
  fi
  exit "$ec"
}
trap rollback ERR

echo "═══ iil-Platform Deploy ═══"
echo "App: $APP_NAME | Env: $ENVIRONMENT | Tag: $IMAGE_TAG"
[[ -n "$PREVIOUS_TAG" ]] && echo "Vorher: $PREVIOUS_TAG"

# IMAGE_TAG in .env schreiben
if [[ -f "$APP_PATH/.env" ]] && grep -q "^IMAGE_TAG=" "$APP_PATH/.env"; then
  sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=${IMAGE_TAG}|" "$APP_PATH/.env"
else
  echo "IMAGE_TAG=${IMAGE_TAG}" >> "$APP_PATH/.env"
fi

# GHCR Login
if [[ -f "/opt/scripts/.ghcr_token" ]]; then
  docker login ghcr.io -u achimdehnert --password-stdin < /opt/scripts/.ghcr_token
fi

# Compose-File nach Umgebung wählen (ADR-022: docker-compose.prod.yml für Production)
COMPOSE_FILE="docker-compose.yml"
if [[ "$ENVIRONMENT" == "production" && -f "$APP_PATH/docker-compose.prod.yml" ]]; then
  COMPOSE_FILE="docker-compose.prod.yml"
fi

# Staging: eigenes Compose-Projekt um DEV-Container nicht zu überschreiben
if [[ "$ENVIRONMENT" == "staging" ]]; then
  export COMPOSE_PROJECT_NAME="staging-${APP_NAME}"
fi

# Deploy
cd "$APP_PATH"
docker compose -f "$COMPOSE_FILE" pull
docker compose -f "$COMPOSE_FILE" up -d --force-recreate --remove-orphans

# Health-Check (nur HTTP 200 akzeptieren — ADR-022)
if [[ -n "$HEALTH_CHECK_URL" ]]; then
  for i in $(seq 1 12); do
    HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 10 "$HEALTH_CHECK_URL" 2>/dev/null || echo "000")
    if [[ "$HTTP_CODE" == "200" ]]; then
      echo "✅ Health-Check OK (Versuch $i)"
      break
    fi
    echo "⏳ Versuch $i/12 — HTTP $HTTP_CODE"
    sleep 5
    [[ $i -eq 12 ]] && { echo "❌ Health-Check fehlgeschlagen"; exit 4; }
  done
else
  sleep 5
  docker compose -f "$COMPOSE_FILE" ps | grep -qi "unhealthy\|exit\|error" && exit 5
  echo "✅ Container läuft"
fi

# Cleanup
docker image prune -f 2>/dev/null || true  # nur dangling (ungetaggte) Images

trap - ERR
echo "═══ Deploy erfolgreich: $APP_NAME:$IMAGE_TAG ($ENVIRONMENT) ═══"
```

### Staging-Port-Schema (dev-server)

Um Port-Konflikte mit DEV-Instanzen zu vermeiden:

| App | Prod-Port | Staging-Port |
|-----|-----------|-------------|
| bfagent | 8088 | 9088 |
| risk-hub | 8090 | 9090 |
| travel-beat | 8089 | 9089 |
| weltenhub | 8081 | 9081 |
| pptx-hub | 8020 | 9020 |
| research-hub | 8098 | 9098 |
| billing-hub | 8062 | 9062 |
| ausschreibungs-hub | 8103 | 9103 |

Staging-Compose: `COMPOSE_PROJECT_NAME=staging-<app>` um Container-Namenskonflikte zu vermeiden.

### Rollback-Prozedur

```bash
# Option 1: Via GitHub Actions UI (empfohlen)
# → Repo → Actions → Deploy → "Run workflow"
# → image_tag_override: v1.3.1

# Option 2: Direkt auf Server (Notfall)
ssh hetzner-prod
/opt/scripts/deploy.sh risk-hub /opt/risk-hub v1.3.1 production https://schutztat.de/healthz/
```

## Invarianten (Non-Negotiable)

1. `:latest` ist in PROD **verboten** — immer expliziter SemVer-Tag
2. Health-Check auf `/healthz/` ist **Pflicht** nach jedem Deploy (ADR-022)
3. `set -euo pipefail` in allen Shell-Skripten
4. GitHub Environment `production` wird nur durch `v*`-Tags getriggert
5. Staging läuft immer hinter Cloudflare Access Zero Trust (nur `@iil.gmbh`)
6. Kein Deploy ohne grüne CI (test + lint) — `_ci-python.yml` als Prerequisite

## Implementierungsplan

| Phase | Inhalt | Aufwand |
|-------|--------|---------|
| 0 | `deploy.sh` auf beiden Servern installieren | 1h |
| 1 | `_deploy-unified.yml` in `platform` Repo anlegen | 2h |
| 2 | Staging-Nginx-Config + Certbot auf dev-server | 1h |
| 3 | Cloudflare Access für `staging.*.iil.pet` Domains | 0.5h |
| 4 | Pilot: risk-hub + bfagent migrieren | 2h |
| 5 | Rollout: alle weiteren Repos (Template-Copy) | 3h |

**Gesamt:** ~9.5h (verteilt auf 2–3 Tage)

### Migrations-Reihenfolge

| Prio | Repo | Begründung |
|------|------|-----------|
| 1 | risk-hub | Referenz-Implementierung, gut testbar |
| 2 | bfagent | Größte App, meiste Änderungen |
| 3 | billing-hub | Kritische Infrastruktur (ADR-118) |
| 4 | travel-beat | Gut testbar, kleine App |
| 5 | ausschreibungs-hub | Neues Repo — direkt mit neuem System |
| 6+ | Alle anderen | Template-Copy, ~10 min pro Repo |

## Consequences

### Positiv

- Ein zentrales `_deploy-unified.yml` regiert alle 20+ Repos
- Neues Repo onboarden = 30 Zeilen Caller + 2 GitHub Environments
- Vollständiger Audit-Trail: Tag = Version = Image = Deployment
- Rollback in < 2 Minuten (Image-Tag-Wechsel)
- Staging-Gate vor jedem Prod-Deploy
- 0 € Zusatzkosten (dev-server als Staging)

### Negativ / Risiken

- Initiale Migration der bestehenden Workflows (~9.5h Gesamtaufwand)
- dev-server ist DEV + Staging — Ressourcen-Konkurrenz bei vielen parallelen Staging-Deploys (Eskalation: Option B)
- Git-Tag-Disziplin muss eingehalten werden (kein Tag = kein Prod-Deploy)
- Kurze Downtime (~5–15s) bei Recreate-Strategie — für kritische Services (billing-hub) ggf. Blue/Green als spätere Erweiterung

### Nicht in Scope

- Blue/Green Deployment (separates ADR bei Bedarf)
- Canary Releases
- Odoo-Server Deployment (eigener Lifecycle)
- Kubernetes/k3s Migration

## Betroffene Repos

- `platform` — Reusable Workflow `_deploy-unified.yml`, `deploy.sh` Script
- Alle 20+ Hub-Repos — Caller-Template + GitHub Environments
- dev-server — Staging-Nginx, Docker-Container, Cloudflare Access

## Review-History

| Datum | Version | Reviewer | Urteil | Link |
|-------|---------|----------|--------|------|
| 2026-03-11 | Input-Bewertung | Cascade | 6 Dateien analysiert, Fixes eingearbeitet | [Bewertung](reviews/ADR-120-input-bewertung.md) |
| 2026-03-11 | v1.0 → v1.1 | Cascade | ❌ → Fixes applied (7 BLOCKs, 6 SUGGESTs, 3 QUESTIONs) | [Input-Report](inputs/ADR-120-review-report.md) |
| 2026-03-11 | v1.1 | Cascade | ✅ APPROVED + Implementiert | `platform/scripts/deploy.sh`, `platform/.github/workflows/_deploy-unified.yml`, `risk-hub/.github/workflows/deploy.yml` |
