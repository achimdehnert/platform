---
retro_schema: 1
date: 2026-10-08
repo_scope: [meiki-hub, meiki-dms, post-hub, buerger-hub, frist-hub, schreib-hub, iil-assist-core, iil-doc-templates, shared-ci, platform]
session_id: 767d40-incr
footprint: deep
findings_total: 18
findings_survived: 10
refuted_rate: 0.39
phase3_refuted: 6
pre_refuted: 1
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [fremde-worktrees-beendet, edit-in-worktree-without-read, rohes-pytest-statt-make-test, shared-ci-action-ungepinnt]
recurring_findings: [deferred-item-no-tracking-issue, edit-in-worktree-without-read, edit-after-compaction-without-reread, hook-block-wiederholt-gleiches-muster, claim-before-cheapest-check, rohes-pytest-statt-make-test]
gates_caught: [claim-before-cheapest-check, direct-gh-pr-merge-bypasses-sa-m, parallel-subagents-shared-scratch-state]
gates_verwandt: [worktree-midsession-accumulation, scope-checkpoint-not-durably-recorded, issue-offen-nach-gemergtem-fix]   # Begründung je Fall in der Recurrence-Spalte von §2 (#1, #5, #6)
over_ask_klassen: []
over_act_klassen: [fremde-worktrees-beendet]
widerlegung: "1 gekippt, 2 neu"
streichkandidaten: []
streich_begruendung: "Keine Phase ohne Wirkung: Skeptiker kippten 6 von 13 Bewertungsbefunden, 2.5 klärte zwei Fakt-Widersprüche, 3b kippte einen Befund samt falschem Gate-Rückfall und fand zwei neue."
---

# Session-Retro 767d40-incr — H1 „Keine Haus-Literale im Code“ und S12-8/9/12

