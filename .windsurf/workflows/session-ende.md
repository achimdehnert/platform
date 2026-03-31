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

## pgvector Memory schreiben (ADR-154)

Nach Schritt 6, **automatisch** folgende Memory-Operationen ausführen:

7. **Session-Summary in pgvector speichern:**
```
agent_memory_upsert(
  entry_key: "session:<YYYY-MM-DD>:<repo>",
  entry_type: "context",
  title: "Session <date> — <repo>: <1-Zeile Summary>",
  content: "<Was wurde erledigt, welche Entscheidungen, welche Dateien>",
  tags: ["session", "<repo>", "<task-type>"]
)
```

8. **Error-Patterns erfassen** (nur bei Bug-Fixes in dieser Session):
```
agent_memory_upsert(
  entry_key: "error:<repo>:<symptom-hash>",
  entry_type: "error_pattern",
  title: "Error: <Symptom-Kurzform>",
  content: "Symptom: ...\nRoot Cause: ...\nFix: ...\nPrevention: ...",
  tags: ["error", "<repo>", "<error-type>"]
)
```

9. **Decay Cleanup** — alte irrelevante Entries abwerten (optional, 1x pro Tag reicht):
```
Falls heute noch kein gc() lief:
agent_memory_search(query: "gc-marker", entry_type: "context")
→ Wenn kein heutiger Marker: im Python-Smoke-Test gc() triggern
```

> **Der User muss NICHTS auflisten.** Der Agent scannt die Session autonom.

Vollständige Details: siehe `knowledge-capture.md`
