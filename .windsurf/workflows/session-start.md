---
description: Session starten — Kontext laden, Stand prüfen, Modell-Tier wählen, sicher loslegen
mode: write
---

# /session-start

> Gegenstück `/session-ende` · `LEHREN` = `docs/governance/session-skills-lehren/start.md`.
> **Neuer Computer?** `git clone https://github.com/achimdehnert/platform` →
> `bash platform/bootstrap.sh` → `source ~/.bashrc`; ohne `$GITHUB_DIR` gilt `$HOME/github`.

## Verwendung

`/session-start [REPO]` — `REPO` = Repo-Slug (z.B. `risk-hub`), Default Auto-Detect via
Git-Root; bei **mehreren offenen Repos** explizit angeben. Der Agent setzt `TARGET_REPO`
für alle folgenden Phasen.

**Platform Sync Loop:** Start = GitHub → platform → alle Repos; Ende = commit → push →
GitHub → alle Repos. **GitHub ist die einzige Source of Truth**, der Sync (0.2) kein Optional.

---

## Phase 0: Tool-Health + Umgebung synchronisieren (IMMER zuerst)

Die mechanischen Unterphasen laufen in **einem** Skript-Aufruf und sind damit strukturell
nicht überspringbar; die Einzel-Befehle leben in `platform/tools/session_start_checks.sh`
(dort gepflegt, hier NICHT duplizieren). → `LEHREN#runner-motiv`

### 0.R Runner ausführen (PFLICHT — ersetzt 0.0/0.1/0.2/0.4/0.4.1/0.4.2-Validate/0.5/0.5.1/0.6/0.7/0.9)

// turbo
```bash
bash "${GITHUB_DIR:-$HOME/github}/platform/tools/session_start_checks.sh" \
  "${TARGET_REPO:-$(basename $(git rev-parse --show-toplevel 2>/dev/null) 2>/dev/null || echo platform)}"
```

→ Ende = Summary `| Phase | Status | Repo | Note |` + Befund-Journal + `RESULT: OK|FAIL`.
→ **`RESULT: FAIL`** (einziger Hard-FAIL: pgvector-Tunnel 0.5) → Session NICHT fortsetzen,
  **kein** Fallback auf lokales Memory (ADR-154).
→ **Spalte `Repo` nennt das Repo, um das es GEHT**, nicht das der Sitzung. Journal mit
  **Alter** spiegeln: `⏳ ALTBEFUND` = nie entschieden · `⏸` = verankert/Verzicht, kommt zur
  Frist zurück · `⏰ WIEDERVORLAGE` = Frist abgelaufen (`befund_journal.py --bericht`).
→ Fremd-Repo-Befunde ohne Artefakt = **kein** Sofort-Auftrag; `/session-ende` 0f verlangt je
  Befund ein Issue im **Zielrepo** oder einen Verzicht mit Grund. → `LEHREN#journal-und-repo-spalte`

**Jede ⚠️ WARN-Zeile ist ein Befund** und gehört ins Session-Start-Board:

