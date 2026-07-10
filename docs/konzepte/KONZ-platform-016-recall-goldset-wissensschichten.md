---
concept_id: KONZ-platform-016
title: Recall-Goldset für Wissensschichten (Wargame-Adaption)
pipeline_status: pilot
tier: T2
owner: Achim Dehnert
spec_refs: []
spec_refs_begruendung: "Mess-Infrastruktur, keine App-/UI-Funktion — kein ADR-211-Spec-Bezug."
adr_threshold: kein ADR
adr_threshold_begruendung: "Addition nach Muster (Eval-Skript + YAML, analog scripts/ + baselines/). Amendment-Check nur, falls ein Recall-Check je harter CI-Step wird — das wäre eine separate, bewusste Entscheidung (Muster: Wargame-Ledger K-11)."
review_by: 2026-10-10
kill_criteria: "Zwei aufeinanderfolgende Quartalsläufe (erstmals Q4/2026) mit 0 neuen Befunden über alle aktiven Recall-Goldsets UND kein Schicht-Ausbau beschlossen → sunset (Goldsets archivieren, Messung einstellen). Zusatz-Kill: ein manueller Lauf > 30 Min → automatisieren oder sunsetten."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "~/.claude/hooks/inject_policies.py", commit_or_pr: "0e29645 (~/.claude)", opened_in_session: true}
  - {claim_id: C2, source_path: "~/.claude/hooks/policy_goldset/results.md", commit_or_pr: "0e29645 (~/.claude)", opened_in_session: true}
  - {claim_id: C3, source_path: "scripts/run_goldset_baseline.py", commit_or_pr: "f9d6082 (main)", opened_in_session: true}
  - {claim_id: C4, source_path: "docs/adr/ADR-209-policy-auto-sync-on-merge.md", commit_or_pr: "f9d6082 (main)", opened_in_session: true}
  - {claim_id: C5, source_path: "~/shared/Second Brain/wargame/success.md §8 (Grep-Rettungsquote, Kipppunkt-Formel)", commit_or_pr: "extern, kein Git", opened_in_session: true}
created: 2026-07-10
---

# KONZ-platform-016: Recall-Goldset für Wissensschichten

## Kernthese

Unsere Wissensschichten (Policy-Hook, Orchestrator-pgvector, Outline, CC-Memory) haben
keinerlei Recall-Messung — ein kleines Goldset je Schicht nach Second-Brain-Wargame-Muster
findet reale Defekte billig, bewiesen am Tag-1-Pilot: der Policy-Hook verlor 4 von 13
Soll-Treffern durch umgebrochene Trigger-Zeilen (Recall 69 %), Fix → 100 % (C1, C2).

## Assumption-/Decision-Ledger

