---
description: Systematischer Review aller .windsurf/workflows/ — Qualität, Stabilität, Fehlerquellen, Optimierungspotenzial für fehlerfreies Coding-Agent-Szenario
---

# /workflow-review — Workflow Quality Review Guide

> **Ziel:** Jeden Workflow auf Stabilität, Korrektheit und Agent-Tauglichkeit prüfen.
> Ergebnis: Liste von Fixes + Optimierungen, priorisiert nach Schweregrad.

---

## Phase 0 — Vorbereitung

// turbo
```bash
export GITHUB_DIR="${GITHUB_DIR:-$HOME/CascadeProjects}"
PLATFORM="${GITHUB_DIR}/platform"
WF_DIR="${PLATFORM}/.windsurf/workflows"

echo "=== Workflow-Inventar ==="
ls "$WF_DIR"/*.md | wc -l
echo "Dateien total"
ls "$WF_DIR"/*.md | xargs -I{} basename {} .md | sort
```

---

## Phase 1 — Struktur-Check (alle Workflows)

Für jeden Workflow prüfen:

// turbo
```bash
echo "=== Frontmatter-Check ==="
for f in ${PLATFORM}/.windsurf/workflows/*.md; do
  name=$(basename $f .md)
  has_desc=$(head -5 "$f" | grep -c "description:" || true)
  has_steps=$(grep -c "^## \|^### \|^[0-9]\+\." "$f" || true)
  line_count=$(wc -l < "$f")
  echo "$name | desc=$has_desc | steps=$has_steps | lines=$line_count"
done
```

**Bewertungskriterien:**

| Kriterium | Grün ✅ | Gelb ⚠️ | Rot 🔴 |
|-----------|---------|---------|--------|
| `description:` im Frontmatter | vorhanden | fehlt | fehlt + keine Überschrift |
| Schritte nummeriert | ≥3 Schritte | 1-2 Schritte | keine Struktur |
| Länge | 30-200 Zeilen | >300 Zeilen | <10 Zeilen |
| `// turbo` Annotation | korrekt gesetzt | fehlend bei safe-Steps | falsch gesetzt bei unsafe |

---

## Phase 2 — MCP-Korrektheit

**Häufigste Fehlerquellen aus der Praxis:**

### 2.1 MCP-Prefix-Drift

```bash
# Prüfe ob Workflows veraltete MCP-Prefixe hardcoden
grep -rn "mcp[0-9]_" ${PLATFORM}/.windsurf/workflows/ | grep -v "mcp0_\|mcp1_" | head -20
```

Erwartung auf Dev Desktop:
- `mcp0_` = github (Issues, PRs, Files, Repos)
- `mcp1_` = orchestrator (Memory, Plans, Evaluate)

> ⚠️ **Nie hardcoden** — immer aus `project-facts.md` lesen. Workflows die `mcp2_`, `mcp3_` etc. hardcoden schlagen auf dem Dev Desktop fehl.

### 2.2 Deprecated Tool-Namen

```bash
grep -rn "agent_memory_upsert\|agent_memory_context\|run_workflow\|discord_notify" \
  ${PLATFORM}/.windsurf/workflows/ | head -10
```

Aktuell gültige Orchestrator-Tools prüfen:
```
mcp1_agent_memory (operation: read|upsert|gc|query)
mcp1_agent_plan_task
mcp1_analyze_task
mcp1_evaluate_task
mcp1_verify_task
mcp1_get_infra_context
mcp1_scan_repo
```

### 2.3 GitHub MCP Rate-Limit-Risiko

Workflows die in Schleifen viele `mcp0_*` Calls machen → Rate-Limit-Gefahr:

```bash
grep -l "for\|while" ${PLATFORM}/.windsurf/workflows/*.md | \
  xargs grep -l "mcp0_"
```

Bei Loops > 10 Repos: `curl` mit `~/.secrets/github_PAT` statt MCP verwenden.

---

## Phase 3 — Stabilität & Fehlerbehandlung

### 3.1 Fehlende Fallbacks

Jeder Workflow-Step der externe Ressourcen nutzt braucht einen Fehlerfall:

```
Checkliste pro Workflow:
□ Was passiert wenn MCP-Server nicht erreichbar?
□ Was passiert wenn GitHub API 403/404 zurückgibt?
□ Was passiert wenn ein Bash-Command fehlschlägt?
□ Gibt es Timeouts für long-running Commands?
```

### 3.2 Idempotenz-Check

```bash
# Workflows die Dateien erstellen — sind sie idempotent?
grep -l "write_to_file\|create.*file\|touch\|mkdir" \
  ${PLATFORM}/.windsurf/workflows/*.md
```

Für jede gefundene Datei: Ist ein "bereits vorhanden"-Check eingebaut?

### 3.3 Git-State-Annahmen

Gefährliche Muster:
```bash
grep -n "git push\|git commit\|git reset --hard" \
  ${PLATFORM}/.windsurf/workflows/*.md | grep -v "pull --rebase"
```

**Regeln:**
- IMMER `git pull --rebase` vor `git push`
- NIE `git reset --hard` ohne explizite User-Bestätigung
- IMMER `git status` vor Commit prüfen

