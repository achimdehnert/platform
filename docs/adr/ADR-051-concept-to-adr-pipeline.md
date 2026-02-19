---
id: ADR-051
title: "Concept-to-ADR Pipeline — Idea Capture & AI-Assisted Promotion"
status: draft
date: 2026-02-19
author: Achim Dehnert
owner: Achim Dehnert
scope: dev-hub, platform
tags: [dev-hub, adr-lifecycle, workflow, concept, governance, cascade]
related: [ADR-050, ADR-015, ADR-054]
last_verified: 2026-02-19
---

# ADR-051: Concept-to-ADR Pipeline — Idea Capture & AI-Assisted Promotion

## Context

The platform uses Architecture Decision Records (ADRs) to document significant
technical decisions. ADRs live as markdown files in the `platform` repository
(GitHub = Single Source of Truth) and are imported into dev-hub for lifecycle
management and browsing.

**Problem**: There is no structured path from "I have an idea" to "This is a
formal ADR". Ideas get lost in chat conversations, Windsurf sessions, or
informal discussions. By the time someone writes an ADR, context and rationale
may have been forgotten or diluted.

**Current gap**:
- No way to capture early-stage ideas before they are mature enough for an ADR
- No file/document upload capability for supporting materials (diagrams, specs)
- No review workflow for concepts before they become formal ADRs
- ADRs can only be imported from existing markdown files, not created in-app

**SSOT constraint**: GitHub (`platform/docs/adr/`) is the canonical location
for all ADRs. The dev-hub database is a read mirror. Any new ADR **must** be
created as a `.md` file in the platform repo first, then imported into dev-hub.

## Decision

Introduce a **two-phase pipeline** that spans two tools:
- **dev-hub** (devhub.iil.pet) = Concept Inbox — low-barrier idea capture
- **IDE + Cascade** = ADR Author — AI-assisted ADR writing & GitHub push

### Phase A: Concept Capture (dev-hub)

A new `Concept` model in the `adr_lifecycle` app captures early-stage ideas:

```python
class Concept(TenantAwareModel):
    title = CharField(max_length=300)
    description = TextField(help_text="Freeform idea description")
    motivation = TextField(blank=True, help_text="Why is this needed?")
    author = ForeignKey(User, on_delete=SET_NULL, null=True)
    status = CharField(choices=[
        ("draft", "Draft"),
        ("under_review", "Under Review"),
        ("ready_for_adr", "Ready for ADR"),
        ("promoted", "Promoted to ADR"),
        ("parked", "Parked"),
        ("rejected", "Rejected"),
    ], default="draft")
    promoted_to_adr_id = CharField(
        max_length=20, blank=True,
        help_text="ADR ID after promotion, e.g. ADR-052"
    )
    tags = JSONField(default=list, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

File attachments for supporting materials:

```python
class ConceptAttachment(TenantAwareModel):
    concept = ForeignKey(Concept, related_name="attachments", on_delete=CASCADE)
    file = FileField(upload_to="concepts/%Y/%m/")
    filename = CharField(max_length=255)
    description = CharField(max_length=500, blank=True)
    uploaded_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    uploaded_at = DateTimeField(auto_now_add=True)
