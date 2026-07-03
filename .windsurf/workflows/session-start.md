---
description: Session starten — Kontext laden, Stand prüfen, Modell-Tier wählen, sicher loslegen
mode: write
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
> → In CC: Session neu starten; in Windsurf: `/windsurf-clean`.
> → Bis dahin: NUR `Read`/`Write`/`Edit` + die stabilen MCP-Tools
>   `mcp__github__*` (GitHub) und `mcp__outline-knowledge__*` (Outline) nutzen.
> → **Lesson Learned 2026-04-05:** Shell-Hang kann ganze Sessions blockieren.
>   Edit-Tools können ebenfalls betroffen sein (zeigen "empty file").
>   `mcp__github__get_file_contents` + `mcp__github__push_files` als Workaround für Git-Operationen.

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
# PARALLEL-SESSION-GUARD (ADR-233 + 🌀 feedback_shared_worktree_multisession_git_collision):
# Der geteilte Haupt-Tree kann von MEHREREN Sessions genutzt werden. Vor jedem
# pull/stash prüfen, ob eine fremde Session den Tree verändert hat:
CUR_BRANCH=$(git branch --show-current 2>/dev/null)
if [ -n "$CUR_BRANCH" ] && [ "$CUR_BRANCH" != "main" ]; then
  echo "⛔ Haupt-Tree steht auf '$CUR_BRANCH' (nicht main) — vermutlich fremde Session aktiv."
  echo "   NICHT pullen/stashen/switchen. Read-only weiterarbeiten oder eigenen Worktree nutzen (0.4.3)."
fi
FOREIGN_WT=$(git worktree list 2>/dev/null | grep -c "session/$(date +%Y-%m-%d)")
[ "$FOREIGN_WT" -gt 0 ] && echo "ℹ️  $FOREIGN_WT aktive Session-Worktrees heute — Kollisions-Check bei Branch-Arbeit."

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
# Stash nur poppen wenn WIR etwas gestasht haben — sonst poppt `git stash pop`
# einen FREMDEN alten Stash-Eintrag (Drift 2026-06-10).
# ACHTUNG: `git status --porcelain` ist auch bei NUR untracked files non-empty,
# aber `git stash` (ohne -u) stasht die dann NICHT und exitet trotzdem 0 → der alte
# `... && STASHED=1`-Guard schlug fälschlich an und poppte einen fremden Stash
# (Drift 2026-06-22, reproduziert). Darum nur auf TRACKED-Änderungen stashen:
STASHED=0
if ! git diff --quiet HEAD 2>/dev/null; then   # tracked changes (staged ODER unstaged) vorhanden?
  git stash --quiet 2>/dev/null && STASHED=1
fi
git pull --rebase --quiet
[ "$STASHED" -eq 1 ] && git stash pop --quiet 2>/dev/null

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
  echo "⚠️  iil-adrfw nicht installiert — pip install iil-adrfw>=0.4.0"
