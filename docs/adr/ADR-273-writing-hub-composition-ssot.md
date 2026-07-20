---
id: ADR-273
title: "writing-hub as composition SSoT for generative long-form authoring; facts and structured templates via shared iil-* packages"
status: proposed
decision_date: 2026-07-13
deciders:
  - "Achim Dehnert"
consulted: []
informed: []
ai_sparring_by:
  - tool: other
    date: 2026-07-13
    role: adversarial-review
    summary: "Two independent external-LLM reviews via /adr-handoff-extern (manual handoff); both verdict revise; convergent on composite-owner gap, fail-open-for-compliance, override governance, build reproducibility, fill-mode tool-vs-contract. Return-flow tag table in body."
domains:
  - architecture
  - authoring
  - governance
tags: [writing-hub, ssot, iil-doc-templates, iil-ingest, iil-enrichment, iil-fieldprefill, composition, fill-mode, provenance]
related:
  - "ADR-169"
  - "ADR-170"
  - "ADR-155"
  - "ADR-253"
  - "ADR-254"
  - "ADR-274"
---

# ADR-273: writing-hub as composition SSoT for generative long-form authoring; facts and structured templates via shared iil-* packages

## Context and Problem Statement

Multiple planned deliverables are "produce a qualified written artifact": research
reports, NIS2/DSB compliance reports, and thesis evaluation reports (MBA-Grader /
Bachelor- und Master-Gutachten). The recurring architectural question is where each
concern belongs:

- Is `writing-hub` the single source of truth (SSoT) for "writing", or do domain
  hubs own their own report generation, or does `writing-hub` consume from domain
  hubs?
- Where do **templates** live when a document is partly a fixed form and partly
  generated prose?

Without a written invariant, two failure modes recur:

1. `writing-hub` drifts into storing domain **facts** (regulatory corpora,
   occupational-safety rules) → two canonical stores for the same facts → drift.
2. Domain hubs re-implement a **writing pipeline** each → two+ authoring engines.

A third question: the platform already ships four reusable packages that cover parts
of this (`iil-enrichment`, `iil-ingest`, `iil-doc-templates`, `iil-fieldprefill`).
The decision must state how `writing-hub` relates to them so future placement is
mechanical, not re-litigated per feature.

## Decision Drivers

- Exactly one canonical store per concern (fact, artifact, template-of-a-mode).
- Reuse the ADR-backed shared packages instead of re-building their capabilities.
- A test any contributor can apply to place a new document type without an ADR.
- Grounded in patterns already live in the codebase, not aspiration.
- **Reproducibility**: a qualified artifact must be explainable later from recorded inputs.

## Considered Options

1. **writing-hub as a monolithic "writing SSoT"** owning facts, templates, and
   generation for every domain.
2. **Report generation per domain hub** (risk-hub generates its own reports, …).
3. **writing-hub as a composition layer** — SSoT for the generative long-form
   *artifact + method*, composing the shared `iil-*` packages, consuming domain
   facts read-only.

## Decision Outcome

**Chosen: Option 3 — writing-hub as composition SSoT.** Six invariants:

1. **Artifact + method SSoT (bounded).** `writing-hub` is the single canonical home
   for *generative long-form authoring* and owns the produced artifact's lifecycle
   (status, revisions, approval, export, archive). "Method" is **not** open-ended —
   see §"What writing-hub owns vs composes vs leaves". It does **not** store domain
   facts.
2. **Facts SSoT elsewhere, consumed read-only.** Domain facts live in the owning
   domain hub (`risk-hub/dsb` for privacy/NIS2, `weltenhub` for fictional worlds) or
   an external authoritative corpus (EUR-Lex, BSI, arXiv). `writing-hub`'s **render
   and generation paths are strictly read-only**; any mutation of a canonical fact is
   an explicit, authorized **command** to the owning hub, never a side effect of
   rendering (this resolves the `save_to_weltenhub(...)` write-back: it is a distinct
   authoring action, not part of consume). Consumed facts enter a build as an
   **immutable snapshot** (see invariant 6), not a live re-resolution per stage.
