---
description: Session beenden — Wissen in Outline sichern, Memory updaten
---

# /session-ende

> Gegenstück: `/session-start`
> Zwei Umgebungen: **WSL** (`/home/dehnert/github/`) und **Dev Desktop** (`/home/devuser/github/`)
> **Der User muss NICHTS auflisten.** Der Agent scannt die Session autonom.

---

## Phase 0: Blockierte Arbeit dokumentieren (NEU — Lesson 2026-04-05)

Falls während der Session Arbeit blockiert wurde (Shell-Hang, MCP-Fehler, Token-Probleme):

```
Prüfe:
1. Gibt es .fixed / .updated / .new Dateien die noch nicht übernommen wurden?
2. Gibt es unbeantwortete Fragen an den User?
3. Gibt es CI/CD Runs die noch verifiziert werden müssen?

Falls ja: Explizit als TODO dokumentieren mit konkretem Befehl zur Übernahme.
```

> Lesson Learned: Wenn Tools blockiert sind, ist es besser die Lösung in einer
> .fixed-Datei zu hinterlegen als die Session ergebnislos zu beenden.

---

## Phase 1: Wissen sichern (Outline + Memory)

1. **Session-Scan** (autonom) — Git-Logs prüfen, Features/Fixes/Deployments/Lessons identifizieren
2. **Outline durchsuchen** — Existiert schon ein Dokument?
3. **Klassifizieren** — Runbook / Konzept / Lesson / Update?
4. **Outline schreiben** — `mcp3_create_runbook`, `mcp3_create_concept`, `mcp3_create_lesson` oder `mcp3_update_document`
5. **Cross-Repo Tagging** — "Gilt für" Abschnitt bei Hub-übergreifendem Wissen
6. **Cascade Memory updaten** — Verweis auf Outline-Dokument

---

## Phase 1b: Docu-Drift-Check (automatisch — NEU 2026-04-23)

Für jedes **in dieser Session geänderte Repo** automatisch prüfen:

```bash
REPO=$(git rev-parse --show-toplevel 2>/dev/null)
REPO_NAME=$(basename "$REPO")

# Trigger-Bedingungen prüfen
VER_CODE=$(grep -r '__version__\|^version' "$REPO/pyproject.toml" 2>/dev/null | grep -oP '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
VER_README=$(head -10 "$REPO/README.md" 2>/dev/null | grep -oP '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
CL_ENTRIES=$(head -15 "$REPO/CHANGELOG.md" 2>/dev/null | grep -c '\[.*\]' || echo 0)
NEW_PY=$(git -C "$REPO" diff --name-only HEAD~1 2>/dev/null | grep -c '\.py$' || echo 0)

echo "Repo: $REPO_NAME | v_code=$VER_CODE | v_readme=$VER_README | cl=$CL_ENTRIES | new_py=$NEW_PY"
```

**Issue automatisch erstellen wenn EINES der folgenden zutrifft:**

| Bedingung | Bedeutung |
|-----------|-----------|
| `v_code != v_readme` | README-Version veraltet |
| `cl_entries == 0` | CHANGELOG noch leer |
| `new_py > 0` AND kein Outline-Eintrag | neues Modul, undokumentiert |

```
Falls Trigger zutrifft:
mcp1_create_issue(
  owner: "achimdehnert",
  repo: "platform",
  title: "[docu-update] <REPO_NAME> — <Grund>",
  body: "Automatisch erkannt in session-ende.\n\nTrigger: <was ausgelöst hat>\n\nAcceptance Criteria:\n- [ ] README.md Version = <VER_CODE>\n- [ ] CHANGELOG.md hat Eintrag\n- [ ] Outline-Eintrag aktuell\n- [ ] Platform-Übersicht aktualisiert",
  labels: ["documentation", "docu-update", "automated"]
)
```

→ **Kein Issue erstellen** wenn: nur Tests geändert, nur Bug-Fix ohne API-Änderung, Issue für dieses Repo bereits offen.