fi
```
→ Zeigt sofort wenn ein ADR kaputtes Frontmatter hat.
→ Fängt Drift nach Schema-Updates oder manuellen Edits.

**Architecture Context laden** (environment-abhängig — Signaturen VOR Nutzung via
`ToolSearch` verifizieren, Policy claude-skills §MCP-Signaturen):

- **Wenn adrfw-MCP-Tools gebunden sind** (`adr_staleness`/`adr_audit`/`adr_query`/
  `adr_freshness` — Prefix aus `project-facts.md`): Staleness (6 Monate), Health-Score
  (warnen bei < 0.95) und Repo-Constraints laden; Ergebnis in 1 Satz zusammenfassen.
- **CC-Standard-Fallback (keine adrfw-MCP-Tools gebunden):** CLI + Skills nutzen —
  `iil-adrfw validate docs/adr/` läuft bereits in 0.4.2; für tiefe Audits `/adr-health`
  aufrufen; Repo-Constraints aus `docs/adr/index.json` (maschinenlesbar) + CORE_CONTEXT.
- **Weekly-Diff** (1×/Woche): `git -C "$PLATFORM_DIR" log --since="7 days ago" --oneline -- docs/adr/ | head`
  genügt als billigster Check; bei vielen Änderungen `/adr-health` empfehlen.

### 0.4.3 Editier-Modus: Worktree statt Haupt-Tree (ADR-233)

**Haupt-Tree heilig.** Der geteilte Checkout `~/github/<repo>` bleibt auf `main` — **kein**
`git switch`/`checkout -b` im Haupt-Tree (parallele Sessions kollidieren sonst über den HEAD).

- **Read-only-Analyse:** im Haupt-Tree erlaubt.
- **Editierende Arbeit:** über den verbindlichen Entry Point starten —
  ```bash
  wt=$(bash "${GITHUB_DIR:-$HOME/github}/platform/tools/repo-session.sh" \
        start "${GITHUB_DIR:-$HOME/github}/$TARGET_REPO" --task "<slug>")
  cd "$wt"   # eigener Branch session/<date>/<owner>/<slug> von origin/main + Lease
  ```
- **Aufräumen (gemergte/stale Worktrees):** `python3 platform/tools/worktree-reaper.py` (dry-run; `--apply` bewusst).
- **Verstoß-Messung:** `bash platform/tools/main-tree-guard.sh report` → `unauthorized_head_flips/30d` (Kill-Gate ADR-233 §8).

> **Rollout:** Der harte Snap-back-Guard (`main-tree-guard.sh install`) wird **erst** scharf geschaltet,
> wenn die branch-switchenden Skills (`hotfix`, `issues-abarbeiten`, `ship`) + lebende Sessions migriert
> sind — sonst bricht er laufende Abläufe. Bis dahin: Konvention + `repo-session` als Einstieg.

### 0.5 SSH Tunnel prüfen — PFLICHT (pgvector MUSS erreichbar sein)

// turbo
```bash
if ! ss -tlnp | grep -q 15435; then
  echo "⚠️ SSH-Tunnel nicht aktiv — starte..."
  # devuser hat KEIN sudo-Passwort (AGENT_HANDOVER §2) → erst sudo-frei versuchen:
  if sudo -n systemctl start ssh-tunnel-postgres 2>/dev/null; then
    sleep 2
  else
    # Fallback ohne sudo: Tunnel direkt aufbauen (Ziel-Port aus AGENT_HANDOVER §7)
    (ssh -f -N -L 15435:localhost:15435 -o BatchMode=yes -o ConnectTimeout=5 \
       -i ~/.ssh/id_ed25519 root@88.198.191.108 2>/dev/null) && sleep 1
  fi
fi
if ss -tlnp | grep -q 15435; then
  echo "✅ pgvector Tunnel aktiv (localhost:15435)"
else
  echo "❌ FEHLER: pgvector Tunnel nicht erreichbar! Memory funktioniert NICHT."
  echo "   Fix (mit sudo-Rechten): sudo systemctl start ssh-tunnel-postgres"
  echo "   ABBRUCH — pgvector ist Pflicht, kein Fallback erlaubt."
fi
```
→ **KEIN Fallback auf agent memory erlaubt.** pgvector MUSS laufen.

### 0.5.1 Secret-Drop-Zone-Guard (KONZ-platform-010, warn)

// turbo
```bash
# ~/shared ist Wegwerf-Scratch; Secrets gehören NUR nach ~/.secrets (SSoT, 0700).
# ~/shared/inbox/secrets ist world-writable (0777) → nie dauerhaft Secrets dort lagern.
if [ -d ~/shared/inbox/secrets ] && [ -n "$(ls -A ~/shared/inbox/secrets 2>/dev/null)" ]; then
  n=$(ls -A ~/shared/inbox/secrets 2>/dev/null | wc -l)
  echo "⚠️  $n Secret(s) in ~/shared/inbox/secrets — gehören nach ~/.secrets (KONZ-010)."
  echo "   Reconcile: byte-identische Dubletten löschen, Unikate verschieben, divergente prüfen."
