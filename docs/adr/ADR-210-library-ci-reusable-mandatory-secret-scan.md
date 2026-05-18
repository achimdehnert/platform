---
status: "accepted"
date: 2026-05-18
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-057-platform-test-strategy.md", "ADR-058-platform-test-taxonomy.md"]
implementation_status: partial
---

# Library CI reusable (`_ci-pypi.yml`) with a mandatory blocking secret-scan for all PyPI-published packages

> **Trigger**: PR #198 hardened the app CI secret-scan (gitleaks). Investigating
> whether PyPI packages benefit revealed they do **not** consume the platform
> reusable CI at all and have **zero** secret scanning — while publishing to the
> public index.

---

## Context and Problem Statement

ADR-057/058 bind a test strategy and taxonomy to **app** repos via the reusable
`_ci-python.yml` (Django/Postgres-shaped: `django_settings_module`, Postgres
service, ADR-058 coverage gate). PR #198 additionally hardened that workflow's
secret-scan into a blocking, GitHub-API-free, pinned gitleaks-CLI gate with a
documented escape-hatch.

The platform's **PyPI library packages** (`iil-aifw`, `iil-promptfw`,
`iil-testkit`, `iil-authoringfw`, … ~14 repos) each ship a **hand-written
inline `ci.yml`**. None consume any platform reusable. Empirically (2026-05-18):
`iil-aifw`, `iil-promptfw`, `iil-testkit` have **0** gitleaks/trufflehog/
detect-secrets references — yet all three publish to the public PyPI index via
`publish.yml` + `PYPI_API_TOKEN`.

**Problem**: an inverted risk posture. The artifacts with the **widest blast
radius** (public, pip-installable, irreversible once published) have the
**least** assurance, while internal hub apps have the #198-hardened gate. CI is
also reinvented inconsistently per package (no shared lint/coverage contract).

`_ci-python.yml` cannot simply be reused: it is app-shaped (Django settings,
Postgres service) and defaults to self-hosted runners; libraries need none of
that and run on `ubuntu-latest` across a Python matrix.

## Decision Drivers

* Secret leakage in a published wheel/sdist is irreversible (rotate + yank).
  Note: a *history* scan does not cover this vector — a secret can enter the
  artifact via `MANIFEST.in`/`package_data` without a clean history finding.
  The control must scan the *built sdist*, not only git history.
* A reusable workflow protects only repos that call it. A mandatory gate with
  rolling, unmetered onboarding leaves the inverted-risk window open; adoption
  must be measured, not assumed.
* Cross-cutting: ~14 package repos, one shared convention beats 14 bespoke ones.
* Reuse, don't fork: the #198-hardened secret-scan must not be re-derived.
* Library CI ≠ app CI — needs its own narrow contract, not Django ballast.

## Considered Options

1. **Do nothing** — packages keep bespoke CI, no secret scan. Rejected: known
   inverted risk on the highest-blast-radius artifacts.
2. **Force packages onto `_ci-python.yml`** — Rejected: app-shaped (Django/
   Postgres/self-hosted), wrong contract, would need invasive opt-out inputs.
3. **New `_ci-pypi.yml` reusable** (chosen) — library-shaped CI carrying the
   #198-hardened secret-scan as a mandatory blocking job; packages onboard by
   replacing their inline `ci.yml` with a thin caller.

## Decision Outcome

Chosen: **Option 3**. Introduce `.github/workflows/_ci-pypi.yml` as the binding
CI reusable for every PyPI-published platform package.

* **`secrets-scan`** — the #198-hardened logic, now a **single shared
  composite action** `.github/actions/gitleaks-scan` consumed identically by
  `_ci-python.yml`, this job and the `build` job (no divergence possible):
  pinned gitleaks CLI (single version pin), full local **history**, **zero
  GitHub API**, **blocking** (`--exit-code 1`), escape-hatch transparency
  (`.gitleaks.toml`/`.gitleaksignore` echoed) and copy-paste fingerprint
  surfacing on failure. Mandatory — not `continue-on-error`.
* **`build`** — `python -m build` + `twine check --strict` + a gitleaks scan
  of the **unpacked sdist** (`--no-git`). This closes the threat-model gap:
  the history scan above does not see secrets that reach PyPI only via the
  packaged artifact, and a "library CI" that never builds the library cannot
  catch broken packaging metadata before it is published. Blocking;
  `enable_build` (default true).
* **`lint`** — `ruff check` + `ruff format --check`, ruff pinned (parity with
  `_ci-python.yml`, default `==0.15.4`).
