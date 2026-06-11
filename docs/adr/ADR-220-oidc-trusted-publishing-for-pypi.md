---
status: proposed
date: 2026-05-18
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-226-library-ci-reusable-mandatory-secret-scan.md"]
implementation_status: none
---

# Migrate token-based PyPI publish workflows to OIDC Trusted Publishing with protected environments

> **Trigger**: ADR-226 closed the *secret-in-artifact* vector by gating every
> `publish-*.yml` before upload. The advocatus-diabolus pass surfaced that the
> *next-larger* irreversible risk is now the publish **credential** itself: the
> single-package legacy workflows authenticate with a long-lived, shared
> `PYPI_API_TOKEN` and no protected environment.

---

## Context and Problem Statement

After ADR-226, the platform's PyPI publish surface is split in two:

* **Modern** — `publish-packages.yml` (django-tenancy, concept-templates,
  dvelop-client): already OIDC-based — `permissions: id-token: write`,
  `environment: { name: pypi }`, `pypa/gh-action-pypi-publish`. **No
  long-lived token.**
* **Legacy** — `publish-iil-testkit.yml`, `publish-iil-codeguard.yml`,
  `publish-iil-ingest.yml`: a single shared `secrets.PYPI_API_TOKEN`,
  `twine upload`, **no `environment:`**, `workflow_dispatch`-triggered.

A long-lived API token that can publish *several* packages is a high,
irreversible blast radius: a single leak (CI log, compromised dependency in
the publish job, malicious PR that reaches the token) lets an attacker
overwrite or yank any of those packages on the public index. ADR-226's
artifact scan does **not** mitigate credential compromise — different threat.

OIDC Trusted Publishing removes the standing credential entirely: PyPI mints a
short-lived, audience-scoped token per run, bound to a specific
repo + workflow + environment. Combined with a GitHub **protected
environment** (required reviewer), the publish step also gains a human gate on
the irreversible action.

## Decision Drivers

* No standing secret to leak beats rotating a secret faster (eliminate, don't
  manage). The credential is the largest remaining irreversible PyPI risk
  after ADR-226.
* Consistency: one publish pattern, not modern-vs-legacy. `publish-packages.yml`
  already proves the target shape in this repo.
* Defense in depth on the irreversible action: a protected `environment`
  adds an approval gate; OIDC scopes the credential to one workflow.
* Must not break publishing: Trusted Publishing requires a **per-project**
  PyPI-side registration that the workflow change alone cannot perform.

## Considered Options

1. **Do nothing** — keep the shared long-lived token. Rejected: known
   high-blast-radius standing credential; inconsistent with the modern path.
2. **Rotate the token + move it to a protected environment, keep `twine`** —
   Rejected: still a standing secret; only shortens the leak window, does not
   eliminate it; half the consistency win.
3. **Per-package short-lived tokens, manual rotation** — Rejected:
   operational toil, human-error-prone, still a standing secret between
   rotations.
4. **OIDC Trusted Publishing + protected `pypi` environment** (chosen) —
   no standing credential, scoped per workflow, human-gated, converges legacy
   onto the proven `publish-packages.yml` pattern.

## Pros and Cons of the Options

### Option 2 — Rotate + protected environment, keep twine
* Good: small change; adds a human gate.
* Bad: standing secret remains; rotation is recurring toil; partial consistency.

### Option 3 — Per-package short-lived tokens
* Good: smaller blast radius than one shared token.
* Bad: standing secrets still exist; manual rotation does not scale to ~14
  packages; the failure mode (expired/blocked publish) is silent and annoying.

### Option 4 — OIDC Trusted Publishing + protected environment (chosen)
* Good: **zero standing publish credential**; per-run, audience-scoped;
  per-repo+workflow+environment binding; human approval gate; one pattern
  platform-wide; `PYPI_API_TOKEN` secret can eventually be deleted.
* Good: composes cleanly with the ADR-226 pre-publish secret gate (gate stays
  exactly where it is, before the publish step).
* Bad / accepted: requires a **manual, per-project PyPI-side registration**
  (Trusted Publisher: owner + repo + workflow filename + environment) **before**
  the workflow change can take effect — otherwise the publish fails. Rollout
  must therefore be coordinated per package, not flipped atomically.
* Bad / accepted: OIDC requires `id-token: write` on the publish job; this is
  a *job-level* permission in a normal (non-reusable) workflow, so the
  #191/#198 reusable-narrowing trap does **not** apply here (these are
  standalone workflows, not called reusables).

## Decision Outcome

