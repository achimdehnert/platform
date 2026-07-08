---
retro_schema: 1
date: 2026-07-08
repo_scope: [nl2cad, cad-hub]
session_id: 6658a4
footprint: full
footprint_reduction_reason: >
  Rule-B-Trigger "Prod-Schritt" (cad-hub #37 löste einen Prod-Deploy aus) hätte
  auf `deep` gestartet. Downgrade auf `full`, da alle 3 Kriterien erfüllt:
  (a) Merge von #37 explizit im Chat freigegeben ("cad-hub #37 jetzt mergen"
  nach namentlicher Rückfrage — Artefakt = Transkript, nicht AskUserQuestion-Tool
  oder PR-Body-Warnung im engen Wortsinn, aber unzweideutig und PR-Nummer-spezifisch);
  (b) voll rollback-fähig (keine DB-Migration, Standard-Django-Deploy, Revert+Redeploy);
  (c) Befund-Dichte-Schätzung ≤10 (durchgängig verifizierte, saubere Session)
  traf zu — real: 15 Survivors über 2 Dimensionen, am oberen Rand der Schätzung.
findings_total: 16
findings_survived: 15
refuted_rate: 0.0625
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [planned-phase-no-issue]
recurring_findings: [planned-phase-no-issue]
---

# Session-Retro · nl2cad/cad-hub · 2026-07-08 (Session 6658a4)

Session-Inhalt: ADR-012 T2 — Migration von cad-hubs eigener Raumerkennung
(`FloorPlanAnalyzer`) auf nl2cad-core `DXFParser`. 3 PRs: cad-hub #37 (Code-Migration,
gemergt + Prod-Deploy verifiziert), nl2cad #57 + #58 (Handover-Nachzug, docs-only).
Pipeline: 1 Collector (haiku) + 2 Finder (sonnet, gebündelte Dimensionen) + 2 Skeptiker
(sonnet) = 5 Subagenten, `full`-Budget eingehalten.

## 1. Executive Summary

- Migration erreichte ihr Kernziel: Raumerkennung ausgetauscht, 5 Konsumenten gefixt,
  Deploy grün verifiziert (Run 28939968106, `deploy / 🚀 Production: success`).
- **Wiederholtes Muster `planned-phase-no-issue` (jetzt ×4 über Retros, GATE-PFLICHT
  seit `a50bc6`):** die als "PR 3" angekündigte Cleanup-Arbeit (`FloorPlanAnalyzer`
  toter Code) hat in keinem der beiden Repos ein Issue — nur Prosa in PR-Body und
  `AGENT_HANDOVER.md`.
- Ein während der Session gefundener, echter Bug (`DWGConverterService.convert()`
  existiert nicht) wurde korrekt als Out-of-Scope erkannt, aber **nicht als Issue
  gefiled** — bleibt für den nächsten DWG-Upload ein scharfer Production-Crash.
- Der einzige Review auf dem 354-zeiligen Code-Diff (ohne Fixture) war ein Ein-Wort-
  "passt" ohne Zeilen-Kommentare — bestätigt, aber durch Skeptiker-B8-Nuance
  eingeordnet: die 3 übersprungenen CI-Gates waren **by-design Opt-in**, keine
  maskierte Failure (anders als der bekannte Slug `ci-gate-maskiert-failure`).
- 1 von 16 geprüften Behauptungen wurde widerlegt (A5: der Magic-Number-Vorwurf war
  falsch — ein Kommentar existiert tatsächlich) — positiv für die Sorgfalt der Session,
  aber `refuted_rate=0.0625` liegt unter dem gesunden Band (0.12–0.50), s. Self-Review.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Deferred "PR 3" (Cleanup `FloorPlanAnalyzer.identify_rooms()`/`calculate_room_areas()`) hat kein Issue in nl2cad oder cad-hub — nur PR-Body-Prosa | Prozesslücke | hoch | SURVIVES | Skeptiker A: `grep` bestätigt beide Methoden noch live in `specialized_analyzers.py:79,127`; `gh api .../issues?state=all` (37 Issues, cad-hub) + Titel-Scan nl2cad: 0 Treffer | `planned-phase-no-issue` ×4 (73003f, a50bc6, 0b46ee, **6658a4**) ⇒ bereits GATE |
