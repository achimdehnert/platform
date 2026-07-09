---
retro_schema: 1
date: 2026-07-05
repo_scope: [iil-adrfw, platform]
session_id: 16fd96
footprint: full
footprint_reduction_reason: >-
  Rule-B trigger was `deep` (prod step = PyPI 0.7.0 publish). Reduced one step to
  `full` because all three hold: (a) the prod step was explicitly human-approved
  (artifact: user "1 go" + explicit "dispatch publish.yml"; PR #51 body warned it
  was the publish path); (b) additive & non-destructive — new version, no DB
  migration, a bad release is fixed forward, not rolled back; (c) findings
  estimate ≤10. Never `lean` (prod step present).
findings_total: 3
findings_survived: 2
refuted_rate: 0.33
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [claim-before-cheapest-check, handover-stale-vor-merge]
recurring_findings: [claim-before-cheapest-check, handover-stale-vor-merge]
---

# Session-Retro — iil-adrfw 0.7.0 release + quality hardening (2026-07-05)

## 1. Executive Summary

- The original ask (release 0.6.0→0.7.0 + publish, triage bandit #50, merge
  dependabot #47, tighten mypy) was **cleanly and verifiably delivered**: 0.7.0
  is live on PyPI with real PEP-740 attestation, #50's 4 findings fixed (not
  suppressed), mypy tightened, all merges on green CI.
