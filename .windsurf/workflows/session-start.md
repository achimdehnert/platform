---
description: Session starten — Kontext laden, Stand prüfen, sicher loslegen
---

# /session-start

> **Alias für `/agent-session-start`** — gleicher Workflow, kürzerer Name.
> Gegenstück: `/session-ende`

Führe **exakt** den Workflow aus `/agent-session-start` aus:

1. **Repo-Kontext laden** — AGENT_HANDOVER.md, CORE_CONTEXT.md, ADR-Index, `mcp14_get_context_for_task()`
2. **Health Dashboard** (bei Infra/Deploy-Sessions) — `mcp6_system_manage(action: health_dashboard)`
3. **Aufgabe klären** — Issue? Use Case? ADR? Governance?
4. **Repo syncen** — `bash ~/github/platform/scripts/sync-repo.sh`
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

9. **Arbeitsplan aufstellen** — Schritte, Komplexität, Risk Level, Gate (unter Einbezug der Warm-Start-Ergebnisse)

Vollständige Details: siehe `agent-session-start.md`
