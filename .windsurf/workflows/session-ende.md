---
description: Session beenden — Wissen sichern (via /knowledge-capture), Memory updaten, Repos committen/pushen
mode: write
---

# /session-ende

> Gegenstück `/session-start` · `LEHREN` = `docs/governance/session-skills-lehren/ende.md` ·
> Runner-Doku = `docs/governance/session-ende-runner.md`. Der Agent scannt die Session
> autonom; Owner/Org aus dem git-Remote, nie hardcoden. → `LEHREN#kopf`

---

## Phase E.R: Runner ausführen (PFLICHT — ersetzt −0.1/0a-deploy/0a-handover-pr/1b-Erzeuger/1c/3.1c/3.2-Banner/3.3)

Einzel-Befehle nur in `platform/tools/session_ende_checks.sh`, hier NICHT duplizieren.

// turbo
```bash
bash "${GITHUB_DIR:-$HOME/github}/platform/tools/session_ende_checks.sh" "$TARGET_REPO" \
  --session-id "$SESSION_ID"   # erste 8 Zeichen der Claude-Code-Session-ID
```

→ Ende = Summary `| Phase | Status | Repo | Note |` + `RESULT: OK|FAIL` +
  `JUDGMENT: 0a 0b 0c 0d 0e 2 3.5` — die Arbeitsliste für Phase 0/2/3.5.
→ **`RESULT: FAIL`** → Sitzung nicht abschließen, bis jedes ❌ behoben ist.
→ **Jede ⚠️ WARN-Zeile und jede `◌`/`SKIP`/`nicht messbar`-Zeile** gehört ins
  Abschluss-Board — die zweite Sorte als Lücke, nicht als Pass.
→ Der Runner **misst**, dieser Skill **deutet**. → `LEHREN#e-r`

| Phase | Bedeutung | kein Befund | Zug |
|---|---|---|---|
| `E.0 banner` | Platform-Version + Commit | — | Zahl in den Abschlussbericht |
| `E.1 deploy-status` | `failure:` = Prod nicht live · `waiting:` = Run hängt am Gate | Repo ohne Deploy-Workflow | transienter Flake: `gh run rerun <id> --failed`; sonst Run-ID als offenen Punkt ins Handover |
| `E.2 handover-prs` | >1 offener PR fasst `AGENT_HANDOVER.md` an | höchstens einer · im Fragment-Modus Übergangsbefund | Alt-Branch übernehmen ODER Alt-PR als „ersetzt durch #N" schließen, **vor** dem Push |
| `E.3 handover-frische` | ❌ Commits nach dem letzten Nachtrag, kein Handover-PR offen · ⚠️ Stand älter als letzter Datei-Commit · **Fragment-Modus:** ❌ kein eigenes Fragment · ❌ `veraltet` (danach weitere PRs) · ◌ Lease ohne `claude_session` | Exit 0, Nachtrag als PR, oder eigenes Fragment ohne späteren Sitzungs-PR | 0a-freshness bzw. 0b-fragment; `veraltet` → neues Fragment |
| `E.4 cross-repo-befunde` | Fremd-Repo-Befund ohne Artefakt oder Verzicht | Exit 0 | Deutung in 0f |
| `E.6 template-drift` | Error-Drift gegen die Repo-Templates | 0 Errors | fixen oder Issue im betroffenen Repo |
| `E.7 dirty-repos` | eigenes Repo mit uncommittetem Stand (Lease heute) | 0 eigene | in 3.1 committen; fremd dirty melden, nicht einsammeln |
| `E.8 worktree-hygiene` | ❌ Baum älter als 14 Tage (`SESSION_ENDE_WORKTREE_MAX_TAGE`); `prunable` räumt der Runner | keiner über der Grenze | entfernen (`repo-session.sh reap` / `git worktree remove`) oder Grund in `<gitdir>/behalten` |
| `E.9 dist-drift` | verteilte Skills weichen von `.windsurf/workflows/` ab | Lanes synchron | `cc-skill-dist/generate.py` laufen lassen, Diff committen |
| `E.10 session-abgleich` | ⚠️ `N Befund(e) dieser Sitzung: <refs>` (mit `--session-id` nur PRs der eigenen Branches; ohne: `kontoweit`) · ◌ Sitzung nicht zuordenbar | Exit 0 | je Ref Issue nachziehen oder Fehlalarm notieren (Zeile 25) |
| `E.11 main-status` | ⚠️ `rot auf main: <repo>: <Workflow> (<Run-ID>)` (jüngster Push-Lauf heute) · ◌ `nicht messbar` | kein Workflow zuletzt rot | **nicht auf rotes main mergen**; eigene Ursache fixen/`gh run rerun <id> --failed`, sonst Issue-Link ins Board |

