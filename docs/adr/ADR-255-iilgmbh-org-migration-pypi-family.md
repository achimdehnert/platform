---
id: ADR-255
title: "Migrate the iil-* PyPI package family from the personal achimdehnert account to the iilgmbh GitHub org + PyPI Organization"
status: proposed
decision_date: 2026-06-22
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh, achimdehnert]
domains: [governance, packaging, ci-cd, security, architecture]
supersedes: []
amends: []
depends_on: []
related: [ADR-230, ADR-233]
tags: [governance, pypi, trusted-publishing, oidc, github-org, iilgmbh, migration, bus-factor, ownership]
scope:
  include_paths:
    - "docs/adr/ADR-255-*"
---

# ADR-255 — iilgmbh org migration for the iil-* PyPI family

## Context

The `iil-*` Python packages (iil-adrfw, iil-aifw, iil-promptfw, iil-authoringfw,
iil-testkit, iil-reflex, iil-researchfw, iil-django-commons, iil-learnfw,
iil-outlinefw, iil-weltenfw, iil-illustrationfw, iil-nl2cadfw, iil-enrichment,
iil-fieldprefill, iil-ingest, iil-codeguard, …) are **company assets** of
iil.gmbh, but their GitHub repos still live under the **personal account**
`github.com/achimdehnert/*`, and the PyPI projects are owned by a **personal
PyPI account**.

Three facts make this the right moment to record a decision:

1. **The `iilgmbh` GitHub org already exists** and is the documented long-term
   home. Migration has already started organically: `iil-klickdummy` and
   `iil-voice-agent` are already under `iilgmbh/*` (7 of ~52 repos moved).
2. **Publishing is cryptographically coupled to the repo owner.** PyPI Trusted
   Publishing (OIDC) matches the `repository_owner` claim that GitHub signs into
   the token (see [[pypi-trusted-publishing-oidc]]). While repos live under
   `achimdehnert`, every trusted publisher must name `achimdehnert` as owner —
   an `iilgmbh` owner only becomes valid **after** the repo moves. So any OIDC
   publisher we configure now (e.g. the one set up for iil-adrfw 0.6.0 on
   2026-06-22) is **throwaway** at migration.
3. **Bus-factor / governance risk.** Company packages whose ownership, secrets,
   and publishing rights sit on one person's personal accounts cannot be handed
   over, audited, or recovered cleanly if that person is unavailable.

This decision is **org-wide in principle** but **scoped in its first wave** to
the iil-* PyPI family, because that is where ownership + publishing governance
bites hardest and where OIDC setup is wasted if done under the wrong owner.

## Decision

1. **GitHub:** Transfer the iil-* PyPI-family repos from `achimdehnert/*` to
   `iilgmbh/*` (GitHub transfer preserves history, issues, PRs, stars and adds
   automatic owner→new-owner redirects).
2. **PyPI:** Create/own the packages under a **PyPI Organization** (`iil`),
   transferring each project's ownership from the personal account to the org.
3. **Publishing:** Standardize on **OIDC Trusted Publishing under iilgmbh** —
   each repo's `publish.yml` requests `id-token: write` and uses
   `pypa/gh-action-pypi-publish`; each PyPI project registers a trusted
   publisher `Owner=iilgmbh, Repository=<repo>, Workflow=publish.yml,
   Environment=pypi`. **Retire all `PYPI_API_TOKEN` secrets** once OIDC works.
4. **Naming:** Align GitHub repo names with their dist names where they diverge
   (e.g. `aifw`→`iil-aifw`, `illustration-fw`→`iil-illustrationfw`) as part of
   the transfer, so repo == dist == publisher claim are consistent.
5. **Tooling defaults:** Update the platform's "default org = achimdehnert"
   assumption (user `CLAUDE.md`, `repo-registry.yaml`, `project-facts`,
   `sync-workflows`, CI badge/URL references) to treat `iilgmbh` as the home of
   the iil-* family.

## Migration order (per repo — strict sequence)

Do **one repo end-to-end** before fanning out; the order matters because a
mid-transfer repo cannot publish:

1. Land an OIDC `publish.yml` on the repo (already done for iil-adrfw).
2. **Transfer** the GitHub repo `achimdehnert/<repo>` → `iilgmbh/<repo>`.
3. Update local remotes in all working trees (`git remote set-url`), CI badge
   URLs, and any cross-repo references.
4. Re-create repo/org **secrets** that did not transfer (org-level secrets
   preferred over per-repo).
5. **PyPI:** add the project to the `iil` PyPI Organization; register the
   trusted publisher with `Owner=iilgmbh`; remove the old `achimdehnert`
   publisher and the `PYPI_API_TOKEN`.
6. Verify: dispatch `publish.yml` (dry-run) → green; a real patch release → on PyPI.

## Consequences

**Positive:** company ownership + bus-factor resolved; tokenless, non-expiring
publishing; consistent repo/dist/publisher naming; auditable org-level secrets;
a single documented home for the family.

**Negative / costs:** every clone's remote must be updated; transient breakage
of hardcoded `achimdehnert/*` URLs (mitigated by GitHub redirects, but they
should not be relied on long-term); platform tooling that assumes
`achimdehnert` as default org must be updated in lockstep; each PyPI project
ownership transfer is manual and irreversible-ish (needs care).

## Risks & rollback

- **Risk:** a repo is transferred but its trusted publisher / token isn't
  reconfigured → publishing blocked. **Mitigation:** the per-repo sequence above
  finishes publishing setup before declaring the repo "done"; keep a fresh
  short-lived API token as a break-glass fallback during cutover.
- **Risk:** platform tooling breaks on `achimdehnert` assumptions.
  **Mitigation:** migrate tooling defaults in the same wave; GitHub redirects
  buy a grace period.
- **Rollback:** GitHub repos can be transferred back; PyPI org ownership can be
  reassigned. Nothing is destructive if done per-repo with verification gates.

## Out of scope (this ADR)

- The remaining ~36 non-package `achimdehnert/*` repos (hubs/apps) — same
  principle applies, but they are later waves and do not block publishing.
- Deleting the stale duplicate checkout `iil-adrfw-repo` (housekeeping, separate).

## Kill-gate

If, after migrating the first 3 packages, the per-repo cutover cost (tooling
breakage, redirect fallout) exceeds the governance benefit, stop and revisit —
do not push the remaining family through a process that is net-negative.
