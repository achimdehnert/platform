---
id: ADR-138
title: "ADR Implementation Tracking Standard — Lifecycle, Frontmatter Fields, and Verification"
status: accepted
date: 2026-03-11
author: Achim Dehnert
owner: Achim Dehnert
decision-makers: [Achim Dehnert]
consulted: []
informed: [all platform teams]
scope: all ADRs in platform/docs/adr/
tags: [governance, adr, implementation, tracking, lifecycle]
related: [ADR-015, ADR-046, ADR-051, ADR-077]
supersedes: []
amends: []
last_verified: 2026-03-11
implementation_status: implemented
implementation_evidence:
  - "docs/adr/ADR-138-implementation-tracking-standard.md: this ADR"
  - "docs/adr/INDEX.md: implementation_status column added"
---

# ADR-138: ADR Implementation Tracking Standard

| Field | Value |
|-------|-------|
| Status | **Accepted** |
| Date | 2026-03-11 |
| Author | Achim Dehnert |
| Scope | All ADRs in `platform/docs/adr/` |

---

## 1. Context and Problem Statement

### 1.1 Problem

ADR status `Accepted` means "architecture decision approved" — it says **nothing** about whether the decision has been implemented in code. This creates real confusion:

| Symptom | Example |
|---------|---------|
| ADR marked Accepted but no code exists | ADR-096 (authoringfw) is Accepted but `authoringfw` package has no domain sub-modules yet |
| ADR marked Accepted and fully implemented but indistinguishable from above | ADR-097 (aifw 0.6.0) is Accepted and fully implemented — same status as ADR-096 |
| Manual Hygiene-Backlog in INDEX.md | Free-text notes like "aifw 0.6.0 bereits implementiert" — not structured, not queryable |
| No verification trail | No record of when implementation was verified or by whom |

### 1.2 Root Cause

The MADR 4.0 standard defines `status` as a decision lifecycle field (`proposed → accepted → deprecated → superseded`). It has no concept of **implementation lifecycle**. Our ADRs conflate "decision approved" with "code shipped".

---

## 2. Decision

### 2.1 New Frontmatter Fields

Every ADR with status `accepted` MUST include these fields in its YAML frontmatter:

```yaml
# Required for all Accepted ADRs:
implementation_status: implemented   # none | partial | implemented | verified
# Optional but recommended:
implementation_evidence:             # list of file:function or URL references
  - "aifw/src/aifw/service.py: _lookup_cascade()"
  - "aifw/src/aifw/migrations/0005_quality_level_routing.py"
```

### 2.2 Implementation Status Values

| Value | Meaning | When to use |
|-------|---------|-------------|
| `none` | Decision accepted, no code yet | ADR just approved, implementation not started |
| `partial` | Some components implemented | Multi-phase ADR with only Phase 1 done |
| `implemented` | All acceptance criteria met | Code exists, tests pass, but not independently verified |
| `verified` | Independently verified in production | Implementation confirmed working in production |

### 2.3 Lifecycle

```
Proposed → Accepted (implementation_status: none)
                ↓
         partial (Phase 1 done)
                ↓
         implemented (all phases done, tests green)
                ↓
         verified (confirmed in production)
```

### 2.4 `implementation_evidence` Format

Evidence entries follow one of these patterns:

```yaml
implementation_evidence:
  # Code reference: repo/path: function_or_class
  - "aifw/src/aifw/service.py: _lookup_cascade()"
  # Migration reference
  - "aifw/src/aifw/migrations/0005_quality_level_routing.py"
  # URL reference (deployed feature)
  - "https://devhub.iil.pet/releases/"
  # Test reference
  - "aifw/tests/test_lookup_cascade.py: 9 test cases"
  # Config/infra reference
  - "all 29 repos: catalog-info.yaml present"
```

### 2.5 ADRs That Do NOT Need Implementation Tracking

| ADR Type | Reason |
|----------|--------|
| `status: deprecated` | No longer active |
| `status: superseded` | Replaced by another ADR |
| `status: proposed` | Not yet accepted |
| Governance/process ADRs | Self-implementing (the ADR IS the implementation) |

### 2.6 INDEX.md Column

The ADR INDEX table gets a new column `Impl` showing implementation status as emoji:

| Emoji | Meaning |
|-------|---------|
| — | Not applicable (deprecated/superseded/governance) |
| ⬜ | `none` — not started |
| 🔶 | `partial` — in progress |
| ✅ | `implemented` |
| ✅✅ | `verified` in production |

---

## 3. Consequences

### 3.1 Positive

- **Single glance**: INDEX.md shows which decisions are actually implemented
- **Grep-able**: `grep "implementation_status: none" docs/adr/*.md` finds all unimplemented ADRs
- **Evidence trail**: `implementation_evidence` links decision to code — reviewable
- **No new tooling**: Plain YAML frontmatter, works with existing toolchain
- **dev-hub integration**: `devhub.iil.pet/adrs/` can parse frontmatter and show dashboard

### 3.2 Negative

- **Manual maintenance**: implementation_status must be updated by the implementer
- **One-time backfill**: All existing Accepted ADRs need the new fields added

### 3.3 Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Forgotten updates | `/adr-review` workflow checks for missing `implementation_status` on Accepted ADRs |
| Stale evidence | `last_verified` field already exists — should be updated when implementation_status changes |

---

## 4. References

- [ADR-015: Platform Governance System](ADR-015-platform-governance-system.md) — governance framework
- [ADR-046: Documentation Governance](ADR-046-docs-hygiene.md) — documentation standards
- [ADR-051: Concept-to-ADR Pipeline](ADR-051-concept-to-adr-pipeline.md) — ADR creation process
- [MADR 4.0](https://adr.github.io/madr/) — base template (extended by this ADR)