* **`test`** — `pip install -e .[<extra>]` + `pytest` with an ADR-058
  coverage gate, run as a **Python-version matrix** (`python_versions` input,
  `fail-fast: false`; default `["3.12"]`, packages widen to their supported
  range). Libraries must support a Python range — apps pin one. **No** Django
  settings, **no** Postgres service. The extra is resolved by a shared
  `resolve-install-extra` composite action that **fails loud** when the
  caller's `install_extra` names an extra the package does not declare
  (pip only *warns* and silently installs the base → confusing downstream
  failures across ~14 heterogeneous packages); a package with no extras at
  all is accepted as a base install.
* **`security`** — `pip check` (dependency conflicts) **always blocking** and
  `pip-audit` (CVE) **blocking by default** (`block_pip_audit`, default true).
  This deliberately does *not* inherit `_ci-python.yml`'s non-blocking stance:
  the ADR's own premise is that published artifacts have the widest,
  irreversible blast radius, so a known-CVE dep in a public wheel must not be
  weaker-gated than in an internal app. Opt-out per caller with justification.
* `runs_on` defaults to **`ubuntu-latest`** (libraries register no self-hosted
  runner); overridable.
* Callers need only `permissions: { contents: read }` — the secret-scan is
  API-free, so the #191/#198 reusable-permission-narrowing trap cannot recur
  here by construction. **Guard**: this holds only while no job calls the
  GitHub API; any future API-using job re-opens the #198 trap and must be
  reviewed against #191/#198 before merge.
* **Adoption gate** — `.github/workflows/pypi-ci-adoption-gate.yml` (weekly)
  enumerates every registry `type: library` repo, checks whether its
  default-branch workflows reference `_ci-pypi.yml`, and maintains one
  tracking issue whose body is the shrinking backlog. Informational (never
  fails CI) so it cannot become noise that gets disabled.

### Consequences

* Good: every published package gets a uniform, hardened secret gate; one
  source of truth for library CI; #198 hardening reused, not copied into 14
  repos.
* Good: API-free secret-scan ⇒ no caller-permission coupling (the #198 root
  cause is structurally absent for packages).
* Bad / accepted: onboarding turns secret-scan **blocking** — a package with
  pre-existing history leaks goes red until triaged (rotate if real;
  `.gitleaksignore` fingerprint if false positive). Same accepted trade-off as
  #198, with the same documented escape-hatch.
* Good: **DRY resolved in-PR** — the gitleaks logic lives once in the
  `.github/actions/gitleaks-scan` composite action (consumed by
  `_ci-python.yml` history scan, `_ci-pypi.yml` history scan, and the
  `build` built-sdist scan). Chosen over a `_secrets-scan.yml` reusable
  workflow: steps-only (no services/matrix), repo already uses composite
  actions (`install-iil-packages@main`), no nested-reusable-workflow limits,
  no extra runner. Incidental hardening: per-invocation `mktemp -d`
  supersedes the old `run_id` tmp scheme — strictly safer on shared
  self-hosted runners; observable behaviour identical.
* Bad / accepted: until a package adopts the caller, it is unprotected. This
  is now **visible and metered** via the adoption gate + tracking issue rather
  than an unowned "rolling onboarding". Distinct from #198: #198 hardened a
  workflow apps *already consumed* (live on merge for all); #210 is live for
  *no* package on merge — the precedent covers the hardening technique, not
  the rollout being automatic.

### Implementation status

* `partial`: `_ci-pypi.yml` (+ `build`, matrix, blocking security) and the
  adoption gate are in place. The reusable was **live-verified end-to-end on
  throwaway branches in `iil-testkit` and `iil-promptfw`** (real CI runs;
  secret-scan + security green; branches then deleted). **No package is
  onboarded yet** — onboarding PRs are deliberately out of scope (CI is red on
  pre-existing package debt the shared contract surfaced, not reusable
  defects). Rollout is owner-paced and tracked by the adoption gate issue.

## More Information

* PR #198 — secret-scan hardening this ADR reuses (mechanism revert + CLI
  migration + escape-hatch + fingerprint surfacing).
* ADR-057 (test strategy), ADR-058 (test taxonomy) — coverage-gate lineage.
* `.github/workflows/pypi-ci-adoption-gate.yml` — the adoption meter; its
  tracking issue (label `adr-210-adoption`) is the live rollout backlog.
* `.github/actions/gitleaks-scan` + `.github/actions/resolve-install-extra` —
  the shared composite actions introduced here (DRY single source).
