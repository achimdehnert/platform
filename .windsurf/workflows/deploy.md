---
description: Deploy any app to production (bfagent, cad-hub, travel-beat, etc.)
---

# Deploy Workflow

> **Architektur (ADR-075 + ADR-100)**: Deployments sind Aufgabe des **Deployment Agent**.
> Cascade (Tech Lead) genehmigt nur bei Gate-2-Situationen (neue Migrations, Breaking Changes).
> Write-Ops laufen über GitHub Actions — NICHT via direktem SSH (hängt).
> Read-Ops (Logs, Status) via `deployment-mcp` Tools.

## Rollen-Trennung (ADR-100)

| Wer | Was |
|-----|-----|
| **Deployment Agent** | Automatischer Deploy nach CI grün (Gate 2, autonom bei Routine) |
| **Cascade (Tech Lead)** | Gate-2-Approval bei neuen Migrations / Breaking Changes |
| **Mensch** | Gate-3/4 bei kritischen Prod-Änderungen |

## Workflow-Übersicht

| Operation | Methode | Link |
|-----------|---------|------|
| Deploy | `infra-deploy` → `deploy-service.yml` | https://github.com/achimdehnert/infra-deploy/actions |
| Rollback | `infra-deploy` → `rollback.yml` | https://github.com/achimdehnert/infra-deploy/actions |
| Migrations | `infra-deploy` → `migrate.yml` | https://github.com/achimdehnert/infra-deploy/actions |
| DB-Backup | `infra-deploy` → `db-backup.yml` | https://github.com/achimdehnert/infra-deploy/actions |
| Health-Check | `infra-deploy` → `health-check.yml` | https://github.com/achimdehnert/infra-deploy/actions |

---

## Pre-Deploy: ADR Freshness Gate (iil-adrfw v0.4.0)

Vor jedem Deploy prüfen ob die ADRs noch zum aktuellen Repo-Stand passen:

```
MCP: mcp2_adr_freshness(repo_path="${GITHUB_DIR}/<SERVICE>")
→ Prüft Version/Port/Image Claims in ADRs gegen compose + requirements
→ severity=warning: Version-Drift (z.B. ADR sagt PostgreSQL 15, Repo hat 16)
→ severity=info: Port-Abweichung (oft irrelevant, nur bei eigenem Repo-Port warnen)
```

| Ergebnis | Aktion |
|----------|--------|
| 0 stale_claims | ✅ Deploy fortsetzen |
| Nur `info` Findings | ✅ Deploy fortsetzen, optional ADR updaten |
| `warning` Findings | ⚠️ User informieren — Deploy möglich, aber ADR-Update empfohlen |
| Version-Mismatch bei Kern-Infra (DB, Python) | ❌ Erst ADR aktualisieren, dann deployen |

→ Verhindert Drift zwischen ADR-Dokumentation und tatsächlichem System-Stand.

---

## Deploy via GitHub Actions (Standard)

### 1. Service deployen (GitHub UI)
1. → https://github.com/achimdehnert/infra-deploy/actions/workflows/deploy-service.yml
2. **Run workflow** → Inputs:
   - `service`: `bfagent` | `travel-beat` | `weltenhub` | `risk-hub` | `dev-hub` | `wedding-hub`
   - `image_tag`: `latest` oder SHA
   - `has_migrations`: `true` oder `false`

### 2. Service deployen (Agent / Cascade)
Verwende `<deployment-mcp>_cicd_manage` *(Prefix aus mcp-tools.md)* mit `action: dispatch`:
```
owner: achimdehnert
repo: infra-deploy
workflow_id: deploy-service.yml
ref: main
inputs: {service: "travel-beat", image_tag: "latest", has_migrations: "false"}
```
Dann Status pollen mit `<deployment-mcp>_cicd_manage` *(Prefix aus mcp-tools.md)* → `action: run_status`.

---

## Rollback

1. → https://github.com/achimdehnert/infra-deploy/actions/workflows/rollback.yml
2. **Run workflow** → `service` + optional `target_tag` (leer = vorheriger Tag)

---

## Migrations (ohne Deploy)

1. → https://github.com/achimdehnert/infra-deploy/actions/workflows/migrate.yml
2. **Run workflow** → `service` + `backup_first: true` (empfohlen)

---

## DB-Backup (manuell)

1. → https://github.com/achimdehnert/infra-deploy/actions/workflows/db-backup.yml
2. **Run workflow** → `service`

Automatisch: täglich 02:00 UTC für alle Services.

---

## Deploy-Status prüfen (Read-Only via deployment-mcp)

### Container-Logs
Verwende `deployment-mcp` → `container_logs` Tool.

### Compose-Status
Verwende `deployment-mcp` → `compose_ps` Tool.

### Deploy-History
→ https://github.com/achimdehnert/infra-deploy/actions

---

## Troubleshooting

