---
description: Session beenden — Wissen sichern (via /knowledge-capture), Memory updaten, Repos committen/pushen
mode: write
---

# /session-ende

> Gegenstück `/session-start` · `LEHREN` = `docs/governance/session-skills-lehren/ende.md` ·
> Runner-Doku = `docs/governance/session-ende-runner.md`.
> **Der User muss NICHTS auflisten** — der Agent scannt die Session autonom. Läuft in
> Claude Code (ADR-230): stabile Tool-Namen `mcp__github__*`/`mcp__orchestrator__*`, nie
> `mcpN_` (Quelle: `project-facts.md`); Owner/Org aus dem git-Remote, nie hardcoden.
> **Platform Sync Loop:** Ende = commit → push → GitHub → alle Repos beim nächsten Start.
> GitHub ist die einzige Source of Truth (Diagramm in `/session-start`).

---

## Phase E.R: Runner ausführen (PFLICHT — NEU 2026-09-02; ersetzt −0.1/0a-deploy/0a-handover-pr/1b-Erzeuger/1c/3.1c/3.2-Banner/3.3)

Die mechanischen Phasen laufen in **einem** Aufruf und sind damit strukturell nicht
überspringbar; die Einzel-Befehle leben in `platform/tools/session_ende_checks.sh` (dort
gepflegt, hier NICHT duplizieren).

// turbo
```bash
bash "${GITHUB_DIR:-$HOME/github}/platform/tools/session_ende_checks.sh" "$TARGET_REPO"
```

→ Ende = Summary `| Phase | Status | Repo | Note |` + `RESULT: OK|FAIL` +
  `JUDGMENT: 0a 0b 0c 0d 0e 2 3.5` — diese Zeile ist die Arbeitsliste für Phase 0/2/3.5.
→ **`RESULT: FAIL`** → Sitzung nicht abschließen, bis jedes ❌ behoben ist.
→ **Jede ⚠️ WARN-Zeile ist ein Befund** und gehört ins Abschluss-Board der Sitzung.
→ **Jede `◌`/`SKIP`/`nicht messbar`-Zeile ist eine Lücke, kein Pass — als solche ins Board.**
→ Der Runner **misst**, dieser Skill **deutet**. Herleitung je Phase: `LEHREN`.

| Phase | Bedeutung | kein Befund | Zug |
|---|---|---|---|
| `E.0 banner` | Platform-Version + Commit | — | Zahl in den Abschlussbericht |
| `E.1 deploy-status` | `failure:` = Prod nicht live · `waiting:` = Run hängt am Gate | Repo ohne Deploy-Workflow | transienter Flake: `gh run rerun <id> --failed`; sonst Run-ID als offenen Punkt ins Handover |
| `E.2 handover-prs` | >1 offener PR fasst `AGENT_HANDOVER.md` an | höchstens einer | Alt-Branch übernehmen ODER Alt-PR als „ersetzt durch #N" schließen, **vor** dem Push |
| `E.3 handover-frische` | Stand älter als der letzte Commit der Datei | Exit 0 | Deutung in 0a-freshness |
| `E.4 cross-repo-befunde` | Fremd-Repo-Befund ohne Artefakt oder Verzicht | Exit 0 | Deutung in 0f |
| `E.5 zusagen` | Vertagung ohne Anker im Segment (advisory) | `✅` je Zusage | Deutung in 0g |
| `E.6 template-drift` | Error-Drift gegen die Repo-Templates | 0 Errors | fixen oder Issue im betroffenen Repo |
| `E.7 dirty-repos` | eigenes Repo mit uncommittetem Stand (Lease heute) | 0 eigene | in 3.1 committen; fremd dirty melden, nicht einsammeln |
| `E.8 worktree-reap` | SKIP: räumt `session_start_checks.sh` 0.4.5 über alle Leases | immer | keiner — sonst dieselbe Mechanik doppelt |
| `E.9 dist-drift` | verteilte Skills weichen von `.windsurf/workflows/` ab | Lanes synchron | `cc-skill-dist/generate.py` laufen lassen, Diff committen |

