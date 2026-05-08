---
description: Session starten — Kontext laden, Stand prüfen, sicher loslegen
---

# /session-start

> Gegenstück: `/session-ende`
> **Neuer Computer?** Einmalig Bootstrap ausführen — danach funktioniert alles automatisch:
> ```bash
> git clone https://github.com/achimdehnert/platform
> bash platform/bootstrap.sh
> source ~/.bashrc
> ```
> `bootstrap.sh` setzt `GITHUB_DIR`, deployt Workflows + Rules, generiert project-facts.
> Ohne `$GITHUB_DIR` gilt Fallback: `$HOME/github`

## Verwendung

```
/session-start [REPO]
```

| Argument | Beschreibung | Default |
|----------|-------------|---------|
| `REPO` | Repo-Slug (z.B. `risk-hub`, `mcp-hub`, `trading-hub`) | Auto-Detect via Git-Root |

**Beispiele:**
- `/session-start risk-hub` — Session explizit für risk-hub starten
- `/session-start` — erkennt Repo aus aktiver Datei im IDE

> Bei **mehreren offenen Repos im Workspace**: immer explizit angeben!
> Der Agent setzt `TARGET_REPO` und nutzt es in allen folgenden Phasen.

---

## Platform Sync Loop (Prinzip)

```
Session Start:  GitHub ──pull──▶ platform ──sync──▶ alle Repos  (aktuell starten)
Session Ende:   Änderungen ──commit──▶ push ──▶ GitHub ──sync──▶ alle Repos  (sofort deployen)
```

> **GitHub ist die einzige Source of Truth.**
> Phase 0.2 + 0.3 sind kein Optional — sie sind das Herzstück des Loops.
> Nur so profitieren ALLE Repos von Verbesserungen der letzten Session.

---

## Phase 0: Tool-Health + Umgebung synchronisieren (IMMER zuerst)

### 0.0 GITHUB_DIR sicherstellen + Version-Banner (PFLICHT — allererster Schritt)

// turbo
```bash
# GITHUB_DIR in ~/.bashrc eintragen falls noch nicht vorhanden
if ! grep -q "GITHUB_DIR" ~/.bashrc 2>/dev/null; then
  echo "" >> ~/.bashrc
  echo "# Platform: Repo-Basisverzeichnis (Single Source of Truth)" >> ~/.bashrc
  echo "export GITHUB_DIR=\"\$HOME/github\"" >> ~/.bashrc
  echo "⚙️  GITHUB_DIR in ~/.bashrc eingetragen (Wert: \$HOME/github)"
  echo "   → Anpassen falls Repos woanders liegen, z.B.: GITHUB_DIR=\$HOME/CascadeProjects"
fi
export GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"

PLATFORM_DIR="${GITHUB_DIR}/platform"
VERSION_BEFORE=$(cat "$PLATFORM_DIR/VERSION" 2>/dev/null || echo "unknown")
COMMIT_BEFORE=$(git -C "$PLATFORM_DIR" log -1 --format="%h" 2>/dev/null || echo "?")
echo ""
echo "┌─────────────────────────────────────────┐"
echo "│  🚀 SESSION START                       │"
echo "│  Platform v${VERSION_BEFORE} (${COMMIT_BEFORE})        │"
echo "│  $(date '+%Y-%m-%d %H:%M')                       │"
echo "└─────────────────────────────────────────┘"
echo "shell-alive-$(date +%s)"
```

> **Wenn dieser Befehl hängt (>5s):** Shell ist blockiert!
> → `/windsurf-clean` ausführen oder Windsurf neustarten
> → Bis dahin: NUR `read_file`, `write_to_file`, `mcp1_*` (GitHub) und `mcp3_*` (Outline) nutzen
> → **Lesson Learned 2026-04-05:** Shell-Hang kann ganze Sessions blockieren.
>   Edit-Tools (`edit`, `multi_edit`) können ebenfalls betroffen sein (zeigen "empty file").
>   GitHub MCP `mcp1_get_file_contents` + `mcp1_push_files` als Workaround für Git-Operationen.

