---
description: Session beenden — Wissen in Outline sichern, Memory updaten
---

# /session-ende

> Gegenstück: `/session-start`
> Zwei Umgebungen: **WSL** (`/home/dehnert/github/`) und **Dev Desktop** (`/home/devuser/github/`)
> **Der User muss NICHTS auflisten.** Der Agent scannt die Session autonom.

---

## Phase 1: Wissen sichern (Outline + Memory)

1. **Session-Scan** (autonom) — Git-Logs prüfen, Features/Fixes/Deployments/Lessons identifizieren
2. **Outline durchsuchen** — Existiert schon ein Dokument?
3. **Klassifizieren** — Runbook / Konzept / Lesson / Update?
4. **Outline schreiben** — `create_runbook`, `create_concept`, `create_lesson` oder `update_document`
5. **Cross-Repo Tagging** — "Gilt für" Abschnitt bei Hub-übergreifendem Wissen
6. **Cascade Memory updaten** — Verweis auf Outline-Dokument

---

## Phase 2: pgvector Memory schreiben (ADR-154)

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
  prevention: "<Wie vermeiden?>"
)
```

9. **Session-Stats prüfen** (optional, 1x pro Woche):
```
session_stats(days: 7)
```

---

## Phase 3: Git Sync — WSL ↔ Dev Desktop (IMMER am Ende)

### 3.1 Alle geänderten Repos committen + pushen

```bash
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
→ Commit-Message enthält `session-ende: auto-sync` zur Erkennung.
→ **NICHT ausführen** wenn der User explizit sagt "nicht pushen" oder ein PR-Review läuft.

### 3.2 Platform-Workflows verteilen (falls platform geändert wurde)

```bash
# Nur wenn platform/.windsurf/workflows/ geändert wurde:
cd ~/github/platform && git diff --name-only HEAD~1 | grep -q ".windsurf/workflows/" && \
  GITHUB_DIR=~/github bash scripts/sync-workflows.sh 2>&1 | grep -cE "LINK|REPLACE"
```
→ Stellt sicher, dass Workflow-Änderungen sofort in alle Repos propagiert werden.

### 3.3 Finale Prüfung — Kein Repo darf dirty sein

```bash
dirty=0
for repo in ~/github/*/; do
  if [ -n "$(cd "$repo" && git status --porcelain 2>/dev/null)" ]; then
    echo "DIRTY: $(basename $repo)"
    dirty=$((dirty + 1))
  fi
done
[ $dirty -eq 0 ] && echo "✅ Alle Repos clean" || echo "⚠️ $dirty Repos noch dirty"
```
→ Ziel: **0 dirty Repos** am Session-Ende.
→ Falls dirty: nochmal committen + pushen oder User fragen.

---

## Checkliste (muss alles grün sein)

| # | Check | Status |
|---|-------|--------|
| 1 | Outline-Dokument geschrieben/aktualisiert | ☐ |
| 2 | pgvector Session-Summary gespeichert | ☐ |
| 3 | Error-Patterns erfasst (falls Bug-Fix) | ☐ |
| 4 | Alle Repos committed + pushed | ☐ |
| 5 | Workflow-Symlinks aktuell | ☐ |
| 6 | Kein Repo dirty | ☐ |