3. **Templates follow their fill-mode; composite templates get a Composition
   Manifest.** See the fill-mode test and the composite-document section below. The
   Composition Manifest **is** the SSoT for a composite document type's template,
   closing the gap that invariant 1 (artifact) and a per-mode template would
   otherwise leave.
4. **Compose over the shared packages via their public surfaces.** `writing-hub`
   uses `iil-enrichment`, `iil-ingest`, `iil-doc-templates`, `iil-fieldprefill`
   through a **documented public import surface** per package (not incidental Django
   internals such as `doc_templates.views`). All four are adoption-ADR backed:
   `iil-enrichment`=platform:ADR-169, `iil-ingest`=platform:ADR-170,
   `iil-doc-templates`=platform:ADR-274, `iil-fieldprefill`=risk-hub:ADR-042. The
   public-surface migration for `iil-doc-templates` is tracked in ADR-274.
5. **Contract-test the seams, with governance.** Every cross-package / cross-repo
   integration boundary gets a **vendored** contract test that itself has: an owner,
   a mandatory CI gate, a declared supported version range, a deprecation policy, and
   a regeneration/staleness rule for the vendored copy (platform:ADR-155).
6. **Build provenance for qualified artifacts.** A qualified/compliance/evaluation
   artifact records an immutable `DocumentBuild` provenance record: resolved fact
   ids+versions+content-hashes, applied overrides, and template/prompt/model/package/
   pipeline versions. Low-stakes artifacts (e.g. fiction drafts) may opt out.

### The fill-mode test (by output contract, not by tool)