### 0.1 Server-Erreichbarkeit prüfen (PFLICHT — vor allen MCP/SSH-Calls)

⚠️ **NIEMALS `ping` verwenden** — Hetzner-Server blockieren ICMP (100% packet loss ist NORMAL).
TCP-Probe auf SSH (22), HTTP (80), HTTPS (443) stattdessen:

// turbo
```bash
python3 ${GITHUB_DIR:-$HOME/github}/platform/infra/scripts/server_probe.py --host 88.198.191.108
```

→ **Server erreichbar**: Normal weiter mit Phase 0.2
→ **Server NICHT erreichbar**: Alle MCP-Calls und SSH-Befehle werden hängen!
  Fallback: `ssh -o ConnectTimeout=10 -o BatchMode=yes root@88.198.191.108 "uptime"`
  Wenn auch SSH scheitert: Hetzner Cloud Console → Server Status prüfen
→ Lesson Learned 2026-04-03: Ping-basierte Diagnose führte zu Fehldiagnose "Server down"

### 0.2 Platform-Repo pullen + Workflows deployen (PFLICHT — GitHub → lokal → alle Repos)

> ⚠️ **Nicht überspringen.** Dieser 3-Schritt-Block ist der Platform Sync Loop.

// turbo
```bash
# Schritt 1: GitHub → lokal (neueste Rules, Workflows, Scripts)
git -C "${GITHUB_DIR:-$HOME/github}/platform" pull --rebase --quiet && echo "✅ platform aktuell"

# Schritt 2: lokal → alle Repos (Symlinks aktualisieren)
GITHUB_DIR="${GITHUB_DIR:-$HOME/github}" \
  bash "${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-workflows.sh" \
  2>&1 | grep -cE "LINK|REPLACE" | xargs -I{} echo "{} Workflow-Symlinks deployed"

# Schritt 3: project-facts.md für alle Repos regenerieren
python3 "${GITHUB_DIR:-$HOME/github}/platform/scripts/gen_project_facts.py" \
  2>&1 | grep -E "✅|⚠️|SKIP" | wc -l | xargs -I{} echo "{} Repos verarbeitet"
```
→ Ab jetzt gelten die neuesten ADRs, Rules und Workflows plattformweit.

// turbo
```bash
PLATFORM_DIR="${GITHUB_DIR:-$HOME/github}/platform"
VERSION_AFTER=$(cat "$PLATFORM_DIR/VERSION" 2>/dev/null || echo "unknown")
COMMIT_AFTER=$(git -C "$PLATFORM_DIR" log -1 --format="%h" 2>/dev/null || echo "?")
if [ "$VERSION_BEFORE" != "$VERSION_AFTER" ] || [ "$COMMIT_BEFORE" != "$COMMIT_AFTER" ]; then
  echo ""
  echo "┌─────────────────────────────────────────┐"
  echo "│  ✅ SYNC ERFOLGREICH                    │"
  echo "│  v${VERSION_BEFORE} → v${VERSION_AFTER}                │"
  echo "│  Commit: ${COMMIT_BEFORE} → ${COMMIT_AFTER}             │"
  echo "└─────────────────────────────────────────┘"
else
  echo ""
  echo "┌─────────────────────────────────────────┐"
  echo "│  ✅ BEREITS AKTUELL                     │"
  echo "│  Platform v${VERSION_AFTER} (${COMMIT_AFTER})       │"
  echo "└─────────────────────────────────────────┘"
fi
```
→ Neues Repo erkannt? → Eintrag in `platform/scripts/repo-registry.yaml` ergänzen.

### 0.4 Target-Repo bestimmen + synchronisieren