```

**Key design choice**: The Concept does NOT create an ADR in the database.
It only captures the idea. The `promoted_to_adr_id` field is a simple string
reference (e.g. "ADR-052"), not a ForeignKey — because the ADR is created in
GitHub first and only later imported into the DB.

### Phase B: ADR Creation (IDE + Cascade)

When a concept is marked `ready_for_adr`, the user switches to their IDE and
tells Cascade:

> "Concept #42 in devhub is ready for an ADR."

Cascade then:

1. **Reads the Concept** from the dev-hub database (via postgres MCP)
2. **Determines next ADR number** by scanning `platform/docs/adr/` on GitHub:
   - Parse all `ADR-NNN-*.md` filenames
   - Filter to standard range (001–099 series)
   - `next_id = max(standard_numbers) + 1`
   - Present to user: "Next available: ADR-052. Confirm?"
3. **Writes the ADR markdown** using the concept's content as input:
   - Full YAML frontmatter (id, title, status:draft, date, author, tags)
   - Context section from concept description
   - Motivation section from concept motivation
   - Decision section (Cascade drafts based on context, user refines)
   - Consequences (positive, negative, risks)
   - References to attachments (if any)
4. **Pushes to GitHub** (`platform/docs/adr/ADR-052-<slug>.md` on main)
5. **Updates the Concept** in dev-hub DB:
   - Sets `status = "promoted"`
   - Sets `promoted_to_adr_id = "ADR-052"`
6. **Imports the new ADR** into dev-hub DB (same as existing import flow)

### ADR Number Assignment — Robust Algorithm

```
1. List all files matching ADR-*.md in platform/docs/adr/
2. Extract numeric part: ADR-001 → 1, ADR-050 → 50
3. Ignore non-standard ranges: ADR-400 (special), ADR-2026-001 (yearly)
4. Standard range = numbers 1–399
5. next_id = max(standard_range) + 1
6. Confirm with user before creating
```

**Why no auto-increment in DB**: ADR numbers must be globally unique across
all environments (GitHub, dev-hub, local clones). A DB sequence would diverge.
The filesystem in the platform repo is the authoritative numbering source.

### End-to-End Workflow

```
┌─────────────────────────────────────────────────────┐
│  Phase A: Concept Capture (devhub.iil.pet)          │
│                                                     │
│  1. User clicks "New Concept" on /adrs/concepts/    │
│  2. Fills in: title, description, motivation, tags  │
│  3. Uploads files (PDFs, diagrams, screenshots)     │
│  4. Saves as "draft"                                │
│  5. Optional: reviews, edits, sets "ready_for_adr"  │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  Phase B: ADR Creation (IDE + Cascade)              │
│                                                     │
│  6. User: "Concept #42 is ready for ADR"            │
│  7. Cascade reads concept from devhub DB            │
│  8. Cascade determines next ADR number              │
│  9. Cascade writes ADR-052-<slug>.md                │
│  10. Cascade pushes to GitHub (SSOT!)               │
│  11. Cascade imports ADR into devhub DB             │
│  12. Cascade sets concept status → "promoted"       │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  Result                                             │
│                                                     │
│  • GitHub: ADR-052-<slug>.md exists (SSOT)          │
│  • devhub: ADR-052 visible in /adrs/ (draft)        │
│  • devhub: Concept #42 marked "promoted"            │
│  • Audit trail: concept → ADR link preserved        │
└─────────────────────────────────────────────────────┘
```

### UI: Concept Views in dev-hub

```python
# In adr_lifecycle/urls.py
path("concepts/", ConceptListView, name="concept-list"),
path("concepts/new/", ConceptCreateView, name="concept-create"),
path("concepts/<int:pk>/", ConceptDetailView, name="concept-detail"),
path("concepts/<int:pk>/upload/", upload_attachment_view, name="concept-upload"),
```

**Concept List** (`/adrs/concepts/`):
- Filterable by status (draft, under_review, ready_for_adr, promoted, parked)
- Shows title, author, status, created date, attachment count
- "New Concept" button (prominent)

**Concept Detail** (`/adrs/concepts/<id>/`):
- Edit title, description, motivation, tags (while draft/under_review)
- Upload/remove attachments
- Status transitions: draft → under_review → ready_for_adr
- Park / Reject with reason
- If promoted: link to the resulting ADR

**No "Promote" button in dev-hub**: Promotion happens via Cascade in the IDE.
The dev-hub only marks concepts as `ready_for_adr`. This enforces the SSOT
principle — ADRs are always created in GitHub first.

## Consequences

### Positive

- **SSOT preserved**: ADRs always originate in GitHub, DB is only a mirror
- **Low barrier**: Ideas captured quickly in browser, no markdown knowledge needed
- **AI-assisted quality**: Cascade writes structured ADRs from freeform concepts
- **Audit trail**: Every ADR traces back to its originating concept
- **File support**: Diagrams, specs, screenshots attached to concepts early
- **Robust numbering**: ADR numbers derived from filesystem, no DB race conditions
- **Review workflow**: Concepts discussed before becoming formal ADRs

### Negative

- Two-tool workflow (browser + IDE) — slightly more friction than single-tool
- Requires Cascade/IDE for ADR creation (no fully self-service web flow)
- File attachments live in dev-hub media storage, not in GitHub

### Mitigations

- Two-tool friction is acceptable: dev-hub for capture, IDE for authoring
  matches natural workflow (quick idea → deep technical writing)
- Attachments: referenced by URL in ADR markdown; important diagrams can
  be copied to `platform/docs/assets/` if needed for long-term preservation

### Risks

- Concepts may accumulate without promotion → mitigate with periodic review
- File uploads need size limits (max 10 MB) and type validation
- Concept model adds complexity to `adr_lifecycle` — monitor for >3 unrelated
  models (monolith guard per ADR-050)

## Implementation Plan

### Phase 1: Models + Admin (MVP)
- Add `Concept` and `ConceptAttachment` models to `adr_lifecycle`
- Register in Django admin for immediate use
- Configure media storage (Docker volume)
- Migration + deploy to devhub.iil.pet

### Phase 2: Concept UI
- Concept list view with status filters
- Concept create form with file upload
- Concept detail view with edit + status transitions
- Link from ADR detail back to originating concept

### Phase 3: Cascade Integration
- Document the Cascade workflow in a Windsurf workflow file
  (`/windsurf/workflows/concept-to-adr.md`)
- Cascade reads concepts via postgres MCP (`postgres` server, devhub DB)
- Cascade scans `platform/docs/adr/` for next ADR number
- Cascade writes + pushes ADR, updates concept status

### Phase 4: Dashboard Integration
- "Recent Concepts" widget on dev-hub dashboard
- Concepts included in unified search
- Concept count in ADR lifecycle statistics

## Alternatives Considered

### A: Fully automated promotion in dev-hub (v1 of this ADR)
A "Promote to ADR" button in dev-hub that creates the ADR directly in the
database. **Rejected** because: violates SSOT principle (GitHub must be
canonical), ADR numbering in DB is fragile, and template-generated ADRs are
lower quality than Cascade-assisted authoring.

### B: Direct ADR creation without Concept stage
Allow creating Draft ADRs directly. **Rejected** because: not every idea
should become an ADR, and the ADR format is too structured for brainstorming.

### C: External tool (Notion, Miro, etc.)
Use an external tool for ideation. **Rejected** because: breaks SSOT, ideas
would live outside the platform ecosystem.

### D: GitHub Issues as concepts
Use GitHub Issues with a "concept" label. **Rejected** because: not
tenant-aware, not integrated with dev-hub lifecycle, no file preview,
no structured promotion workflow.
