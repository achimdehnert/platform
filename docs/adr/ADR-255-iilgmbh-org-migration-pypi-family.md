---
id: ADR-255
title: "Migrate the iil-* PyPI package family from the personal achimdehnert account to the iilgmbh GitHub org + PyPI Organization"
status: accepted
decision_date: 2026-06-22
deciders: [Achim Dehnert]
consulted: [Claude Code, external LLM review (cross-provider)]
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

> Rev 4 (2026-07-05): **REC-1 owner condition — GitHub half now MET.** The
> `iilgmbh` GitHub org holds **≥ 2 independent owners** — `achimdehnert` and
> `wirdigital`, both `role=admin`, `state=active` (verified live:
> `gh api "orgs/iilgmbh/members?role=admin" --jq length` → `2`, 2026-07-05).
> This clears the Phase-0 sub-blocker "iilgmbh has only 1 owner" that was RED
> since Rev 2. **Still open on the same REC-1 clause (do NOT read this as
> readiness-complete):** (a) the **PyPI org `iil`** must likewise have ≥ 2
> owners — unverified here (not a GitHub API surface; check `pypi.org/org/iil/`
> members); (b) **team-bound repo roles** (access via team, not per-person);
> (c) a documented **recovery + offboarding path**; (d) a **periodic role +
> trusted-publisher review** cadence. Two owners are *necessary*, not
> *sufficient*, for the governance target state. **This changes nothing about
> the per-repo transfer gate (REC-2/REC-5):** acceptance still authorizes the
> method, not an unattended fan-out; `platform` itself is a separate,
> cutover-planned decision (see `docs/konzepte/`), not covered by this ADR.

> Rev 3 (2026-06-23): **accepted**. Method gate before any transfer is now
> implemented as code, not prose: the machine-readable migration SSoT lives at
> [`registry/iil-migration.yaml`](../../registry/iil-migration.yaml) (REC-3) with
> an idempotent checker at `tools/iil_migration_check.py`; the org-resolution
> convention (REC-4/REC-14) is anchored in `CORE_CONTEXT.md`. **Phase-0 gate and
> the per-repo strict sequence remain blocking — acceptance authorizes the method,
> not an unattended fan-out.** First-wave verification (2026-06-23) already
> surfaced a registry drift the checker is built to catch: `repo_owner` claimed
> `iil-testkit: iilgmbh`, but the repo is really `achimdehnert/iil-testkit`
> (corrected in `tools/registry-canonical.py`). Pilot trio fixed per REC-12:
> **(a) iil-adrfw** (no-rename, `publish.yml` already landed), **(b) promptfw →
> iil-promptfw** (rename), **(c) aifw → iil-aifw** (integration-rich + rename =
> hardest). Verified state at acceptance: iilgmbh holds 12 repos incl.
> iil-fieldprefill, iil-klickdummy, iil-relaunch, illustration-fw; the iil-* PyPI
> family otherwise still under `achimdehnert`.

> Rev 2 (2026-06-22): hardened after a cross-provider external review (Steelman →
> 3-role → out-of-the-box). The review's recommendation was **revise**; its valid
> findings (REC-1…14) are woven in below as our own reasoned clauses, not verbatim.
> The bus-factor goal can be formally "achieved" yet practically missed without a
> defined role/recovery/revocation target state — that gap is now closed here.

## Context

The `iil-*` Python packages (iil-adrfw, iil-aifw, iil-promptfw, iil-authoringfw,
iil-testkit, iil-reflex, iil-researchfw, iil-django-commons, iil-learnfw,
iil-outlinefw, iil-weltenfw, iil-illustrationfw, iil-nl2cadfw, iil-enrichment,
iil-fieldprefill, iil-ingest, iil-codeguard, …) are **company assets** of
iil.gmbh, but their GitHub repos still live under the **personal account**
`github.com/achimdehnert/*`, and the PyPI projects are owned by a **personal
PyPI account**.

Why now:
1. **The `iilgmbh` GitHub org already exists** and is the documented long-term
   home. Migration has started organically: `iil-klickdummy` + `iil-voice-agent`
   are already under `iilgmbh/*` (7 of ~52 repos moved).
2. **Publishing is cryptographically coupled to the repo owner.** PyPI Trusted
   Publishing (OIDC) matches the `repository_owner` claim GitHub signs into the
   token. While repos live under `achimdehnert`, every trusted publisher must
   name `achimdehnert` as owner — an `iilgmbh` owner only becomes valid **after**
   the repo moves. Any OIDC publisher configured now (e.g. iil-adrfw 0.6.0 on
   2026-06-22) is **throwaway** at migration.
3. **Bus-factor / governance risk.** Company packages whose ownership, secrets
   and publishing rights sit on one person's personal accounts cannot be handed
   over, audited or recovered cleanly if that person is unavailable.

Scoped first wave = the iil-* PyPI family (where ownership + publishing governance
bites hardest and OIDC setup is wasted under the wrong owner).

## Naming map (the three names are intentionally different)

