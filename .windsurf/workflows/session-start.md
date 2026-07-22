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
> Der Sync-Loop (Runner-Phase 0.2) ist kein Optional — er ist das Herzstück des Loops.
> Nur so profitieren ALLE Repos von Verbesserungen der letzten Session.

---

## Phase 0: Tool-Health + Umgebung synchronisieren (IMMER zuerst)

> **Deterministischer Runner (NEU 2026-07-18 — Ausführungstreue-Programm, platform#1167):**
> Die mechanischen Unterphasen 0.0–0.9 (außer 0.4.3 Worktree-Modus + 0.8 Modell-Tier,
> beides Judgment) laufen in **einem** Skript-Aufruf. Einzelne Phasen sind damit
> strukturell nicht mehr überspringbar — das Skript läuft immer bis zur Summary durch.
> Die Einzel-Befehle leben in `platform/tools/session_start_checks.sh` (dort gepflegt,
> hier NICHT duplizieren — Retro c494a2: lange Phasenlisten werden überflogen).

### 0.R Runner ausführen (PFLICHT — ersetzt 0.0/0.1/0.2/0.4/0.4.1/0.4.2-Validate/0.5/0.5.1/0.6/0.7/0.9)

// turbo
```bash
bash "${GITHUB_DIR:-$HOME/github}/platform/tools/session_start_checks.sh" \
  "${TARGET_REPO:-$(basename $(git rev-parse --show-toplevel 2>/dev/null) 2>/dev/null || echo platform)}"
```

→ Ende = Summary-Tabelle `| Phase | Status | Note |` + `RESULT: OK|FAIL`.
→ **RESULT: FAIL** (einziger Hard-FAIL: pgvector-Tunnel, Phase 0.5) → Session NICHT
  fortsetzen, bis behoben — **kein** Fallback auf lokales Memory (ADR-154).
→ **Jede ⚠️ WARN-Zeile ist ein Befund** und gehört ins Session-Start-Board:
  - `0.4 … GUARD(dirty/branch=…)`: fremde Session möglich — Repo NICHT stashen/switchen
    (ADR-233 + 🌀 Shared-Worktree-Kollision), read-only weiterarbeiten.
  - `0.7 failure:<repos>`: je Repo Deploy-Log lesen + User informieren —
    🌀 `feedback_deploy_green_not_change_live`: run-conclusion allein belegt nicht,
    dass die Änderung live ist. Optional als error_pattern sichern (/session-ende Phase 2).
  - `0.7 waiting>24h:<repos>`: **stiller Prod-Blocker** — ein Run haengt an einem
    Environment-Approval-Gate und belegt die Concurrency-Group weiter; jeder spaetere
    Deploy steht als `pending` mit 0 Jobs und erreicht Prod nie, ohne dass ein Check
    rot wird. `gh run cancel` wirkt dort NICHT. Aufloesen ueber das Gate des ALTEN Runs:
    `gh api repos/<o>/<r>/actions/runs/<id>/pending_deployments -X POST -F 'environment_ids[]=<envid>' -f state=rejected`
    (Realfall 2026-07-21 ausschreibungs-hub: Merge #159 war 9 Tage nicht live).
    **`state` erst nach einem Blick auf den Commit waehlen, nicht reflexhaft `rejected`:**
    ist der wartende Run *ueberholt* (sein Stand steckt laengst in HEAD), gehoert er
    abgelehnt — ein Approve wuerde einen alten Stand nach Prod schieben. Ist er dagegen
    der **neueste** Run, ist `approved` die richtige Antwort; `rejected` wirft dort genau
    den Deploy weg, den man haben wollte. Billigster Check:
    `gh run view <id> --json headSha,displayTitle` gegen `git log origin/main -1`.
  - `0.7 … bewusst abgelehnte Freigabe (kein Befund):<repos>`: **kein Handlungsbedarf.**
    Eine mit `rejected` geschlossene Environment-Freigabe zaehlt GitHub als `failure`;
    bei docs-only-Merges ist genau das der gewollte Weg (Gate zu, Concurrency-Group
    frei). Der Scan trennt das ueber den Approval-Eintrag des Runs — echte Fehlschlaege
    haben keinen. Nur wenn eine Ablehnung *nicht* beabsichtigt war, ist sie ein Befund.
  - `0.4.1 BLOCK-Findings`: zuerst fixen, bevor weitergearbeitet wird.

**Troubleshooting (Lessons aus den Alt-Phasen — gelten unverändert):**

- **Runner hängt >5s vor der ersten Ausgabe-Zeile:** Shell blockiert! In CC: Session neu
  starten; in Windsurf: `/windsurf-clean`. Bis dahin NUR `Read`/`Write`/`Edit` + stabile
  MCP-Tools (`mcp__github__*`, `mcp__outline-knowledge__*`) nutzen;
  `mcp__github__get_file_contents` + `mcp__github__push_files` als Git-Workaround
  (Lesson 2026-04-05: Shell-Hang kann ganze Sessions blockieren, Edit-Tools zeigen
  dann ggf. "empty file").
- **NIEMALS `ping`** für Server-Checks — Hetzner blockt ICMP (100% packet loss ist
  NORMAL); der Runner nutzt `server_probe.py` (TCP 22/80/443). Server trotzdem nicht
  erreichbar → `ssh -o ConnectTimeout=10 -o BatchMode=yes root@88.198.191.108 "uptime"`;
  scheitert auch das: Hetzner Cloud Console → Server-Status (Lesson 2026-04-03:
  Ping-Diagnose führte zu Fehldiagnose "Server down").
- **pgvector-Tunnel:** devuser hat KEIN sudo-Passwort (AGENT_HANDOVER §2) — der Runner
  versucht erst `sudo -n systemctl start ssh-tunnel-postgres`, dann den direkten
  ssh-Tunnel (Ziel-Port aus AGENT_HANDOVER §7). Beides scheitert → mit sudo-Rechten:
  `sudo systemctl start ssh-tunnel-postgres`.
- **Stash-Semantik (0.4):** Der Runner stasht grundsätzlich NICHT (Guard statt Stash) —
  die alte Auto-Stash-Logik poppte 2× fremde Stash-Einträge (Drift 2026-06-10 +
  2026-06-22, untracked-only-Falle). Dirty Target-Repo = bewusste Handentscheidung.
- **ADR-156 rot (0.6):** MCP-Server neustarten, dann `verify-adr156.sh` erneut prüfen.
- **Neues Repo erkannt** → Eintrag in `platform/scripts/repo-registry.yaml` ergänzen.

### Architecture Context laden (ex-0.4.2, environment-abhängig)

Der Schema-Validate-Teil läuft im Runner (Phase 0.4.2); das Kontext-Laden bleibt
Modell-Arbeit (Signaturen VOR Nutzung via `ToolSearch` verifizieren, Policy
claude-skills §MCP-Signaturen):

- **Wenn adrfw-MCP-Tools gebunden sind** (`adr_staleness`/`adr_audit`/`adr_query`/
  `adr_freshness` — Prefix aus `project-facts.md`): Staleness (6 Monate), Health-Score
  (warnen bei < 0.95) und Repo-Constraints laden; Ergebnis in 1 Satz zusammenfassen.
- **CC-Standard-Fallback (keine adrfw-MCP-Tools gebunden):** CLI + Skills nutzen —
  `iil-adrfw validate docs/adr/` läuft bereits im Runner; für tiefe Audits `/adr-health`
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

## Startklar-Checkliste (PFLICHT — NEU 2026-07-15, Ausführungstreue-Gate)

> **Lesson 2026-07-15 (Retro c494a2):** `session-ende.md` bekam 2026-07-14 eine neue
> Pflicht-Phase (0a-handover-pr), die in derselben Session, die sie brauchte, trotz
> vorliegender Skill-Kopie NICHT ausgeführt wurde — ein langes Multi-Phasen-Dokument
> wird überflogen statt Phase für Phase abgehakt. `session-start.md` hatte bis hierhin
> **gar keine** Abschluss-Checkliste trotz 14 Unterphasen (0.0–0.9) + 3 weiteren Phasen —
> das größte Ausführungstreue-Risiko dieses Skills, weil es JEDE Session zuerst durchläuft.

| # | Check | Status |
|---|-------|--------|
| 1 | Runner `tools/session_start_checks.sh` gelaufen, Summary-Tabelle gezeigt (0.R) | ☐ |
| 2 | RESULT beachtet: FAIL → Stopp; jede ⚠️ WARN als Befund gespiegelt (0.R) | ☐ |
| 3 | Architecture Context geladen (ex-0.4.2) | ☐ |
| 4 | Modell-Tier bewusst gewählt (0.8) | ☐ |
| 5 | Repo-Kontext + Memory-Warm-Start geladen (Phase 1/2) | ☐ |
| 6 | Recurring-Errors geprüft, Handover↔Memory-Reconciliation gemacht (2.5/2.6) | ☐ |
| 7 | Editier-Modus auf Worktree gesetzt, kein Edit im Haupt-Tree (0.4.3, ADR-233-Kill-Gate) | ☐ |
| 8 | Arbeitsplan aufgestellt (Phase 3) | ☐ |

**Pflicht-Selbstcheck (2-Schritt, NEU 2026-07-15 — Retro c494a2-incr Befund #3):** Diese
Checkliste selbst ließ bei ihrer Erstellung 0.4.3 und Phase 3 aus, weil beide keine
wörtliche "PFLICHT"/"NEU"-Markierung im Titel tragen, obwohl beide faktisch mandatorisch
sind (0.4.3 = ADR-233-Kill-Gate, Phase 3 = das eigentliche Ergebnis des Skills). Reines
Filtern nach dem Stichwort "PFLICHT" übersieht genau solche Phasen. Richtiger Ablauf:
(1) ALLE `##`/`###`-Überschriften oben mechanisch auflisten (`grep -n "^## \|^### "`),
(2) DANN jede einzeln beurteilen, ob sie faktisch mandatorisch ist — nicht nur nach dem
Wort im Titel filtern. Bei einer neuen Pflicht-Phase diese Tabelle im selben PR erweitern,
nicht in einem Folge-Commit "irgendwann".

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

- 2026-07-18: v3 — Deterministischer Runner `tools/session_start_checks.sh` ersetzt die
  mechanischen Einzel-Blöcke 0.0/0.1/0.2/0.4/0.4.1/0.4.2-Validate/0.5/0.5.1/0.6/0.7/0.9
  (Ausführungstreue-Programm #1167, Retro c494a2: lange Phasenlisten werden beim
  Ausführen überflogen — ein Skript-Lauf ist nicht überspringbar und endet mit
  maschinenlesbarer Summary + RESULT). Judgment-Phasen (0.4.3 Worktree, 0.8 Modell-Tier,
  Architecture Context, Phasen 1–3) bleiben im Skill. Troubleshooting-Lessons der
  Alt-Phasen in 0.R konsolidiert, kein Inhalt ersatzlos gelöscht (Lehre #1122/#1165).
  Startklar-Checkliste 12→8 Rows (alte Rows 1–7 = jetzt Runner-Summary). Runner real
  verifiziert (Lauf 2026-07-18: reproduzierte die Live-Befunde der manuellen Session).
- 2026-07-15 (Nachtrag, Retro c494a2-incr): die frisch angelegte Startklar-Checkliste ließ
  selbst 2 faktisch mandatorische Phasen aus (0.4.3 Worktree-Gate, Phase 3 Arbeitsplan) —
  beide ohne wörtliche "PFLICHT"-Markierung im Titel, weshalb der reine Stichwort-Filter
  sie überging. Rows 11+12 ergänzt, Pflicht-Selbstcheck auf 2-Schritt-Verfahren (erst alle
  Überschriften auflisten, dann einzeln beurteilen) umgestellt.
- 2026-07-15: Neue "Startklar-Checkliste" ergänzt — der Skill hatte trotz 14 Unterphasen
  (0.0–0.9) + 3 weiteren Phasen bisher KEINE Abschluss-Checkliste (anders als
  session-ende.md). Aus Retro `session-retro-2026-07-15-platform-c494a2`: eine lange,
  rein prosaische Phasenliste wird beim Ausführen überflogen statt Zeile für Zeile
  abgehakt, besonders am Session-Anfang unter Zeitdruck. Höchster Hebel aller drei
  session-xxx-Skills, weil er jede Session zuerst durchläuft.
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