> Is the required output a **schema-/field-bound structured contract**, or **narrative
> long-form prose**? — decided by the *output contract*, **not** by whether an LLM is
> involved (both `iil-doc-templates` and `iil-fieldprefill` use LLM prefill, so "LLM
> vs not" does not discriminate).

| | Schema-/field-bound output | Narrative long-form output |
|---|---|---|
| Output | compliance record, structured form, a Gutachten's criteria/grade **frame** | report/essay prose, a Gutachten's per-criterion **justification** |
| Home | domain hub, on top of **`iil-doc-templates`** (sections→fields) + **`iil-fieldprefill`** | **writing-hub** pipeline + `peer_review_service` |
| Template = | prescribed form (sections/fields) | structure frame for generative slots |

The mode is a property of the **output contract per segment**, evaluated at the
segment level, so re-classifying a segment is a manifest data-edit, not a cross-repo
code move.

### Composite documents (the "both" case) — orchestration and ownership

A document that is **both** (e.g. a thesis Gutachten: fixed criteria/grade frame +
generated per-criterion justification) is described by a **versioned Composition
Manifest** owned by `writing-hub`:

- The manifest declares, per **segment**: output contract (schema-bound / narrative),
  producer (a shared package / the writing-hub pipeline), data source (which domain
  hub or corpus), and read-only vs command semantics.
- **Orchestration owner = `writing-hub`** (it owns the final assembled artifact and
  its state machine). Domain hubs are **called**, never the orchestrator, to keep one
  dependency direction (invariant 7 below).
- Assembly per composite type: `iil-ingest` reads inputs, `iil-doc-templates` +
  `iil-fieldprefill` fill the schema-bound segments, `writing-hub` generates the
  narrative segments, and the manifest binds them into one owned artifact.

### Integration direction (no cycles)

Dependency direction is fixed: **`writing-hub` → domain hubs / packages**, never the
reverse. No mutual Django-model imports between `writing-hub` and a domain hub; the
seam is a typed client / package API with idempotent reads, explicit timeouts, retries,
and version negotiation. A domain hub that needs a mostly-deterministic report with a
**bounded** LLM-prose share MAY emit it via `iil-*` + a thin LLM call **without**
importing the full `writing-hub` pipeline — the "engine-duplicate" line is drawn by
proportion of narrative content, not by "any LLM prose at all".

### Failure semantics (domain-parametrized, not uniform)

`*_available=False` graceful degradation is **only** for low-stakes domains (fiction).
For compliance / authoritative-corpus facts the default is **fail-closed**: a missing
required source blocks the build (or at minimum blocks approval and export) and marks
the artifact invalid; optional sources produce a visible warning status; stale data is
used only under a documented staleness rule. A silently partially-ungrounded qualified
document is treated as more dangerous than a hard stop.

### Project-local overrides (governed, non-canonical)

Overrides are explicitly **non-canonical build inputs**, not a second truth store. Each
override records provenance (the canonical id+version it overrides), scope, precedence,
author, timestamp, output visibility, a review/expiry policy, and conflict behavior;
an optional promotion path writes the value back to the owning hub as a command
(invariant 2). **Overrides of authoritative-corpus (regulatory) facts are forbidden** —
only a corrective command to the owning hub is allowed.

### What writing-hub owns vs composes vs leaves (bounding "method")

- **Owns:** long-form generation, peer review, revision/DAG, the artifact lifecycle,
  the Composition Manifest, export of the assembled artifact.
- **Composes (does not own):** ingest (`iil-ingest`), structured templating +
  field prefill (`iil-doc-templates` / `iil-fieldprefill`), fact enrichment
  (`iil-enrichment`).
- **Leaves to domain hubs / corpora:** canonical facts, domain-prescribed compliance
  records, and any deterministic form-fill document whose structure is domain-owned.

### Package → role map (verified in code, 2026-07-13)

| Package | Adoption ADR | Role | Reference impl (verified) |
|---|---|---|---|
| `iil-enrichment` | platform:ADR-169 | bridge managed records ↔ external authoritative sources | generic form of `writing-hub/apps/worlds` ↔ `weltenhub` consume |
| `iil-ingest` | platform:ADR-170 | document ingestion (pdf/ocr) | `risk-hub` deps + ex-schutz |
| `iil-doc-templates` | platform:ADR-274 | sections→fields templates, PDF extract + LLM prefill | `risk-hub/src/explosionsschutz/apps.py` imports `doc_templates.views` (a fragile internal surface — public-surface migration tracked in ADR-274); `ExConceptTemplateStore` is a thin domain wrapper |
| `iil-fieldprefill` | risk-hub:ADR-042 | prefill orchestration via `register_retriever`/`register_system_prompt` plugin registry | `writing-hub/apps/outlines/retrievers.py` **and** `risk-hub/.../ex_doc_prefill.py` register into the same registry |

### Reference implementations proving the pattern is already live

- **Fact consumption (invariant 2):** `writing-hub/apps/worlds` stores
  `ProjectWorldLink.weltenhub_world_id` (a reference) + project-local overrides, reads
  canonical data via `client.worlds.get(...)`; the `save_to_weltenhub(...)` path is an
  explicit authoring **command**, not part of the read path (invariant 2).
- **Compose over shared registry (invariant 4):** both `writing-hub`
  (`apps/outlines/retrievers.py`) and `risk-hub` register into `iil-fieldprefill` via
  the same `register_retriever` / `register_system_prompt` plugin surface.
- **Domain wrapper over shared template engine (invariant 3):**
  `risk-hub`'s `ExConceptTemplateStore` sits on top of the shared `doc_templates` app.

## Consequences

**Positive**

- New document types are placed by the fill-mode test → a package choice, not an ADR
  (subject to the ADR-threshold caveat below).
- No duplicated facts, no duplicated authoring engines.
- The three named use cases become composition of existing, ADR-backed parts:
  - **Research reports / NIS2/DSB:** `writing-hub` pipeline + `iil-enrichment`
    connectors; NIS2/DSB facts consumed read-only from `risk-hub/dsb` (`Policy`,
    `PrivacyAudit`, `NIS2ReadinessStatus`, VVT lookups).
  - **MBA-Grader:** `iil-ingest` (thesis) + `iil-doc-templates`/`iil-fieldprefill`
    (Gutachten frame) + `writing-hub/peer_review_service` (evaluation prose), bound by
    a Composition Manifest.

**Negative / costs**

- `writing-hub` gains dependencies on `iil-ingest` and `iil-doc-templates` (already
  depends on `iil-fieldprefill`), and becomes an integration nexus — mitigated by the
  fixed one-way dependency direction.
- Read-time coupling to domain hubs needs the failure matrix and the immutable
  snapshot — real added mechanism.
- **Re-classifying a segment's mode** is a manifest data-edit (mitigated by invariant
  3); changing an entire doc-type's home is still a cross-repo move.
