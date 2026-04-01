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

## Git Sync (Multi-Env) — WSL ↔ Dev Desktop

6b. **Alle geänderten Repos committen + pushen:**
```bash
# Alle Repos mit uncommitted changes finden und pushen:
for repo in ~/github/*/; do
  cd "$repo"
  if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    repo_name=$(basename "$repo")
    echo "PUSH $repo_name..."
    git add -A
    git commit -m "session-ende: auto-sync $(date +%Y-%m-%d)"
    git push
  fi
done
```
→ Stellt sicher, dass die andere Umgebung (WSL / Dev Desktop) beim nächsten `/session-start` den aktuellen Stand hat.
→ Bei WIP-Branches: Commit-Message enthält `session-ende: auto-sync` zur Erkennung.
→ **NICHT ausführen** wenn der User explizit sagt "nicht pushen" oder ein PR-Review läuft.

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
log_error_pattern(
  repo: "<repo>",
  symptom: "<Was ging schief?>",
  root_cause: "<Warum?>",
  fix: "<Was wurde gefixt?>",
  prevention: "<Wie vermeiden?>",
  error_type: "<sql|auth|config|deployment|...>"
)
```
→ SHA-Hash-Dedup: gleicher Symptom+Repo erzeugt keinen Duplikat-Eintrag.

9. **Session-Stats prüfen** (optional, 1x pro Woche reicht):
```
session_stats(days: 7)
→ Zeigt: Sessions, Entries, Error-Patterns der letzten 7 Tage
→ Bei auffällig vielen Errors: Patterns reviewen via find_similar_errors()
```

> **Der User muss NICHTS auflisten.** Der Agent scannt die Session autonom.

Vollständige Details: siehe `knowledge-capture.md`