Chosen: **Option 4**. Converge the legacy single-package publish workflows
onto the OIDC + protected-environment pattern already used by
`publish-packages.yml`, preserving the ADR-226 pre-publish secret gate.

Target shape for each legacy `publish-*.yml` (build/scan unchanged; only
auth + environment change):

```yaml
publish:
  environment:
    name: pypi
    url: https://pypi.org/project/<dist-name>/
  permissions:
    id-token: write          # OIDC — no PYPI_API_TOKEN
  steps:
    - ...build...
    - twine check dist/*
    - uses: achimdehnert/platform/.github/actions/gitleaks-scan@main   # ADR-226 gate, unchanged
      with: { mode: sdist, source: dist, ... }
    - uses: pypa/gh-action-pypi-publish@release/v1                     # OIDC, no token env
```

### Rollout (ordered, per package — non-atomic by necessity)

1. Register the GitHub Actions Trusted Publisher on PyPI for the project
   (owner action, pypi.org → project → Publishing): repo
   `achimdehnert/platform`, workflow filename, environment `pypi`.
2. Create the `pypi` GitHub environment (optionally a required reviewer).
3. Merge the workflow change for that package.
4. Verify one real publish succeeds via OIDC.
5. After all legacy workflows migrated and verified: delete the
   `PYPI_API_TOKEN` repo/org secret.

### Consequences

* Good: the largest remaining irreversible PyPI risk (standing shared token)
  is eliminated, not merely shortened; one publish pattern platform-wide.
* Good: orthogonal to ADR-226 — the secret gate stays exactly where it is.
* Bad / accepted: a package whose Trusted Publisher is not yet registered
  **cannot publish** until step 1 is done. This is an ordering constraint, not
  a regression; documented in the rollout and the PR.
* Bad / accepted: a misconfigured environment (e.g. required reviewer
  unavailable) blocks an urgent publish — acceptable trade-off for a
  human gate on an irreversible public action; emergency path is a temporary
  reviewer or the documented token fallback until cutover completes.

### Confirmation

1. Per-package: a successful OIDC publish run (no `PYPI_API_TOKEN` in env)
   recorded against the rollout checklist.
2. Repo-wide: `grep PYPI_API_TOKEN .github/workflows/` returns nothing once
   cutover is complete (the standing-secret elimination is the success
   criterion, machine-checkable).
3. Consistency: every `publish-*.yml` has `permissions: id-token: write` +
   `environment:` and uses `pypa/gh-action-pypi-publish`.

### Implementation status

* `none`: decision recorded only. No workflow changed in this ADR's PR — the
  change is unsafe to merge before per-project PyPI Trusted Publisher
  registration (would break publishing). Implementation is owner-paced via the
  rollout checklist; this ADR is the contract it executes against.

## Glossar

> Zielgruppe: Fachpersonal ohne IT-Hintergrund.

* **API-Token (PyPI)** — ein langlebiges „Passwort", mit dem CI Pakete
  veröffentlicht. Wird es bekannt, kann jeder die betroffenen Pakete
  überschreiben — unwiderruflich.
* **Blast Radius / Schadenspotenzial** — wie viel kaputtgehen kann, wenn *ein*
  Geheimnis kompromittiert wird (hier: alle Pakete, die der geteilte Token
  veröffentlichen darf).
* **OIDC (OpenID Connect)** — ein Verfahren, bei dem GitHub für *einen*
  Veröffentlichungslauf einen kurzlebigen, eng begrenzten Nachweis erzeugt;
  es existiert kein dauerhaftes Passwort, das geleakt werden könnte.
* **Protected Environment** — eine GitHub-Schutzstufe, die einen Schritt (hier:
  Veröffentlichen) erst nach Freigabe durch eine benannte Person erlaubt.
* **Trusted Publisher** — eine bei PyPI hinterlegte Vertrauensbeziehung
  „dieses Repo + dieser Workflow + diese Umgebung darf dieses Paket
  veröffentlichen" — Voraussetzung dafür, dass OIDC funktioniert.

## More Information

* ADR-226 — library CI reusable + the pre-publish secret gate this builds on.
* `publish-packages.yml` — the in-repo reference implementation of the target
  pattern (OIDC + `environment: pypi` + `pypa/gh-action-pypi-publish`).
* PyPI docs — Trusted Publishers / `pypa/gh-action-pypi-publish`.
* Drift lesson `2026-05-18-secret-gate-wrong-workflow` (ADR-226 review): a
  control must sit at the irreversible action — here the *credential* is that
  surface, so OIDC removes the standing credential rather than guarding it.
