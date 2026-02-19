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

#### Data Model

Module-level status choices with explicit state machine (following
`ADRStatus` / `VALID_TRANSITIONS` pattern in `adr_lifecycle`):

```python
class ConceptStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    UNDER_REVIEW = "under_review", "Under Review"
    READY_FOR_ADR = "ready_for_adr", "Ready for ADR"
    PROMOTED = "promoted", "Promoted to ADR"
    PARKED = "parked", "Parked"
    REJECTED = "rejected", "Rejected"


CONCEPT_TRANSITIONS: dict[str, list[str]] = {
    ConceptStatus.DRAFT: [
        ConceptStatus.UNDER_REVIEW,
        ConceptStatus.PARKED,
        ConceptStatus.REJECTED,
    ],
    ConceptStatus.UNDER_REVIEW: [
        ConceptStatus.READY_FOR_ADR,
        ConceptStatus.DRAFT,
        ConceptStatus.PARKED,
        ConceptStatus.REJECTED,
    ],
    ConceptStatus.READY_FOR_ADR: [
        ConceptStatus.PROMOTED,
        ConceptStatus.UNDER_REVIEW,
    ],
    ConceptStatus.PROMOTED: [],   # terminal
    ConceptStatus.PARKED: [
        ConceptStatus.DRAFT,
    ],
    ConceptStatus.REJECTED: [],   # terminal
}
```

The `Concept` model captures early-stage ideas with minimal structure:

```python
class Concept(TenantAwareModel):
    """Early-stage idea that may be promoted to a formal ADR."""

    title = models.CharField(max_length=300)
    description = models.TextField(
        help_text="Freeform idea description.",
    )
    motivation = models.TextField(
        blank=True,
        help_text="Why is this needed?",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="concepts_created",
    )
    status = models.CharField(
        max_length=20,
        choices=ConceptStatus.choices,
        default=ConceptStatus.DRAFT,
        db_index=True,
    )
    promoted_to_adr = models.ForeignKey(
        "ADR",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="originating_concepts",
        help_text="Linked after ADR import into DB.",
    )
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "title"],
                name="uq_concept_tenant_title",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[s.value for s in ConceptStatus],
                ),
                name="concept_status_chk",
            ),
        ]
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_concept_tenant_status",
            ),
            models.Index(
                fields=["tenant_id", "-created_at"],
                name="idx_concept_tenant_created",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def allowed_transitions(self) -> list[str]:
        """Status values this Concept can transition to."""
        return CONCEPT_TRANSITIONS.get(self.status, [])

    @property
    def is_promotable(self) -> bool:
        return self.status == ConceptStatus.READY_FOR_ADR

    @property
    def status_color(self) -> str:
        """Tailwind color class for status badge."""
        colors = {
            ConceptStatus.DRAFT: "gray",
            ConceptStatus.UNDER_REVIEW: "yellow",
            ConceptStatus.READY_FOR_ADR: "blue",
            ConceptStatus.PROMOTED: "green",
            ConceptStatus.PARKED: "orange",
            ConceptStatus.REJECTED: "red",
        }
        return colors.get(self.status, "gray")
```

File attachments for supporting materials:

```python
def concept_upload_path(instance: ConceptAttachment, filename: str) -> str:
    """Tenant-isolated upload path."""
    return f"concepts/{instance.tenant_id}/{filename}"


class ConceptAttachment(TenantAwareModel):
    """File attached to a Concept (diagrams, specs, screenshots)."""

    concept = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to=concept_upload_path)
    original_filename = models.CharField(
        max_length=255,
        help_text="Original upload filename for display.",
    )
    description = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="concept_attachments_created",
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.original_filename} on {self.concept.title}"
```

**Design notes**:

- `promoted_to_adr` is a **nullable ForeignKey** to `ADR`, not a string.
  It is `null` while the concept is pre-promotion. After Cascade creates
  the ADR in GitHub and imports it into the DB, the FK is linked via the
  `link_concept_to_adr()` service function.