fi
```
→ Warn, kein Hard-Fail (legitime Zwischen-Drops nicht blockieren). Wiederholungs-Bremse gegen
  das Drift-Muster (inbox driftete schon 1× nach der 2026-05-30-Konsolidierung, KONZ-010 B5).
→ Bei Fehler: Session NICHT fortsetzen bis Tunnel steht.

### 0.6 Deploy-Infrastruktur prüfen (ADR-156)

// turbo
```bash
bash ${GITHUB_DIR:-$HOME/github}/mcp-hub/scripts/verify-adr156.sh
```
→ Muss `ALL 21 CHECKS PASSED` zeigen.
→ Bei Fehlern: MCP-Server neustarten, dann erneut prüfen.

### 0.7 Deploy-Status aller Apps scannen (ADR-156)

Prüfe ob kürzlich fehlgeschlagene Deploys vorliegen — **zwei Wege, je nach Umgebung**:

- **CC-Standard (immer verfügbar):** letzten Deploy-Run je Prod-Repo via GitHub:
  ```bash
  for r in risk-hub billing-hub cad-hub coach-hub trading-hub travel-beat weltenhub wedding-hub pptx-hub; do
    gh run list -R "$(git -C ${GITHUB_DIR:-$HOME/github}/platform remote get-url origin | sed -E 's#.*[:/]([^/]+)/.*#\1#')/$r" \
      --workflow Deploy --limit 1 --json conclusion --jq '.[0].conclusion // "none"' 2>/dev/null \
      | xargs -I{} echo "$r: {}"
  done
  ```
- **Mit deployment-MCP gebunden** (Prefix aus project-facts.md): `ssh_manage exec` mit
  `/opt/deploy-core/deploy-status.sh <repo>` je Prod-Repo.

→ Für jedes Repo mit `failure`/`FAILED`: Deploy-Log lesen und User informieren —
  🌀 `feedback_deploy_green_not_change_live`: run-conclusion allein belegt nicht,
  dass die Änderung live ist.
→ Optional als Memory-Entry sichern (siehe `/session-ende` Phase 2 — `error_pattern`).

### 0.8 Modell-Tier für die Session wählen (policies/session-routing.md)

**Vor dem ersten Arbeits-Schritt einmal bewusst routen** — nicht per Default auf dem
teuersten Modell bleiben (Policy-Realfall: $1577 in 48h für Tier-3-Arbeit auf Tier-4-Modell):

| Geplante Session-Arbeit | Modell | Warum |
|---|---|---|
| Lange autonome Multi-Repo-Stränge, adversariale Orchestrierung (/repo-optimize, /platform-audit), schwierigste Architektur-Synthese | **Fable 5** | Long-Horizon + Sub-Agent-Delegation; orchestriert, Sonnet-Finder arbeiten |
| ADR-Drafting, komplexe Einzel-PRs, tiefes Review, Konzepte | **Opus** | Tier-4-Reasoning zum halben Fable-Preis |
| Issue-Abarbeitung, Bugfix-PRs, Sweeps, Lint, mechanische Edits | **Sonnet** | Tier 3 — Ergebnis ununterscheidbar, ~5× günstiger |
| Status-Checks, Log-Lesen, triviale Fragen | **Haiku / /fast** | Tier 2 |

→ Mid-Session runterschalten, wenn der anspruchsvolle Teil erledigt ist (`/model`).
→ Faustregel: **Fable orchestriert, delegiert Mechanik als Sonnet-Subagents/-Issues** —
  nicht Fable die Mechanik selbst tippen lassen.

### 0.9 Staging-Health-Check (ADR-157)

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

1. **Repo-Kontext laden** — AGENT_HANDOVER.md, CORE_CONTEXT.md, ADR-Index; falls
   platform-context-MCP gebunden: `mcp__platform-context__get_context_for_task()`
2. **Health Dashboard** (bei Infra/Deploy-Sessions) — falls deployment-MCP gebunden:
   `mcp__deployment-mcp__system_manage(action: health_dashboard)`
3. **Aufgabe klären** — Issue? Use Case? ADR? Governance?
4. **Branch-Status prüfen** — `git status && git log --oneline -5`
5. **Tests baseline** — `make test` (CI-relevant) bzw. `pytest tools/tests/ -q` (falls vorhanden)
6. **Knowledge-Lookup** — Outline durchsuchen (Repo-Steckbrief, Task-Wissen, Lessons, Cascade-Aufträge)
7. **ADR-Inputs prüfen** — Neue Input-Dokumente aus Outline abholen (falls Outline-MCP gebunden):
```
mcp__outline-knowledge__search_knowledge(query: "Input ADR", collection: null, limit: 10)
```
→ Sucht nach Dokumenten mit Titel "Input ADR-XXX: ..." in allen Collections.
→ Unbearbeitete Inputs (ohne ✅ im Titel) dem User melden.
→ Nach Verarbeitung: Titel auf `✅ Input ADR-156: ...` setzen via `mcp__outline-knowledge__update_document()`.

---

## Phase 2: pgvector Warm-Start (ADR-154)

> **Stabile CC-Namen** — `mcp__orchestrator__*` (nicht `mcpN_`, die sind Windsurf-Ära
> und environment-volatil). Signatur vor Nutzung via `ToolSearch select:<name>` prüfen.

8. **Memory Warm-Start / Bekannte Fehler / Recurring Errors** — über `mcp__orchestrator__agent_memory_search`:
```
mcp__orchestrator__agent_memory_search(
  filter_type: "solved_problem",   // oder "error_pattern" für Bug-Fix-Sessions
  filter_tag: "<repo>"             // optional
)
```
→ Liefert relevante Session-Summaries, Error-Patterns und Lessons aus pgvector.
→ Falls leer: normal weiterarbeiten (Memory füllt sich über `/session-ende`).

> ℹ️ Ergänzend: `mcp__orchestrator__find_similar_errors` + `mcp__orchestrator__check_recurring_errors`
> (siehe Phase 2.5). Bei orchestrator-404 (SSE-Session-Stickiness): 🌀
> `feedback_orchestrator_sse_session_stickiness_404` — nicht per Reconnect heilbar.

---

## Phase 2.5: Error-Learning (Recurring Errors → ADR-Kandidaten)

**Proaktives Root-Cause-Scanning** — Fehler die sich 3×+ wiederholen sind strukturell, nicht zufällig.

```
mcp__orchestrator__check_recurring_errors(threshold=3)
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
# Owner aus dem git-Remote ableiten, nicht hardcoden:
#   OWNER=$(git remote get-url origin | sed -E 's#.*[:/]([^/]+)/[^/]+(\.git)?$#\1#')
mcp__github__list_issues(labels=["adr-candidate", "auto-detected"], state="open")
# Nur erstellen wenn gleiche entry_key nicht schon offen

