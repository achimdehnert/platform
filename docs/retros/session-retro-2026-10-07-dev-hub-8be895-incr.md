---
retro_schema: 1
date: 2026-10-07
repo_scope: [dev-hub, platform]
session_id: 8be895-incr
footprint: lean
footprint_reduction_reason: "Prod nur lesend befragt (cgroup-Dateien, Logs, Zählungen), kein Prod-Schreibschritt; die einzige Löschung (R1) hat der Owner auf 2026-10-18 vertagt. 1 Code-PR (#486) offen und ungemergt, keine Migration, kein ADR."
findings_total: 5
findings_survived: 5
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 4
  prozess_effizienz: 4
  entscheidungsqualitaet: 4
gate_candidates: []
recurring_findings: [akzeptanzkriterium-ohne-pruefung-der-schreibwege, board-bietet-nicht-faellige-irreversible-aktion-an, board-id-kollidiert-mit-retro-massnahme, frist-widerspruch-ledger-vs-issue, sicherungsinventar-unvollstaendig]
gates_caught: [gh-body-file-leer-ueberschrieben]
gates_verwandt: [scope-checkpoint-not-durably-recorded]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "n/a (lean): 0 gekippt, 0 neu"
streichkandidaten: []
streich_begruendung: "keiner, weil dieses Inkrement nur die Pflichtteile von lean nutzte und jeder davon eine Wirkung hatte: die Wirkungsbilanz bestätigte, dass alle vier rückfälligen Gates schon einen Beschluss haben, und der Längsschnitt zeigte, dass keiner der fünf Slugs schon vorkam"
---

# Session-Retro 2026-10-07 (dev-hub, Sitzung 8be895, Inkrement)

Inkrement zur Retro [`session-retro-2026-10-06-dev-hub-8be895.md`](session-retro-2026-10-06-dev-hub-8be895.md). Owner-Auftrag: „N1 M1 T1 R1 go und dann retro / ende“.

Artefakte dieses Inkrements:

- dev-hub PR [#486](https://github.com/achimdehnert/dev-hub/pull/486): OCR-Speichergrenze mit Kindprozessen, Zeitgrenze für den Nachtlauf. Offen, Gate grün, ungemergt.
- dev-hub [#484 Kommentar 6031757379](https://github.com/achimdehnert/dev-hub/issues/484#issuecomment-6031757379): erster Nachtlauf belegt, Abschnitt 1 abgehakt.
- dev-hub [#426 Kommentar 6031764368](https://github.com/achimdehnert/dev-hub/issues/426#issuecomment-6031764368): Schreibwege geprüft, Entscheidung A/B an den Owner.
- dev-hub [#443 Kommentar 6032975846](https://github.com/achimdehnert/dev-hub/issues/443#issuecomment-6032975846): Bestand gemessen, Löschung auf Owner-Entscheid vertagt.

## 0.0 Wirkungsbilanz

`tools/gate_wirkung.py` lief als erster Schritt und meldet 4 rückfällige Gates. Für alle vier liegt bereits ein Beschluss vor, diese Retro fasst keinen zweiten.

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| handover-stale-vor-merge | 5 | Quelle | **nachschärfen**, Beschluss in Parent `8be895`; in diesem Inkrement kein Handover-Merge |
| built-but-never-called | 3 | Quelle | **ausweiten**, Beschluss Owner-Wort „187 go“ (`0405d4`); hier kein Vorkommen |
| claim-before-cheapest-check | 3 | Quelle | **ausweiten**, Beschluss `728cf0-incr` / [platform#2666](https://github.com/achimdehnert/platform/issues/2666); hier kein Vorkommen |
| worktree-midsession-accumulation | 2 | Ausgang | **herabstufen**, Beschluss `4f385c-incr2` (M6); hier kein Vorkommen, die Worktrees wurden je Aufgabe beendet |

## 1. Executive Summary

- N1 Teil 1 ist belegt. Im Nachtlauf liefen alle drei Konten durch, es gab keinen OOM, und die Absagen „Texterkennung nötig“ stehen auf 0. Teil 2 ist erst ab 2026-10-08 möglich.
- M1 liegt als PR #486 vor. Das Gate ist grün, die Negativkontrolle ist dokumentiert, der Merge braucht das Owner-Wort.
- T1: Das Ziel „nur lesend“ aus #426 hätte drei laufende Funktionen abgeschaltet (#2). Die Entscheidung A/B liegt beim Owner.
- R1: Vor dem Löschen kam der Einwand, der Owner hat auf 2026-10-18 vertagt. Das Board hatte die Löschung als sofort ausführbar angeboten (#3).
- Eigener Fehler: Die Board-ID „M1“ kollidierte mit der Retro-Maßnahme M1 (#1).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Board-ID „M1“ bezeichnete die Retro-Maßnahmen M5/M6, während die Retro selbst ein anderes M1 führt | Kommunikation | niedrig | SURVIVES (inline, kein Skeptiker) | Sitzungstranskript; nur dort belegt, nicht per gh/git nachprüfbar | `board-id-kollidiert-mit-retro-massnahme` ×1 |
| 2 | Das Kriterium „fine-grained, read-only“ in #426 wurde ohne Blick auf die Schreibwege gesetzt; drei laufende Funktionen schreiben (Approve, Release-Tag, Watchdog-Issue) | fehlende Validierung | mittel | SURVIVES (inline, kein Skeptiker) | dev-hub#426 (angelegt 2026-10-02), Kommentar 6031764368; `apps/operations/views.py:274`, `apps/releases/views.py:86`, `apps/repo_health/tasks.py:155` | `akzeptanzkriterium-ohne-pruefung-der-schreibwege` ×1 |
| 3 | Das Board bot die Löschung aus #443 elf Tage vor der Frist als „go“-fähig an; der Einwand kam erst beim Ausführen | Kommunikation | mittel | SURVIVES (inline, kein Skeptiker) | dev-hub#443 Kommentar 6032975846 (Owner-Entscheid: warten); Board selbst nur im Transkript | `board-bietet-nicht-faellige-irreversible-aktion-an` ×1 |
| 4 | Zwei Löschfristen für dieselben Sicherungen: 2027-01-04 (Vorschlag im Ledger #440) und 2026-10-18 (#443) | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | dev-hub#440 Kommentar 5982916108; dev-hub#443 Body Zeile 4 | `frist-widerspruch-ledger-vs-issue` ×1 |
| 5 | In `/etc/cloudflared` auf prod-b liegen 11 Konfigurationskopien vom 2026-08-04, die kein Sicherungs-Issue führt | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | `ls /etc/cloudflared` auf prod-b, festgehalten in dev-hub#443 Kommentar 6032975846 | `sicherungsinventar-unvollstaendig` ×1 |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | N1 und M1 geliefert, T1 und R1 bewusst beim Owner; #2, #3 |
| architektur_design | 4 | cgroup-Messung plus Kindprozess statt `max_tasks_per_child`, Begründung in #486 |
| code_konventionstreue | 4 | Invarianten-Test gegen Migration 0013, Lint vor dem Commit (B905 behoben); #1 betrifft nur das Board |
| risiko_debt | 4 | Löschung nicht vorgezogen; #5 als Nebenbefund verankert |
| prozess_effizienz | 4 | ein Hook-Block (#gates_caught), sonst ohne Rework; #3 kostete eine Rückfrage |
| entscheidungsqualitaet | 4 | #2 vor dem Token-Tausch gefunden statt danach; #3 per Einwand abgefangen |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Board-IDs wurden frei vergeben und trafen auf die Maßnahmen-IDs der Retro | Board-IDs mit eigenem Präfix je Quelle vergeben (z.B. `RM5` für Retro-Maßnahme 5) und nie eine fremde Nummer wiederverwenden | #1 |
| #426 legte „read-only“ als Kriterium fest, bevor `git grep` nach Schreibwegen lief | Beim Anlegen eines Rechte-Issues den Schreibweg-Grep sofort laufen lassen und das Ergebnis ins Kriterium schreiben | #2 |
| R1 stand mit Frist 2026-10-18 im 🟢-Bucket wie ein sofort ausführbares Item | Irreversible Items vor ihrer Frist als ⛔ „fällig ab <Datum>“ führen, nicht als go-fähig | #3 |
| Der Ledger-Vorschlag 2027-01-04 blieb neben der Issue-Frist stehen | Beim Anlegen des Fristen-Issues den Vorschlag im Ledger ausdrücklich als ersetzt markieren | #4 |
| Das Sicherungsinventar in #443 entstand aus dem Gedächtnis des Rückbaus | Das Inventar mit `ls`/`find` an jeder Ablage messen, auch an Konfigurationsorten | #5 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py`: Keiner der fünf Slugs kam vorher vor. Verwandt, aber nicht gleich: `action-board-link-missing` ×1 (`7d2e16`) und `irreversible-action-under-proposed-adr` ×1 (`6cec19`). Also keine GATE-PFLICHT. Abgleich mit `MEMORY.md` per grep: kein Eintrag zu Board-IDs oder Fristen.

### 5a. Rückfall-Prüfung

- **Gate gh-body-file-leer-ueberschrieben hat gefangen**, kein Rückfall: Die Body-Änderung an #484 hing nicht an `test -s`, der Hook blockte. Der zweite Versuch lief mit Kette.
- **Gate scope-checkpoint-not-durably-recorded**: Fall außerhalb des Zuschnitts, deshalb `gates_verwandt`. Prod wurde in diesem Inkrement nur gelesen. Der einzige Prod-Schreibschritt (R1) wurde vor der Ausführung vorgelegt und als Owner-Entscheid in #443 festgehalten.
- Die vier rückfälligen Gates aus 0.0 traten hier nicht erneut auf.

### 5b. Autonomie-Kalibrierung

- over_ask: keine. Die Rückfrage zu R1 betraf eine irreversible Löschung vor der vereinbarten Frist, also ein Gate.
- over_act: keine. #486 bleibt ungemergt, das Token wurde nicht angefasst, gelöscht wurde nichts.

## 6. Verankerung (Vorschläge, nicht geschrieben)

- **memory_candidate (feedback):** „Action-Board: irreversible Items vor ihrer Frist als ⛔ ‚fällig ab <Datum>‘ führen, nie im go-fähigen Bucket. **Why:** dev-hub#443, R1 am 2026-10-07 elf Tage zu früh als go angeboten. **How to apply:** beim Board-Bau jede Löschung und jeden Widerruf gegen ihre Frist prüfen.“
- **memory_candidate (feedback):** „Board-IDs nie aus fremden Nummernkreisen (Retro-Maßnahmen, Kriterien) wiederverwenden; Präfix je Quelle.“
- **adr_candidates:** keine.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Merge OCR-Fix | dev-hub | [#486](https://github.com/achimdehnert/dev-hub/pull/486) | 🟢 | Owner: „merge #486“ |
| 2 | Token-Rechte A oder B | dev-hub | [#426](https://github.com/achimdehnert/dev-hub/issues/426) | 🟢 | Owner entscheidet, legt Token ab |
| 3 | Sicherungen löschen ab 18.10. | dev-hub | [#443](https://github.com/achimdehnert/dev-hub/issues/443) | ⛔ | fällig 2026-10-18, Owner-Wort |
| 4 | K4-RAM-Nachtrag | dev-hub | [#484](https://github.com/achimdehnert/dev-hub/issues/484) | ⛔ | fällig 2026-10-08 |
| 5 | Board-Regeln als Memory | — | Abschnitt 6 | 🟢 | Owner verankert oder verwirft |

## 8. Nicht verifiziert (Restlücken)

- **#1 und #3 nur im Transkript belegt.** Die Boards stehen in keinem GitHub-Artefakt. Billigster Check: `retro_transkript_kennzahlen.py` mit Suche nach „R1“ und „M1“ im Assistententext.
- **Kein Skeptiker für #2 und #3** (lean). Die Bewertung „ohne Prüfung gesetzt“ bzw. „zu früh angeboten“ ist ein Selbsturteil. Billigster Check: ein Sonnet-Skeptiker je Befund, etwa 55k Tokens.
- **Deployments-Recht für die Freigabe** (in #426 genannt) wurde nicht gegen die API geprüft, sondern aus der GitHub-Doku übernommen. Billigster Check: Probe-Aufruf mit dem neuen Token.
- **`memory.peak` 488 MB** zählt seit dem Containerstart. Der Nachtlauf allein ist damit nicht isoliert gemessen.

getan: N1-Messung und Kommentar, PR #486, Schreibweg-Prüfung #426, Bestandsmessung #443, diese Retro · angenommen: Deployments-Recht laut Doku; dass der Ledger-Vorschlag 2027-01-04 durch #443 ersetzt ist · nicht verifizierbar: #1/#3 außerhalb des Transkripts, Bewertungen ohne Skeptiker · offen geblieben: Merge #486, Token-Entscheid, Löschung ab 2026-10-18, K4-Nachtrag ab 2026-10-08.

## Widerlegung

n/a (lean): Ohne Subagenten gibt es keine Widerlegungsbahn. Die Restlücke steht in §8. Bei dem Fehlen ist #3 der Befund mit dem höchsten Kipp-Risiko. Ein Gegenargument wäre, dass das Board nur den Owner-Zug zeigte und die Rückfrage genau richtig kam.

## Streichbahn

Keiner, weil dieses Inkrement nur die Pflichtteile von lean nutzte und jeder davon eine Wirkung hatte. Die Wirkungsbilanz bestätigte, dass alle vier rückfälligen Gates schon einen Beschluss haben. Der Längsschnitt zeigte, dass keiner der fünf Slugs schon vorkam.
