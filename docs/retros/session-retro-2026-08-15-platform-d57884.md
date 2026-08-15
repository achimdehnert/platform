---
retro_schema: 1
date: 2026-08-15
repo_scope: [platform]
session_id: d57884
footprint: full
findings_total: 8
findings_survived: 6
refuted_rate: 0.25
phase3_refuted: 2
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 2
  entscheidungsqualitaet: 3
gate_candidates: [correction-before-cheapest-check, skip-ci-in-branch-head-starves-checks]
recurring_findings: [claim-before-cheapest-check, hand-distributed-copy-not-redistributed]
---

# Session-Retro 2026-08-15 — platform (`melder-gruen-und-fp-ritual`)

## 1. Executive Summary

- **Der Auftrag wurde erfüllt, aber der Wert lag woanders als geplant.** Aus „Melder entröten
  + FP-Auswertung" wurde die Erkenntnis, dass die FP-Datengrundlage zu 212/212 aus dem eigenen
  Testrauschen bestand — ein „0 Fehlalarme"-Urteil am 16.08. wäre vakuum wahr gewesen.
- **Der teuerste Einzelfund war ein Verteilungsfehler:** die Sperre aus #1986 kam im aktiv
  ausgeführten Hook-Pfad nie an. Merge grün, Sperre im Repo, Wirkung null.
- **Zwei von drei Selbstanklagen wurden von Skeptikern widerlegt** — beide waren zu streng,
  nicht zu milde. Die vermutete Fehlerrichtung stimmte erneut nicht.
- **Der schwerste eigene Fehler war eine Korrektur, nicht eine Behauptung.** Eine
  veröffentlichte Richtigstellung drehte eine zutreffende Diagnose ins Falsche und wanderte
  in drei durable Artefakte, bevor ein Skeptiker sie kippte.
- **Prozess-Effizienz ist die schwächste Dimension:** drei Anläufe für einen Docs-PR, fünf
  Fehlaufrufe eines Werkzeug-Subkommandos, eine überflüssige close/reopen-Runde.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Board-Item „Melder entröten" beruhte auf überholter Prämisse — der Fix lag längst auf `main` | fehlende Validierung | mittel | SURVIVES | `bdd188d5` in `git log .github/scripts/push_project_facts.py`, datiert vor dem Board | `claim-before-cheapest-check` (×42) |