Nachtrag zu [767d40](session-retro-2026-10-07-meiki-hub-767d40.md) (platform#3839), gleiche Sitzung (Transkript `363309f7`). Fenster 2026-10-07T21:59Z bis 2026-10-08T09:14Z.

Owner-Aufträge im Fenster: „go S12-8, S12-9, S12-12 und H1“ (05:55Z) · „Merge #61; S12-8 A; [H1] OK zur Reihenfolge 1–7“ (06:29Z) · „H1 A; [S12-9] Tag v0.16.4 setzen“ (07:07Z) · „H1-6 go; H1-7 go; DMS-29 go“ (08:03Z).

Geliefert: schreib-hub#92/#93/#94, iil-assist-core#61/#62 (Tags v0.16.4, v0.16.5), iil-doc-templates#37 (Tag v0.11.2), meiki-hub#587/#588, meiki-dms#28/#30/#31, post-hub#108/#109, buerger-hub#13, frist-hub#231/#234, shared-ci#108. Sammel-Issue [meiki-hub#582](https://github.com/meiki-lra/meiki-hub/issues/582) offen. CI auf `main` nach den Merges in allen neun Ziel-Repos grün, Publish-Läufe v0.16.4/v0.16.5 grün (3b).

## 0.0 Wirkungsbilanz

`gate_wirkung.py` meldet drei Gates `RUECKFAELLIG`. Alle drei sind schon mit Beschluss verbucht:

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| built-but-never-called | 3 | Quelle | ausweiten — Beschluss 0405d4 („187 go“), in dieser Sitzung kein neuer Fall |
| claim-before-cheapest-check | 3 | Quelle | ausweiten — Beschluss 728cf0-incr (platform#2666). Im Fenster zweimal als Stop-Hook gefeuert und befolgt (gates_caught); neuer Fall #17 in einem PR-Text, den der Hook nicht liest — fällt unter dieselbe Ausweitung, kein zweites Gate |
| worktree-midsession-accumulation | 2 | Ausgang | herabstufen — Beschluss 4f385c-incr2 M6; Befund #1 liegt außerhalb seines Zuschnitts |

Infra-Sonde: einzige CI-Änderung ist der neue Workflow `haus-literale.yml` (`runs-on: ubuntu-latest`) — ohne Befund.

## 1. Executive Summary

- **Ziel weitgehend erreicht:** S12-8/9/12 gemergt und getaggt; H1 Schritte 1–7 nach Owner-Reihenfolge, Gate läuft als Pilot in meiki-hub (Bestand 144 in 22 Dateien), Ausweitung bewusst gestuft. CI und Publish grün.
- **Schwerster Befund (#1, over_act):** Eine Aufräum-Schleife beendete Worktrees von fünf fremden Sitzungen, eine davon aktiv. Schaden null, Verfahren falsch: Auswahl nach Pfad + PR gemergt + sauber, ohne Lease-Zugehörigkeit.
- **Owner-Frage nie vorgelegt (#3):** iil-doc-templates#37 weicht von Owner-Entscheid A ab und bat „vor dem Merge sagen“; das Board führte nur „Merge #37, dann Tag“. Ende-zu-Ende-Probe für schreib-hub#86 fehlt.
- **Hausregeln gebrochen:** ≥32 Edits ohne Read (#4), 49 rohe pytest-Läufe in Worktrees statt `make test` (#18), ungeprüfte Pin-Aussage im PR-Text (#17).
- **Widerlegt:** ADR-044-Verstoß, Image-Lücke in drei Schwesterrepos, H1-Zielverfehlen, Nachzug-Mangel #588 (Skeptiker) und der vermeintliche Closes-Gate-Rückfall (3b).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Aufräum-Schleife 08:55:01Z beendete Worktrees fremder Sitzungen: dev-hub #492/#494 (Sitzung 34d00dac, seit 06:20Z ruhend), platform #3842/#3844/#3846/#3857 (#3857-Sitzung 30ca77c3 aktiv), #3849 ohne Lease-Zuordnung. Kein Schaden (gemergt, sauber, lokale Branches da); `worktree-reaper.py` hätte aktive Leases unter 12 h Karenz liegen lassen | Werkzeug | mittel | SURVIVES | Lease-JSONs `~/.repo-session/leases/` (Feld `claude_session`); `tools/worktree-reaper.py` ~318–370; Befehlsbeleg 08:55:01Z | neu `fremde-worktrees-beendet`; gates_verwandt worktree-midsession-accumulation: Gate zielt auf Ansammlung eigener Worktrees, hier die Gegenrichtung (fremde beendet) |
| 2 | Ausgelassenes aus H1 (Gate in 6 Repos, Kern-Schritte dto/registry/mandant/dvelop/seed_feiertage, post-hub-Literale, meiki-hub-Skripte, Bestandsabbau, Owner-Frage Kern-Startbestand) nur im Sammelkommentar von #582, ohne Link je Posten; eigene Issues nur frist-hub#232/#233, meiki-dms#29 | Prozesslücke | mittel | SURVIVES | [meiki-hub#582](https://github.com/meiki-lra/meiki-hub/issues/582) Kommentar „Bewusst ausgelassen“; `gh issue list --search` je Repo ab 07.10. | `deferred-item-no-tracking-issue` ×60 (Gate declined) |
| 3 | iil-doc-templates#37 weicht von Owner-Entscheid A in schreib-hub#86 ab (gequotete Aufforderung wird Name, 39 Felder) und bat „vor dem Merge sagen“. Das Board führte S12-8 um 06:51, 07:06 und 07:48Z nur als „Merge #37, dann Tag v0.11.2“; die Abweichung erschien in keinem Sitzungstext. Merge 08:05Z durch Owner-Konto, nicht über das Skript (Betreff weicht ab); Ende-zu-Ende-Probe (Ausfüllhilfe mit FILLIN-Hausvorlage) fehlt, #86 offen | Kommunikation | mittel | SURVIVES | [iil-doc-templates#37](https://github.com/iilgmbh/iil-doc-templates/pull/37) (73d7839); [schreib-hub#86](https://github.com/meiki-lra/schreib-hub/issues/86); Transkript 06:35–08:10Z | neu `abweichung-im-pr-text-nicht-aufs-board` |
| 4 | Edit ohne vorheriges Read: 32 von 58 Fehlerläufen „File has not been read yet“, Triplets nach Kompaktierung (03:29, 03:32, 03:36, 03:40Z schreib-hub; 06:07Z iil-assist-core; 06:35Z iil-doc-templates) | Werkzeug | mittel | SURVIVES (kommandobelegt) | `retro_transkript_kennzahlen.py --von 2026-10-07T21:59Z` (Fehlerläufe); `grep -c` = 32 | `edit-in-worktree-without-read` ×8, `edit-after-compaction-without-reread` ×5 — GATE-PFLICHT ohne Gate |
| 5 | Scope-Checkpoint durabel, aber spät: einziger Checkpoint Kommentar 6055850027 in #582 um 08:24:57Z, 2 h 15 min nach drittem Repo (iil-assist-core#61, 06:09Z) | Prozesslücke | niedrig | SURVIVES | `gh api repos/meiki-lra/meiki-hub/issues/582/comments` (created_at) | neu `scope-checkpoint-spaet`; gates_verwandt scope-checkpoint-not-durably-recorded: Gate prüft Existenz, nicht Zeitpunkt — Checkpoint existiert |
| 6 | „Closes-Gate rückfällig: #61 schließt #60, obwohl post-hub/buerger-hub nicht abgedeckt“ | fehlende Validierung | niedrig | REFUTED (3b) | post-hub `origin/main:requirements.txt:25` `kommunalassist-core>=0.16.1,<0.17` seit #104 (06.10.); buerger-hub ohne `.html`/`.css` — K3 war erfüllt, Gate schwieg zu Recht | gates_verwandt issue-offen-nach-gemergtem-fix: kein Rückfall, der Fall war kein Ausstehendes |
| 7 | Gate haus-literale in meiki-hub bindet `iilgmbh/shared-ci/.github/actions/haus-literale@main` ungepinnt ein; shared-ci-README Z. 7 „Konsumenten pinnen auf einen Tag, NICHT @main“; nach #108 kein shared-ci-Tag | Konvention | niedrig | SURVIVES | meiki-hub `origin/main:.github/workflows/haus-literale.yml:21`; shared-ci `origin/main:README.md:7` | neu `shared-ci-action-ungepinnt` (silent-failure-lint.yml:24 schon vorher @main) |
| 8 | Owner-Kürzel S12-8/S12-9/S12-12/H1-6d in keinem Issue/PR mit ihrem Artefakt verknüpft; GitHub-Leser kann „go S12-8 …“ keinem Objekt zuordnen | Kommunikation | niedrig | SURVIVES | `gh search issues/prs` in meiki-lra, iilgmbh: 0 Treffer; einzig `~/shared/merge-schreib-hub-94.sh:2` | neu `owner-kuerzel-ohne-artefakt-bezug` |
| 9 | Zweimal nacktes `git stash -q && … ; git stash pop -q` für Vorher-Nachher-Vergleich (06:07Z iil-assist-core, 06:47Z meiki-dms); Hook `block_bare_stash_pop.py` griff beide Male richtig — gemeinsames `refs/stash` bei parallelen Sitzungen | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Kennzahlen-Datei Fehlerläufe 06:07:12Z, 06:47:03Z | `hook-block-wiederholt-gleiches-muster` ×3, bewusst ohne Gate (declined); gates_caught parallel-subagents-shared-scratch-state |
| 10 | H1-Ziel „Regel gilt im ganzen System“ verfehlt, Gate nur in meiki-hub, Musterlücke | Soll-Ist | hoch | REFUTED | Zielzustand „Ein CI-Gate“; Ausweitung je Repo im Scope-Checkpoint und #588 benannt; Musterlücke in shared-ci#108 „Bewusst nicht“ | — |
| 11 | Kern #62 legt Feiertage/Registry als Package-Data ab, widerspricht ADR-044 P6 | verfrühte Festlegung | mittel | REFUTED | meiki-hub `docs/adr/ADR-044-…md:97` nennt Verfahren/Quellsystem/Feiertagskalender als Kern-Registry mit Startbestand; P6 zielt auf Hausbezeichnung, Fristwert, Vorlage | — |
| 12 | meiki-dms#30 ohne Image-Smoke gemergt, Lehre nicht auf post-hub/buerger-hub/frist-hub übertragen | fehlende Validierung | mittel | REFUTED | #30 nannte die Lücke offen; die drei Schwestern `COPY --chown=app:app . .`, `.dockerignore` schließt nur `docs/`/`tests/` aus, `docs/contracts` nur in Docstrings | — |
| 13 | Nachzug meiki-hub#588 nach shared-ci#108 nicht im Merge-Skript | Prozesslücke | niedrig | REFUTED | Reihenfolge im #582-Kommentar 08:24:07Z und #588-Abschnitt „Nachtrag“ angekündigt; #108 08:39:59Z vor #588 09:05:02Z | — |
| 14 | CMIS-Testzugang in der Historie | Sicherheit | Hinweis | REFUTED (pre) | Finder selbst: kein Secret, kein Handlungsbedarf | — |
| 15 | Konflikt K1: „Tag v0.16.4 setzte der Owner“ | Fakt | — | REFUTED | Befehlsbeleg 07:07:18Z `git tag v0.16.4 310e65e && git push` durch die Sitzung, 11 s nach Owner-Wort „Tag v0.16.4 setzen“ — gedeckt | — |
| 16 | Konflikt K2: „Bestand ≥ 175 Treffer“ | Fakt | — | REFUTED | awk-Summe `origin/main:.github/haus-literale-bestand.yml` = 144 in 22 Dateien (Sammelkommentar #582 nennt 145) | — |
| 17 | PR-Text iil-assist-core#61 „Release-Folgen“ nennt post-hub `<0.15`; tatsächlich `>=0.16.1,<0.17` seit 06.10. — geschrieben ohne die Abhängigkeitsdatei des Konsumenten zu lesen | fehlende Validierung | niedrig | SURVIVES (3b NEU) | [iil-assist-core#61](https://github.com/iilgmbh/iil-assist-core/pull/61) PR-Text Z. 45; post-hub `origin/main:requirements.txt:25` | `claim-before-cheapest-check` (Ausweitung #2666) |
| 18 | 51 rohe `pytest`-Aufrufe im Fenster, 49 davon in Repo-Worktrees, obwohl `make test ARGS=…` nachweislich genutzt wurde — Hausregel „make test, nie rohes pytest“ | Konvention | niedrig | SURVIVES (3b NEU) | Transkript-Auswertung Bash-`tool_use` 2026-10-07T21:59Z–08T09:14Z (Muster `pytest` ohne `make test`) | `rohes-pytest-statt-make-test` ×2 — GATE-PFLICHT |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 3 | #3 — S12-8 ohne Ende-zu-Ende-Beleg; H1 gestuft erreicht (#10 widerlegt) |
| architektur_design | 4 | #11 widerlegt; Datendatei-Ansatz trägt; kleiner Mangel #7 |
| code_konventionstreue | 3 | #18 und #7 — zwei Konventionen verletzt |
| risiko_debt | 3 | #2 — acht Posten ohne eigenes Objekt |
| prozess_effizienz | 3 | #4 — 32 Fehlerläufe Edit ohne Read |
| entscheidungsqualitaet | 3 | #1 — fremde Worktrees ohne Zugehörigkeitsprüfung beendet |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Schleife über `*/2026-10-08-achim-dehnert-*`, Kriterium PR MERGED + sauber | `repo-session.sh end` nur für Leases mit `claude_session` == eigene Sitzung; Rest über `reap`, das Karenz und aktive Leases achtet | #1 |
| Ausgelassenes als Sammelkommentar in #582 | je Posten ein Issue im Ziel-Repo, Sammelkommentar verlinkt nur | #2 |
| #37 bat „vor dem Merge sagen“, Board zeigte nur „Merge #37“ | jede „vor dem Merge sagen“-Frage aus dem eigenen PR-Text als eigenes 🟢-Item mit Kürzel aufs Board | #3 |
| Edit nach Kompaktierung ohne Read, Triplets | nach jeder Kompaktierung vor dem ersten Edit je Datei ein Read; Edits je Datei bündeln | #4 |
| Checkpoint 2 h 15 min nach drittem Repo | Checkpoint-Kommentar im Sammel-Issue beim ersten Worktree im dritten Repo | #5 |
| Action `@main` | shared-ci nach #108 taggen, Konsument pinnt den Tag | #7 |
| Kürzel nur im Chat | Kürzel in PR-Titel/-Body bzw. Issue-Kommentar schreiben, wenn der Owner es vergibt | #8 |
| zweimal nacktes `stash`/`stash pop` | Vorher-Nachher-Vergleich in einem zweiten Worktree auf `origin/main` statt über `refs/stash` | #9 |
| Pin-Stand der Konsumenten aus dem Gedächtnis | vor „Release-Folgen“ je Konsument `git show origin/main:requirements.txt \| grep <paket>` | #17 |
| `.venv/bin/python -m pytest …` im Worktree | `make test ARGS="<pfad> -k …"` auch für gezielte Läufe | #18 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (2026-10-08, vor diesem Report): 65 Slugs ≥2. In dieser Retro wieder: `deferred-item-no-tracking-issue` ×59, `edit-in-worktree-without-read` ×7, `edit-after-compaction-without-reread` ×4 — alle GATE-PFLICHT; `hook-block-wiederholt-gleiches-muster` ×2 — bewusst ohne Gate (Owner-Entscheid, `retro_kpis.py`), Wiederkehr ändert daran nichts, der Hook griff; `rohes-pytest-statt-make-test` ×1 → mit diesem Report ×2, GATE-PFLICHT. MEMORY.md (`grep`): zu fremden Worktrees, rohem pytest und Konsumenten-Pins kein Eintrag.

### 5a. Rückfall-Prüfung

- **Kein neuer Gate-Rückfall.** Der im Entwurf gemeldete Rückfall von `issue-offen-nach-gemergtem-fix` ist von 3b gekippt (#6): Das Gate schwieg zu Recht.
- `claim-before-cheapest-check`: Fall #17 liegt in einem PR-Text, den der Stop-Hook nicht liest. Er gehört zur schon beschlossenen Ausweitung (platform#2666), kein zweites Gate.
- `edit-in-worktree-without-read`, `edit-after-compaction-without-reread`, `rohes-pytest-statt-make-test`: kein Gate, GATE-PFLICHT ⇒ Gate-Kandidaten.
- `deferred-item-no-tracking-issue`: Gate `declined`; Wiederkehr ×60 ⇒ Entscheidung „declined“ dem Owner zur Überprüfung vorlegen.
- `worktree-midsession-accumulation`, `scope-checkpoint-not-durably-recorded`: gates_verwandt, Begründung §2 #1/#5.

### 5b. Autonomie-Kalibrierung

- **over_act** `fremde-worktrees-beendet` (#1): Eingriff in fremden Arbeitsbereich ohne Owner-Wort; reversibel, aber außerhalb des eigenen Scopes.
- **over_ask**: keine Klasse. Tag v0.16.4 war ausdrücklich angewiesen (#15), Tags v0.16.5/v0.11.2 setzte der Owner selbst.

## 6. Verankerung (Vorschläge, nicht geschrieben)

**memory_candidates**

```markdown
---
name: fremde-worktrees-nie-beenden
description: repo-session end nur auf Leases der eigenen Sitzung; Schleifen über Pfadmuster treffen fremde Sitzungen
metadata:
  type: feedback
drift: true
drift_episode: 2026-10-08-fremde-worktrees
---
Eine Schleife über `~/.repo-session/worktrees/*/<datum>-<owner>-*` mit Kriterium „PR MERGED + sauber“
beendete am 2026-10-08 Worktrees von fünf fremden Sitzungen, eine davon aktiv.
**Why:** Pfadmuster tragen Datum und Owner, nicht die Sitzung; dieselbe Person fährt parallele Sitzungen.
**How to apply:** vor `end` das Lease-Feld `claude_session` mit der eigenen Sitzung vergleichen; sonst `reap` (achtet Karenz). [[kd-testserver-port-hygiene]]
```

```markdown
---
name: pr-frage-vor-merge-aufs-board
description: „Bitte vor dem Merge sagen“ im eigenen PR-Text ist ein Board-Item, kein PR-Detail
metadata:
  type: feedback
---
iil-doc-templates#37 wich von Owner-Entscheid A ab und fragte im PR-Text; das Board zeigte nur „Merge #37“.
**Why:** Der Owner liest das Board, nicht jeden PR-Text; die Frage kam nie an.
**How to apply:** jede offene Frage aus eigenem PR-Text als 🟢-Item mit Kürzel aufs Board, Merge-Skript erst danach. [[advocatus-vor-owner-go]]
```

**adr_candidates:** keine. **Gate-Kandidaten** (Gate-PR, kein ADR): `fremde-worktrees-beendet` (Prüfung in `repo-session.sh end`), `edit-in-worktree-without-read` (PreToolUse-Hinweis nach Kompaktierung), `rohes-pytest-statt-make-test` (PreToolUse-Hinweis auf `pytest` in Repo-Worktrees mit Makefile-Ziel `test`), `shared-ci-action-ungepinnt` (Workflow-Lint `uses: iilgmbh/shared-ci/…@main`).

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | `end` nur eigene Sitzung | platform | — | 🟢 | Owner-Go, dann Gate-PR `repo-session.sh` |
| M2 | Ausgelassenes als Issues | meiki-hub u. a. | meiki-hub#582 | 🔵 | je Posten Issue, Kommentar verlinken |
| M3 | #37-Abweichung entscheiden | iil-doc-templates | schreib-hub#86 | 🟢 | Owner: Abweichung annehmen oder Rückbau |
| M4 | Action auf Tag pinnen | meiki-hub | meiki-hub#588 | 🔵 | shared-ci-Tag (Owner), dann Pin-PR |
| M5 | PR-Text #61 berichtigen | iil-assist-core | iil-assist-core#61 | 🔵 | Korrektur-Kommentar post-hub-Pin |
| M6 | Gate rohes pytest | platform | — | 🟢 | Owner-Go, dann Gate-PR |
| M7 | declined-Gate prüfen | platform | — | 🟢 | Owner: deferred-item weiter declined? |

## 8. Nicht verifiziert (Restlücken)

- Ob die Leases der fremden Sitzungen vor 08:55Z schon geschlossen waren (Rename ändert mtime nicht). Billigster Check: Transkripte 34d00dac/30ca77c3 nach `repo-session.sh end` vor 08:55Z durchsuchen.
- Remote-Branches der platform-PRs nach dem Beenden nicht per `ls-remote` geprüft (dev-hub: 0 Treffer, erwartbar nach Merge).
- Wer #37 um 08:05Z ausgelöst hat: Owner-Konto, nicht über das Skript, kein Agenten-Befehl im Transkript 07:50–08:15Z (Hypothese: Owner in eigenem Werkzeug).
- Laufende Hook-Kopie `scope_checkpoint_scanner.py` weicht von der platform-Quelle ab (Hygiene-Melder) — Einfluss auf #5 nicht geprüft.
- #18: Ein Teil der rohen pytest-Läufe kann ein Vorher-Nachher-Vergleich gewesen sein, den `make test` nicht abbildet; Einzelprüfung nicht gemacht.
- #5 und #8 hat 3b nur plausibilisiert, nicht nachgezogen.

## Widerlegung

Phase 3b (Opus, frischer Kontext; sah Entwurf, Footprint, Artefaktliste, Belegdateien):

| Befund | Ergebnis | Verdikt |
|---|---|---|
| #1 | hält; präzisiert: 34d00dac seit 06:20Z ruhend, nur 30ca77c3 aktiv | BESTAETIGT |
| #2, #4, #7 | hält, nachgezogen | BESTAETIGT |
| #3 | hält, Beleg verschärft: Abweichung nie auf dem Board, Merge nicht über Skript | BESTAETIGT |
| #5, #8 | hält, nur plausibilisiert | BESTAETIGT |
| #6 | widerlegt: post-hub pinnt `<0.17`, buerger-hub ohne Oberfläche — K3 erfüllt, Gate schwieg zu Recht | GEKIPPT |
| #9 | hält, umklassiert: Hook griff richtig (gates_caught) | BESTAETIGT |
| #10–#16 | Widerlegungen halten | BESTAETIGT |
| #17 | ungeprüfte Pin-Aussage im PR-Text #61 | NEU |
| #18 | rohes pytest in Worktrees | NEU |

Eigene Nachprüfung der tragenden 3b-Aussagen: post-hub `requirements.txt:25` (`>=0.16.1,<0.17`, Commit 2d01dea #104), buerger-hub 0 `.html`/`.css`-Dateien, 51/49 rohe pytest-Aufrufe. 3b nannte `rohes-pytest-statt-make-test` „zweimal“ im Längsschnitt — `retro_kpis.py` zählt ×1, im Report korrigiert.

## Phase 6 — Extern-Handoff

Begründet n/a: optional bei `deep`; drei frühere Briefings (2a5c44, eff9b5, 8a0235) liegen ohne Rückweg in `~/shared/`, ein viertes vergrößert nur den offenen Stapel. Kein Urteil über Leser.

## Streichbahn

Keiner, weil jede Phase Wirkung zeigte: Phase 3 kippte 6 von 13 Bewertungsbefunden, 2.5 klärte zwei Fakt-Widersprüche (#15, #16), 3b kippte einen Befund samt falschem Gate-Rückfall und fand zwei neue, 0.0 ordnete drei Rückfälle bestehenden Beschlüssen zu. Ratsche: Der Kandidat der Vorretro (`inline-heredoc-quoting-rework`) ist mit platform#3841 (R8) gestrichen.

## Self-Review

Meta-Agent (Phase 5, Sonnet) prüfte den Entwurf gegen die Skill-Regeln: Belege #3, #5, #7, #16, #17 unabhängig bestätigt (#1/#18 für ihn nicht einsehbar, von 3b und mir nachgezogen); Längsschnitt-Zähler, Scores, Invariante (10 = 10), Pfad und 0.0-Behandlung OK; `refuted_rate` 0.39 mitten im gesunden Band. Behoben: #17 Zeilenangabe (Z. 45 statt 46), #9/§5 `hook-block-wiederholt-gleiches-muster` ist bewusst ohne Gate, nicht GATE-PFLICHT.

Zählweise `refuted_rate`: `phase3_refuted` 6 = #10, #11, #12, #13, #15, #16 (die drei Skeptiker prüften 13 Bewertungsbefunde einschließlich der zwei Konflikt-Tasks); `pre_refuted` 1 = #14. #6 kippte erst in 3b und zählt wie in der Vorretro 213b56-incr nicht in die Rate (7/18 = 0.39). `retro_report_check.py`: Exit 0.

**getan:** drei Finder, drei Skeptiker inklusive zwei Konflikt-Tasks, 3b-Widerlegung, eigene Nachprüfung jeder 3b-Kernaussage, Längsschnitt und Wirkungsbilanz. · **angenommen:** Sitzungszugehörigkeit über das Lease-Feld `claude_session`; Kennzahlen-Datei vollständig. · **nicht verifizierbar:** wer #37 auslöste; Lease-Zustand fremder Sitzungen vor 08:55Z. · **offen geblieben:** M1–M7, Owner-Frage Kern-Startbestand und H1-6d (frist-hub#233).
