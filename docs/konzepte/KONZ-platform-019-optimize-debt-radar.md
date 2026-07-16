---
concept_id: KONZ-platform-019
title: optimize-debt-radar — wöchentlicher Fleet-Radar für /repo-optimize-Kandidaten
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: []              # Tooling/CI-Konzept — kein Klickdummy-Spec; ADR-211 nicht einschlägig
adr_threshold: kein ADR    # Addition nach fleet-drift-report-Muster; Token-Wiring separat gegated
review_by: 2026-10-15
kill_criteria: "2 aufeinanderfolgende Quartale, in denen KEIN geflaggter Repo tatsächlich einen /repo-optimize-Tiefenlauf mit ≥1 SURVIVES-Befund auslöst → Radar abschalten (Signal ohne Rückbau = Alarm-Müdigkeit)."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: .windsurf/workflows/platform-audit.md, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C2, source_path: .windsurf/workflows/repo-optimize.md, commit_or_pr: "PR-1172", opened_in_session: true}
  - {claim_id: C3, source_path: tools/, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C4, source_path: memory/project_cloud_routines_agent_program.md, commit_or_pr: memory, opened_in_session: true}
created: 2026-07-15
---

# KONZ-platform-019 — optimize-debt-radar

**Tier: T2** — Auto-Eskalation greift: persistentes Artefakt (Workflow + Tool + rollierendes Issue)
+ Cross-Repo (Fleet-Scan) + Security-Perimeter (Cross-Repo-Read-Token). Kein T3, weil Addition
nach bestehendem `fleet-drift-report`-Muster, read-only, keine SSoT-Verschiebung, kein neuer
Lifecycle. **Bedingt:** bleibt T2, *solange* der Fleet-Read über den bereits existierenden
GitHub-App-Token (achimdehnert) läuft; erfordert das Wiring einen NEUEN breit-gescopten PAT/Secret
→ dieser Teilschritt wird eigenständig auf Security-Config-Gate-Niveau behandelt.

## Kernthese

