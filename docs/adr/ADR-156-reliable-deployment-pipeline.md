---
status: proposed
date: 2026-04-02
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
related:
  - ADR-075-deployment-agent.md
  - ADR-090-cicd-pipeline-python-postgres.md
  - ADR-120-unified-deployment-pipeline.md
---

# ADR-156: Reliable Deployment Pipeline — Solving SSH/MCP Timeout and Multi-Node Sync

## Metadaten

| Attribut          | Wert                                                        |
|-------------------|-------------------------------------------------------------|
| **Status**        | Proposed                                                    |
| **Scope**         | platform-wide (alle 18+ Hub-Repos, Prod-Server, Dev Desktop) |
| **Erstellt**      | 2026-04-02                                                  |
| **Autor**         | Achim Dehnert                                               |

## Problemstellung

### Kernproblem

Deployments über `deployment-mcp` / `ssh_manage` hängen regelmäßig bei Operationen >30 Sekunden. Das betrifft:

| Operation | Typische Dauer | Symptom |
|-----------|---------------|---------|
| `docker compose pull` | 30-120s | WaitDelay expired |
| `docker compose up -d` | 10-60s | SSH-Heredoc-Timeout |
| `python manage.py migrate` | 5-30s | Sporadisch |
| `docker build` | 120-600s | Immer |
| `collectstatic` | 10-30s | Sporadisch |

### Root Causes (aus Error-Pattern-DB)

1. **MCP-SSH-Tool WaitDelay**: Internes Timeout bei langen SSH-Sessions (~30s)
2. **SSH KeepAlive**: Lange Heredoc-Sessions werden durch SSH-KeepAlive unterbrochen
3. **Kein Background-Mechanismus**: MCP wartet synchron auf Command-Output
4. **Kein standardisiertes Deploy-Script**: Jedes Repo hat eigene Mechanismen
5. **Multi-Node-Sync**: Dev Desktop ↔ GitHub ↔ Prod-Server Drift

### Betroffene Umgebungen

| Umgebung | Rolle | Problem |
|----------|-------|---------|
| Dev Desktop (88.99.38.75) | Development + MCP-Server | SSH zu Prod hängt bei Writes |
| Prod-Server (88.198.191.108) | 18+ Container, Deployments | Empfängt Deploys |
| GitHub Actions (Self-Hosted Runner) | CI/CD | Runner auf Prod, konkurriert mit Apps |

## Decision Drivers

1. **Zuverlässigkeit**: Deployments MÜSSEN deterministisch funktionieren (kein Hängen)
2. **Geschwindigkeit**: Deploy sollte <2 Min (ohne Build) dauern
3. **Idempotenz**: Gleicher Deploy-Befehl = gleiches Ergebnis
4. **Observability**: Jeder Deploy-Schritt muss geloggt und nachvollziehbar sein
5. **Agent-Kompatibilität**: Cascade/Deployment-Agent muss Deploys autonom ausführen können
6. **Rollback**: Jederzeit auf vorherigen Stand zurückkehren

## Considered Options

### Option A: Server-Side Deploy-Script (nohup-Pattern)

**Prinzip**: Kurzer SSH-Write-Befehl platziert Script auf Server, startet es im Background.

```
Dev Desktop → SSH → Server: write deploy.sh → nohup deploy.sh &
Dev Desktop → SSH → Server: tail -f /var/log/deploy/<repo>.log (poll)
```

**Pro**:
- Löst Timeout-Problem sofort (SSH nur für Schreibvorgang)
- Einfach zu implementieren
- Log auf Server persistent

**Contra**:
- Kein atomares Rollback
- Keine Orchestrierung zwischen Steps
- Log-Polling ist fragil

### Option B: GitHub Actions als einziger Deploy-Kanal

**Prinzip**: Alle Deploys laufen über GitHub Actions — MCP triggert nur Dispatch.

```
Dev Desktop → MCP → GitHub API: dispatch deploy.yml
Dev Desktop → MCP → GitHub API: poll run_status
```

**Pro**:
- Kein SSH-Timeout-Problem (Runner läuft lokal auf Server)
- Full Audit-Trail in GitHub
- Standardisiert für alle Repos

**Contra**:
- Runner konkurriert mit Prod-Apps um Ressourcen
- Latenz (Workflow-Start 5-15s, Queue)
- GitHub-Abhängigkeit für jeden Deploy

### Option C: Hybrid — Server-Side Agent + GitHub Actions Fallback

**Prinzip**: Leichtgewichtiger Deploy-Agent auf dem Prod-Server, gesteuert über standardisiertes Protokoll.

```
1. Dev/MCP → SSH (kurz): POST deploy-request an lokalen Agent
2. Agent auf Server: führt deploy.sh aus, loggt in /var/log/deploy/
3. Dev/MCP → SSH (kurz): GET deploy-status (poll)
4. Fallback: GitHub Actions Workflow als Alternative
```