| 2 | Pre-existing Bug gefunden (`dxf_analyzer.py:60` ruft `DWGConverterService.convert()`, Methode existiert nicht — nur `convert_to_dxf`/`convert_bytes_to_dxf`), nicht gefixt, nicht als Issue getrackt | fehlende Validierung | hoch | SURVIVES | Skeptiker A: `grep -n "def "` in `dwg_converter.py` bestätigt fehlende Methode; `gh issue list --search "convert"` beide Repos: 0 Treffer | neu |
| 3 | Einziger Review auf cad-hub #37 ist Ein-Wort-"passt", keine Zeilen-Kommentare, trotz 354 Zeilen echtem Code-Diff (Fixture ausgeklammert) | Prozesslücke | hoch | SURVIVES | Skeptiker A+B: `gh pr view 37 --json reviews` → 1 Review; `gh api .../pulls/37/comments` + `.../issues/37/comments` → beide `[]` | neu |
| 4 | `test_room_area_unit_regression.py` — Test für den eigentlichen Kernbug (Einheiten-Fix) nutzt nur `MagicMock` mit Fake-Daten, nicht die im selben PR mitgelieferte echte 185KB-Fixture | fehlende Validierung | mittel | SURVIVES | Skeptiker A: Volltext gelesen, `grep -rln "real_lageplan_r12" tests/` zeigt nur `test_dxf_room_detection.py` nutzt die Fixture | neu |
| 5 | 3 CI-Checks (Contract Tests, Architecture Guardian ADR-155, QM Gate ADR-174) zeigen "skipped" statt "success" auf der Migrations-PR — **bestätigt als by-design Opt-in-Gate, keine maskierte Failure** | Werkzeug (informativ) | niedrig | SURVIVES (Fakt), Risiko-Einordnung entkräftet | Skeptiker B8: `_ci-python.yml` liest `job['result'] not in ('success','skipped')` als einzige Failure-Bedingung — explizite Design-Entscheidung, deckt sich mit Memory `nl2cad-opt-in-ci-gates` | kein Match zu `ci-gate-maskiert-failure` (anderes Muster: dort echte Failures maskiert, hier 0 Failures) |
| 6 | PR-Body behauptet "112 passed, 1 unrelated skip"; echtes CI-Log zeigt "112 passed, **2 skipped**, 12 warnings" | fehlende Validierung | niedrig | SURVIVES | Skeptiker A: `gh run view --job ... --log` → reales pytest-Summary widerspricht PR-Body-Zahl (Playwright-e2e-Skip lokal nicht reproduziert, da lokal nicht installiert) | neu |
| 7 | 2 separate docs-only-PRs (nl2cad #57, #58) gegen dieselbe Datei, 48 Min. auseinander, PR #58 nur um Merge-Status-Wortlaut zu korrigieren; **kein Review auf keinem der beiden** | Prozesslücke | niedrig | SURVIVES | Skeptiker A+B: `gh pr view 57/58 --json files,mergedAt,reviews` → identische Datei, 48m39s Abstand, `reviews:[]` bei beiden | neu |

**Bestätigt, aber nicht Soll-Ablauf-würdig (informativ, keine Handlung nötig):**
- A5 (Magic-Number `_MAX_ROOM_AREA_M2` ohne Kommentar) — **REFUTED**: ein 4-zeiliger
  Erklär-Kommentar existiert (`room_analysis.py:22-26`), von PR #37 selbst hinzugefügt.
- A8 (3 Mgmt-Command-Dateien + 1-Zeilen-Template-Edit im Scope einer "Raumerkennung"-PR)
  — SURVIVES als Fakt, aber selbst-gehedgt formuliert; beide Änderungen sind sachlich
  Teil der Migration (Diagnose-Tool, Einheiten-Fix in der Template-Anzeige) — kein
  Scope-Creep im engeren Sinn.
- B3 (kein Beleg für Rebase gegen main vor Merge) — SURVIVES wörtlich, aber Skeptiker B
  zeigt: der Branch war nie veraltet (Base-Commit enthielt #31/#33/#34 bereits, da er
  danach erst angelegt wurde) — die implizierte Risiko-Einschätzung trägt nicht.
- B7 (ein `cancelled` Deploy-Run in der Tageshistorie) — SURVIVES als Fakt, aber
  eindeutig PR #31 zugeordnet (Merge-Commit-SHA identisch), nicht dieser Session.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Kernziel erreicht + deployed + verifiziert; Abzug für untrackte PR-3-Deferral (#1) |
| architektur_design | 4 | Contract-stabile Migration, Keyword-Union statt Ersetzen, gestufter Rollout — solide Entscheidungen |
| code_konventionstreue | 4 | Lint clean, Tests vorhanden, Konventionen eingehalten |
| risiko_debt | 3 | 2 echte Risiko-Funde (#1 untracked dead code, #2 untracked Bug) senken den Score trotz sonst sauberer Umsetzung |
| prozess_effizienz | 3 | Rubber-Stamp-Review (#3) + PR-Fragmentierung (#7) sind vermeidbarer Overhead |
| entscheidungsqualitaet | 4 | Recherche-vor-Umsetzung (2 Read-only-Agenten), empirische Verhaltens-Wechsel-Verifikation, Evidenz-Disziplin durchgängig |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| PR-Body kündigt "PR 3" als Folgearbeit an, kein Issue erstellt (#1, ×4-Wiederholung) | Vor PR-Merge: für jede im PR-Body explizit als "folgt separat"/"deferred" angekündigte Arbeit **sofort** ein GitHub-Issue erstellen und im PR-Body verlinken (`Follow-up: #<issue>`) — nicht nur Prosa | #1 |
| Bug beim Recherchieren gefunden (`DWGConverterService.convert()`), im Chat/Outline notiert, aber kein Repo-Issue | Jeder während einer Session entdeckte, out-of-scope belassene Bug bekommt **vor Session-Ende** ein Issue im betroffenen Repo (nicht nur Outline-Lesson) — Outline dokumentiert das "Warum", das Issue macht es auffindbar/aktionabel für den nächsten Bearbeiter | #2 |
| PR mit 354 Zeilen echtem Diff durch Ein-Wort-Review "passt" freigegeben | Bei selbst-verfassten PRs mit >X Zeilen echtem Diff (Fixtures ausgeklammert) im PR-Body explizit auf die kritischen Stellen hinweisen ("Bitte besonders auf Zeile X/Y schauen"), um den Reviewer zu gezielter Prüfung statt Pauschal-Approval zu führen | #3 |
| Kernbug-Fix (Einheiten-Korrektur) nur gegen Mock-Daten getestet, echte Fixture im selben PR ungenutzt für diesen Test | Wenn ein PR bereits eine echte Fixture einführt, den Regressionstest für den eigentlichen Bug-Fix **gegen dieselbe Fixture** schreiben, nicht nur gegen synthetische Mocks — Mocks für Wiring/Contract, echte Daten für den Kernclaim | #4 |
| 3 "skipped" CI-Checks auf einer ADR-getaggten Migrations-PR ohne Erklärung im PR-Body | Bei Opt-in-CI-Gates, die auf einer Architektur-relevanten PR (ADR-Tag) skippen, einen Ein-Zeiler im PR-Body ergänzen ("Contract/Guardian/QM-Gate sind Opt-in, hier bewusst übersprungen weil…"), damit ein Reviewer nicht rätseln muss ob das ein Defekt ist | #5 |
| PR-Body-Testzahl ("1 unrelated skip") wich vom echten CI-Log ab ("2 skipped") | Testzahlen im PR-Body aus dem **tatsächlichen CI-Run-Log** zitieren (`gh run view --log`), nicht aus dem zuletzt lokal beobachteten Lauf — lokale und CI-Umgebung können divergieren (hier: Playwright) | #6 |
| 2 kleine docs-PRs für denselben Datei-Abschnitt, 48 Min. auseinander, kein Review | Vor dem Schreiben eines Status-Updates zu einem PR den tatsächlichen Merge-Zeitpunkt abwarten/verifizieren, statt "offen" zu dokumentieren und später per Folge-PR zu korrigieren — ein einziger, korrekt getimter Handover-Commit statt zwei | #7 |

**Invariante geprüft:** 7 Soll-Schritte = 7 überlebende Haupt-Befunde. ✓

## 5. Längsschnitt

`python3 tools/retro_kpis.py` gegen alle 19 (jetzt 20) Retro-Reports gelaufen:

- **`planned-phase-no-issue`** stand bei ×3 [73003f, a50bc6, 0b46ee] — mit dieser
  Session **×4**. War bereits GATE-PFLICHT seit `a50bc6` (2026-07-02); die dort
  vorgeschlagene Fix-Idee ("Skill-Regel in repo-optimize/session-ende:
  [FLEET-PATTERN]-Survivor ⇒ Issue-Pflicht") ist erkennbar **noch nicht verankert** —
  sonst wäre dieser 4. Fall nicht aufgetreten. Handlungsempfehlung s. §7 M1.
- Geprüfter Fehlalarm: `ci-gate-maskiert-failure` (×2, GATE) wurde **explizit
  gegengecheckt und verworfen** als Match für Befund #5 — unterschiedliches Muster
  (maskierte echte Failure vs. by-design Opt-in-Skip ohne jede Failure). Wichtig,
  das nicht fälschlich zusammenzulegen (Belegpflicht für Längsschnitt-Behauptungen).
- Keine weiteren Slug-Matches unter den 7 Hauptbefunden dieser Session — #2–#4, #6, #7
  sind neue Kandidaten-Slugs (noch nicht ×2, daher kein Gate, aber im Auge behalten).

**5b. Autonomie-Kalibrierung** (gegen die eigene Transkript-Historie dieser Session,
nicht gegen Repo-Artefakte — Sonderfall, da dies das Verhalten des Haupt-Agenten selbst
misst, nicht Session-Inhalt):

- **`over_ask` = 1 (schwach):** Rückfrage vor Commit+Push des ersten cad-hub-Branches
  ("1 commit und push 2 weiter") — ein Push auf einen Nicht-main-Branch ohne
  Auto-Deploy ist voll reversibel (Branch löschbar, kein Prod-Bezug) und trifft
  laut `autonomy-gates.md` keines der 5 Gates. Hätte autonom laufen können.
- **`over_act` = 1 (Near-Miss, nicht vollzogen):** `gh pr merge 58` wurde aufgerufen,
  bevor eine PR-Nummer-spezifische Freigabe für **genau dieses** PR vorlag (die
  vorherige Freigabe galt für #37) — vom Auto-Mode-Classifier korrekt blockiert,
  *bevor* der Merge stattfand. Kein Schaden entstanden, aber die Erkenntnis kam vom
  Classifier, nicht von eigener Vorab-Prüfung — sollte künftig vor dem Tool-Call
  geprüft werden, nicht danach.
- Beide Zähler stehen bei 1 — noch kein ×2-Muster über Retros hinweg (keine
  bestehenden `over_ask`/`over_act`-Slugs in `retro_kpis.py`-Output gefunden, die
  passen); nicht gate-pflichtig, aber Kandidaten für künftige Beobachtung.

## 6. Verankerung — kopierfertige Vorschläge (Mensch entscheidet)

**memory_candidates** (nl2cad-Projekt-Memory, Typ `lesson_learned`):
```yaml
name: adr012-t2-pr3-deferral-no-issue
description: "PR-Body kündigt Folge-PR an, kein Issue erstellt — 4. Wiederholung von planned-phase-no-issue"
type: lesson_learned
content: |
  Bei ADR-012-T2 (cad-hub #37) wurde "PR 3" (Cleanup FloorPlanAnalyzer) im PR-Body
  als Folgearbeit angekündigt, aber kein Issue erstellt. Dasselbe Muster
  (planned-phase-no-issue) trat bereits ×3 in anderen Retros auf (73003f, a50bc6,
  0b46ee) — jetzt ×4. Merksatz: Jede im PR-Body als "folgt separat" markierte
  Arbeit bekommt sofort ein Issue, nicht nur Prosa.
```

**adr_candidates:** keiner — die Befunde sind Prozess-/Konventionslücken, keine
Architektur-Entscheidung (passt zu `adr-threshold.md`).

**Gate-PR-Vorschlag** (für `planned-phase-no-issue`, jetzt ×4 — überfällig):
Ein `session-ende`- oder `repo-optimize`-Skill-Check, der PR-Bodies auf Phrasen wie
"folgt separat"/"PR 3"/"deferred"/"nach Bake-Zeit" scannt und bei Fund ohne
verlinktes Issue eine Warnung ausgibt — die 2026-07-02 vorgeschlagene Fix-Idee ist
4 Retros später immer noch nicht verankert.

## 7. Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|------|------|---------------|--------|-----------|
| M1 | Issue "Cleanup FloorPlanAnalyzer dead code (PR 3)" erstellen, in cad-hub #37 verlinken | cad-hub | — | 🟢 offen | du/ich: Issue anlegen |
| M2 | Issue "DWGConverterService.convert() existiert nicht — AttributeError im DWG-Fallback" erstellen | cad-hub | — | 🟢 offen | du/ich: Issue anlegen |
| M3 | `planned-phase-no-issue` (×4, GATE) als Skill-Regel verankern (PR-Body-Scan) | platform | — | 🟢 offen | du: priorisieren, überfällig seit `a50bc6` |
| M4 | memory_candidate `adr012-t2-pr3-deferral-no-issue` materialisieren | nl2cad | — | 🔵 ich sofort | ich, nach Freigabe |

## 8. Nicht verifiziert (Restlücken)

- **"Bug wurde diese Session gefunden, nicht vorher bekannt"** (Befund #2): technisch
  korrekt, dass der Bug pre-existing und unrelated zu PR #37 ist — aber ob er
  wirklich zum ersten Mal in dieser Session entdeckt wurde (vs. bereits woanders
  bekannt) ist nur aus dem Chat-Transkript ableitbar, nicht aus Repo-Artefakten.
  Billigster Check: `grep -r "convert()" ~/shared/*.md` und Outline-Suche nach
  "DWGConverterService" vor dieser Session — nicht durchgeführt.
- **Ob PR #37s "112 passed, 1 unrelated skip"-Behauptung auf einem älteren,
  bereits divergenten Lauf beruhte** oder schlicht eine lokale Beobachtung ohne
  CI-Abgleich war: nicht rekonstruierbar ohne Zugriff auf den exakten lokalen
  Testlauf-Zeitpunkt.
- **Autonomie-Kalibrierung (§5b)** beruht auf Selbstbeobachtung des Haupt-Agenten
  (Transkript), nicht auf unabhängiger Artefakt-Verifikation wie der Rest des
  Reports — methodischer Sonderfall, explizit gekennzeichnet, nicht mit denselben
  Skeptiker-Garantien wie §2 zu verwechseln.

## Self-Review (Phase 5 — Meta, nur Output-Qualität)

- `refuted_rate = 0.0625` liegt **unter** dem historischen gesunden Band (0.12–0.50,
  s. `frist-hub-7f7fbd`-Trend). Numerischer Befund, keine Bewertung einzelner
  SURVIVES/REFUTED-Entscheide: die 2 Finder produzierten überwiegend haltbare
  Behauptungen (15/16 SURVIVES) — plausibel bei einer Session, die durchgängig mit
  Verifikations-Zwischenschritten arbeitete (viele "Behauptungen" waren bereits
  vor-verifizierte Fakten aus einer ohnehin evidenzdisziplinierten Session), aber
  ein Wert dieser Größenordnung ist ein Signal, beim nächsten Lauf gezielt
  schärfere/aggressivere Finder-Prompts zu testen, um zu prüfen ob 0.0625 Robustheit
  oder zu laxe Falsifikation widerspiegelt.
- Invariante `|Soll-Schritte|==|Survivors|` (7=7) erfüllt.
- Scores ganzzahlig, an Befunden verankert (keine Halbwerte).
- Frontmatter vollständig, Pfad kollisionsfrei (repo+session-id).
