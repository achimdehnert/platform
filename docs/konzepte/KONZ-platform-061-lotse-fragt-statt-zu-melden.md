---
concept_id: KONZ-platform-061
title: Der Lotse fragt statt zu melden — Befund wird Vorschlag, Daumen wird Freigabe
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: []            # keine SoR-Spec; Erweiterung der Raum-Grammatik (KONZ-059) um einen zweiten Antwortweg
adr_threshold: kein ADR   # neue Konvention in einem Repo (chat-hub) plus ein Leser in platform; kein neuer SSoT, keine neue Datenquelle. Der Freigabe-Perimeter wird NICHT erweitert (Prod/Publish bleiben ausgeschlossen), deshalb kein Charta-Entscheid nötig — Charta Art. 2 bleibt wörtlich in Kraft.
review_by: 2026-11-15
kill_criteria: "Wenn bis 2026-11-03 (28 Tage nach Bau) weniger als 5 Fragen des Lotsen beantwortet wurden ODER auch nur eine Reaktion einen Vorgang ausgelöst hat, den der Owner so nicht wollte (falscher Vorgang, falsche Klasse, doppelte Auslösung), wird der Reaktionsweg abgeschaltet (ein Schalter in der Wache) und der Lotse fragt weiter, aber die Antwort ist wieder nur das geschriebene Wort."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: chat-hub/deploy/lotse_auftrag.py, commit_or_pr: "pruefe_go() Z.141-171: Entwurf muss eigene Lotse-Nachricht sein, go-Event muss Owner-TEXT sein (audio wird ausdruecklich abgelehnt), unverbraucht, Wort ^go\\b, zeitlich NACH dem Entwurf", opened_in_session: true}
  - {claim_id: C2, source_path: chat-hub/deploy/chat_lotse.py, commit_or_pr: "_room_events(): nur RoomMessage, Audio-Subtypen, MegolmEvent — m.reaction wird NICHT in den Eingang gereicht; Senden von Reaktionen existiert (build_reaction_content, cmd_react)", opened_in_session: true}
  - {claim_id: C3, source_path: "~/.venvs/chat-lotse (matrix-nio)", commit_or_pr: "nio.ReactionEvent vorhanden, traegt key + reacts_to (gemessen 2026-09-22)", opened_in_session: true}
  - {claim_id: C4, source_path: docs/konzepte/KONZ-platform-059-auftragsraum-lernschleife-chat.md, commit_or_pr: "Backlog-Zeile 2: Reaktion statt Kommandosprache ausdruecklich als Alternative notiert (#3049, #3079); Backlog-Zeile 4: Kennzahlen in die Morgen-Meldung statt eigener Lauf", opened_in_session: true}
  - {claim_id: C5, source_path: chat-hub/deploy/lotse_briefing.sh, commit_or_pr: "headless claude -p mit enger Werkzeug-Erlaubnisliste, systemd-Zeitgeber werktags 07:00 Europe/Berlin — der vorhandene Weg fuer eine taegliche Nachricht in den Raum", opened_in_session: true}
  - {claim_id: C6, source_path: tools/befund_journal.py, commit_or_pr: "--bericht/--json: Befunde des Sitzungsstarts mit Alter, Anker, Verzicht; Quelle der Vorschlaege", opened_in_session: true}
  - {claim_id: C7, source_path: docs/konzepte/KONZ-platform-060-lotse-stimme-im-raum.md, commit_or_pr: "P1 dort als Out-of-Scope geführt, Owner-Freigabe 2026-09-22 fuer diesen Zuschnitt (fragen + Daumen)", opened_in_session: true}
created: 2026-09-22
---

# KONZ-platform-061 — Der Lotse fragt statt zu melden

> **Selbstbetreffend** (Charta Art. 3): Der Lotse bekommt eine eigene Stimme im Ablauf
> (er eröffnet Vorgänge, statt nur zu antworten) und einen zweiten Freigabeweg.
> Owner-Entscheid 2026-09-22: beides, mit den Grenzen unten.

