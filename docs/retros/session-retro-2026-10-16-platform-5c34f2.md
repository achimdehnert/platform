---
retro_schema: 1
date: 2026-10-16
repo_scope: [platform]
session_id: 5c34f2
footprint: full
findings_total: 18
findings_survived: 16
refuted_rate: 0.11
phase3_refuted: 1
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 2
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [kriterium-teilerfuellt-als-erfuellt-gemeldet]
recurring_findings: [kriterium-teilerfuellt-als-erfuellt-gemeldet, claim-before-cheapest-check, check-ohne-positivkontrolle, run-result-not-anchored, deferred-item-no-tracking-issue, serielle-prs-auf-derselben-datei]
gates_caught: [claim-before-cheapest-check, rohes-pytest-statt-make-test, aufschub-anker, serielle-prs-auf-derselben-datei]
gates_verwandt: [built-but-never-called, melder-ohne-leser]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "1 gekippt, 2 neu"
streichkandidaten: [wirkungsbilanz-tabelle-bei-entschiedenen-gates]
---

# Session-Retro 2026-10-16 (platform, Sitzung 5c34f2)

Sitzung vom 2026-10-16, 10:17 bis etwa 15:40 UTC, Thema Forgejo-Pilot (KONZ-platform-072, Mandat [#4018](https://github.com/achimdehnert/platform/issues/4018)). Sie schließt an die Sitzung d9f597 an, deren Retro bis etwa 09:05 UTC reicht. Footprint `full`: sieben PRs in einem Repo, kein Prod, keine Migration, kein ADR. Dazu kommen der lokale Pilot (Upgrade auf Forgejo 17, HTTPS-Umstellung, Probe-Repos) und ein Google-Cloud-Testprojekt ohne Abrechnungskonto für den Kill-Test S7, angelegt nach Owner-Wort „GC go“. Agenten-Budget 7: drei Finder, zwei Skeptiker (gebündelt nach Technik und Prozess), Widerlegungsbahn, Meta-Prüfung.

Artefakte (Grenze über die Branch-Präfixe `session/2026-10-16/achim-dehnert/konz072-*` und `pypi-release-melder`, nicht über das Datum):

- PR [#4041](https://github.com/achimdehnert/platform/pull/4041) FJ17 und T25, [#4042](https://github.com/achimdehnert/platform/pull/4042) K1U entfällt, [#4043](https://github.com/achimdehnert/platform/pull/4043) Alternativen zu Forgejo, [#4044](https://github.com/achimdehnert/platform/pull/4044) S7 Google-Brücke und Release-Melder (Konzept), [#4045](https://github.com/achimdehnert/platform/pull/4045) `tools/pypi_release_melder.py`, [#4054](https://github.com/achimdehnert/platform/pull/4054) Lesart Hoheit = B, [#4058](https://github.com/achimdehnert/platform/pull/4058) Ergebnis Kill-Test S7. Alle gemergt.
- Ledger-Kommentare in #4018 vom 2026-10-16 ab 10:17 UTC, Freigabe-Zeilen MB, DM, GH, AH, GC, SG, SB im Body.
- Nicht in der Sitzung: #4055 (App lotse-autor), #4059 (Retro meiki-hub 41679a). [#4056](https://github.com/achimdehnert/platform/pull/4056) (App lotse-autor, Branch `fix/melder-releases-unlesbar`, 15:10–15:16 UTC) kommt aus einer anderen Sitzung, repariert aber den Melder aus #4045 und zählt deshalb als Beleg (Befund 17).

## 0.0 Wirkungsbilanz

`tools/gate_wirkung.py` lief als erster Schritt und meldet vier rückfällige Gates: claim-before-cheapest-check (7), check-ohne-positivkontrolle (4), built-but-never-called (3), edit-in-worktree-without-read (2). Alle vier hat die Retro [d9f597](session-retro-2026-10-16-platform-d9f597.md) §0.0 am selben Tag mit Konsequenz geführt (nachschärfen [#2666](https://github.com/achimdehnert/platform/issues/2666), nachschärfen Rev 2 [#3722](https://github.com/achimdehnert/platform/issues/3722), ausweiten per Owner „187 go“, ausweiten [#3906](https://github.com/achimdehnert/platform/issues/3906)). Je Gate also („nachschärfen“ heißt dort ausweiten mit neuer Positivkontrolle und `revised` in der Gate-Datei): **Gate rückfällig: claim-before-cheapest-check** → ausweiten (nachschärfen); **Gate rückfällig: check-ohne-positivkontrolle** → ausweiten (nachschärfen Rev 2); **Gate rückfällig: built-but-never-called** → ausweiten; **Gate rückfällig: edit-in-worktree-without-read** → ausweiten. Diese Retro wiederholt die Tabelle nicht, sondern nennt nur, was in dieser Sitzung dazukam: claim-before-cheapest-check hat zweimal gefangen (11:03 und 14:58 UTC, dazu einmal in der Retro selbst) und einmal nicht (Befund 2). check-ohne-positivkontrolle hat einen neuen Fall: Der Melder aus #4045 wertete ein fehlendes `releases`-Feld als „0 Versionen“ (Befund 17). built-but-never-called liegt beim Release-Melder außerhalb des Zuschnitts (§5a).

## 1. Executive Summary

- Alle Owner-Aufträge sind geliefert und gemergt: FJ17 auf 17.0.0 mit T25, Alternativen-Anhang, S7-Konzept, Release-Melder, Lesart B, Kill-Test S7 gemessen. Google nimmt den nicht öffentlichen Pilot-Issuer an, TestPyPI meldet „valid token“.
- Der schwerste Befund: S7 wurde dem Owner um 15:20 UTC als bestanden empfohlen und mit „SG go“ gewertet, bevor der Teil „nur von geschütztem Tag“ des Kill-Kriteriums gemessen war. Die Messung danach war rot (`ref_protected` kommt nie als `'true'`), daraus wurde sieben Minuten später „SB go“ mit schwächerer Bedingung (Befund 1). Das ist das zweite Vorkommen nach Retro ec3416 Befund 12. Die Memory dazu griff erst eine Minute nach der Empfehlung: Die SG-Zeile im Body nennt den offenen Teil 2 schon selbst. Ein Beschluss auf falscher Grundlage blieb nicht stehen.
- #4058 schreibt im öffentlichen Konzept „fremde Repos werden von Google abgewiesen“ als Messung, unter der gewerteten Bedingung ist das eine Hypothese (Befund 18). Der Melder aus #4045 hatte einen stillen Null-Fehler, den eine andere Sitzung mit #4056 behob (Befund 17).
- Die gewertete Variante ist schwächer als im Konzept beschrieben: Die Google-Bedingung bindet den Workflow nicht, der Vergleich mit einem GitHub-Publisher ohne Environment ist zu günstig (Befund 4). Der Release-Melder, im Konzept als zweite Linie genannt, wird von nichts aufgerufen (Befund 5).
- Nachgehalten wird zu wenig: Messlauf der gewerteten Variante fehlte im Ledger (Befund 3, in der Retro nachgetragen), Folgearbeit ohne Anker (Befund 6), Rückbau des Google-Projekts nicht im Runbook (Befund 7).
- Freigaben mit Außenwirkung lagen alle vor der Tat (Google-Projekt 25 s nach „GC go“ angelegt, Abrechnung aus). Kein Leck im öffentlichen Repo, Suche mit Positivkontrolle.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | S7 als bestanden empfohlen und mit „SG go“ (15:22 UTC) gewertet, bevor Teil 2 des Kill-Kriteriums (Upload nur von geschütztem Tag) gemessen war; Messung danach rot, Ersatz „SB go“ 15:29 UTC; T26 sagt „S7 gemessen“, ein Upload wurde nie versucht. Die SG-Body-Zeile (15:23 UTC) nennt Teil 2 schon als offen; Kommentar 6218785683 nummeriert den roten Teil im selben Text einmal als Teil 2 und einmal als Teil 1 | verfrühte Festlegung | mittel (3b: hoch → mittel) | SURVIVES (kommandobelegt, Severity in 3b gekippt) | #4018 Body-Bearbeitungsverlauf; Kommentare [6218686626](https://github.com/achimdehnert/platform/issues/4018#issuecomment-6218686626) und [6218785683](https://github.com/achimdehnert/platform/issues/4018#issuecomment-6218785683); Body-Zeilen SG, SB; #4058 | `kriterium-teilerfuellt-als-erfuellt-gemeldet` ×2 (ec3416 Befund 12) |
| 2 | TestPyPI-Konto des Owners als Voraussetzung unterstellt, nicht geprüft; Owner 15:19 UTC „ich bin dort mit keinem nutzer angemeldet“, Korrektur 15:20 UTC | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | #4018 Kommentar [6218686626](https://github.com/achimdehnert/platform/issues/4018#issuecomment-6218686626) („Das hatte ich nicht geprüft“) | `claim-before-cheapest-check` |
| 3 | Messlauf zur gewerteten Variante (Lauf 9 Tag `v4.0.0`, Lauf 10 `main`) stand nicht im Ledger, obwohl #4058 sich darauf beruft; letzter Kommentar vor dem Merge 15:25 UTC, Merge 15:31 UTC. In der Retro nachgetragen | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | #4058 Belegliste; Nachtrag [6219134027](https://github.com/achimdehnert/platform/issues/4018#issuecomment-6219134027); Pilot-API Aufgaben 85/86 | `run-result-not-anchored` |
| 4 | Schwächen der gewerteten S7-Variante unvollständig benannt: Bedingung prüft nur Repository und Tag-Präfix, nicht den Workflow; Vergleich „etwa GitHub-Publisher ohne Environment“ zu günstig, weil PyPI bei GitHub den Workflow-Dateinamen pinnt | verfrühte Festlegung | mittel | SURVIVES (Phase 3) | `docs/konzepte/anhaenge/KONZ-072-einsatzkonzept-forgejo.md` §2.1 Block „Ergebnis Kill-Test“; aktive Bedingung per Provider-Abfrage | neu |
| 5 | Release-Melder `tools/pypi_release_melder.py` wird im Konzept als „zweite Linie“ geführt, aber von keinem Makefile-Ziel, Workflow, Cron oder Timer aufgerufen; kein Alarmkanal, Exit immer 0 | Werkzeug | mittel | SURVIVES (kommandobelegt) | `git grep pypi_release_melder origin/main` außerhalb Modul/Tests: 0 (Positivkontrolle Tests: 3); `crontab -l`: 0; Timer-Liste nur sichtbarkeits-melder | verwandt `built-but-never-called`, `melder-ohne-leser` |
| 6 | Folgearbeit ohne Issue oder Ledger-Zeile mit Status: Melder-Funde (iil-testkit 0.6.0 ohne Tag und Attestation, iil-aifw 0.13.0 ohne Attestation, Flotten-Inventar veraltet), Alarmkanal und Zeitplan des Melders, Upstream-Meldung `ref_protected` (nur durch einen Menschen), TestPyPI-Nachholung „beim ersten Stufe-2-Release“ | Prozesslücke | mittel | SURVIVES (kommandobelegt) | #4018 Kommentar [6215540260](https://github.com/achimdehnert/platform/issues/4018#issuecomment-6215540260); `gh issue list --search` ohne Treffer zu diesen Funden | `deferred-item-no-tracking-issue` |
| 7 | Rückbau-Runbook (KONZ-072 Z. 192) nennt Google-Testprojekt, Dienstkonto, Pilot-CA, Caddy-Front, Probe- und Demo-Repos nicht; Rückbau des Google-Projekts steht nur in einem Kommentar; „Ein Token muss nicht widerrufen werden“ widerspricht dem Ledger | Prozesslücke | mittel | SURVIVES (Phase 3) | `docs/konzepte/KONZ-platform-072-forgejo-pilot.md` Z. 192 (Positivkontrolle der Suche); #4018 Kommentar [6218623044](https://github.com/achimdehnert/platform/issues/4018#issuecomment-6218623044) | neu |
| 8 | Freigaben „PD go“, „RW go“ (11:38 UTC) und „GB go“ (11:59 UTC) stehen nicht als Zeile im #4018-Body; „GB go“ gab das Google-Projekt schon frei, um 15:09 UTC wurde es mit „GC go“ erneut eingeholt, ohne GB als ersetzt zu markieren | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | #4018 Body; Kommentare [6214698365](https://github.com/achimdehnert/platform/issues/4018#issuecomment-6214698365), [6215540260](https://github.com/achimdehnert/platform/issues/4018#issuecomment-6215540260) | neu |
| 9 | Vier PRs auf denselben Einsatzkonzept-Anhang (#4041, #4044, #4054, #4058), #4042 nimmt 16 min nach #4041 den Owner-Zug K1U wieder heraus; Hinweis „serielle-prs-auf-derselben-datei“ bei #4054 ohne Reaktion gemergt | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | Merge 10:30:01 und 10:46:51 UTC; Check-Hinweis auf #4054 | `serielle-prs-auf-derselben-datei` |
| 10 | Pilot-Jobs sind nicht isoliert: privilegierter dind auf `tcp://0.0.0.0:2375` ohne TLS im Netz von Forgejo, Jobs mit `network: host`; die in der Sitzung neu erzeugte Pilot-CA hat keine Name Constraints. Im Konzept nicht benannt | Wissenslücke | mittel | SURVIVES (Phase 3) | `~/sandbox-laeufe/forgejo-pilot/compose.yml` Z. 43–71, `runner/config.yml`, `openssl x509 -text` auf `tls/ca/root.crt` | neu |
| 11 | Release-Melder: Herkunftsprüfung akzeptiert jede der vier Orgs für jeden Repo-Namen, `repo_tags()` nimmt die erste antwortende Org und ist ungetestet; `PUBLISHER_REMOTE` und Tag-Formen sind Code-Literale statt Daten | Werkzeug | niedrig | SURVIVES (Phase 3, Test-Vorwurf zu Netz-Doubles widerlegt) | `tools/pypi_release_melder.py` Z. 54, 71–78, 100, 159–170; `tools/tests/test_pypi_release_melder.py` Z. 127 | neu |
| 12 | Kill-Tests in anderer Reihenfolge als empfohlen (S1 → S4 → S7 → S3): S7 zuerst und allein gemessen, Abweichung im Ledger nicht begründet | Kommunikation | niedrig | SURVIVES (Phase 3) | Einsatzkonzept §2 Empfehlung; T26 | neu |
| 13 | Eine für eine andere Sitzung bestimmte Owner-Nachricht (12:50 UTC) führte zu einer Absender-Suche im Postfach und zum Auslesen des Transkripts einer Parallelsitzung, bevor geklärt war, ob sie zum Auftrag gehört; Abbruch nach „falsche session“ 12:51 UTC, nichts geschrieben | Kommunikation | niedrig | SURVIVES (Phase 3) | Scope-Checkpoint #4018 Kommentar 13:21 UTC; Transkript 12:50:52–12:51:19 UTC | neu |
| 14 | Drei Blockaden vor der Tat: rohes `pytest` (12:01 UTC, Hook), Aufschub-Anker (15:25 UTC, Hook), Zugriff auf Zugangsdaten nach „fülle du es selbständig aus“ (10:44 UTC, Berechtigungsprüfung). Je ein Retry, keine Wirkung | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Transkript-Kennzahlen; #4045 „7333 passed“ per `make test` | `rohes-pytest-statt-make-test` (gefangen) |
| 17 | Release-Melder aus #4045 wertete ein fehlendes `releases`-Feld der PyPI-Antwort als „0 Versionen“ (`.get("releases", {})`), das Paket fiel still aus dem Bericht; das bricht die eigene Kopfregel des Moduls („Null aus dem eigenen Fehlerfall ist keine Abwesenheit“). Behoben durch #4056 aus einer anderen Sitzung (vorher 4 rot, nachher 0) | fehlende Validierung | mittel | SURVIVES (3b neu, gegengeprüft) | `git show 5d8a5234:tools/pypi_release_melder.py` Z. 151, Z. 23; [#4056](https://github.com/achimdehnert/platform/pull/4056) | `check-ohne-positivkontrolle` (Gate rückfällig) |
| 18 | #4058 schreibt für die gewertete Variante unter „Gemessen“: „main und fremde Repos werden von Google abgewiesen“; das fremde Repo ist nur unter der früheren Bedingung gemessen, unter der gewerteten eine Hypothese. Im öffentlichen Konzept steht eine Hypothese als Messung | fehlende Validierung | mittel | SURVIVES (3b neu, gegengeprüft) | `docs/konzepte/anhaenge/KONZ-072-einsatzkonzept-forgejo.md` Z. 123 f. auf `origin/main`; Nachtrag [6219134027](https://github.com/achimdehnert/platform/issues/4018#issuecomment-6219134027) | `claim-before-cheapest-check` |
| 15 | „GH go“ war over_ask, weil nur die lokale Sandbox betroffen war | — | — | REFUTED (Phase 3): Umstellung berührte die laufende K2-Messung und den Auth-Pfad (Gate Security-Config) | #4018 Body GH; Ledger „berührt K2-Messung und Sync. Owner-Entscheid nötig“ | — |
| 16 | Tag-Schutzmuster inkonsistent, `v2.0.0` war ungeschützt | — | — | REFUTED (vor Phase 3): `v2.0.0` war die bewusste Negativkontrolle unter Muster `v1*` | Pilot-API Aufgaben 81–83; Kommentar [6218785683](https://github.com/achimdehnert/platform/issues/4018#issuecomment-6218785683) | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Alle Aufträge gemergt, S7 bis „valid token“ gemessen; Mangel: Kriterium nur in schwächerer Form erfüllt, Upload nie versucht (Befund 1), eine Aussage im Konzept ungemessen (Befund 18) |
| architektur_design | 3 | Gewertete Variante ohne Workflow-Bindung (Befund 4), Pilot-Jobs nicht isoliert (Befund 10) |
| code_konventionstreue | 2 | Stiller Null-Fehler gegen die eigene Kopfregel (Befund 17), Literale statt Daten im Melder (Befund 11); Gegenpol: Tests `test_should_…`, `make test` grün |
| risiko_debt | 3 | Rückbau Google-Projekt nicht im Runbook (Befund 7), Melder läuft nicht (Befund 5) |
| prozess_effizienz | 3 | Serielle PRs und zurückgenommener Owner-Zug (Befund 9), Freigaben unvollständig verankert (Befund 8) |
| entscheidungsqualitaet | 3 | Empfehlung SG vor Wortlaut-Abgleich, Owner entschied zweimal (Befund 1); Gegenpol: GH und GC korrekt vorgelegt (Befund 15) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| SG empfohlen nach Messung bis „valid token“, Teil 2 erst nach „SG go“ | Vor jeder Bewertungs-Empfehlung das Kill-Kriterium wörtlich zitieren, je Teil Beleg oder „ungemessen“ daneben; erst wenn alle Teile gemessen sind, Kürzel vorlegen | #1 |
| TestPyPI-Konto als vorhanden unterstellt | Vor einem Owner-Zug dessen Voraussetzungen (Konto, Rolle, Zugang) als Liste prüfen oder als offene Frage in denselben Zug schreiben | #2 |
| #4058 belegt mit drei Kommentaren, keiner zeigt die gewertete Bedingung | Reihenfolge Messung → Ledger-Kommentar → PR; die PR-Belegliste verlinkt nur Kommentare, die genau die gewertete Bedingung zeigen | #3 |
| Schwäche nur am gemessenen Ausfall `ref_protected` beschrieben | Schwächen einer OIDC-Bedingung entlang der Claim-Liste prüfen (repository, ref, workflow, ref_protected, sub) und je Claim „gebunden/nicht gebunden“ ins Konzept | #4 |
| Melder als zweite Linie im Konzept, ohne Aufrufer | Ein Werkzeug erst als Schutzlinie benennen, wenn es als Runner-Phase im Melder-Register steht (mit Leser) oder ein Zeitplan es aufruft | #5 |
| Folgearbeit nur als Prosa in Kommentaren | Je ausgelassenem Punkt im selben Zug eine Ledger-Zeile mit Status oder ein Issue, Liste unter den Ledger-Kommentar | #6 |
| Rückbau Google-Projekt nur im Kommentar | Jedes neue Außenartefakt im selben Zug in die Rückbau-Zeile des Konzepts eintragen | #7 |
| PD, RW, GB nicht im Body; GC holt GB erneut ein | Jede Freigabe als Body-Zeile; ein Kürzel, das ein früheres ersetzt, nennt das frühere als ersetzt | #8 |
| Vier PRs auf denselben Anhang, K1U-PR nach 16 min zurückgenommen | Owner-Entscheide zu einem Dokument sammeln und einen PR je Block; den Serien-Hinweis vor dem Merge beantworten | #9 |
| Pilot-Isolation nicht geprüft, als S7 echte Tokens brachte | Vor dem ersten Lauf mit echten Fremd-Tokens die Job-Isolation des Pilots prüfen und als Einschränkung ins Konzept | #10 |
| Org-Zuordnung generisch, Literale im Melder | Org und Tag-Form je Paket aus der Flotten-Datei lesen, `repo_tags` mit Double testen | #11 |
| S7 zuerst, Abweichung unbenannt | Abweichung von einer dokumentierten Reihenfolge im Ledger mit Grund benennen | #12 |
| Fremde Nachricht sofort bearbeitet | Bei einer Owner-Nachricht ohne Bezug zum Auftrag zuerst ein Satz Rückfrage, dann lesen | #13 |
| Regel stand im Kontext, Werkzeug fing erst beim Aufruf | Vor Testlauf und Zugangsdaten-Frage die Hausregel anwenden (`make test`, Owner-Skript in `~/zug/`) | #14 |
| Melder-Tests deckten nur vollständige PyPI-Antworten ab | Für jeden Datenpfad eines Melders einen Test mit fehlendem Schlüssel, der „unlesbar“ statt „0“ erwartet; die Kopfregel als Test formulieren | #17 |
| Konzepttext fasst Messung und Übertragung unter „Gemessen“ zusammen | Im Konzept je Aussage zur gewerteten Variante „gemessen (Lauf N)“ oder „übertragen, Hypothese“ schreiben, wie im Ledger-Nachtrag | #18 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` gelaufen. Slugs dieser Retro mit Zähler ≥2:

- `kriterium-teilerfuellt-als-erfuellt-gemeldet`: ×1 laut `retro_kpis.py`, inhaltlich ×2, neu benannt, zweites Vorkommen nach ec3416 Befund 12 (dort ohne Slug). Memory `feedback_mandats_kriterium_im_wortlaut_pruefen` existiert (per `ls` geprüft) und griff erst eine Minute nach der Empfehlung (Selbstkorrektur in der SG-Zeile) ⇒ formal **GATE-PFLICHT**, Kandidat in §6; das Gate soll die Empfehlung abfangen, nicht die nachträgliche Korrektur.
- `check-ohne-positivkontrolle`: Gate rückfällig, Konsequenz entschieden (#3722); hier Befund 17.
- `claim-before-cheapest-check` ×111, Gate vorhanden, rückfällig, Konsequenz entschieden (#2666).
- `deferred-item-no-tracking-issue` ×68, gedeckt und teils declined; hier erneut (Befund 6).
- `run-result-not-anchored` ×3, bewusst ohne Gate (dokumentierte Owner-Entscheidung); hier das vierte Vorkommen.
- `serielle-prs-auf-derselben-datei` ×2, Gate vorhanden (Hinweis), hat gefangen.

### 5a. Rückfall-Prüfung

`tools/gate_wirkung.py` gelaufen (§0.0).

- **Gate rückfällig: claim-before-cheapest-check** — Befunde 2 und 18 sind weitere Fälle nach dem Bau. Konsequenz steht: ausweiten (nachschärfen, #2666), kein zweites Gate.
- **Gate rückfällig: check-ohne-positivkontrolle** — Befund 17: stille Null im eigenen Melder, in der Sitzung nicht bemerkt. Konsequenz steht: ausweiten (nachschärfen Rev 2, #3722), kein zweites Gate.
- built-but-never-called: Zuschnitt sind `raw_data`-Schlüssel ohne Leser und öffentliche Funktionen in `tools/`, die nur Tests rufen. Der Melder ist ein Skript mit `main`, kein Funktionsaufrufer fehlt im Sinn des Gates ⇒ `gates_verwandt`, kein Rückfall.
- melder-ohne-leser: Zuschnitt sind Runner-Phasen im Melder-Register (`governance/melder-register.yaml`). Der Release-Melder ist keine Runner-Phase und steht nicht im Register ⇒ `gates_verwandt`. Genau diese Lücke schließt Soll-Schritt zu Befund 5.
- serielle-prs-auf-derselben-datei: Hinweis kam, der PR wurde ohne Antwort gemergt. Das Gate ist ein Hinweis, kein Blocker; Befund niedrig, keine Gate-Änderung. In `gates_caught` steht es, weil es feuerte; abgewendet hat es die Serie nicht.

### 5b. Autonomie-Kalibrierung

- over_ask: Kandidat „GH go“ in Phase 3 widerlegt (Befund 15). „GC go“ nach „GB go“ ist eine zweite Freigabe für dasselbe Projekt; ob die Kontofrage sie gerechtfertigt hat, ist ungeprüft (§8). Keine Klasse.
- over_act: keiner. Google-Projekt 15:09:32 UTC angelegt, Freigabe 15:09:07 UTC; HTTPS-Neustart nach „GH go“; Demo-Repo lokal ohne Außenwirkung.

## 6. Verankerung (Vorschläge, nicht geschrieben)

**memory_candidates**

```markdown
---
name: feedback_kill_kriterium_alle_teile_vor_empfehlung
description: "Kill-/Mandats-Kriterium erst nach Messung ALLER Teile als bestanden empfehlen; 2. Episode nach ec3416 (S7, 2026-10-16)"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-10-16-s7-sg-vor-teil2
---
S7 wurde nach Messung bis „valid token“ als bestanden empfohlen („SG go“ 15:22 UTC), Teil 2
„nur von geschütztem Tag“ war ungemessen und dann rot („SB go“ 15:29 UTC). Erste Episode: ec3416 Befund 12.
**Why:** Der Owner entscheidet sonst zweimal, die erste Entscheidung steht auf falscher Grundlage.
**How to apply:** Kriterium wörtlich zitieren, je Teil Beleg oder „ungemessen“; Kürzel erst vorlegen, wenn kein Teil „ungemessen“ ist, sonst ausdrücklich „teilweise, Rest: …“. Ergänzt [[feedback_mandats_kriterium_im_wortlaut_pruefen]].
```

```markdown
---
name: feedback_owner_zug_voraussetzungen_pruefen
description: "Vor einem Owner-Zug dessen Voraussetzungen prüfen (Konto, Rolle); TestPyPI-Fall 2026-10-16"
metadata:
  type: feedback
---
Vorschlag „Pending Publisher bei TestPyPI eintragen“ unterstellte ein TestPyPI-Konto des Owners, das es nicht gab.
**Why:** Ein unausführbarer Owner-Zug kostet eine Rückfrage und Vertrauen.
**How to apply:** Voraussetzungen als Liste prüfen oder als offene Frage in denselben Zug.
```

**adr_candidates:** keine. Die Bewertung der S7-Variante gehört in KONZ-072 und an das Gate 2027-01-15.

**Gate-Kandidat** `kriterium-teilerfuellt-als-erfuellt-gemeldet` (GATE-PFLICHT): Hinweis-Hook auf Kommentare in Mandats-Issues, die „bestanden“ oder „erfüllt“ zu einem Kriterium melden, ohne dass der Kommentar das Kriterium zitiert und je Teil einen Beleg nennt. Bau nur nach Owner-Wort.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Messlauf gewertete Variante ins Ledger | platform | [#4018](https://github.com/achimdehnert/platform/issues/4018#issuecomment-6219134027) | ✅ | erledigt in der Retro |
| M2 | Konzept-Nachtrag S7: „fremde Repos abgewiesen“ als Hypothese kennzeichnen oder Fremd-Repo-Lauf nachholen, Workflow nicht gebunden, Vergleich korrigieren, Pilot-Isolation, Rückbau-Zeile um Google-Projekt, CA, Caddy, Repos | platform | [#4018](https://github.com/achimdehnert/platform/issues/4018) | 🟢 | Owner-Kürzel, dann ein PR auf KONZ-072 (Befunde 4, 7, 10, 12, 18) |
| M3 | Release-Melder als Runner-Phase mit Register-Eintrag und Leser einhängen, Org/Tag-Form aus Flotten-Datei, Test für fehlende Schlüssel je Datenpfad | platform | [#4045](https://github.com/achimdehnert/platform/pull/4045) | 🟢 | Owner-Kürzel, dann Issue und PR (Befunde 5, 11, 17; Kernfehler schon durch #4056 behoben) |
| M4 | Folge-Ledger-Zeilen: Melder-Funde, Alarmkanal, Upstream-Meldung, TestPyPI-Nachholung, Body-Zeilen PD/RW/GB | platform | [#4018](https://github.com/achimdehnert/platform/issues/4018) | 🔵 | ich, ohne Owner-Wort (Befunde 6, 8) |
| M5 | Gate-Kandidat Kriterium im Wortlaut | platform | — | 🟢 | Owner-Kürzel für den Bau (Befund 1) |
| M6 | Memory-Kandidaten aus §6 | platform | — | 🟢 | Owner-Kürzel (Befunde 1, 2) |
| M7 | Streichkandidat Wirkungsbilanz-Tabelle | platform | — | 🟢 | Owner-Kürzel für Skill-Edit (§Streichbahn) |

Befunde 9, 13 und 14 brauchen keine eigene Maßnahme über den Soll-Ablauf hinaus. Befund 3 ist mit M1 erledigt.

## 8. Nicht verifiziert (Restlücken)

- **getan:** drei Finder, zwei Skeptiker, Widerlegungsbahn, Meta-Prüfung; Ledger-Nachtrag zu Befund 3; Lecksuche über alle sieben PRs (Projekt-ID, Projektnummer, Org-Nummer, Dienstkonto-Adressen, Konto-Domain: 0 Treffer, Positivkontrolle auf der Projekt-Notiz: 1 Treffer); Freigabe-Reihenfolge Google-Projekt per `createTime`.
- **angenommen:** dass ein fremdes Repo auch unter der gewerteten Bedingung abgewiesen wird (nur unter der früheren gemessen, Repo-Teil unverändert; als Befund 18 geführt); dass die Wertung über „valid token“ statt Upload als Ziel des Kill-Tests gilt (billigster Check: Owner-Frage, Score zielerreichung hängt daran); dass PyPI bei GitHub-Publishern den Workflow-Dateinamen pinnt (Wissensstand des Skeptikers, nicht online geprüft).
- **nicht verifizierbar:** Befunde 10, 13 und 14 sind nur lokal belegt (Pilot-Dateien außerhalb des Repos, Transkript-Kennzahlen), ohne Sitzungszugang nicht per gh/git nachprüfbar. Ursache, warum Forgejo 17 `ref_protected` nie setzt (Hypothese „nicht implementiert“; billigster Check: Quelltext der Claim-Erzeugung im Forgejo-Repo lesen). Ob Pilot-Jobs die Google-Tokens anderer Jobs sehen könnten (nicht gemessen). Ob die Kontofrage die zweite Freigabe GC nach GB nötig machte.
- **offen geblieben:** M2 bis M7; Rückbau des Google-Projekts am Gate 2027-01-15; Upstream-Meldung an Forgejo durch einen Menschen.

## Widerlegung

Ein Subagent (Opus, frischer Kontext) mit Entwurf, Footprint und Artefaktliste, Auftrag „Widerlege das Urteil dieser Retro“. Ergebnis **1 gekippt, 2 neu**; die drei Punkte habe ich selbst nachgeprüft (`gh issue view 4018` SG-Zeile, `gh pr view 4056`, Konzept Z. 121–126 auf `origin/main`).

| # | Ergebnis | Verdikt | Beleg |
|---|---|---|---|
| 1 | hält im Kern, Severity hoch überzogen: SG-Zeile 15:23 UTC nennt Teil 2 schon offen, gemessen und vor dem Merge von #4058 durch SB ersetzt, ohne Außenwirkung | GEKIPPT (hoch → mittel) | #4018 Body-Bearbeitungsverlauf |
| 2–14 | halten (Befund 10 nicht nachgeprüft, Pilot-Dateien außerhalb `origin/main`) | BESTAETIGT | Kommentare 6218686626, 6219134027; Konzept Z. 121–126, 192 f.; Melder Z. 159–170, 221–235 |
| 15, 16 | REFUTED halten | BESTAETIGT | GH-Body-Zeile „Risiko für K2-Messung und Abgleich“; Tabelle in 6218785683 |
| 17 | stiller Null-Fehler im Melder, behoben in #4056 | NEU | `git show 5d8a5234:tools/pypi_release_melder.py` Z. 151 |
| 18 | Hypothese als Messung im Konzept | NEU | Konzept Z. 123 f. gegen Nachtrag 6219134027 |

Scores: code_konventionstreue von 3 auf 2 (Befund 17). zielerreichung 4 nennt 3b unentscheidbar, weil das Kill-Kriterium „Upload“ sagt; in §8 als Annahme geführt.

## Streichbahn

Kandidat `wirkungsbilanz-tabelle-bei-entschiedenen-gates`, Belegart **Dublette**: Die Phase-0.0-Tabelle der rückfälligen Gates steht am 2026-10-16 wortgleich in drei Retros (d9f597 §0.0, chat-hub c5851a §0.0, diese Sitzung), weil alle vier Gates schon entschieden sind. Vorschlag: Sind alle `RUECKFAELLIG`-Gates in einer Retro der letzten 7 Tage mit Konsequenz geführt, genügt in 0.0 ein Link darauf plus die neuen Vorkommen dieser Sitzung. Diese Retro wendet das schon so an (§0.0). Skill-Edit nur nach Owner-Wort (M7).

## Self-Review

Separater Meta-Agent, sah nur Report und Skill. Stichprobe 11 Belege per gh/git, alle bestätigt; Invariante 16 Soll-Zeilen = 16 SURVIVES = `findings_survived`; `refuted_rate` 0.11 = 2/18, Band laut `retro_kpis.py` „gesund“; `retro_report_check.py` Exit 0. Vier Befunde am Report, eingearbeitet:

1. „nachschärfen“ ist keine der drei Antworten aus 5a ⇒ als „ausweiten“ zugeordnet (§0.0, §5a).
2. Befunde 10, 13, 14 nur lokal belegt ⇒ in §8 unter „nicht verifizierbar“.
3. Slug-Zähler des neuen Slugs ⇒ „×1 laut `retro_kpis.py`, inhaltlich ×2“; `serielle-prs-auf-derselben-datei` in `gates_caught` begründet (§5a).
4. Reihenfolge der Zeilen 17/18 vor 15/16 in §2: bewusst so gelassen, Überlebende vor Widerlegten.

Agenten-Budget: 7 (3 Finder, 2 Skeptiker, 3b, Meta). Der Skill nennt für `full` mit 3b und Meta ≤6 (Phase 5) und ≤7 (Phase 3b); die Retro liegt an der oberen Grenze, die Unstimmigkeit im Skill ist ein Kandidat für die nächste Skill-Pflege.
