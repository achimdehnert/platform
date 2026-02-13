# mcp-governance

MCP Tool Governance — Specification Standard, Service Discovery & Error Contract.

## Overview

Provides the platform-wide standard for MCP tool governance per [ADR-010](../../docs/adr/ADR-010-mcp-tool-governance.md):

- **`mcp_governance.spec`** — Pydantic v2 models (`ToolSpec`, `ParamSpec`, `ReturnSpec`) + enums
- **`mcp_governance.response`** — Structured error contract (`ok()`, `fail()`, `from_ssh()`)
- **`mcp_governance.spec.validator`** — Schema validation and compliance checking

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

### Define a ToolSpec

```python
from mcp_governance.spec import ToolSpec, ToolCategory, ParamSpec

spec = ToolSpec(
    name="docker_manage",
    server="deployment_mcp",
    description="Manage Docker containers and compose stacks on remote servers via SSH",
    category=ToolCategory.DEVOPS_DEPLOY,
    tags=["docker", "compose"],
)
```

### Structured Responses

```python
from mcp_governance.response import ok, fail

# Success
return ok({"containers": [...]}, suggestion="Use compose_ps for overview")

# Failure
return fail("Container not found", code="NOT_FOUND", retryable=False)
```

### Validate Specs

```python
from mcp_governance.spec.validator import validate_spec

result = validate_spec(spec)
if not result.is_valid:
    print(result.errors)
```

## Testing

```bash
PYTHONPATH=. python3.11 -m pytest tests/ -v
```

## Package Structure

```text
mcp_governance/
├── __init__.py
├── response.py          # Shared error contract
└── spec/
    ├── __init__.py
    ├── enums.py         # ToolCategory, TenantMode, SideEffect, ErrorPolicy
    ├── models.py        # ParamSpec, ReturnSpec, ToolSpec
    └── validator.py     # validate_spec(), validate_registry()
```