→ Vorher prüfen ob bereits ein offenes Issue existiert:
```
mcp1_list_issues(owner: "achimdehnert", repo: "platform",
  labels: ["docu-update"], state: "open")
→ Nur erstellen wenn kein Issue mit "[docu-update] <REPO_NAME>" bereits offen.
```

---

## Phase 2: pgvector Memory schreiben (ADR-154)

7. **Session-Summary in pgvector speichern:**
```
mcp2_agent_memory_upsert(
  entry_key: "session:<YYYY-MM-DD>:<repo>",
  entry_type: "context",
  title: "Session <date> — <repo>: <1-Zeile Summary>",
  content: "<Was wurde erledigt, welche Entscheidungen, welche Dateien>",
  tags: ["session", "<repo>", "<task-type>"]
)
```

8. **Error-Patterns erfassen** (nur bei Bug-Fixes in dieser Session):
```
mcp2_log_error_pattern(
  repo: "<repo>",
  symptom: "<Was ging schief?>",
  root_cause: "<Warum?>",
  fix: "<Was wurde gefixt?>",
  prevention: "<Wie vermeiden?>"
)
```

9. **Session-Stats prüfen** (optional, 1x pro Woche):
```
mcp2_session_stats(days: 7)
```

---

## Phase 3: Git Sync — WSL ↔ Dev Desktop (IMMER am Ende)

### 3.1 Alle geänderten Repos committen + pushen

```bash
for repo in ~/github/*/; do
  cd "$repo"
  if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    repo_name=$(basename "$repo")
    # Spezifische Commit-Message statt generisch
    changes=$(git diff --stat --cached 2>/dev/null; git diff --stat 2>/dev/null)
    echo "PUSH $repo_name..."
    git add -A
    git commit -m "session-ende($repo_name): $(date +%Y-%m-%d) — $(git diff --cached --stat | tail -1)"
    git push
  fi
done
```
→ Commit-Message enthält **Repo-Name + Änderungsstatistik** statt nur `auto-sync`.
→ **NICHT ausführen** wenn der User explizit sagt "nicht pushen" oder ein PR-Review läuft.

### 3.1b Cleanup: Temporäre Dateien entfernen

```bash
# .fixed / .updated / .new Dateien die erfolgreich übernommen wurden
find ~/github/ -maxdepth 4 -name "*.fixed" -o -name "*.updated" -o -name "*.new" 2>/dev/null | head -10
```
→ Falls vorhanden: Prüfen ob übernommen, dann löschen. Falls NICHT übernommen → User warnen.

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

### 3.4 Fallback bei Shell-Hang

Falls Shell blockiert ist, nutze GitHub MCP für kritische Pushes:
```
mcp1_push_files(owner: "achimdehnert", repo: "<repo>", branch: "main",
  files: [{"path": "<pfad>", "content": "<inhalt>"}],
  message: "session-ende: <beschreibung>")
```
→ Funktioniert nur für **public Repos** oder Repos mit Write-Token.
→ Für private Repos: User muss manuell pushen.

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
| 7 | Keine .fixed/.updated Dateien übrig | ☐ |
| 8 | Blockierte Arbeit dokumentiert | ☐ |
| 9 | Docu-Drift-Check: Issue erstellt falls nötig (NEU) | ☐ |

---

## MCP-Server Quick-Reference (aktuell)

| Prefix | Server | Zweck |
|--------|--------|-------|
| `mcp0_` | deployment-mcp | SSH, Docker, Git, DB, DNS, SSL, System |
| `mcp1_` | github | Issues, PRs, Repos, Files, Reviews |
| `mcp2_` | orchestrator | Task-Analyse, Agent-Team, Tests, Lint, Memory |
| `mcp3_` | outline-knowledge | Wiki: Runbooks, Konzepte, Lessons |
| `mcp4_` | paperless-docs | Dokumente, Rechnungen |
| `mcp5_` | platform-context | Architektur-Regeln, ADR-Compliance |
