# bfagent-core

Shared core components for the BFAgent Hub ecosystem.

## Features

- **Tenancy**: Multi-tenant support with subdomain resolution and Postgres RLS
- **Request Context**: Thread-safe context propagation (tenant_id, user_id, request_id)
- **Audit**: Audit event logging for compliance
- **Outbox**: Transactional outbox pattern for reliable event publishing

## Installation

```bash
pip install bfagent-core
# or from git
pip install "bfagent-core @ git+https://github.com/achimdehnert/platform.git#subdirectory=packages/bfagent-core"
```

## Usage

### Request Context

```python
from bfagent_core.context import get_context, set_tenant, set_user_id

# Set context (typically in middleware)
set_tenant(tenant_id=uuid, tenant_slug="demo")
set_user_id(user_id)

# Get context anywhere
ctx = get_context()
print(ctx.tenant_id, ctx.user_id, ctx.request_id)
```

### Audit Events

```python
from bfagent_core.audit import emit_audit_event

emit_audit_event(
    tenant_id=tenant_id,
    category="risk.assessment",
    action="created",
    entity_type="risk.Assessment",
    entity_id=assessment.id,
    payload={"title": assessment.title},
)
```

### Outbox Pattern

```python
from bfagent_core.outbox import emit_outbox_event

emit_outbox_event(
    tenant_id=tenant_id,
    topic="risk.assessment.created",
    payload={"assessment_id": str(assessment.id)},
)
```

### Postgres RLS

```python
from bfagent_core.db import set_db_tenant

# Set tenant for RLS (in middleware)
set_db_tenant(tenant_id)
```

## Django Integration

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    "bfagent_core",
]
```

Add middleware:

```python
MIDDLEWARE = [
    ...
    "bfagent_core.middleware.RequestContextMiddleware",
    "bfagent_core.middleware.SubdomainTenantMiddleware",
]
```

## License

MIT