| Phase | Bedeutung | kein Befund | Zug |
|---|---|---|---|
| `0.3 modellwechsel` | Modell ≠ `assessed_with` („bewertet ↔ läuft") | Rücksprung **auf** das bewertete Modell | MAJOR: Vollmachten weg (Runbook §3a), §2-Köder, #1640 · MINOR: Smoke §1 |
| `0.4 GUARD(dirty/branch)` | fremde Session im Haupt-Tree möglich | — | nicht stashen/switchen (ADR-233), read-only weiter |
| `0.4.1 BLOCK-Findings` | harte Repo-Health-Verstöße | — | zuerst fixen |
| `0.4.4 basis-abstand` | Worktree weit hinter `main` | keine Lease über der Schwelle | **vor** dem ersten Edit `git merge origin/main` |
| `0.7 failure:<repos>` | Deploy im Repo rot | `bewusst abgelehnte Freigabe` (docs-only) | Deploy-Log lesen, User informieren; grün ≠ live |
| `0.7 waiting>24h` | Run hängt am Environment-Gate, belegt die Concurrency-Group | — | Gate des ALTEN Runs via `pending_deployments` schließen, Zustand nach Commit-Blick |
| `0.7.6 leseflaeche` | Prio-Zeilen zeigen auf Geschlossenes | `◌ NICHT pruefbar` = Abdeckungslücke | **vor** Arbeitsbeginn nachziehen, `befund_leseflaeche.py --alle-gesehen` |
| `0.7.7 gate-wirkung` | gebautes Gate versagt, Befund 2×+ zurück | `zu-frueh`/`unerprobt` | im Board benennen, Behandlung in Retro 4/5a |
| `0.7.11 erreichbarkeit` | **5xx** = Dienst tot · **NXDOMAIN** = Deklaration falsch | 401/403 (Cloudflare Access) | 5xx im Ziel-Repo, NXDOMAIN in `ports.yaml`; Ausnahme braucht `betriebsstatus_grund:` |
| `0.7.12 prod-wirkung` | `RUECKSTAND:` = live ≠ `main` | `wartet auf Prod-Freigabe` bis 14 Tage | ins Board; nach 14 Tagen kippt die Zeile |
| `0.7.16 origin-tls` | `abgelaufen`/`laeuft-ab` = Renewal kaputt · `fallback-zertifikat` = **kein** Cert | `cloudflare-origin-ca`, `kein-tls-am-origin` | Renewal bzw. vhost/cert am Host reparieren |
| `0.7.17 backup-deckung` | Volume ohne `pgdump`/`volumes`/`verzicht`/`anonym` = **UNGEDECKT** | `verzicht` **mit** Grund | nach Lage trennen: in Nutzung / Container steht / verwaist |
| `0.7.18 speicher` | < 7 Tage bis voll oder < 10 % frei | — | Platte ins Board, Wachstum abstellen; Offsite zählt mit |
| `0.7.23 melder-register` | Phase ohne Eintrag / `leser: UNBENANNT` / Karteileiche | — | `melder_register_check.py --kurz`, Leser benennen |

**Jede `◌`/`nicht messbar`/`SAMMELPHASE`-Zeile ist eine Lücke, kein Pass — als solche ins Board.**

- **`ℹ️ HINWEIS`** = Melder unter der Trefferquote, selbst herabgestuft: lesen, nicht als
  Befund erzwingen — der **Melder** ist dann der Befund.
- **Block „⏳ ohne Entscheidung > 14 d"** = der Melder hat funktioniert, es fehlt die
  Entscheidung (anders als ein frischer `⏳ ALTBEFUND`).
- Herleitungen, Realfälle, Zahlen je Klasse: → `LEHREN#warn-klassenkunde`

**Troubleshooting:** Runner hängt >5 s vor der ersten Ausgabe → Shell blockiert, Session neu
starten, bis dahin nur `Read`/`Write`/`Edit` + `mcp__github__*`. **NIEMALS `ping`** (Hetzner
blockt ICMP) — der Runner nutzt `server_probe.py` (TCP 22/80/443). pgvector-Tunnel scheitert
trotz `sudo -n` → mit sudo-Rechten `sudo systemctl start ssh-tunnel-postgres`. Der Runner
**stasht nicht** (Guard statt Stash); dirty Target-Repo = Handentscheidung. ADR-156 rot →
MCP-Server neustarten, `verify-adr156.sh` erneut. Neues Repo → in
`platform/scripts/repo-registry.yaml` eintragen. → `LEHREN#troubleshooting`

### Architecture Context laden (ex-0.4.2, environment-abhängig)

Schema-Validate läuft im Runner; Kontext-Laden bleibt Modell-Arbeit (Signaturen VOR Nutzung
via `ToolSearch` prüfen, Policy claude-skills §MCP-Signaturen):

- **adrfw-MCP gebunden** (`adr_staleness`/`adr_audit`/`adr_query`/`adr_freshness`): Staleness
  (6 Monate), Health-Score (warnen < 0.95), Repo-Constraints laden; Ergebnis in 1 Satz.
- **CC-Fallback:** `iil-adrfw validate docs/adr/` läuft im Runner; tiefe Audits `/adr-health`;
  Constraints aus `docs/adr/index.json` + CORE_CONTEXT.
- **Weekly-Diff:** `git -C "$PLATFORM_DIR" log --since="7 days ago" --oneline -- docs/adr/ | head`

### 0.4.3 Editier-Modus: Worktree statt Haupt-Tree (ADR-233)

**Haupt-Tree heilig.** `~/github/<repo>` bleibt auf `main` — **kein** `git switch`/`checkout -b`
dort (parallele Sessions kollidieren über den HEAD). Read-only-Analyse dort erlaubt.

```bash
wt=$(bash "${GITHUB_DIR:-$HOME/github}/platform/tools/repo-session.sh" \
      start "${GITHUB_DIR:-$HOME/github}/$TARGET_REPO" --task "<slug>" --ziel "<Sitzungsziel>")
cd "$wt"   # Branch session/<date>/<owner>/<slug> von origin/main + Lease
```

- **`--ziel`** ist optional, beantwortet aber „warum dieser Branch?" und „welche PRs gehören
  zur Sitzung?"; es bleibt über alle Aufgaben derselben Sitzung gleich.
- **Aufräumen:** `python3 platform/tools/worktree-reaper.py` (dry-run; `--apply` bewusst).
- **Verstoß-Messung:** `bash platform/tools/main-tree-guard.sh report` →
  `unauthorized_head_flips/30d` (Kill-Gate ADR-233 §8); harter Guard noch nicht scharf.
  → `LEHREN#worktree-ziel`

### 0.8 Modell-Tier für die Session wählen (policies/session-routing.md)

**Vor dem ersten Arbeits-Schritt bewusst routen** — nicht per Default auf dem teuersten
Modell bleiben:

| Session-Arbeit | Modell |
|---|---|
| Lange autonome Multi-Repo-Stränge, adversariale Orchestrierung, schwerste Architektur-Synthese | **Fable 5** |
| ADR-Drafting, komplexe Einzel-PRs, tiefes Review, Konzepte | **Opus** (Tier 4, halber Preis) |
| Issue-Abarbeitung, Bugfix-PRs, Sweeps, Lint, mechanische Edits | **Sonnet** (Tier 3, ~5× günstiger) |
| Status-Checks, Log-Lesen, triviale Fragen | **Haiku / /fast** (Tier 2) |

→ Mid-Session runterschalten (`/model`), wenn der anspruchsvolle Teil erledigt ist.
→ **Fable orchestriert, delegiert Mechanik als Sonnet-Subagents/-Issues.** → `LEHREN#modell-routing`

---

## Phase 1: Kontext laden

1. **Repo-Kontext** — `AGENT_HANDOVER.md` (Prio-Tabelle + Stand) **und die letzten Einträge
   aus `AGENT_HANDOVER_LOG.md`** (append-only, neueste **unten**, `tail -60`),
   `CORE_CONTEXT.md`, ADR-Index; falls gebunden `mcp__platform-context__get_context_for_task()`
2. **Health Dashboard** (Infra/Deploy, falls gebunden):
   `mcp__deployment-mcp__system_manage(action: health_dashboard)`
3. **Aufgabe klären** — Issue? Use Case? ADR? Governance?
4. **Branch-Status** — `git status && git log --oneline -5`
5. **Tests baseline** — `make test` bzw. `pytest tools/tests/ -q`
6. **Knowledge-Lookup** — Outline (Repo-Steckbrief, Task-Wissen, Lessons)
7. **ADR-Inputs** — `mcp__outline-knowledge__search_knowledge(query: "Input ADR", limit: 10)`;
   unbearbeitete (ohne ✅ im Titel) melden, nach Verarbeitung Titel auf `✅ Input ADR-…` setzen.

## Phase 2: pgvector Warm-Start (ADR-154)

8. **Memory Warm-Start / bekannte Fehler** — `mcp__orchestrator__agent_memory_search(
   filter_type: "solved_problem" | "error_pattern", filter_tag: "<repo>")`. Liefert
   Session-Summaries, Error-Patterns, Lessons; leer → normal weiter (füllt sich über
   `/session-ende`). Stabile CC-Namen `mcp__orchestrator__*`, Signatur via
   `ToolSearch select:<name>` prüfen. Bei orchestrator-404 (SSE-Session-Stickiness):
   🌀 `feedback_orchestrator_sse_session_stickiness_404` — nicht per Reconnect heilbar.

## Phase 2.5: Error-Learning (Recurring Errors → ADR-Kandidaten)

`mcp__orchestrator__check_recurring_errors(threshold=3)` → `{symptom, root_cause, fix,
occurrence_count, last_occurred_at, action}`. 3×+ wiederholte Fehler sind strukturell, nicht
zufällig; Tags mit `resolved` herausfiltern.

| Occurrences | Action | Automatik |
|---|---|---|
| 3-4× | 🟡 ESCALATED | User informieren, Fix-Hypothese vorschlagen |
| 5-9× | 🔴 CRITICAL | Issue mit Label `adr-candidate` anlegen (wenn nicht offen) |
| 10×+ | 🚨 BLOCKER | Session stoppen, User-Approval holen |

→ **Recurring Errors ≥ 5× → Issue mit Label `adr-candidate` anlegen** (Owner aus dem
git-Remote ableiten, nicht hardcoden; vorher auf offene Dublette prüfen).
→ Gestrichenes Template + Beleg: `LEHREN#error-learning-template`

## Phase 2.6: Handover ↔ Memory Reconciliation (Drift-Guard — NEU 2026-06-24)

Für **jede** offene Prio aus `AGENT_HANDOVER.md` (Phase 1.1) gegen das Warm-Start-Memory
(Phase 2) abgleichen: Gibt es einen Memory-Eintrag, der dieselbe Aufgabe als **erledigt**
markiert **und neuer** ist als der Handover-Stand (Datum in `## ⚡ Aktueller Stand`)?

- **Treffer → NICHT blind starten.** Diskrepanz evidenz-diszipliniert spiegeln („verifiziert:
  Memory `<key>` sagt erledigt am `<Datum>`; Handover sagt offen") und den Handover
  sauberziehen, **bevor** Arbeit beginnt. Kein Treffer → normal weiter.
- **Die Diskrepanz IST der Fund**, nicht die erneute Ausführung.
  → `LEHREN#handover-memory-reconciliation`

## Phase 2.7: Session-Zielzustand klären (Zielzustand-Loop — NEU 2026-08-07, PFLICHT für Arbeits-Sessions)

Vor dem Arbeitsplan den **Zielzustand der Session** festmachen (`policies/zielzustand.md` +
SA-4 aus `policies/autonomy-gates.md`):

1. **Quelle:** User-Auftrag → der ist die Quelle; ohne Auftrag → die Handover-Prio.
2. **Akzeptiertes Artefakt** (Issue/ADR/KONZ mit Akzeptanzkriterien) vorhanden? →
   referenzieren, NICHT neu formulieren. Es ist zugleich der **SA-4-Anker**: Umbauten, die
   nachweisbar auf seine Kriterien einzahlen, laufen autonom durch.
3. **Keins vorhanden** und Arbeit substanziell → Zielzustands-Vorschlag (3–7 Zeilen: 1 Satz
   Endzustand + 2–5 prüfbare Kriterien + Out-of-Scope) und **Akzeptanz einholen, bevor
   substanzielle Arbeit beginnt**. Schweigen ≠ Zustimmung. Bei Akzeptanz und PR-überlebender
   Arbeit als Issue im Ziel-Repo materialisieren (`/prompt --auftrag`).
4. **Right-Sizing:** reine Frage-/Triage-Sessions und triviale Fixes überspringen diese Phase
   (die Anweisung ist der Zielzustand) — bewusste Entscheidung, keine Auslassung.

## Phase 3: Arbeitsplan

12. **Arbeitsplan aufstellen** — Schritte, Komplexität, Risk Level, Gate (mit Warm-Start-
    Ergebnissen + Eskalationen), **gegen den Zielzustand aus 2.7**

---

## Startklar-Checkliste (PFLICHT — NEU 2026-07-15, Ausführungstreue-Gate)

| # | Check | Status |
|---|-------|--------|
| 1 | Runner `session_start_checks.sh` gelaufen, Summary gezeigt (0.R) | ☐ |
| 2 | RESULT beachtet: FAIL → Stopp; jede ⚠️ WARN als Befund gespiegelt | ☐ |
| 2a | Journal gelesen: Altbefunde mit **Alter**, Fremd-Repo-Befunde benannt | ☐ |
| 2b | Rückfällige Gates aus 0.7.7 im Board benannt | ☐ |
| 2c | `0.7.11`: 5xx von NXDOMAIN getrennt; jede `ports.yaml`-Ausnahme mit Grund | ☐ |
| 2d | `0.7.16`: `abgelaufen`/`laeuft-ab` von `fallback-zertifikat` getrennt | ☐ |
| 2e | `0.7.17`: rote Volumes nach Lage getrennt; jeder Verzicht mit Grund | ☐ |
| 2f | `0.7.18`: Platten unter 7 Tagen Vorlauf benannt; `SAMMELPHASE` ≠ Entwarnung | ☐ |
| 2g | `0.3`: MAJOR ggü. bewertet gespiegelt (Vollmachten suspendiert, §2-Köder, #1640) | ☐ |
| 2h | `0.7.23`: kein Melder ohne Leser, keine Karteileiche; Block „⏳ > 14 d" geprüft | ☐ |
| 3 | Architecture Context geladen (ex-0.4.2) | ☐ |
| 4 | Modell-Tier bewusst gewählt (0.8) | ☐ |
| 5 | Repo-Kontext + Memory-Warm-Start geladen (Phase 1/2) | ☐ |
| 6 | Recurring-Errors geprüft, Handover↔Memory abgeglichen (2.5/2.6) | ☐ |
| 7 | Editier-Modus auf Worktree gesetzt, kein Edit im Haupt-Tree (0.4.3) | ☐ |
| 7a | Basis-Abstand aus 0.4.4 gelesen, betroffener Worktree **vor** dem Edit gemergt | ☐ |
| 7b | Zielzustand geklärt: referenziert ODER akzeptiert ODER Überspringen begründet | ☐ |
| 8 | Arbeitsplan aufgestellt (Phase 3, gegen den Zielzustand) | ☐ |

**Neue Pflicht-Phase ⇒ Checklisten-Zeile im selben PR**; Auswahl über
`grep -n "^## \|^### "` und Einzelbeurteilung, **nicht** über das Wort „PFLICHT".
→ `LEHREN#startklar-selbstcheck`

---

## Anti-Patterns

- ❌ `ping` für Server-Checks (Hetzner blockt ICMP — TCP-Probe nutzen, 0.1).
- ❌ Im geteilten Haupt-Tree branchen/stashen, wenn eine fremde Session aktiv ist
  (0.4-Guard; editieren nur via `repo-session.sh`-Worktree, ADR-233).
- ❌ Bei pgvector-Ausfall still auf lokales Memory ausweichen (0.5 ist hart).
- ❌ MCP-Tools mit `mcpN_`-Prefix hardcoden oder ungeprüfte Signaturen aus dem Skill-Text
  übernehmen — `.windsurf/rules/project-facts.md` + `ToolSearch` sind die Quelle.
- ❌ Handover-Prio blind starten, ohne Phase 2.6 — Cross-Host-Sessions hinterlassen
  erledigte Prios als „offen".
- ❌ Session auf dem teuersten Modell beginnen, ohne 0.8 bewusst entschieden zu haben.
- ❌ **In einem Worktree weiterarbeiten, den 0.4.4 als weit hinter `main` meldet**, ohne ihn
  vorher nachzuziehen — der Konflikt entsteht sonst beim Merge, wo er am teuersten ist.

## Changelog

> Nur die letzten drei Einträge (Policy seit #2696). Volle Historie: `LEHREN#changelog-historie`.

- 2026-09-02: **Kontext-Diät** (#2690 K5) — 41 137 → ~15 200 B; WARN-Deutung als Tabelle,
  Lehren/Historie nach `docs/governance/session-skills-lehren/start.md`; gestrichen:
  Auto-Issue-Template (S1), `mcpN_`-Quick-Reference (S5), Windsurf-Fallback.
- 2026-09-02: **Phase 0.7.23 `melder-register`** ergänzt (#2690 K3) — je Runner-Phase Leser,
  Frist, Herabstufungsschwelle in `governance/melder-register.yaml`, geprüft über
  `tools/melder_register_check.py`; vierte Lautstärke `ℹ️ HINWEIS`, Checkliste 2h.
- 2026-09-02: **Phase 0.3 `modellwechsel`** ergänzt (#2690 K2) — Maßstab „bewertet mit ↔
  läuft mit"; laufendes Modell primär aus dem Session-Transkript, Alias-Tabelle nur als
  gewarnter Fallback (`tools/modellwechsel_check.py`), Checkliste 2g.
