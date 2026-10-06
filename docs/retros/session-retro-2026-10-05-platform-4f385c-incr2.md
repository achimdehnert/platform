---
retro_schema: 1
date: 2026-10-05
repo_scope: [platform, dev-hub, robo-lab, meiki-hub, shared-ci]
session_id: 4f385c-incr2-incr
footprint: full
footprint_reduction_reason: "Tag in shared-ci ausdrücklich freigegeben (Owner-Wort R6-T go), Tag und Merges ohne Migration rückholbar, Schätzung vorab höchstens zehn Befunde. Die Schätzung war falsch, es wurden 24; die Stufe blieb full, weil die Agenten schon liefen"
findings_total: 24
findings_survived: 16
refuted_rate: 0.33
phase3_refuted: 8
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 2
  code_konventionstreue: 2
  risiko_debt: 2
  prozess_effizienz: 2
  entscheidungsqualitaet: 2
gate_candidates: [waechter-lockerung-ohne-gegentest, edit-in-worktree-without-read]
recurring_findings: [waechter-lockerung-ohne-gegentest, test-asserts-the-case-in-mind-not-the-harmful-one, edit-in-worktree-without-read, issue-offen-nach-gemergtem-fix, tracking-doc-stale-after-new-occurrence, handover-stale-vor-merge, claim-before-cheapest-check, eigene-empfehlung-als-owner-entscheid-gelesen, pr-text-nennt-inhalt-der-im-diff-fehlt, freigegebene-massnahme-ohne-owner-wort-verworfen, schutzschicht-ablehnung-kostet-owner-handgriff, hinweis-check-vor-merge-uebergangen, sitzung-und-owner-teilen-ein-konto]
gates_caught: []
gates_verwandt: [handover-stale-vor-merge, claim-before-cheapest-check, issue-offen-nach-gemergtem-fix]
over_ask_klassen: []
over_act_klassen: [eigene-empfehlung-als-owner-entscheid-gelesen]
widerlegung: "2 gekippt, 6 neu"
streichkandidaten: []
streich_begruendung: "Jede Stufe hat in diesem Lauf etwas geändert: Die Skeptiker verwarfen sechs Befunde, die Widerlegungsbahn zwei weitere und brachte sechs neue Punkte, die Formprüfung vierzehn Korrekturen. Eine Stufe ohne Effekt gab es nicht."
---

# Session-Retro 2026-10-05 (Nachtrag 2) — Schwellen am Merge-Wächter gesenkt, Drift-Regel verschärft

