---
description: Deploy any app to production (bfagent, cad-hub, travel-beat, etc.)
---

# Deploy Workflow

> **Architektur (ADR-075)**: Write-Ops (Deploy, Migrate, Backup) laufen über
> `infra-deploy` GitHub Actions — NICHT via direktem SSH (hängt).
> Read-Ops (Logs, Status) via `deployment-mcp` Tools.

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
   - `service`: `bfagent` | `travel-beat` | `weltenhub` | `risk-hub` | `dev-hub`
   - `image_tag`: `latest` oder SHA
   - `has_migrations`: `true` oder `false`

### 2. Service deployen (Agent / Cascade)
Verwende `mcp7_cicd_manage` mit `action: dispatch`:
```
owner: achimdehnert
repo: infra-deploy
workflow_id: deploy-service.yml
ref: main
inputs: {service: "travel-beat", image_tag: "latest", has_migrations: "false"}
```
Dann Status pollen mit `mcp7_cicd_manage` → `action: run_status`.

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