- The follow-on quality work (coverage 80→85 #53, mypy strict subset #53, bandit
  SAST→blocking #54 + platform#938) also landed and is functionally correct.
- **One genuine defect shipped to platform `main`** (#938): a GitHub Actions
  ternary rendered the bandit job name as "…non-blocking" even when blocking —
  cosmetic only (gating keys on `ci / gate`), self-caught, fix in flight (#941).
- **Two survivors, both repeats of already-gate-mandatory patterns**:
  `claim-before-cheapest-check` (merged on "YAML parses", never rendered the
  expression) and `handover-stale-vor-merge` (#55 lists open #941 as "landed").
- A skeptic **refuted** the scariest-sounding process claim: #941 is *not*
  structurally unmergeable — the owner added `@wirdigital` as a 2nd code owner
  (#940) minutes before the code-owner rule activated, so #941 has a normal
  review path. (This corrects a wrong statement the session made to the user.)

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| C1 | GHA ternary shipped to platform main renders bandit job name "non-blocking" while the job is actually blocking; cosmetic only (required check = `ci / gate`, aggregates on job *result* not name) | fehlende Validierung | mittel | **SURVIVES** | platform `_ci-pypi.yml:318` (#938, merged 05:46:55Z); live in iil-adrfw #54 run `28731104132` job `ci / SAST (bandit, non-blocking)`; iil-adrfw main protection `contexts:["ci / gate"]` | `claim-before-cheapest-check` (gate-mandatory ×≥3) |
| C2 | #941 is "structurally unmergeable by normal means" (solo code owner = author, bypass_actors empty) | verfrühte Festlegung | — | **REFUTED** | `#940` (merged 05:59:43Z) added `@wirdigital` to CODEOWNERS; ruleset `17621471` count=1 → one non-author owner approval suffices | — |
| C3 | iil-adrfw #55 handover lists platform#941 under a "landed" verb with no status qualifier, while #941 is OPEN/BLOCKED | Kommunikation | niedrig | **SURVIVES** | #55 body "…(#54 + platform#938; cosmetic name-fix in platform#941)" under "…priorities landed"; `gh pr view 941` → state OPEN | `handover-stale-vor-merge` (gate-mandatory ×≥2) |

Non-findings explicitly cleared by finders (stated for the record, not counted):
coverage 80→85 (verified 87.5% in CI run `28730992215`), mypy strict-subset +
deferred counts (independently reproduced: `disallow_any_generics`=45,
`warn_unreachable`=2), `assert`→`RuntimeError` (correct under `-O`), #51 release
bundling (pragmatic per repo release-gate convention), #47 dependabot,
#941-as-org-wide-PR-for-cosmetics (proportionate; reusable-workflow edits are
org-wide surface regardless of diff size).

## 3. Scorecard (1–5, integer, anchored)

| Dimension | Score | Anchor |
|---|---|---|
| zielerreichung | 4 | All 7 goals delivered + published live; small mängel = C1 defect + C3 dangling thread |
| architektur_design | 4 | `bandit_blocking` mirrors the proven `mypy_blocking` pattern, backward-compatible opt-in; only the label expression was flawed |
| code_konventionstreue | 4 | Conventional commits, ADR-233 worktrees, test-naming intact; C3 doc-accuracy is the sole ding |
| risiko_debt | 3 | Cosmetic defect reached org-wide shared CI; deferrals transparent; #941 dangling — manageable, above fleet mean (2.69) |
| prozess_effizienz | 3 | #938→#941 rework caused by C1; several merge round-trips (guard re-auth); each step green |
| entscheidungsqualitaet | 3 | Sound tech calls (suppress/RuntimeError/strict-subset), but the ternary idiom choice + a *wrong* hand-off claim ("#941 unmergeable") pull this down |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| #938 merged to platform main on "YAML validated (parses)" (PR body); the dynamic-name expression's *rendered* value was never checked → wrong label live | Before merging a change to a shared/org-wide workflow, **render/dry-run any dynamic `${{ }}` expression** (esp. GHA `&&/||` where a branch can be falsy) — run the workflow once or evaluate the expression, not just YAML-parse. "Parses" is not "renders correctly". | #C1 |
| #55 handover wrote "…cosmetic name-fix in platform#941" under "…priorities landed", but #941 was OPEN/BLOCKED at write time | When a status/handover doc references a PR, **query its live state at write time** and label open PRs explicitly (`(open, pending review)`); never fold an unmerged PR into a "landed" clause. | #C3 |

Invariante erfüllt: |Soll-Schritte| = 2 = |Survivors (C1, C3)|.

## 5. Längsschnitt (retro_kpis.py über alle docs/retros)

`python3 tools/retro_kpis.py` — beide Survivors treffen **bereits gate-pflichtige**
Wiederholungs-Slugs (≥2 über Retros), kein neues Memo nötig:

- **`claim-before-cheapest-check`** (gate-mandatory) ← **C1**. Dieselbe Wurzel wie
  der CLAUDE.md-Gate-Realfall: „gebaut + lokal grün ≠ funktioniert" — hier
  „YAML parses ≠ Expression rendert korrekt". Das Werkzeug (Workflow) hätte
  **einmal echt** laufen müssen, bevor #938 als fertig galt.
- **`handover-stale-vor-merge`** (gate-mandatory) ← **C3**. Handover-Doc überholt
  den realen Merge-Stand.

`refuted_rate` dieser Session = 0.33 (1 REFUTED / 3, pre_refuted=0) — im gesunden
Band (Trend: …0.38 · 0.50 · **0.33**), weder Stroh-Finder (>0.8) noch Theater (<0.2).

## 5b. Autonomie-Kalibrierung

- **over_ask = 0**: kein deterministisch/reversibler Schritt fälschlich als „dein
  Zug" vorgelegt. Die Freigabe-Fragen betrafen echte Gates (Publish, org-weiter
  Merge, Ruleset-Änderung).
- **over_act = 0**: kein Gate autonom überschritten. PRs wurden autonom *geöffnet*
  (reversibel, kein Gate); alle *Merges* zu prod/publish/org-wide liefen erst nach
  wörtlicher Freigabe bzw. wurden vom Auto-Classifier abgefangen. Der Scope-Sprung
  ins 2. Repo (platform, org-weites `_ci-pypi.yml`) wurde dem User gespiegelt.
- **Governance-Kalibrierungspunkt (an den User, kein Agent-Fix):** das am
  2026-07-05T06:00:34Z aktivierte Ruleset (`require_code_owner_review`, count=1,
  `bypass_actors: []`) fängt **die eigenen** Solo-PRs des Owners (Autor kann sich
  nicht selbst approven). Wenn die Absicht „Achim merged solo, `@wirdigital` nur
  als Ausfall-Backup" ist, passt die Regel nicht dazu → Owner in `bypass_actors`
  aufnehmen, `@wirdigital` als CODEOWNER für fremd-authorierte PRs behalten.

## 6. Verankerung (kopierfertig — Mensch entscheidet)

**memory_candidates:**
- ✅ *bereits geschrieben diese Session:* `gha-ternary-empty-string-footgun`
  (reference, drift) — GHA `cond && '' || X` liefert immer X. Deckt C1 technisch ab.
- *kein neues Memory für C1/C3 nötig:* beide sind bestehende gate-pflichtige
  Slugs (`claim-before-cheapest-check`, `handover-stale-vor-merge`) — Verankerung
  gehört als **Gate/Hook**, nicht als N-ter Notizzettel.

**adr_candidates:** keine. (Alle Änderungen additiv/pattern-folgend; `adr-threshold`
nicht erreicht — `bandit_blocking` spiegelt `mypy_blocking`.)

**gate_candidates (an bestehende Gate-Pflicht angedockt):**
- `claim-before-cheapest-check`: ergänze die „einmal echt laufen"-Regel um den
  CI-Expression-Fall — ein geänderter Workflow mit dynamischem `${{ }}`-Ausdruck
  gilt erst als validiert, wenn der Ausdruck **gerendert** wurde (1 realer Run
  oder Expression-Eval), nicht nur `yaml.safe_load`.
- `handover-stale-vor-merge`: die Regel deckt Handover/Status-Docs, die einen
  PR-Stand **behaupten**; C3 zeigt die Verschärfung — beim Schreiben eines
  Handover-Verweises auf einen PR dessen Live-State abfragen und offene PRs
  explizit als solche kennzeichnen, nie unter einem „landed/erledigt"-Verb bündeln.

## 7. Maßnahmen (Action Board)

🟢 **Offen — dein Zug**
| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| A1 | #941 (Label-Fix) approven + mergen — **normaler Weg**, kein Ruleset-Hack | platform | #941 | 🟢 offen | `@wirdigital` approven lassen → `gh pr merge 941 --squash` (du/wirdigital) |
| A2 | Governance-Kalibrierung: willst du eigene Solo-PRs mergen können? Dann `achimdehnert` in `bypass_actors` des Rulesets, `@wirdigital` als CODEOWNER behalten | platform | ruleset 17621471 | 🟢 offen | Entscheiden + Ruleset-Edit (du) |

🔵 **Offen — ich kann sofort (auf dein Wort)**
| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| B1 | C3 heilen: #52/#55-Nachtrag „#941 open/pending" in AGENT_HANDOVER, sobald #941 gemergt ist ohnehin obsolet | iil-adrfw | — | 🔵 ready | Nach A1: Handover-Zeile auf „bandit blocking, label green" ziehen (ich) |

✅ **Erledigt**
| # | Item | Repo | PR/Issue | Status |
|---|---|---|---|---|
| C | 0.7.0 released + published (verified live) | iil-adrfw | #51 | ✅ done |
| D | bandit #50 → green, mypy tightened, coverage 85, bandit blocking | iil-adrfw | #51/#53/#54 | ✅ done |
| E | GHA-Footgun als Memory verankert | — | `gha-ternary-empty-string-footgun` | ✅ done |

## 8. Nicht verifiziert (Restlücken)

- **`contextlib.suppress(Exception)` maskiert weiterhin alle Exceptions** in den 3
  best-effort-Loops (cli.py validate/graph/export). Finder-2 stufte es als „kein
  Regressions-Neuschaden, aber Failure-Modus unverbessert" ein — **nicht als
  Befund verifiziert** (pre-existing). Billigster Check: gezielt einen kaputten
  ADR einspeisen und prüfen, ob `graph`/`export` ihn still überspringt.
- **Actor-Intent des Ruleset-Changes:** dass `id 33293099` = `achimdehnert`
  (interaktiv, KONZ-012 Phase A) und nicht die Retro-Session ist, ist per API-Id
  belegt; „bewusst vs. versehentlich" ist Interpretation, nicht artefakt-hart.
- **`platform` #939/#942–#945** (open/blocked, heute aktualisiert) sind **fremde
  Workstreams** (KONZ-012, kd-skills, ADRs), nicht Teil dieser Session — nicht
  reviewed. Billigster Check: `gh pr view <n> --json author,headRefName`.