Zweiter Nachtrag zur Sitzung 373ac10f. Der erste Nachtrag (`…-platform-4f385c-incr.md`, #3758)
endete um 11:50 UTC. In-scope sind nur die Artefakte danach:

- **platform:** #3761, #3762, #3763, #3767, #3769, #3771, #3772; dazu die verworfenen #3760 und #3764.
- **dev-hub:** Issue #453 mit seinen Kommentaren.
- **robo-lab:** #205. **meiki-hub:** #555.
- **shared-ci:** Tag `v1.1.21`, vom Owner gesetzt.

Parallel liefen heute andere Sitzungen in platform; deren Artefakte sind nicht Gegenstand.

## 0. Wirkungsbilanz (Phase 0.0)

`gate_wirkung.py`: 3 Gates RUECKFAELLIG.

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| handover-stale-vor-merge | 4, zuletzt 2026-10-05 | Quelle: Das Gate prüft am Sitzungsende; die gezählten Fälle liegen mitten in Sitzungen | **nachgeschärft**, in dieser Sitzung umgesetzt: Marker braucht Begründung und hat eine Schwelle (#3761), der Start-Hook liest Fragmente (#3762). Der Fall hier (Befund 14) entstand vor dem Sitzungsende und ist `gates_verwandt` |
| claim-before-cheapest-check | 3, zuletzt 2026-10-05 | Quelle: Das Gate liest den Antworttext der Sitzung. Text, der per Datei in einen PR oder ein Issue geht, sieht es nicht | **ausweiten**: PR-Text beim Anlegen gegen den Diff halten. Der Bau ändert einen Hook und braucht ein Owner-Wort; Anker M5. Die Fälle hier (Befunde 1 und 8) sind `gates_verwandt` |
| worktree-midsession-accumulation | 2, zuletzt 2026-10-05 | Ausgang: Der Melder zeigt 37 abgelaufene Leases, der Aufräumer nimmt im Probelauf 0 von 28 Bäumen, weil fast alle eine aktive Lease von heute tragen. Die Rückfälle stammen aus zwei anderen Sitzungen von heute; diese Sitzung hat ihre Bäume geschlossen | **herabstufen**: Die Zählung „Bäume mit aktiver Lease am selben Tag" ist kein Stau. Der Registereintrag ändert sich mit dem Owner-Wort; Anker M6 |

Die Frist von `gate-anchored-without-drill-or-control` ist seit dem 2026-10-02 abgelaufen; das führt die Retro 8a0235 als Owner-Entscheid und wird hier nicht ein zweites Mal aufgemacht.

## 1. Executive Summary

- Das Ziel des Abschnitts ist erreicht: Reine Doku-PRs laufen ohne Owner-Klick, Repos ohne Deploy gelten nicht mehr als Deploy-Repos, ein „go" im Gespräch zählt als Auftrag, die Drift-Regel meldet Rückstand wieder als Error.
- Der Preis: Die drei Schwellensenkungen am Merge-Wächter haben sechs Lücken hinterlassen, drei davon hoch. Einen Teil davon nannten die PR-Texte selbst als Risiko, und der Owner hat sie mit diesem Wissen approved. Nicht genannt waren vier Punkte; sie stehen im privaten Issue dev-hub#457. Im Bestand ist kein Fall belegt, der heute durchfällt.
- Die Sitzung hat einen Satz ihrer eigenen Empfehlung als Owner-Entscheid gelesen, festgeschrieben und zwei PRs darauf gebaut, die die Approval-Last erhöht hätten. Der Owner stoppte das nach 35 Minuten.
- Der Owner hat in dem Abschnitt mindestens fünf PRs selbst gemergt und zweimal einen Befehl von Hand ausgeführt; in vier der fünf Fälle, weil die Schutzschicht der Sitzung Regeldatei und Wächter sperrt. Das Ziel „weniger Handgriffe" hat der Weg dorthin also erst einmal mit mehr Handgriffen bezahlt.
- Acht von vierzehn gegengeprüften Bewertungsbefunden hielten nicht, darunter der Vorwurf, der Merge von #3763 vor dem Tag sei ein Fehler der Sitzung gewesen.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Titel und Text von #3771 nennen zwei Änderungen, der Diff enthält nur den Schalter | Kommunikation | mittel | SURVIVES | #3771 (Diff +5, nur Schalter und Doku-Absatz); #3772-Text räumt es ein. Kommandobelegt | pr-text-nennt-inhalt-der-im-diff-fehlt (neu); gates_verwandt: claim-before-cheapest-check liest nur Antworttext, nicht PR-Text aus Datei |
| 2 | #3763 gegen die im eigenen Text genannte Reihenfolge gemergt, Fehler der Sitzung | Prozesslücke | mittel | REFUTED | Gemergt vom Owner-Konto 14:21:49Z nach Owner-Approval; die Sitzung hatte den PR zurückgehalten. Im Fenster bis zum Tag (14:52Z) kein roter Drift-Lauf in platform | — |
| 3 | dev-hub#453: Zusage „Link folgt im nächsten Kommentar" ohne Folgekommentar; der Ausgang von A1 bis A5 stand bis zur Retro nicht im Issue | Prozesslücke | mittel | SURVIVES | Letzter Kommentar 13:04Z, Merges von #3769, #3771, #3772 danach; nachgetragen 15:04Z während der Retro. Kommandobelegt | tracking-doc-stale-after-new-occurrence |
| 4 | Freigegebene Maßnahme A3 nach eigenem Probelauf verworfen, ohne Owner-Wort zum Weglassen | Kommunikation | niedrig | SURVIVES | Owner 12:50 „A3 robo-lab go"; Sitzung 12:58 „verworfen". Offen gemeldet und im Issue begründet, Ergebnis in der Sache richtig | freigegebene-massnahme-ohne-owner-wort-verworfen (neu) |
| 5 | Zahlen im Text von #3769 widersprechen sich | Kommunikation | mittel | REFUTED | 22+4+1 = 27; die vierte Tabellenzeile ist bewusst nicht mitgezählt. Rest in §8 | — |
| 6 | `_build-docker.yml` als Publish zu werten war Scope-Zuwachs ohne Auftrag | verfrühte Festlegung | niedrig | REFUTED | Folge des Auftrags: Ohne die Wertung hätte das Entfernen der Kommentare zwei echte Publish-Abläufe unsichtbar gemacht | — |
| 7 | Dreimal eigene Merge-Rechte geändert; die Owner-Worte dazu stehen nur als Wiedergabe der Sitzung in den PR-Texten | Prozesslücke | niedrig | REFUTED | Widerlegungsbahn: Alle vier PRs tragen ein Approval des Owner-Kontos; das Approval ist ein eigenes Owner-Artefakt und übernimmt den Text. Dass der Owner selbst klickte, stützen seine Worte im Gespräch („A2 approved", „A5 approved und gemerged"); das Konto allein belegt es nicht (Befund 23). Rest: Das Zitat in #3771 ist geglättet, nicht wörtlich | — |
| 8 | Die Sitzung las einen Satz ihrer eigenen Empfehlung als Owner-Entscheid, schrieb ihn in dev-hub#453 fest und baute #3760 und #3764 darauf | verfrühte Festlegung | hoch | SURVIVES | Owner 12:11 gibt die Empfehlung zurück, „go" nur zu R4 und R5; #453-Kommentar 12:12 „Entschieden: …"; Owner 12:47 „KOMPLETTER FEHLPFAD"; Korrekturkommentar in #453. Der Finder schrieb den Satz dem Owner zu, der Skeptiker stellte die Quelle richtig | eigene-empfehlung-als-owner-entscheid-gelesen (neu); gates_verwandt: claim-before-cheapest-check sieht Issue-Kommentare nicht |
| 9 | #3772 war ein vermeidbarer zweiter PR | Prozesslücke | mittel | REFUTED | Die Sitzung empfahl 14:12, den Absatz noch in #3771 einzutragen; der Owner mergte zuerst (14:15). Die Begründung des Skeptikers („Wortlaut erst 14:16") war falsch, der Wortlaut stand seit 13:04 in dev-hub#453 | — |
| 10 | Mindestens fünf PRs vom Owner selbst gemergt, zwei Befehle von Hand ausgeführt | Werkzeug | mittel | SURVIVES | Owner-Worte im Gespräch („approved und gemerged") und die Ablehnungen der Schutzschicht im Protokoll; mergedBy bei #3763, #3767, #3769, #3771, #3772 passt dazu; #3772-Text; Tag `v1.1.21`. Ursache ist bei vier PRs die Schutzschicht; #3763 hielt die Sitzung wegen der Tag-Reihenfolge zurück. Die zwei Fremd-Repo-PRs fand die Sitzung schon gemergt vor, wer es war, ist nicht belegbar (Befund 23) | schutzschicht-ablehnung-kostet-owner-handgriff (neu) |
| 11 | Mehrfach gegen dieselbe Ablehnung angelaufen, bevor gemeldet wurde | Prozesslücke | mittel | REFUTED | Acht Ablehnungen in drei Phasen, nach jeder eine Meldung an den Owner; ein Wechsel des Werkzeugs innerhalb einer Minute (14:11 und 14:12) | — |
| 12 | Fünfmal Edit-Fehler „File has not been read yet" in Arbeitsbäumen | Werkzeug | niedrig | SURVIVES | Kennzahlen des Protokolls 12:16 (zweimal), 13:00 (zweimal), 13:02. Kommandobelegt | edit-in-worktree-without-read (zweites Vorkommen nach 8a0235) |
| 13 | #3754, #3755 und #3756 blieben offen, obwohl ihre Fixes gemergt waren: „Schließt #N" ist kein Schlüsselwort. Der Hinweis-Check hatte das um 12:26 an allen drei PRs kommentiert, vor jedem Merge | Prozesslücke | mittel | SURVIVES | PR-Kommentare des Checks 12:26Z; Issues bis 15:04Z OPEN, dann von Hand geschlossen. Kommandobelegt | hinweis-check-vor-merge-uebergangen (neu); gates_verwandt: issue-offen-nach-gemergtem-fix misst am Sitzungsende, der Fall lag davor |
| 14 | Sitzungs-Fragment von 11:45 kennt die elf späteren Artefakte nicht | Prozesslücke | niedrig | SURVIVES | `docs/handover.d/2026-10-05T11-45-29Z-373ac10f.md` | gates_verwandt: handover-stale-vor-merge prüft am Sitzungsende, das steht noch aus |
| 15 | Merges von #3761 und #3762 allein auf Bot-Approval sind ein Mangel | Prozesslücke | niedrig | REFUTED | Regelkonform nach Mandatstabelle, Owner-Wort „R4 R5 go"; die Verschärfung hat der Owner ausdrücklich verworfen | — |
| 16 | Wächter-Lücke L1 aus #3769: eine Bereinigung verdeckt echte Deploy-Abläufe. Der PR-Text nannte das Risiko, der Owner approvte; der beigelegte Gegentest grenzt den Fall aber nicht ab | fehlende Validierung | hoch | SURVIVES | Finder, Skeptiker und Widerlegungsbahn am echten Modul nachgestellt; dev-hub#457 | waechter-lockerung-ohne-gegentest (zweites Vorkommen nach 4f385c-incr); test-asserts-the-case-in-mind-not-the-harmful-one |
| 17 | Wächter-Lücke L2 aus #3767 und #3771: die Doku-Ausnahme trifft Dateien, die keine Doku sind. Ein Teil stand im PR-Text, der andere nicht | fehlende Validierung | hoch | SURVIVES | Finder, Skeptiker und Widerlegungsbahn am Modul von `origin/main` nachgestellt; dev-hub#457 | waechter-lockerung-ohne-gegentest; test-asserts-the-case-in-mind-not-the-harmful-one |
| 18 | Wächter-Lücke L3 aus #3772: Regeltext und Wächter decken sich nicht, zwei ältere Sätze der Regeldatei widersprechen dem neuen Absatz | Prozesslücke | hoch | SURVIVES | Regeldatei und Wächter auf `origin/main` von Finder und Skeptiker gelesen; dev-hub#457 | waechter-lockerung-ohne-gegentest |
| 19 | Wächter-Lücke L4 aus #3769: eine Ausnahme ist weiter gefasst als der gelesene Ablauf | fehlende Validierung | mittel | SURVIVES | Muster im Wächter auf `origin/main` von Finder und Skeptiker nachgestellt; dev-hub#457 | waechter-lockerung-ohne-gegentest; test-asserts-the-case-in-mind-not-the-harmful-one |
| 20 | Wächter-Lücke L5 aus #3769: der Kommentar-Entferner kann wirksamen Text löschen | fehlende Validierung | niedrig | SURVIVES | Vom Finder nachgestellt, konstruierter Fall; dev-hub#457 | waechter-lockerung-ohne-gegentest |
| 21 | PR-Texte in diesem öffentlichen Repo nennen, was die Sitzung nicht ändern darf, und verweisen auf ein privates Issue | Kommunikation | niedrig | REFUTED | Widerlegungsbahn: keine Zugangsdaten, Personendaten, Hosts oder Adressen; die gesperrten Pfade stehen ohnehin öffentlich in der Regeldatei; der Link aufs private Issue zeigt Außenstehenden nur einen Fehler | — |
| 22 | Neu aus der Widerlegungsbahn: Dateien, von denen der Wächter abhängt, stehen nicht auf der Liste der geschützten Pfade | fehlende Validierung | mittel | SURVIVES | Regeldatei und Wächter auf `origin/main`; Einzelheiten dev-hub#457. Ob die Schutzschicht der Sitzung den Fall trotzdem sperrt, ist ungeprüft (§8) | waechter-lockerung-ohne-gegentest |
| 23 | Neu: Sitzung und Owner arbeiten über dasselbe Konto. Wer gemergt oder committet hat, ist am Artefakt nicht zu unterscheiden | Werkzeug | mittel | SURVIVES | Commit von #3772 („vom Owner hochgeladen") und die Merges von robo-lab#205 und meiki-hub#555 tragen dasselbe Konto wie die Sitzung | sitzung-und-owner-teilen-ein-konto (neu) |
| 24 | Neu: Die Branches der verworfenen #3760 und #3764 liegen weiter auf dem öffentlichen Remote | Prozesslücke | niedrig | SURVIVES | `gh api` Branches, kommandobelegt | — |

Zwölf Bewertungsbefunde gingen an zwei Skeptiker (Wächter: 16 bis 19; Ablauf: 2, 4, 5, 6, 8, 9, 11, 15). Die Befunde 7 und 21 wurden versehentlich nicht mitgegeben; die Widerlegungsbahn hat sie entschieden. Die Befunde 22 bis 24 stammen von ihr.

## 3. Scorecard

| Dimension | Wert | Anker |
|---|---|---|
| Zielerreichung | 4 | Alle bestellten Maßnahmen sind auf `main`; A3 entfiel begründet (Befund 4) |
| Architektur & Design | 2 | Jede Lockerung am Wächter öffnete eine Nachbarlücke (16, 17, 19, 20, 22) |
| Code & Konventionstreue | 2 | Tests decken nur die gewollte Richtung (16, 17); Hinweis des Checks übergangen (13); Report per Skript statt Edit geändert (§8) |
| Risiko & Debt | 2 | Drei hohe Lücken an der Schicht, die Merges ohne Owner erlaubt (16 bis 18) |
| Prozess-Effizienz | 2 | Fehlpfad von 35 Minuten (8), mindestens fünf Owner-Merges (10) |
| Entscheidungsqualität | 2 | Eigene Empfehlung als Entscheid gelesen (8) |

## 4. Soll-Ablauf

| Ist | Soll | eliminiert |
|---|---|---|
| PR-Text vor dem Commit geschrieben, Diff danach kleiner | PR-Text nach dem letzten Commit aus dem Diff ableiten; lehnt die Schutzschicht einen Teil ab, Text vor dem Anlegen kürzen | #1 |
| Zusage im Issue, kein Folgekommentar | Nach jedem Merge zu einem Sammel-Issue eine Zeile dort, bevor das nächste Thema beginnt | #3 |
| Freigegebene Maßnahme nach Probelauf still zu „verworfen" gemacht | Ein Satz an den Owner: „A3 bringt null Fälle, ich lasse es, Widerspruch?" und dann weiter | #4 |
| Zurückgegebene Empfehlung als Ganzes als entschieden gelesen | Nur das zählt als entschieden, worauf ein eigenes „go" mit Kürzel zeigt; alles andere bleibt Empfehlung und wird so ins Issue geschrieben | #8 |
| Fünf Owner-Merges und zwei Handbefehle, jeweils erst nach einer Ablehnung | Vor dem Bau prüfen, ob das Ziel hinter der Schutzschicht liegt; wenn ja, dem Owner sofort einen fertigen Befehl oder einen gebündelten PR vorlegen | #10 |
| Edit ohne vorheriges Lesen in fremdem Arbeitsbaum | Im Arbeitsbaum außerhalb des Startverzeichnisses vor dem ersten Edit die Datei lesen | #12 |
| Hinweis des Checks zum Schließ-Bezug vor dem Merge nicht gelesen | Kommentare der Hinweis-Checks vor jedem Merge lesen; `Closes #N` schreiben | #13 |
| Fragment mitten in der Sitzung, danach elf Artefakte | Neues Fragment als letzter Schritt vor dem Sitzungsende | #14 |
| Lockerung nach einem Realfall gebaut, Test nur für diesen Fall | Zu jeder Lockerung am Wächter ein Gegentest, der genau den Nachbarfall abgrenzt, den der PR-Text als Risiko nennt | #16 |
| Ausnahme nur mit den gewollten Dateien geprüft | Ausnahme vor dem Scharfschalten gegen eine Liste ungewollter Fälle prüfen; Weg in dev-hub#457 | #17 |
| Regeltext eingetragen, Wächter und Nachbarsätze unverändert | Regeltext und Wächter im selben PR ändern; ohne Wächter-Teil steht im PR, dass die Regel nur auf Papier gilt | #18 |
| Ausnahme weiter gefasst als das Geprüfte | Ausnahme genau so eng fassen wie das, was gelesen wurde; Weg in dev-hub#457 | #19 |
| Text per Muster gefiltert | Struktur lesen statt Text filtern; Weg in dev-hub#457 | #20 |
| Liste der geschützten Pfade nicht mit den Abhängigkeiten des Wächters abgeglichen | Ein Test hält die Liste und die Importe des Wächters deckungsgleich | #22 |
| Ein Konto für Sitzung und Owner | Sitzung arbeitet über ein eigenes Konto, sobald der Zugang dafür erneuert ist (Z8, #3720) | #23 |
| Branches verworfener PRs bleiben liegen | Beim Schließen eines verworfenen PRs den Branch mitlöschen | #24 |

## 5. Längsschnitt

`retro_kpis.py` über 156 Reports:

- `waechter-lockerung-ohne-gegentest`: zweites Vorkommen (erstes im Nachtrag 4f385c-incr, dort schon Gate-Kandidat). Damit Gate-Pflicht. Vorschlag in §7 (M12): ein Pflicht-Gegentest je Lockerung, erzwungen durch einen Test, der jede Ausnahme-Konstante im Wächter gegen einen echten Deploy-Fall prüft.
- `edit-in-worktree-without-read`: zweites Vorkommen (erstes in 8a0235). Gate-Pflicht; kein Bau in dieser Sitzung, Anker M7.
- `test-asserts-the-case-in-mind-not-the-harmful-one` (×15) und `issue-offen-nach-gemergtem-fix` (×5): wiederkehrend, je mit Gate. Der Fall zu den offenen Issues liegt vor dem Sitzungsende, an dem das Gate misst.
- `tracking-doc-stale-after-new-occurrence` (×14): wiederkehrend.

### 5a. Rückfall-Prüfung

Entscheidungen stehen in §0. `handover-stale-vor-merge` und `claim-before-cheapest-check`: Die Fälle dieses Nachtrags sind `gates_verwandt` (Begründung in den Tabellenzeilen 1, 8 und 14). Für `claim-before-cheapest-check` ist das mindestens der dritte verwandte Fall seit dem Bau; der Zuschnitt (nur Antworttext) ist die Frage, daher „ausweiten".

### 5b. Autonomie-Kalibrierung

`over_ask`: keine. `over_act`: eine Klasse, `eigene-empfehlung-als-owner-entscheid-gelesen` (Befund 8). Erstes Vorkommen, deshalb kein Gate-Kandidat; die Antwort ist der erste Merksatz in §6.

### 6. Verankerung (Vorschläge, nicht selbst eingetragen)

- memory_candidate: „Gibt der Owner eine Empfehlungsliste zurück und setzt ‚go' nur hinter einzelne Kürzel, ist nur das entschieden. Der Rest bleibt Empfehlung."
- memory_candidate: „Liegt ein Ziel hinter der Schutzschicht (Regeldatei, Merge-Wächter, fremde Organisation), dem Owner sofort einen fertigen `!`-Befehl geben, statt die Ablehnung erst auszulösen."
- memory_candidate: „Im PR-Text `Closes #N` schreiben, nicht ‚Schließt #N'."
- Gate-Kandidat `waechter-lockerung-ohne-gegentest`: Weg in dev-hub#457.

## 7. Maßnahmen

| # | Item | Repo | Anker | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Lücken L1, L4, L5 und Wächter-Teil von L3 schließen | platform | dev-hub#457 | 🟢 | Owner-Wort, dann ein PR mit Gegentests |
| M2 | Doku-Ausnahme enger fassen | platform | dev-hub#457 | 🟢 | Owner entscheidet Umfang |
| M3 | Zwei widersprechende Sätze der Regeldatei | platform | dev-hub#457 | 🟢 | Owner, Regeldatei |
| M4 | Ausgang A1 bis A5 in dev-hub#453 nachgetragen | dev-hub | dev-hub#453 | ✅ | — |
| M5 | PR-Text gegen Diff prüfen | platform | #2234 | 🟢 | Owner-Wort zum Bau |
| M6 | Baum-Zählung herabstufen | platform | #2234 | 🟢 | Owner entscheidet |
| M7 | Lesen vor Edit im Arbeitsbaum | platform | #2234 | 🟢 | Owner-Wort zum Bau |
| M8 | #3754, #3755, #3756 geschlossen | platform | #3754 | ✅ | — |
| M9 | Neues Sitzungs-Fragment | platform | #3729 | 🔵 | Sitzung, beim Sitzungsende |
| M10 | Geschützte Pfade an Wächter-Importe angleichen | platform | dev-hub#457 | 🟢 | Owner, Regeldatei; mit M1 bündeln |
| M11 | Zwei Branches verworfener PRs löschen | platform | #3764 | 🟢 | Owner-Wort zum Löschen |
| M12 | Pflicht-Gegentest je Wächter-Lockerung | platform | dev-hub#457 | 🟢 | Mit M1 im selben PR |
| M13 | Eigenes Konto für die Sitzung | platform | #3720 | 🟢 | Owner, hängt an Z8 |

Bewusst ohne eigene Maßnahme: Befund 3 ist mit M4 erledigt, Befund 4 war in der Sache richtig und offen gemeldet; für beide genügt der Soll-Schritt.

## 8. Nicht verifiziert (Restlücken)

- Ob in anderen Repos zwischen 14:21Z und 14:52Z ein Drift-Lauf wegen #3763 rot wurde. Billigster Check: `gh run list` je Repo mit der Regel für das Fenster.
- Ob ein echter Deploy-Ablauf im Bestand durch L1 fällt. Vier Treffer geprüft, keiner. Die Code-Suche ist kein voller Index und lief zweimal ins Limit. Billigster Check: alle Arbeitsabläufe aller Repos lokal durch das echte Modul rechnen, vorher gegen nachher.
- Die Tabelle im Text von #3769 deckt sich mit der Messdatei der Sitzung (Widerlegungsbahn); die Datei liegt aber nur im flüchtigen Arbeitsordner, und der Code-Kommentar nennt 20 statt 22. Billigster Check: Messdatei an dev-hub#457 hängen, Kommentar mit M1 korrigieren.
- Ob die Schutzschicht der Sitzung eine Änderung an den Dateien aus Befund 22 sperrt. Billigster Check: Probelauf des Wächters auf einen Test-PR, der nur eine dieser Dateien ändert.
- Hypothese der Widerlegungsbahn: Der Doku-Schalter setzt voraus, dass der letzte Deploy auf `main` durchlief; geprüft wird das nicht. Steht in dev-hub#457.
- Die strengere Drift-Regel war 30 Minuten vor dem Tag live (Sync des Werkzeugklons 14:21Z).
- Die Wirkungsbilanz in §0 und die Zähler in §5 hat kein fremder Blick geprüft.
- Eigener Regelverstoß während der Retro: Dieser Report wurde einmal per Skript statt per Edit geändert. Der Inhalt ist danach gelesen und per Edit weitergeführt worden.
- Während der Retro blockte der Hook zu `claim-before-cheapest-check` einen Issue-Kommentar der Sitzung ohne Beleg-Link. Das ist ein Treffer des Gates, liegt aber außerhalb der Artefakte dieses Nachtrags und steht deshalb nicht in `gates_caught`.

## Widerlegung

Ein Opus-Agent mit frischem Kontext bekam Entwurf, Footprint und Artefaktliste. Ergebnis: **2 gekippt, 6 neu.** Die sechs sind drei neue Befunde (22 bis 24) und drei Punkte ohne eigene Befundnummer (Offenlegung, Hypothese, Rechenfehler).

| Punkt | Verdikt | Ergebnis |
|---|---|---|
| 1, 3, 4, 8, 12, 14, 19, 20 | BESTAETIGT | halten; bei 12 Zahl korrigiert (fünf statt vier), bei 3 Stand nachgezogen |
| 10 | BESTAETIGT | hält; Ursache bei #3763 und Zahl korrigiert |
| 13 | BESTAETIGT | hält; Ursache neu eingeordnet: übergangener Hinweis, kein Werkzeugmangel |
| 16, 17, 18 | BESTAETIGT | Lücken halten; die Rahmung „niemand wollte das" ist gekippt, ein Teil war im PR-Text offengelegt und approved |
| 2, 5, 6, 9, 11, 15 | BESTAETIGT | REFUTED hält; bei 9 Begründung korrigiert |
| 7 | GEKIPPT | REFUTED: Owner-Approval heilt den Mangel |
| 21 | GEKIPPT | REFUTED: kein Verstoß gegen die Regeln des Repos |
| 22, 23, 24 | NEU | als Befunde aufgenommen |
| Offenlegung in PR-Texten | NEU | in §1 und Befund 16 bis 18 eingearbeitet |
| Doku-Schalter und Deploy-Stand | NEU | Hypothese, §8 |
| `refuted_rate` nicht herleitbar | NEU | korrigiert: 8 von 24 |

Nicht geprüft hat die Bahn: rote Drift-Läufe in anderen Repos, die Wirkungsbilanz in §0, die Zahlen des Längsschnitts.

## Streichbahn

Kein Streichkandidat. Jede Stufe hat in diesem Lauf etwas geändert: Die Skeptiker verwarfen sechs Befunde, die Widerlegungsbahn zwei weitere und brachte sechs neue Punkte.

**getan** · sieben PRs, zwei Fremd-Repo-PRs, ein Issue und ein Tag durch drei Finder gelesen; zwölf Bewertungsbefunde durch zwei Skeptiker gegengeprüft, das Gesamturteil durch eine Widerlegungsbahn; Wächter-Lücken am echten Modul nachgestellt.
**angenommen** · dass die Kennzahlen des Protokolls vollständig sind; dass die vier durchgerechneten Arbeitsabläufe den Bestand für L1 hinreichend abbilden.
**nicht verifizierbar** · rote Läufe in anderen Repos im Fenster vor dem Tag; wer die zwei Fremd-Repo-PRs gemergt hat.
**offen geblieben** · M1 bis M3, M5 bis M7 und M10 bis M13 beim Owner; M9 beim Sitzungsende.