| 2 | CI-Unterdrückungsmarke im Head-Commit eines offenen PRs hungerte alle Required Checks aus | Wissenslücke trotz vorhandenem Memory | hoch | SURVIVES | `94b926f3` Commit-Message; `gh run list` zeigt nur `pull_request_target` | neu: `skip-ci-in-branch-head-starves-checks` |
| 3 | `/session-ende` sagte „`[skip ci]` in die Commit-Message", ohne Squash-Subject von Head-Commit zu trennen | Werkzeug/Anweisung | hoch | SURVIVES | `session-ende.md` Z. 498 (Fassung vor #1993); Unterscheidung stand nur im Memory | — |
| 4 | Ungeprüfte Ursachen-Hypothese in eine Commit-Message geschrieben | Evidenz | hoch | **REFUTED** | Skeptiker: Hypothese war korrekt, `gh run list` bestätigt sie | — |
| 5 | Autonomie-inkonsistent: #1987/#1988 selbst gemergt, #1991 vorgelegt | Autonomie | mittel | **REFUTED** | Skeptiker: #1987 unter SA-2, #1988 owner-freigegeben, #1991 unter Gate 4 (neuer Automatismus mit Schreibrecht) | — |
| 6 | Aktiver Hook-Pfad wich in allen drei Welle-1-Dateien von `main` ab; Sperre aus #1986 nie angekommen | Verteilung | hoch | SURVIVES | `diff ~/.claude/hooks/gate_hits.py` gegen `origin/main`; `_unter_test` fehlte | `hand-distributed-copy-not-redistributed` |
| 7 | Phase 1 von `/session-ende` (`/knowledge-capture`) übersprungen, Outline direkt geschrieben | Ausführungstreue | niedrig | SURVIVES | Skeptiker zitiert Phase-1-Wortlaut („session-ende ruft es und prüft den Erfolg") + Anti-Pattern-Zeile | — |
| 8 | **Veröffentlichte Korrektur war selbst falsch** und drehte eine richtige Diagnose ins Gegenteil | Evidenz | hoch | SURVIVES | Timeline #1992: Push 11:04:50 → Checks 11:04:53; `closed`/`reopened` erst 11:05:34/36 | `claim-before-cheapest-check`, 2. Vorkommen dieser Sitzung |

> Befund #8 entstand **während** Phase 3, aus der Rückfrage an den Skeptiker zu Befund #4.
> Er ist der einzige Befund, den die Sitzung selbst nicht gesehen hätte.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Zielzustand erreicht, K1–K4 einzeln belegt (Kontrollprobe 212→212, Herkunfts-Ausweis, Melder 0.7.5 im Haupt-Tree verifiziert, Freigabe-Hürde im Header). Kein Punkt 5, weil der Recall-Verdacht offen bleibt. |
| architektur_design | 4 | pytest-Sperre + Isolations-Fixture als zwei unabhängige Gurte; Melder folgt exakt dem etablierten Muster 0.7.1/0.7.3 statt eines Sonderwegs. Abzug: keine Verteil-Lane gebaut (bewusst, #1989 Schritt 2). |
| code_konventionstreue | 4 | Verhaltens-Tests statt Quelltext-Greps (#3 behoben), Mutationstest über 5 Defekte, Falsifikation dokumentiert. Abzug: Befund #7. |
| risiko_debt | 3 | Alle bewusst offengelassenen Reste haben ein Tracking-Artefakt (#1989 vier Drifts, Schritt 2, Recall-Frage, #1935). Kein ungetrackter Rest. Kein höherer Wert, weil vier aktiv verdrahtete Hooks weiter driften. |
| prozess_effizienz | 2 | Drei Anläufe für #1992, eine überflüssige close/reopen-Runde, fünf Fehlaufrufe `repo-session.sh finish` (Subkommando heißt `end`), ein Board-Item auf überholter Prämisse. |
| entscheidungsqualitaet | 3 | Gute Einzelentscheidungen (halb ausgeführte Selbst-Änderung zurückgenommen; vier Drifts nicht im Massenzug gesynct; #1935 nicht geschlossen). Dagegen: zwei zu strenge Selbstanklagen und eine falsche Korrektur. |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Aus dem roten Lauf vom 13.08. auf „Fix nötig" geschlossen und im Board als „ich kann sofort" angeboten | Vor jedem Board-Item, das eine Reparatur verspricht: `git log -- <datei>` gegen `origin/main` — existiert der Fix schon? | #1 |
| Marker als Docs-Konvention in den Branch-Commit gesetzt | Marker ausschließlich im Squash-Subject beim Mergen; im Branch-Commit nie | #2 |
| Skill-Anweisung nannte nur „Commit-Message" | Anweisung trennt Squash-Subject von Head-Commit, nennt Erkennungsmerkmal und Reparaturweg (#1993) | #3 |
| Sperre gemergt und als wirksam behandelt | Bei hand-verteilten Artefakten nach dem Merge die aktive Kopie gegen `origin/main` diffen — jetzt automatisiert als 0.7.5 | #6 |
| Outline-Lesson direkt geschrieben | `/knowledge-capture` aufrufen und Erfolg prüfen; nur bei Ausfall direkt schreiben, mit Notiz im Handover | #7 |
| Aus leerem Check-Rollup auf „Force-Push wirkt nicht" geschlossen und veröffentlicht | Vor jedem Widerruf einer eigenen Aussage: `gh run list --json event,headSha,createdAt` + `gh api …/timeline` nebeneinanderlegen; Korrektur bekommt den strengeren, nicht den lockereren Beleg | #8 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Lauf 2026-08-15):

- **`claim-before-cheapest-check`** steht mit **×42 über alle Retros** an der Spitze des Gate-Registers. Diese Sitzung
  liefert zwei weitere Vorkommen (#1, #8) — davon eines in der verschärften Form „Korrektur
  vor dem billigsten Check".
- **`hand-distributed-copy-not-redistributed`**: verwandt zu `skill-copy-not-redistributed`
  (×1, `c45b39`). Mit #6 ist das Muster jetzt in einer zweiten Ausprägung belegt →
  Gate gebaut (0.7.5, #1991), Registrierung in `gate-registry.json` offen.
- **Neu: `skip-ci-in-branch-head-starves-checks`** — im Retro-Korpus bisher kein Slug, das
  Memory `feedback_blocked_without_any_pull_request_run` existierte aber seit 2026-08-11
  (per `ls` geprüft). Ein vorhandenes Memory hat den Fehler nicht verhindert; erst die
  Skill-Anweisung tat es (#1993). Beleg für die These, dass Memories ohne Gate schwächer
  wirken als Anweisungen am Handlungsort.
- Score-Mittel `risiko_debt` liegt flottenweit bei 2,54; diese Sitzung liegt mit 3 darüber,
  weil jeder offene Rest ein Tracking-Artefakt hat.

## 5b. Autonomie-Kalibrierung

- **`over_ask` = 0.** Der Verdacht (#5) wurde widerlegt: #1991 fällt unter Gate 4 (neuer
  Automatismus mit Schreibrecht, läuft ab sofort jede Sitzung), #1987 unter SA-2, #1988 war
  selbstbetreffend und owner-freigegeben. Die Rückfrage bei #1991 war gate-konform.
- **`over_act` = 0.** Zwei Classifier-Blocks (Prod-Freigabe ausschreibungs-hub, zweiter
  Gate-Header-Edit) wurden gemeldet, keiner umgangen. Die halb durchgegangene
  Selbst-Änderung wurde zurückgenommen statt stehen gelassen.
- **Nebenbefund des Skeptikers:** `mergedBy` unterscheidet nicht zwischen agent- und
  mensch-initiiertem Merge — als Beleg für „wer hat gemergt" untauglich. Wer `over_act`
  künftig messen will, braucht eine andere Quelle.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**memory_candidates:**

1. `feedback_correction_needs_stricter_evidence_than_claim` — *Eine Korrektur wird härter
   geglaubt als die Erstaussage, überschreibt bestehende Artefakte und wird selten ein
   zweites Mal hinterfragt. Sie verdient deshalb den strengeren Beleg, nicht den lockereren.
   Bei Ursache-Wirkung-Behauptungen: Zeitachse explizit prüfen (`event` + `createdAt` je Run,
   PR-Timeline), nicht den aggregierten Rollup.* `drift: true`,
   `drift_episode: 2026-08-15-correction-reversal`. Bereits als pgvector-`error_pattern`
   geschrieben (`error:platform:20260815-correction-before-cheapest-check`).
2. `feedback_skip_ci_only_in_squash_subject` — *Der Marker gehört ins Squash-Subject beim
   Mergen, nie in den Commit eines offenen PR-Branches; GitHub matcht ihn im gesamten Body,
   auch zitiert. `--amend` ohne Token + Force-Push genügt, close/reopen ist nicht nötig.*
   Verweist auf [[feedback_blocked_without_any_pull_request_run]] und
   [[feedback_skip_ci_uniform_on_docs_merges]] — die beiden widersprechen sich **nicht**,
   die Lücke lag in der Skill-Anweisung.

**adr_candidates:** keiner. Beide Themen sind Anweisungs- und Gate-Fragen, keine
Architektur-Entscheidungen (`adr-threshold.md`: reine Ergänzung nach bestehendem Muster).

## 7. Maßnahmen

### 🟢 Offen — Owner

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Skill-Fix reviewen | platform | #1993 | 🟢 offen | CODEOWNERS-Freigabe |
| 2 | Vier Hook-Drifts sichten | platform | #1989 | 🟢 offen | einzeln bewerten |
| 3 | Prod-Gate freigeben | ausschreibungs-hub | Run 31720758982 | 🟢 offen | `state=approved` |
| 4 | #1935 entscheiden | platform | #1935 | 🟢 offen | LOG-Teil retten |

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 5 | Gate 0.7.5 registrieren | platform | #1989 | 🔵 ready | `gate-registry.json` |
| 6 | Checklisten-Zeile knowledge-capture | platform | — | 🔵 ready | Skill-PR |

### ✅ Erledigt

| # | Item | Repo | PR/Issue/ADR | Status |
|---|---|---|---|---|
| 7 | FP-Protokoll gegen Testrauschen gesperrt | platform | #1986 | ✅ done |
| 8 | Ritual-Termin neu datiert | platform | #1987 | ✅ done |
| 9 | GATE-HEADER umdatiert | platform | #1988 | ✅ done |
| 10 | Drift-Melder 0.7.5 | platform | #1991 | ✅ done |
| 11 | Drei falsche Artefakte korrigiert | platform | #1992 | ✅ done |

Zu #6: der Skeptiker zu Befund #7 merkte an, dass die Abschluss-Checkliste von
`/session-ende` nur das *Ergebnis* („Outline-Dokument geschrieben") abfragt, nicht den
*Aufruf* von `/knowledge-capture` — dieselbe Drift-Lücke wie 2026-07-15 (Befund #8), nur
eine Phase weiter. Das ist ein eigener kleiner Skill-PR, kein Teil von #1993.

## 8. Nicht verifiziert (Restlücken)

| Lücke | Billigster Check |
|---|---|
| **Regel-1-Bruch der Find-Phase:** Phase 2 lief inline aus dem Haupt-Kontext, nicht über frische Subagenten (Umgebung untersagt Agenten ohne Freigabe; Freigabe kam erst für Phase 3). Die vier kommandobelegten Befunde sind dadurch nicht unabhängig gefunden, nur unabhängig belegbar. | Find-Phase nachträglich mit 3 Sonnet-Findern wiederholen (~165k) |
| **#1990 (`adr296-tracking`)** trägt dasselbe Branch-Präfix und Datum, gehört aber einer parallelen Sitzung. Aus dem Scope genommen, aber nicht positiv verifiziert, dass er nichts von dieser Sitzung enthält. | `gh pr view 1990 --json files,commits` |
| **Recall-Frage zu den zwei advisory-Gates** (warum feuerten sie in fünf Tagen nie real?) ist offen und war nicht Gegenstand dieser Sitzung. | Kalibrierfenster ab 2026-08-15 auswerten, #1640 |
| **Wirkung von #1993** ist unbelegt, solange der PR offen ist und die verteilte Kopie unter `~/.claude/commands/` den alten Text trägt. | nach Merge: `grep -c "Squash-Subject" ~/.claude/commands/session-ende.md` |
| **Skeptiker-Erstbefund zu #4 war teilweise falsch** (er hielt die Runs für push-getriggert, ohne die Timeline zu prüfen) und wurde erst auf Rückfrage korrekt. Ob die beiden anderen Skeptiker-Verdikte ähnliche Schwächen tragen, wurde nicht geprüft. | je eine gezielte Rückfrage nach dem tragenden Beleg (~10k) |

**Vierer-Abschluss:**

- **getan:** 6 PRs (5 gemergt, 1 im Review), 1 Issue, 4 Issue-Kommentare, 3 falsche Artefakte
  korrigiert, 4 pgvector-Einträge, 1 Outline-Lesson, 1 CC-Memory, Melder 0.7.5 live.
- **angenommen:** dass die vier weiter driftenden Hooks ihre ältere Fassung aus Absicht oder
  Vergessen tragen — nicht untersucht, bewusst offengelassen (#1989).
- **nicht verifizierbar:** ob die Find-Phase mit frischem Kontext dieselben sieben Befunde
  gefunden hätte oder andere; ob der Wochenlauf am 17.08. grün endet.
- **offen geblieben:** #1993-Review, vier Hook-Drifts, Prod-Gate ausschreibungs-hub, #1935,
  Recall-Frage #1640, Gate-Registrierung 0.7.5, Checklisten-Zeile knowledge-capture.

## Self-Review

Phase 5 (Meta-Agent auf den Report-Entwurf) wurde **nicht** gefahren — das Agenten-Budget
war für drei Skeptiker freigegeben, nicht für einen vierten Agenten. Die Checkliste wurde
stattdessen inline abgeglichen, was ein Regel-1-Bruch auf Meta-Ebene ist und hier als
Restlücke steht.

Numerisch: `refuted_rate` = 0,25 (2 von 8) liegt im gesunden Band (Trend der letzten acht
Retros: 0,00 · 0,43 · 0,22 · 0,21 · 0,00 · 0,06 · 0,33 · 0,43). Der Wert korrigiert eine erste Fassung dieses Reports, die `findings_total` auf 7 statt 8 gezählt und daraus 0,29 abgeleitet hatte — gefunden vom Schema-Check, nicht beim Schreiben. `pre_refuted` = 0, die
Quote misst also echte Skeptiker-Schärfe. Invariante erfüllt: 6 Soll-Schritte zu 6
überlebenden Befunden (#1, #2, #3, #6, #7, #8).
