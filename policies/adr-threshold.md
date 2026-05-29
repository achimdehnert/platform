# Policy: ADR Threshold

**Trigger words:** ADR, architecture decision, adr-record, adr nötig

## Rule

Do **not** propose writing an ADR for work that is purely an *addition*
following an existing pattern. ADRs are reserved for genuine architecture
decisions.

## ADR is required when *any* of these is true

- New external dependency or service boundary (new DB, new API, new MCP, new SaaS)
- Reverses or replaces an existing architectural decision
- Cross-cutting impact across multiple apps/teams/repos
- Non-trivial trade-off worth recording for a future challenger
- Anything that touches data sovereignty, security perimeter, or licensing

## ADR is NOT required when

- A new app/feature **follows an existing pattern** (e.g. "another Platform
  Agent in dev-hub like Drift Detector / TechDocs")
- Reversible by removing one app or one Celery task
- Local to one repo with no public surface
- Dependency bump within the same major version
- Code-style or refactor work

For these → **CHANGELOG entry + PR description** is enough.

## Where ADRs live

`~/github/platform/docs/adr/ADR-NNN-*.md`. Get next number:

```bash
ls ~/github/platform/docs/adr/ | sort | tail -1
```

## Changelog

- 2026-05-11: Initial. Promoted after user feedback ("Ergänzung keine
  Architektur-Entscheidung") on repo_health agent.