| id | Aussage | Typ | Evidenz/Falsifikation | Status |
|---|---|---|---|---|
| L1 | „Recall-Goldset" ≠ „Goldset-Baseline" (ADR-177): Letzteres benchmarkt Kosten/Routing der FeatureBot-Pipeline, nicht Wissens-Recall. Namenskollision benannt, Namespace getrennt | Entscheidung | C3 | gesetzt |
| L2 | Schichten-Reihenfolge: (1) Policy-Hook ✓ deterministisch, (2) pgvector `policy:<topic>` (Headless-Pfad, ADR-209), (3) Outline `search_knowledge`, (4) CC-Memory-Recall. Ausbau je Schicht erst nach Befund-Nutzen der vorherigen | Entscheidung | C4; evidence-discipline („erst messen") | gesetzt |
| L3 | pgvector- und Outline-Suche haben ungemessene Recall-Lücken | Annahme | Falsifikation: je 15-Fragen-Goldset, Baseline-Lauf; Schicht 2 vor review_by | offen |
| L4 | Goldset-Fragen im Trigger-/Titel-Wortlaut testen die Regex, nicht die Abdeckung (Overfitting) | Risiko | Gegenregel im Set-Kopf: Alltagssprache, Paraphrasen-Pflicht, Quartals-Frischfragen (Wargame WG-12, C5) | mitigiert |
| L5 | Messung ohne Konsequenz stirbt („Ampeln ohne Konsequenz sind Deko", C5) | Risiko | Regel: jeder Miss ⇒ Fix-Commit oder Ledger-Zeile im selben Lauf; Anker = review_by-Wiedervorlage | mitigiert |
| L6 | Hook-Goldset läuft deterministisch ohne LLM-Kosten (< 5 s, subprocess) | Annahme | C2 — Lauf 2×2026-07-10 real ausgeführt | bestätigt ✓ |
| L7 | SSoT der Hook-Goldset-Artefakte ist `~/.claude/hooks/policy_goldset/` (git, neben dem Gemessenen); platform hält KEIN Duplikat, nur diesen KONZ als Verweis | Entscheidung | SSoT-Prüfung: zweite Wahrheit vermieden | gesetzt |
| L8 | Substring-Matching erzeugt False Positives („Session-Retro" → session-routing); Fix (word-boundary) ändert Trefferverhalten aller Policies | Risiko | FP-Zähler ist Runner-Metrik; Semantik-Änderung = Owner-Entscheid, bewusst NICHT im MVC | offen — Owner |

## MVC (konkret)

1. **Geliefert (Pilot, 2026-07-10):** `~/.claude/hooks/policy_goldset/{goldset.yaml, run_goldset.py, results.md}` + Hook-Fix Fortsetzungszeilen — Commit `0e29645` in `~/.claude`. Baseline 69 % → 100 % dokumentiert in results.md (C2).
2. **Schicht 2 (vor 2026-10-10):** 15 Fragen gegen `agent_memory_search(query="policy:<topic>")` — misst, ob der ADR-209-Headless-Pfad dieselben Policies liefert wie der interaktive Pfad (Drift-Detektor zwischen den beiden Konsumpfaden). Ablage: `~/.claude/hooks/policy_goldset/pgvector-goldset.yaml`, Runner-Erweiterung ebenda.
3. **Lauf-Kadenz:** quartalsweise manuell (`python3 run_goldset.py`), Ergebnis-Zeile nach `results.md`; KEINE CI-Einbindung im MVC (siehe adr_threshold_begruendung).
4. **Frühwarn-Analogon:** Der Runner zählt FP gesamt je Lauf; steigt FP über 2 Läufe, ist das der Trigger für den L8-Owner-Entscheid (Analogon zur Wargame-Grep-Rettungsquote: Messgröße, die VOR dem sichtbaren Versagen steigt, C5).

## Kill-Gate + Threshold

**Kill:** siehe `kill_criteria` (messbar: 2 × 0-Befund-Quartalslauf → sunset; > 30 Min/Lauf → automatisieren oder sunsetten). **Exception-Budget:** Schicht 3+4 dürfen bis 2026-10-10 unvermessen bleiben; danach Baseline oder begründete Ledger-Zeile.
**Threshold:** Keine neue Boundary — reines Messwerkzeug, kein Gate, kein neues Statusmodell, kein Scoreboard (Ergebnisse leben in einer results.md an der SSoT, L7).

## Befunde (inkl. Advocatus Diabolus)

| id | Befund | Antwort/Konsequenz |
|---|---|---|
| B1 | **Fund:** 5 Policies trugen tote Trigger-Fortsetzungszeilen (u. a. `llm, groq, openai, mandantendaten, doku-pflicht, gate`); Hook las nur Zeile 1 → Recall 69 % | Hook-Fix (Fortsetzungszeilen bis Leerzeile), Wiederholungslauf 13/13 (C1, C2) |
| B2 | **Diabolus:** „Den Bug fand die Inspektion, nicht das Goldset — wozu das Set?" | Die Inspektion fand ihn nur, weil der Goldset-Bau das Lesen der Trigger-Zeilen erzwang; gegen *Wieder*-Einführung (nächste umgebrochene Policy-Zeile) schützt allein der wiederholbare Lauf |
| B3 | **Diabolus:** „100 % Recall ist mit beliebig laxem Matching erkaufbar (FP-Inflation)" | Richtig — deshalb ist FP-gesamt gleichrangige Runner-Metrik (2 FP im 100 %-Lauf ausgewiesen, C2); Recall ohne FP-Zahl gilt als unvollständiger Lauf |
| B4 | **Maintainer-2028:** Policy-Umbenennung/-Umzug bricht `expected` still | Nein — Miss wird im nächsten Lauf sichtbar; genau das ist die Funktion (Wargame-WG-21-Analogon: Pfad-Konsistenz des Messinstruments, C5) |
| B5 | **Lücke:** Gemessen ist nur der interaktive Pfad; der Headless-Pfad (pgvector, ADR-209) und dessen Auto-Sync („in-progress", C4) sind ungemessen — heutiger Session-Start meldete zudem 25 Commits Policy-Rückstand auf dem Sync-Pfad (platform-pinned dirty) | MVC Punkt 2 (Schicht 2) misst exakt diese Drift zwischen den zwei Konsumpfaden |

## Alternativen

| id | Alternative | Entscheid |
|---|---|---|
| A1 | Nichts messen (Status quo) | abgelehnt — der Tag-1-Fund (B1) widerlegt „der Hook funktioniert schon"; Kosten der Messung: < 1 h Bau, < 5 s je Lauf |
| A2 | Sofort-Vollausbau: CI-Step + alle 4 Schichten + LLM-Judge für Antwortqualität | abgelehnt — Overbuild vor Nutzen-Beweis; LLM-Läufe kosten Abo-Budget (Analogon Wargame SE-3); Ausbau nur entlang L2-Reihenfolge nach Befund-Nutzen |