mcp__github__create_issue(
    owner="<OWNER>", repo="platform",
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

## Phase 2.6: Handover ↔ Memory Reconciliation (Drift-Guard — NEU 2026-06-24)

> **Lesson 2026-06-24 (iil-klickdummy):** Arbeit auf einem anderen Gerät
> (iPad/claude.ai) aktualisierte das **geteilte pgvector-Memory**, aber **nicht**
> das git-getrackte `AGENT_HANDOVER.md`. Die nächste Session auf dem Dev-Host sah
> eine als „offen" gelistete Prio, die laut Memory längst **erledigt** war — und
> hätte sie fast erneut bearbeitet (~35 KDs Doppelarbeit). Die *verursachende*
> Session läuft nicht durch *unser* `/session-ende` → ein Guard greift nur **hier
> am Start**, nicht am Ende.

Für **jede** offene Prio aus der `AGENT_HANDOVER.md`-Tabelle (Phase 1, Schritt 1)
gegen das Warm-Start-Memory (Phase 2) abgleichen:

- Memory-Eintrag, der dieselbe Aufgabe als **erledigt/komplett/abgeschlossen**
  markiert **und neuer** ist als der Handover-Stand (Datum in der
  `## ⚡ Aktueller Stand`-Überschrift)?
- **Treffer → NICHT blind starten.** Diskrepanz dem User spiegeln, evidenz-diszipliniert:
  „verifiziert: Memory `<key>` sagt erledigt am `<Datum>`; Handover sagt offen" →
  vorschlagen, den Handover sauberzuziehen, **bevor** Arbeit beginnt.
- Kein Treffer → normal weiter zu Phase 3.

→ Billigster Check zuerst (Evidenz-Disziplin): **die Diskrepanz IST der Fund** —
  nicht die erneute Ausführung der Aufgabe.

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

> **Claude Code:** stabile Namen `mcp__github__*` / `mcp__orchestrator__*` /
> `mcp__outline-knowledge__*` verwenden — die `mcpN_`-Nummern sind Windsurf-Ära und
> environment-volatil. Signaturen vor Nutzung via `ToolSearch select:<name>` prüfen.

---

## Anti-Patterns

- ❌ `ping` für Server-Checks (Hetzner blockt ICMP — TCP-Probe nutzen, 0.1).
- ❌ Im geteilten Haupt-Tree branchen/stashen, wenn eine fremde Session aktiv ist
  (0.4-Guard beachten; editieren nur via `repo-session.sh`-Worktree, ADR-233).
- ❌ Bei pgvector-Ausfall still auf lokales Memory ausweichen (0.5 ist hart).
- ❌ MCP-Tools mit `mcpN_`-Prefix hardcoden oder ungeprüfte Signaturen aus dem
  Skill-Text übernehmen — `project-facts.md` + `ToolSearch` sind die Quelle.
- ❌ Handover-Prio blind starten, ohne Phase 2.6 (Memory-Reconciliation) —
  Cross-Host-Sessions hinterlassen erledigte Prios als „offen".
- ❌ Session auf dem teuersten Modell beginnen, ohne 0.8 (Modell-Routing) bewusst
  entschieden zu haben.

## Changelog

- 2026-07-02: v2.1 — CC-first-Call-Sites vollendet: Phase 1/2/2.5 riefen noch
  Windsurf-Prefix-Tools (`mcp__platform-context__get_context_for_task`, `mcp__deployment-mcp__system_manage`,
  `mcp__outline-knowledge__search_knowledge`, `mcp__orchestrator__agent_memory`, `<orc>_`/`<gh>_`-Platzhalter) — auf
  stabile `mcp__…`-Namen umgestellt (v2 hatte nur die Warnung ergänzt, nicht die
  Aufrufe); Shell-Hang-Fallback (Z.80) + Auto-Issue-Owner (git-Remote statt
  hardcoded) mitgezogen; TODO(mcp-migration)-Marker geschlossen; orchestrator-404-
  Drift-Verweis ergänzt; Testbefehl auf `make test`.
- 2026-07-02: v2 — `mode: write` nachgetragen; Parallel-Session-Guard in 0.4
  (ADR-233 + Shared-Worktree-Drift); 0.5 sudo-freier Tunnel-Fallback (devuser ohne
  sudo); adrfw-MCP-Block environment-aware mit CC-CLI-Fallback (Signaturen-Policy);
  0.7 mit gh-Fallback (deployment-MCP optional); NEU 0.8 Modell-Tier-Routing
  (policies/session-routing.md, Fable/Opus/Sonnet-Split); Anti-Patterns + Changelog
  ergänzt (claude-skills-Policy-Pflichtsektionen).
- ≤2026-06-24: Windsurf-Ära-Stände (Phase 2.6 Reconciliation, Stash-Guards 0.4,
  Drift-Lessons) — Historie siehe git log.