**Läuft der Runner nicht** (Shell blockiert, keine Ausgabe nach 5 s): Session neu starten;
bis dahin nur `Read`/`Write`/`Edit` + `mcp__github__*`, und **auf einem Branch, nie auf
`main`** (ADR-242/GH013).

---

## Phase 0: Handover, Abnahme, Befunde (die `JUDGMENT`-Liste des Runners)

### 0a: Blockierte Arbeit dokumentieren (PFLICHT)

Wurde Arbeit blockiert (Shell-Hang, MCP-Fehler, Token)? (1) `.fixed`/`.updated`/`.new`
unübernommen? (2) Fragen an den User unbeantwortet? (3) CI-Runs ohne Verifikation? Jedes Ja
wird ein offener Punkt im Handover **mit dem konkreten Übernahme-Befehl**. → `LEHREN#0a`

### 0a-merge: Den eigenen Handover-PR selbst mergen (PFLICHT)

Sobald der Handover-PR grün ist, **ohne Rückfrage mergen** und im Abschlussbericht nennen:
`gh pr merge <N> --squash --delete-branch` (CI grün) bzw. `… --auto` (CI läuft noch).

**Vier Grenzen — dann PR offen lassen und im Abschlussbericht mit Grund nennen:** PR
enthält mehr als Dokumentation · ADR-Statuswechsel im selben PR · Repo mit
Auto-Deploy-on-`main` (Merge = Prod-Schritt, Gate 2) · CI rot oder Required Checks fehlen.
→ `LEHREN#0a-merge`

### 0b-fragment: Eigenes Fragment statt geteilter Dateien (PFLICHT in Repos mit `docs/handover.d/`)

Liegt `docs/handover.d/` im Repo, schreibt die Sitzung nur **ihre eigene** Datei; das
**ersetzt** 0a-freshness, 0b, 0c und den Eintrag in `AGENT_HANDOVER_LOG.md`:

```bash
python3 tools/agent-handover/fragments.py neu --session-id "$SESSION_ID" \
  --titel "<Sitzungsthema>" --ziel "<Zielzustand mit Issue>"
# ## Erledigt · ## Offen (je Punkt genau eine Issue-/PR-URL) · ## Log ausfüllen
python3 tools/agent-handover/fragments.py pruefen
```

Geteilte Handover-Dateien **nicht** anfassen. Fragment in den letzten (oder einen eigenen)
PR; nach dem Merge **unveränderlich**, Korrektur = neues Fragment. Danach noch ein PR →
neues Fragment, sonst `E.3` ❌. Memory (Phase 2) bleibt Pflicht. → `LEHREN#0b-fragment`

### 0a-freshness: Handover-Rezenz erzwingen (PFLICHT — Gate `handover-stale-vor-merge`)

Gemessen in **E.3**, gedeutet hier.

- **❌ FAIL** → seit dem letzten Nachtrag sind Commits gelandet und kein Handover-PR ist
  offen. Nachtragen, auch wenn der letzte Stand von einer Parallelsitzung stammt.
- **Exit 0** → frisch, weiter.
- **Exit 1** → Stand-Abschnitt JETZT nachziehen (Datum + Prio-Zeilen), dann erneut prüfen.
  Stehenlassen nur mit einem Satz Grund im Commit-/PR-Text. → `LEHREN#0a-freshness`

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

