---
status: accepted
date: 2026-05-08
decision-makers:
  - Achim Dehnert
depends-on:
  - ADR-083 (Hybrid ADR Governance)
  - ADR-059 (Automated ADR Drift Detection)
related:
  - ADR-065 (Filesystem-first ADR numbering)
  - ADR-071 (Code Quality Tooling)
  - ADR-138 (Implementation Tracking Standard)
repo: platform
consumers:
  - platform
  - dev-hub
  - mcp-hub
domains:
  - governance/adr
  - tooling/mcp
implementation_status: implemented
staleness_months: 6
last_reviewed: 2026-05-09
drift_check_paths:
  - platform/.github/workflows/adr-validate.yml
  - platform/.windsurf/workflows/adr.md
  - platform/.windsurf/workflows/session-start.md
---

# ADR-190: Adopt iil-adrfw as ADR Tooling Framework

| Metadaten | |
|-----------|---|
| **Status** | Accepted |
| **Datum** | 2026-05-08 |
| **Entscheider** | Achim Dehnert |
| **Abhängig von** | ADR-083, ADR-059 |

## Context

The platform manages 157+ ADRs across a growing ecosystem of 25+ Django apps,
14 frameworks, and 3 GitHub organizations. ADR-083 established the governance
structure (platform-central + repo-local), and ADR-059 mandated automated drift
detection. However, neither specified the concrete tooling.

Until now, ADR validation was manual or ad-hoc. There was no schema enforcement
in CI, no staleness tracking, no dependency graph analysis, and no way for
Cascade (the coding agent) to query architecture decisions at runtime. This led
to recurring issues:

- ADRs with invalid frontmatter went undetected for weeks
- Supersession chains broke silently (orphaned `superseded_by` references)
- Coding agents made decisions contradicting existing ADRs because they had no
  way to discover which ADRs apply to a given file path
- Cross-repo validation was impossible — an ADR could claim rules for consumer
  repos without verifying actual compliance

The `iil-adrfw` package (v0.3.1) was developed to address all of these gaps in
a single, deterministic tool — no LLM calls, pure schema validation + graph
analysis + pattern matching.

## Decision

We adopt **iil-adrfw** as the platform's ADR tooling framework. It provides:

1. **CLI** (`iil-adrfw validate|staleness|graph|export|audit|query`) for local
   and CI usage
2. **MCP Server** (11 tools via FastMCP, prefix `mcp2_`) for real-time Cascade
   integration
3. **CI Integration** (`adr-validate.yml`) as a required check on `platform/main`
4. **Schema v3** as the canonical frontmatter specification for all ADRs

All ADR lifecycle operations (creation, validation, auditing, querying) MUST use
iil-adrfw. Manual frontmatter editing is allowed but MUST pass `iil-adrfw validate`
before merge.

## Consequences

### Positive

- 157/157 ADRs schema-valid in CI — invalid frontmatter is blocked at PR time
- Cascade can discover applicable ADRs via `mcp2_adr_impact(file_path=...)` before coding
- Staleness and drift are detected automatically (`mcp2_adr_staleness`)
- New ADR proposals are pre-validated for duplicates and supersession conflicts
- Cross-repo validation prevents ADRs from making claims that contradict actual code
- Deterministic — no LLM dependency, reproducible results

### Negative

- Additional PyPI dependency (`iil-adrfw>=0.3.1`) required in CI
- Schema evolution requires coordinated updates (tool + all 157 ADRs)
- MCP prefix (`mcp2_`) is environment-specific and may shift on Windsurf restart
- Tool maintenance burden falls on a single developer

## Alternatives Considered

| Alternative | Reason for Rejection |
|------------|---------------------|
| **adr-tools (shell-based)** | No schema validation, no MCP integration, no graph analysis. Only handles creation/listing. |
| **Custom GitHub Actions only** | Would cover CI validation but not runtime Cascade integration or staleness tracking. |
| **Manual review** | Doesn't scale to 157+ ADRs. Supersession drift and staleness go undetected. |
| **LLM-based ADR analysis** | Non-deterministic, expensive, slow. Inappropriate for governance where reproducibility is critical. |

## Implementation

| Component | Location | Status |
|-----------|----------|--------|
| PyPI package | `iil-adrfw>=0.4.0` | ✅ published |
| MCP server | `iil-adrfw-mcp` (stdio) | ✅ 12 tools |
| CI workflow | `platform/.github/workflows/adr-validate.yml` | ✅ required check |
| Session-start | Step 0.4.2 (`mcp2_adr_staleness` + `mcp2_adr_audit`) | ✅ integrated |
| Pre-code | Step A0 (`mcp2_adr_impact`) | ✅ integrated |
| PR-review | Step 1.5 (`mcp2_adr_check`) | ✅ integrated |
| ADR creation | Step 1.5 (`mcp2_adr_propose`) | ✅ integrated |

## MCP Tools (12)

| Tool | Purpose |
|------|---------|
| `adr_validate` | Schema v3 frontmatter validation |
| `adr_staleness` | Age + drift + missing reviews |
| `adr_impact` | File path → applicable ADRs |
| `adr_check` | Run ADR rules against code paths |
| `adr_explain` | Audience-tailored rule explanation |
| `adr_query` | Query constitution by question/domain/path |
| `adr_audit` | Constitution-level health audit |
| `adr_propose` | Pre-validate new ADR proposals |
| `adr_diff` | Diff constitution between times or sets |
| `adr_narrate` | Audience-tailored narrative summary |
| `adr_validate_cross_repo` | Validate ADR claims against consumer repos |
| `adr_freshness` | Check ADR content claims against repo state (versions, ports, images) |