---

## Phase 4 — Token-Effizienz

### 4.1 Redundante Calls identifizieren

```bash
# Workflows die project-facts mehrfach laden
grep -c "get_file_contents\|project-facts" \
  ${PLATFORM}/.windsurf/workflows/*.md | grep -v ":0\|:1" | sort -t: -k2 -rn | head -10
```

**Optimierungsregel:** `project-facts.md` enthält ALLES — nie separaten Call für settings.py, apps/, etc.

### 4.2 // turbo Potenzial

```bash
# Steps die safe auto-run wären aber kein turbo haben
grep -B2 "git status\|ls -la\|cat \|echo \|wc -l" \
  ${PLATFORM}/.windsurf/workflows/*.md | grep -v "// turbo" | head -20
```

`// turbo` korrekt einsetzen:
- ✅ Read-only Commands (`ls`, `cat`, `git log`, `git status`, `curl -s GET`)
- ✅ Status-Checks (`docker ps`, `systemctl status`)
- ❌ NIEMALS bei: `git push`, `git commit`, `docker stop`, `rm`, API-Write-Calls

---

## Phase 5 — Einzelreview: Kritische Workflows

Die folgenden Workflows haben hohe Fehlerauswirkung → besonders gründlich reviewen:

### session-start.md / session-ende.md
```
Prüfe:
□ GITHUB_DIR korrekt gesetzt (~/CascadeProjects auf Dev Desktop)?
□ MCP-Prefix-Tabelle aktuell?
□ Git-Sync-Schleife auf allen Repos getestet?
□ pgvector-Tunnel-Check vorhanden?
```

### deploy.md / ship.md
```
Prüfe:
□ Pre-flight Migration-Check vorhanden?
□ Health-Check nach Deploy?
□ Rollback-Anweisung vorhanden?
□ Kein hardcodierter Server-IP?
□ env_file statt environment: ${VAR}?
```

### sync-workflows-to-repos.yml (CI)
```
Prüfe:
□ Registry SSoT (github_repos.yaml) als Quelle?
□ Symlink-Handling (deleteFile + createFile)?
□ Rate-Limit-Awareness (Batch-Größe)?
□ SHA-Konflikt-Handling (Retry)?
```

### agentic-coding.md
```
Prüfe:
□ Gate-Checks vorhanden (Gate 1/2/3)?
□ Planner-Call für komplexe Tasks?
□ Evaluate-Call am Ende?
□ Rollback-Pfad definiert?
```

---

## Phase 6 — Bewertungs-Output

Nach dem Review für jeden Workflow eine Zeile:

```
FORMAT: [NAME] | [SCORE 1-5] | [STATUS] | [AKTION]

Scores:
5 = Production-ready, keine Änderungen nötig
4 = Minor issues, 1-2 kleine Fixes
3 = Moderate issues, Refactor empfohlen
2 = Major issues, vor nächstem Einsatz fixen
1 = Broken/gefährlich, sofort fixen oder deaktivieren

Status: ✅ OK | ⚠️ Warn | 🔴 Fix | 🗑️ Deprecated

Beispiel:
session-start    | 4 | ⚠️ | MCP-Prefix-Tabelle aktualisieren
deploy           | 5 | ✅ | —
sync-workflows   | 3 | ⚠️ | Rate-Limit-Retry ergänzen
old-workflow     | 1 | 🗑️ | Durch neue Version ersetzen
```

---

## Phase 7 — Fix-Priorisierung

Fixes priorisieren nach:

| Priorität | Kriterium |
|-----------|-----------|
| **P0 — Sofort** | Workflow crasht / löscht Daten / hardcoded Secrets |
| **P1 — Diese Woche** | Workflow schlägt reproduzierbar fehl |
| **P2 — Backlog** | Performance / Token-Ineffizienz / fehlende Fallbacks |
| **P3 — Nice to have** | Dokumentation / Beispiele / Turbo-Annotations |

```bash
# Issues für P0/P1 Fixes automatisch erstellen
TOKEN=$(cat ~/.secrets/github_PAT)
curl -s -X POST \
  -H "Authorization: token $TOKEN" \
  "https://api.github.com/repos/achimdehnert/platform/issues" \
  -d "{
    \"title\": \"[workflow-fix] <NAME>: <Problem>\",
    \"body\": \"Gefunden via /workflow-review\\n\\nPriorität: P0/P1\\n\\nProblem: <...>\\nFix: <...>\",
    \"labels\": [\"workflow\", \"automated\"]
  }"
```

---

## Checkliste — Neuer Workflow

Vor dem Merge jedes neuen Workflows:

```
□ Frontmatter mit description: vorhanden
□ Alle Schritte nummeriert oder klar gegliedert
□ MCP-Prefix NICHT hardcodiert (oder explizit dokumentiert)
□ // turbo nur bei read-only Steps
□ Fehlerfall für externe Ressourcen definiert
□ Idempotent (mehrfach ausführbar ohne Schaden)
□ In workflow-index.md eingetragen
□ Sync-Workflow-Kategorien geprüft (UNIVERSAL / DJANGO_HUB_WF / PACKAGE_WF)
```