## Kernthese

Die Befunde existieren längst und niemand liest sie im Alltag; die Freigabe existiert längst
und kostet einen getippten Satz. Beides zusammen ist ein Vorschlag, den ein Daumen erledigt —
**ohne neue Datenquelle und ohne neuen Freigabe-Perimeter**: Die Reaktion ist von sich aus an
den Entwurf gebunden (`reacts_to`, C3) und damit ein *engeres* Signal als das heutige „go",
das nur zeitlich hinter dem Entwurf stehen muss (C1).

## Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| A1 | Die Wache reicht Reaktionen heute nicht durch — `_room_events` kennt nur Text, Audio, Megolm | Annahme | C2. Falsifikation: eine Reaktion des Owners erzeugt eine Eingangszeile | belegt |
| A2 | `nio.ReactionEvent` trägt `key` und `reacts_to`; verschlüsselte Räume brauchen nichts Zusätzliches | Annahme | C3 und Docstring `_send_event` (m.reaction wird wie jedes Event verschlüsselt). Falsifikation: Reaktion kommt als undecryptable an | belegt, Prüfung in MVC-1 |
| D1 | Die Reaktion ist ein **Antwortweg**, kein Kommandokanal: sie kann nur beantworten, was der Lotse selbst als Entwurf gestellt hat — nie einen Vorgang eröffnen | Entscheidung | Folgt aus `reacts_to` (C3) + `pruefe_go`-Muster (C1). Alternative: freie Emoji-Grammatik („✅ schließt Vorgang N") — genau das hat KONZ-059 als Kommandosprache ohne Grammatik-Gate verworfen (C4) | gesetzt |
| D2 | Genau **ein** Zeichen gilt: 👍 = ja. Kein Nein-Zeichen, kein Vokabular | Entscheidung | Ein zweites Zeichen verdoppelt die Sortierregeln (C4). Nein ist Schweigen oder ein Satz; Schweigen bleibt ausdrücklich **keine** Zustimmung | gesetzt |
| D3 | Der Lotse fragt **in der Morgen-Meldung**, nicht in einem eigenen Lauf | Entscheidung | C4 Backlog-Zeile 4, C5 (Briefing-Lane existiert, 07:00). Alternative: eigener Zeitgeber je Befund — erzeugt den Melder, den niemand liest, und macht den Raum zum Log | gesetzt |
| D4 | Nur Befunde aus einer **Klassen-Erlaubnisliste** werden zur Frage; alles andere bleibt Meldung | Entscheidung | Startliste: abgelaufene Leases räumen · Zertifikat < 30 Tage melden · Prio-Referenz auf Geschlossenes nachziehen · verwaistes Manifest · Dependabot-Sammel-PR. Alternative: jeder Befund darf fragen — dann ist die Erlaubnisliste die Zahl der Fragen, nicht ihre Klasse | gesetzt, wächst per Owner-Wort |
| D5 | **Prod, Publish, Löschen, Security-Config, fremde Orgs sind nie per Reaktion freigebbar** — dort bleibt das geschriebene Wort, auch wenn die Klasse sonst passt | Entscheidung | Charta Art. 2, `autonomy-gates.md` (5 Gates). Ein Daumen ist zu billig für einen irreversiblen Schritt | gesetzt, hart |
| D6 | Eine Reaktion wird **einmal** verbraucht, wie das go-Event heute | Entscheidung | C1 (`_verbraucht_dir`). Falsifikation: derselbe Daumen löst zweimal aus | gesetzt |
| R1 | Zweiter Eingabeweg verdoppelt die Sortierregeln und die Positivkontrolle | Risiko | C4, ausdrücklich so notiert. Gate: D1/D2 halten ihn auf **einen** Fall (Antwort auf eigenen Entwurf, ein Zeichen) statt auf eine Grammatik | gedeckt |
| R2 | Fehlklick: Daumen auf die falsche Nachricht | Risiko | `reacts_to` bindet an genau einen Entwurf; der Entwurf nennt den Vorgang im Klartext. Gate: der Lotse bestätigt die Auslösung mit einer Zeile, die den Vorgang wiederholt — ein Fehlklick ist binnen Sekunden sichtbar | gedeckt |
| R3 | Der Lotse fragt zu oft und der Raum wird zum Melder-Log | Risiko | Gate: **höchstens 3 Fragen je Morgen-Meldung**, und ein Befund wird höchstens **einmal** gefragt (Journal merkt „gefragt am"); danach ist er wieder stille Meldung | offen → MVC-3 |
| R4 | Gesprochenes „go" wird heute abgelehnt (`audio` ist explizit ausgeschlossen, C1) — seit KONZ-060 antwortet der Owner aber oft gesprochen | Risiko | Nebenbefund von heute. Bewusst **nicht** in diesem Konzept gelöst: ein Transkript als Freigabe hieße, einem STT-Modell die Auslösung zu überlassen. Der Daumen ist genau die Antwort darauf | gedeckt, als Befund B3 geführt |

## MVC — kleinste Fassung, die beide Hälften beweist

Feste Kette, keine Schleife (Step 2a: Frage 2 ja, 5 nein, 6 keine Schleife).

| # | Stufe | Repo | Änderung | Positivkontrolle |
|---|---|---|---|---|
| MVC-1 | Reaktion sichtbar | chat-hub | `_room_events` kennt `ReactionEvent` → Eingangszeile `{"reaktion": "👍", "reagiert_auf": "$…"}`; `format_message` um die zwei Felder erweitert; Wache schreibt sie wie jede andere Zeile | Owner setzt 👍 auf eine Lotse-Nachricht → Zeile im Eingang |
| MVC-2 | Reaktion als Freigabe | chat-hub | `pruefe_go_reaktion(eingang_dir, reaktion_event, owner, entwurf_event)` neben `pruefe_go`: Owner, `reagiert_auf == entwurf_event`, Zeichen 👍, unverbraucht, nach dem Entwurf; `lotse_auftrag.sh anlegen --go-event` nimmt beide Arten | 👍 auf einen Entwurf legt das Issue an; derselbe Daumen ein zweites Mal wird abgelehnt |
| MVC-3 | Der Lotse fragt | platform + chat-hub | `tools/chat_agent/vorschlaege.py`: liest `befund_journal.py --json` (C6), filtert auf die Klassen aus D4, lässt Gefragtes aus, gibt höchstens 3; die Briefing-Lane (C5) hängt sie als Fragen an die Morgen-Meldung; Journal merkt `gefragt_am` | Eine Morgen-Meldung trägt eine Frage; ein 👍 darauf erzeugt das Issue; am Folgetag wird derselbe Befund nicht erneut gefragt |
| MVC-4 | Grenze prüfen | chat-hub | Klassen aus D5 werden von `vorschlaege.py` nie vorgeschlagen; `pruefe_go_reaktion` kennt eine Sperrliste und verweigert dort die Reaktion mit Grund | Negativprobe: ein Prod-Schritt als Entwurf + 👍 → Ablehnung mit Klartext-Grund |
| MVC-5 | Brief | chat-hub | `brief.md`: wann gefragt wird, wie bestätigt wird, dass Schweigen kein Ja ist | Brief gelesen, Sitzung neu gestartet |

## Kill-Gate + Threshold

Siehe `kill_criteria`. Exception-Budget: bis 2026-11-03 höchstens **1** Fehlauslösung, die der
Owner zurücknehmen muss; die zweite schaltet den Reaktionsweg ab (`CHAT_LOTSE_REAKTION_GO=0`,
ein Schalter, kein Rückbau). ADR-Threshold: **kein ADR** — keine neue Datenquelle, kein
erweiterter Perimeter; die Charta bleibt wörtlich in Kraft (D5).

| Kriterium | Status | Beleg |
|---|---|---|
| ≥ 5 beantwortete Fragen bis 2026-11-03 | offen | Journal `gefragt_am` + Antwort-Event |
| 0 ungewollte Auslösungen | offen | Owner-Widerspruch im Raum |
| Keine Reaktion außerhalb der Erlaubnisliste angenommen | offen | Negativprobe MVC-4 |

## Befunde (inkl. Advocatus Diabolus)

| # | Befund | Evidenz | Konsequenz |
|---|---|---|---|
| B1 | Diabolus: „Zweiter Eingabeweg" ist der dokumentierte Einwand aus KONZ-059 — er wird hier nicht widerlegt, sondern **eingegrenzt**: die Reaktion kann nichts eröffnen, nur beantworten | C4, D1 | Wenn die Eingrenzung bricht (jemand baut „✅ schließt Vorgang N"), ist das Kill-Gate-Fall, nicht Erweiterung |
| B2 | Diabolus: Der Lotse, der Vorschläge macht, verschiebt die Initiative — aus „Werkzeug auf Zuruf" wird „Gegenüber, das etwas will" | Charta Art. 8 (nicht auf eigene Reichweite optimieren) | Deshalb Obergrenze 3 Fragen, einmal je Befund, nur aus einer benannten Klassenliste, und nie mit Prod-Wirkung |
| B3 | Gesprochenes „go" wird abgelehnt, seit heute antwortet der Owner aber oft gesprochen — die Freigabe ist der einzige Weg, der Sprache ausschließt | C1, KONZ-060 | Bewusst so gelassen; der Daumen ist die Antwort. Falls der Owner ein gesprochenes „go" will: eigener Entscheid, nicht hier |
| B4 | Maintainer: Die Klassenliste (D4) ist eine Liste, die veraltet | — | Sie steht in `vorschlaege.py` als Konstante mit Kommentar je Zeile, nicht in einer Konfigurationsdatei — wer sie ändert, sieht den Grund daneben |
| B5 | Die Reaktion ist **stärker** gebunden als das heutige Text-„go" (`reacts_to` vs. bloße Zeitordnung) | C1, C3 | Dieses Konzept macht die Freigabe an einer Stelle strenger, nicht nur bequemer |

## Alternativen

| # | Alternative | Warum nicht |
|---|---|---|
| ALT-1 | Freie Emoji-Grammatik (✅ erledigt, ⏰ Frist, ❌ nein) | Kommandosprache ohne Grammatik-Gate — genau der Einwand aus KONZ-059 (C4); ein Tippfehler wird hier zum Fehlklick auf den falschen Vorgang |
| ALT-2 | Eigener Zeitgeber „Lotse fragt" | Zweite tägliche Nachricht neben Briefing und Zeitung; KONZ-059 hat das für Kennzahlen bereits verworfen (C4) |
| ALT-3 | Gesprochenes „go" zulassen | Ein STT-Modell entscheidet über die Auslösung; `pruefe_go` schließt Audio heute ausdrücklich aus (C1) — das war eine bewusste Grenze, keine Lücke |

## Top-3-Risiken

1. **B2 Initiative** — messbar über die Zahl der Fragen; Obergrenze und Klassenliste sind die Bremse.
2. **R1/ALT-1 Ausweitung** — der Reaktionsweg wächst zur Grammatik. Gate: genau ein Zeichen, genau ein Bezug.
3. **R3 Raum als Log** — 3 Fragen je Meldung, jeder Befund einmal.

## Out-of-Scope

- Reaktionen als **Kommando** (Vorgang schließen, Frist setzen) — ALT-1, verworfen.
- Gesprochene Freigabe — B3.
- Freigaben mit Prod-, Publish-, Lösch- oder Security-Wirkung — D5, hart.