`AGENT_HANDOVER_LOG.md` **nur anhängen** (CI `handover-append-only`), `AGENT_HANDOVER.md`
**umschreiben**. Danach `git add docs/AGENT_HANDOVER.md && git commit -m "chore: update
AGENT_HANDOVER"`. → `LEHREN#0b`

### 0c: Erledigte/verschobene Prioritäten nachziehen (PFLICHT)

Hat die Session eine Aufgabe aus der `## Prioritäten`-Tabelle erledigt oder verschoben?

1. Tabelle aktualisieren — erledigte Zeile entfernen, Rest neu nummerieren, eine
   `> **Erledigt <Datum>:** …`-Notiz darunter, ein Stichpunkt in `## ⚡ Aktueller Stand`.
2. **Handover UND Memory (Phase 2) aktualisieren, nie nur eins.** → `LEHREN#0c`

### 0d: Abnahme gegen den Session-Zielzustand + SA-4-Zähler (PFLICHT)

1. **Abnahme:** für den in `/session-start` 2.7 geklärten Zielzustand genau einen Ausgang im
   Stand-Block: **erreicht** (Kriterien einzeln verifiziert) · **nicht erreicht** (mit dem
   fehlenden Kriterium) · **verschoben** (nur mit Tracking-Artefakt im selben Zug). Ohne
   Zielzustand: „Zielzustand: n/a (begründet)".
2. **SA-4-Zähler**, eine Zeile im Stand-Block: `SA-4: <n> Anwendungen · <m> Einzel-OK trotz
   Klassen-Deckung · <f> Fehlanwendungen`. `f > 0` → sofort als Befund melden. `m` speist
   den Kill-Test (Signal G, >30 %). → `LEHREN#0d`

### 0e: Clear-Härte — was überlebt den Kontext-Verlust? (PFLICHT)

Nach dem Handover-Block, **vor** Phase 1. Jedes „ja" bekommt im selben Zug ein dauerhaftes
Artefakt (Issue, Handover-Zeile, Memory) — Chat und PR-Text zählen nicht.

