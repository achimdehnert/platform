---
description: 3-Node Sync WSL ↔ GitHub ↔ Server — konsistenter Stand aller Repos auf allen Knoten
---

# /sync-repo — 3-Node Sync Workflow

**Das Problem:** Cascade schreibt gleichzeitig über filesystem MCP (WSL/lokal) und GitHub MCP (remote).
Resultat: lokale Repos divergieren → `git pull` scheitert mit "overwritten by merge" / "untracked files".

## Architektur

```
GitHub          = Single Source of Truth (immer autoritativ)
   ↑↓
WSL             = Git-Checkouts ${GITHUB_DIR:-$HOME/github}/<repo>  →  git pull --no-rebase
   ↓ SSH
Server          = /opt/platform/  → Git-Checkout  →  git pull --no-rebase
                  /opt/<app>/     → Docker-only   →  docker pull + compose up -d
```

**Was der Server NICHT hat:** Git-Checkouts der App-Repos (bfagent, travel-beat etc.).
Die laufen dort nur als Docker-Container. Updates kommen via `docker pull`, nicht `git pull`.

---

## Schnellreferenz

| Befehl | Was passiert |
|--------|--------------|
| `bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-repo.sh` | WSL: **CWD-Repo** syncen |
| `bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-repo.sh ${GITHUB_DIR:-$HOME/github}/bfagent` | WSL: explizites Repo |
| `bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-repo.sh --all` | WSL: alle 24 Repos |
| `bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-repo.sh --server` | Server: platform git pull + alle Apps docker pull |
| `bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-repo.sh --server platform` | Server: nur /opt/platform |
| `bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-repo.sh --server bfagent` | Server: nur bfagent docker pull |
| `bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-repo.sh --full` | WSL --all + Server alles (vollständig) |

---

## Normalfall: CWD-Repo nach Cascade-Session syncen

// turbo
```bash
bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-repo.sh
```

Synct das **aktuelle Verzeichnis** — von jedem Repo aus aufrufbar.

## Alle WSL-Repos syncen (24 Repos)

```bash
bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-repo.sh --all
```

Synct: platform, bfagent, travel-beat, weltenhub, risk-hub, pptx-hub, mcp-hub,
aifw, promptfw, authoringfw, nl2cad, weltenfw, cad-hub, trading-hub, wedding-hub,
dev-hub, coach-hub, 137-hub, billing-hub, illustration-hub, illustration-fw,
odoo-hub, infra-deploy, testkit

## Server syncen (nach ADR-Commits oder zwischen Deployments)

```bash
bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-repo.sh --server
```

Server-Aktionen:
- `/opt/platform/` → `git pull --no-rebase origin main`
- `/opt/bfagent-app/`, `/opt/travel-beat/`, etc. → `docker compose pull && up -d`

## Vollständiger 3-Node-Sync

```bash
bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-repo.sh --full
```

Dauer: ~30–60 Sekunden für alle Nodes.

---

## Sicherheitsgarantien

- **Kein `git reset --hard`** — lokale Arbeit geht nie verloren
- **Kein force-push** — GitHub wird nie überschrieben
- **Kein blindes `git stash drop`** — Stash wird nach Pull wiederhergestellt
- **Auto-commit** für Cascade-Patterns: `windsurf-rules/`, `scripts/`, `docs/adr/`,
  `.windsurf/workflows/`, `docs/CORE_CONTEXT.md`, `docs/AGENT_HANDOVER.md`
- **Stash + restore** für alles andere (`.env`, WIP-Code, temp-Dateien)
- **Backup-Branch** für unpushed commits: `backup/sync-TIMESTAMP`
- **Idempotent**: mehrfach ausführbar, keine Seiteneffekte

## Empfehlung: In täglichen Workflow integrieren

Am Anfang **jeder** Cascade-Session:
```bash
bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-repo.sh
```

Am Ende einer Session (nach ADR-Commits via GitHub MCP):
```bash
bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-repo.sh --full
```