**Läuft der Runner nicht** (Shell blockiert, keine Ausgabe nach 5 s): Session neu starten;
bis dahin nur `Read`/`Write`/`Edit` + `mcp__github__*`, und **auf einem Branch, nie auf
`main`** (geschützt in platform + 10 Repos, ADR-242/GH013).

---

## Phase 0: Handover, Abnahme, Befunde (die `JUDGMENT`-Liste des Runners)

### 0a: Blockierte Arbeit dokumentieren (PFLICHT)

Wurde Arbeit blockiert (Shell-Hang, MCP-Fehler, Token)? (1) `.fixed`/`.updated`/`.new`
unübernommen? (2) Fragen an den User unbeantwortet? (3) CI-Runs ohne Verifikation? Jedes Ja
wird ein offener Punkt im Handover **mit dem konkreten Übernahme-Befehl**. → `LEHREN#0a`

### 0a-merge: Den eigenen Handover-PR selbst mergen (PFLICHT — Owner-Weisung 2026-08-10)

Sobald der Handover-PR grün ist, **ohne Rückfrage mergen** und im Abschlussbericht nennen:
`gh pr merge <N> --squash --delete-branch` (CI grün) bzw. `… --auto` (CI läuft noch).

**Grenzen — hier gilt die Weisung NICHT, dann bleibt es bei der Vorlage:**

| Bedingung | Warum |
|---|---|
| PR enthält mehr als Dokumentation | Code/Konfiguration ist eine Entscheidung, kein Bericht |
| ADR-Statuswechsel im selben PR | Aussage über Wirklichkeit, kein Protokoll |
| Repo mit Auto-Deploy-on-`main` | Der Merge IST dort der Prod-Schritt → Gate 2 |
| CI rot oder Required Checks fehlen | Grün ist die Bedingung, nicht die Formalie |

→ Trifft eine Grenze zu: PR offen lassen, im Abschlussbericht **mit Grund** nennen.
→ `LEHREN#0a-merge`

### 0a-freshness: Handover-Rezenz erzwingen (PFLICHT — Gate `handover-stale-vor-merge`)

Gemessen in `session_ende_checks.sh` **E.3**, gedeutet hier. Registry-`module`:
`scripts/checks/agent_handover_freshness_check.py`; zusätzlich läuft
`.github/workflows/handover-freshness-advisory.yml` bei **jedem** PR (Registry-Revision
2026-08-20).

- **Exit 0** → frisch, weiter.
- **Exit 1** → Stand-Abschnitt JETZT nachziehen (Datum + Prio-Zeilen), dann erneut prüfen.
  Ihn stehen zu lassen ist zulässig, braucht aber einen Satz mit Grund im Commit-/PR-Text —
  stillschweigend stale mergen ist der ×12-Verstoß. → `LEHREN#0a-freshness`

### 0b: AGENT_HANDOVER.md aktualisieren (PFLICHT bei WIP-Stand)

Für jedes Repo mit uncommittetem Stand (Runner-Phase `E.7`) den Abschnitt
**„⚡ Aktueller Stand"** aktualisieren:

```markdown
## ⚡ Aktueller Stand (<DATUM>)
**Aktiver Branch:** `<branch>`
**Was wurde implementiert:** <Datei> — <1-Zeile geändert/neu>
**Uncommitted Changes:** <git status --short>
**Nächster Schritt:** <konkret, copy-pasteable Befehle>
**Session Resume:** claude --resume <session-id>
```

