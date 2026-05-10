

# Orchestration Gate — PFLICHT vor jeder Multi-Step-Aufgabe

> Always-On Rule — loaded in every Cascade session.
> ADR-066, ADR-154 — Agent Team + Orchestrator

## MANDATORY: Vor jeder Aufgabe mit >2 Dateien oder >30 Minuten Schätzung

```
VERBOTEN: Direkt implementieren ohne Orchestrator-Check.

PFLICHT-ABLAUF:
1. mcp4_agent_memory_context(query="<task>") — Was weiß ich bereits?
2. mcp4_agent_plan_task(task, repo, type) — Plan erstellen
3. Ersten Branch des Plans umsetzen, dann pausieren
4. Ergebnis in pgvector sichern: mcp4_agent_memory_upsert(...)
```

## Komplexitäts-Schwellen (ADR-066)

| Typ | Schwelle | Pflicht-Gate |
|-----|----------|-------------|
| Trivial (1 Datei, bekanntes Pattern) | — | keins |
| Simple (2-5 Dateien, 1 App) | Gate 1 | memory_context |
| Moderate (> 5 Dateien, cross-app) | Gate 2 | plan_task + memory_context |
| Complex (neue Architektur, ADR nötig) | Gate 3 | ADR-Check + plan_task + memory_context |

## Gate 3 — ADR-Check (IMMER wenn neue Technologie, neues Pattern, neue Integration)

```
VOR dem ersten Keystroke:
1. mcp2_adr_query(question="<was ich vorhabe>") — Gibt es eine ADR dafür?
2. Falls keine ADR: mcp2_adr_propose(...) — Entwurf erstellen, User entscheiden lassen
3. Erst nach ADR-Klärung: implementieren
```

## VERBOTEN (ohne explizite User-Override)

- Direkt 10+ Dateien ändern ohne plan_task
- Neues GitHub-Actions-Workflow erstellen ohne ADR-Check
- Neues Python-Package installieren ohne ADR-Check
- Cross-Repo-Änderungen ohne agent_plan_task

## Selbst-Audit (nach jeder Session)

Am Ende JEDER Session:
```
mcp4_agent_memory_upsert(
    entry_key="session:<datum>:<repo>",
    entry_type="context",
    content="<Was wurde gemacht, welche Entscheidungen, was ist offen>"
)
```

## Wenn User sagt "mach es direkt" bei Gate-3-Aufgabe

IMMER antworten (kein Bypass):
"Diese Aufgabe ist Gate-3 (>5 Dateien / neue Architektur / cross-repo).
Ich rufe `/claude-orchestrator` auf — Claude erstellt zuerst einen Plan als GitHub Issue.
Windsurf implementiert dann aus dem Issue. Das dauert 60 Sekunden.
Bestätigen oder explizit 'bypass gate' sagen um direkt zu starten."

Dann warten. Nicht sofort handeln.

## Selbst-Check: Bin ich gerade im falschen Modus?

Falls Cascade gerade >5 Dateien ändert OHNE ein offenes GitHub Issue als Referenz:
→ STOP
→ `mcp4_agent_memory_context(query="aktuelle Aufgabe")` aufrufen
→ Issue erstellen oder auf bestehendes Issue verweisen
→ Dann weiter