// turbo
```bash
# TARGET_REPO: explizit angegeben oder aus Git-Root
if [ -n "${TARGET_REPO:-}" ]; then
  echo "Target Repo (explizit): $TARGET_REPO"
  cd ${GITHUB_DIR:-$HOME/github}/$TARGET_REPO
elif git rev-parse --show-toplevel &>/dev/null; then
  TARGET_REPO=$(basename $(git rev-parse --show-toplevel))
  echo "Target Repo (auto-detect): $TARGET_REPO"
else
  TARGET_REPO="platform"
  echo "Target Repo (fallback): $TARGET_REPO"
  cd ${GITHUB_DIR:-$HOME/github}/$TARGET_REPO
fi
export TARGET_REPO

# Aktuelles Repo synchronisieren
git stash --quiet 2>/dev/null
git pull --rebase --quiet
git stash pop --quiet 2>/dev/null

# Kern-Repos (MCP-Infrastruktur)
for repo in mcp-hub platform risk-hub; do
  (cd ${GITHUB_DIR:-$HOME/github}/$repo && git pull --rebase --quiet 2>/dev/null) &
done
wait
echo "Git Sync done"
```
→ Stellt sicher, dass WSL ↔ Dev Desktop synchron sind.
→ Bei Konflikten: `git stash pop` manuell lösen, NICHT force-pushen.

### 0.4.1 REFLEX aktualisieren + Workspace-Repo prüfen (ADR-165)

// turbo
```bash
# REFLEX auf aktuelle Version bringen
cd ${GITHUB_DIR:-$HOME/github}/iil-reflex && git pull --rebase --quiet 2>/dev/null
REFLEX_VER=$(cd ${GITHUB_DIR:-$HOME/github}/iil-reflex && .venv/bin/python -c "import reflex; print(reflex.__version__)" 2>/dev/null || echo "?")
echo "REFLEX v${REFLEX_VER}"

# Aktuelles Workspace-Repo prüfen (nur wenn reflex.yaml vorhanden)
REPO_NAME=$(basename $(git rev-parse --show-toplevel 2>/dev/null) 2>/dev/null)
if [ -f ${GITHUB_DIR:-$HOME/github}/${REPO_NAME}/reflex.yaml ]; then
  cd ${GITHUB_DIR:-$HOME/github}/iil-reflex && .venv/bin/python -m reflex review all ${REPO_NAME} --fail-on block --emit-metrics 2>&1 | tail -8
else
  echo "ℹ️  ${REPO_NAME}: kein reflex.yaml — übersprungen"
fi
```
→ Stellt sicher, dass immer die aktuelle REFLEX-Version läuft.
→ Zeigt neue BLOCKs sofort am Session-Start an.
→ Wenn `--fail-on block` fehlschlägt: Findings zuerst fixen bevor weitergearbeitet wird.

### 0.4.2 ADR Schema Validation + Architecture Context (iil-adrfw)

// turbo
```bash
# Schnell-Check: ADR-Frontmatter gegen Schema v3 validieren
if command -v iil-adrfw &>/dev/null; then
  iil-adrfw validate ${GITHUB_DIR:-$HOME/github}/platform/docs/adr/ 2>&1 | tail -3
else
  echo "⚠️  iil-adrfw nicht installiert — pip install iil-adrfw>=0.3.1"
fi
```
→ Zeigt sofort wenn ein ADR kaputtes Frontmatter hat.
→ Fängt Drift nach Schema-Updates oder manuellen Edits.

**Architecture Context laden** (MCP — Prefix `mcp2_` für iil-adrfw, aus project-facts.md):

```
MCP: mcp2_adr_staleness(months=6)
→ Zeigt: stale ADRs, broken refs, missing reviews — sofort User informieren bei Findings

MCP: mcp2_adr_audit()
→ Health Score prüfen — bei score < 0.95 warnen

MCP: mcp2_adr_query(question="Which ADRs apply to <TARGET_REPO>?")
→ Repo-spezifische Architektur-Constraints für die aktuelle Session laden
```

→ Ergebnis kurz zusammenfassen: "X ADRs gelten für dieses Repo, Health Score Y, Z stale."
→ Bei kritischen Findings (score < 0.90 oder broken refs): User informieren vor Weiterarbeit.

### 0.5 SSH Tunnel prüfen — PFLICHT (pgvector MUSS erreichbar sein)