- `original_filename` preserves the upload name independently of the
  storage backend path (same pattern as pptx-hub `Presentation`).
- `created_by` is consistent across both models (not `author` / `uploaded_by`).
- Upload path includes `tenant_id` for filesystem-level tenant isolation.
- `created_at` / `updated_at` are inherited from `TenantAwareModel`.

#### Service Layer

All business logic lives in `adr_lifecycle/services.py` (not in views):

```python
def create_concept(
    *,
    tenant_id: UUID,
    title: str,
    description: str,
    motivation: str = "",
    tags: list[str] | None = None,
    created_by: User | None = None,
) -> Concept:
    """Create a new Concept and emit audit event."""
    concept = Concept.objects.create(
        tenant_id=tenant_id,
        title=title,
        description=description,
        motivation=motivation,
        tags=tags or [],
        created_by=created_by,
        status=ConceptStatus.DRAFT,
    )
    emit_audit_event(
        tenant_id=tenant_id,
        category="adr_lifecycle",
        action="concept_created",
        entity_type="Concept",
        entity_id=concept.pk,
        payload={"title": title},
    )
    return concept


def transition_concept_status(
    *,
    concept: Concept,
    to_status: str,
    actor: User | None = None,
    reason: str = "",
) -> Concept:
    """Transition Concept status with validation against state machine."""
    allowed = CONCEPT_TRANSITIONS.get(concept.status, [])
    if to_status not in allowed:
        raise ValueError(
            f"Cannot transition from {concept.status} to {to_status}. "
            f"Allowed: {allowed}"
        )
    old_status = concept.status
    concept.status = to_status
    concept.save(update_fields=["status", "updated_at"])
    emit_audit_event(
        tenant_id=concept.tenant_id,
        category="adr_lifecycle",
        action="concept_status_changed",
        entity_type="Concept",
        entity_id=concept.pk,
        payload={
            "from_status": old_status,
            "to_status": to_status,
            "reason": reason,
        },
    )
    return concept


def link_concept_to_adr(
    *,
    concept: Concept,
    adr: ADR,
) -> Concept:
    """Link a promoted Concept to its resulting ADR after import."""
    concept.promoted_to_adr = adr
    concept.status = ConceptStatus.PROMOTED
    concept.save(update_fields=["promoted_to_adr", "status", "updated_at"])
    emit_audit_event(
        tenant_id=concept.tenant_id,
        category="adr_lifecycle",
        action="concept_promoted",
        entity_type="Concept",
        entity_id=concept.pk,
        payload={"adr_id": adr.adr_id},
    )
    return concept
```

### Phase B: ADR Creation (IDE + Cascade)

When a concept is marked `ready_for_adr`, the user switches to their IDE and
tells Cascade:

> "Concept #42 in devhub is ready for an ADR."

Cascade then:

1. **Reads the Concept** from the dev-hub database (via postgres MCP)
2. **Determines next ADR number** by scanning `platform/docs/adr/` on GitHub:
   - Parse all `ADR-NNN-*.md` filenames
   - Filter to standard range (001–399)
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
5. **Imports the new ADR** into dev-hub DB (same as existing import flow)
6. **Links the Concept** via `link_concept_to_adr()` service function

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
│  12. Cascade links concept → ADR via service fn     │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  Result                                             │
│                                                     │
│  • GitHub: ADR-052-<slug>.md exists (SSOT)          │
│  • devhub: ADR-052 visible in /adrs/ (draft)        │
│  • devhub: Concept #42 status=promoted, FK→ADR-052  │
│  • Audit trail: concept → ADR link preserved        │
└─────────────────────────────────────────────────────┘
```

### UI: Concept Views in dev-hub

```python
# In adr_lifecycle/urls.py
path("concepts/", ConceptListView.as_view(), name="concept-list"),
path("concepts/new/", ConceptCreateView.as_view(), name="concept-create"),
path("concepts/<int:pk>/", ConceptDetailView.as_view(), name="concept-detail"),
path("concepts/<int:pk>/transition/", concept_transition_view, name="concept-transition"),
path("concepts/<int:pk>/upload/", concept_upload_view, name="concept-upload"),
```

**Concept List** (`/adrs/concepts/`):
- Filterable by status (draft, under_review, ready_for_adr, promoted, parked)
- Shows title, created_by, status badge, created date, attachment count
- "New Concept" button (prominent)

**Concept Detail** (`/adrs/concepts/<id>/`):
- Edit title, description, motivation, tags (while draft/under_review)
- Upload/remove attachments
- Status transitions via `transition_concept_status()` service
- Park / Reject with reason
- If promoted: link to the resulting ADR via `promoted_to_adr` FK

**No "Promote" button in dev-hub**: Promotion happens via Cascade in the IDE.
The dev-hub only marks concepts as `ready_for_adr`. This enforces the SSOT
principle — ADRs are always created in GitHub first.

## Consequences

### Positive

- **SSOT preserved**: ADRs always originate in GitHub, DB is only a mirror
- **Strictly normalized**: FK to ADR (not string ref), TextChoices, constraints
- **State machine**: Explicit `CONCEPT_TRANSITIONS` with validation in service
- **Service layer**: All mutations via `services.py` with audit events
- **Low barrier**: Ideas captured quickly in browser, no markdown knowledge needed
- **AI-assisted quality**: Cascade writes structured ADRs from freeform concepts
- **Audit trail**: Every ADR traces back via `originating_concepts` reverse FK
- **File support**: Tenant-isolated uploads with original filename preserved
- **Robust numbering**: ADR numbers derived from filesystem, no DB race conditions

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
- `adr_lifecycle` app grows to 5 models (ADR, ADRStatusTransition, ADRComment,
  Concept, ConceptAttachment) — acceptable since all are ADR-pipeline related,
  but monitor: split if unrelated models appear (monolith guard per ADR-050)

## Implementation Plan

### Phase 1: Models + Admin (MVP)
- Add `ConceptStatus`, `CONCEPT_TRANSITIONS`, `Concept`, `ConceptAttachment`
- Add service functions: `create_concept()`, `transition_concept_status()`,
  `link_concept_to_adr()`
- Register in Django admin for immediate use
- Configure media storage (Docker volume mount for `/app/media/`)
- Migration + deploy to devhub.iil.pet

### Phase 2: Concept UI
- Concept list view with status filters
- Concept create form with file upload (HTMX for dynamic attachment list)
- Concept detail view with edit + status transitions via service layer
- Link from ADR detail back to originating concept

### Phase 3: Cascade Integration
- Document the Cascade workflow in a Windsurf workflow file
  (`.windsurf/workflows/concept-to-adr.md`)
- Cascade reads concepts via postgres MCP (`postgres` server, devhub DB)
- Cascade scans `platform/docs/adr/` for next ADR number
- Cascade writes + pushes ADR, updates concept via `link_concept_to_adr()`

### Phase 4: Dashboard Integration
- "Recent Concepts" widget on dev-hub dashboard
- Concepts included in unified search
- Concept count in ADR lifecycle statistics

## Alternatives Considered

### A: Fully automated promotion in dev-hub (v1 of this ADR)
A "Promote to ADR" button in dev-hub that creates the ADR directly in the
database with `promoted_to_adr_id = CharField`. **Rejected** because: violates
SSOT principle (GitHub must be canonical), string reference violates strict
normalization, ADR numbering in DB is fragile, and template-generated ADRs are
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

## Review Changelog

- **v1** (2026-02-19): Initial draft with in-DB promotion and string reference.
  Rejected after review: SSOT violation, no state machine, inline choices.
- **v2** (2026-02-19): Split into two-phase pipeline (devhub + Cascade).
  Still had: CharField for ADR ref, inline tuples, missing constraints.
- **v3** (2026-02-19): Full platform compliance. Fixed: FK normalization,
  TextChoices, UniqueConstraint, CONCEPT_TRANSITIONS state machine,
  related_name on all FKs, consistent `created_by` naming, tenant-isolated
  upload path, DB indexes, explicit service layer with audit events.
