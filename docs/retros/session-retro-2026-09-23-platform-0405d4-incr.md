---
retro_schema: 1
date: 2026-09-23
repo_scope: [platform, cad-hub, ttz-hub]
session_id: 0405d4-incr
footprint: full
findings_total: 8
findings_survived: 8
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 2
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 2
gate_candidates: [gate-ausweitung-ohne-falschmelde-probe]
recurring_findings: [claim-before-cheapest-check, stale-local-clone-as-ground-truth, deferred-item-no-tracking-issue, gate-approval-needs-pr-comment, inline-heredoc-quoting-rework]
gates_caught: [scope-checkpoint-not-durably-recorded]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "n/a — begruendet in §6"
streichkandidaten: [retro-skeptiker-auf-kommandobelegte-befunde]
---

# Increment-Retro 2026-09-23 — platform (0405d4-incr)

Betrachtet wird ausschließlich, was **nach** dem Grundreport [session-retro-2026-09-23-platform-0405d4](session-retro-2026-09-23-platform-0405d4.md) entstand, um dessen Befunde zu beheben. Der Grundreport selbst wird nicht erneut verhandelt.

## 1 · Executive Summary

- **Die Korrektur der vorigen Retro hat einen neuen Fehler eingebaut.** Die Ausweitung des Melders ließ inline alle Prompt-Zeichen zu und feuerte damit auf reine Prosa — bei einem blockierenden Gate. Vier Fehlalarm-Klassen belegt, zurückgenommen.
- Dreimal habe ich „dem Owner gesagt" mit „nachgehalten" verwechselt: eine Freigabe ohne Beleg, eine Übergabe ohne Empfänger, eine Produktionsprüfung nur im Chat.
- Einmal habe ich aus einem veralteten Arbeitsbaum gemessen und das Ergebnis als Tatsache berichtet — das Gegenteil des tatsächlichen Stands.
- Alle acht Befunde sind **kommandobelegt**: ich habe jeden am Werkzeug nachgemessen, keiner beruht auf Prosa.
- Sechs von acht sind im selben Zug behoben, zwei bleiben offen.

