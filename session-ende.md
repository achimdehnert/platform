---
description: Session beenden — Wissen in Outline sichern, Memory updaten
---

# /session-ende

> Gegenstück: `/session-start`
> **Der User muss NICHTS auflisten.** Der Agent scannt die Session autonom.

---

## Platform Sync Loop (Prinzip)

```
Session Start:  GitHub ──pull──▶ platform ──sync──▶ alle Repos  (aktuell starten)
Session Ende:   Änderungen ──commit──▶ push ──▶ GitHub ──sync──▶ alle Repos  (sofort deployen)
```

> **Jede Verbesserung an Workflows, Rules oder Scripts landet nach der Session
> automatisch platform-weit in ALLEN Repos — beim nächsten Session-Start.**
> GitHub ist die einzige Source of Truth. Lokale Pfade sind irrelevant.

---

## Phase −0.1: Version-Banner (allererster Schritt)

// turbo
```bash
# GITHUB_DIR sicherstellen (analog session-start)
if ! grep -q "GITHUB_DIR" ~/.bashrc 2>/dev/null; then
  echo "" >> ~/.bashrc
  echo "export GITHUB_DIR=\"\$HOME/github\"" >> ~/.bashrc
  echo "⚙️  GITHUB_DIR in ~/.bashrc eingetragen"
fi
export GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"

PLATFORM_DIR="${GITHUB_DIR}/platform"
VERSION_BEFORE=$(cat "$PLATFORM_DIR/VERSION" 2>/dev/null || echo "unknown")
COMMIT_BEFORE=$(git -C "$PLATFORM_DIR" log -1 --format="%h" 2>/dev/null || echo "?")
echo ""
echo "┌─────────────────────────────────────────┐"
echo "│  🏁 SESSION ENDE                        │"
echo "│  Platform v${VERSION_BEFORE} (${COMMIT_BEFORE})        │"
echo "│  $(date '+%Y-%m-%d %H:%M')                       │"
echo "└─────────────────────────────────────────┘"
```

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

**Einmal am Session-Ende — scannt ALLE in dieser Session geänderten Repos.**

### Schritt 1: Alle angefassten Repos der Session ermitteln

```bash
# Alle Repos mit Commits in den letzten 8h (= diese Session)
for repo in ${GITHUB_DIR:-$HOME/github}/*/; do
  [[ "$(basename $repo)" == *.* ]] && continue
  last=$(git -C "$repo" log --since="8 hours ago" --oneline 2>/dev/null | wc -l)
  [ "$last" -gt 0 ] && echo "$(basename $repo)"
done
```

→ Ergibt Liste aller aktiven Repos dieser Session, z.B.:
```
iil-reflex
platform
risk-hub
```

### Schritt 2: Docu-Drift pro Repo prüfen

Für **jeden** Repo aus der Liste:

```bash
for REPO_NAME in <liste-aus-schritt-1>; do
  REPO=${GITHUB_DIR:-$HOME/github}/$REPO_NAME

  VER_CODE=$(grep -r '__version__\|^version' "$REPO/pyproject.toml" 2>/dev/null \
             | grep -oP '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
  VER_README=$(head -10 "$REPO/README.md" 2>/dev/null \
               | grep -oP '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
  CL_ENTRIES=$(head -15 "$REPO/CHANGELOG.md" 2>/dev/null | grep -c '\[.*\]' 2>/dev/null || echo 0)
  NEW_PY=$(git -C "$REPO" log --since="8 hours ago" --name-only --pretty="" 2>/dev/null \
           | grep -c '\.py$' || echo 0)

  echo "$REPO_NAME | v_code=$VER_CODE | v_readme=$VER_README | cl=$CL_ENTRIES | new_py=$NEW_PY"
done
```

### Schritt 3: Issues erstellen (nur bei Trigger)

**Trigger-Regeln** — Issue erstellen wenn EINES zutrifft:

| Bedingung | Trigger | Kein Issue wenn |
|-----------|---------|-----------------|
| `v_code != v_readme` | README-Version veraltet | `v_code` leer (kein Python-Package) |
| `cl_entries == 0` | CHANGELOG leer | nur Infra/Skript-Repo ohne pyproject.toml |
| `new_py >= 1` | neue .py Datei in Session | nur Tests (`test_*.py`) |

**Duplikat-Schutz** — immer zuerst prüfen:
```
mcp1_list_issues(owner: "achimdehnert", repo: "platform",
  labels: ["docu-update"], state: "open")
→ Nur erstellen wenn KEIN Issue "[docu-update] <REPO_NAME>" bereits offen.
```

**Issue erstellen:**
```
mcp1_create_issue(
  owner: "achimdehnert", repo: "platform",
  title: "[docu-update] <REPO_NAME> — <Trigger-Grund>",
  body: "Automatisch erkannt via session-ende Phase 1b.\n\n
Trigger: <v_code != v_readme | cl leer | neue .py>\n\n
Acceptance Criteria:\n
- [ ] README.md Version = <VER_CODE>\n
- [ ] CHANGELOG.md hat Eintrag für v<VER_CODE>\n
- [ ] Outline-Eintrag vorhanden + aktuell\n
- [ ] Platform-Übersicht aktualisiert (❌→✅)\n
- [ ] git commit + push",
  labels: ["documentation", "docu-update", "automated"]
)
```

→ **`platform`-Repo selbst**: kein docu-update Issue — platform ist Meta-Repo.

