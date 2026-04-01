---
description: Session starten — Kontext laden, Stand prüfen, sicher loslegen
---

# /session-start

> Gegenstück: `/session-ende`
> Zwei Umgebungen: **WSL** (`/home/dehnert/github/`) und **Dev Desktop** (`/home/devuser/github/`)

---

## Phase 0: Umgebung synchronisieren (IMMER zuerst)

### 0.1 Platform-Repo pullen (enthält Workflows + ADRs)

// turbo
```bash
cd ~/github/platform && git pull --rebase --quiet
```

### 0.2 Workflow-Symlinks aktualisieren

// turbo
```bash
GITHUB_DIR=~/github bash ~/github/platform/scripts/sync-workflows.sh 2>&1 | grep -E "LINK|REPLACE|WARN" | head -20
```
→ Stellt sicher, dass alle Repos die aktuellen Workflows haben.
→ Neue Workflows in platform werden automatisch verteilt.

### 0.3 Aktuelles Workspace-Repo + Kern-Repos synchronisieren

// turbo
```bash
# Aktuelles Repo
git stash --quiet 2>/dev/null
git pull --rebase --quiet
git stash pop --quiet 2>/dev/null

# Kern-Repos (MCP-Infrastruktur)
for repo in mcp-hub platform risk-hub; do
  (cd ~/github/$repo && git pull --rebase --quiet 2>/dev/null) &
done
wait
echo "Git Sync done"
```
→ Stellt sicher, dass WSL ↔ Dev Desktop synchron sind.
→ Bei Konflikten: `git stash pop` manuell lösen, NICHT force-pushen.

### 0.4 SSH Tunnel prüfen (nur Dev Desktop, für pgvector Memory)

```bash
# Nur auf Dev Desktop (88.99.38.75):
ss -tlnp | grep 15435 || sudo systemctl start ssh-tunnel-postgres
```

---

## Phase 1: Kontext laden

1. **Repo-Kontext laden** — AGENT_HANDOVER.md, CORE_CONTEXT.md, ADR-Index, `get_context_for_task()`
2. **Health Dashboard** (bei Infra/Deploy-Sessions) — `system_manage(action: health_dashboard)`
3. **Aufgabe klären** — Issue? Use Case? ADR? Governance?
4. **Branch-Status prüfen** — `git status && git log --oneline -5`
5. **Tests baseline** — `pytest tests/ -q --tb=no` (falls vorhanden)
6. **Knowledge-Lookup** — Outline durchsuchen (Repo-Steckbrief, Task-Wissen, Lessons, Cascade-Aufträge)

---

## Phase 2: pgvector Warm-Start (ADR-154)

7. **Memory Warm-Start** — Relevante Memories aus früheren Sessions laden:
```
agent_memory_context(
  task_description: "<User-Aufgabe aus erster Nachricht>",
  top_k: 5
)
```
→ Zeigt relevante Session-Summaries, Error-Patterns und Lessons.
→ Falls leer: normal weiterarbeiten (Memory füllt sich über `/session-ende`).

8. **Delta-Check** — Was hat sich seit der letzten Session geändert?
```
get_session_delta()
```

9. **Bekannte Fehler prüfen** (bei Bug-Fix-Sessions):
```
find_similar_errors(query: "<Fehlerbeschreibung>", repo: "<aktuelles Repo>")
```

10. **Wiederkehrende Fehler prüfen** (automatisch, jede Session):
```
check_recurring_errors()
```
→ 🟡 ESCALATED (3-5x): nachhaltige Lösung untersuchen.
→ 🔴 CRITICAL (≥6x): sofortige Analyse, Blocker für andere Tasks.

---

## Phase 3: Arbeitsplan

11. **Arbeitsplan aufstellen** — Schritte, Komplexität, Risk Level, Gate (unter Einbezug der Warm-Start-Ergebnisse + Eskalationen)
