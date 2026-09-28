---
retro_schema: 1
date: 2026-09-28
repo_scope: [chat-hub, dev-hub, platform]
session_id: d332fc
footprint: lean
findings_total: 3
findings_survived: 2
refuted_rate: 0.33
phase3_refuted: 0
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 4
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [gate-claim-before-cheapest-check-wirkungslos]
recurring_findings: [claim-before-cheapest-check, partial-fix-not-generalized-to-sibling-artifacts]
gates_caught: [direct-gh-pr-merge-bypasses-sa-m, stale-local-clone-as-ground-truth]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "n/a (lean)"
streichkandidaten: []
streich_begruendung: "Keiner, weil diese lean-Retro nur zwei Phasen durchlief (0.0, 5) und beide lieferten verwertbare Treffer — 0.0 ordnete F1 einem offenen Gate-Issue zu, retro_kpis zeigte F2 als Wiederholung."
---

# Session-Retro 2026-09-28 · Lotsen-Übergabe an der Sichtbarkeits-Sperre (d332fc)

**Footprint `lean`:** ein PR (iilgmbh/chat-hub#145), ein beschriebenes Repo (chat-hub), kein
Prod-Schritt im engeren Sinn, keine Migration, kein ADR. dev-hub ist Ziel eines vom Lotsen
angelegten Issues, platform nur gelesen. Agenten-Budget 0, ein Inline-Pass über zwei Dimensionen
(Soll-Ist, Entscheidungen & Fehler). Restlücke: Der lokale Pull des chat-hub-Klons ändert das
Laufzeitverhalten des Lotsen sofort — als Merge-Folge mit Owner-Go, aber ohne eigene Prüfung
im Raum (§8).

## 0.0 Wirkungsbilanz

`tools/gate_wirkung.py`: 7 Gates `RUECKFAELLIG`.

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | 4 (+1 hier, F1) | Quelle — Zeitangaben aus dem Chat werden nicht geprüft | **ausweiten**, auf bestehendem Issue platform#2666 |
| untested-tool-module-green-gate | 3 | kein Vorkommen hier | in dieser Retro nicht entschieden (§8) |
| worktree-midsession-accumulation | 3 | kein Vorkommen hier | in dieser Retro nicht entschieden (§8) |
| check-ohne-positivkontrolle | 2 | kein Vorkommen hier | in dieser Retro nicht entschieden (§8) |
| melder-ohne-leser | 2 | kein Vorkommen hier | in dieser Retro nicht entschieden (§8) |
| secret-leak-via-safe-pattern | 2 | kein Vorkommen hier | in dieser Retro nicht entschieden (§8) |
| stale-local-clone-as-ground-truth | 2 | hat hier gegriffen (KONZ-039 aus `origin/main` gelesen) | keine, Beleg für das Gate |

## 1. Executive Summary

- Der Lotse steckte fest: Standardziel `platform` ist öffentlich, der Bestätigungsschalter ist für die Raum-Session gesperrt. Fix: Standardziel `dev-hub` (privat), iilgmbh/chat-hub#145, Tests 318 grün, Live-Probe `PRIVATE`.
- Die Übergabe kam danach an (achimdehnert/dev-hub#403, 12:43 UTC).
- F1: Ein älteres Issue (dev-hub#398, 10:06 UTC, vor Sitzungsbeginn 10:54 UTC) wurde als „vermutlich die Übergabe“ genannt. Der billigste Check, Anlagezeit gegen Sitzungsbeginn, fehlte.
- F2: Der Fix stellte das Ziel um, nicht aber den Hinweis „`#N weiter`“ im selben Text. Seit dem Ziel dev-hub ist er mehrdeutig, platform#403 existiert als anderes Issue. Nachgezogen als iilgmbh/chat-hub#146.
- platform privat schalten (#3234) und die Zeitungsausgabe aus dem Raum (dev-hub#403) sind auf eigene Sitzungen vertagt.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| F1 | Übergabe-Zuordnung zu dev-hub#398 ohne Zeitabgleich; #398 lag vor Sitzungsbeginn | fehlende Validierung | mittel | SURVIVES | achimdehnert/dev-hub#398 `createdAt` 10:06:02Z vs. erste Nutzer-Nachricht 10:54:14Z (`retro_transkript_kennzahlen.py`) | claim-before-cheapest-check |
| F2 | Fix des Standardziels ließ den Hinweis „`#N weiter`“ im selben Issue-Text unverändert | Werkzeug | mittel | SURVIVES | iilgmbh/chat-hub#145 Diff ohne `uebergabe_text`; dev-hub#403 Body enthält „`#N weiter`“; platform#403 ist ein anderes Issue | partial-fix-not-generalized-to-sibling-artifacts |
| F3 | Zwei Edits vor dem Lesen der Datei abgelehnt | Werkzeug | niedrig | REFUTED (pre) | Transkript 12:20:02Z, im selben Zug behoben, ohne Folgen | — |

F1 und F2 sind durch Befehle belegt (Zeitstempel, Textvergleich). Bei `lean` gibt es keinen Skeptiker.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Übergabe angekommen (dev-hub#403); F2 als Rest |
| architektur_design | 4 | Sperre bleibt, nur das Standardziel ändert sich; Schalter bewusst nicht freigegeben |
| code_konventionstreue | 4 | Test als Invariante, Commit-Format eingehalten; F2 |
| risiko_debt | 4 | F2 in #146 erfasst |
| prozess_effizienz | 3 | F1: falsche Zuordnung, eine zusätzliche Runde mit dem Raum |
| entscheidungsqualitaet | 4 | A3 und #403 wegen Scope bewusst vertagt; F1 |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| dev-hub#398 als „vermutlich A1“ genannt, ohne `createdAt` mit dem Zeitpunkt des Go zu vergleichen | Vor jeder Zuordnung „das ist Ergebnis X“ die Anlagezeit gegen den Auslösezeitpunkt prüfen; liegt nichts danach, „noch nicht angekommen“ melden | #F1 |
| Standardziel umgestellt, Hinweistext im selben Issue unverändert | Beim Wechsel eines Ziels alle Stellen suchen, die das alte Ziel implizit voraussetzen (`grep` nach `#N`, Repo-Name) | #F2 |

## 5. Längsschnitt

`tools/retro_kpis.py`: `claim-before-cheapest-check` ×95 und
`partial-fix-not-generalized-to-sibling-artifacts` ×15, beide **GATE-PFLICHT**. Für die zweite
Klasse gibt es unter `docs/governance/gates/gates/` kein Gate (per `git ls-tree` geprüft).
Das Gate bleibt Pflicht und offen (§8).

### 5a. Rückfall

`claim-before-cheapest-check` ist rückfällig: **Gate rückfällig**, Antwort **ausweiten**. Die
Familie „Chronologie-Behauptung über fremde Läufe“ ist in platform#2666 schon beschrieben. F1 ist
ein weiterer Fall davon und wird dort als Kommentar angehängt, kein zweites Gate.

### 5b. Autonomie-Kalibrierung

`over_ask` 0, `over_act` 0. Der Merge-Versuch für #145 lief mit Owner-Go, wurde von
`direct-gh-pr-merge-bypasses-sa-m` gefangen und war da schon überholt: der PR war bereits über
das Owner-Konto gemergt (12:32:54Z).

## 6. Verankerung

- `memory_candidates`: keine neue Memory. F1 ist schon durch das Gate und platform#2666 gedeckt.
- `adr_candidates`: keine.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Hinweis mit Repo-Namen | chat-hub | iilgmbh/chat-hub#146 | 🟢 | Fix-PR mit Test |
| M2 | Gate auf Zeitangaben ausweiten | platform | #2666 | 🟢 | F1 als Fall anhängen, dann bauen |
| M3 | Gate für nicht nachgezogene Nachbarstellen | platform | — | 🟢 | Owner-Entscheid, ob Gate oder Sunset |
| M4 | Streichbahn | platform | — | ✅ | keiner, Grund im Frontmatter |

## 8. Nicht verifiziert (Restlücken)

- **getan:** Fix #145 gemergt und lokal ausgerollt, Übergabe dev-hub#403 angekommen, F2 als #146 erfasst, F1 an platform#2666.
- **angenommen:** Die Raum-Session nutzt den lokalen Klon `~/github/chat-hub` (Raum-Brief nennt den Pfad). Dass sie den neuen Standard ohne `--repo` nutzt, ist nicht gesondert belegt: #403 lief mit ausdrücklichem Owner-Wort zum Ziel.
- **nicht verifizierbar:** Wer den PR um 12:32:54Z gemergt hat (Owner-Hand oder Auto-Merge). Billigster Check: `gh api repos/iilgmbh/chat-hub/issues/145/events`.
- **offen geblieben:** Sechs rückfällige Gates ohne Vorkommen hier sind in dieser Retro nicht entschieden. M3 hat noch kein Gate. Kein Skeptiker und keine Widerlegungsbahn (lean) — Regel 1 ist nur durch die Befehlsbelege gedeckt.

## Widerlegung

n/a — Footprint `lean` (0 Subagenten). Beide Überlebenden sind durch Befehle belegt, nicht durch Bewertung.

## Streichbahn

Keiner, weil beide durchlaufenen Phasen (0.0, 5) einen Treffer lieferten, der sonst untergegangen wäre.