**Pro**:
- Kein Timeout (Agent läuft lokal)
- Minimaler SSH-Overhead (nur kurze HTTP-ähnliche Befehle)
- Offline-fähig (Agent auf Server)
- GitHub Actions als Backup

**Contra**:
- Neuer Service auf Server (Wartung)
- Mehr Komplexität

## Entscheidung

### Gewählt: Option A (Server-Side Deploy-Script) als Phase 1, Option C als Langfrist-Ziel

**Begründung**: Option A löst das akute Problem sofort mit minimalem Aufwand. Option C ist das strategische Ziel, aber erfordert mehr Planung.

## Implementierungsplan

### Phase 1: Standardisiertes Deploy-Script (sofort)

Jedes Hub-Repo bekommt ein `/opt/<repo>/deploy.sh`:

```bash
#!/bin/bash
set -euo pipefail
REPO="$1"
LOG="/var/log/deploy/${REPO}-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

echo "=== Deploy $REPO started at $(date) ==="

cd /opt/$REPO

# 1. Pull latest image
docker compose -f docker-compose.prod.yml pull web

# 2. Run migrations (if migrate service exists)
docker compose -f docker-compose.prod.yml run --rm migrate 2>/dev/null || \
  docker compose -f docker-compose.prod.yml exec -T web python manage.py migrate --noinput || true

# 3. Recreate web + workers
docker compose -f docker-compose.prod.yml up -d --force-recreate web
docker compose -f docker-compose.prod.yml up -d --force-recreate celery 2>/dev/null || true

# 4. Health check (max 30s)
for i in $(seq 1 6); do
  if docker compose -f docker-compose.prod.yml exec -T web python -c "
import urllib.request; urllib.request.urlopen('http://localhost:8000/livez/')
" 2>/dev/null; then
    echo "=== Health check PASSED ==="
    echo "=== Deploy $REPO completed at $(date) ==="
    exit 0
  fi
  echo "Health check attempt $i/6 failed, waiting 5s..."
  sleep 5
done

echo "=== HEALTH CHECK FAILED — consider rollback ==="
exit 1
```

### MCP-Aufruf (Agent-Pattern)

```python
# 1. Script schreiben (kurzer SSH-Write)
ssh_manage(action="file_write", path="/opt/<repo>/deploy.sh", content=SCRIPT)

# 2. Deploy im Background starten (kurzer SSH-Exec)
ssh_manage(action="exec", command="nohup bash /opt/<repo>/deploy.sh <repo> &", timeout=10)

# 3. Status pollen (kurzer SSH-Read)
ssh_manage(action="file_read", path="/var/log/deploy/<repo>-*.log", tail=20)
```

### Phase 2: Deploy-Status-API (mittelfristig)

Einfacher Status-Endpoint auf dem Server:
- `GET /deploy/status/<repo>` → JSON mit letztem Deploy-Status
- Implementierung: kleines Python-Script das Log-Files parsed
- MCP kann per `http_check` pollen statt SSH

### Phase 3: Server-Side Deploy-Agent (langfristig — Option C)

- Systemd-Service auf Prod-Server
- REST-API für Deploy-Trigger, Status, Rollback
- Queue für parallele Deploys
- Integriertes Rollback (vorheriges Image-Tag speichern)

## Sofort-Maßnahmen (Quick Wins)

1. **`/var/log/deploy/` Verzeichnis** auf Prod-Server erstellen
2. **`deploy.sh` Template** in `platform/deployment/templates/` bereitstellen
3. **MCP-Workflow** `/ship` anpassen auf nohup-Pattern
4. **Logrotate** für Deploy-Logs (7 Tage Retention)

## Risiken

| Risiko | Mitigation |
|--------|-----------|
| Deploy-Script hängt auf Server | Timeout in Script (max 300s), Logfile zeigt Status |
| Parallele Deploys | Lock-File `/tmp/deploy-<repo>.lock` |
| Log-Verzeichnis voll | Logrotate, max 7 Tage |
| SSH-Key-Rotation | Nicht betroffen (Standard-SSH-Keys) |

## Confirmation

- [ ] `/var/log/deploy/` auf Prod-Server erstellt
- [ ] `deploy.sh` Template in platform/deployment/templates/
- [ ] `/ship` Workflow auf nohup-Pattern umgestellt
- [ ] Erster erfolgreicher Deploy über neues Pattern
- [ ] Logrotate konfiguriert

## Changelog

| Version | Datum | Änderung |
|---------|-------|----------|
| v1 | 2026-04-02 | Initial — Problemanalyse + 3 Optionen + Phasenplan |
