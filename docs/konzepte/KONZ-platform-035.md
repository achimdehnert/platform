---
concept_id: KONZ-platform-035
title: Deckungsausweis — Vollständigkeit von Sachverhalts-Darlegungen aus E-Mail
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: []          # kein Klickdummy; betrifft Werkzeug- und Antwortkonvention (begründet leer)
adr_threshold: Amendment   # ADR-284 §2 dehnt den Coverage-Contract auf Live-Antworten aus
review_by: 2026-10-27
kill_criteria: "Eine Sachverhalts-Darlegung lässt bis 2026-09-30 eine relevante Mail aus, die INNERHALB des ausgewiesenen Deckungsbereichs lag → Konzept verfehlt seinen Zweck, wird verworfen statt geflickt. Ausserhalb des Bereichs = kein Fehlschlag, sondern eine Scope-Entscheidung."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: docs/adr/ADR-284-mail-intelligence-action-system.md, commit_or_pr: "2c3b2f11/main", opened_in_session: true}
  - {claim_id: C2, source_path: docs/adr/ADR-286-mail-agent-crypto-shredding-derived-index.md, commit_or_pr: "#1488", opened_in_session: true}
  - {claim_id: C3, source_path: tools/mail_agent/read_mail.py, commit_or_pr: "#1487", opened_in_session: true}
  - {claim_id: C4, source_path: tools/mail_agent/graph_mail.py, commit_or_pr: "#1485", opened_in_session: true}
  - {claim_id: C5, source_path: tools/mail_agent/vorgang.py, commit_or_pr: "#1490", opened_in_session: true}
  - {claim_id: C6, source_path: .windsurf/workflows/mailcheck.md, commit_or_pr: "#1485", opened_in_session: true}
created: 2026-07-27
---

# KONZ-platform-035: Deckungsausweis

**Tier T2**, weil es eine **neue Konvention** einführt (ein Pflichtbestandteil für eine ganze
Klasse von Antworten) und die verteilten Mail-Skills berührt — aber in einem Repo lebt und
durch Entfernen *eines* Ausgabeblocks rückbaubar ist. Kein SSoT-Reversal, keine neue
Abhängigkeit, keine Cross-Repo-Codeänderung.

## Kernthese

**Vollständigkeit ist nicht beweisbar, Deckung schon** — deshalb trägt jede
Sachverhalts-Darlegung ihren Deckungsausweis, und ohne ihn gilt sie als unvollständig.

## Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| A1 | Der Coverage-Contract aus ADR-284 §2 bindet **nur Phase 1 (den Index)**. §3 führt Phase 0–4 auf; verbindlich ist ausdrücklich nur Phase 1. Die **Live-Antwort** ist ungeregelt. | Annahme→belegt | E1 (C1, §2 Nr. 1 + §3 Scope-Tabelle) | offen |
| A2 | Alle drei Fehlschläge vom 2026-07-27 traten in **Live-Antworten** auf, nicht im Index — der existiert noch gar nicht. | Annahme→belegt | E3 (C3/C4, PRs #1485/#1487) | offen |
| B1 | Ein erfundener Platzhalter (`--from "@"`) verwarf auf „Gesendete Elemente" **21 von 34** Nachrichten still; Exchange liefert Absender teils als X.500-DN ohne `@`. | Befund | E3 (C4, #1485 — Live-Messung 34 vs. 13) | behoben |
| B2 | Eine Trefferliste ohne Nenner ist von einer Vollerhebung nicht unterscheidbar (`--list N` gab N Zeilen und sonst nichts). | Befund | E3 (C3, #1487) | behoben |
| B3 | Ein Sachverhalt wurde aus **INBOX allein** dargelegt: 3 von 11 Nachrichten. Die übrigen lagen in `Gesendete Objekte`, `MEIKI` und im **Papierkorb**. | Befund | E3 (Session-Lauf `vorgang.py --topic`, C5) | offen |
| B4 | **Kein Ordner ist der Vorgang.** Der belegte Fall verteilt sich über fünf Ordner. | Befund | E3 (C5, s. B3) | offen |
| B5 | Die Feldwahl entscheidet mehr als der Begriff: derselbe Term ergab 0 (SUBJECT) / 327 (BODY) / 678 (TEXT). | Befund | E3 (C5, #1490 Live-Messung) | behoben (Warnung) |
| D1 | **Jede Sachverhalts-Darlegung trägt einen Deckungsausweis** — Konten, Ordnerzahl, Zeitfenster, Kriterien je mit eigener Trefferzahl, geprüfte Menge, ausdrücklich Nicht-Gedecktes. Fehlt er, gilt die Darlegung als unvollständig. | Entscheidung | D (Alternative: Freitext-Disclaimer — verworfen, weil nicht prüfbar) | offen |
| D2 | **Pflicht-Scope ist ALLES**: alle Ordner aller benannten Konten, **einschließlich Gesendet und Papierkorb**. Ausschlüsse sind zu **benennen**, nicht zu unterstellen. | Entscheidung | E3 (B3 — drei der elf Nachrichten lagen im Papierkorb) | offen |
| D3 | **Mehrere unabhängige Kriterien statt eines**, jedes mit eigener Trefferzahl: Thread-Header · Betreff · Beteiligte · zitierter Text · Anhangs-Prüfsumme. Ein Kriterium, das nichts findet, wird dadurch **sichtbar** statt unbemerkt. | Entscheidung | E1 (C2, ADR-286 §4.9 „deterministische Signale") | offen |
| D4 | **Kalibrierung vor Vertrauen**: Vor einer Vollständigkeitsaussage muss die Abfrage ein Element zurückgeben, von dem feststeht, dass es enthalten ist. Erscheint es nicht, ist nicht die Menge leer, sondern die Abfrage kaputt. | Entscheidung | E3 (B1 — genau dieser Test hätte den Fehlschlag verhindert) | offen |
| D5 | **Über-Einschluss vor Unter-Einschluss.** Eine überflüssige Mail kostet Aufmerksamkeit, eine fehlende kostet eine falsche Auskunft. Im Zweifel aufnehmen und als unsicher kennzeichnen. | Entscheidung | D (Alternative: Präzision priorisieren — verworfen, Kostenasymmetrie) | offen |
| D6 | Der Deckungsausweis ist **maschinell erzeugt**, nicht von Hand geschrieben. Ein handgeschriebener Ausweis ist eine Behauptung über eine Behauptung. | Entscheidung | D | offen |
| R1 | Der Ausweis wird zur Formalie: er steht da, wird aber nicht gelesen, und die Zahl darin ist falsch. | Risiko | — | Gegenmaßnahme: D6 (maschinell) + Kill-Gate misst Auslassungen, nicht Ausweis-Präsenz |
| R2 | Pflicht-Scope über alle Ordner ist teuer — gemessen 50–77 s über 110 Ordner / 46.065 Nachrichten. | Risiko | E3 (C5, Live-Messung) | Gegenmaßnahme: Kosten ausweisen, nicht Scope kürzen; Kürzung ist eine benannte Ausnahme |
| R3 | Mehr Ordner heißt mehr berührte personenbezogene Daten. Datenschutzfreundlich ist **nicht** automatisch, was weniger anfasst. | Risiko | E1 (C2, ADR-286 §4.9 „Ehrliche Grenzen") | Gegenmaßnahme: anlassbezogen statt systematisch; nichts persistieren |

## Steelman

Der stärkste Fall für dieses Konzept ist nicht Ordnung, sondern **Haftung**. Wer als
Datenschutzbeauftragter oder Betreuer eine Auskunft gibt, haftet für ihre Richtigkeit — und eine
Auskunft aus unvollständigem Material ist falsch, auch wenn jeder einzelne Satz stimmt. Der
Deckungsausweis verwandelt eine unprüfbare Zusicherung („ich habe alles angesehen") in eine
prüfbare Angabe („110 Ordner, 46.065 Nachrichten, Kriterium Betreff, 11 Treffer"). Das ist
derselbe Schritt, den ADR-284 für den Index gegangen ist — nur für die Antwort.

## Advocatus Diabolus

| Frage | Antwort |
|---|---|
| Wo entsteht eine Doppelquelle? | Nirgends — der Ausweis beschreibt eine Abfrage, er speichert nichts. Er ist flüchtig wie die Antwort, zu der er gehört. |
| Wo wird SSoT nur behauptet? | Beim Scope: „alle Ordner" stimmt nur für die Konten, auf die der Zugriff besteht. Der HNU-Kanal läuft nach Entscheid vom 2026-07-27 bei Variante C — Suche ja, Zuordnung nein. Das gehört in den Ausweis, nicht in eine Fußnote. |
| Wo wird ein Werkzeug faktisch zur Boundary? | Wenn der Ausweis zur Voraussetzung wird, ist das Werkzeug, das ihn erzeugt, kritischer Pfad. Fällt es aus, gibt es keine Darlegung mehr. → Der Ausweis muss auch von Hand ausfüllbar sein, dann aber als solcher gekennzeichnet. |
| Wo manuelle Pflicht ohne Enforcement? | **Hier liegt die eigentliche Schwäche.** „Ich lege keinen Sachverhalt ohne Ausweis vor" ist eine Zusage, kein Gate. Ein Hook kann den Ausweis im Text erkennen, aber nicht seine Richtigkeit. Ehrlich benannt: Dies ist ein **Review-Gate, kein Exit-Code**. |
| Wo ist „sichtbar machen" schwächer als „verhindern"? | Beim Scope. Sichtbar zu machen, dass der Papierkorb nicht durchsucht wurde, hilft nur, wenn jemand hinsieht. Deshalb D2: Papierkorb und Gesendet sind **Pflicht**, nicht Option — Weglassen ist die begründungspflichtige Abweichung. |
| Wo kann man formal erfüllen und praktisch umgehen? | Indem der Scope eng gewählt und korrekt ausgewiesen wird — formal sauber, praktisch nutzlos. Dagegen hilft nur das Kill-Kriterium, das an **Auslassungen** misst, nicht am Vorhandensein des Ausweises. |

## Maintainer-2028

Wer das in zwei Jahren liest, muss erkennen: Der Ausweis ist **nicht** dazu da, Arbeit zu
dokumentieren, sondern eine bestimmte Fehlerklasse unmöglich zu machen — die stille Teilmenge,
die wie eine Vollmenge aussieht. Wird er zur Pflichtübung ohne Bezug zur Frage, ist er zu
streichen und nicht zu erweitern. Die Frage an ihn lautet nie „ist er da", sondern „hätte er den
Fehler gefangen".

## Alternativen

| # | Alternative | Warum nicht |
|---|---|---|
| 1 | Freitext-Hinweis („nicht abschließend geprüft") an jede Antwort | Nicht prüfbar und deshalb wirkungslos — genau die Sorte Disclaimer, die man nach dreimal Lesen überliest. Der heutige Fehlschlag hatte einen solchen Vorbehalt nicht nötig, er hatte falsche Zahlen. |
| 2 | Erst den Index aus ADR-284 Phase 1 bauen, dann ist das Problem weg | Löst es nicht: Der Index deckt, was er indexiert hat. Die Frage „war der Scope vollständig" stellt sich dort genauso — und bis er existiert, bleibt jede Antwort ungeregelt. |

## MVC — konkreter Plan

| Baustein | Datei / Ort | Inhalt |
|---|---|---|
| Ausweis-Erzeugung | `tools/mail_agent/vorgang.py` | Funktion `deckungsausweis(konten, ordner_gesamt, ordner_durchsucht, kriterien: dict[str,int], fenster, nicht_gedeckt: list[str]) -> str` — rein, ohne IMAP, testbar |
| Ausgabe | dieselbe Datei, `cmd_topic` / `cmd_show` | Ausweis **vor** der Trefferliste, nicht als Fußnote |
| Mehrere Kriterien | `cmd_topic` | Betreff · Beteiligte · zitierter Text · Anhangs-Hash, je mit eigener Trefferzahl im Ausweis |
| Kalibrierung | `vorgang.py --calibrate <id>` | prüft, ob eine bekannt vorhandene Nachricht von der Abfrage zurückgegeben wird |
| Skill-Pflicht | `.windsurf/workflows/mailcheck.md`, `briefing.md`, `iil-mail.md` | Ein Abschnitt: Sachverhalts-Darlegung ohne Deckungsausweis gilt als unvollständig |
| ADR-Anschluss | ADR-284 §2 | Amendment: Coverage-Contract gilt auch für Live-Antworten, nicht nur für den Index |

**Nicht im MVC:** semantische Relevanzbestimmung. Welche der gefundenen Mails wirklich zum
Sachverhalt gehören, entscheidet der Mensch — das Konzept sichert die **Deckung**, nicht die
**Relevanz**, und dieser Unterschied ist der Kern seiner Ehrlichkeit.

## Kill-Gate

**Messbare Abbruchschwelle:** Legt eine Sachverhalts-Darlegung bis **2026-09-30** eine relevante
Mail nicht vor, die **innerhalb des ausgewiesenen Deckungsbereichs** lag, hat das Konzept seinen
Zweck verfehlt und wird **verworfen, nicht geflickt**.

**Ausdrücklich kein Fehlschlag:** eine fehlende Mail **außerhalb** des ausgewiesenen Bereichs.
Dann hat der Ausweis funktioniert und der Scope war zu eng — das ist eine Entscheidung, kein
Defekt.

**Exception-Budget:** einmalige Verlängerung bis **2026-10-31**, danach ohne weitere.

| Kriterium | Status | Beleg |
|---|---|---|
| K1 Ausweis wird maschinell erzeugt und erscheint vor der Trefferliste | offen | — |
| K2 Pflicht-Scope schließt Gesendet und Papierkorb ein | offen | — |
| K3 Mindestens zwei unabhängige Kriterien mit getrennter Trefferzahl | offen | — |
| K4 Kalibrierung existiert und wird vor Vollständigkeitsaussagen benutzt | offen | — |
| K5 Keine Auslassung innerhalb des ausgewiesenen Bereichs bis 2026-09-30 | offen | — |

## Threshold

**Amendment an ADR-284**, kein neuer org-weiter ADR: Der Coverage-Contract existiert bereits als
Entscheidung (§2 Nr. 1), er ist nur auf den Index beschränkt. Ihn auf Live-Antworten auszudehnen
ist eine Erweiterung nach bestehendem Muster — keine neue Architekturentscheidung.
