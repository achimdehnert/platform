---
retro_schema: 1
date: 2026-07-05
repo_scope: [nl2cad]
session_id: e623cd
footprint: full
findings_total: 8
findings_survived: 7
refuted_rate: 0.13
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 4
  entscheidungsqualitaet: 4
gate_candidates: [claim-before-cheapest-check, lint-failure-no-local-gate, phantom-ci-gate-skip-only]
recurring_findings: [claim-before-cheapest-check, lint-failure-no-local-gate]
---

# Session-Retro — nl2cad Audit-Remediation + Kalkulations-Konzept (2026-07-03…07-05)

Methode: 4 Eiserne Regeln (Richter≠Angeklagter). 1 Collector (haiku) + 3 Finder + 2 Skeptiker
(sonnet, frischer Kontext, unabhängig aus main gezogen). Synthese inline. In-Scope: PRs #26–#34
(gemergt) + #42 (offen, Konzept). Out-of-Scope (andere Sessions am 04.07.): #35–#41.

## 1. Executive Summary
- **9 PRs (#26–#34) sauber**: alle grün gemergt, kein Merge-auf-Rot, kein unabsichtliches Dangling,
  Fixes im Code stichprobenverifiziert (nicht nur PR-Prosa). Sequenzielle Cluster-Kadenz war
  **sachlich geboten** (Datei-Hotspots — Bündelung hätte echte Konflikte erzeugt, Finder 3 falsifizierte
  die Anti-Pattern-Hypothese selbst).
- **Kern-Schwäche: Phantom-CI-Gates.** Zwei zentrale „validiert"-Claims (GAEB-XSD-Validität, Golden-
  Realdaten) laufen in CI **nur im Skip-Pfad** → kein Regressionsschutz. Der XSD-Claim war zum Merge
  lokal echt belegt (Herabstufung kritisch→hoch), aber ohne CI-Gate.
- **Ein REFUTED**: die Behauptung „~2/3 der Audit-Befunde in keinem PR-Body erwähnt" fiel — #27 nennt A7,
  #32 nennt B8 explizit als bewusste Folgearbeit (Richter≠Angeklagter fing die Finder-Übertreibung).
