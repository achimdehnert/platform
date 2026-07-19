---
retro_schema: 1
date: 2026-07-19
repo_scope: [writing-hub]
session_id: 11feac
footprint: full
findings_total: 4
findings_survived: 3
refuted_rate: 0.25
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 5
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [always-instruction-without-enforcement, workaround-without-tracking-anchor]
recurring_findings: [always-instruction-without-enforcement, workaround-without-tracking-anchor]
over_ask: 0
over_act: 1
footprint_reduction_reason: "n/a — full ist der Standard; kein Prod-Code/Migration/ADR, aber >2 PRs (8) → nicht lean"
---

# Session-Retro 2026-07-19 — writing-hub: Klickdummy-Schema-Bereinigung

## 1. Executive Summary
- **Kernziel voll erreicht:** #202/#242/#244 geschlossen, alle 14 Klickdummy-Module 0 zentrale Schema-WARNs (von 180+), unabhängig auf pristine `origin/main` reproduziert (Skeptiker + Collector).
- **8 PRs, 100 % CI-grün, kein Prod-Deploy** (durchgehend `klickdummy/**`/docs = cosmetic per `deploy.yml`-changes-Gate — Gate verifiziert wirksam).
- **3 überlebende Befunde, alle Prozess/Governance, keiner kritisch:** (F1) Wizard in 2 CI-Zyklen zum bekannten Endzustand; (F2) Δ12 spec↔MMD-Content-Drift bewusst aufgeschoben, aber nirgends getrackt; (F3) freigabepflichtiges UX-Vertrag-Dokument solo gemergt, Freigabe-Pflicht nirgends erzwungen.
- **F2 + F3 sind Nth-Instanzen bereits gate-pflichtiger Längsschnitt-Slugs** (`workaround-without-tracking-anchor`, `always-instruction-without-enforcement`) — kein neues Memo, sondern Gate-Verankerung fällig.
- **Inhaltsqualität hoch:** grounding/personas/purpose/parity real geerdet (keine Platzhalter), 8 executable Asserts screen-genau + in CI gegen Chromium PASSED.

