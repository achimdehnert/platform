---
description: Session starten — Kontext laden, Stand prüfen, sicher loslegen
---

# /session-start

> **Alias für `/agent-session-start`** — gleicher Workflow, kürzerer Name.
> Gegenstück: `/session-ende`

Führe **exakt** den Workflow aus `/agent-session-start` aus:

1. **Git Sync (Multi-Env)** — Alle Repos auf aktuellem Stand bringen:
```bash
# Im aktuellen Workspace-Repo:
git stash && git pull --rebase && git stash pop 2>/dev/null
# Falls Multi-Repo-Session (mcp-hub, platform, risk-hub):
for repo in mcp-hub platform risk-hub; do
  cd ~/github/$repo && git pull --rebase --quiet 2>/dev/null
done
```
→ Stellt sicher, dass WSL ↔ Dev Desktop synchron sind.
→ Bei Konflikten: `git stash pop` manuell lösen, NICHT automatisch force-pushen.

2. **Repo-Kontext laden** — AGENT_HANDOVER.md, CORE_CONTEXT.md, ADR-Index, `mcp14_get_context_for_task()`
3. **Health Dashboard** (bei Infra/Deploy-Sessions) — `mcp6_system_manage(action: health_dashboard)`
4. **Aufgabe klären** — Issue? Use Case? ADR? Governance?
5. **Branch-Status prüfen** — `git status && git log --oneline -5`
6. **Tests baseline** — `pytest tests/ -q --tb=no`
7. **Knowledge-Lookup** — Outline durchsuchen (Repo-Steckbrief, Task-Wissen, Lessons, Cascade-Aufträge)

## pgvector Warm-Start (ADR-154)

8. **Memory Warm-Start** — Relevante Memories aus früheren Sessions laden:
```
agent_memory_context(
  task_description: "<User-Aufgabe aus erster Nachricht>",
  top_k: 5
)
```
→ Zeigt relevante Session-Summaries, Error-Patterns und Lessons aus früheren Sessions.
→ Falls Ergebnisse: kurz zusammenfassen und in Arbeitsplan einbeziehen.
→ Falls leer: normal weiterarbeiten (Memory füllt sich über `/session-ende`).

9. **Delta-Check** — Was hat sich seit der letzten Session geändert?
```
get_session_delta()
```
→ Zeigt Entries die seit dem letzten Session-Ende geschrieben/aktualisiert wurden.
→ Relevant bei Multi-Agent oder wenn zwischen Sessions manuell gearbeitet wurde.

10. **Bekannte Fehler prüfen** (bei Bug-Fix-Sessions):
```
find_similar_errors(
  query: "<Fehlerbeschreibung aus User-Nachricht>",
  repo: "<aktuelles Repo>"
)
```
→ Falls bekannter Error-Pattern: Fix direkt anwenden statt neu debuggen.

11. **Wiederkehrende Fehler prüfen** (automatisch, jede Session):
```
check_recurring_errors()
```
→ Findet Error-Patterns die ≥3x aufgetreten sind (Eskalations-Schwelle).
→ Bei Treffern: **Deep Root-Cause Analysis** starten statt Quick-Fix.
→ 🟡 ESCALATED (3-5x): nachhaltige Lösung untersuchen.
→ 🔴 CRITICAL (≥6x): sofortige Analyse, Blocker für andere Tasks.

12. **Arbeitsplan aufstellen** — Schritte, Komplexität, Risk Level, Gate (unter Einbezug der Warm-Start-Ergebnisse + Eskalationen)

Vollständige Details: siehe `agent-session-start.md`
