# platform-context

Shared platform foundation for all Django projects in the iil.pet ecosystem.

## What it provides

- **Request Context** — Thread-safe context propagation (tenant_id, user_id, request_id)
- **Multi-Tenancy Middleware** — Subdomain-based tenant resolution + Postgres RLS
- **Audit Event Logging** — Structured audit trail (model-agnostic)
- **Outbox Pattern** — Reliable event publishing within transactions
- **Exception Hierarchy** — Structured platform exceptions
- **Template Context Processors** — Tenant/permission info in Django templates

## Installation

```bash
pip install -e packages/platform-context
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    "platform_context",
]
```

## Usage

```python
from platform_context import get_context, set_tenant, set_user_id
from platform_context.middleware import SubdomainTenantMiddleware
from platform_context.audit import emit_audit_event
from platform_context.exceptions import TenantNotFoundError
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `TENANT_BASE_DOMAIN` | `"localhost"` | Base domain for subdomain resolution |
| `TENANT_MODEL` | `"tenancy.Organization"` | Dotted path to tenant model |
| `TENANT_SLUG_FIELD` | `"slug"` | Field name for slug lookup |
| `TENANT_ID_FIELD` | `"tenant_id"` | Field name for tenant_id |
| `TENANT_ALLOW_LOCALHOST` | `False` | Allow admin access without tenant (dev) |
| `PLATFORM_AUDIT_MODEL` | `None` | Dotted path to AuditEvent model |
| `PLATFORM_OUTBOX_MODEL` | `None` | Dotted path to OutboxMessage model |

## Relation to bfagent-core

`platform-context` is the framework-agnostic foundation extracted from
`bfagent-core` (see ADR-028). `bfagent-core` now depends on
`platform-context` and re-exports its public API for backward compatibility.

New projects should depend on `platform-context` directly.
