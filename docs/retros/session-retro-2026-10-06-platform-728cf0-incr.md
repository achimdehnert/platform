---
retro_schema: 1
date: 2026-10-06
repo_scope: [platform, shared-ci]
session_id: 728cf0-incr
footprint: full
findings_total: 13
findings_survived: 6
refuted_rate: 0.54
phase3_refuted: 6
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 4
  entscheidungsqualitaet: 3
gate_candidates: [dry-run-does-not-cover-write-path]
recurring_findings: [edit-in-worktree-without-read, tracking-doc-stale-after-new-occurrence, dry-run-does-not-cover-write-path]
gates_caught: [claim-before-cheapest-check]
gates_verwandt: [tracking-doc-stale-after-new-occurrence]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "1 gekippt, 2 neu"
streichkandidaten: []
streich_begruendung: "keiner, weil jede gelaufene Phase hier Wirkung hatte: die Skeptiker verwarfen fünf von sieben Bewertungsbefunden, die Widerlegungsbahn kippte #2 und fand #12 und #13, die Kennzahlen trugen #9"
---

# Session-Retro 2026-10-06 (Sitzung 728cf098, Inkrement)

Inkrement zur Eltern-Retro [`session-retro-2026-10-05-platform-728cf0.md`](session-retro-2026-10-05-platform-728cf0.md) (Commit `730e9715`, 2026-10-05T17:43:09Z). In Scope ist nur, was danach entstand; die Eltern-Retro wird nicht neu verhandelt. Fenster: 2026-10-05T17:43Z bis 2026-10-06T10:35Z.

Scope über die Nummern der Sitzung, nicht über das Datum:

- **platform:** PRs #3783, #3793, #3794, #3798 (V1 bis V2b der Kontext-Diät), Issues #3785 und #2234 (Owner-Wort M6), Fragmente `docs/handover.d/*728cf098*`.
- **shared-ci:** PRs #92 (Dependabot, von der App gemergt), #99 und #101 (Owner-Merge), Issues #96 und #100 (geschlossen), Runs 37425530577, 37437247675 und 37438633182, Tag `v1.1.24` (vom Owner gesetzt), Secret `AUTO_RELEASE_APP_ID` gelöscht, Variable `AUTO_RELEASE_CLIENT_ID` (vom Owner angelegt).

**Footprint `full`:** zwei Repos, kein Prod-Schritt, keine Migration, kein ADR. Tag, Secret und Variable setzte der Owner. Agentenbudget: 3 Finder, 2 Skeptiker, 1 Widerlegung, 1 Meta, zusammen 7 und damit eins über der Obergrenze ≤6 für `full` mit 3b und Meta (Phase 5); die Skeptiker sind nach Dimensionen gebündelt (Soll-Ist mit Entscheidungen, Prozess), weil sieben Bewertungsbefunde vorlagen. Transkript-Kennzahlen ab 17:43:09Z (`retro_transkript_kennzahlen.py`): 0 Ablehnungen, 15 Fehlerläufe, 17 Silent-Reminder.

## 0.0 Wirkungsbilanz

`python3 tools/gate_wirkung.py` lief als erster Schritt und meldet drei Gates als RUECKFAELLIG, alle mit letztem Rückfall 2026-10-05 vor diesem Fenster. Die Eltern-Retro hat für alle drei eine Konsequenz entschieden; dieses Inkrement übernimmt sie und stellt keine zweite daneben.

