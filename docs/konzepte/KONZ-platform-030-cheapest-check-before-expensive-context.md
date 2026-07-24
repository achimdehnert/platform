---
concept_id: KONZ-platform-030
title: Cheapest-Check-Before-Expensive-Context — wiederkehrendes Gate-Muster verankern
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []
adr_threshold: kein ADR (Gate-Tool nach Präzedenz block_stale_branch_commit/test_claim_check; falls org-weit verpflichtend → Amendment ADR-058/CI-Health prüfen)
review_by: 2026-08-01
kill_criteria: "Wenn der Warn-only-Pilot über 4 Wochen / ≥15 einschlägige PRs eine False-Positive-Rate >20% hat ODER 0 echte Treffer liefert → Gate verwerfen (das Muster bleibt dann Policy/Hook-Konvention, kein CI-Gate)."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: platform/tools/retro_kpis.py, commit_or_pr: "ausgeführt 2026-06-24", opened_in_session: true}
  - {claim_id: C2, source_path: ~/.claude/hooks/evidence_claim_scanner.py, commit_or_pr: "head gelesen", opened_in_session: true}
  - {claim_id: C3, source_path: ~/.claude/hooks/block_stale_branch_commit.sh, commit_or_pr: "head gelesen", opened_in_session: true}
  - {claim_id: C4, source_path: platform/tools/test_claim_check.py, commit_or_pr: "head gelesen", opened_in_session: true}
  - {claim_id: C5, source_path: iilgmbh/risk-hub ci.yml + Runs 28092468642/28093059202/28093722599, commit_or_pr: "risk-hub#276", opened_in_session: true}
  - {claim_id: C6, source_path: ~/.claude/settings.json (hooks-Block), commit_or_pr: "gelesen", opened_in_session: true}
created: 2026-06-24
---

# KONZ-platform-030 — Cheapest-Check-Before-Expensive-Context

**Tier: T3** — auto-eskaliert: das Konzept berührt eine **neue Boundary (ein Gate)**, ist
**cross-repo/org-weit** wirksam und schlägt einen Enforcement-Mechanismus vor. Damit greift die
Auto-Eskalation des `/konzept`-Skills unabhängig von der Selbsteinstufung.

> **Methoden-Ehrlichkeit (Reduktion benannt):** Der T3-Standard verlangt einen 3-Agenten-Adversariat-
> Fan-out. Hier inline ausgeführt (Steelman/Diabolus/Maintainer-2028 als Abschnitte), bewusste
> Reduktion: das Artefakt ist ein **reversibler Vorschlags-Doc**, nicht das Gate selbst; der echte
> adversariale Test ist die **Warn-only-Pilotphase** (SUGGEST) gegen reale PRs. Diese Reduktion ist
> ein bekanntes Risiko (RISK-5), kein verdeckter Shortcut.

## 1. Executive Summary
- `retro_kpis.py` (C1) weist **9 Slugs ≥2 über Retros als gate-pflichtig** aus; das Cluster
  `claim-before-cheapest-check` + `lint-failure-no-local-gate` + `skipped-cheapest-empirical-precheck`
  + `pre-build-gates-skipped` + `verified-before-end-to-end` ist **ein** Wurzelthema: *etwas wird im
  teuersten Kontext (CI/Prod) zum ersten Mal ausgeführt, obwohl der billigste Ziel-Kontext-Check
  lokal in Sekunden möglich war.*
