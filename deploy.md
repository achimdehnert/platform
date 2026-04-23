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