// turbo
```bash
if ! ss -tlnp | grep -q 15435; then
  echo "⚠️ SSH-Tunnel nicht aktiv — starte..."
  sudo systemctl start ssh-tunnel-postgres
  sleep 2
fi
if ss -tlnp | grep -q 15435; then
  echo "✅ pgvector Tunnel aktiv (localhost:15435)"
else
  echo "❌ FEHLER: pgvector Tunnel nicht erreichbar! Memory funktioniert NICHT."
  echo "   Fix: sudo systemctl start ssh-tunnel-postgres"
  echo "   ABBRUCH — pgvector ist Pflicht, kein Fallback erlaubt."
fi
```
→ **KEIN Fallback auf Cascade Memory erlaubt.** pgvector MUSS laufen.
→ Bei Fehler: Session NICHT fortsetzen bis Tunnel steht.

### 0.6 Deploy-Infrastruktur prüfen (ADR-156)

// turbo
```bash
bash ${GITHUB_DIR:-$HOME/github}/mcp-hub/scripts/verify-adr156.sh
```
→ Muss `ALL 21 CHECKS PASSED` zeigen.
→ Bei Fehlern: MCP-Server neustarten, dann erneut prüfen.

### 0.7 Deploy-Status aller Apps scannen (ADR-156)

Prüfe ob kürzlich fehlgeschlagene Deploys vorliegen:

```
mcp0_ssh_manage:
  action: exec
  host: 88.198.191.108
  command: "for repo in risk-hub billing-hub cad-hub coach-hub trading-hub travel-beat weltenhub wedding-hub pptx-hub; do bash /opt/deploy-core/deploy-status.sh $repo 2>/dev/null; done"
```

→ Für jedes Repo mit `"status":"FAILED"`: Deploy-Log lesen und User informieren.
→ Optional als Memory-Entry sichern (siehe `/session-ende` Phase 2 — `error_pattern`).

### 0.8 Staging-Health-Check (ADR-157)

Prüfe ob Staging-Services auf Dev Desktop (88.99.38.75) erreichbar sind:

// turbo
```bash
python -c "
import yaml, urllib.request, socket
from pathlib import Path
import os
gh = os.environ.get('GITHUB_DIR') or f\"{os.environ['HOME']}/CascadeProjects\"
d = yaml.safe_load(Path(f'{gh}/platform/infra/ports.yaml').read_text())
ok = fail = skip = 0
for name, cfg in sorted(d.get('services',{}).items()):
    if not cfg or not cfg.get('staging'): continue
    port = cfg['staging']
    try:
        s = socket.create_connection(('88.99.38.75', port), timeout=2)
        s.close()
        ok += 1
    except (socket.timeout, ConnectionRefusedError, OSError):
        skip += 1
print(f'Staging: {ok} up, {skip} nicht erreichbar (normal wenn nicht deployed)')
"
```
→ Informativ, kein Blocker. Zeigt welche Hubs auf Staging laufen.

---

## Phase 1: Kontext laden

1. **Repo-Kontext laden** — AGENT_HANDOVER.md, CORE_CONTEXT.md, ADR-Index, `mcp5_get_context_for_task()`
2. **Health Dashboard** (bei Infra/Deploy-Sessions) — `mcp0_system_manage(action: health_dashboard)`
3. **Aufgabe klären** — Issue? Use Case? ADR? Governance?
4. **Branch-Status prüfen** — `git status && git log --oneline -5`
5. **Tests baseline** — `pytest tests/ -q --tb=no` (falls vorhanden)
6. **Knowledge-Lookup** — Outline durchsuchen (Repo-Steckbrief, Task-Wissen, Lessons, Cascade-Aufträge)
7. **ADR-Inputs prüfen** — Neue Input-Dokumente aus Outline abholen:
```
mcp3_search_knowledge(query: "Input ADR", collection: null, limit: 10)
```
→ Sucht nach Dokumenten mit Titel "Input ADR-XXX: ..." in allen Collections.
→ Unbearbeitete Inputs (ohne ✅ im Titel) dem User melden.
→ Workflow: User erstellt `Input ADR-156: Deploy-Script Referenz` in Outline → Cascade findet es hier.
→ Nach Verarbeitung: Titel auf `✅ Input ADR-156: ...` setzen via `mcp3_update_document()`.

---

## Phase 2: pgvector Warm-Start (ADR-154)

