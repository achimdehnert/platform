---
concept_id: KONZ-platform-009
title: Registry-SSoT vereinheitlichen — github_repos.yaml + ports.yaml in canonical-Union
pipeline_status: idea
tier: T2
owner: achimdehnert
spec_refs: []
adr_threshold: kein ADR
review_by: 2026-07-30
kill_criteria: "canonical.yaml enthält nach der Änderung WENIGER Repos als vorher ODER registry_api.repo() wirft Exceptions für vorher funktionierende Repos"
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: registry/canonical.yaml, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C2, source_path: registry/github_repos.yaml, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C3, source_path: infra/ports.yaml, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C4, source_path: tools/registry-canonical.py, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C5, source_path: tools/registry-consistency-check.py, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C6, source_path: docs/adr/ADR-234-clean-state-invariant.md, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C7, source_path: tools/registry_api.py, commit_or_pr: main, opened_in_session: true}
created: 2026-06-30
---

# KONZ-platform-009 — Registry-SSoT vereinheitlichen

**Kernthese:** `registry/github_repos.yaml` (113 Repos, vollständigstes Inventar) als dritten
Input in die ADR-234-canonical-Union falten; `registry_api.repo()` gibt dann für alle ~74 heute
blinden Repos valide Daten zurück; Port-Cross-Check in registry-consistency-check.py als SUGGEST
verankern.

---

## Annahmen-/Entscheidungs-Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|----|---------|-----|------------------------|--------|
| L1 | `canonical.yaml` hat 45 Repos; `github_repos.yaml` hat 113 (inkl. 68 archived), 74 nur in gh_repos | Beobachtung | C1+C2, Live-Zählung in Session | verifiziert |
| L2 | `registry_api.repo()` gibt None für alle 74 nur-in-gh_repos-Repos | Beobachtung | C7: load_canonical() liest ausschließlich canonical.yaml | verifiziert |
| L3 | 8 non-archived Repos fehlen in canonical: django-lms-lite, doc-hub, iil-django-commons, llm-mcp, meiki-hub, riskfw, ttz-hub, uptime-kuma | Beobachtung | C1+C2, Live-Diff in Session | verifiziert |
| L4 | canonical._note ist stale: "NICHT kanonisch geschaltet" obwohl der Flip per ADR-234 erfolgt ist | Beobachtung | C1 opened, _note text gelesen | verifiziert |
| L5 | Port-Fakt existiert in 3 Quellen: infra/ports.yaml (authoritative, per-Env), canonical.flat.port, github_repos.yaml.port_prod | Beobachtung | C1+C2+C3 opened | verifiziert |
| L6 | `tools/registry-canonical.py build` nimmt aktuell NUR repo-registry.yaml + repos.yaml als Input | Beobachtung | C4 opened: FLAT + RICH constants, kein gh_repos | verifiziert |
| L7 | github_repos.yaml hat anderes Schema als flat (port_prod statt port, github: statt name, deployed: statt deployed_url) | Beobachtung | C2 opened, schema verglichen | verifiziert |
| L8 | Archived Repos (68 in gh_repos) sollen NICHT in canonical erscheinen (würde Union von 45 auf ~119 aufblasen) | Entscheidung | D: Filter `status != archive`; Alternative: archiv-Sektion in canonical | offen — Feedback erbeten |
| L9 | Kein ADR nötig: github_repos.yaml als 3rd Input folgt dem bestehenden Union-Canonical-Muster (ADR-234 P0) — reine Ergänzung | Entscheidung | C6: ADR-234 beschreibt die Union-Strategie, nennt nur 2 Quellen; aber Erweiterung ist kein Reversal | verifiziert (adr-threshold policy) |
| L10 | Port-Cross-Check startet als SUGGEST (repo-health-rule-discipline) | Entscheidung | D per Policy; SUGGEST→Gate nach 0-FP-Validierung gegen Fleet | verifiziert |

---

## MVC (Minimum Viable Change — 4 sequentielle PRs)

**PR-1 (Trivial — sofort, 5 min):** `_note` in `tools/registry-canonical.py` build-Output auf
`"canonical ist autoritativ, Views sind generierte Read-APIs"` korrigieren. Rebuild canonical.yaml
und committen. Kein Code-Risiko.