| Gate | Rückfälle seit Bau | Ursache (Ausgang/Quelle) | Konsequenz |
|---|---|---|---|
| handover-stale-vor-merge | 4 | Quelle: E.3 zählt nur PRs nach dem Fragment und liest „Offen“ nicht | **nachschärfen** nach Vorlage G2 (`docs/governance/gates/vorschlag-rueckfaellige-gates-2026-10-05.md`), Eltern-Entscheid; im Inkrement kein Vorkommen: #3798 mit dem Fragment wurde 08:32:31Z gemergt, vor #92 (08:36:44Z), #2 ist widerlegt |
| claim-before-cheapest-check | 3 | Quelle: Hook sieht keine Prognosen und keine PR-Texte | **nachschärfen** am bestehenden Eintrag ([#2666](https://github.com/achimdehnert/platform/issues/2666)), Eltern-Entscheid; im Inkrement hat das Gate zweimal gefangen (#10), kein neuer Rückfall |
| worktree-midsession-accumulation | 2 | Ausgang: Melder zählt aktive Leases vom selben Tag als Stau | **herabstufen**, Eltern-Entscheid (Retro `4f385c-incr2` M6); im Inkrement kein Vorkommen |

## 1. Executive Summary

- Das Ziel M5b ist erreicht: Die Automatik mergt Action-Bumps mit dem App-Token (Run 37437247675, #92), die Umstellung auf `client-id` ist gemergt (#101), das alte Secret ist gelöscht.
- Den Auto-Tag-Pfad hat noch kein Lauf gezeigt. #101 liegt nach `v1.1.24` auf main und ist keine Versionszeile; bis zu einem Hand-Tag meldet die Automatik „Release bleibt Mensch“. Der Abschluss von #96 sagt das nicht, obwohl dieselbe Sperre fünf Minuten vorher sichtbar gegriffen hatte (#3).
- Die Prognose, der erste scharfe Lauf setze `v1.1.24` selbst, stützte sich nur auf Trockenläufe. Die Lehre steht seit 2026-07-28 als Drift-Memory und wird von `retro_kpis.py` nicht gezählt, weil sie nie als `recurring_findings` geführt wurde (#4, #13).
- Der Retro-Entwurf schlug für Edit ohne Read (#9) einen Verzicht vor, den der Owner mit „M6 ja“ schon verworfen hatte; die Widerlegungsbahn fing das (#12).
- Sieben von dreizehn Befunden fielen, darunter das Sicherheitsrisiko im `pull_request`-Job (#6) und die vermeintlich alten Skill-Kopien (#1).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Startlast nur im Repo gesenkt, verteilte Kopien unter `~/.claude/commands/` und `hooks/managed/` alt | Prozesslücke | mittel | REFUTED | `tools/session_start_checks.sh` Phase 0.7.13 verteilt die Lanes `skills commands hooks` bei Drift neu (`generate.py --ref origin/main --allow-live`); beobachtet einmal: `manifest.json` `source_commit` 35db40d1, Dateien 05:29Z ohne `generate.py` in dieser Sitzung | – |
| 2 | Letztes Fragment `2026-10-06T08-24-16Z-728cf098` führt M5b als offen, ein Abschlussfragment fehlt | Kommunikation | niedrig | REFUTED (3b) | `docs/handover.d/README.md` verlangt eine Datei je Sitzung, keinen Zwischenstand je Faden; Sitzung läuft noch, Fragment fällig mit `/session-ende` (Maßnahme Z4) | – |
| 3 | #101 legt Nicht-Versionszeilen zwischen `v1.1.24` und main; der Auto-Tag ist bis zu einem Hand-Tag gesperrt, der Abschluss von #96 nennt das nicht | Kommunikation | mittel | SURVIVES | `gh api repos/iilgmbh/shared-ci/compare/v1.1.24...main` → ahead 2 (`dfcda8c7`, `2cc338c0`), nur `.github/workflows/auto-release.yml`; `tools/auto_release.py` Z. 292 „Release bleibt Mensch“; #96 08:37:34Z „Tag bleibt beim Menschen (gewollt)“, 08:42:41Z „Ab v1.1.24 taggt sie auch selbst, solange …“ | tracking-doc-stale-after-new-occurrence |
| 4 | Prognose „Cron setzt v1.1.24 selbst“ war vorhersehbar falsch, gestützt nur auf Trockenläufe | fehlende Validierung | mittel | SURVIVES | #96 Kommentare 2026-10-05T17:45:15Z und 18:05:59Z (dieser mit „(Prognose)“); Run 37425530577 rot mit HTTP 403 „without `workflows` permission“; `GITHUB_TOKEN` bekommt nie `workflows` | dry-run-does-not-cover-write-path |
| 5 | Trockenlauf kann das Schreibrecht nicht zeigen | fehlende Validierung | niedrig | REFUTED (pre) | Lücke ist im Workflow-Kommentar benannt („Das Schreibrecht zeigt erst der scharfe Lauf“), der scharfe Lauf 37437247675 schloss sie | – |
| 6 | Job `trocken` nutzt `AUTO_RELEASE_APP_KEY` auf `pull_request`, Rechtezuwachs am Review vorbei | Werkzeug | mittel | REFUTED | `collaborators`: nur zwei Admins; Org `default_repository_permission: read`, keine Teams; main ohne Branch-Protection (404), Ruleset nur `deletion`/`non_fast_forward`; Admins können ohnehin direkt pushen. Rest: Härtung per Environment | – |
| 7 | LEHREN-Kopf `retro.md` sagt „wörtlich … Nichts wurde gelöscht“, #3798 räumt Umformulierungen ein; Test-Docstring nennt noch „E.0 bis E.9“ | Konvention | niedrig | SURVIVES | `docs/governance/session-skills-lehren/retro.md` Z. 7–9; Body #3798 Z. 24 („einige Passagen umformuliert … alter Wortlaut bei `35db40d1`“); `tools/tests/test_session_ende_checks.py:11` | – |
| 8 | #101 vor der Owner-Vorbedingung (Variable) geöffnet, erster Trockenlauf rot | Prozesslücke | mittel | REFUTED | Reihenfolge um 08:48:16Z angekündigt, Rerun im selben Owner-Einzeiler wie die Variable (08:51:43Z), Attempt 1 rot nur für den eigenen PR, Merge erst 10:27:47Z | – |
| 9 | Achtmal Edit ohne vorheriges Read im Worktree | Werkzeug | niedrig | SURVIVES | Transkript 2026-10-05T18:30:41–53Z (fünf Gate-Dateien), 19:53:52–56Z (dreimal `handover_prio_mirror.sh`); in den 15 Fehlerläufen der Kennzahlen | edit-in-worktree-without-read |
| 10 | Hook „Unbelegte Bescheinigung“ blockierte zweimal Freigabe-Kommentare, Prozesslücke ohne Schablone | Prozesslücke | niedrig | REFUTED | Beide Blocks berechtigt (unbelegtes „geprüft“, „freigegeben“ ohne Beleg), Nachbesserung nach 7 s bzw. 4 s; Gate hat gefangen | claim-before-cheapest-check (gefangen) |
| 11 | Mindestens 6 Owner-Handgriffe, 2 vermeidbar, trotz „weiter MAXIMAL AUTONOM“ | Kommunikation | mittel | REFUTED | Rerun steckte im Variable-Einzeiler; Secrets 07:20Z, Merge #99 07:59:17Z, Tag 08:42Z lagen vor der Anweisung 08:48:05Z; Secret, Variable, Tag sind Security-Config bzw. Publish | – |
| 12 | Retro-Entwurf empfahl `declined` für `edit-in-worktree-without-read`, obwohl der Owner den Bau mit „M6 ja“ beschlossen hatte | Kommunikation | mittel | SURVIVES (3b) | [#2234 Kommentar 2026-10-05T17:54:20Z](https://github.com/achimdehnert/platform/issues/2234#issuecomment-6000046771): „M6 (Retro 728cf0): Das Gate `edit-in-worktree-without-read` … wird gebaut“; kein Widerruf danach | – |
| 13 | `dry-run-does-not-cover-write-path` ist in vier Retros als verwandt erwähnt, aber nie in `recurring_findings` geführt; `retro_kpis.py` zählt den Slug deshalb nicht | Werkzeug | mittel | SURVIVES (3b) | `git grep` auf origin/main: Retros 287b23, 36c670, 8ed6a2, ec0588a8 verweisen auf das Drift-Memory `feedback_dry_run_does_not_cover_write_path` (den Slug selbst nennt nur 287b23); `retro_kpis.py` gibt den Slug nicht aus | – |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 4 | M5b erreicht, Auto-Tag-Pfad unbewiesen (#3) |
| architektur_design | 4 | App-Token mit Client-ID als Variable; Sicherheitsbefund widerlegt (#6) |
| code_konventionstreue | 4 | veralteter Docstring und LEHREN-Kopf (#7) |
| risiko_debt | 3 | Auto-Tag bis zum Hand-Tag gesperrt, nirgends vermerkt (#3) |
| prozess_effizienz | 4 | acht Edit-ohne-Read-Fehlerläufe, je ein Retry (#9) |
| entscheidungsqualitaet | 3 | Prognose ohne Prüfung des Schreibpfads (#4); Empfehlung gegen ein Owner-Wort (#12) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| #101 nach `v1.1.24` gemergt, #96 verspricht weiter den Auto-Tag | Vor dem Merge eines Folge-PRs gegen die Release-Regel prüfen (`compare <tag>...main`) und im Ursprungs-Issue den neuen Zustand mit nächstem Schritt nennen | #3 |
| Prognose zum Auto-Tag nur aus Trockenläufen | Vor einer Prognose zum Schreibpfad die Rechte des Tokens gegen jede Datei des Ziel-PRs prüfen (`workflows` bei `.github/workflows/`) | #4 |
| E.5 entfernt, Docstring und LEHREN-Kopf nicht angepasst | Beim Streichen einer Phase `git grep` nach ihrer Nummer über Tests und LEHREN im selben PR | #7 |
| Edit auf Worktree-Datei ohne Read, achtmal | Vor dem ersten Edit im Worktree die Zieldateien per Read im Bündel öffnen | #9 |
| Verzicht empfohlen, ohne nach einer Owner-Entscheidung zum Slug zu suchen | Vor jeder Gate-Empfehlung `gh search issues "<slug>"` im Owner-Repo, Treffer mit Owner-Wort übernehmen statt neu entscheiden | #12 |
| Erstfall 2026-07-28 nur als Memory, Folgefälle nur als „verwandt“ erwähnt | Wiederkehrende Lehre in `recurring_findings` führen, sobald eine Retro sie wiedererkennt | #13 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` lief.

| Slug | Zähler | Gate | Folge |
|---|---|---|---|
| edit-in-worktree-without-read | ×5 mit diesem Inkrement | keines gebaut; Bau beschlossen (Owner-Wort M6, #2234) | GATE-PFLICHT eingelöst durch Beschluss, Bau offen in der Reihenfolge aus #2234 |
| tracking-doc-stale-after-new-occurrence | ×16 mit diesem Inkrement | `gates/aufschub-anker.json` (deckt vier Slugs) | gates_verwandt: das Gate prüft Aufschübe ohne Anker, #3 ist kein Aufschub, sondern ein durch Folge-PR überholter Abschlusskommentar |
| claim-before-cheapest-check | ×103 | `gates/claim-before-cheapest-check.json` | gefangen (#10), Beleg für das Gate |
| dry-run-does-not-cover-write-path | ×1 im Zähler, tatsächlich ≥5 (Erstfall 2026-07-28 plus vier Retros als „verwandt“, #13) | – | GATE-PFLICHT; Drift-Memory seit 2026-07-28 hat #4 nicht verhindert |

Memory-Abgleich per `grep -l -i` im Memory-Verzeichnis: `Trockenl` trifft `feedback_dry_run_does_not_cover_write_path.md` (drift: true); `edit-in-worktree` und „Edit ohne Read“ treffen nichts.

### 5a. Rückfall-Prüfung

| Gate | Fall | Rückfall? |
|---|---|---|
| claim-before-cheapest-check | #10, zwei Blocks mit Nachbesserung | nein, gefangen (`gates_caught`) |
| handover-stale-vor-merge | #2 | nein, #2 widerlegt; Fragment war beim Merge aktuell |
| worktree-midsession-accumulation | – | nein, kein Fall im Inkrement |
| aufschub-anker | #3 | gates_verwandt: Zuschnitt sind Aufschübe ohne Anker, #3 ist ein überholter Abschlusskommentar ohne Aufschub |

### 5b. Autonomie-Kalibrierung

over_ask: keine Klasse. Die Owner-Handgriffe (Secret, Variable, Tag, Merges auf `.github/workflows/`) fallen unter Security-Config, Publish oder Governance-Pfad (#11 widerlegt). over_act: keine Klasse; Merge, Tag und Rerun liefen nur auf Owner-Wort. `retro_kpis.py --nominierung`: kein Klassen-Muster ≥2, das dieses Inkrement berührt.

## 6. Verankerung (Vorschläge, nicht geschrieben)

- memory_candidates: keiner. #4 wiederholt ein bestehendes Drift-Memory, ein zweites Memo änderte nichts; Kandidat ist ein Gate (`dry-run-does-not-cover-write-path`). #9 ist über M6 entschieden.
- adr_candidates: keiner.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| Z1 | #96 um Auto-Tag-Sperre ergänzen (#3) | shared-ci | [#96 Kommentar](https://github.com/iilgmbh/shared-ci/issues/96#issuecomment-6014622728) | ✅ | Issue bleibt geschlossen, Beobachtung beim Cron 2026-10-07 |
| Z2 | Gate Lesen-vor-Edit bauen (#9, #12) | platform | #2234 | 🟢 | beschlossen (M6), Reihenfolge Owner |
| Z3 | Docstring und LEHREN-Kopf nachziehen (#7) | platform | Docstring im Retro-PR #3805, LEHREN-Kopf [#3806](https://github.com/achimdehnert/platform/pull/3806) | 🟢 | #3806 wartet auf Review (Governance-Pfad) |
| Z5 | Gate-Pflicht Trockenlauf-Schreibpfad (#4, #13) | platform | #2234 | 🟢 | Owner: bauen oder declined |

Ledger ohne Befund: Abschlussfragment mit M5b-Stand schreibt `/session-ende` in dieser Sitzung (#2 widerlegt, keine Maßnahme).

## 8. Nicht verifiziert (Restlücken)

- **getan:** 3 Finder, 2 Skeptiker, Widerlegungsbahn, Meta-Agent; `gate_wirkung.py`, `retro_kpis.py` (auch `--nominierung`), `retro_report_check.py`.
- **angenommen:** Die Selbstheilung der Lanes in 0.7.13 zieht die aktuellen Kopien beim nächsten Start nach (#1); einmal beobachtet (05:29Z), welche Sitzung sie auslöste, ist offen.
- **nicht verifizierbar:** ob der Cron am 2026-10-07 wie aus dem Code abgeleitet „Release bleibt Mensch“ meldet (#3).
- **offen geblieben:** Härtung des `trocken`-Jobs per Environment (#6, kein Befund, Option); Zählweise für die Fälle aus #13 in den vier älteren Retros nicht nachgetragen, weil Retros nicht rückwirkend geändert werden.

## Self-Review

Sonnet-Meta-Agent, sah nur Report und Skill. Stichprobe #3, #7, #12, #13 nachgezogen, alle bestätigt. Gemeldet und behoben: 0.0 und 5a führten nur eines von drei RUECKFAELLIG-Gates (jetzt alle drei mit Eltern-Konsequenz); Maßnahme zum widerlegten #2 stand als Z-Item (jetzt Ledger-Zeile); Agentenbudget ohne Skill-Zahl begründet (jetzt ≤6 aus Phase 5); Beleg zu #13 präzisiert (Memory-Link statt Slug). Ohne Mangel: Scores, Invariante 6 Soll-Schritte zu 6 Überlebenden, Frontmatter 13 = 6 + 6 + 1, Pfad kollisionsfrei, `retro_report_check.py` Exit 0, `refuted_rate` 0.54 im gesunden Band 0.2–0.8.

## Widerlegung

Opus-Subagent, frischer Kontext, sah nur Entwurf, Footprint und Artefaktliste.

| # | Verdikt 3b | Beleg |
|---|---|---|
| 1 | BESTAETIGT (REFUTED hält) | `manifest.json` `source_commit` 35db40d1, Heilung 05:29Z beobachtet |
| 2 | GEKIPPT | `docs/handover.d/README.md`: Fragment je Sitzung, nicht je Faden; Sitzung läuft noch |
| 3 | BESTAETIGT, schwerer | #96 08:37:34Z zeigt, dass dieselbe Sperre gerade gegriffen hatte |
| 4 | BESTAETIGT | Workflow-Kopf Z. 18–19 nennt die `workflows`-Grenze selbst |
| 6 | BESTAETIGT (REFUTED hält) | Org-Mitglieder 2, keine Teams, Default-Recht read |
| 7, 9 | BESTAETIGT | wie Tabelle |
| 5, 8, 10, 11 | kein Gegenbeleg | Zeitstempel decken sich mit `mergedAt` |
| 12 | NEU | #2234, Owner-Wort M6 |
| 13 | NEU | vier Retros nennen die Lehre nur „verwandt“ |

## Streichbahn

Keiner, weil jede gelaufene Phase hier Wirkung hatte: die Skeptiker verwarfen fünf von sieben Bewertungsbefunden, die Widerlegungsbahn kippte #2 und fand #12 und #13, die Kennzahlen trugen #9.
