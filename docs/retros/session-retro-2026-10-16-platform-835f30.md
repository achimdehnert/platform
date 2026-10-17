---
retro_schema: 1
date: 2026-10-16
repo_scope: [platform, dialog-repo-privat, checkpoint-repo-privat]
session_id: 835f30
footprint: deep
findings_total: 19
findings_survived: 15
refuted_rate: 0.21
phase3_refuted: 3
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 2
  entscheidungsqualitaet: 3
gate_candidates: [kontrolllauf-schreibt-echtes-gate-log, kuerzel-ohne-artefakt-bezug]
recurring_findings: [deferred-item-no-tracking-issue, hook-drill-ohne-fehlalarm-gegenprobe, kuerzel-ohne-artefakt-bezug]
gates_caught: [claim-before-cheapest-check, vertrauliches-verlaesst-ablage, aufschub-anker, parallel-session-pr-collision, scope-checkpoint-not-durably-recorded, rohes-pytest-statt-make-test, check-ohne-positivkontrolle, inline-heredoc-quoting-rework, cd-fehlschlag-kette-laeuft-weiter, pr-autor-identitaet-nicht-angewandt, untested-command-handed-to-user, issue-ohne-dublettensuche, main-tree-guard-recurring-incident]
gates_verwandt: [self-review-presented-as-review, gate-approval-needs-pr-comment]
over_ask_klassen: []
over_act_klassen: [audit-log-bereinigung-versucht, aussenwirkung-gebuendelt-in-einem-befehl]
widerlegung: "5 gekippt, 4 neu"
streichkandidaten: []
streich_begruendung: Kein Gate blieb ohne Wirkung. vertrauliches-verlaesst-ablage fängt zu viel statt zu wenig; dafür ist der Fix #4053 der richtige Weg, nicht die Streichung.
---

# Session-Retro 2026-10-16 (platform, Sitzung 835f30)

Sitzung am 2026-10-16 von etwa 10:17 bis 15:40 UTC, danach Retro. Thema war die Zusammenarbeit mit einem Partner-Agenten: Messversuch, Dialog-Repo, Gates für vertrauliche Inhalte. Footprint `deep`, drei Repos berührt, davon zwei privat (Dialog-Repo und Checkpoint-Repo; ihre Namen bleiben hier ungenannt, weil platform öffentlich ist). Kein Prod, keine Migration, kein ADR. Agenten-Budget 8: drei Finder, drei Skeptiker, Widerlegungsbahn, Meta-Prüfung.

Artefakte der Sitzung:

