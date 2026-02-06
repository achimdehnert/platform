# Docker Deployment

## Übersicht

Jede App hat ein eigenes `docker-compose.prod.yml` in `/srv/<app>/` auf dem Hetzner VM.
Images werden via GitHub Actions gebaut, zu GHCR gepusht und per
`deploy-remote.sh` auf dem Server deployed.

## Deploy-Workflow (CI/CD)

```text
push main ──► CI (lint/test) ──► Build Image ──► GHCR
                                                   │
                auto (staging)                     │
                ┌──────────────────────────────────┘
                ▼
         deploy-remote.sh auf VM
         ┌─────────────────────┐
         │ 1. State sichern    │
         │ 2. DB Backup        │
         │ 3. Image pullen     │
         │ 4. Migrate (expand) │ ◄── GATE: Fehler → stop
         │ 5. Service restart  │
         │ 6. Healthcheck      │
         │ 7. Rollback on fail │
         └─────────────────────┘

tag v* ──► Build ──► GHCR ──► Manual Approval ──► deploy-remote.sh
```

### Manuelles Deployment

```bash
# Auf dem Server:
/srv/bfagent/scripts/deploy-remote.sh \
  --app bfagent \
  --tag abc1234 \
  --deploy-dir /srv/bfagent

# Rollback:
/srv/bfagent/scripts/deploy-remote.sh \
  --app bfagent \
  --tag <previous-tag> \
  --rollback-to <previous-tag> \
  --skip-migrate
```

### Exit Codes

| Code | Bedeutung | Aktion |
|------|-----------|--------|
| 0 | Erfolg | — |
| 1 | Allgemeiner Fehler | Fix + Retry |
| 2 | Healthcheck fehlgeschlagen, Rollback OK | Logs prüfen |
| 3 | Rollback fehlgeschlagen | **Manuelle Intervention** |
| 4 | Migration fehlgeschlagen, Container NICHT neu gestartet | Migration fixen |

## Services

### BF Agent

```yaml
services:
  bfagent-web:      # Django/Gunicorn (:8000) — Healthcheck auf /livez/
  caddy:            # Reverse Proxy (:80)
  mcphub-api:       # MCP Hub API (:8080)
  llm-gateway:      # LLM Gateway (:8100) — Healthcheck auf /health
  postgres:         # PostgreSQL 16 (:5432) — pg_isready Healthcheck
  redis:            # Redis 7 (:6379) — redis-cli ping Healthcheck
```

## Healthchecks

Zwei Ebenen von Health-Endpoints:

**Docker-Container Healthcheck** (Liveness — ist der Prozess da?):

```yaml
healthcheck:
  test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/livez/')\""]
  interval: 15s
  timeout: 5s
  retries: 3
  start_period: 30s
```

**Readiness Probe** (`/healthz/` — kann Traffic bedient werden?):

```json
{
  "status": "ok",
  "version": "1.0.0",
  "git_sha": "abc1234",
  "checks": {
    "database": {"status": "ok", "latency_ms": 1.2},
    "cache": {"status": "ok", "latency_ms": 0.8},
    "disk": {"status": "ok", "free_pct": 72.3},
    "migrations": {"status": "ok", "pending": 0}
  }
}
```

## Resource Limits

| Service | Memory Limit | Memory Reserved |
|---------|-------------|----------------|
| bfagent-web | 512 MB | 256 MB |
| postgres | 512 MB | — |
| redis | 192 MB | — |

## Expand/Contract Migration Pattern

```text
Phase 1 (EXPAND):  Neue Spalten/Tabellen hinzufügen (backward compatible)
  └── deploy-remote.sh führt `migrate --noinput` VOR Restart aus

Phase 2 (MIGRATE DATA): Daten in neue Spalten füllen
  └── Management Command oder Data Migration

Phase 3 (CONTRACT): Alte Spalten entfernen (separates Deploy)
  └── Erst wenn aller Code die neuen Spalten nutzt
```

**Regel:** Niemals destruktive Migrations (DROP COLUMN) im selben
Deploy wie den Code der die Spalte nicht mehr nutzt.
