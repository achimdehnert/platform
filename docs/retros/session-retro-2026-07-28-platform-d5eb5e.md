---
retro_schema: 1
date: 2026-07-28
repo_scope: [platform]
session_id: d5eb5e
footprint: deep
findings_total: 20
findings_survived: 19
refuted_rate: 0.05
phase3_refuted: 1
pre_refuted: 0
over_ask: 1
over_act: 0
scores:
  zielerreichung: 2
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 2
  entscheidungsqualitaet: 2
gate_candidates:
  - pr-body-stale-after-authorized-execution
  - production-run-as-first-integration-test
  - sibling-tools-diverge-on-source-of-truth
  - prose-measurement-without-reproducible-artifact
  - duplicate-logic-instead-of-reusing-existing
recurring_findings:
  - claim-before-cheapest-check
  - deferred-item-no-tracking-issue
  - parallel-session-pr-collision
  - untested-tool-module-green-gate
  - scope-checkpoint-not-durably-recorded
  - handover-stale-vor-merge
  - autonomous-no-human-review
---

# Session-Retro 2026-07-28 — platform (d5eb5e)

## 1. Executive Summary

- **Keine der vier Handover-Prios ist weiter als am Morgen.** Stattdessen entstand ein
  nicht angekündigtes fünftes Arbeitspaket (Mail-Archivierung), das die Session füllte —
  ohne dokumentierten Scope-Checkpoint.
- **28.158 Nachrichten wurden in zwei Produktivpostfächern verschoben** — mit Code aus
  fünf offenen PRs, die zu keinem Zeitpunkt Fremd-Review hatten und nicht auf `main` liegen.
- **Drei von drei Fehlern im Verschiebe-Werkzeug fielen erst im scharfen Lauf auf**, nicht
  durch Tests. Der Trockenlauf kann diese Fehlerklasse strukturell nicht fangen, weil er
  den Schreibpfad nie ausführt.
- **Ein realer Merge-Konflikt liegt unsichtbar bereit:** #1494 und #1500 ersetzen dieselben
  vier Zeilen in `bekannte_konten()` unterschiedlich. GitHub zeigt ihn nicht, weil es nur
  gegen `main` prüft.
- **Von 20 Befunden überleben 19 die Falsifikation.** Alle acht der Dimension
  „Entscheidungen & Fehler" halten, auch der, gegen den eine Gegenmessung vorlag.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Keine der 4 Handover-Prios weiter als vor der Session | Prozesslücke | hoch | SURVIVES | `git show origin/main:AGENT_HANDOVER.md` Z. 184–187; `gh pr view {1498,1500,1501,1502,1504} --json files,body` | scope-checkpoint-not-durably-recorded |