**Zwei Ziele, zwei Regeln:** `AGENT_HANDOVER_LOG.md` wird **nur angehängt** (neuer Block ans
Ende, bestehende Einträge nie ändern — CI-Check `handover-append-only` blockt Verstöße).
`AGENT_HANDOVER.md` wird **umgeschrieben** (0c verlangt das); Konflikte bleiben laut.
Danach `git add docs/AGENT_HANDOVER.md && git commit -m "chore: update AGENT_HANDOVER"` —
`/session-start` Phase 1 liest die Datei beim nächsten Mal. → `LEHREN#0b`

### 0c: Erledigte/verschobene Prioritäten nachziehen (PFLICHT — NEU 2026-06-24)

Hat die Session eine Aufgabe aus der `## Prioritäten`-Tabelle erledigt oder verschoben?

1. Tabelle aktualisieren — erledigte Zeile entfernen, Rest neu nummerieren, eine
   `> **Erledigt <Datum>:** …`-Notiz darunter, ein Stichpunkt in `## ⚡ Aktueller Stand`.
2. **Handover UND Memory (Phase 2) aktualisieren, nie nur eins.** Cross-Host-Sessions
   (iPad/claude.ai) schreiben nur ins geteilte pgvector-Memory → der git-getrackte Handover
   driftet. → `LEHREN#0c`

### 0d: Abnahme gegen den Session-Zielzustand + SA-4-Zähler (PFLICHT — NEU 2026-08-07)

1. **Abnahme:** für den in `/session-start` 2.7 geklärten Zielzustand genau einen Ausgang im
   Stand-Block: **erreicht** (Kriterien einzeln verifiziert, nicht pauschal) · **nicht
   erreicht** (mit dem fehlenden Kriterium) · **verschoben** (nur mit Tracking-Artefakt im
   selben Zug). Ohne Zielzustand: „Zielzustand: n/a (begründet)".
2. **SA-4-Zähler**, eine Zeile im Stand-Block: `SA-4: <n> Anwendungen · <m> Einzel-OK trotz
   Klassen-Deckung · <f> Fehlanwendungen`. `f > 0` → SA-4 fällt auf Einzelfreigabe zurück:
   sofort als Befund melden. `m` speist den Kill-Test (Signal G, >30 %). → `LEHREN#0d`

### 0e: Clear-Härte — was überlebt den Kontext-Verlust? (PFLICHT — NEU 2026-08-12)

Nach dem Handover-Block, **vor** Phase 1, drei Fragen. Jede mit „ja" beantwortete Zeile
bekommt im selben Zug ein dauerhaftes Artefakt (Issue-Kommentar, Handover-Zeile,
Memory-Datei) — „steht im Gesprächsverlauf" zählt so wenig wie „steht im PR-Text".