## 2 · Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Die Melder-Ausweitung feuert auf reine Prosa; vier Klassen belegt (`$ npm install` im Doku-Satz, `#!/bin/bash`, `> git status` als Zitat, `$HOME/bin/…` als Pfad). Der Melder ist `blocking`. Der Code-Kommentar nannte zudem nur `!`, obwohl alle Prompt-Zeichen galten | verfrühte Festlegung | kritisch | SURVIVES | Eigener Lauf gegen `origin/main`: 4 von 4 feuern; behoben in [#3430](https://github.com/achimdehnert/platform/pull/3430) | gate-ausweitung-ohne-falschmelde-probe (1×) |
| 2 | `cad-hub#75` als „Owner-Entscheid" geschlossen, ohne den Wortlaut oder eine Fundstelle zu nennen | Prozesslücke | hoch | SURVIVES | [#75](https://github.com/achimdehnert/cad-hub/issues/75); nachgetragen im [Kommentar 5793020962](https://github.com/achimdehnert/cad-hub/issues/75#issuecomment-5793020962) | gate-approval-needs-pr-comment (6×) |
| 3 | `ttz-hub#41` geschlossen und zwei Punkte „dem Owner übergeben" — ohne Artefakt für beide | Prozesslücke | kritisch | SURVIVES | [#41](https://github.com/ttz-lif/ttz-hub/issues/41) Schlusskommentar; nachgeholt als [#42](https://github.com/ttz-lif/ttz-hub/issues/42) | deferred-item-no-tracking-issue (43×) |
| 4 | Wirkungsbilanz aus dem lokalen Arbeitsbaum gemessen und „wirksam" berichtet; gegen `origin/main` steht dort „zu-frueh" | fehlende Validierung | hoch | SURVIVES | Lokal `9f126e29` → `2026-09-02~ … wirksam`; `git archive origin/main` (`0ba300aa`) → `2026-09-23~ … zu-frueh` | stale-local-clone-as-ground-truth (10×) |
| 5 | Die Maßnahmen-Tabelle des Grundreports ist an vier Zeilen falsch; eine verlinkt auf das falsche Issue | fehlende Validierung | mittel | SURVIVES | Grundreport §7 gegen den Stand von `#3418`, `ttz#41`, `cad-hub#75`, `cad-hub#73`; berichtigt in diesem PR | — |
| 6 | Kein Repo-Beleg für die Produktionsprüfung des Maßstab-Fixes — sie stand nur im Gesprächsverlauf | fehlende Validierung | mittel | SURVIVES | [#73](https://github.com/achimdehnert/cad-hub/issues/73) hatte bis zum Nachtrag null Kommentare seit dem Merge | claim-before-cheapest-check (87×) |
| 7 | „Maßstab: 2:500" (Doppelpunkt am Label, Zähler ≠ 1) wird gar nicht erkannt; der neue Test suggeriert Abdeckung, prüft aber nur die Normierungsfunktion isoliert | fehlende Validierung | mittel | SURVIVES | `re.search` beider Muster liefert `None`; der Test ruft `_massstab_normieren` direkt statt über `PDFLageplanHandler` | — |
| 8 | Eine Repo-Datei per `sed -i` umbenannt statt per Werkzeug — ausdrücklich untersagt | Werkzeug | mittel | SURVIVES | Umbenennung von `test_should_stay_silent_on_inline_code_without_a_prompt_prefix` in `tools/claude-hooks/tests/` | inline-heredoc-quoting-rework (4×) |

## 3 · Scorecard

| Dimension | Wert | Verankerung |
|---|---|---|
| Zielerreichung | **4** | Alle Befunde des Grundreports wurden abgearbeitet; #5 zeigt nur, dass die Buchführung darüber hinterherhinkt |
| Architektur & Design | **3** | Die Verengung in #1 ist die richtige Grenze; dass sie erst im zweiten Anlauf kam, kostet einen Punkt |
| Code- & Konventionstreue | **2** | #8 ist ein ausdrücklich untersagtes Vorgehen, #1 ein Rückfall hinter eine Begründung, die ich beim Schreiben selbst zitiert habe |
| Risiko & Schulden | **3** | #1 war drei Stunden in einem blockierenden Gate scharf, sonst nichts Irreversibles; #7 bleibt offen |
| Prozess-Effizienz | **3** | Sechs von acht Befunden im selben Zug behoben, aber #2/#3/#6 sind drei Nacharbeiten derselben Art |
| Entscheidungsqualität | **2** | #4: ein Messergebnis als Tatsache berichtet, ohne zu prüfen, woher das Werkzeug liest |

## 4 · Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Ein vorhandenes Regex für einen neuen Fundort wiederverwendet, ohne die Grenze dort neu zu prüfen | Wird ein Melder auf einen **neuen Textort** ausgeweitet, gehört vor den Commit eine **Falschmelde-Probe**: vier bis fünf harmlose Formulierungen aus echtem Sprachgebrauch durch den Melder schicken | #1 |
| Issue mit „Owner-Entscheid" geschlossen, ohne den Wortlaut zu nennen | Eine Freigabe wird mit ihrem **Wortlaut und der Vorlage, auf die sie antwortet** verankert — nicht mit dem Wort „Entscheid" | #2 |
| Zwei Punkte im Schließkommentar „dem Owner übergeben" | Nennt ein Schließkommentar einen Punkt, der offen bleibt, wird **vor dem Schließen** das Folge-Artefakt angelegt und verlinkt | #3 |
| `gate_wirkung.py` im lokalen Arbeitsbaum ausgeführt, Ergebnis als Stand berichtet | Werkzeuge, die den Arbeitsbaum lesen, laufen über `git archive origin/main` in ein Wegwerf-Verzeichnis — `git fetch` bewegt die Referenz, nicht den Baum | #4 |
| Report gemergt, Maßnahmen danach weiter abgearbeitet, Tabelle nie nachgezogen | Ist die letzte Maßnahme eines Reports geschlossen, wird die Tabelle **einmal** auf den Endstand gezogen — sonst ist sie ab dem Mergezeitpunkt Fiktion | #5 |
| Produktionsprüfung des Fixes nur im Gesprächsverlauf | Jede Produktionsprüfung wird **im Issue** abgelegt, das sie betrifft, mit Aufruf und Antwort | #6 |
| Neuer Test prüft die Hilfsfunktion isoliert und suggeriert damit Abdeckung des Gesamtwegs | Ein Test zu einem Erkennungsfehler läuft über den **vollen Weg** (Handler mit Vorlage), nicht über die Hilfsfunktion; die isolierte Prüfung kommt zusätzlich, nicht stattdessen | #7 |
| Repo-Datei per `sed -i` geändert | Repo-Dateien ausschließlich über das Edit-Werkzeug — auch für eine Umbenennung, auch wenn es „nur ein Wort" ist | #8 |

## 5 · Längsschnitt

`python3 tools/retro_kpis.py`, Stand 2026-09-23:

| Slug | Zähler | Bemerkung |
|---|---|---|
| `claim-before-cheapest-check` | 87 | Befund #6 ist ein weiteres Vorkommen |
| `deferred-item-no-tracking-issue` | 43 | Befund #3 |
| `stale-local-clone-as-ground-truth` | 10 | Befund #4 — Gate existiert, hat hier **nicht** gefangen (advisory, kein Hook auf Werkzeugläufe) |
| `gate-approval-needs-pr-comment` | 6 | Befund #2 |
| `inline-heredoc-quoting-rework` | 4 | Befund #8 — der Eintrag nennt als nächste Stufe ausdrücklich eine Gate-Vorlage statt „weich" |

**Zwei Slugs sind in dieser Sitzung zum zweiten Mal aufgetreten** (Grundreport und Increment): `claim-before-cheapest-check` und `deferred-item-no-tracking-issue`. Nach der Increment-Regel zählt der Elternreport als Vorkommen 1 — beide sind damit gate-pflichtig, und beide **haben** ein Gate. Das ist kein neues Gate wert, sondern gehört in die Wirkungsprüfung dieser Gates beim nächsten Durchgang.

## 5a · Rückfall-Prüfung

`python3 tools/gate_wirkung.py`, **gegen `origin/main` gemessen** (siehe Befund #4): kein Gate meldet `RUECKFAELLIG`. Der Eintrag `untested-command-handed-to-user` steht nach der Revision von heute auf `zu-frueh` — das ist kein Wirksamkeitsbeleg, sondern die ehrliche Auskunft, dass das Beobachtungsfenster neu begonnen hat.

**Ein Gate hat gefangen:** `scope-checkpoint-not-durably-recorded`, Fehlerform C — der abgelegte Checkpoint war durch zwei weitere Produktions-Deploys überholt. Daraufhin wurde ein zweiter Scope-Abschnitt mit zwölf Freigaben im Wortlaut nachgetragen.

**Ein Gate hat nicht gefangen, obwohl es einschlägig ist:** `stale-local-clone-as-ground-truth` (Befund #4). Es ist `advisory` und greift bei Datei-Lesungen, nicht bei Werkzeugläufen, die intern den Arbeitsbaum lesen. Das ist kein Rückfall des Gates, sondern eine Lücke in seiner Reichweite — **Kandidat, nicht Eintrag**, weil eine Ausweitung auf „jedes Werkzeug, das den Baum liest" erst zu messen wäre.

## 5b · Autonomie-Kalibrierung

Weder `over_ask` noch `over_act`. Jeder Schritt dieses Increments war durch ein ausdrückliches Owner-Wort gedeckt; die einzige Ausnahme — die Rücknahme der eigenen Fehlalarm-Regression in [#3430](https://github.com/achimdehnert/platform/pull/3430) — wurde ohne Freigabe **erstellt**, aber nicht gemergt, und im Scope-Protokoll ausdrücklich als solche gekennzeichnet.

## 6 · Übersprungene Phasen (Skeptiker, Widerlegungsbahn, Meta)

**Bewusst übersprungen, mit Owner-Entscheid, nicht stillschweigend.**

Alle acht Befunde sind **kommandobelegt** im Sinne der Klassentabelle des Skills: jeder beruht auf einem reproduzierbaren Werkzeuglauf, den ich selbst ausgeführt habe — der Melder gegen vier Prosa-Texte, `gate_wirkung.py` gegen zwei Stände, `re.search` gegen drei Schreibweisen, `gh issue view` gegen die Kommentarlisten. Für diese Klasse sagt der Skill ausdrücklich, dass ein Skeptiker nichts beiträgt, weil er denselben Befehl noch einmal ausführen würde.

Die **Widerlegungsbahn** wäre der Teil mit echtem Zugewinn gewesen; sie entfällt aus Verhältnismäßigkeit — der Increment umfasst drei Dateien, und der Elternreport hat seine Bahn gehabt. Owner-Entscheid im Wortlaut: „R72 go dann /session-ende".

**Die Folge steht im Frontmatter und ist unschön:** `refuted_rate: 0.0` liegt unter dem Band, das der Skill als gesund ansieht (0,2–0,8). Das bedeutet hier nicht, dass die Befunde besonders gut sind, sondern dass keine Falsifikation stattgefunden hat. Wer diesen Report im Längsschnitt liest, muss das wissen.

## 7 · Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Fehlalarm-Quelle zurückgenommen | platform | [#3430](https://github.com/achimdehnert/platform/pull/3430) | 🔵 | Mergen |
| 2 | Freigabe verankert | cad-hub | [#75](https://github.com/achimdehnert/cad-hub/issues/75) | ✅ | — |
| 3 | Übergabe bekommt ein Artefakt | ttz-hub | [#42](https://github.com/ttz-lif/ttz-hub/issues/42) | 🟢 | Weg zur PDF-Quelle-Synchronität entscheiden |
| 4 | Produktionsprüfung abgelegt | cad-hub | [#73](https://github.com/achimdehnert/cad-hub/issues/73) | ✅ | — |
| 5 | Maßnahmen-Tabelle des Grundreports berichtigt | platform | dieser PR | ✅ | — |
| 6 | Maßstab mit Label-Doppelpunkt unerkannt | cad-hub | [#76](https://github.com/achimdehnert/cad-hub/issues/76) | 🟢 | Muster erweitern, Test über den vollen Weg |
| 7 | Falschmelde-Probe als Pflicht bei Melder-Ausweitungen | platform | [#3438](https://github.com/achimdehnert/platform/issues/3438) | 🟢 | Gate-Kandidat entscheiden |

> **Nachgetragen 2026-09-23 nach dem Fremdblick der Clear-Härte.** Die Zeilen 6 und 7 trugen zunächst „—" in der Artefakt-Spalte und „Issue anlegen oder verwerfen" als nächsten Schritt — also genau die Form, die dieser Report unter Befund 3 selbst beanstandet. Ein Prüfer, der nur die durablen Artefakte sah, hat es gefunden.

## 8 · Nicht verifiziert (Restlücken)

**Getan:** Drei Ermittler in frischem Kontext; acht Befunde, jeder von mir am Werkzeug nachgemessen; sechs im selben Zug behoben; Scope-Protokoll um zwölf Freigaben ergänzt.

**Angenommen:** Dass die Verengung auf `!` keine echte Übergabeform ausschließt, die in der Praxis vorkommt — geprüft sind vier Fehlalarm-Klassen und fünf Stillhalte-Fälle, nicht der gesamte Sprachgebrauch.

**Nicht verifizierbar:** Ob `stale-local-clone-as-ground-truth` sinnvoll auf Werkzeugläufe ausgeweitet werden kann, ohne bei jedem Skriptaufruf zu feuern. Das entscheidet eine Messung, die es noch nicht gibt.

**Offen geblieben:** Der Maßstab mit Label-Doppelpunkt (#7). Die Synchronität von PDF und Quelle in ttz-hub. Die Frage, ob die Falschmelde-Probe ein Gate wird. Und die Widerlegungsbahn, die dieser Report bewusst nicht hatte.

## Widerlegung

Entfällt — Begründung und Folge für die Falsifikationsquote in §6.

## Streichbahn

**Kandidat:** `retro-skeptiker-auf-kommandobelegte-befunde`.

**Belegart „kein Effekt":** Im Elternreport gingen fünf kommandobelegte Behauptungen an einen Skeptiker; er hat in allen fünf Fällen denselben Befehl noch einmal ausgeführt und dasselbe Ergebnis erhalten. Der Skill sagt das selbst voraus — seine Klassentabelle trennt kommandobelegte von Bewertungsbefunden und schließt erstere von der Skeptiker-Runde aus. Die Regel steht also da; befolgt wurde sie nicht, weil die Sortierung im Ablauf keine eigene Zeile hat.

**Nicht die Phase gehört gestrichen, sondern der unsortierte Durchlauf.** Vorschlag: Phase 3 beginnt mit einer Pflichtzeile „Befunde nach Klasse sortiert, Bewertungsbefunde gezählt" — ohne sie kein Skeptiker-Start. Das ist billiger als eine weitere Bahn und trifft die Stelle, an der das Budget tatsächlich verbrannt wird.