`/repo-optimize` ist teuer und nur session-lokal lauffähig; ein **billiger, wöchentlich
automatischer Radar** zählt die bereits definierten Debt-Signale über die Fleet und flaggt die
wenigen Repos, die einen Tiefenlauf verdienen — damit ersetzt Zielung das Raten (statt 33
Tiefenläufe „auf Verdacht").

## Ledger (Annahmen / Entscheidungen / Risiken)

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|----|---------|-----|--------------------------|--------|
| L1 | `/repo-optimize` kann nicht in einer Cloud-Routine laufen (braucht lokale Klone + 8 Subagenten + Worktree) | Annahme | C2 (Step 0/1/4 lesen Klone, spawnen Subagenten); C4 (Container ohne SSH/Klone) | verifiziert |
| L2 | Die Debt-Signale sind bereits maschinen-zählbar definiert (UUIDField-PK, os.environ, print(), direkte LLM-Imports, DEFAULT_AUTO_FIELD, health-Endpoints, fehlende Pflichtdateien, Test-Dateizahl) | Annahme | C1 (platform-audit Phase 1.2/2.1) | verifiziert |
| L3 | Kein Tool/Workflow ist heute als Fleet-Optimierungs-Debt-Scanner konzipiert | Annahme | grep: keine `optimize-debt`/`debt-radar`-Datei; `*_drift/*_meter/*_sweep` decken andere Signale ab (C3) | verifiziert (Rest-H: die 6 Signal-Literal-Treffer in Workflows sind inzidentell, nicht einzeln geöffnet) |
| L4 | Radar dupliziert NICHT `fleet-drift-report` (Drift/Registry/Deploy) noch `deploy-health-triage` (rote Deploys) | Entscheidung | C4 (deren Scope); Radar-Scope = Code-Optimierungs-Debt | gesetzt |
| L5 | Der Radar FIXT nichts — er flaggt nur; der Tiefenlauf + jede Änderung bleibt menschen-initiierte Session (kein Coding-Agent) | Entscheidung | C4 (Design-Entscheid 2026-07-11: kein Auto-Fix-Agent) | gesetzt |
| L6 | Owner-Scope: CI-Token erreicht achimdehnert; iilgmbh/meiki-lra werden als „nicht prüfbar (Owner-Scope)" geführt, lokal-lauffähig als Lückenschluss | Risiko | C4 (Owner-Bindung der App) | offen (Wiring) |
| L7 | Signal-Definitionen dürfen nur EINMAL leben — der Tool wird SSoT der Signal-Menge, `/platform-audit` referenziert ihn, statt die Greps ein zweites Mal hart zu kodieren | Entscheidung | C1 (platform-audit kodiert die Greps heute inline → sonst Doppelquelle) | gesetzt |
| R-thresh | Schwelle = **Delta-ggü-Vorwoche**, nicht absolut (User-Entscheidung 2026-07-16, folgt Empfehlung AD-6: alarm-müdigkeits-ärmer) | Entscheidung | — | entschieden |

## MVC (konkreter Plan)

1. **`tools/optimize_debt_radar.py`** — liest lokale Klone (oder shallow-Clones in CI), zählt je
   Repo die L2-Signale, emittiert **maschinenlesbares JSON** `{repo: {signal: count, ...}, total,
   delta_vs_last}`. Signal-Menge ist hier definiert (SSoT, L7). Baseline-Datei im Repo für Delta.
2. **`tools/tests/test_optimize_debt_radar.py`** — greift `tools-tests.yml` (Signal-Zählung an
   Fixture-Repo, Threshold-Logik, „nicht prüfbar"-Pfad für fremde Owner).
3. **`.github/workflows/optimize-debt-radar.yml`** — `schedule` wöchentlich; Fleet shallow-clone
   (achimdehnert) → Tool → **ein** rollierendes Issue Label `optimize-radar` (Kommentar je Lauf,
   Marker `<!-- optimize-radar:<iso-week> -->`, nie Zweit-Issue), Top-N über Schwelle mit
   Signal-Evidenz; fremde Owner als „nicht prüfbar (Owner-Scope)".
4. **`/platform-audit`-Skill** referenziert künftig den Tool-Output statt eigener Inline-Greps (L7).
5. Label `optimize-radar` anlegen.

**Reihenfolge / Gates:** Schritt 1–2 zuerst, lokal gegen die Fleet grün ziehen (reversibel, kein
Gate). Schritt 3 (Workflow + Token) als eigener, gegateter PR — **Token-Wiring per Dry-Run-in-CI
beweisen** (Gate `autonomous-no-human-review`: ein org-weit lesender Automatismus bekommt vor Merge
einen erzwungenen CI-Dry-Run, der die Token-Verdrahtung zeigt; lokaler Lauf zählt NICHT als Beweis).

## Befunde (inkl. Advocatus Diabolus)

| # | Befund | Antwort / Mitigation |
|---|--------|----------------------|
| AD-1 | **Doppelquelle:** Radar zählt, was `/platform-audit` auch zählt → zweite Wahrheit | L7: Tool wird SSoT der Signal-Menge; platform-audit referenziert ihn statt zweiter Inline-Greps |
| AD-2 | **„Sichtbar machen" schwächer als „verhindern":** Radar surfaced nur, fixt nicht | Bewusst (L5, kein Coding-Agent). Die Verhinderungs-Ebene ist das vertagte CI-Gate (Issue #1173) — hier nur gespiegelt, nicht dupliziert |
| AD-3 | **Manuelle Pflicht ohne Enforcement:** flaggt Repos, aber niemand fährt den Tiefenlauf → Issue wächst nur | Kill-Gate misst genau das (2 leere Quartale → aus); rollierendes Issue statt N Issues hält Rauschen klein |
| AD-4 | **Tool wird faktisch Boundary:** Debt-Zahl wird gegamed / zum de-facto Gate | Rein advisory, kein Merge-Block; Schwelle ist Zielhilfe, kein Pflicht-Score |
| AD-5 | **Owner-Scope-Blindstelle:** iilgmbh/meiki-lra ungescannt | L6: lokal-lauffähig als Lückenschluss; im Issue explizit „nicht prüfbar" statt still weglassen |
| AD-6 | **Alarm-Müdigkeit** bei absoluter Schwelle (dauerhaft „rote" Repos) | Delta-ggü-Vorwoche als Default erwägen (R-thresh) — nur Zuwächse melden |

## Alternativen (verworfen)

| Alt | Beschreibung | Warum verworfen |
|-----|--------------|-----------------|
| A | Debt-Zählung in `fleet-drift-report` (Cloud, täglich) falten — 0 neue Artefakte | Kadenz-Mismatch: täglicher Code-Scan von 33 Repos ist Verschwendung für ein langsam driftendes Signal; bläht eine Drift-Routine mit fremdem Kostenprofil |
| B | Eigene Cloud-Routine (Sonnet + GitHub-MCP-Greps) | Owner-Scope-Lücke (kein Fleet-voll), MCP-Grep-Flakiness, belastet Routinen-Budget; git-nativer Scan ist robuster + versioniert/testbar |

## Out-of-the-Box

Der Tool-Output (`{repo: debt-signals}`-JSON) ist über den Radar hinaus wiederverwertbar: als
Trend-Metrik in `adr-nightly-metrics`-Manier, als Eingabe für eine spätere Priorisierung von
`/repo-optimize`-Läufen, oder als Baseline für das vertagte CI-Gate (#1173). Bewusst NICHT jetzt
bauen — nur als Anschlussfläche vermerkt.

## Entscheidung + Kill-Gate

**Entschieden (2026-07-16):** MVC Schritt 1–2 bauen (gate-frei), Schritt 3 als separat gegateten PR
mit Token-Dry-Run. Schwelle: **Delta-ggü-Vorwoche** (AD-6, alarm-müdigkeits-ärmer) — kein offener
Punkt mehr.

**Kill-Gate (messbar):** siehe Frontmatter `kill_criteria` — 2 leere Quartale ohne ausgelösten
Rückbau → Radar `sunset`. **Exception-Budget:** bis `review_by` 2026-10-15; danach ohne belegten
Nutzen (≥1 geflaggter Repo führte zu SURVIVES-Befund) nicht verlängern.

## Bezug

- Verankerungs-Kette: PR #1172 (Komplexitäts-Bilanz + kreativer Zuwachs in `/repo-optimize`),
  PR #1174 (CORE_CONTEXT-Konvention), Issue #1173 (hartes CI-Gate, vertagt).
- Nachbar-Automatik: Cloud-Routinen-Programm (`deploy-health-triage`, `fleet-drift-report`,
  `pr-review-prep`, `deep-review`) — Radar grenzt sich per Scope ab (L4).