**PR-2 (Quickest User-Visible Fix — ohne Schema-Änderung):** `tools/registry_api.py`:
`load_canonical()` lädt `registry/github_repos.yaml` als sekundäre Quelle. Für Repos die NUR
in gh_repos stehen, synthetisiert es eine minimal-kanonische Eintrag-Form (`flat.port`,
`flat.type`, `flat.status`, `in_gh_repos: true`). `registry_api.repo(name)` gibt dann für alle
74 blinden Repos valide Daten zurück. Kein Umbau von canonical.yaml selbst. Reversibel durch
einen Revert in registry_api.py.

**PR-3 (Strukturelle Lösung):** `registry-canonical.py build` mit optionalem `--with-gh-repos`-
Flag, das github_repos.yaml als 3. Quelle einschließt. Schema-Mapping: `port_prod → flat.port`,
`github:owner/repo → owner-Feld`, `deployed → flat.deployed`, `status → flat.status`. Nur
non-archived Repos (L8). `in_gh_repos: bool` Flag in canonical. `registry-canonical.py verify`
erweitern. Dann canonical.yaml rebuilden + committen (ersetzt PR-2 auf Dauer).

**PR-4 (Port-Cross-Check):** `registry-consistency-check.py`: neuen Check-Block der
`canonical.flat.port == ports.yaml.<repo>.services.<repo>.prod` vergleicht (SUGGEST, exit 0).
Trigger: paths: `registry/**`, `infra/ports.yaml`. Nach 0-FP-Validierung gegen alle Repos
→ Gate-Promotion via separatem PR.

---

## Kill-Gate + Threshold

- **Hartes Kill-Gate PR-3:** `python3 tools/registry-canonical.py verify` (mit gh_repos) muss
  exakt dieselben Repos wie vorher für flat/rich View produzieren (0 Regressions). CI-Block wenn Diff.
- **Weiches Kill-Gate PR-2:** `registry_api.repo(r) is not None` für alle 8 non-archived missing
  Repos — pytest-Test vor Merge.
- **Exception-Budget:** PR-3 darf max. 2026-07-15 brauchen. Danach verfällt PR-2 als Dauerlösung
  (bleibt aber als Fallback).

---

## Befunde + Adversariat (T2)

| id | Befund | Typ | Diabolus-Antwort |
|----|--------|-----|-----------------|
| B1 | github_repos.yaml hat 68 archived Repos — wenn drin, bläht canonical stark auf | Risiko | Filter (L8) hält canonical schlank; archived-only Zugriff via direktem YAML-Load wenn je gebraucht |
| B2 | PR-2 (Fallback in registry_api.py) erzeugt temporäre 2-Quellen-Lage in Code | Risiko | TTL: PR-2 wird durch PR-3 ersetzt; Flag `TODO(pr3): remove fallback` in Code |
| B3 | Schema-Mismatch (port_prod ≠ port) — Mapping könnte falsche Ports einbringen | Risiko | Smoke-Test: nach PR-3 rebuild, `registry_api.port("billing-hub") == 8092` vs ports.yaml verifizieren |
| B4 | Advocatus: canonical.yaml wächst von 45 → ~53 Repos — „eine Zahl" für Fleet-Size stimmt nicht mehr | Risiko | Akzeptabel: canonical war nie vollständig (die 45 waren der kleinste gemeinsame Nenner) |
| B5 | Advocatus: _note fix (PR-1) ohne rebuild canonical.yaml ist nur kosmetisch | Beobachtung | Rebuild als Teil von PR-1 mitgeliefert (canonical ist generiert, rebuild ist deterministisch) |

## Alternativen

| id | Variante | Aufwand | Abgrenzung |
|----|----------|---------|------------|
| A1 (empfohlen) | PR-2 → PR-3 sequentiell wie oben | M | Quickfix + strukturelle Lösung |
| A2 | Nur PR-2 (Fallback permanent) | S | Schneller, aber 2-Quellen bleibt als tech-debt |
| A3 | Neues unified schema von Grund auf (alle drei files ersetzen) | XL | Zu invasiv für aktuellen Stand; revisit nach PR-3 Erfahrung |

---

*Lifecycle: review_by 2026-07-30. Wenn PR-3 bis dahin nicht gemergt: dieses Konzept auf
`pipeline_status: sunset` setzen und A2 als Dauerlösung akzeptieren.*