GitHub-org, PyPI-org and the legacy personal account are **independent
namespaces** — they need not (and do not) share a name. This is deliberate, not
drift:

| Axis | Name | Role |
|---|---|---|
| GitHub organization | **`iilgmbh`** | repo home → signs the OIDC `repository_owner` claim that the trusted publisher matches |
| PyPI organization | **`iil`** | package ownership ("IIL Institut f. Informationslogistik GmbH"); matches the `iil-*` dist prefix |
| PyPI personal account (legacy) | **`iildehnert`** | currently owns the projects → transfer **out** into the `iil` org |
| Distribution prefix | **`iil-*`** | the published package names |

Decision: **keep the PyPI org `iil`** (it already exists, is the company, and
matches the `iil-*` package prefix) rather than create a second `iilgmbh` PyPI
org for cosmetic symmetry. Trusted Publishing matches the **GitHub** owner
(`iilgmbh`), independent of the PyPI org name, so the names matching buys nothing
functional; a second company org would mean duplicate identity and a likely
second paid subscription. The mapping above is the canonical answer to "why does
the PyPI org have a different name than the GitHub org?".

## Governance target state (the actual goal, not just relocation) — REC-1

Moving assets into an org is necessary but **not sufficient**; the migration must
land an explicit, verifiable end state, else org ownership is nominal while
control stays personal:

- **≥ 2 independent company-controlled owners** for both the GitHub org and the
  PyPI org (no single human is the sole admin of either).
- **Team-bound repo/project roles** (access via team membership, not per-person
  grants); the personal `achimdehnert` account's residual access is explicitly
  defined (ideally: maintainer-at-most, not owner).
- A documented **recovery + offboarding path** (how access is restored if an
  owner is unavailable; how a leaver is removed).
- A **periodic role + trusted-publisher review** cadence so ownership cannot
  silently re-personalize over time (M28-3).
- Stated **without** assuming a specific GitHub plan, SSO/SAML, or paid
  protection features — where a control needs such a feature, name the assumption.

## Phase-0 prerequisites gate (before ANY per-repo transfer) — REC-2

A blocking checklist, verified once up front (several items are currently
**unverified assumptions**, flagged honestly):

- [x] **PyPI Organization `iil` exists and is ours** — VERIFIED 2026-06-22:
      `pypi.org/org/iil/` → HTTP 200, profile = "IIL Institut f.
      Informationslogistik GmbH". **Remaining:** no `iil-*` projects are under the
      org yet (they still sit on the personal `iildehnert` account) — project
      transfer is the migration work; confirm the org owner-role target state above.
- [ ] The target **GitHub name is available** under `iilgmbh` for each repo.
- [ ] Target-org **Actions/Environments/Apps/Runners/permissions** that the first
      CI run depends on are present and policy-compatible (AD-12) — verify the
      effective org policies, not just the repo's.
- [ ] A break-glass runbook (below) is written before the first cutover.

## Migration registry — single source of truth — REC-3

A single **machine-readable registry** (e.g. `registry/iil-migration.yaml`) is
the SSoT for the whole migration; no second truth in prose. Per package it holds
at least: `dist`, `pypi_project`, `repo_current`, `repo_final`, `rename` (bool),
`workflow`, `environment`, `publisher_current`, `publisher_final`, `role_target`,
`dependencies`, `status`, `verification` (release proof). An **idempotent checker**
validates reality against it, so a later package cannot silently drift (M28-1/4).

## Decision

1. **GitHub:** Transfer the iil-* PyPI-family repos `achimdehnert/* → iilgmbh/*`
   (transfer preserves history/issues/PRs/stars + adds redirects).
2. **PyPI:** Own the packages under the **`iil` PyPI Organization**; transfer each
   project from the personal account to the org.
3. **Publishing:** Standardize on **OIDC Trusted Publishing under iilgmbh** with a
   hardened workflow baseline (REC-7, below). **Retire AND server-side-revoke** all
   `PYPI_API_TOKEN`s once OIDC works — removing the GitHub secret is not enough;
   the underlying PyPI token must be revoked and scrubbed from any other store
   (AD-15).
4. **Naming:** Align repo names with dist names where they diverge — but as a
   **separate gate**, not coupled to the transfer (REC-8). `Repo == Dist` is the
   **default with a documented exception path**, not an absolute rule (M28-5).
5. **Org resolution (not a default swap):** Replace the "default org =
   achimdehnert" assumption with an **explicit resolver** — `iil-*` (or registry
   entries) route to `iilgmbh`, while `achimdehnert`, `ttz-lif`, `meiki-lra`
   remain independent valid targets and **unknown projects get no silent
   fallback** (REC-4, AD-6).

### publish.yml security baseline — REC-7
Every migrated `publish.yml`:
- splits **build** and **publish** into separate jobs; only the **artifact** is
  passed between them;
- sets `id-token: write` **only on the publish job**, with otherwise minimal
  permissions;
- uses a dedicated **`pypi` environment** and **controlled release triggers**
  (not arbitrary branch pushes);
- pins the publish action and documents the protection mechanism within the
  org features actually available (AD-5).

