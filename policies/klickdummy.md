# Policy: Klickdummy — Spec-first, Prod-safe, Off-Ramp

**Trigger words:** klickdummy, clickdummy, click dummy, mock-prototyp,
mock prototype, demo-render, demo render, `?demo=`, prototyp, prototype,
spec-driven, parity, ADR-180, ADR-211, klickdummy-i1, klickdummy-i2

> **DRAFT — pending review.** Distilled from `platform:ADR-211` Rev 4 by
> agent for issue `adr-211-followup/SF1` (#223). Normative text is the
> ADR; this is the operative restatement. Do not treat as accepted until
> ratified together with the ADR-211 PR. ADR-211 acceptance gate: status
> stays `proposed` until C1–C6 green.

## Rule

Any click-through artifact (klickdummy / mock / demo-render / spec-driven
UI) across **any** repo must satisfy four invariants. Approach is free
(hand-rolled, AI-generated, Figma-as-spec) **iff** I1–I4 hold.

- **I1 Spec-first** — the source of truth is a versioned, machine-readable
  spec artifact (YAML/JSON/structured frontmatter). Markdown bullets do
  **not** count. The klickdummy *renders* the spec; it is never the
  source. Enforced by `make -C <repo> klickdummy-i1` (exit code,
  CI-verified) — a frontmatter claim is not evidence.
- **I2 Prod safety** — exactly one class per klickdummy, **explicitly
  declared**: **Mock-Prototyp** (no backend; system boundaries as
  target-mocks) **or** **Demo-Render** (env-gated; unreachable in prod).
  "No class declared" is an I2 violation (no vacuous pass). Platform only
  checks **that** a repo-defined `make -C <repo> klickdummy-i2` exists
  and exits 0 — **never** a platform-wide string-grep.
- **I3 Lifecycle / off-ramp** — (A) no target system: ends at documented
  stakeholder review → ADR `accepted-frozen`/`superseded`, spec frozen,
  path `klickdummy/archive/`. (B) transition: per-screen once an impl
  route exists. (C) with target system: parity-green per screen ⇒ static
  source removed. **Staging is an explicitly allowed dual-source space**
  (parity runs there); the forbidden boundary is the **prod release**
  (tag/container push to prod), **not** staging.
- **I4 Namespace** — repo klickdummy ADR uses the reserved title prefix;
  cross-repo refs only as `repo:ADR-NNN` (regex
  `^[a-z][a-z0-9-]+:ADR-\d{3}$`).

Repo-local and untouched by this policy: tech stack, schema, UI building
blocks, test stack. Implementation ADRs (e.g. `risk-hub:ADR-046`) keep
their repo-locality; this policy replaces none of them.

## How to apply

1. Before building/registering a klickdummy: confirm a machine-readable
   spec exists (I1) and the class is explicitly declared (I2). No class
   → stop, it is non-conformant.
2. Demo-Render must be env-gated and proven unreachable in prod
   (repo-defined `klickdummy-i2`: prod smoke + middleware unit test,
   `?demo=` in prod → 404/disabled).
3. Once a screen has an impl route and green parity **and** ships in a
   prod release, the static source for that screen must be gone (I3).
   Staging may carry both sources — that is intended.
4. Reference another repo's klickdummy ADR only as `repo:ADR-NNN`.
5. Adoption is checked by the `onboard-repo` skill (I1–I4 + ADR header +
   `make klickdummy-{i1,i2,i3,i4}`) and
   `platform/scripts/checks/klickdummy_registry.sh`.

## Source ↔ injection (two layers — Home is NOT deprecated)

- **Rationale:** `platform:ADR-211`.
- **Source (versioned):** `platform/policies/klickdummy.md` (this file) —
  reviewable, single source.
- **Injection (operative):** `~/.claude/policies/klickdummy.md` is synced
  **from** this source via `~/.claude/bin/claude-policy` (same mechanism
  as `adr-threshold.md`/`llm-routing.md`; the UserPromptSubmit hook
  injects from `~/.claude/policies/`). The repo path **feeds** the home
  injection, it does **not** replace it. Source↔injection drift is itself
  a check (ADR-211 C6: `diff -q` source vs injected).

> ⚠️ Discrepancy flagged for review: issue #223's task list says
> "deprecate the home-dir path with a stub". ADR-211 Rev 4 supersedes
> that — Home is the injection target, kept and synced, **not**
> deprecated. This file follows the ADR; #223 wording should be updated.

## Relation

`platform:ADR-211` (rationale + executable acceptance gate C1–C6),
`adr-threshold.md` (self-test: this reverses repo-autonomous klickdummy
proliferation and closes a prod security surface across ≥3 repos).
