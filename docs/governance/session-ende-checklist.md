# Session-Ende — Abschluss-Checkliste

> Ausgelagert aus `.windsurf/workflows/session-ende.md` (2026-04-29, ADR-175)
> Wird am Ende des `/session-ende` Workflows konsultiert

---

## Checkliste (muss alles grün sein)

| # | Check | Status |
|---|-------|--------|
| 1 | Outline-Dokument geschrieben/aktualisiert | ☐ |
| 2 | pgvector Session-Summary gespeichert | ☐ |
| 3 | Error-Patterns erfasst (falls Bug-Fix) | ☐ |
| 4 | Alle Repos committed + pushed | ☐ |
| 5 | Platform gepusht → Workflows sync → project-facts aktuell | ☐ |
| 6 | Kein Repo dirty | ☐ |
| 7 | Keine .fixed/.updated Dateien übrig | ☐ |
| 8 | Blockierte Arbeit dokumentiert | ☐ |
| 9 | Docu-Drift-Check: Issue erstellt falls nötig (Phase 1b) | ☐ |
| 10 | Template-Drift-Check: Error-Drifts gefixt (Phase 1c) | ☐ |

---

## MCP-Server Quick-Reference

> ⚠️ MCP-Prefix ist environment-spezifisch — IMMER `project-facts.md` als Quelle nehmen!

### Dev Desktop (adehnert@dev-desktop)

| Prefix | Server | Zweck |
|--------|--------|-------|
| `mcp0_` | github | Issues, PRs, Repos, Files, Reviews |
| `mcp1_` | orchestrator | Memory, Task-Analyse, Plans, Evaluate, Verify |

### WSL / Prod-Server

| Prefix | Server | Zweck |
|--------|--------|-------|
| `mcp0_` | deployment-mcp | SSH, Docker, Git, DB, DNS, SSL, System |
| `mcp1_` | github | Issues, PRs, Repos, Files, Reviews |
| `mcp2_` | orchestrator | Memory, Task-Analyse, Agent-Team |
| `mcp3_` | outline-knowledge | Wiki: Runbooks, Konzepte, Lessons |
| `mcp4_` | paperless-docs | Dokumente, Rechnungen |
| `mcp5_` | platform-context | Architektur-Regeln, ADR-Compliance |