## 2. Befund-Tabelle
| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|--------|-----------|----------|---------|-------|------------|
| 1 | Wizard erhielt Option B (#249, schloss #244) und 20 Min später Option A (#250) — zwei volle CI-Zyklen für einen Endzustand, den #247 bereits als Empfehlung nannte | verfrühte Festlegung / Prozess | niedrig | SURVIVES | PR #247-Body (empfahl A), #249-Body ("kein parity — wäre A"), #250 additive Diff `85f3e51` (kein Codeverlust). **Mitigation (session-only, Hypothese):** User beauftragte B und A in zwei getrennten Turns explizit — die „Vermeidbarkeit" unterstellt Selbststeuerung; realer Overhead war eine bewusste User-Wahl (erst B, dann A) | ×1 (neu) |
| 2 | Δ12 spec↔MMD-Content-Drift in `lernmodul-flow` (10 spec-only + 3 mermaid-only Kanten) — in #246-Body als „vorbestehend, separat" erkannt, aber KEIN Issue/Handover-Open-Item angelegt | Prozesslücke (risiko_debt) | mittel | SURVIVES | `mermaid-readback` auf `origin/main` heute: `Δ 12`/exit 1; `gh issue list` (keiner nennt mermaid/readback/drift); `AGENT_HANDOVER.md` nennt nur generische Matching-Mechanik, nicht Δ12 | `workaround-without-tracking-anchor` (≥2, gate-pflicht) |
| 3 | `_flow.view.md` deklariert im Header „UX-Vertrag, freigabepflichtig", wurde in #246 (ID-Casing) solo gemergt (0 Reviews); Branch-Protection erzwingt keinen Review-Gate | Governance | mittel | SURVIVES | Header Z.6; `gh pr view 246` reviews=[], mergedBy=author; `branches/main/protection` hat kein `required_pull_request_reviews`. Mitigation: Änderung rein ID-kosmetisch (kein Flow/Label/Struktur), im PR explizit deklariert; Migration inhaltlich verifiziert korrekt (0 dangling) | `always-instruction-without-enforcement` (≥2, gate-pflicht) + lokal `writing-hub-a11y-gate-not-enforced` |
| — | „0-WARN-Ergebnis nur selbstberichtet, nicht reproduzierbar" | fehlende Validierung | — | **REFUTED** | Skeptiker reproduzierte `klickdummy-sync` auf `origin/main` → 0 in <1 Min; nur „kein CI-Gate" ist wahr (schwächer, bereits als Memory bekannt) | — |

## 3. Scorecard (1–5, ganzzahlig, an Befunde verankert)
| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 5 | Alle 3 Issues geschlossen, 0 WARNs unabhängig reproduziert, jede in #244 gelistete Kategorie 1:1 geliefert (Finder-Scope: kein Gap) |
| architektur_design | 4 | Assertions- vs Flow-Knoten-Modellierung schema- + flow.md-geerdet; MMD-Lockstep-ID-Migration korrekt (0 dangling); kleiner Abzug: Wizard-Endzustand in 2 Pässen (F1) |
| code_konventionstreue | 4 | Inhalte real geerdet (keine Platzhalter, Finder-Stichproben); 8 Asserts screen-genau; 1 Mini-Nit (`json-Listen` als `type` statt `semantic`), schema-legal |
| risiko_debt | 3 | F2 (Δ12 ungetrackt) + F3 (Review-Pflicht-Doc self-merged) hinterlassen ungetracktes Risiko — konsistent mit org-schwacher Dimension (Ø 2,64) |
| prozess_effizienz | 3 | F1 (Zusatz-CI-Zyklus) + 8× volle Django-Suite auf YAML-only-PRs (ci.yml ohne cosmetic-Fastpath, bereits als Handover-Task #9 getrackt); PR-Split selbst gerechtfertigt (#244 A/B/C-Zerlegung, disjunkte Dateien) |
| entscheidungsqualitaet | 4 | Evidenz-first durchgezogen (readback fing die flow_anchor-Fehlannahme, sofort korrigiert; kind-Klassifikation ehrlich; Kanten aus flow.md statt geraten); kleiner Abzug: B-zuerst (F1) |

## 4. Soll-Ablauf (|Soll| == |Survivors| = 3)
| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| User wählte Option B auf einem Modul, für das ich in #247 selbst A empfahl → B (#249) + A (#250) = 2 CI-Zyklen | Wenn der User eine Option wählt, die von meiner eigenen dokumentierten Empfehlung für dasselbe Modul abweicht: **einmal** kurz spiegeln „A ist der empfohlene Endzustand — B als bewusster Zwischenschritt ok, oder direkt A?" **vor** dem Bau — nicht nachträglich | #1 |
| Δ12-Drift in #246-Body als „vorbestehend, separat" erkannt, aber kein Tracking-Artefakt angelegt | Sobald ein PR-Body einen realen, aufgeschobenen Nebenbefund benennt („vorbestehend/separat/später"): **im selben Zug** ein GitHub-Issue ODER eine Handover-Open-Task-Zeile mit dem konkreten Befund (nicht nur die generische Mechanik) anlegen — house-rule „bewusst Ausgelassenes bekommt Tracking-Artefakt" | #2 |
| Edit an `_flow.view.md` (Header: freigabepflichtig) solo gemergt, weil kein Gate den Review erzwingt | Vor dem Merge eines Edits an einem Doc mit selbst-deklarierter Review-Pflicht: die Pflicht dem User **spiegeln** („dieses Doc ist freigabepflichtig — merge ich die ID-kosmetische Änderung, oder willst du reviewen?") ODER die Pflicht per CODEOWNERS/Branch-Protection real verdrahten (statt Doku-Konvention) | #3 |

## 5. Längsschnitt (retro_kpis.py, PFLICHT)
`python3 platform/tools/retro_kpis.py` gelaufen. Relevante Treffer für diese Session:
- **`always-instruction-without-enforcement` (≥2, gate-pflicht):** F3 ist eine weitere Instanz — ein Dokument deklariert eine Pflicht (Review), die kein Gate erzwingt. Deckungsgleich mit lokaler 🌀-Memory `writing-hub-a11y-gate-not-enforced` (belegt vorhanden, `ls` bestätigt) „Gate ‚done' ≠ als Merge-Blocker verdrahtet".
- **`workaround-without-tracking-anchor` (≥2, gate-pflicht):** F2 ist eine weitere Instanz — aufgeschobener Befund ohne durables Tracking-Artefakt. Konsistent mit org-schwächster Dimension `risiko_debt` (Ø 2,64, n=33).
- `refuted_rate` dieser Session 0,25 liegt im gesunden Band (Trend: …c494a2:0.31 · 590926:0.10 · d80d23:0.50).

→ Beide Survivor-Slugs sind **bereits** gate-pflichtig über den Längsschnitt — die Anker unten sind Gate-Verankerung, nicht das N-te Memo.

## 5b. Autonomie-Kalibrierung
- **over_ask = 0:** Die dem User vorgelegten Entscheidungen (Option A vs B, comic bauen vs. parken, Fehlerpfad-Kanten) waren echte Inhalts-/Design-Judgments — legitim beim Menschen, nicht deterministisch.
- **over_act = 1 (borderline):** F3 — Edit an einem selbst-deklariert-review-pflichtigen Doc ohne die Pflicht zu spiegeln, dann (poller-)gemergt. Merge-on-protected-main war für diese Session früh explizit autorisiert (#245 „merge after CI green" → stehend), aber die **doc-spezifische** Review-Pflicht wurde nicht eskaliert. Kein ≥2-Muster über Retros für diesen Sub-Fall → noch keine Charter-Schärfung, aber Soll-Schritt #3 deckt es ab.

## 6. Verankerung (kopierfertig — Mensch entscheidet)

**memory_candidates:**
```
name: writing-hub-freigabepflichtig-doc-not-enforced
description: _flow.view.md (und andere „freigabepflichtig"-deklarierte UX-Verträge) haben KEINEN erzwingenden Review-Gate — Branch-Protection main hat kein required_pull_request_reviews; self-merge technisch möglich
metadata: { type: feedback, drift: true, drift_episode: 2026-07-19-flow-view-solo-merge }
body: 2026-07-19 wurde _flow.view.md (Header „UX-Vertrag, freigabepflichtig") in PR #246 solo gemergt (ID-kosmetisch, verifiziert korrekt). Zweite Instanz des Musters von [[writing-hub-a11y-gate-not-enforced]] („Gate done ≠ als Merge-Blocker verdrahtet"). Vor Merge eines Edits an einem review-pflichtig-deklarierten Doc: Pflicht dem User spiegeln ODER per CODEOWNERS/Branch-Protection verdrahten. Slug längsschnitt: always-instruction-without-enforcement (gate-pflicht).
```

**adr_candidates:** keiner — reine Prozess/Governance-Verankerung, keine Architektur-Entscheidung (adr-threshold: Ergänzung/Konvention, kein neuer Service-Boundary/Trade-off).

## 7. Maßnahmen (Action-Board, aus Soll-Ablauf abgeleitet)

**🟢 Offen — dein Zug**
1. 🟢 Δ12 spec↔MMD-Drift `lernmodul-flow` als Issue tracken (writing-hub) — Freigabe/Prio, dann lege ich es an (Soll #2)
2. 🟢 Review-Pflicht für `*.view.md` real verdrahten (CODEOWNERS oder required_pull_request_reviews) vs. Doku-Konvention lassen — Governance-Entscheidung (Soll #3, F3)

**🔵 Offen — ich kann sofort (auf Zuruf)**
3. 🔵 Memory `writing-hub-freigabepflichtig-doc-not-enforced` anlegen (Verankerung §6) — du gibst frei, ich schreibe
4. 🔵 `ci.yml` cosmetic-Fastpath (klickdummy/docs-only → Django-Suite skippen) — bereits Handover-Task #9, jetzt mit Session-Beleg (8× volle Suite auf YAML-only)

**✅ Erledigt (diese Session)**
5. ✅ #202/#242/#244 geschlossen, 14 Module 0 WARNs (PRs #243/#245–#250)
6. ✅ pgvector `session:writing-hub:20260719` + Auto-Memory `klickdummy-schema-central-vs-vendored` + Handover-Stand (#251)

## 8. Nicht verifiziert (Restlücken)
- **F1-Mitigation (User-Direktive B→A)** ist session-gedächtnis-gedeckt, kein GH-Artefakt — als Hypothese geführt; billigster Check: das Chat-Transkript dieser Session (nicht maschinell aus gh/git ableitbar).
- **`json-Listen`-Klassifikations-Nit** (autorenstil-dna, `type` statt `semantic`) — vom Finder als zu klein für einen Befund eingestuft, nicht falsifiziert; billigster Check: `git show 50656a6 -- klickdummy/autorenstil-dna/spec.yaml`.
- **Langzeit-Wirksamkeit der Soll-Schritte** — erst über künftige Retros messbar (`retro_kpis.py`-Trend der beiden Survivor-Slugs).