- Contract tests + provenance records + manifest schema versioning are ongoing cost.

**ADR-threshold caveat (invariant 3):** "no ADR for a new document type" holds **only**
while the existing ADR threshold is not crossed — a new document type that introduces a
new service boundary, cross-repo dependency, or security/sovereignty/licensing surface
**does** need its own ADR.

## Open Points / follow-ups

- **REC-A (resolved):** `iil-doc-templates` gets its own platform adoption ADR —
  **platform:ADR-274** (decided 2026-07-13). Still open there: curate its public import
  surface and migrate `risk-hub`'s `doc_templates.views` usage onto it; correct the
  `iil-fieldprefill` README's stale "ADR-107" reference (real adoption = risk-hub:ADR-042;
  platform:ADR-107 is "Erweitertes Agent-Team").
- **Namespace drift (🌀):** cross-repo ADR refs are repo-qualified throughout
  (`platform:ADR-155` vs `writing-hub:ADR-155` serien-dramaturgie collision). Treated
  as a traceability precondition, not cosmetic.

## External sparring — return-flow audit (Step 5, KONZ-platform-010)

Two independent external reviews (manual handoff, 2026-07-13); both verdict **revise**,
convergent on the composite-owner gap, fail-open-for-compliance, override governance,
build reproducibility, and the tool-vs-contract fill-mode flaw. Tag table (only
`[valid]` flowed in, as changes with our own reasoning):

| Finding (synthesized) | Source IDs | Verdikt | Applied as |
|---|---|---|---|
| Composite doc has no orchestration/final-artifact owner | R1 AD-1/M28-2, R2 AD-1/M28-1 | valid | inv. 3 + Composition Manifest §, inv. 1 (artifact lifecycle) |
| read-only claim contradicts `save_to_weltenhub` | R1 AD-2 | valid | inv. 2 (mutation = explicit command) |
| overrides = second truth store, ungoverned | R1 AD-3/M28-3, R2 AD-4/M28-2 | valid | Overrides § (provenance/expiry; corpus overrides forbidden) |
| fail-open unsafe for compliance | R1 AD-4/M28-4, R2 AD-3/M28-3 | valid | Failure-semantics § (domain-parametrized, fail-closed) |
| no immutable snapshot → non-reproducible build | R1 AD-5/M28-1 | valid (scoped) | inv. 6 (provenance for qualified artifacts; low-stakes opt-out) |
| fill-mode test tool-based, not mechanical | R1 AD-6, R2 AD-5 | valid | fill-mode test rewritten to output-contract, per-segment |
| inv. 4 "ADR-backed" false for doc-templates | R2 AD-2, R1 AD-9/AD-11 | valid | inv. 4 (public surface) + platform:ADR-274 adoption (REC-A resolved) |
| "no ADR for new doc-type" vs ADR-threshold | R1 AD-8 | valid | ADR-threshold caveat |
| integration direction / mutual deps | R1 AD-7, R2 (OOB-C coupling) | valid | Integration-direction § (one-way, no model deps) |
| "method" too broad → god-hub | R1 AD-10/M28-5, R2 M28-5 | valid | "owns vs composes vs leaves" § |
| contract tests lack owner/CI/version/deprecation | R1 AD-11/M28-6, R2 AD-8/M28-4 | valid | inv. 5 (governance) |
| template-of-a-mode SSoT tension | R2 AD-7 | valid | inv. 3 (manifest = composite-template SSoT) |
| domain hub may emit bounded-prose report w/o full pipeline | R2 AD-6/REC-7 | valid (boundary read only) | Integration-direction § (proportion line); does **not** reopen writing-hub-as-home |
| namespace collisions undermine traceability | R1 AD-12/REC-11, R2 REC-4 | valid | Open Points (precondition, repo-qualified refs) |
| buy DITA/CCMS instead of iil-* | R2 OOB-B | out-of-scope | rejected — violates settled single-org `iil-*`/sovereignty constraints |
| extract `iil-compose` neutral 5th package | R2 OOB-C | missversteht-context | rejected — contradicts settled "writing-hub is home"; the coupling *question* it raises is handled via Integration-direction § |