| 2 | PR-Body #1502 sagt „Noch nicht ausgeführt", während 22.599 Verschiebungen liefen; Body nie editiert | fehlende Validierung | kritisch | SURVIVES | Body vs. Kommentar `IC_kwDORAOORM8AAAABMAxFnA` (07:11Z) | pr-body-stale-after-authorized-execution |
| 3 | Kein schreibendes Werkzeug für die Mutationen | Prozesslücke | hoch | **REFUTED** | `archiv_einsortieren.py` Z. 453–468: `--quelle`/`--ziel-wurzel`/`--imap-konto` generisch; 2 von 3 Fällen damit real ausgeführt | — |
| 4 | #1498 behauptet „schließt #1481" ohne `roles.py`-Diff; `closingIssuesReferences` leer | verfrühte Festlegung | mittel | SURVIVES | `gh pr view 1498 --json files,closingIssuesReferences`; `gh issue view 1481` → OPEN | claim-before-cheapest-check |
| 5 | Postfach-Defekte aus #1504 zu Nicht-Aufgaben erklärt, kein Tracking-Issue | Prozesslücke | hoch | SURVIVES | `gh issue list --search "created:>=2026-07-28"` → 3 Treffer, keiner passend | deferred-item-no-tracking-issue |
| 6 | `AGENT_HANDOVER.md` nicht nachgezogen; kein begleitender Handover-PR, anders als übliches Muster (#1486, #1404) | Prozesslücke | niedrig | SURVIVES | `git show origin/main:AGENT_HANDOVER.md` Kopf „2026-07-25"; `gh pr list --search "AGENT_HANDOVER in:title"` | handover-stale-vor-merge |
| 7 | Garantie „Trockenlauf ist Standard" nur durch `if not args.apply` in `main()`/`lauf_imap()`; kein Test ruft beide auf | fehlende Validierung | kritisch | SURVIVES | `archiv_einsortieren.py` Z. 432, 533; Grep über 3 Testdateien → 0 Aufrufe | untested-tool-module-green-gate |
| 8 | Vier Fehlerzweige in `imap_verschiebe()` ungetestet; `FakeImap.uid()` liefert immer OK. Duplikat-Risiko bei EXPUNGE-Fehler, da `imap_posten()` nicht auf `\Deleted` filtert | fehlende Validierung | hoch | SURVIVES | `archiv_einsortieren.py` Z. 176–203 vs. `test_archiv_imap.py` Z. 782–793; `readonly=False` bestätigt | untested-tool-module-green-gate |
| 9 | Backoff 2/4/8 s lief live; ~12.311 Posten fälschlich als Fehler gezählt | verfrühte Festlegung | hoch | SURVIVES | Commit `7f13d95c` messageBody | production-run-as-first-integration-test |
| 10 | Zwei Tests prüfen nur Konstanten (`>= 60`, `>= 8`, `<= 20`), kein Verhalten | fehlende Validierung | mittel | SURVIVES | `test_archiv_stapel.py` Z. 932–933, 1015–1019 | — |
| 11 | Graph-Einsortierer entscheidet nach `receivedDateTime`, Prüfer nach `sentDateTime`; `sentDateTime` kommt im Diff von #1502 null Mal vor | Wissenslücke | hoch | SURVIVES | `grep sentDateTime pr1502.diff` → 0; `ablage_pruefung.py` Z. 319–349 | sibling-tools-diverge-on-source-of-truth |
| 12 | Die Entlastungs-Messung „7.326 von 7.326" existiert nur als Prosa in einer Commit-Message; kein Skript, kein Log im PR. #1504 nennt eine andere Stichprobe (24) | fehlende Validierung | hoch | SURVIVES | `gh pr view 1502 --json commits`; PR-Dateiliste ohne Messskript | prose-measurement-without-reproducible-artifact |
| 13 | Byte-identische Regexe + fast identische Ordner-Walks doppelt in #1502/#1504; `organize_mail.py:list_folders()` auf main nicht importiert | Prozesslücke | mittel | SURVIVES | `_LIST_ZEILE`/`_UID`/`_INTERNALDATE` identisch; `git show origin/main:tools/mail_agent/organize_mail.py` Z. 98 | duplicate-logic-instead-of-reusing-existing |
| 14 | Vier stille `except Exception` in `ImapQuelle`; bei vollem Verbindungsabbruch greift auch der Nenner-Abgleich nicht, weil `status()` über dieselbe Verbindung scheitert | fehlende Validierung | mittel | SURVIVES | `ablage_pruefung.py` Z. 224–227, 235–238, 243–249, 270–273 | — |
| 15 | #1498 hebt §4.7 „kein LLM-Zugriff" und §4.9 Regel 1 für den bürgernahen MEiKI-Kanal auf; Freigabe nur als Fließtext, nicht als verlinktes Artefakt | fehlende Validierung | hoch | SURVIVES | `gh pr view 1498 --json reviews` → `[]`; eigener Review-Prep-Kommentar benennt die Lücke | claim-before-cheapest-check |
| 16 | #1494 und #1500 ersetzen dieselben vier Zeilen in `bekannte_konten()` unterschiedlich — echter, von GitHub unsichtbarer Merge-Konflikt | fehlende Validierung | hoch | SURVIVES | `gh pr diff 1494/1500 -- tools/mail_agent/vorgang.py`; beide `baseRefOid e971840b` | parallel-session-pr-collision |
| 17 | 9 offene PRs, alle `REVIEW_REQUIRED`, ältester 14,9 h — die letzten 20 gemergten PRs lagen 0–2 h offen | Prozesslücke | hoch | SURVIVES | `gh pr list --state merged --limit 20 --json createdAt,mergedAt` | — |
| 18 | Zwei Workflows chronisch rot seit 22./23.07. (`HTTP 401 Bad credentials`), in dieser Session nicht bemerkt; 2 neue Drift-Funde nicht triagiert | Wissenslücke | mittel | SURVIVES | Runner Health Check + Deploy Failure Monitor Logs; Registry-Live-Reconcile ist per Design rot | — |
| 19 | 28.158 Nachrichten in 2 Produktivpostfächern mutiert mit Code ohne jede Fremd-Review, nicht auf `main` | Prozesslücke | kritisch | SURVIVES | `gh pr view 1502 --json reviews` → `[]`, `state OPEN`, `mergedAt null`; Kommentare 06:33Z/07:11Z, Commits `4abe3d86`/`423770de` | autonomous-no-human-review |
| 20 | Alle drei Fix-Commits in #1502 benennen ausdrücklich, dass der Fehler erst im scharfen Lauf auffiel, nicht durch Tests | fehlende Validierung | hoch | SURVIVES | Commits `faad65b4`, `7f13d95c`, `423770de` messageBody | production-run-as-first-integration-test |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **2** | #1: 0 von 4 Handover-Prios bewegt; #6: kein Handover-Nachzug |
| architektur_design | **3** | #11/#13 (Inkonsistenz, Duplikation) gegen die bewusst begründete Trennung Prüfer/Einsortierer, die den IMAP-Fehler aufdeckte |
| code_konventionstreue | **4** | Commit-Format, `test_should_*`, keine Backticks — vom Finder ausdrücklich als sauber bestätigt; Abzug für #10 |
| risiko_debt | **2** | #5 (kein Tracking), #7/#8 (Kerngarantie ungetestet), #16 (Konflikt), #19 (Prod ohne Review) |
| prozess_effizienz | **2** | #17 (15 h vs. 0–2 h Norm), #20 (Validierung erst im Prod-Lauf), #6 |
| entscheidungsqualitaet | **2** | #15 (Schutzklauseln ohne verlinkte Freigabe), #4 (Überbehauptung), #2 (Artefakt widerspricht Wirkung) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| 4 Handover-Prios blieben unberührt, ein fünftes Thema füllte den Tag | Beim Themenwechsel weg von der Handover-Liste einmal innehalten und den Wechsel als Zeile im Handover festhalten, bevor gearbeitet wird | #1 |
| PR-Body sagt „Noch nicht ausgeführt", Ausführung nur im Kommentar | Nach jedem `--apply`-Lauf den PR-**Body** editieren, nicht nur kommentieren — der Body ist das Artefakt, das gelesen wird | #2 |
| „schließt #1481" ohne Code-Diff behauptet | Vor jedem „schließt #N" im PR-Text prüfen, ob der Diff die Akzeptanzkriterien wirklich erfüllt; sonst „bereitet #N vor" | #4 |
| Postfach-Defekte im PR-Text zu Nicht-Aufgaben erklärt | Im selben Zug ein Issue je aufgeschobener Restmenge anlegen und aus dem PR verlinken | #5 |
| Kein begleitender Handover-PR zu 5 Feature-PRs | Handover-Update als sechsten PR im selben Zug erzeugen, wie im Muster #1486/#1404 | #6 |
| `main()`/`lauf_imap()` von keinem Test aufgerufen | Einen Test mit gefälschtem `args`-Objekt und Fake-Transport ergänzen, der belegt: ohne `--apply` erfolgt **kein** Schreibaufruf | #7 |
| `FakeImap.uid()` liefert immer OK | Fake um konfigurierbare Fehlerantworten je Befehl erweitern und alle vier Fehlerzweige durchlaufen; zusätzlich `UNDELETED` in `imap_posten()` | #8 |
| Backoff-Konstante geschätzt, Korrektur erst nach 12.311 Falsch-Fehlern | Vor dem ersten Massenlauf einen künstlich gedrosselten Testlauf gegen einen kleinen Ordner fahren, der die Retry-Schleife wirklich auslöst | #9 |
| Tests prüfen `DROSSEL_WARTEN >= 60` statt Verhalten | Drossel-Zyklus mit gemocktem `time.sleep` über mehrere Runden simulieren und die Gesamt-Wartezeit prüfen | #10 |
| Graph-Einsortierer nutzt `receivedDateTime`, Prüfer `sentDateTime` | Beide Werkzeuge auf dieselbe Quelle ziehen und die Wahl im Code kommentieren — wie für IMAP bereits geschehen | #11 |
| Messung „7.326 von 7.326" nur als Prosa in einer Commit-Message | Jede Zahl, die eine Entscheidung trägt, als reproduzierbares Skript in den PR legen — Prosa ist kein Beleg | #12 |
| Regexe und Ordner-Walks doppelt implementiert | Vor Neuimplementierung `git grep` nach vorhandener Funktion; gemeinsame IMAP-Helfer in ein Modul ziehen | #13 |
| Vier stille `except Exception` in `ImapQuelle` | Jede Ausnahme mit Ordnername und Fehlertyp in eine Störungsliste schreiben, die der Bericht ausweist | #14 |
| Schutzklauseln aufgehoben, Freigabe nur als Fließtext | Vor dem Aufheben einer Schutzklausel die Freigabe als PR-Kommentar anfordern und im ADR darauf verlinken | #15 |
| Drei PRs ändern dieselbe Datei, nur ein Paar wurde geprüft | Vor jedem neuen PR `gh pr list --state open` und die Dateilisten aller offenen PRs gegen die eigenen Dateien schneiden | #16 |
| 9 PRs offen, ältester 14,9 h, weiter neue erzeugt | Ab 3 offenen eigenen PRs keine neuen mehr erzeugen, sondern den Stapel als Board vorlegen und auf Review warten | #17 |
| Zwei Workflows seit 6 Tagen rot, unbemerkt | Rote Cron-Workflows auf `main` in den Session-Start-Runner aufnehmen, nicht nur Deploy-Läufe | #18 |
| 28.158 Nachrichten mit ungeprüftem Branch-Code mutiert | Vor einem Massenlauf gegen Produktivdaten den Werkzeug-PR mergen lassen oder die Ausführung ausdrücklich als Gate vorlegen | #19 |
| Alle drei Fehler fielen erst im scharfen Lauf auf | Vor dem ersten `--apply` gegen ein Referenzpostfach mit bekanntem Bestand laufen — der Trockenlauf deckt den Schreibpfad strukturell nicht ab | #20 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über alle Reports in `docs/retros/`:

- **18 Slugs stehen bereits bei ≥2 und sind damit gate-pflichtig.** Sieben davon sind in
  dieser Session erneut aufgetreten: `claim-before-cheapest-check` (#4, #15),
  `deferred-item-no-tracking-issue` (#5), `parallel-session-pr-collision` (#16),
  `untested-tool-module-green-gate` (#7, #8), `scope-checkpoint-not-durably-recorded` (#1),
  `handover-stale-vor-merge` (#6), `autonomous-no-human-review` (#19).
- **Score-Mittel über 54 Retros:** `risiko_debt` ist mit **2,61** die dauerhaft schwächste
  Dimension. Diese Session liegt mit **2** darunter — der Trend verschlechtert sich.
- **`refuted_rate`-Trend:** 0,08 · 0,20 · 0,00 · 0,11 · 0,35 · 0,21 · 0,13 · 0,22 → diese
  Session **0,05**. Echte Falsifikations-Quote hier identisch, da `pre_refuted = 0`:
  `1/(20−0) = 0,05`. **Fünf von neun Sessions liegen damit unter 0,2** — die Band-Regel
  wertet das als Hinweis, dass die Falsifikation Theater sein könnte. Das ist kein
  Einzelausreißer dieser Session, sondern ein Muster der Reihe und gehört als eigener
  Prüfpunkt in die Skill, nicht in diesen Report.
- **Fünf neue Slugs** ohne Vorlauf: `pr-body-stale-after-authorized-execution`,
  `production-run-as-first-integration-test`, `sibling-tools-diverge-on-source-of-truth`,
  `prose-measurement-without-reproducible-artifact`,
  `duplicate-logic-instead-of-reusing-existing`.

## 5b. Autonomie-Kalibrierung

- **`over_act` = 0.** Jeder Produktiv-Schritt hatte eine ausdrückliche menschliche Freigabe
  im Gespräch. Aber: **keine dieser Freigaben hinterließ ein durables Artefakt** — weder
  PR-Kommentar noch Issue. Befund #19 ist deshalb kein Autonomie-Überschritt, sondern eine
  Dokumentationslücke an einem Gate. Das ist derselbe Mechanismus wie in
  `feedback_gate_approval_needs_pr_comment`.
- **`over_ask` = 1.** Der 2022-Pilotlauf über 145 Nachrichten wurde einzeln vorgelegt,
  obwohl er vollständig reversibel und im selben Zug freigegeben war. Vertretbar als
  Vorsicht vor dem ersten scharfen Lauf, aber im Verhältnis zum nachfolgenden
  22.599er-Lauf inkonsistent.
- **Kalibrierungs-Vorschlag:** Nicht die Gate-Liste verschieben, sondern die
  **Artefakt-Pflicht** an Gate 1/2 schärfen — eine Freigabe für einen Prod-Schritt gilt
  erst als erteilt, wenn sie als PR-Kommentar oder Issue-Zeile existiert.

## 6. Verankerung

### memory_candidates

```markdown
---
name: feedback_pr_body_stale_after_execution
description: Nach einem --apply-Lauf den PR-BODY editieren, nicht nur kommentieren — der Body ist das gelesene Artefakt
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-28-pr-body-stale
---

Ein PR-Body, der „noch nicht ausgeführt" sagt, während der Lauf längst lief, ist ein
falsches Artefakt — auch wenn die Ausführung im Kommentar-Thread dokumentiert ist.

**Why:** Am 2026-07-28 stützte ein unabhängiger Prüfer sein Urteil („nur Trockenlauf")
auf den Body von platform#1502 und lag falsch; ein zweiter Prüfer las die Kommentare und
kam zum Gegenteil. Der Widerspruch kostete einen zusätzlichen Stichentscheid.

**How to apply:** Nach jedem Lauf, der Produktivdaten verändert, den Body im selben Zug
editieren. Kommentare ergänzen, der Body führt. Verwandt: [[feedback_gate_approval_needs_pr_comment]]
```

```markdown
---
name: feedback_dry_run_does_not_cover_write_path
description: Ein Trockenlauf führt den Schreibpfad nie aus — dessen Fehler fallen erst im scharfen Lauf auf
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-28-write-path-untested
---

Der sichere Modus eines Werkzeugs ist genau der Modus, der seinen gefährlichen Teil nicht
prüft. Grüne Tests plus sauberer Trockenlauf sagen **nichts** über die Zeile, die schreibt.

**Why:** Am 2026-07-28 fielen alle drei Fehler von `archiv_einsortieren.py` erst im
scharfen Lauf auf: falsches Schlüsselwort an die HTTP-Hülle (Abbruch beim 1. von 145),
zu kurzer Drossel-Backoff (12.311 Falsch-Fehler), Sortierung nach Ankunft statt Kopfzeile.

**How to apply:** Vor dem ersten `--apply` gegen Produktivdaten (1) einen Test, der den
Schreibaufruf gegen einen Fake fährt und die Signatur gegen die echte bindet, (2) einen
Lauf gegen ein Referenzpostfach mit bekanntem Bestand. Verwandt:
[[feedback_throwing_test_double_is_vacuous_behind_except]]
```

```markdown
---
name: feedback_sibling_tools_need_one_source_of_truth
description: Schreiber und Prüfer müssen dieselbe Datenquelle nutzen, sonst erzeugt der eine, was der andere meldet
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-28-two-date-sources
---

Zwei Werkzeuge desselben Arbeitspakets, die dieselbe Frage aus verschiedenen Feldern
beantworten, produzieren Geisterbefunde: Der Schreiber legt ab, der Prüfer meldet es als
Fehler.

**Why:** Am 2026-07-28 sortierte der Graph-Pfad von `archiv_einsortieren.py` nach
`receivedDateTime`, während `ablage_pruefung.py` genau dieses Feld als unzuverlässig
einstuft und `sentDateTime` nutzt. Für IMAP war die Lehre gezogen, für Graph nicht.

**How to apply:** Bei einem Schreiber/Prüfer-Paar die Quelle **einmal** festlegen und in
beiden Modulen kommentieren. Weicht einer ab, braucht es eine reproduzierbare Messung im
Repo — nicht eine Zahl in einer Commit-Message.
```

### adr_candidates

Kein neuer ADR nötig. Die Schutzklausel-Aufhebung (#15) gehört als Freigabe-Kommentar an
den bestehenden PR #1498, nicht in ein neues Dokument.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 Freigabe für §4.7/§4.9-Aufhebung als PR-Kommentar nachtragen — https://github.com/achimdehnert/platform/pull/1498
2. 🟢 Merge-Reihenfolge #1494/#1500 entscheiden (echter Konflikt) — https://github.com/achimdehnert/platform/pull/1500
3. 🟢 Fünf PRs reviewen, damit der Stapel abgebaut wird — https://github.com/achimdehnert/platform/pull/1504

### 🔵 Offen — ich kann sofort

4. 🔵 Tracking-Issues für die Postfach-Defekte aus #1504 anlegen — https://github.com/achimdehnert/platform/pull/1504
5. 🔵 „schließt #1481" im Body von #1498 auf „bereitet vor" korrigieren — https://github.com/achimdehnert/platform/pull/1498
6. 🔵 Body von #1502 um die tatsächlich gelaufenen Mutationen ergänzen — https://github.com/achimdehnert/platform/pull/1502
7. 🔵 Graph-Pfad auf `sentDateTime` ziehen + Messskript beilegen — https://github.com/achimdehnert/platform/pull/1502
8. 🔵 Apply-Gate und vier IMAP-Fehlerzweige testen — https://github.com/achimdehnert/platform/pull/1502

## 8. Nicht verifiziert (Restlücken)

- **Zahl der mutierten Nachrichten.** Der Stichentscheid kommt auf **28.158** (22.599 +
  649 + 4.910) und weist „rund 30.000" als ≈6 % Abweichung aus. Der IIL-Sent-Archiv-Lauf
  (6.877) ist in dieser Summe **nicht** enthalten; ob er in den Artefakten belegt ist,
  wurde nicht geprüft. Billigster Check: `gh pr view 1502 --json comments` nach „6.877".
- **Ob die 401-Fehler der beiden roten Workflows dieselbe Ursache haben.** Beide melden
  `Bad credentials`, ein gemeinsamer Token wurde nicht nachgewiesen. Billigster Check:
  `gh workflow view <name> --yaml` und die verwendeten Secret-Namen vergleichen.
- **Ob der Merge-Konflikt #1494/#1500 tatsächlich blockiert.** Belegt ist die identische
  Zeilenersetzung; ein realer Merge-Versuch fand nicht statt. Billigster Check:
  `git merge-tree` gegen beide Branch-Heads.
- **Wer den Verteiler-Drift von 2 auf 0 gebracht hat.** Kein Artefakt dieser Session
  berührt `doctor.py` oder `generate.py`; der Skeptiker führt es als Hypothese.
- **Wirkung der 11 gelöschten Nachrichten.** Sie liegen in „Gelöschte Elemente" und sind
  rückholbar; ein Nachweis, dass keine davon geschäftsrelevant war, existiert nicht.

## Self-Review

Ein separater Meta-Reviewer hat den Bericht gegen die Skill-Regeln geprüft — nicht die
Session. Ergebnis: **8 von 9 Struktur- und Rechenregeln erfüllt.**

Bestätigt: Frontmatter vollständig und typrichtig · Scores ganzzahlig und je an einer
Befund-Nummer verankert · Invariante `|Soll-Schritte| == |überlebende Befunde|` exakt
erfüllt (19 = 19, Referenzmenge deckungsgleich) · Befund-Tabelle mit eingefrorenen Spalten
und lückenloser Nummerierung · `refuted_rate = (1+0)/20 = 0,05` rechnerisch korrekt ·
§8 mit fünf Restlücken und je einem billigsten Check · Memory-Kandidaten als Vorschläge,
nicht als geschriebene Dateien · Report-Pfad kollisionsfrei.

**Ein Mangel, behoben:** Die erste Fassung ordnete `refuted_rate = 0,05` als „am unteren
Rand, aber innerhalb der Streuung" ein und verschwieg die Band-Implikation. Der
Meta-Reviewer rechnete nach: **fünf von neun Sessions liegen unter 0,2** — die Band-Regel
deutet das als möglicherweise theatralische Falsifikation. §5 ist entsprechend korrigiert.

**Methodenbefund für die Skill selbst** (nicht für diesen Report): Ein Skeptiker widerlegte
zwei Befunde auf Basis eines PR-**Bodies**, während ein anderer Skeptiker denselben Sachverhalt
aus den PR-**Kommentaren** gegenteilig entschied. Der Widerspruch wurde erst durch einen
zusätzlichen Stichentscheid aufgelöst. Die Phase-3-Regel schreibt vor, Belege „unabhängig
und breiter" zu ziehen — sie benennt aber nicht, dass ein PR-Body das **älteste** Artefakt
eines Threads ist und von Kommentaren und Commit-Messages überholt werden kann. Eine
Ergänzung der Verify-Regel um „bei PR-Belegen immer Body **und** Kommentare **und**
Commit-Messages mit Zeitstempel-Vergleich" hätte den Stichentscheid erspart.
