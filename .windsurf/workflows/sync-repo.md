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
WSL             = Git-Checkouts ~/github/<repo>  →  git pull --rebase
   ↓ SSH
Server          = /opt/platform/  → Git-Checkout  →  git pull --rebase
                  /opt/<app>/     → Docker-only   →  docker pull + compose up -d
```

**Was der Server NICHT hat:** Git-Checkouts der App-Repos (bfagent, travel-beat etc.).
Die laufen dort nur als Docker-Container. Updates kommen via `docker pull`, nicht `git pull`.

---

## Schnellreferenz

| Befehl | Was passiert |
|--------|--------------|
| `bash scripts/sync-repo.sh` | WSL: platform syncen (Normalfall) |
| `bash scripts/sync-repo.sh ~/github/bfagent` | WSL: einzelnes Repo |
| `bash scripts/sync-repo.sh --all` | WSL: alle 14 Repos |
| `bash scripts/sync-repo.sh --server` | Server: platform git pull + alle Apps docker pull |
| `bash scripts/sync-repo.sh --server platform` | Server: nur /opt/platform |
| `bash scripts/sync-repo.sh --server bfagent` | Server: nur bfagent docker pull |
| `bash scripts/sync-repo.sh --full` | WSL --all + Server alles (vollständig) |

---

## Normalfall: WSL nach Cascade-Session syncen

// turbo
```bash
cd ~/github/platform && bash scripts/sync-repo.sh
```

## Alle WSL-Repos syncen

```bash
bash scripts/sync-repo.sh --all
```

Synct: platform, bfagent, travel-beat, weltenhub, risk-hub, pptx-hub, mcp-hub,
aifw, promptfw, authoringfw, cad-hub, trading-hub, wedding-hub, dev-hub

## Server syncen (nach ADR-Commits oder zwischen Deployments)

```bash
bash scripts/sync-repo.sh --server
```

Server-Aktionen:
- `/opt/platform/` → `git pull --rebase origin main`
- `/opt/bfagent-app/`, `/opt/travel-beat/`, etc. → `docker compose pull && up -d`

## Vollständiger 3-Node-Sync

```bash
bash scripts/sync-repo.sh --full
```

Dauer: ~30–60 Sekunden für alle Nodes.

---

## Sicherheitsgarantien

- **Kein `git reset --hard`** — lokale Arbeit geht nie verloren
- **Kein force-push** — GitHub wird nie überschrieben
- **Auto-commit** für Cascade-Patterns: `windsurf-rules/`, `scripts/`, `docs/adr/`,
  `.windsurf/workflows/`, `docs/CORE_CONTEXT.md`, `docs/AGENT_HANDOVER.md`
- **Stash + restore** für alles andere (`.env`, WIP-Code, temp-Dateien)
- **Rebase-Fallback** auf merge wenn Konflikte entstehen
- **Idempotent**: mehrfach ausführbar, keine Seiteneffekte

## Empfehlung: In täglichen Workflow integrieren

Nach jeder Cascade-Session:
```bash
bash ~/github/platform/scripts/sync-repo.sh        # platform
# oder vollständig:
bash ~/github/platform/scripts/sync-repo.sh --full
```