> **MCP-Prefix beachten** — auf Dev Desktop ist `mcp1_` = orchestrator (siehe `project-facts.md`).

8. **Memory Warm-Start / Bekannte Fehler / Recurring Errors** — alles über `mcp1_agent_memory`:
```
mcp1_agent_memory(
  operation: "query",
  filter_type: "solved_problem",   // oder "error_pattern" für Bug-Fix-Sessions
  filter_tag: "<repo>"             // optional
)
```
→ Liefert relevante Session-Summaries, Error-Patterns und Lessons aus pgvector.
→ Falls leer: normal weiterarbeiten (Memory füllt sich über `/session-ende`).

> ℹ️ `mcp2_get_session_delta` + `mcp2_find_similar_errors` + `mcp2_check_recurring_errors`
> sind wieder verfügbar (seit Issue #80 Reopened). Siehe Phase 2.5.

---

## Phase 2.5: Error-Learning (Recurring Errors → ADR-Kandidaten)

**Proaktives Root-Cause-Scanning** — Fehler die sich 3×+ wiederholen sind strukturell, nicht zufällig.

```
MCP: <orc>_check_recurring_errors(threshold=3)
→ liefert: Liste mit {symptom, root_cause, fix, occurrence_count, last_occurred_at, action}
```

**Auswertungs-Regeln:**

| Occurrences | Action | Automatik |
|------------|--------|-----------|
| 3-4× | 🟡 ESCALATED | User am Session-Start informieren, Fix-Hypothese vorschlagen |
| 5-9× | 🔴 CRITICAL | **Auto-Issue** mit Label `adr-candidate` erstellen (wenn noch nicht offen) |
| 10×+ | 🚨 BLOCKER | Session stoppen, User-Approval holen bevor weitergemacht wird |

**Auto-Issue-Template** (für 5×+ Occurrences):

```
<gh>_list_issues(labels=["adr-candidate", "auto-detected"], state="open")
# Nur erstellen wenn gleiche entry_key nicht schon offen

<gh>_create_issue(
    owner="achimdehnert", repo="platform",
    title=f"[adr-candidate] Recurring: {symptom[:60]}",
    body=f"**Occurrences:** {count}× (seit {first_seen})\n"
         f"**Last:** {last_occurred_at}\n\n"
         f"**Symptom:** {symptom}\n"
         f"**Root Cause:** {root_cause}\n"
         f"**Bisheriger Fix:** {fix}\n\n"
         f"→ Fix löst Symptom, nicht Root Cause. ADR für strukturelle Lösung nötig.",
    labels=["adr-candidate", "auto-detected", "agent-learning"]
)
```

**Status-RESOLVED Filter:** Tags mit `resolved` aus Output filtern (bereits behobene Patterns).

---

## Phase 3: Arbeitsplan

12. **Arbeitsplan aufstellen** — Schritte, Komplexität, Risk Level, Gate (unter Einbezug der Warm-Start-Ergebnisse + Eskalationen)

---

## MCP-Server Quick-Reference

> ⚠️ **Prefix ist environment-spezifisch** — immer `project-facts.md` als Quelle nehmen!

### Dev Desktop (adehnert@dev-desktop)

| Prefix | Server | Zweck |
|--------|--------|-------|
| `mcp0_` | github | Issues, PRs, Repos, Files, Reviews |
| `mcp1_` | orchestrator | Memory, Task-Analyse, Plans, Evaluate, Verify |

### WSL / Prod-Server (Standard-Konfiguration)

| Prefix | Server | Zweck |
|--------|--------|-------|
| `mcp0_` | deployment-mcp | SSH, Docker, Git, DB, DNS, SSL, System |
| `mcp1_` | github | Issues, PRs, Repos, Files, Reviews |
| `mcp2_` | orchestrator | Memory, Task-Analyse, Agent-Team |
| `mcp3_` | outline-knowledge | Wiki: Runbooks, Konzepte, Lessons |
| `mcp4_` | paperless-docs | Dokumente, Rechnungen |
| `mcp5_` | platform-context | Architektur-Regeln, ADR-Compliance |
