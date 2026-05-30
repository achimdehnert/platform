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
implementation_evidence:
  - ".github/actions/gitleaks-scan/action.yml — shared #198-hardened scan (history/dir/sdist modes)"
  - ".github/actions/resolve-install-extra/action.yml — wrong-extra fail-loud guard"
  - ".github/workflows/_ci-pypi.yml — library CI reusable (lint/secret/build/test-matrix/security)"
  - ".github/workflows/_ci-python.yml — secrets-scan rewired to the shared action"
  - "Pre-publish binding gate wired into publish-iil-testkit/-codeguard/-ingest, publish-platform-context, publish-packages (3 prod jobs + testpypi)"
  - ".github/workflows/pypi-ci-adoption-gate.yml — weekly adoption meter + tracking issue"
  - "Live-verified (PR #199): gitleaks-scan success on iil-testkit + iil-promptfw throwaway branches (deleted)"
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

## Pros and Cons of the Options

### Option 1 — Do nothing (bespoke CI, no secret scan)
* Good: zero work; no onboarding friction.
* Bad: the known inverted-risk posture persists on the highest-blast-radius
  artifacts; a secret reaching public PyPI is irreversible (rotate + yank).
* Bad: CI reinvented per package — no shared lint/coverage/secret contract.

### Option 2 — Force packages onto `_ci-python.yml`
* Good: one reusable, no new file.
* Bad: app-shaped (Django settings, Postgres service, self-hosted default) —
  wrong contract for libraries; needs invasive opt-out inputs that erode the
  app contract for every existing consumer.
* Bad: still does not gate the *publish* path (same blind spot as today).

### Option 3 — New `_ci-pypi.yml` + a binding pre-publish gate (chosen)
* Good: library-shaped contract; #198 hardening reused via one shared
  composite action (no divergence); the irreversible event is gated **by
  construction** for all packages, with PR-time scanning as defense-in-depth.
* Good: API-free secret-scan ⇒ no caller-permission coupling (#191/#198
  trap structurally absent).
* Bad / accepted: a package with pre-existing history/artifact leaks goes red
  until triaged; documented escape-hatch (`.gitleaksignore`) for false
  positives, but **not** for the publish-artifact gate (must not ship).
* Bad / accepted: gitleaks logic now exercised in three modes — mitigated by
  it being a single composite action with one version pin.

## Decision Outcome

Chosen: **Option 3**. Introduce `.github/workflows/_ci-pypi.yml` as the binding
CI reusable for every PyPI-published platform package.

**Two-layer control (the binding layer is the publish path, not PR CI):**

* **Binding — pre-publish gate (closed by construction).** PR-time CI only
  protects repos that adopt it, and the irreversible event (`twine upload` /
  `gh-action-pypi-publish` / public GitHub Release) lives in *separate*
  platform-repo `publish-*.yml` workflows that no package-repo CI can gate
  (often `workflow_dispatch`, which bypasses branch protection). Therefore the
  shared `gitleaks-scan` action in **`mode: sdist`** is wired into **every**
  publish workflow (`publish-iil-testkit`, `-codeguard`, `-ingest`,
  `publish-platform-context`, `publish-packages` — all 3 prod jobs + TestPyPI),
  immediately before upload. It unpacks and scans **every sdist and wheel** —
  the exact bytes that reach the index (artifact identity, strictly stronger
  than build-tool parity). These workflows live in this repo, so the gate is
  present **by construction for all packages today**, independent of adoption.
* **Shift-left — `_ci-pypi.yml` (metered, defense-in-depth).** The same
  hardened scan + library contract at PR time, so a secret is caught before it
  is ever merged. Adoption is rolling and measured (see Adoption gate).

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
* Good: **the cure is administered, not just shipped.** The earlier draft
  gated only PR CI while the irreversible `twine upload` lived in unguarded,
  separate `publish-*.yml`. The pre-publish gate now blocks the actual
  irreversible event for every package by construction; PR-CI adoption is
  defense-in-depth and is metered (adoption gate + tracking issue) rather
  than an unowned "rolling onboarding".
* Bad / accepted: the gate runs the gitleaks CLI inside each publish job
  (~10–20 s + one pinned-binary download per publish). Acceptable: publishes
  are infrequent and the alternative (a leaked, yanked release) is far costlier.
* Bad / accepted: scanning the built artifact cannot use the `.gitleaksignore`
  intent escape-hatch — a real secret in the shipping bytes must block,
  period. False positives are handled by excluding the file from the build
  (MANIFEST.in / package_data), not by suppression.

### Confirmation

Compliance is verified by construction and continuously, not by review alone:

1. **Pre-publish gate (binding).** Every `publish-*.yml` in this repo runs
   `gitleaks-scan@main` (`mode: sdist`) immediately before the upload/release
   step. A finding fails the job → no upload. This is structural: a new
   publish workflow without the gate is visible in PR review of *this* repo,
   and the gate references the single shared action (one version pin).
2. **Shift-left scan.** `_ci-pypi.yml` runs the same hardened scan at PR time
   for adopted packages.
3. **Adoption meter.** `pypi-ci-adoption-gate.yml` (weekly) lists every
   registry `type: library` repo not yet calling `_ci-pypi.yml` and maintains
   one tracking issue (label `adr-226-adoption`) — the shrinking backlog is
   the measurable rollout signal.