---

## Phase 1c: Template-Drift-Check (automatisch — NEU 2026-04-28)

**Nur für Repos mit Änderungen in dieser Session — nur Error-Level (kein Lärm).**

```bash
PLATFORM_DIR="${GITHUB_DIR:-$HOME/github}/platform"

# Repos mit Commits in den letzten 8h (aus Phase 1b)
CHANGED_REPOS=$(for repo in ${GITHUB_DIR:-$HOME/github}/*/; do
  [[ "$(basename $repo)" == *.* ]] && continue
  last=$(git -C "$repo" log --since="8 hours ago" --oneline 2>/dev/null | wc -l)
  [ "$last" -gt 0 ] && echo "$(basename $repo)"
done | grep -v '^platform$')

if [ -n "$CHANGED_REPOS" ]; then
  echo "Drift-Check für: $CHANGED_REPOS"
  python3 "$PLATFORM_DIR/scripts/drift_check.py" $CHANGED_REPOS \
    --severity=error \
    --fail-on-error 2>&1 | grep -E '🔴|✅|Errors|Gesamt' || true
else
  echo "ℹ️  Keine geänderten Repos — Drift-Check übersprungen"
fi
```

→ **Nur `--severity=error`** — Warnings werden täglich per GitHub Action erfasst, nicht im Session-Ende-Lärm.
→ Bei 🔴 Errors: Sofort fixen oder als Issue dokumentieren (analog Phase 1b).
→ Keine Issues wenn `--fail-on-error` sauber durchläuft (Exit 0).

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
for repo in ${GITHUB_DIR:-$HOME/github}/*/; do
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
find ${GITHUB_DIR:-$HOME/github}/ -maxdepth 4 -name "*.fixed" -o -name "*.updated" -o -name "*.new" 2>/dev/null | head -10
```
→ Falls vorhanden: Prüfen ob übernommen, dann löschen. Falls NICHT übernommen → User warnen.

### 3.2 Platform-Workflows + project-facts verteilen (IMMER — kein Conditional)

> ⚠️ **PFLICHT — nicht überspringen.** Dieser Schritt stellt sicher, dass Verbesserungen
> sofort platform-weit aktiv sind. Egal ob etwas geändert wurde oder nicht.

// turbo
```bash
# 1. Platform-Repo committen + pushen (falls geändert)
cd ${GITHUB_DIR:-$HOME/github}/platform
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -m "chore(platform): session-ende $(date +%Y-%m-%d) — rules/workflows sync"
  git push
  echo "✅ platform gepusht"
else
  echo "ℹ️  platform: kein Commit nötig"
fi

# 2. Workflows an ALLE Repos verteilen (Symlinks aktualisieren)
GITHUB_DIR="${GITHUB_DIR:-$HOME/github}" \
  bash "${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-workflows.sh" \
  2>&1 | grep -cE "LINK|REPLACE" | xargs -I{} echo "{} Workflow-Symlinks aktualisiert"

# 3. project-facts.md für alle Repos aktualisieren
python3 "${GITHUB_DIR:-$HOME/github}/platform/scripts/gen_project_facts.py" \
  2>&1 | grep -E "✅|⚠️" | head -10
```

→ **Ergebnis**: Nächster `session-start` auf JEDER Maschine hat automatisch die aktuellen Rules + Workflows.
→ Unregistrierte Repos (⚠️) → in `platform/scripts/repo-registry.yaml` eintragen.

// turbo
```bash
PLATFORM_DIR="${GITHUB_DIR:-$HOME/github}/platform"
VERSION_AFTER=$(cat "$PLATFORM_DIR/VERSION" 2>/dev/null || echo "unknown")
COMMIT_AFTER=$(git -C "$PLATFORM_DIR" log -1 --format="%h" 2>/dev/null || echo "?")
echo ""
if [ "$VERSION_BEFORE" != "$VERSION_AFTER" ] || [ "$COMMIT_BEFORE" != "$COMMIT_AFTER" ]; then
  echo "┌─────────────────────────────────────────┐"
  echo "│  ✅ DEPLOYED TO GITHUB                  │"
  echo "│  v${VERSION_BEFORE} → v${VERSION_AFTER}                │"
  echo "│  Commit: ${COMMIT_BEFORE} → ${COMMIT_AFTER}             │"
  echo "│  Plattformweit aktiv ab nächstem Start  │"
  echo "└─────────────────────────────────────────┘"
else
  echo "┌─────────────────────────────────────────┐"
  echo "│  ℹ️  KEINE PLATFORM-ÄNDERUNGEN         │"
  echo "│  Platform v${VERSION_AFTER} (${COMMIT_AFTER})       │"
  echo "└─────────────────────────────────────────┘"
fi
```

### 3.3 Finale Prüfung — Kein Repo darf dirty sein

```bash
dirty=0
for repo in ${GITHUB_DIR:-$HOME/github}/*/; do
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
| 5 | Platform gepusht → Workflows sync → project-facts aktuell | ☐ |
| 6 | Kein Repo dirty | ☐ |
| 7 | Keine .fixed/.updated Dateien übrig | ☐ |
| 8 | Blockierte Arbeit dokumentiert | ☐ |
| 9 | Docu-Drift-Check: Issue erstellt falls nötig (Phase 1b) | ☐ |
| 10 | Template-Drift-Check: Error-Drifts gefixt (Phase 1c) | ☐ |

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