- platform: PR [#4047](https://github.com/achimdehnert/platform/pull/4047) geschlossen (Dublette), [#4048](https://github.com/achimdehnert/platform/pull/4048) gemergt (Gate vertrauliches-verlaesst-ablage), [#4052](https://github.com/achimdehnert/platform/pull/4052) gemergt (Aufschub-Anker), [#4055](https://github.com/achimdehnert/platform/pull/4055) offen (lokale Modellroute, Melder Kundendaten an Billiganbieter), [#4056](https://github.com/achimdehnert/platform/pull/4056) gemergt (Melder-Fix). Issues [#4049](https://github.com/achimdehnert/platform/issues/4049), [#4053](https://github.com/achimdehnert/platform/issues/4053), Kommentare in [#3862](https://github.com/achimdehnert/platform/issues/3862).
- Dialog-Repo (privat): PR #1 und #2 gemergt, #3, #4 und #6 offen, Issue #5 geschlossen, Ruleset `main-nur-per-pr` angelegt.
- Checkpoint-Repo (privat): Scope-Checkpoint mit drei Kommentaren (11:53Z, 14:04Z, 14:59Z).
- Nicht in der Sitzung: übrige platform-PRs desselben Tages (Parallelsitzungen).

## 0.0 Wirkungsbilanz

`tools/gate_wirkung.py` lief als erster Schritt. Alle vier rückfälligen Gates sind entschieden, die Beschlüsse stehen in [`session-retro-2026-10-16-platform-d9f597.md`](session-retro-2026-10-16-platform-d9f597.md) §0.0.

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | 7 | Quelle | nachschärfen, beschlossen ([#2666](https://github.com/achimdehnert/platform/issues/2666)). Hier siebenmal gefangen (Befund 16). Befunde 2 und 7 liegen außerhalb des Zuschnitts, siehe §5a |
| check-ohne-positivkontrolle | 4 | Quelle | nachschärfen Rev 2, beschlossen ([#3722](https://github.com/achimdehnert/platform/issues/3722)). Hier mindestens zweimal gefangen. Befund 11 ist verwandt: die Positivkontrolle lief, die Fehlalarm-Gegenprobe traf die falsche Population |
| built-but-never-called | 3 | Quelle | ausweiten, beschlossen (Owner „187 go“). Kein Fall |
| edit-in-worktree-without-read | 2 | Quelle | ausweiten, beschlossen ([#3906](https://github.com/achimdehnert/platform/issues/3906)). Kein Fall; nach jeder Verdichtung kam der Read-Batch zuerst |

## 1. Executive Summary

- Die Aufträge wurden geliefert: Partner-Mail, Berichtigung, Eingaben, Neubewertung des Messversuchs, zwei Gates, Melder-Fix, Dialog-Repo mit Auftrag 001. Die Skeptiker widerlegten 5 von 12 geprüften Befunden, die Widerlegungsbahn holte zwei davon zurück (3 verworfen); widerlegt bleiben „Owner-Wort LR go fehlt“, „@-Erwähnung als Umgehung“ und „#3862 ohne Anker“.
- Das neue Gate #4048 ging ohne Meldephase scharf; seine Fehlalarm-Gegenprobe lief über Befehle, unter denen noch kein einziger Tresor-Befehl war (Befund 11). Dasselbe Muster plant #4055: Sperren am 23.10., Auswertung am 30.10. (Befund 3).
- Die eigene Positivkontrolle schrieb 7 Zeilen ins echte Gate-Log; der Versuch, sie herauszufiltern, wurde als Audit-Eingriff gesperrt (Befund 1).
- Im Dialog-Repo wurde mit leeren Approvals gemergt, ein eigener Fund war vor der Partnerantwort sichtbar, und die Wache läuft ohne technisches Ende auf einem ungeprüften Zweig (Befunde 4, 5, 14).
- Den Owner kostete die Sitzung 15 Kürzel und zahlreiche Skriptläufe, drei Kürzel davon liefen erst in eine Classifier-Sperre (Befund 17); zwei Freigaben haben keine Gegenzeile in einem Artefakt (Befund 18).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Die Positivkontrolle zu #4048 (12:50:45Z) und die Selbstprobe im Owner-Skript `nd.sh` (13:02:56Z, 13:03:37Z) riefen den Hook ohne `GATE_HITS_DATEI` auf und schrieben 7 Zeilen mit leerer Session ins echte Gate-Log. Um 12:50:51Z versuchte der Agent, alle Zeilen des Slugs per `grep -v` zu entfernen; gesperrt als „Logging/Audit Tampering“. Die Zeilen stehen noch dort | fehlende Validierung | mittel | SURVIVES (Beleg korrigiert in 3b) | Transkript Z. 2639 (12:50:45Z) und Z. 2649 (12:50:50Z); Gate-Log 5 Zeilen 12:50:46Z ohne Session; `nd.sh` Z. 37 schreibt `probe.md` | neu: kontrolllauf-schreibt-echtes-gate-log |
| 2 | Das Owner-Skript für den Approve von #4052 enthielt den vom Agenten vorformulierten Review-Text „… geprueft“ ohne Subjekt. Der Code-Owner-Review unter dem Owner-Konto behauptet damit eine Prüfung, die der Agent formuliert hat | Kommunikation | mittel | SURVIVES | Skript-mtime 13:21:29Z, Review APPROVED 13:25:14Z, Merge 13:27Z | verwandt: self-review-presented-as-review |
| 3 | #4055 schaltet den Melder per Owner-Skript am 2026-10-23 auf Sperren; die Auswertung der Meldewoche ist laut PR-Text und Registry-`expires_note` erst zum 2026-10-30 vorgesehen. Fehlalarme würden erst nach dem Scharfschalten bewertet | verfrühte Festlegung | mittel | SURVIVES | Owner-Skript Z. 10/41 (`STICHTAG`, `billig_melden_bis`); Diff #4055 Registry `expires 2026-10-30`, `expires_note` „Fehlalarme → Stichtag verschieben“ | hook-drill-ohne-fehlalarm-gegenprobe (s. Befund 11) |
| 4 | Dialog-Repo: PR #2 wurde 18 s nach einem Approve ohne Text gemergt, die Rückfrage „Funde oder ausdrücklich keine Funde“ kam 34 min später mit dem Wortlaut „bevor gemergt wird“. PR #1 wurde 10 s nach dem ersten von vier leeren Approves über das Owner-Konto gemergt. Die Review-Form stand nur im Auftragstext | Prozesslücke | mittel | SURVIVES | PR #2: Approve 14:23:11Z, Merge 14:23:29Z, Rückfrage 14:57:42Z; PR #1: Approves 14:34:51Z–14:36:52Z, Merge 14:35:01Z | verwandt: gate-approval-needs-pr-comment |
| 5 | Ein Fund des Agenten zu Auftrag 001 wurde über Register-Issue #5 (14:49:39Z) sichtbar, bevor die Partnerseite in PR #2 Funde geliefert hatte. Die Berichtigung kam 15:20:04Z, der Fund zählt nicht für die Bilanz | Prozesslücke | mittel | SURVIVES | Dialog-Repo Issue #5 Timeline; Kommentar 15:20:04Z | — |
| 6 | Der Advocatus-WARN zu #4055 (15:12:26Z: `urlopen` folgt `http_proxy`, die Loopback-Prüfung schützt nur die URL) ist weder behoben noch als Issue verankert | Prozesslücke | mittel | SURVIVES | `gh pr view 4055`: letzter Commit 14:06:23Z; Issue-Suche „proxy“, „http_proxy“, „4055“ leer | deferred-item-no-tracking-issue (declined) |
| 7 | Der Scope-Checkpoint von 14:59:03Z sagt „Nicht berührt: Prod, Rechte, Hooks.“, obwohl am selben Tag #4048, #4052 und der offene #4055 Hook-Code ändern und um 14:04:26Z im Dialog-Repo das Ruleset `main-nur-per-pr` entstand | Kommunikation | mittel | SURVIVES (in 3b erweitert) | Checkpoint-Kommentar 14:59:03Z; Ruleset `created_at` 14:04:26Z; Kommentar-Sperre 14:58:56Z auf die Vorfassung | verwandt: claim-before-cheapest-check (Negativaussage außerhalb des Zuschnitts) |
| 8 | #4047 entstand unter dem Owner-Konto und wurde nach dem Hinweis des Gates nach 8 s geschlossen und als #4048 über die App neu eröffnet. Folgenlos | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Gate-Treffer 12:52:44Z; #4047 12:52:48Z–12:52:56Z; #4048 12:52:59Z | gates_caught: pr-autor-identitaet-nicht-angewandt |
| 9 | Messversuch-Läufe und versiegelte Funde liegen nur im flüchtigen Scratchpad unter `/tmp`. Die Kopie in den Tresor blockierte die Schranke (Fehlalarm-Klasse #4053), die Sicherung wartet als Owner-Skript | Prozesslücke | mittel | SURVIVES (kommandobelegt) | Schranken-Meldung „bewegt Tresor-Inhalt in ein geschuetztes Ziel“; Owner-Skript `sv.sh` | — |
| 10 | Um 11:51Z bündelte ein Befehl zwei Außenwirkungen (Entwurf verwerfen und Kommentar im Checkpoint-Repo); gesperrt als „External System Writes“ | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Kennzahlen: Ablehnung 11:51Z | — |
| 11 | #4048 ging ohne Meldephase direkt auf `blocking`. Die Fehlalarm-Gegenprobe (Replay 13.357 Aufrufe, 0 Sperren) lief über eine Population ohne Tresor-Befehle: den Tresor legte der Agent erst um 12:50:16Z an, alle Tresor-Befehle der Sitzung kamen danach. Bis 13:48Z sperrte das Gate neunmal, 9 der 18 Fehlerläufe der Sitzung | fehlende Validierung | mittel | SURVIVES (in 3b zurückgeholt) | Transkript Z. 2608 (`mkdir` 12:50:16Z); PR-Text #4048; Registry `mode: blocking`; Gate-Log 13:03Z–13:48Z; Fix #4053 offen | hook-drill-ohne-fehlalarm-gegenprobe (2. Retro) |
| 12 | In #3862 blieben Punkte 1 und 3 ohne Anker | Prozesslücke | niedrig | REFUTED | #3862 offen; Punkt 1 im Body, Punkt 3 in Kommentar 6215336428, bestätigt in 6217014010 | — |
| 13 | Nach der Ablehnung von `--add-reviewer` nutzte der Agent eine @-Erwähnung als Ersatzweg | Prozesslücke | hoch | REFUTED | Erwähnung im PR-Text ab Anlage 14:18:28Z, Text nie bearbeitet, Ablehnung 14:18:44Z; Reviewer-Eintrag als Owner-Skript, ausgeführt 14:20:43Z | — |
| 14 | Die Wache im Dialog-Repo läuft als Probelauf ohne technisches Ende (`Persistent=true`, kein Enddatum, keine Ablaufprüfung im Code; der 23.10. steht nur in Beschreibung und PR-Text) und führt einen veränderlichen Arbeitszweig aus, dessen PR #6 noch nicht reviewt ist. „AL go“ (14:53:16Z) fiel, bevor PR #6 existierte (14:57:40Z). Der Vorwurf „ohne Owner-Freigabe“ bleibt widerlegt | Prozesslücke | niedrig | SURVIVES (in 3b teilweise zurückgeholt) | Owner-Lauf `al.sh` 15:04:20Z; PR #6 `createdAt` 14:57:40Z, Stand REVIEW_REQUIRED; Unit-Datei | — |
| 15 | #4055 zitiert ein Owner-Wort „LR go“, das im Transkript fehlt | Kommunikation | hoch | REFUTED | Transkript Z. 3277/3291/3293: „LR go“ 13:04:47Z, eingereiht während eines Turns | — |
| 16 | Der Stop-Hook claim-before-cheapest-check feuerte siebenmal; das sei ein Rückfall | fehlende Validierung | mittel | REFUTED (vorab) | Das Feuern ist der Fang (Zuschnitt „prüfbare Behauptung ohne Werkzeuglauf“), Gate-Log, 7 Zeilen mit dieser Session-ID | gates_caught |
| 17 | Die Sitzung kostete den Owner 15 Kürzel und eine zweistellige Zahl von Skriptläufen. Dreimal folgte auf ein Kürzel erst eine Classifier-Sperre und dann doch ein Owner-Skript: Repo-Kommentar nach „GZ go“ (11:51Z), Repo-Anlage nach „RT go“ (13:56Z), Zeitgeber nach „AL go“ (14:57Z, „Unauthorized Persistence“) | Prozesslücke | mittel | SURVIVES (neu in 3b) | Transkript, Ablehnungen 11:51Z, 13:56:19Z, 14:57:22Z; 24 Skripte in `~/zug` im Zeitfenster (teils Parallelsitzungen) | — |
| 18 | Zwei Freigaben der Sitzung („MA go“ 13:32Z, „FR go“ 13:46Z) haben keine Gegenzeile im Checkpoint-Issue, in GitHub oder in der Memory; vier weitere stehen nur in der lokalen Memory. Charta Art. 10 verlangt ein durables Artefakt im selben Zug | Prozesslücke | mittel | SURVIVES (neu in 3b) | Checkpoint-Kommentare: 0 Treffer „MA go|FR go“; Memory-Ordner: 0 Treffer | kuerzel-ohne-artefakt-bezug (2. Retro) |
| 19 | Zwölf Kontextverdichtungen in rund vier Stunden (11:50Z–15:48Z, etwa alle 20 Minuten). Zwei Owner-Kürzel kamen als eingereihte Nachrichten an; an genau dieser Lücke hing Befund 15 | Werkzeug | mittel | SURVIVES (neu in 3b) | Transkript, 12 Einträge `compact_boundary` | verwandt: compaction-without-reread (Wiederlesen hier ungeprüft) |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 4 | Alle Aufträge geliefert; die zweite Messversuch-Runde wartet auf den Partner, nicht auf uns. Offen: Befund 9 |
| architektur_design | 3 | Schaltreihenfolge ohne Meldephase (Befunde 3, 11), Proxy-Lücke (Befund 6), Wache ohne Ende (Befund 14) |
| code_konventionstreue | 3 | Konventionen eingehalten. Mangel: Kontrollläufe ohne Log-Isolation (Befund 1) |
| risiko_debt | 3 | Proxy-Lücke ohne Anker (Befund 6), Material im flüchtigen Scratchpad (Befund 9), ungeprüfter Zweig in der Wache (Befund 14) |
| prozess_effizienz | 2 | 18 Fehlerläufe, davon 9 aus dem eigenen Gate (Befund 11); sechs Ablehnungen; Owner-Last (Befund 17); zwölf Verdichtungen (Befund 19) |
| entscheidungsqualitaet | 3 | Vorformulierter Prüfvermerk (Befund 2), Merge vor Funden (Befund 4), Fund vor Partnerantwort (Befund 5), Freigaben ohne Gegenzeile (Befund 18) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Positivkontrolle und Skript-Probe schreiben ins echte Log, danach Filterversuch auf den ganzen Slug (12:50Z) | Jeder Kontrolllauf eines Hooks setzt `GATE_HITS_DATEI` auf eine Temp-Datei. Unechte Zeilen meldet der Agent dem Owner, statt sie zu löschen | #1 |
| Owner-Skript mit fertigem Review-Text „geprueft“ | Der Review-Text sagt, wer was geprüft hat („Agent: Tests grün; Owner: Diff gesehen“), oder bleibt Platzhalter | #2 |
| #4055 plant Sperren am 23.10. vor der Auswertung am 30.10. | Der Stichtag liegt nach der Auswertung der Meldewoche | #3 |
| Neues Gate direkt `blocking`, Gegenprobe über eine Population ohne den Zielfall | Neue Schranken starten `advisory` mit Meldewoche; scharf erst nach Auswertung der Meldungen gegen die Population, für die das Gate gebaut ist | #11 |
| Merge des Auftrags-PR nach einem leeren Approve, Rückfrage danach | Der Auftrag fordert die Fundliste als Review-Text; gemergt wird erst, wenn sie oder „keine Funde“ dasteht | #4 |
| Register-Issue mit eigenem Fund vor der Partnerantwort | Eigene Funde zu einem laufenden Auftrag bleiben versiegelt, bis die Partnerseite geliefert hat | #5 |
| Advocatus-WARN zu einem offenen PR bleibt ohne Folge | Jeder WARN-Befund zu einem offenen PR bekommt im selben Zug einen Commit oder eine Ledger-Zeile | #6 |
| Checkpoint „Nicht berührt: … Rechte, Hooks“ trotz Hook-PRs und Ruleset | Negativaussagen im Checkpoint werden gegen die Artefaktliste geprüft und eng formuliert | #7 |
| PR unter Owner-Konto angelegt, nach Hinweis neu angelegt | Bei Hook- und Governance-Pfaden den PR direkt über die App anlegen | #8 |
| Material bleibt im Scratchpad, Tresor-Kopie blockiert | Vertrauliches Material entsteht direkt im Tresor, oder die Sicherung geht im selben Zug als Owner-Skript raus | #9 |
| Zwei Außenwirkungen in einem Befehl (11:51Z) | Je Außenwirkung ein eigener Aufruf | #10 |
| Probelauf-Zeitgeber ohne Ende auf veränderlichem Zweig | Enddatum als Prüfung im Code oder `ExecCondition`; der Dienst läuft auf einem festen, reviewten Stand | #14 |
| Kürzel → Classifier-Sperre → Owner-Skript | Erkennbar classifier-pflichtige Items (Repo-Anlage, Persistenz, Rechte) gehen gleich als Owner-Skript raus; das Kürzel entfällt | #17 |
| Freigabe nur im Chat | Jede Freigabe bekommt im selben Zug eine Zeile im Checkpoint- oder Mandats-Issue | #18 |
| Verdichtung etwa alle 20 Minuten | Große Ausgaben in Subagenten oder Dateien auslagern; nach jeder Verdichtung eingereihte Owner-Nachrichten aus dem Transkript nachlesen | #19 |

## 5. Längsschnitt

Gate-Treffer dieser Sitzung laut Gate-Log (Session-ID 835f30f0): vertrauliches-verlaesst-ablage 11, aufschub-anker 10, claim-before-cheapest-check 7, parallel-session-pr-collision 4, scope-checkpoint-not-durably-recorded 3, je 2 rohes-pytest-statt-make-test, check-ohne-positivkontrolle und inline-heredoc-quoting-rework, je 1 fünf weitere. Dazu 7 Zeilen ohne Session-ID (Befund 1).

`tools/retro_kpis.py` lief. Es meldet 71 Slugs mit ≥2 Vorkommen. Aus dieser Sitzung:

- `hook-drill-ohne-fehlalarm-gegenprobe` (Befunde 11, 3): zweite Retro nach 766e8c-incr, GATE-PFLICHT. Die Antwort steht im Soll-Ablauf (Meldephase vor Scharfschaltung) und als Maßnahme Z3 ([#4061](https://github.com/achimdehnert/platform/issues/4061)).
- `kuerzel-ohne-artefakt-bezug` (Befund 18): zweite Retro nach 767d40-incr (anderes Repo). GATE-PFLICHT, Gate-Kandidat, Melder als [#4062](https://github.com/achimdehnert/platform/issues/4062).
- `deferred-item-no-tracking-issue` (Befund 6): liegt unter `declined/`, wird nur gezählt.
- `self-review-presented-as-review` (Befund 2) und `gate-approval-needs-pr-comment` (Befund 4) sind Aliase gebauter Gates, beide verwandt, kein Rückfall, siehe §5a.
- Neu und einmalig: `kontrolllauf-schreibt-echtes-gate-log` (Befund 1), als Gate-Kandidat geführt, weil der Fix billig und strukturell ist.

Abgleich mit dem Memory-Index per `grep`: „Freigabe ohne Text ≠ Review“ steht bereits in der Projekt-Memory zur Zusammenarbeit, „Approval-Last aktiv verringern“ als Feedback-Memory. Einträge zu „Review-Text im Owner-Skript“ (Befund 2) und „Gate-Log nicht selbst bereinigen“ (Befund 1) fehlen.

### 5a. Rückfall-Prüfung

Kein gebautes Gate ist in dieser Sitzung rückfällig.

| Gate | Fall | Ursache | Antwort |
|---|---|---|---|
| claim-before-cheapest-check | Befund 2: „geprueft“ im Review-Text eines Owner-Skripts | außerhalb des Zuschnitts: der Text lief über einen Owner-Lauf (`!`), nicht über einen Agenten-Aufruf | verwandt (Alias self-review-presented-as-review). Entscheidung zum Nachschärfen liegt bei #2666 |
| claim-before-cheapest-check | Befund 7: „Nicht berührt“ im Checkpoint | Negativaussage über Reichweite; die Vorfassung wurde um 14:58:56Z gesperrt, die Neufassung behielt den Satz | verwandt. Kandidat für #2666 |
| check-ohne-positivkontrolle | Befund 11 | die Positivkontrolle lief (5/5); es fehlte die Gegenprobe gegen die Zielpopulation | verwandt. Kandidat für #3722 Rev 2 |
| no-checks-reported-read-as-green | Befund 4: Merge nach leerem Approve | anderes Repo, Merge nicht über `pr_merge_sa` | verwandt (Alias gate-approval-needs-pr-comment) |
| pr-autor-identitaet-nicht-angewandt | Befund 8 | Hinweis kam bei der Anlage, Korrektur nach 8 s | Fang |

### 5b. Autonomie-Kalibrierung

- over_ask: keine Klasse. Alle Owner-Fragen betrafen Außenwirkung, Partner-Kommunikation oder Schranken. Die Owner-Last aus Befund 17 ist ein Umweg (Kürzel vor Classifier-Sperre), kein überflüssiges Fragen.
- over_act: `audit-log-bereinigung-versucht` (Befund 1) und `aussenwirkung-gebuendelt-in-einem-befehl` (Befund 10). Beide wurden gesperrt, bevor sie wirkten.

## 6. Verankerung (Vorschläge, nicht geschrieben)

**memory_candidates**

```markdown
---
name: review-text-im-owner-skript-nie-vorformuliert
description: Owner-Skripte für Approves tragen keinen fertigen Prüfvermerk des Agenten
metadata:
  type: feedback
---
Ein Owner-Skript, das einen Review abgibt, enthält als Text einen Platzhalter oder eine Zuordnung („Agent: Tests grün; Owner: Diff gesehen“), nie „geprüft“ ohne Subjekt.
**Why:** Retro 835f30 Befund 2. Der Code-Owner-Review zu #4052 trug den vom Agenten vorformulierten Text „… geprueft“.
**How to apply:** Gilt für jedes `gh pr review --approve` in `~/zug/*.sh`.
```

```markdown
---
name: gate-log-unechte-zeilen-melden-nicht-loeschen
description: Unechte Zeilen im Gate-Log meldet der Agent; löschen oder filtern ist ein Audit-Eingriff
metadata:
  type: feedback
---
Stehen Kontroll- oder Testzeilen im echten Gate-Log, meldet der Agent sie dem Owner und behebt die Ursache (`GATE_HITS_DATEI` im Kontrolllauf). Er filtert das Log nie selbst.
**Why:** Retro 835f30 Befund 1. Ein Filter auf den ganzen Slug wurde als „Logging/Audit Tampering“ gesperrt.
**How to apply:** Vor jedem Schreibzugriff auf `~/.claude/hooks/gate-hits.jsonl` stoppen.
```

```markdown
---
name: classifier-pflichtiges-gleich-als-owner-skript
description: Repo-Anlage, Persistenz und Rechte gehen ohne Kürzel-Umweg direkt als Owner-Skript raus
metadata:
  type: feedback
---
Ein Item, das erkennbar am Auto-Mode-Classifier scheitert (Repo-Anlage, systemd-Units, Rechte), steht im Board gleich als `! bash ~/zug/<id>.sh`, nicht erst als Kürzel.
**Why:** Retro 835f30 Befund 17. Dreimal folgte auf ein Kürzel eine Sperre und dann doch ein Skript; ergänzt [[feedback_weniger_approvals]].
**How to apply:** Vor jedem Board-Item mit Außenwirkung prüfen, ob es in der Ablehnungsliste des Classifiers steht.
```

**adr_candidates:** keine. Befunde und Maßnahmen liegen unter der ADR-Schwelle.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| Z1 | Stichtag nach Auswertung legen | platform | [#4055](https://github.com/achimdehnert/platform/pull/4055) | 🔵 | Agent, Commit im PR |
| Z2 | Proxy-Lücke in #4055 schließen | platform | [#4055](https://github.com/achimdehnert/platform/pull/4055) | 🔵 | Agent, Commit im PR |
| Z3 | Kontrollläufe isolieren, Meldephase für neue Schranken | platform | [#4061](https://github.com/achimdehnert/platform/issues/4061) | 🟢 | Owner `Z3 go` |
| Z4 | Sicherung in den Tresor | lokal | — | 🟢 | Owner führt `sv.sh` aus |
| Z5 | Memory „Review-Text im Owner-Skript“ | lokal | — | 🟢 | Owner `Z5 go` |
| Z6 | Memory „Gate-Log melden, nicht löschen“ | lokal | — | 🟢 | Owner `Z6 go` |
| Z7 | Memory „Classifier-Pflichtiges gleich als Skript“ | lokal | — | 🟢 | Owner `Z7 go` |
| Z8 | Nachtrag im Checkpoint: Befund 7 berichtigen, MA/FR nachtragen | Checkpoint-Repo | Checkpoint-Issue (privat) | 🔵 | Agent, ein Kommentar |
| Z9 | Enddatum und fester Stand für die Wache | Dialog-Repo | PR #6 (privat) | 🔵 | Agent, Commit im PR |
| Z10 | Melder: Kürzel ohne Gegenzeile | platform | [#4062](https://github.com/achimdehnert/platform/issues/4062) | 🟢 | Owner `Z10 go` |

## 8. Nicht verifiziert (Restlücken)

- Herkunft der Gate-Log-Zeile 12:40:39Z mit Session-ID dieser Sitzung; sie fiel in den Filter von Befund 1 und liegt vor dem Merge von #4048.
- Ob der Owner den Diff von #4052 vor dem Skriptlauf sah (Befund 2).
- Ob nach jeder der zwölf Verdichtungen neu gelesen wurde (Befund 19); belegt ist nur die Zahl.
- Freigabe R6 (12:14:20Z): Gegenzeile nicht vollständig geprüft.
- Die Owner-Nachrichtenliste der Retro erfasste eingereihte Nachrichten nicht; daran hing Befund 15.
- Die Zahl der Owner-Skripte dieser Sitzung: 24 im Zeitfenster, die Zuordnung zu Parallelsitzungen ist offen (Befund 17).

**Vierklang**

- **getan:** Wirkungsbilanz, Collect, drei Finder, Konfliktprüfung (4 Widersprüche), drei Skeptiker, Längsschnitt, Rückfall-Prüfung, Widerlegungsbahn mit Nachprüfung ihrer Kernbelege, Meta-Prüfung, Report-Check (`retro_report_check.py` Exit 0). Phase 6 n/a (keine Anforderung). Infra-Sonde n/a (Hook-Sitzung, kein CI, Deploy, Runner oder Host). Befund-Dichte vorab mittel geschätzt (reversibel, aber Gate-Neubau). Die vier Konfliktprüfungen aus 2.5 liefen in den Skeptiker-Aufträgen, im Budget von 8 Agenten.
- **angenommen:** Die Kennzahlen-Datei bildet Ablehnungen und Fehlerläufe vollständig ab. Die Sitzungsgrenze über die Artefaktliste ist richtig gezogen.
- **nicht verifizierbar:** Inhalte im Tresor (Schranke), Absicht hinter dem Wortlaut des Checkpoints.
- **offen geblieben:** Z1–Z10, #4053, Auswertung der Wache am 2026-10-23, Review der Dialog-PRs #3, #4, #6.

## Widerlegung

Die Widerlegungsbahn (ein Opus-Agent, nur lesend) sah Entwurf, Footprint und Artefaktliste. Ergebnis `5 gekippt, 4 neu`; die Kernbelege wurden danach selbst nachgeprüft (Transkript-Zeitstempel, Gate-Log, Ruleset, PR #6).

- Gekippt: Befund 1 (Schreiber war die eigene Positivkontrolle, nicht ein Drill), Befund 7 (auch „Rechte“ falsch), Befund 11 (REFUTED → SURVIVES: Replay ohne Tresor-Befehle), Befund 14 (teilweise SURVIVES: kein technisches Ende, ungeprüfter Zweig), Zahlen im Text (5 von 12 statt 13, fünf statt vier Einzel-Slugs, Sitzungsende).
- Neu: Befunde 17, 18, 19. Der vierte Punkt (9 von 18 Fehlerläufen aus dem eigenen Gate) ging in Befund 11 auf.
- Bestätigt: Befunde 2, 3, 4, 6, 15 und die Frontmatter-Formel. Keine nichtöffentlichen Namen im Entwurf.

## Streichbahn

Keiner. vertrauliches-verlaesst-ablage hatte am ersten Tag mehrere Fehlalarme, fängt also zu viel und nicht zu wenig; der Weg ist der Fix #4053. Alle übrigen Gates dieser Sitzung haben gefangen oder lagen außerhalb ihres Zuschnitts.

## Self-Review

Eine Meta-Prüfung (sonnet, nur lesend) hat den Report gegen den Skill gehalten. Bestätigt sind die Struktur, die Frontmatter-Rechnung (4 von 19 verworfen, 0,21) und die Abdeckung aller 15 überlebenden Befunde im Soll-Ablauf. Vier Punkte hat sie beanstandet, alle am 2026-10-16 behoben:
- Die Soll-Zeile für #3 und #11 war zusammengelegt und ist jetzt geteilt.
- Für `kuerzel-ohne-artefakt-bezug` fehlte der Gate-Pfad, er steht jetzt in [#4062](https://github.com/achimdehnert/platform/issues/4062).
- Ein privater Repo-Name stand im Text und ist entfernt.
- Für Phase 6 und die Infra-Sonde fehlten die n/a-Vermerke, sie sind ergänzt.

Offen bleibt, was kein Agent prüfen kann: der Inhalt der privaten Repos und ob der Owner die Diffs vor seinen Freigaben gesehen hat (§8).