- **Zwei bereits gate-pflichtige Längsschnitt-Muster wiederholt**: `lint-failure-no-local-gate` (#34 mypy)
  und `claim-before-cheapest-check` (schema-valide nur lokal) — je ≥2 über Retros (`retro_kpis.py`).
- **Restdebt neu**: hartkodierte MwSt gegen eigene Konvention (E4); BGF/BRI-Analyzer ohne Konsumenten (E6).

## 2. Befund-Tabelle
| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| E1 | „schema-valide"-Claim (#34) ohne CI-Regressionsschutz — `xmlschema` keine Dependency, XSD-Test nur via `GAEB_XSD_DIR` (Skip in CI); Validierungslogik selbst echt, Lizenz-Restriktion begründet Opt-in | fehlende Validierung | hoch | SURVIVES (kritisch→hoch) | `test_gaeb_da_xml_33.py:221-248`; `grep GAEB_XSD .github/workflows`=0; `grep xmlschema */pyproject.toml`=0 | claim-before-cheapest-check ≥2 |
| E2 | Golden-Realdaten-CI-Job läuft nur im Skip-Pfad — Secret `NL2CAD_TESTDATA_URL` nie gesetzt; alle „Realdaten-Wirkung"-Tabellen sind Session-Einmalmessungen | fehlende Validierung | hoch | SURVIVES | `ci.yml:113,118,129`; `gh secret list`=ohne NL2CAD_TESTDATA_URL | phantom-ci-gate-skip-only |
| S3 | #32 reparierte nur eine von zwei konkurrierenden GK-Logiken — `core/analyzers/brandschutz_analyzer.py:234` (BGF/Geschosszahl) widerspricht weiter `nl2cad-brandschutz/gebaeudeklasse.py` (OKFF/NE) | fehlende Validierung | mittel | SURVIVES | `brandschutz_analyzer.py:234-244` `_determine_gebaeudeklasse(bgf_m2, floor_count)` vs. `gebaeudeklasse.py:144-220` `ermittle(...ne_flaechen_m2)`; beide auf main, divergente Kriterienbasis | contradictory-duplicate-partial-fix |
| E4 | MwSt `0.19`/`1.19` 4× hartkodiert (1.19 neu aus #31), gegen eigene Konvention „keine Konstanten in Business-Logik" (für DIN/MBO/ASR umgesetzt) | verfrühte Festlegung | mittel | SURVIVES | `gaeb/models.py:83`+`generator.py:199` ×2 Kopien; `git blame`→e9566c0; `core/constants.py:5` | hardcoded-vs-own-convention |
| E6 | BGF/BRI-`GebaeudeKennzahlenAnalyzer` (#33) ohne Produktions-Konsument — nicht in `handlers/massen.py` verdrahtet, kein Registry/Pipeline | neue Tech-Debt | mittel | SURVIVES | `grep -rln`=nur Def+Reexport+3 Tests; massen.py referenziert nicht | dead-end-analyzer |
| S1 | #42/Gap-Analyse behandeln nur die Kalkulations-Hälfte des Audit-Doppelziels; kein Rückverweis „Brandschutz/Fluchtwege bleibt offen" (Verengung war user-geframt + in Gap-Analyse sichtbar → nicht „still") | Prozesslücke | mittel | SURVIVES (kritisch→mittel) | `grep flucht/brandschutz` in #42-Diff=0; Gap-Analyse Z.1-4 user-geframt, Z.21 Brandschutz sichtbar | tracking-misses-original-goal |
| P7 | #34 CI-Lint+mypy-Failure → Fix-Push nötig (65s); kein lokaler mypy-Gate vor Push | Werkzeug | niedrig | SURVIVES | `gh run`: fail cafb435 → success e356de8; Drift-Memory `ci-ruff-format-check-gotcha` | lint-failure-no-local-gate ≥2 |
| S2 | „~2/3 der Audit-Befunde in keinem PR-Body erwähnt" | Prozesslücke | (mittel) | **REFUTED** | #27-Body nennt A7, #32-Body nennt B8 explizit als Folgearbeit; nur A12 wirklich unerwähnt | — |

## 3. Scorecard (1–5, an Befunden verankert)
| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Kalkulations-Quartett real gefixt + code-verifiziert; Doppelziel-Brandschutzhälfte offen (S1), GK-Fix partiell (S3) |
| architektur_design | 3 | gute Muster (provenance/coverage/fail-loud), aber byte-Copy institutionalisiert + E6 totes Feature-Ende + E4 |
| code_konventionstreue | 3 | E4 verletzt die eigene „keine Konstanten"-Konvention direkt; sonst ruff/Tests sauber |
| risiko_debt | 3 | neue Debt E4/E6 + Phantom-Gates E1/E2 (falsches Vertrauen), aber alles reversibel+dokumentiert |
| prozess_effizienz | 4 | saubere Kadenz (Hotspot-gerechtfertigt), kein Merge-auf-Rot; einziges Rework P7 (89s Rebase #31, 65s mypy #34) |
| entscheidungsqualitaet | 4 | überwiegend belegt+konservativ; #42-Konzept mit adversarialem Dreiklang stark; Abzug E1/E2/S1 |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #) — |Soll| = |Survivors| = 7
| Ist (belegt) | Soll | eliminiert |
|---|---|---|
| „schema-valide" nur lokal via `GAEB_XSD_DIR` validiert, kein CI-Pfad | Für lizenz-restringierten Validierungs-Input CI-Pfad via Secret+Download bauen (Muster golden-realdata) ODER fehlenden Schutz als „kein CI-Gate"-Issue führen — nicht als „validiert" abschließen | #E1 |
| golden-realdata-Job läuft nur im Skip-Pfad (Secret nie gesetzt) | Nach Einführung eines gated CI-Jobs Secret setzen + EINEN echten Nicht-Skip-Lauf als Nachweis erzwingen, bevor er als „Gate" zählt | #E2 |
| #32 fixte 1 von 2 GK-Logiken, ließ core/analyzers:234 divergent | Bei Fix an 1 von N konkurrierenden Implementierungen alle N per `grep` auflisten + mitfixen ODER als Issue mit Datei:Zeile anlegen (nicht nur PR-Body) | #S3 |
| MwSt 4× hartkodiert gegen eigene Konvention | Steuersatz + GAEB-Konstanten nach `core/constants.py` (Quelle/Stand wie DIN/MBO); byte-Copy über echte Package-Dep auflösen | #E4 |
| BGF/BRI-Analyzer ohne Konsument gemergt | Neues Analyzer-Feature im selben PR an ≥1 Konsument (massen.py/Report) anschließen ODER „nicht verdrahtet"-Issue, nicht als fertig behandeln | #E6 |
| Gap-Analyse/#42 verengt Doppelziel ohne Rückverweis | Greift eine Folge-Frage ein Teilziel eines dokumentierten Gesamtziels auf → im Abschlussartefakt expliziter „offen aus Ursprungsziel: X"-Satz | #S1 |
| #34 mypy-CI-Failure, kein lokaler mypy-Gate | Pre-Push-Gate auf `ruff format --check` UND `mypy` erweitern (Drift-Memory `ci-ruff-format-check-gotcha` generalisieren) | #P7 |

## 5. Längsschnitt (retro_kpis.py über alle platform/docs/retros/)
- **Gate-pflichtig re-instanziiert (≥2 über Retros):** `claim-before-cheapest-check` (E1 — Claim „schema-valide"
  ohne unabhängigen CI-Check; genau die Familie der evidence-discipline-Policy Punkt 5/6) und
  `lint-failure-no-local-gate` (P7 — mypy-CI-Failure ohne lokalen Gate; bestehende Drift-Memory
  `ci-ruff-format-check-gotcha` deckt bisher nur `ruff format`, nicht `mypy`).
- **Neuer, verwandter Slug `phantom-ci-gate-skip-only`** (E1+E2): CI-Job existiert, läuft aber strukturell nur
  im Skip-Pfad → grün ohne Deckung. Kandidat für ein CI-Gate „gated Job muss ≥1 echten Nicht-Skip-Lauf
  nachweisen, sonst Warnung".
- `refuted_rate` dieser Session **0.13** — am unteren Band (Präzedenz 0.00 existiert), erklärbar durch saubere,
  freigegebene, reversible Arbeit: die meisten Befunde sind echt (SURVIVES), 1 Übertreibung (S2) sauber
  gefangen, 2 Severity-Downstufungen (E1, S1) in der Beleg-Spalte statt drittem Verdikt.

## 5b. Autonomie-Kalibrierung
- `over_ask`: **0** belegt — die Merge-Freigaben (#26–#34) waren gate-pflichtig (Merge = potenziell Prod-nah,
  hier bewusst je einzeln vorgelegt); das war korrekt, kein Over-Ask.
- `over_act`: **0** — kein autonomer Prod/Publish/3.-Repo-Schritt ohne Freigabe. platform-/nl2cad-Doc-PRs
  wurden offen gelassen (nicht selbst gemergt). Charter nicht zu schärfen.

## 6. Verankerung (kopierfertig — Mensch entscheidet)

**memory_candidates** (nl2cad Auto-Memory):
```markdown
---
name: nl2cad-phantom-ci-gates
description: Zwei "validiert"-Claims (GAEB-XSD, Golden-Realdaten) laufen in CI nur im Skip-Pfad — kein Regressionsschutz
metadata: {type: feedback}
drift: true
drift_episode: 2026-07-05-phantom-ci-gate
---
GAEB-XSD-Validierung (test_gaeb_da_xml_33.py, GAEB_XSD_DIR) und Golden-Realdaten (ci.yml golden-realdata, Secret NL2CAD_TESTDATA_URL) sind opt-in und laufen in CI IMMER im Skip-Pfad → "schema-valide"/"Realdaten-Wirkung" waren Session-lokale Einmalmessungen, kein CI-Regressionsschutz.
**Why:** lokal-grün wurde mit CI-geschützt verwechselt; Lizenz-/Datengröße-Restriktion (XSDs lizenzpflichtig, Realdaten ~1 GB) begründet Opt-in, aber der fehlende CI-Pfad blieb ungebaut.
**How to apply:** Ein gated CI-Job zählt erst als "Gate", wenn ≥1 echter Nicht-Skip-Lauf nachgewiesen ist (Secret+Download-Pfad wie golden-realdata gedacht, aber Secret nie gesetzt). Siehe [[ci-ruff-format-check-gotcha]].
```

**adr_candidates**: keiner neu — die Packaging-Grundsatzfrage (byte-Copy core↔Schwester, E4-Kontext) ist bereits
als Audit-C1–C3 offen und in KONZ-nl2cad-002 REC-5 als Blocker für `nl2cad-calc` benannt; sie braucht ein
**Datum+Owner** (fehlt bisher), keinen neuen ADR.

## 7. Maßnahmen (Action-Board)
| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| A1 | Phantom-CI-Gates schließen: golden-realdata-Secret setzen + 1 echten Lauf; XSD-CI-Pfad ODER „kein Gate"-Issue | nl2cad | — | 🟢 dein Zug | du: Secret NL2CAD_TESTDATA_URL setzen; ich: dann CI-Pfad/Issue |
| A2 | B8 schließen: zweite GK-Logik in core/analyzers angleichen/entfernen | nl2cad | Issue anlegen | 🔵 ich sofort | ich: Issue mit Datei:Zeile + Fix-PR |
| A3 | MwSt+GAEB-Konstanten nach core/constants.py (E4) | nl2cad | — | 🔵 ich sofort | ich: Fix-PR (klein) |
| A4 | BGF/BRI-Analyzer an massen.py-Handler verdrahten (E6) | nl2cad | — | 🔵 ich sofort | ich: Anbindungs-PR |
| A5 | Pre-Push-Gate `ruff format --check` + `mypy` (P7); Drift-Memory generalisieren | nl2cad | — | 🔵 ich sofort | ich: Memory-Update + optional pre-commit |
| A6 | Gate-pflichtige Slugs (`claim-before-cheapest-check`, `lint-failure-no-local-gate`) — bereits ≥2, gehören als CI/Hook-Gate, nicht als N-tes Memo | platform | retro_kpis-Backlog | 🟢 dein Zug | du: Gate-Priorisierung |
| A7 | nl2cad-Memory `nl2cad-phantom-ci-gates` anlegen (§6) | nl2cad | — | 🟢 dein Zug | du: Verankerung freigeben |

## 8. Nicht verifiziert (Restlücken)
- **A12** (DIN-276-KG-Mapping-Schlüssel) ist laut Skeptiker der einzige der drei Stichproben, der in **keinem**
  PR-Body erwähnt ist — ob die grobe „~2/3 offen"-Schätzung stimmt, wurde NICHT vollständig ausgezählt.
  Billigster Check: Audit-Befundliste gegen alle #26–#34-Bodies diffen.
- **Wirk-Korrektheit der Fixes an Realdaten** über die Session-Einmalmessung hinaus — nicht CI-verifiziert
  (genau E1/E2). Billigster Check: golden-realdata-Secret setzen, echten Lauf ansehen.
- **over_ask/over_act = 0** aus Artefakten geschlossen (Merge-Freigaben im PR-Verlauf sichtbar); die
  Konversations-internen „dein Zug"-Vorlagen wurden nicht transkript-ausgezählt.
