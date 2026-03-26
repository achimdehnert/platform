---
description: Session beenden — Wissen in Outline sichern, Memory updaten
---

# /session-ende

> **Alias für `/knowledge-capture`** — gleicher Workflow, kürzerer Name.
> Gegenstück: `/session-start`

Führe **exakt** den Workflow aus `/knowledge-capture` aus:

1. **Session-Scan** (autonom) — Git-Logs prüfen, Features/Fixes/Deployments/Lessons identifizieren
2. **Outline durchsuchen** — Existiert schon ein Dokument?
3. **Klassifizieren** — Runbook / Konzept / Lesson / Update?
4. **Outline schreiben** — `create_runbook`, `create_concept`, `create_lesson` oder `update_document`
5. **Cross-Repo Tagging** — "Gilt für" Abschnitt bei Hub-übergreifendem Wissen
6. **Cascade Memory updaten** — Verweis auf Outline-Dokument

> **Der User muss NICHTS auflisten.** Der Agent scannt die Session autonom.

Vollständige Details: siehe `knowledge-capture.md`
