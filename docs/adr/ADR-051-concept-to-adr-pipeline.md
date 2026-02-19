---
id: ADR-051
title: "Concept-to-ADR Pipeline — Idea Capture & Promotion Workflow"
status: draft
date: 2026-02-19
author: Achim Dehnert
owner: Achim Dehnert
scope: dev-hub
tags: [dev-hub, adr-lifecycle, workflow, concept, governance]
related: [ADR-050, ADR-015]
last_verified: 2026-02-19
---

# ADR-051: Concept-to-ADR Pipeline — Idea Capture & Promotion Workflow

## Context

The platform uses Architecture Decision Records (ADRs) to document significant
technical decisions. Currently, ADRs are created as markdown files in the
`platform` repository and imported into dev-hub for lifecycle management.

**Problem**: There is no structured path from "I have an idea" to "This is a
formal ADR". Ideas get lost in chat conversations, Windsurf sessions, or
informal discussions. By the time someone writes an ADR, context and rationale
may have been forgotten or diluted.

**Current gap**:
- No way to capture early-stage ideas before they are mature enough for an ADR
- No file/document upload capability for supporting materials (diagrams, specs)
- No review workflow for concepts before they become formal ADRs
- ADRs can only be imported from existing markdown files, not created in-app

## Decision

Introduce a **two-stage pipeline** in the dev-hub `adr_lifecycle` app:

### Stage 1: Concept

A new `Concept` model captures early-stage ideas with minimal structure:

```python
class Concept(TenantAwareModel):
    title = CharField(max_length=300)
    description = TextField(help_text="Freeform idea description")
    motivation = TextField(blank=True, help_text="Why is this needed?")
    author = ForeignKey(User, on_delete=SET_NULL, null=True)
    status = CharField(choices=[
        ("draft", "Draft"),
        ("under_review", "Under Review"),
        ("promoted", "Promoted to ADR"),
        ("parked", "Parked"),
        ("rejected", "Rejected"),
    ], default="draft")
    promoted_to_adr = ForeignKey("ADR", null=True, blank=True, on_delete=SET_NULL)
    tags = JSONField(default=list, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Attachments** are stored via a separate model:

```python
class ConceptAttachment(TenantAwareModel):
    concept = ForeignKey(Concept, related_name="attachments", on_delete=CASCADE)
    file = FileField(upload_to="concepts/%Y/%m/")
    filename = CharField(max_length=255)
    description = CharField(max_length=500, blank=True)
    uploaded_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    uploaded_at = DateTimeField(auto_now_add=True)
```

### Stage 2: Promotion to ADR

A service function `promote_concept_to_adr()` creates a Draft ADR from a
Concept:

```python
def promote_concept_to_adr(
    concept: Concept,
    actor: User,
) -> ADR:
    """Promote a Concept to a Draft ADR with pre-filled template."""
    next_id = _get_next_adr_id(concept.tenant_id)
    adr = ADR.objects.create(
        tenant_id=concept.tenant_id,
        adr_id=f"ADR-{next_id:03d}",
        title=concept.title,
        status="draft",
        author=actor.get_full_name() or actor.username,
        content_markdown=_render_adr_template(concept),
        tags=concept.tags,
    )
    concept.status = "promoted"
    concept.promoted_to_adr = adr
    concept.save()
    emit_audit_event(
        tenant_id=concept.tenant_id,
        category="adr_lifecycle",
        action="concept_promoted",
        entity_type="Concept",
        entity_id=concept.pk,
        payload={"adr_id": adr.adr_id},
    )
    return adr
```

The generated ADR markdown follows the standard template:

```markdown
---
id: ADR-{NNN}
title: "{concept.title}"
status: draft
date: {today}
author: {actor}
---

# ADR-{NNN}: {concept.title}

## Context

{concept.description}

## Motivation

{concept.motivation}

## Decision

[To be defined]

## Consequences

[To be defined]

## Attachments

- [List of linked concept attachments]
```

### UI Workflow

1. **Dashboard** → "New Concept" button (prominent, low-barrier)
2. **Create Concept** form: title, description, motivation, tags, file uploads
3. **Concept List** view with status filters (like ADR list)
4. **Concept Detail** view with:
   - Edit capability (while in draft/under_review)
   - Comment thread for review discussion
   - "Promote to ADR" button (creates Draft ADR)
   - "Park" / "Reject" actions with reason
5. **ADR Detail** shows backlink to originating Concept (if any)

### URL Structure

```python
# In adr_lifecycle/urls.py
path("concepts/", ConceptListView, name="concept-list"),
path("concepts/new/", ConceptCreateView, name="concept-create"),
path("concepts/<int:pk>/", ConceptDetailView, name="concept-detail"),
path("concepts/<int:pk>/promote/", promote_to_adr_view, name="concept-promote"),
path("concepts/<int:pk>/upload/", upload_attachment_view, name="concept-upload"),
```

## Consequences

### Positive

- **Low barrier to entry**: Ideas can be captured quickly without ADR formalism
- **Audit trail**: Every ADR can trace back to its originating concept
- **File support**: Diagrams, specs, screenshots can be attached early
- **Review workflow**: Concepts can be discussed before becoming formal ADRs
- **Nothing gets lost**: Parked concepts remain searchable for future reference

### Negative

- Additional model complexity in `adr_lifecycle` app
- File storage needs to be configured (media volume in Docker)
- Monolith guard: `adr_lifecycle` app grows — monitor for >3 unrelated models

### Risks

- Concepts may accumulate without promotion → need periodic review/cleanup
- File uploads need size limits and type validation

## Implementation Plan

### Phase 1: Models + Admin (MVP)
- Add `Concept` and `ConceptAttachment` models
- Register in Django admin for immediate use
- Migration + deploy

### Phase 2: Views + Templates
- Concept list, detail, create views
- File upload handling
- "Promote to ADR" service + view

### Phase 3: Integration
- Dashboard widget showing recent concepts
- Search integration (concepts in unified search)
- Backlink from ADR detail to originating concept

## Alternatives Considered

### A: Direct ADR creation with upload
Skip the Concept stage, allow creating Draft ADRs directly in the UI with
file uploads. **Rejected** because: not every idea should become an ADR, and
the ADR format is too structured for early-stage brainstorming.

### B: External tool (Notion, Miro, etc.)
Use an external tool for ideation. **Rejected** because: breaks the
single-source-of-truth principle — ideas would live outside the platform.

### C: GitHub Issues as concepts
Use GitHub Issues with a "concept" label. **Rejected** because: not
tenant-aware, not integrated with dev-hub lifecycle, no file preview.
