---
id: ADR-274
title: "Adopt iil-doc-templates as the reusable structured-document template engine (Django-app tier)"
status: accepted
decision_date: 2026-07-13
deciders:
  - "Achim Dehnert"
implementation_status: implemented
implementation_evidence:
  - "iil-doc-templates v0.3.1 (pyproject: reusable Django document template system — create, edit, fill templates with PDF extraction and LLM prefill)"
  - "risk-hub declares `iil-doc-templates>=0.3.1` as a normal index dependency (pyproject.toml)"
  - "risk-hub/src/explosionsschutz/apps.py imports doc_templates.views; risk-hub/src/projects/services.py returns DocumentTemplates from the doc_templates app"
  - "risk-hub ExConceptTemplateStore is a thin domain wrapper over the shared doc_templates app (template_json = serialized Pydantic ConceptTemplate + source_document FK)"
consulted: []
informed: []
domains:
  - architecture
  - tooling
tags: [iil-doc-templates, templates, structured-documents, django-app, prefill, ssot]
related:
  - "ADR-169"
  - "ADR-170"
  - "ADR-273"
---

# ADR-274: Adopt iil-doc-templates as the reusable structured-document template engine (Django-app tier)

## Context and Problem Statement

Multiple hubs need to produce **structured documents**: a prescribed set of
sections and fields, created (often by extracting a source PDF), then filled —
deterministically from data or via LLM prefill of individual fields. Examples: the
Explosionsschutzdokument in `risk-hub`, VVT / DSB records, and the fixed
criteria/grade **frame** of a thesis Gutachten.

`risk-hub` already solved this and depends on `iil-doc-templates` in production, but
the adoption was never recorded as a platform decision. ADR-273 (writing-hub as
composition SSoT) explicitly relies on all four `iil-*` packages being adoption-ADR
backed; `iil-enrichment` (ADR-169) and `iil-ingest` (ADR-170) have one, and
`iil-fieldprefill` has `risk-hub:ADR-042` — `iil-doc-templates` was the gap. This ADR
closes it (ADR-273 REC-A).

Without a recorded decision, the risk is: each hub grows its own template store, or
`iil-doc-templates` becomes a de-facto platform contract via incidental internals
(e.g. importing `doc_templates.views`) rather than a documented public surface.

## Decision Drivers

- **DRY**: structured-template + field-prefill logic must not be re-implemented per hub.
- **Consistency** with the existing `iil-*` reuse pattern (ADR-169/170).
- **A named boundary** to the generative long-form engine (writing-hub) — this package
  owns the *schema-/field-bound* mode, not narrative prose (ADR-273 fill-mode test).
- **A stable public surface** so consumers do not couple to Django internals.

## Considered Options

### Option A — Adopt `iil-doc-templates` as a reusable Django-app package (chosen)

A reusable Django app (`INSTALLED_APPS = ["doc_templates"]`, `include("doc_templates.urls")`)
providing `DocumentTemplate` (structure = sections→fields), `DocumentInstance`
(values), and services (`pdf_service`, `llm_service`, `template_service`,
`retriever`). Hubs compose it and may add a thin domain wrapper
(cf. `ExConceptTemplateStore`).

### Option B — Keep template logic inside risk-hub, other hubs import risk-hub

Wrong dependency direction (a domain hub as a base library); rejected — same reasoning
as ADR-170 Option B.

### Option C — Fold it into `iil-doc-templates`'s consumers ad hoc (no shared package)

Each hub re-implements sections/fields + PDF extraction + prefill → drift, the exact
failure this ADR prevents. Rejected.

## Decision Outcome

**Chosen: Option A.** `iil-doc-templates` is the platform's reusable engine for
**structured (schema-/field-bound) documents**. It is deliberately **Django-app tier**,
not the pure-Python-core tier of `iil-enrichment`/`iil-ingest`, because its value is the
persisted `DocumentTemplate`/`DocumentInstance` models plus admin/URL surface.

Boundary and obligations:

1. **Mode boundary (ADR-273).** `iil-doc-templates` owns the schema-/field-bound output
   mode. Narrative long-form prose stays in `writing-hub`. A composite document
   (e.g. Gutachten) uses this package for the frame and `writing-hub` for the prose,
   bound by a Composition Manifest (ADR-273 invariant 3).
2. **Public surface.** Consumers use a **documented public import surface**
   (the app's models/services API), **not** incidental internals such as
   `doc_templates.views`. Establishing/curating that public surface is a follow-up
   obligation of this adoption (see Confirmation).
3. **Contract-tested seam.** Each consuming hub vendors a contract test for its
   integration with `iil-doc-templates`, with the governance from ADR-273 invariant 5
   (owner, CI gate, supported version range, deprecation, regeneration/staleness).
4. **Domain wrappers, not forks.** A hub may add a thin domain wrapper
   (`ExConceptTemplateStore` is the reference), but must not re-implement the engine.

### Confirmation

- `risk-hub` continues to import from a documented `doc_templates` public surface
  (migrate off `doc_templates.views` internal import to the curated API).
- `writing-hub` consuming `iil-doc-templates` (per ADR-273, e.g. MBA-Grader frame)
  imports only the public surface + a vendored contract test.
- `iil-doc-templates` publishes a `catalog-info.yaml` (`spec.type: library`) and a
  documented public API section in its README.

## Consequences

**Positive**
- Closes ADR-273 REC-A: all four `iil-*` packages are adoption-ADR backed.
- One engine for structured documents; domain wrappers stay thin.
- Clean split from the generative engine via the ADR-273 fill-mode test.

**Negative / costs**
- The current `doc_templates.views` import in `risk-hub` is a fragile internal surface;
  curating a stable public API + migrating the import is real follow-up work.
- Django-app tier means consumers inherit a Django dependency (acceptable — all current
  consumers are Django hubs).

## Open Points

- Define and document the public import surface; migrate `risk-hub`'s
  `doc_templates.views` usage onto it.
- Correct the stale `iil-fieldprefill` README reference "ADR-107" (real adoption =
  `risk-hub:ADR-042`; `platform:ADR-107` is "Erweitertes Agent-Team") — same
  namespace-drift cleanup noted in ADR-273 Open Points.

## More Information

- **ADR-169** — iil-enrichment adoption (reuse-pattern precedent).
- **ADR-170** — iil-ingest adoption (reuse-pattern precedent).
- **ADR-273** — writing-hub as composition SSoT; this package is the schema-/field-bound
  half of its fill-mode test; adoption requested as REC-A.
- **risk-hub:ADR-042** — iil-fieldprefill adoption (the prefill orchestration this
  engine pairs with).
