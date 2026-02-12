# Proposal: Universelles Server Build & Deploy Script

**Status:** Implementiert + getestet (Trading-Hub)
**Scope:** Alle Docker-basierten Apps auf 88.198.191.108
**Script:** `platform/scripts/server-build-deploy.sh`

## Problem

### 1. MCP ssh_manage Timeout

Der `deployment-mcp` SSH-Client (`ssh_manage`) hängt bei Operationen >60s:

- Docker Build (10-15 Min bei ML-Dependencies)
- Große `pip install` (PyTorch, Stable-Baselines3)
- `git clone` großer Repos

**Root Cause:** Windows `ProactorEventLoop` + SSH-Semaphore (serialisierte Calls)
führt zu Deadlocks bei langen Sessions. Betrifft `exec`, `run_script` UND `file_write`.

### 2. Kein einheitlicher Build-Prozess

Jede App hat eigene CI/CD-Pipelines, aber für manuelle/Cascade-Deploys fehlt ein Standard-Verfahren.

## Lösung

### A. WSL SSH als MCP-Fallback

Für alle SSH-Operationen >30s direkt WSL nutzen:

```powershell
# Statt MCP ssh_manage:
wsl ssh -o ConnectTimeout=10 root@88.198.191.108 'COMMAND'

# Dateitransfer:
wsl scp FILE root@88.198.191.108:/opt/APP/FILE
```

### B. Background Build & Deploy Script

Ein universelles Script das:

1. Im Hintergrund läuft (`nohup`)
2. Status in einer Datei schreibt (pollbar)
3. Für jede App funktioniert (auto-detect compose, ports, deps)

**Usage:**

```bash
# Im Hintergrund starten (kehrt sofort zurück)
wsl ssh root@88.198.191.108 'nohup bash /opt/build-deploy.sh <app-name> > /dev/null 2>&1 &'

# Status pollen
wsl ssh root@88.198.191.108 'cat /opt/<app-name>/build-deploy.status'

# Log anschauen
wsl ssh root@88.198.191.108 'tail -20 /opt/<app-name>/build-deploy.log'
```

**Status-Phasen:**
`STARTED` → `TOKEN` → `CLONE` → `DEPS` → `BUILD` → `BUILD_OK` → `PUSH` → `PUSH_OK` → `DEPLOY` → `DEPLOY_OK` → `HEALTH` → `DONE:OK`

## Kompatibilität

| App         | Getestet | Compose-Pfad                     | Port | Health     |
| ----------- | -------- | -------------------------------- | ---- | ---------- |
| trading-hub | ✅        | `docker-compose.prod.yml`        | 8088 | `/livez/`  |
| travel-beat | ✅ Port   | `docker-compose.prod.yml`        | 8089 | `/livez/`  |
| risk-hub    | ✅ Port   | `docker-compose.prod.yml`        | 8090 | `/health/` |
| weltenhub   | ✅ Port   | `docker-compose.prod.yml`        | 8081 | `/health/` |
| bfagent     | ✅ Port   | `docker-compose.prod.yml`        | 8091 | `/healthz/`|
| wedding-hub | ✅ Port   | `docker-compose.prod.yml`        | 8093 | `/livez/`  |
| pptx-hub    | N/A      | `docker-compose.prod.yml`        | 8020 | `/health/` |

Das Script erkennt Compose-Pfad, Image-Name und Port automatisch.

## Wann welches Tool nutzen

| Operation                      | MCP ssh_manage | WSL SSH        |
| ------------------------------ | -------------- | -------------- |
| Container Logs (<100 Zeilen)   | ✅              | ✅              |
| Container Status               | ✅              | ✅              |
| Docker Build                   | ❌ hängt        | ✅ (nohup)      |
| pip install                    | ❌ hängt        | ✅              |
| git clone (große Repos)        | ❌ hängt        | ✅              |
| Datei lesen (<1MB)             | ✅              | ✅              |
| Datei schreiben                | ❌ hängt        | ✅ (scp)        |
| Migrations                     | ⚠️ meist OK    | ✅              |

## Langfristige Empfehlung

1. **MCP ssh_manage fixen** — `asyncio.Semaphore` durch Thread-Pool ersetzen
2. **CI/CD als primären Build-Weg nutzen** — alle Repos auf Platform Reusable Workflows migrieren
3. **Dieses Script als Notfall-/Cascade-Deploy** behalten für Fälle wo CI/CD zu langsam ist