- Realfall 2026-06-24 (C5, risk-hub#276): neuer Live-Parity-CI-Job lief **4× rot**; ein Fehllauf
  (Prod-Secret-Guard) war lokal via `python -c "import config.settings"` in ~1 s fangbar.
- **Kernthese:** Das Muster ist nachweislich wiederkehrend und damit gate-reif — **aber** „cheapest
  check before claim" ist in seiner *allgemeinen* Form **nicht** mechanisch erzwingbar. Erzwingbar
  ist genau **ein schmaler, strukturell erkennbarer Sub-Fall**: ein PR, der einen
  **app-bootenden CI-Job** neu einführt/ändert, ohne einen deklarierten lokalen Vorab-Check.
- **Empfehlung:** Ein **warn-only CI-Gate** in der Familie `test_claim_check.py` bauen (Phase
  SUGGEST→FAIL), das genau diesen Sub-Fall erkennt — **kein** neues ADR, **keine** neue SSoT.

## 2. Scope & Evidenzbasis
In-scope: das wiederkehrende Muster + sein erzwingbarer Kern. Out-of-scope: die allgemeine
Verhaltensdisziplin (bleibt `evidence-discipline.md` + `evidence_claim_scanner.py`).

| ID | Claim | Evidenz | Stufe |
|----|-------|---------|-------|
| C1 | `claim-before-cheapest-check` ≥2 gate-pflichtig (Cluster von 5 verwandten Slugs) | `retro_kpis.py`-Lauf 2026-06-24 | E3 |
| C5 | Realfall: neuer App-CI-Job 4× rot, ≥1 Fehllauf lokal vorab fangbar | risk-hub#276 + 3 Run-IDs | E3 |
| C2 | `evidence_claim_scanner.py` = Stop-Hook, scant **Text-Claims** post-hoc | Hook-Header | E2 |
| C3 | `block_stale_branch_commit.sh` = PreToolUse-Gate, **aus Retro-Muster→Gate**, fail-open | Hook-Header | E2 |
| C4 | `test_claim_check.py` = warn-only CI-Gate, Phase SUGGEST→FAIL, deterministisch (kein LLM) | Tool-Header | E2 |
| C6 | Hooks real verdrahtet in settings.json (PreToolUse/Stop) | settings.json | E2 |

## 3. Infrastruktur-Fit (Root-Cause-Tiefe: existiert das Gate schon? — Nein, aber die Familie schon)
Die Org hat **bereits ein etabliertes Muster** „wiederkehrendes Retro-Finding → deterministisches
Gate, phasenweise, fail-open":
- `evidence_claim_scanner.py` (C2) — fängt **Text**-Über-Claims im Assistant-Turn (post-hoc).
- `block_stale_branch_commit.sh` (C3) — harter PreToolUse-Gate gegen einen anderen Drift (stale branch).
- `test_claim_check.py` (C4) — warn-only CI-Gate: „behauptet getestet, kein Test-Diff".

**Verifizierte Lücke:** Keiner dieser Mechanismen deckt den S6-Fall ab — *ein neu eingeführter
app-bootender CI-Job, dessen billigster lokaler Vorab-Check übersprungen wurde.* `evidence_claim_scanner`
prüft erzeugten Text, nicht das strukturelle Artefakt (neuer Workflow-Job); `test_claim_check` prüft
Test-Claims, nicht App-Boot-Jobs. → Das neue Gate ist **Ergänzung**, keine Dublette.

## 4. Steelman (stärkste Begründung FÜR ein Gate)
Die Memo-Ebene hat bei *jedem* der Präzedenzfälle (C2/C3/C4) **nachweislich nicht gehalten** — die
jeweiligen Hooks/Gates wurden erst gebaut, *nachdem* eine Policy im Kontext stand und trotzdem
verletzt wurde (siehe `evidence_claim_scanner`-Header: „a passive rule does not change behaviour
reliably"). `claim-before-cheapest-check` ist mit ≥2 über Retros exakt an derselben Schwelle. Ein
weiteres Memo wäre per Org-Doktrin („nicht der N-te Notizzettel") der falsche Zug.

## 5. Konzeptdefinition — was erzwingbar ist vs. was Konvention bleibt
**Trennlinie (der Kern der Anforderung):**

| Schicht | Inhalt | Mechanismus | Status |
|--------|--------|-------------|--------|
| **Erzwingbar (mechanisch)** | PR führt einen `.github/workflows/*.yml`-Job neu ein/ändert ihn, der eine App bootet (Regex-Signale: `manage.py (migrate\|runserver\|seed)`, `gunicorn`, `docker compose .* up`, `runserver`) **und** weder PR-Body-Marker `precheck:` noch Label `local-boot-verified` trägt | **warn-only CI-Gate** `tools/cheapest_check_gate.py` (Familie `test_claim_check.py`), Phase SUGGEST→FAIL, deterministisch, fail-open | **neu (Vorschlag)** |
| **Konvention (nicht erzwingbar)** | Die allgemeine „billigster Check vor Claim/Push"-Disziplin über alle Aufgabentypen | `evidence-discipline.md` + `evidence_claim_scanner.py` (Stop-Hook, bestehend) | **bestehend** |

**MVC (konkret, kein Anforderungs-Freitext):**
1. `platform/tools/cheapest_check_gate.py` — Input: geänderte Dateien + Diff der Workflow-YAMLs + PR-Body + Labels. Logik: App-Boot-Signal im neuen/geänderten Job ∧ kein Precheck-Marker → WARN-Kommentar mit dem konkreten Vorschlag („vor dem Push lokal: `DJANGO_SETTINGS_MODULE=<settings> python -c 'import <settings>'` bzw. `make run-local`"). Sonst still.
2. Eingebunden als CI-Step im platform-shared-CI **und** opt-in pro Repo (wie `test_claim_check`).
3. Phase SUGGEST: Verdikt-Exit immer 0 (nur Kommentar), bis FP-frei gegen echte PRs validiert.
4. Marker-Konvention dokumentiert: PR-Body-Zeile `precheck: <cmd>` ODER Label `local-boot-verified` macht das Gate still (= ehrlicher Selbst-Beleg, nachprüfbar im Body).

## 6. Adversariale Analyse
**Advocatus Diabolus:**
- *Zweite Wahrheit?* Der Precheck-Marker ist eine Selbst-Deklaration — gamebar („`precheck: done`" ohne Lauf). → Gegenmaßnahme: Marker verlangt das **konkrete Kommando**, nicht „done"; FP-Toleranz akzeptiert, weil das Gate **WARN** ist, nicht Block — Ziel ist Reibung/Erinnerung an der richtigen Stelle, nicht Beweis. Ein Beweis-Anspruch wäre Overreach (genau der Fehler, den das Gate anprangert).
- *Tool wird zur Boundary?* Ja — bewusst, aber fail-open + warn-only hält die Boundary weich bis FP-Validierung.
- *Manuelle Pflicht ohne Enforcement?* Der Marker ist die einzige manuelle Komponente; das Gate erzwingt nicht den *Lauf*, nur die *Deklaration*. Ehrlich benannt (RISK-2).
- *Verschlimmert es F11/F17/F18/F19?* Nein — orthogonal (kein Spec/Locator/DSL-Bezug).

**Maintainer-2028:** Ein weiteres Tool in der `*_check.py`-Familie erhöht die CI-Tool-Last. → Gegenmaßnahme: gleiche Bauform/CLI-Konvention wie `test_claim_check.py` (ein Reviewer versteht beide in einem Blick); Kill-Gate verhindert Zombie-Gate.

## 7. Deep-Dive — Erkennungsheuristik App-Boot-Job
Signal-Regex auf dem **Diff** der `.github/workflows/*.yml` (nur HINZUGEFÜGTE Zeilen): `manage\.py\s+(migrate|runserver|seed)`, `gunicorn\s`, `docker\s+compose\s.*\bup\b`, `uvicorn\s`. Treffer ∧ kein `precheck:`/Label → WARN. Bewusst eng (lieber FN als FP in der SUGGEST-Phase). Erweiterung später datengetrieben aus den ersten Treffern.

## 8. Alternativen
| # | Alternative | Warum nicht (primär) |
|---|-------------|----------------------|
| A1 | Nur Memory/Policy ergänzen (kein Gate) | Genau das hat ≥2× nicht gehalten — Org-Doktrin „nicht N-tes Memo" |
| A2 | PreToolUse(Bash)-Hook der `git push` blockt, wenn Workflow-Diff ohne Precheck | Lokaler Hook erreicht **nur Dev-Host-Sessions**, nicht Cross-Host (iPad) — dieselbe Lücke wie der Handover-Drift; CI-Gate erreicht alle PRs |
| A3 | Hartes required CI-Gate sofort | Verfrüht ohne FP-Validierung; verletzt selbst das Safe-Rollout-Prinzip |

## 9. Out-of-the-Box
Statt eines neuen Gates den **`retro_kpis.py`-Längsschnitt selbst** zum Gate-Generator machen: ein
Slug ≥2 erzeugt automatisch ein `[gate-candidate]`-Issue mit Template (Symptom/Root/Fix). Verschiebt
den Hebel von „pro Muster ein Tool von Hand" zu „die Längsschnitt-Maschine eskaliert selbst".
**Backlog-Notiz, nicht Teil des MVC** (eigener Threshold-Check).

## 10. Befunde
| # | Befund | Schwere | Evidenz |
|---|--------|---------|---------|
| B1 | Muster ist gate-reif (≥2), aber allgemein nicht erzwingbar — nur der App-Boot-Sub-Fall | hoch | C1, C5 |
| B2 | Gate-Familie + Bauform existiert bereits → niedrige Baukosten, keine neue Architektur | mittel | C2/C3/C4 |
| B3 | Cross-Host-Sessions (iPad) machen lokale Hooks (A2) unzureichend → CI-Gate ist der einzige Allzu-Pfad | mittel | C5-Kontext + Handover-Drift dieser Session |

## 11. Top-5-Risiken
1. **Selbst-Deklarations-Gaming** des Precheck-Markers (mittel) → akzeptiert, weil warn-only; Ziel ist Reibung, nicht Beweis.
2. **False-Positives** auf nicht-app-bootenden Jobs (mittel) → enge Regex + SUGGEST-Phase + Kill-Gate.
3. **CI-Tool-Sprawl** (niedrig) → strikte Bauform-Parität zu `test_claim_check.py`.
4. **Zombie-Gate** ohne Wirkung (niedrig) → Kill-Gate (FP>20% ODER 0 Treffer/4 Wo → verwerfen).
5. **Enforcement-Illusion** (mittel, RISK-5) → Doc benennt klar: Gate erzwingt **Deklaration**, nicht **Lauf**; FP-Toleranz explizit.

## 12. Empfehlungen
1. **REC-1:** `platform/tools/cheapest_check_gate.py` bauen, Bauform/CLI = `test_claim_check.py`, Phase **SUGGEST (warn-only, Exit 0)**.
2. **REC-2:** In platform-shared-CI als opt-in-Step registrieren; zuerst in 1 Pilot-Repo (risk-hub, wo der Realfall war).
3. **REC-3:** Precheck-Marker-Konvention (`precheck: <cmd>` im PR-Body ODER Label `local-boot-verified`) in der Repo-CONTRIBUTING/CLAUDE.md dokumentieren.
4. **REC-4:** **Kein** neues ADR — Präzedenz (C3/C4 ohne ADR gebaut). Falls REC-2 später org-weit *verpflichtend* wird → dann Amendment an ADR-058 (Test-Taxonomie) oder die CI-Health-Governance prüfen.
5. **REC-5 (Backlog):** OOTB — `retro_kpis.py` ≥2 → Auto-`[gate-candidate]`-Issue (eigener Threshold-Check).

## 13. Entscheidung + Kill-Gate + 30/60/90
**Entscheidung (vorgeschlagen, Mensch bestätigt):** REC-1..3 umsetzen (Pilot risk-hub, warn-only).
**Kill-Gate (messbar):** Pilot 4 Wochen / ≥15 einschlägige PRs. FP-Rate >20% ODER 0 echte Treffer →
Gate verwerfen, Muster bleibt Policy/Hook-Konvention. Exception-Budget: 1× Verlängerung um 2 Wochen
bis **2026-08-15**, dann harte Entscheidung promote|delete.
- **30 Tage:** Tool gebaut + im Pilot-Repo warn-only aktiv; erste Treffer-/FP-Zahlen gesammelt.
- **60 Tage:** FP-frei → auf FAIL hochziehen (Pilot-Repo); Marker-Konvention dokumentiert.
- **90 Tage:** Promote-Entscheidung org-weit (opt-in vs. shared-CI-default) auf Datenbasis.
