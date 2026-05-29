# Policy: Where do Platform Agents live?

**Trigger words:** platform agent, wo soll, which hub, welcher hub, where
should this live, host für, agent, drift, scribe, guardian

## Rule

Cross-cutting agents that scan, monitor, or report on the **platform itself**
(not a business domain) live in **`dev-hub/apps/<agent_name>/`**.

## Examples

| Agent | Lives in | Why dev-hub |
|---|---|---|
| `agents_dashboard` | dev-hub | exists already, root of "Platform Agents" concept |
| `adr_lifecycle` (ADR Scribe + Drift) | dev-hub | platform-wide ADR state |
| `techdocs` | dev-hub | doc sync from 10 repos |
| `health` | dev-hub | endpoint polling across hubs |
| `repo_health` *(2026-05-11, new)* | dev-hub | git status across all repos |

## Anti-pattern

> "risk-hub already has aifw installed → host repo-health there"

Wrong. Domain hubs (risk-hub for ARBSCHUTZ, weltenhub for storytelling,
travel-beat for trips) host **business logic only**. Cross-cutting
platform-aware code is in dev-hub or `platform` package.

## Where dev-hub provides

- `django-celery-beat` (scheduling) already configured
- `aifw` available for LLM routing (add to deps + INSTALLED_APPS once)
- `techdocs.DocSite/DocPage` available for report rendering
- `apps/core` with TenantAwareModel, audit, outbox
- Postgres + Redis infra in prod (devhub.iil.pet)

## Decision flow

```
New cross-cutting feature?
├── About the platform/codebase itself? → dev-hub
├── About a business domain (Arbeitsschutz, Reisen, …)? → domain hub
└── Shared library / convention? → platform package
```

## Changelog

- 2026-05-11: Initial. Promoted after user feedback ("wieso nicht dev-hub —
  das wäre eine logische Basis") on repo_health agent host choice.