4. **Live verification.** PR #199: `gitleaks-scan` succeeded end-to-end on
   `iil-testkit` + `iil-promptfw` throwaway branches (real CI, then deleted).

### Deferred decisions

* **OIDC Trusted Publishing for the legacy publish workflows.**
  `publish-packages.yml` already uses `id-token: write` + `environment: pypi`
  + `pypa/gh-action-pypi-publish` (no long-lived token). The single-package
  legacy workflows (`publish-iil-testkit/-codeguard/-ingest`) still use a
  shared long-lived `PYPI_API_TOKEN` and no protected environment — a broader,
  more irreversible blast radius than the secret-in-artifact case this ADR
  closes. Migrating them to OIDC + a reviewer-protected `environment` is the
  natural next risk reduction; tracked as a follow-up, not blocking ADR-226.
* **Publish-workflow fragmentation.** Five hand-rolled `publish-*.yml` with
  divergent build tools (`hatchling` vs `python -m build`) and triggers. A
  shared `_publish-pypi.yml` reusable (carrying the gate + OIDC by default) is
  the consolidation target — separate ADR when scoped.
* **TestPyPI parity.** The gate is wired into the TestPyPI job too; if the
  TestPyPI path is later dropped, remove that gate with it.

### Implementation status

* `partial`: the **binding pre-publish gate is fully in place** (wired into
  all `publish-*.yml`), plus `_ci-pypi.yml` (+ `build`, matrix, blocking
  security), the shared composite actions, and the adoption meter. The scan
  was **live-verified end-to-end on throwaway branches in `iil-testkit` and
  `iil-promptfw`** (real CI; secret-scan + security green; branches deleted).
  Still `partial` (not `implemented`) because **no package has adopted
  `_ci-pypi.yml`** as its PR CI — onboarding PRs are deliberately out of scope
  (CI is red on pre-existing package debt the shared contract surfaced, not
  reusable defects). The irreversible-risk window is nonetheless **closed**
  via the by-construction publish gate; shift-left rollout is owner-paced and
  metered by the adoption issue. → `implemented` once the publish gate has run
  green on ≥1 real publish; → `verified` once ≥1 package consumes
  `_ci-pypi.yml` on `@main`.

## More Information

* PR #198 — secret-scan hardening this ADR reuses (mechanism revert + CLI
  migration + escape-hatch + fingerprint surfacing).
* ADR-057 (test strategy), ADR-058 (test taxonomy) — coverage-gate lineage.
* `.github/workflows/pypi-ci-adoption-gate.yml` — the adoption meter; its
  tracking issue (label `adr-226-adoption`) is the live rollout backlog.
* `.github/actions/gitleaks-scan` + `.github/actions/resolve-install-extra` —
  the shared composite actions introduced here (DRY single source).
* PR #199 — implementing PR (review history incl. advocatus-diabolus passes).

## Glossar

> Zielgruppe: Fachpersonal ohne IT-Hintergrund. Begriffe in der Reihenfolge
> des Alphabets, kontextbezogen erklärt.

* **Artefakt (build artifact)** — die fertig „verpackte" Software-Datei, die
  veröffentlicht wird (siehe *sdist*, *wheel*). Genau diese Datei landet bei
  den Nutzern; ein Fehler darin ist nach Veröffentlichung kaum rückholbar.
* **Blocking / blockierend** — eine Prüfung, die bei Fehlschlag den Vorgang
  *stoppt* (z. B. die Veröffentlichung verhindert), statt nur zu warnen.
* **CI (Continuous Integration)** — automatische Prüfungen (Tests, Stil,
  Sicherheits-Scan), die bei jeder Code-Änderung laufen.
* **Composite Action** — ein wiederverwendbarer Baustein für CI-Abläufe; hier
  die *eine* Stelle, an der der Geheimnis-Scan definiert ist (statt mehrfach
  kopiert → keine Abweichungen möglich).
* **gitleaks** — ein Werkzeug, das Code/Dateien nach versehentlich enthaltenen
  *Geheimnissen* (Passwörter, API-Schlüssel, Tokens) durchsucht.
* **OIDC / Trusted Publishing** — Veröffentlichen ohne langlebiges Passwort:
  PyPI vertraut kurzlebigen, automatisch erzeugten Nachweisen. Reduziert das
  Schadenspotenzial eines geleakten Tokens.
* **PyPI** — der öffentliche Python-Paket-Index; `pip install` lädt von dort.
  Eine einmal veröffentlichte Version ist praktisch unwiderruflich.
* **Reusable Workflow** — ein zentral gepflegter CI-Ablauf, den viele Repos
  „aufrufen", statt ihn je Repo selbst zu schreiben.
* **sdist (source distribution)** — das Quellcode-Paket (`.tar.gz`), das nach
  PyPI hochgeladen wird.
* **Secret / Geheimnis** — ein Zugangsdatum (Passwort, Token, Schlüssel), das
  niemals in Code oder Artefakt gelangen darf.
* **wheel** — das vorgebaute Installationspaket (`.whl`); kann andere Dateien
  enthalten als das *sdist*, daher werden beide gescannt.