- **Workflow hängt**: Runner-Status → https://github.com/achimdehnert/infra-deploy/settings/actions/runners
- **Deploy fehlgeschlagen**: Auto-Rollback greift — Deploy-Log via `deployment-mcp` → `ssh_manage file_read /opt/deploy/production/.deployed/deploy.log`
- **Health-Check manuell**: `infra-deploy` → `health-check.yml` → Run workflow
- **NIEMALS**: `deployment-mcp` Write-Tools (compose_up, compose_restart) für Deploys verwenden → hängt (ADR-075)

---

## Stuck Deploy — Diagnose & Fix

### Symptom
Deploy-Runs bleiben permanent in `queued` — `deploy / 🔍 Resolve` zeigt leere Runner-Spalte.
CI-Jobs des gleichen Commits liefen durch. Mehrere Runs pilen sich auf.

### Root Cause
Zwei Ursachen kombinieren sich — **Root Cause ist #3**:
1. **Kein `concurrency` auf Workflow-Ebene** → mehrere Deploy-Runs starten gleichzeitig
2. **Job-Level `concurrency: cancel-in-progress: false`** in `_deploy-unified.yml` → steckengebliebene `deploy-staging` Jobs halten einen Concurrency-Lock
3. ⭐ **`prod-server` Custom-Label fehlt auf dem Runner** → `runs-on: prod-server` findet keinen Runner! CI-Jobs laufen auf `self-hosted` (random dispatch), Deploy braucht explizit `prod-server`-Label.

**Runner-Label prüfen** (sofort):
```bash
TOKEN=$(cat ~/.secrets/github_token)
curl -s -H "Authorization: token ${TOKEN}" \
  "https://api.github.com/repos/achimdehnert/{REPO}/actions/runners" \
  | python3 -c "import json,sys; [print(r['id'], r['name'], [l['name'] for l in r.get('labels',[])]) for r in json.load(sys.stdin).get('runners',[])]"
# prod-server runner muss 'prod-server' in labels haben!
```
**Label hinzufügen** (Fix):
```bash
curl -X POST -H "Authorization: token ${TOKEN}" \
  "https://api.github.com/repos/achimdehnert/{REPO}/actions/runners/{RUNNER_ID}/labels" \
  -d '{"labels":["prod-server"]}'
```

### Fix — permanent (schon integriert)
`deploy.yml` (jedes Repo) bekommt Workflow-level concurrency:
```yaml
concurrency:
  group: deploy-{app_name}-${{ github.ref_name }}
  cancel-in-progress: true   # neuer Push cancelt hängenden alten Run sofort
```
`_deploy-unified.yml` (Platform): Staging-Job `cancel-in-progress: true`.

### Notfall-Prozedur wenn Deploy feststeckt

// turbo
1. Hängende Runs canceln:
```bash
TOKEN=$(cat ~/.secrets/github_token)
REPO="achimdehnert/dev-hub"   # Repo anpassen
curl -s -H "Authorization: token ${TOKEN}" \
  "https://api.github.com/repos/${REPO}/actions/runs?status=queued&per_page=10" \
  | python3 -c "import json,sys; [print(r['id']) for r in json.load(sys.stdin)['workflow_runs']]"
# Für jeden Run-ID:
curl -X POST -H "Authorization: token ${TOKEN}" \
  "https://api.github.com/repos/${REPO}/actions/runs/{RUN_ID}/cancel"
```

2. Runner neustarten (falls nötig):
```bash
ssh root@88.198.191.108 \
  "systemctl restart actions.runner.achimdehnert-{repo}.prod-server.service"
```

3. Templates-Hotfix (template-only Änderungen, ohne GHA):
```bash
# Lokales Repo → direkt in Container kopieren
scp templates/controlling/dashboard.html root@88.198.191.108:/tmp/
ssh root@88.198.191.108 "docker cp /tmp/dashboard.html devhub_web:/app/templates/controlling/dashboard.html"
```

4. Frischen Deploy via workflow_dispatch triggern:
```bash
curl -X POST -H "Authorization: token ${TOKEN}" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/${REPO}/actions/workflows/deploy.yml/dispatches" \
  -d '{"ref":"main"}'
```

---

## Lessons Learned (Feb 2026)

### Private Repo Dependencies im Docker-Build

`git+https://` in `requirements.txt` schlägt im Docker-Build fehl (keine GitHub-Auth).
**Lösung**: Vendor-Pattern — Package unter `vendor/` im Repo, `requirements.txt` referenziert lokalen Pfad.
Siehe: `wedding-hub/.windsurf/workflows/platform-package-integration.md`

### SSH-Timeouts bei Build-Operationen

| Operation | Min. Timeout |
| --- | --- |
| Docker Build | 300-600s |
| Docker Push | 300s |
| Compose Pull | 120s |
| Git Pull | 30s |

Bei `deployment-mcp` → `ssh_manage exec` immer `timeout: 600` für Build-Operationen!

### DB-Credentials nie raten

Immer zuerst Container-Environment inspizieren:
```bash
docker inspect <container> --format '{{range .Config.Env}}{{println .}}{{end}}' | grep POSTGRES
```

### Server-Pfade nachschlagen

Nicht raten — in `project-facts.md` des jeweiligen Repos nachschauen oder:
```bash
find /opt -maxdepth 2 -name "docker-compose.prod.yml" 2>/dev/null
```