## Migration order (per repo — strict sequence) — REC-5, REC-6, REC-8

One repo end-to-end before fan-out. **Restore publishing capability first; defer
non-critical reference updates** so the critical-path outage is as short as
possible:

1. Land the hardened OIDC `publish.yml` (done for iil-adrfw).
2. **(Rename gate, optional & separate)** If renaming: first scan name-dependent
   consumers; rename either before transfer with that scan, or after a green
   transfer — never bundle two identity changes blindly (REC-8).
3. **Transfer** `achimdehnert/<repo> → iilgmbh/<repo>`.
4. **Immediately restore CI + publishing:** re-create org/repo secrets needed by
   CI; register the `iilgmbh` trusted publisher; remove the old `achimdehnert`
   publisher; revoke the token.
5. **Verify identity by a real, logged release** through the **final** publisher
   — a dry-run only proves build/metadata/workflow-executability, **not** the
   production publisher identity (REC-6, AD-4). Record the release proof in the
   registry. Decide per package whether a transparent **migration-patch release**
   is acceptable or a time-boxed transitional state holds until the next
   feature-legitimate release (AD-14/M28-7).
6. **Then, as timed follow-ups (non-blocking):** update local remotes, CI
   badges, doc links and other non-critical references (REC-5).

## Secrets — smallest sensible scope — REC-10

Maintain a **secrets inventory + access matrix** (owner, purpose, rotation). Use
the **smallest sensible scope**, not a blanket "org-level preferred": org secrets
are exposed only to selected repos; shared secrets that widen blast radius are
justified per entry (AD-11).

## Break-glass token runbook — REC-9

If a short-lived API token is used as a cutover fallback, it is a **runbook**, not
a loose note: named principal, **project-scoped only**, created **only at incident
time**, transferred via a defined secure channel, with a **max lifetime**,
**server-side revocation immediately after use**, and a stored revocation proof
(AD-10).

## Consequences

**Positive:** company ownership + bus-factor genuinely resolved (with the target
state above); tokenless, non-expiring publishing; consistent repo/dist/publisher
naming; auditable, least-scope secrets; a registry-backed SSoT.

**Negative / costs:** every clone's remote must be updated; transient breakage of
hardcoded `achimdehnert/*` URLs; platform tooling that assumes `achimdehnert`
must migrate in lockstep; each PyPI ownership transfer is manual.

## Risks & recovery matrix — REC-11

"Nothing is destructive" was **too strong** (AD-9): removed publishers, revoked
tokens, external references and already-published versions are **not** undone by a
repo transfer-back. Replace blanket rollback with a **per-phase recovery matrix**:
each phase names its trigger, the back-out path, any new credentials required,
the external side-effects that persist, and **the point past which a forward-fix
beats a revert**.

## Kill-gate — measurable method gate — REC-12

Make the kill-gate measurable **before** the first transfer, on **3 pilot
profiles**: (a) a simple no-rename package, (b) a rename case, (c) an
integration-rich case (per the registry). Score **separately**: one-off platform
tooling effort vs. marginal per-repo operator time vs. publishing interruption vs.
manual interventions vs. broken critical integrations vs. residual stale refs. If
marginal per-repo cost (not the one-off platform fix) exceeds the governance
benefit, stop.

## Redirects + stale-ref hygiene — REC-13

GitHub redirects get a **bounded grace period**, after which an **automated check**
fails on remaining `achimdehnert/*` references. Generated artifacts are
**regenerated from their SSoT**, never hand-patched (M28-2/6).

## Bootstrap standard for new packages — REC-14

A lasting consequence: every **new** `iil-*` package is org-native from day one —
created under `iilgmbh`, registered in the PyPI org, final repo name, the hardened
OIDC workflow pattern, and a registry entry — so this misconfiguration cannot
recur (M28-8).

## Alternatives considered

- **Dual-publisher shadow cutover** (register the `iilgmbh` publisher and keep the
  old one until the first successful release): **worth piloting** on the first
  package to shrink the no-working-publisher window — adopt into the standard
  sequence if it verifies. *(Not rejected.)*
- **Central release broker** (one hardened repo publishes all artifacts):
  **rejected** — moves the bus-factor into a technical single point of failure and
  obscures artifact provenance.
- **Monorepo for the family**: **rejected** — couples independent versioning/
  history/access and is disproportionate to an ownership migration.

## Out of scope (this ADR)

- The remaining ~36 non-package `achimdehnert/*` repos (hubs/apps) — same
  principle, later waves, don't block publishing.
- Deleting the stale duplicate checkout `iil-adrfw-repo` (housekeeping).

## External review trace

Hardened via a cross-provider external review on 2026-06-22 (Steelman → 3-role →
out-of-the-box). All findings were context-faithful (none rolled back the settled
choices: iilgmbh-as-target, OIDC-as-mechanism, ADR-warranted, PyPI-family-first).
Valid findings incorporated as REC-1…14 above; broker/monorepo recorded as
considered-and-rejected; dual-publisher-shadow kept as a pilot option.
