---
status: "proposed"
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

* **`secrets-scan`** — the #198-hardened job verbatim: pinned gitleaks CLI
  (single `GITLEAKS_VERSION` pin point), full local history, **zero GitHub
  API**, **blocking** (`--exit-code 1`), escape-hatch transparency
  (`.gitleaks.toml`/`.gitleaksignore` echoed) and copy-paste fingerprint
  surfacing on failure. Mandatory — not `continue-on-error`.
* **`lint`** — `ruff check` + `ruff format --check`, ruff pinned (parity with
  `_ci-python.yml`, default `==0.15.4`).
* **`test`** — `pip install -e ".[<extra>]"` + `pytest` with an ADR-058
  coverage gate; **no** Django settings, **no** Postgres service.
* **`security`** — `pip-audit` + `pip check`, non-blocking (parity).
* `runs_on` defaults to **`ubuntu-latest`** (libraries register no self-hosted
  runner); overridable.
* Callers need only `permissions: { contents: read }` — the secret-scan is
  API-free, so the #191/#198 reusable-permission-narrowing trap cannot recur
  here by construction.

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
* Bad / accepted: initial DRY debt — the gitleaks job is duplicated between
  `_ci-python.yml` and `_ci-pypi.yml`. Tracked as a follow-up: extract a shared
  `_secrets-scan.yml` once both are stable in production.

### Implementation status

* `partial`: `_ci-pypi.yml` added; `iil-testkit` + `iil-promptfw` onboarded and
  verified as the proof-of-pattern. Remaining ~12 package repos: rolling
  onboarding, tracked separately (not a blocker for this ADR).

## More Information

* PR #198 — secret-scan hardening this ADR reuses (mechanism revert + CLI
  migration + escape-hatch + fingerprint surfacing).
* ADR-057 (test strategy), ADR-058 (test taxonomy) — coverage-gate lineage.
* Follow-up: shared `_secrets-scan.yml` extraction (DRY) once stable.