| # | Frage | Fix, falls ja |
|---|-------|---------------|
| 1 | Entscheidung, Textvorschlag oder Messwert nur im Gesprächsverlauf? | ins zugehörige Issue / den Handover schreiben |
| 2 | Etwas Dauerhaftes im Scratchpad / `/tmp`, das 3.1b wegräumt? | vorher an einen dauerhaften Ort |
| 3 | Dauerhaftes Dokument verweist auf Flüchtiges („siehe Sitzungsprotokoll", `/tmp`-Pfad)? | Verweis durch Inhalt oder echten Link ersetzen |

**Kein automatisches `/clear` einbauen.** → `LEHREN#0e`

### 0f: Cross-Repo-Befunde ins Zielrepo bringen (PFLICHT)

Gemessen in **E.4** (`tools/befund_journal.py --offen-cross-repo`), gedeutet hier. Exit 0 =
nichts offen. Exit 1 = je Befund **einen** der beiden Wege gehen:

| Weg | Wann | Kommando |
|---|---|---|
| Verankern | Der Befund gehört repariert | Issue **im Zielrepo**, dann `--verankert '<ID>' '<URL>'` |
| Verzicht | Nicht weiterverfolgen | `--verzichtet '<ID>' '<Grund>'` — ohne Grund zählt es nicht |

**Fremdes Repo = Scope-Checkpoint:** ab drei betroffenen Repos oder bei fremder Org
(`meiki-lra`, `ttz-lif`, `iilgmbh`) erst den Owner fragen.

**Jeder behandelte Melder-Befund bekommt ein Urteil** (Quote im Start als `0.7.19`):
`befund_journal.py --echt '<ID>' '<Notiz>'` bzw. `--falsch '<ID>' '<warum Fehlalarm>'`.

**Rückfällige Gates aus `tools/gate_wirkung.py`** (`/session-retro` 0.0/5a): **behandelt**
(Eintrag unter `docs/governance/gates/` im selben PR nachgezogen, Herabstufung = `declined`
mit Grund) **oder Verzicht mit Grund**, nie stehen lassen. → `LEHREN#0f`

### 0f-verankerung: Neues Gate nur mit Drill, Positivkontrolle, Messpunkt (PFLICHT)

Wird ein Gate verankert **oder neu verankert** (`revised`, neuer `drill`, neues `module`,
geänderter `mode`), dann **vor dem Commit**:

```bash
python3 tools/gate_verankerung_check.py --neu --basis origin/main
```

- **Exit 0** — `drill` (Datei existiert), `positivkontrolle: {ref, datum}` und Messpunkt
  (`slug` + `built`/`revised` als ISO-Datum) vorhanden. Darf in die Registry.
- **Exit 1** — **NICHT eintragen**, sondern in die `kandidaten`-Liste (platform#2234).
- **Exit 2** — Werkzeugfehler, kein Verdikt, kein Eintrag. → `LEHREN#0f-verankerung`

### 0h: Fremder Blick auf 0d und 0e (PFLICHT ab `full`)

| Footprint | Regel |
|---|---|
| **lean** (1 Repo, ≤2 PRs, kein Prod/Migration/Publish) | **überspringen** |
| **full / deep** (≥3 Repos ODER Prod/Publish ODER Migration) | **zwei Subagenten**, eng geführt |

- **Agent 1 (0d):** nur Zielzustand + Artefakte, nicht meine Erzählung; je Kriterium
  ERFÜLLT / NICHT ERFÜLLT / NICHT PRÜFBAR **mit Beleg**. Bei Abweichung gewinnt **sein** Urteil.
- **Agent 2 (0e):** **nur die durablen Artefakte** + die drei 0e-Fragen, kein Gesprächsverlauf.
- Beide Ergebnisse in den Stand-Block. Subagenten untersagt → inline, Bruch dort benennen.

Kosten ~110k Token je Sitzungsende. → `LEHREN#0h`

### 0i: Auftragsraum — keine Korrektur ohne Artefakt (PFLICHT)

`python3 tools/chat_agent/auftragsraum.py offen --block` (nur platform-Sessions). Exit 1:
je Zeile `regel <nachricht_id> --why …` ausführen oder Verzicht mit Grund im Stand-Block.
Offene Aufträge ohne Issue werden gemeldet, nicht angelegt (Start 1.8). Betriebsakte:
`docs/betrieb/auftragsraum.md`. → `LEHREN#0i`

---

## Phase 1: Wissen sichern — an `/knowledge-capture` delegieren (PFLICHT)

Outline-Schreiben **nicht hier inline duplizieren**. session-ende ruft `/knowledge-capture`
und **prüft den Erfolg**: Doc-URL/ID zurück? → für Phase 2 merken. Kein Ergebnis? →
offener Punkt im Handover (0b). → `LEHREN#1`

## Phase 1b: Docu-Drift — Zeiger statt Erzeuger

Doku-Lücke beim Committen (3.1) — README-Version ≠ Code-Version, leeres CHANGELOG, neue
Module ohne Doku — als Issue **ins betroffene Repo**, nicht in `platform`. → `LEHREN#1b`

## Phase 2: pgvector Memory schreiben (PFLICHT — ADR-154)

Pfad ist die CLI `platform/tools/session-memory`, **nicht** der MCP.

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
→ **`--session-id <slug>` bei Parallelbetrieb** (`tools/session-leases --repo <repo>`);
  `--allow-overwrite` überschreibt statt `<key>-2`. → `LEHREN#2`
→ **Error-Patterns** (nur Bug-Fixes): `--type error_pattern --key
  "error:<repo>:<YYYYMMDD>-<shortid>"`, Inhalt Symptom/Root Cause/Fix/Prevention. Weitere
  `--type`: open_task, decision, lesson_learned, repo_context, agent_handoff (Default `context`).

---

## Phase 3: Git Sync — WSL ↔ Dev Desktop (IMMER am Ende)

### 3.1 Alle geänderten Repos committen + pushen (PFLICHT)

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

→ **`[skip ci]` nur ins Squash-Subject beim Mergen** — **niemals** in einen Commit eines
  offenen PR-Branches, auch nicht zitiert. Leerer Check-Rollup = Befund; Reparatur:
  `git commit --amend` ohne den Token + Force-Push.
→ **NICHT pushen**, wenn der User „nicht pushen" sagt oder ein PR-Review läuft.
→ Fremde dirty Files (andere Session, unbekannte Herkunft): liegen lassen + melden.
→ `gh pr update-branch` nur bei Konflikt (`DIRTY`), nie nur wegen „hinter main“. → `LEHREN#3.1`

### 3.1b Cleanup: Temporäre Dateien entfernen (PFLICHT — nach 0e, nie davor)

`find ${GITHUB_DIR:-$HOME/github}/ -maxdepth 4 \( -name "*.fixed" -o -name "*.updated" -o
-name "*.new" \)` → prüfen ob übernommen, dann löschen; sonst User warnen. Worktrees:
Start 0.4.5 und `E.8`. → `LEHREN#3.1c`

### 3.2 Platform-Workflows + CC-Skills verteilen (IMMER — kein Conditional)

// turbo
```bash
GITHUB_DIR="${GITHUB_DIR:-$HOME/github}" \
  bash "${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-workflows.sh" \
  2>&1 | grep -cE "LINK|REPLACE" | xargs -I{} echo "{} Workflow-Symlinks aktualisiert"
```

→ dirty `platform` nur über Worktree-Branch + PR. `project-facts.md` macht der CI-Cron
  (on-demand `python3 platform/scripts/gen_project_facts.py --repo <name>`); CC-Skills über
  `platform/tools/cc-skill-dist/` (Messung `E.9`). → `LEHREN#3.2`

### 3.4: Abschluss — Maßnahmen statt Nacherzählung (PFLICHT, wenn etwas zu entscheiden ist)

1. **Erster Satz:** schließbar ja/nein — passend zur Clear-Freigabe-Zeile (3.5).
2. **Nummerierte Maßnahmen**, je Zeile Kürzel · Entscheidung · Empfehlung · Issue-/PR-Link
   (ohne Link = Verstoß gegen 0e); getrennt nach „dein Wort nötig" / „kann ich ohne dich".
3. **Beispielantwort** („Z1 Z3 go, Z4 Liste") für die Freigabe per Kürzel.

Eigene Prüfbelege in einem Satz. Nichts zu entscheiden → nur der erste Satz. → `LEHREN#3.4-abschluss`

### 3.5: Clear-Freigabe — expliziter letzter Satz (PFLICHT)

Letzter Output der Sitzung, nach der Abschluss-Checkliste, **genau eine** der beiden Zeilen:

- **🟢 CLEAR-FREIGABE: JA** — Checkliste vollständig grün UND alle drei 0e-Fragen mit „nein"
  beantwortet oder ihr Fix verankert (Issue/Handover/Memory, nicht nur Chat).
- **🔴 CLEAR-FREIGABE: NEIN — <konkreter Grund>** — mindestens ein Punkt **aus dieser
  Sitzung** offen (selbst dirty gemachtes Repo, offene Checkliste-Zeile, unbeantwortete oder
  ungefixte 0e-Frage). Der Grund benennt das fehlende Ding.

**Fremder Stand hemmt nicht** (fremd dirty, fremdes rotes Deploy, konkurrierender
Handover-PR): melden. Prüffrage „habe ich das dirty gemacht?" — per Änderungszeit und
Turn-Historie. Keine dritte Formulierung, kein Weglassen. → `LEHREN#3.5`

---

## Anti-Patterns (Skill ist `mode: write`)

- ❌ Owner/Org/MCP-Prefixe/IPs hardcoden; `mcpN_`-Nummern nie aus einem Skill-Text übernehmen.
- ❌ Memory-Calls mit der alten Windsurf-Signatur (`entry: {entry_id…}`) statt `entry_key`.
- ❌ Die Verbote aus Phase 1, 3.1 und E.R brechen: Outline inline, **`git add -A`**,
  Fremd-Artefakte einsammeln, Direkt-Push auf `main`, `SKIP`/`◌` als Entwarnung.

Re-Run ist sicher (idempotent). → `LEHREN#anti-patterns`

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
| 6 | Kein Repo aus DIESER Sitzung dirty; fremd dirty nur gemeldet (E.7) | ☐ |
| 7 | Keine .fixed/.updated Dateien übrig | ☐ |
| 8 | Blockierte Arbeit dokumentiert (0a) | ☐ |
| 9 | Doku-Lücke aus 3.1 als Issue im betroffenen Repo (1b) | ☐ |
| 10 | Template-Drift: Error-Drifts gefixt (E.6) | ☐ |
| 11 | Prios in Handover UND Memory nachgezogen (0c) — Fragment-Modus: Fragment, `pruefen` grün (0b-fragment) | ☐ |
| 12 | Konkurrierende `AGENT_HANDOVER.md`-PRs behandelt vor dem eigenen Push (E.2) | ☐ |
| 13 | Handover-Freshness: Exit 0 oder Grund im Commit-/PR-Text (E.3 / 0a-freshness); Fragment-Modus: E.3 grün | ☐ |
| 14 | Abnahme im Stand-Block: erreicht / nicht erreicht / verschoben+Tracking / n/a (0d) | ☐ |
| 15 | SA-4-Zähler-Zeile geschrieben, Fehlanwendung als Befund gemeldet (0d) | ☐ |
| 16 | Handover-PR gemergt — oder eine der vier Grenzen benannt (0a-merge) | ☐ |
| 17 | Rückfälliges Gate aus `tools/gate_wirkung.py` behandelt ODER Verzicht mit Grund (0f) | ☐ |
| 18 | Clear-Härte: nichts Dauerhaftes lebt nur im Chat oder im Scratchpad (0e) | ☐ |
| 19 | Cross-Repo-Befunde: Exit 0, oder je Befund verankert bzw. verzichtet (E.4 / 0f) | ☐ |
| 21 | Clear-Freigabe-Zeile als letzter Satz — 🟢 JA oder 🔴 NEIN + Grund (3.5) | ☐ |
| 22 | Gate verankert? `gate_verankerung_check.py --neu` grün, sonst Kandidat (0f-verankerung) | ☐ |
| 23 | Ab `full`: 0d und 0e von je einem fremden Agenten gegengelesen (0h) | ☐ |
| 24 | Auftragsraum: `offen --block` Exit 0, oder je Korrektur `regel` bzw. Verzicht mit Grund (0i) | ☐ |
| 25 | `E.10 session-abgleich`: Exit 0, oder je Befund Issue bzw. notierter Fehlalarm | ☐ |
| 26 | Letzte Antwort: „schließbar ja/nein", Maßnahmen mit Empfehlung + Link, Beispielantwort (3.4) | ☐ |

**Neue Pflicht-Phase ⇒ Checklisten-Zeile im selben PR**; Auswahl über
`grep -n "^## \|^### "` und Einzelbeurteilung, **nicht** über das Wort „PFLICHT".
Nummern bleiben stabil (Zeile 20 entfiel). → `LEHREN#abschluss-selbstcheck`

---

## Laufzeit

`LAUFZEIT:`-Zeile; Schalter `SESSION_CHECKS_TIMING=voll`, `SESSION_CHECKS_PARALLEL`,
`DRIFT_CHECK_PARALLEL`, `SESSION_CHECKS_VORLAUF_BEHALTEN=1`. Teuerste Phase: E.6. → `LEHREN#laufzeit`

## Changelog

- 2026-10-06: **Kürzung, Zusagen-Prüfer entfernt** (V2b, platform#3785).
- 2026-10-05: **Runner-Phase E.11 main-status** (Retro 8a0235 R14).
- 2026-10-05: **Phase 3.4 Abschluss-Maßnahmen + Checklisten-Zeile 26** (platform#3716).

> Nur die letzten drei Einträge (Policy seit platform#2696). Wortlaut: `LEHREN#changelog-historie`.