| # | Frage | Fix, falls ja |
|---|-------|---------------|
| 1 | Entscheidung, Textvorschlag oder Messwert nur im Gesprächsverlauf? | ins zugehörige Issue / den Handover schreiben |
| 2 | Etwas Dauerhaftes im Scratchpad / `/tmp`, das 3.1b wegräumt? | vorher an einen dauerhaften Ort |
| 3 | Dauerhaftes Dokument verweist auf Flüchtiges („siehe Sitzungsprotokoll", `/tmp`-Pfad)? | Verweis durch Inhalt oder echten Link ersetzen |

**Frage 3 ist die gefährlichste**, weil sie als einzige nicht auffällt. **Kein
automatisches `/clear` einbauen** — der Wert steckt in der Frage. → `LEHREN#0e`

### 0f: Cross-Repo-Befunde ins Zielrepo bringen (PFLICHT — NEU 2026-08-16, platform#2004)

Gemessen in `session_ende_checks.sh` **E.4** (`tools/befund_journal.py --offen-cross-repo`),
gedeutet hier. Exit 0 = nichts offen. Exit 1 = je Befund **einen** der beiden Wege gehen:

| Weg | Wann | Kommando |
|---|---|---|
| Verankern | Der Befund gehört repariert | Issue **im Zielrepo**, dann `--verankert '<ID>' '<URL>'` |
| Verzicht | Nicht weiterverfolgen | `--verzichtet '<ID>' '<Grund>'` — ohne Grund zählt es nicht |

**Das Issue gehört ins Zielrepo, nicht hierher.** **Fremdes Repo = Scope-Checkpoint:** ab
drei betroffenen Repos oder bei fremder Org (`meiki-lra`, `ttz-lif`, `iilgmbh`) erst den
Owner fragen.

**Jeder behandelte Melder-Befund bekommt `--echt` oder `--falsch`** — ohne Urteil ist die
Präzision des Melders unbekannt (Quote im Start als `0.7.19`, ab drei Urteilen):
`befund_journal.py --echt '<ID>' '<Notiz>'` bzw. `--falsch '<ID>' '<warum Fehlalarm>'`.

**Rückfällige Gates aus Start-Phase 0.7.7** (Gate `gate-rueckfall-unbemerkt`,
Registry-`module` `tools/gate_wirkung.py`): genau zwei zulässige Abschlüsse — **behandelt**
(Gate ausgeweitet/umgebaut/herabgestuft, `docs/governance/gate-registry.json` im selben PR
nachgezogen, bei Herabstufung `declined` mit Begründung) **oder Verzicht mit Grund**. Die
Zeile stehen zu lassen ist keine dritte Antwort. → `LEHREN#0f`

### 0f-verankerung: Neues Gate nur mit Drill, Positivkontrolle, Messpunkt (PFLICHT — NEU 2026-09-02, platform#2690 K4)

Wird ein Gate verankert **oder neu verankert** (`revised`, neuer `drill`, neues `module`,
geänderter `mode`), dann **vor dem Commit**:

```bash
python3 tools/gate_verankerung_check.py --neu --basis origin/main
```

- **Exit 0** — der Eintrag trägt alle drei Nachweise: `drill` (Datei existiert),
  `positivkontrolle: {ref, datum}`, Messpunkt (`slug` in Slug-Form + `built`/`revised` als
  ISO-Datum). Er darf in die Registry.
- **Exit 1** — der Eintrag wird **NICHT eingetragen**, sondern geht in die
  `kandidaten`-Liste der Registry (Tracking: platform#2234).
- **Exit 2** — Werkzeugfehler (Basis nicht lesbar). Kein Verdikt, also auch kein Eintrag.

`faengt` ersetzt die Positivkontrolle nicht. Alt-Einträge fordert `--neu` nicht rückwirkend
ein; Nachziehen des Bestands: platform#2703. → `LEHREN#0f-verankerung`

### 0g: Zusagen dieser Sitzung gegen Tracking-Artefakte prüfen (PFLICHT — NEU 2026-08-23, platform#2211)

Gemessen in `session_ende_checks.sh` **E.5** (`tools/verankerung_pruefer.py` über die eigenen
PR-Texte von heute), gedeutet hier. Gate `zusage-ohne-verankerung`, Registry-`module`
`tools/verankerung_pruefer.py`. Geprüft wird der **Typ** der Zusage, nicht ihr Wortlaut.

- **`✅`** — jede erkannte Zusage trägt ein Tracking-Issue. Weiter.
- **`⚠️`** — je Stelle **eine** von zwei Antworten, nie keine: Issue anlegen und die Nummer
  **im selben Abschnitt** des PR-Textes nennen, **oder** die Meldung als Fehlalarm in
  `docs/governance/verankerung-kalibrierung-2026-08-23.md` notieren (mit Zitat).
- **`◌ NICHT PRUEFBAR`** (kein Klassifikator erreichbar) und **`◌ … UNGEPRUEFT`**
  (Zeitbudget erschöpft, rund 80 s je Segment) benennen eine Lücke — die dort genannten
  Segmente sind nicht angesehen worden.

**Modus `advisory`** bei gemessener Präzision 0,50 — der Befund wird gelesen, nicht
erzwungen. → `LEHREN#0g`

---

### 0h: Fremder Blick auf 0d und 0e (PFLICHT ab `full` — NEU 2026-08-17, Owner-Freigabe)

0d und 0e sind **Selbstbeurteilung** — die Restmenge setze ich selbst, und was nur im
Gesprächsverlauf lebt, fühlt sich für mich vorhanden an. Für genau das führt
`/session-retro` seit jeher „Richter ≠ Angeklagter".

| Footprint | Regel |
|---|---|
| **lean** (1 Repo, ≤2 PRs, kein Prod/Migration/Publish) | **überspringen** |
| **full / deep** (≥3 Repos ODER Prod/Publish ODER Migration) | **zwei Subagenten**, eng geführt |

- **Agent 1 (zu 0d)** bekommt nur Zielzustand und Artefakte, **nicht** meine Erzählung:
  je Kriterium ERFÜLLT / NICHT ERFÜLLT / NICHT PRÜFBAR **mit Beleg**. Weicht sein Urteil
  ab, gewinnt **seins** im Stand-Block.
- **Agent 2 (zu 0e)** bekommt **ausschließlich die durablen Artefakte** und die drei
  0e-Fragen. Er darf den Gesprächsverlauf **nicht** sehen — das ist der Punkt.
- Beide Ergebnisse in den Stand-Block, auch wenn sie unbequem sind.
- **Subagenten untersagt?** 0d/0e inline, aber den Bruch **im Stand-Block benennen**.

**Kosten, damit die Entscheidung bewusst fällt:** ~55k Token je Agent ⇒ **~110k je
Sitzungsende** dieser Klasse. Deshalb der Footprint-Schalter statt „immer". → `LEHREN#0h`

---

## Phase 1: Wissen sichern — an `/knowledge-capture` delegieren (PFLICHT)

Outline-Schreiben **nicht hier inline duplizieren** — Klassifikation, Cross-Repo-Tagging und
Tool-Wahl macht `/knowledge-capture`. session-ende ruft es und **prüft den Erfolg**:
Doc-URL/ID zurück? → für Phase 2 merken. Kein Ergebnis? → offener Punkt im Handover (0b).

## Phase 1b: Docu-Drift — Zeiger statt Erzeuger

Der Verarbeiter läuft als CI (`.github/workflows/docu-update-agent.yml`); die Erzeugung von
`[docu-update]`-Issues ist kein Schritt dieses Skills mehr. Fällt beim Committen (3.1) eine
Doku-Lücke auf — README-Version ≠ Code-Version, leeres CHANGELOG, neue Module ohne Doku —,
gehört sie als Issue **ins betroffene Repo**, nicht in `platform`. → `LEHREN#1b`

## Phase 2: pgvector Memory schreiben (PFLICHT — ADR-154)

Primärer Pfad ist die CLI `platform/tools/session-memory`, **nicht** der MCP: sie wirkt
unabhängig von der MCP-Bindung in jedem Repo.

```bash
cat > /tmp/session-summary.md <<'SUMEOF'
# Session <date> — <repo>   ## Erledigt … ## Entscheidungen … ## Offen …
SUMEOF
python3 "${GITHUB_DIR:-$HOME/github}/platform/tools/session-memory" write \
  --repo <repo> --title "Session <date> — <repo>: <1-Zeile>" --session-id <kurz-slug> \
  --tag session --tag <repo> --tag <task-type> --content-file /tmp/session-summary.md
```

→ **Verifizieren, bevor „gesichert" behauptet wird:** `session-memory get --key <entry_key
  aus der Ausgabe>` — der ausgegebene Key, nicht der erwartete.
→ **`--session-id <slug>` bei Parallelbetrieb** (`tools/session-leases --repo <repo>` zeigt
  es). Ohne ihn weicht die CLI auf `<key>-2`, `-3`, … aus statt zu überschreiben;
  `--allow-overwrite` erzwingt das alte Verhalten. → `LEHREN#2`
→ **Error-Patterns** (nur bei Bug-Fixes): gleiche CLI, `--type error_pattern`,
  `--key "error:<repo>:<YYYYMMDD>-<shortid>"`, Inhalt Symptom/Root Cause/Fix/Prevention.
→ `entry_type` default `context`; `--type`-Werte: open_task | decision | lesson_learned |
  error_pattern | repo_context | agent_handoff.

---

## Phase 3: Git Sync — WSL ↔ Dev Desktop (IMMER am Ende)

### 3.1 Alle geänderten Repos committen + pushen (PFLICHT — Session-Attribution, Protection-aware)

Pro Repo aus `E.7 dirty-repos`:

```bash
cd "$repo"
BR=$(git branch --show-current)   # Branch IMMER re-checken, vor jedem Commit
git status --porcelain            # sichten: gehört jede Datei zu DIESER Session?
git add <datei1> <datei2>         # explizit — nie `git add -A`
git commit -m "session-ende($(basename $repo)): $(date +%Y-%m-%d) — <Beschreibung>"
# main? Schutz prüfen: gh api "repos/{owner}/<repo>/rules/branches/main" --jq 'length'
# > 0  → ⛔ Direkt-Push scheitert (ADR-242): repo-session.sh start . --task session-ende-sync
# sonst: git push   ·   Session-Branch: git push -u origin "$BR", danach PR
```

→ **`[skip ci]` gehört nur ins Squash-Subject beim Mergen** (`gh pr merge --squash --subject
  "… [skip ci]"`) — **niemals** in einen Commit eines offenen PR-Branches, auch nicht
  zitiert: GitHub matcht den Marker im gesamten Commit-Body und überspringt dann **alle**
  Läufe, auch das `pull_request`-Event. Erkennungsmerkmal ist ein **leerer Check-Rollup** —
  der ist kein „läuft noch", sondern der Befund. Reparatur: `git commit --amend` ohne den
  Token + Force-Push; close/reopen ist überflüssig.
→ **NICHT pushen**, wenn der User „nicht pushen" sagt oder ein PR-Review läuft.
→ Fremde dirty Files (andere Session, unbekannte Herkunft): liegen lassen + melden.
→ **Rebase-on-ready:** `gh pr update-branch` erst unmittelbar vor dem finalen Push/Merge.
  → `LEHREN#3.1`

### 3.1b Cleanup: Temporäre Dateien entfernen (PFLICHT — nach 0e, nie davor)

`find ${GITHUB_DIR:-$HOME/github}/ -maxdepth 4 \( -name "*.fixed" -o -name "*.updated" -o
-name "*.new" \)` → prüfen ob übernommen, dann löschen; sonst User warnen. Gemergte
Session-Worktrees räumt `session_start_checks.sh` 0.4.5 über **alle** Leases ab (`E.8` steht
deshalb auf SKIP). → `LEHREN#3.1c`

### 3.2 Platform-Workflows + CC-Skills verteilen (IMMER — kein Conditional)

// turbo
```bash
GITHUB_DIR="${GITHUB_DIR:-$HOME/github}" \
  bash "${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-workflows.sh" \
  2>&1 | grep -cE "LINK|REPLACE" | xargs -I{} echo "{} Workflow-Symlinks aktualisiert"
```

→ `platform` selbst ist geschützt (ADR-242): dirty `platform` geht über Worktree-Branch +
  PR, nie per Direkt-Push auf `main`.
→ `project-facts.md` erzeugt der CI-Cron `gen-project-facts.yml` (Mo 04:00 UTC) — hier
  nicht zusätzlich. On-demand: `python3 platform/scripts/gen_project_facts.py --repo <name>`.
→ Für **CC-Skills** ist `platform/tools/cc-skill-dist/` der kanonische Weg (Messung `E.9`).
  → `LEHREN#3.2`

### 3.5: Clear-Freigabe — expliziter letzter Satz (PFLICHT — NEU 2026-08-30, Owner-Weisung)

Letzter Output der Sitzung, nach der Abschluss-Checkliste, **genau eine** der beiden Zeilen:

- **🟢 CLEAR-FREIGABE: JA** — Checkliste vollständig grün UND alle drei 0e-Fragen mit „nein"
  beantwortet oder ihr Fix verankert (Issue/Handover/Memory, nicht nur Chat).
- **🔴 CLEAR-FREIGABE: NEIN — <konkreter Grund>** — mindestens ein Punkt offen (dirty Repo,
  offene Checkliste-Zeile, unbeantwortete oder ungefixte 0e-Frage). Der Grund benennt das
  fehlende Ding, nicht nur „nicht grün".

Keine dritte Formulierung, kein Weglassen dieser Zeile. → `LEHREN#3.5`

---

## Anti-Patterns (Skill ist `mode: write`)

- ❌ Owner/Org/MCP-Prefixe/IPs hardcoden — Owner aus dem git-Remote ableiten, Tools mit
  stabilen CC-Namen nennen, `mcpN_`-Nummern nie aus einem Skill-Text übernehmen
  (`project-facts.md` + `ToolSearch` sind die Quelle).
- ❌ Outline-Schreiben hier inline duplizieren statt an `/knowledge-capture` zu delegieren
  und den **Erfolg zu prüfen**.
- ❌ `git push`, wenn der User „nicht pushen" sagt oder ein PR-Review läuft (3.1).
- ❌ **`git add -A` — in keiner Phase.** Immer explizite Pfade nach Sichtung
  (🌀 `feedback_git_add_all_swept_artifacts`: .pyc/.coverage landeten in Commits).
- ❌ Fremd-Session-Artefakte einsammeln — dirty Files ohne Bezug zur eigenen Turn-Historie
  melden statt committen (🌀 Session-Attribution, Realfall #734).
- ❌ Direkt-Push auf geschützte `main`-Branches (ADR-242) — Session-Branch + PR ist der Pfad.
- ❌ Memory-Calls mit der alten Windsurf-Signatur (`entry: {entry_id…}`) — die CC-Signatur
  ist flach mit `entry_key`.
- ❌ Eine Runner-Zeile mit `SKIP`/`◌` als Entwarnung verbuchen (E.R).

**Idempotenz:** Re-Run ist sicher — Commits/Sync sind wiederholbar, der Runner ist read-only,
Memory-Upserts deduplizieren per `content_hash`.

---

## Abschluss-Checkliste (PFLICHT — muss alles grün sein)

| # | Check | Status |
|---|-------|--------|
| 0 | Runner gelaufen, Summary gezeigt, jede WARN gespiegelt (E.R) | ☐ |
| 1 | Outline-Dokument geschrieben/aktualisiert | ☐ |
| 2 | pgvector Session-Summary gespeichert, `entry_key` verifiziert | ☐ |
| 3 | Error-Patterns erfasst (falls Bug-Fix) | ☐ |
| 4 | Alle Repos committed + pushed | ☐ |
| 5 | Platform gepusht → Workflows sync → Skill-Lanes synchron (E.9) | ☐ |
| 6 | Kein eigenes Repo dirty (E.7) | ☐ |
| 7 | Keine .fixed/.updated Dateien übrig | ☐ |
| 8 | Blockierte Arbeit dokumentiert (0a) | ☐ |
| 9 | Doku-Lücke aus 3.1 als Issue im betroffenen Repo (1b) | ☐ |
| 10 | Template-Drift: Error-Drifts gefixt (E.6) | ☐ |
| 11 | Erledigte/verschobene Prios in Handover UND Memory nachgezogen (0c) | ☐ |
| 12 | Konkurrierende `AGENT_HANDOVER.md`-PRs behandelt vor dem eigenen Push (E.2) | ☐ |
| 13 | Handover-Freshness: Exit 0 oder Grund im Commit-/PR-Text (E.3 / 0a-freshness) | ☐ |
| 14 | Abnahme im Stand-Block: erreicht / nicht erreicht / verschoben+Tracking / n/a (0d) | ☐ |
| 15 | SA-4-Zähler-Zeile geschrieben, Fehlanwendung als Befund gemeldet (0d) | ☐ |
| 16 | Handover-PR gemergt — oder eine der vier Grenzen benannt (0a-merge) | ☐ |
| 17 | Rückfälliges Gate aus Start 0.7.7 behandelt ODER Verzicht mit Grund (0f) | ☐ |
| 18 | Clear-Härte: nichts Dauerhaftes lebt nur im Chat oder im Scratchpad (0e) | ☐ |
| 19 | Cross-Repo-Befunde: Exit 0, oder je Befund verankert bzw. verzichtet (E.4 / 0f) | ☐ |
| 20 | Zusagen-Prüfer: `✅`, oder je Meldung Issue bzw. dokumentierter Fehlalarm (E.5 / 0g) | ☐ |
| 21 | Clear-Freigabe-Zeile als letzter Satz — 🟢 JA oder 🔴 NEIN + Grund (3.5) | ☐ |
| 22 | Gate verankert? `gate_verankerung_check.py --neu` grün, sonst Kandidat (0f-verankerung) | ☐ |
| 23 | Ab `full`: 0d und 0e von je einem fremden Agenten gegengelesen (0h) | ☐ |

**Neue Pflicht-Phase ⇒ Checklisten-Zeile im selben PR**; Auswahl über
`grep -n "^## \|^### "` und Einzelbeurteilung, **nicht** über das Wort „PFLICHT".
→ `LEHREN#abschluss-selbstcheck`

---

## Changelog

- 2026-09-02: **Phase 0h Fremder Blick (PFLICHT ab `full`) + Checklisten-Zeile 23** (#2036) —
  Owner-Freigabe für Subagenten in den Session-Skills, ausdrücklich **selbstbetreffend**.
  Nur 0d und 0e bekommen fremden Kontext; der mechanische Rest bleibt Skript. Der Zweig
  stammt vom 2026-08-17 und hieß dort `0g`; `main` vergab denselben Buchstaben inzwischen
  an #2211, deshalb `0h` und Zeile 23. Beim Nachziehen **neu geschrieben** statt gemergt:
  `main` hatte die Datei zwischenzeitlich von 55 auf 20 kB gekürzt, ein Merge hätte das
  zurückgedreht. Herleitung in `LEHREN#0h`.

> Nur die letzten drei Einträge (Policy seit platform#2696). Volle Historie:
> `LEHREN#changelog-historie`.

- 2026-09-02: **Kontext-Diät + Runner-Verdrahtung** (#2690 K5, +K1) — 55 516 → ~20 400 B.
  Phase `E.R` ruft `tools/session_ende_checks.sh` (E.0–E.9) und ersetzt die mechanischen
  Abschnitte; Lehren/Historie in `session-skills-lehren/ende.md`; gestrichen: S2–S5.
- 2026-09-02: **Phase 0f-verankerung (PFLICHT) + Checklisten-Zeile 22** (#2690 K4) — ein Gate
  kommt nur mit Drill, Positivkontrolle und Messpunkt in die Registry. Anlass: 14 von 33
  Gates rückfällig, 0 von 31 Einträgen mit Beleg eines echten Treffers (#2374, #2678).
- 2026-08-30: **Phase 3.5 Clear-Freigabe (PFLICHT) + Checklisten-Zeile 21** — Owner wörtlich:
  „session-ende liefert häufig keinen sauberen Zustand für clear." Die Antwort auf die
  0e-Frage wird laut ausgesprochen statt in einem Häkchen verborgen.
