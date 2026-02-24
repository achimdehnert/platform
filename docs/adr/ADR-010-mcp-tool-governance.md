---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-010: MCP Tool Governance — Specification Standard, Service Discovery & Composition

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-13 |
| **Author** | Achim Dehnert |
| **Reviewers** | Cascade (Review v2, 2026-02-13) |
| **Supersedes** | ADR-015 (Component Registry — dead-code, never deployed) |
| **Related** | ADR-008 (Infrastructure Services), ADR-009 (Deployment Architecture) |
| **Inspired by** | ToolUniverse (Harvard/Zitnik Lab) — architecture patterns only |

---

## 1. Context

### 1.1 Current State

The MCP Hub provides **7 active MCP servers** with ~30+ tools across multiple domains:

| Server | Domain | Status | Tools | Error Format | Spec Governance |
|--------|--------|--------|-------|--------------|-----------------|
| `deployment_mcp` | DevOps | ✅ Production | `cicd_manage`, `docker_manage`, `ssh_manage`, ... | `response.py` envelope | Ad-hoc |
| `llm_mcp` | AI/LLM | ✅ Production | `generate_text`, `chat`, `llm_list` | Flat `{success, content}` | Ad-hoc |
| `illustration_mcp` | Creative | ✅ Production | `generate_image`, `edit_image` | Unknown | Ad-hoc |
| `ifc_mcp` | CAD/BIM | ✅ Production | `ifc_import_file`, `ifc_window_schedule`, ... | `TextContent` (no envelope) | Ad-hoc |
| `orchestrator_mcp` | Platform | ✅ Production | `check_repos`, `run_cmd`, `git_manage` | Flat `{success, error}` | Ad-hoc |
| `travel_mcp` | Travel | ✅ Production | Trip/destination tools | No standard | Ad-hoc |
| `registry_mcp` | Discovery | ❌ Dead code | `search_registry`, `list_mcp_servers` | `TextContent` | ADR-015 (never deployed) |

Additional: `mcp_base` (shared library), `_archive/ui_hub` (archived).

Every server defines its own conventions for tool naming, parameter schemas, error handling, return formats, and documentation. There is no centralized registry, no discovery mechanism, and no way for AI assistants to dynamically find tools.

### 1.2 Pain Points

1. **No Specification Standard**: Each MCP server defines tools in isolation — inconsistent naming, varying error formats, no return schema guarantees
2. **No Service Discovery**: AI assistants (Claude, Cascade) must be statically configured with known tools — adding a new tool requires prompt/config updates everywhere
3. **No Composition**: Multi-tool workflows (e.g., research → generate → feedback) are manually orchestrated by the AI with no structured chaining
4. **Inconsistent Error Handling**: Audit reveals 4+ formats in production:
   - `deployment_mcp`: Structured `{success, data, error: {code, message}, suggestion}` via `response.py`
   - `llm_mcp`: Flat `{success, content, usage, error: string}`
   - `orchestrator_mcp`: Flat `{success, error: string, output}`
   - `ifc_mcp`: `TextContent` with embedded JSON or plain strings — no envelope
   - `travel_mcp`: No standard response format
5. **No Tenant Awareness Metadata**: No way for an AI to know which tools respect multi-tenancy and which operate globally
6. **Documentation Drift**: Tool descriptions in code diverge from Sphinx docs over time
7. **Prior Dead-Code Registry**: `registry_mcp` (ADR-015) was written but never deployed — its `platform.reg_mcp_server` tables were never created. `REGISTRY_DATABASE_URL` not configured. This ADR supersedes that approach.

### 1.3 External Analysis: ToolUniverse Patterns

A comprehensive evaluation of ToolUniverse (Harvard/Zitnik Lab) revealed that while its 600+ biomedical tools have no domain relevance for our platform, three architectural patterns are directly applicable:

| Pattern | ToolUniverse Implementation | Our Gap | Adoptability |
|---------|---------------------------|---------|-------------|
| **AI-Tool Interaction Protocol** | Specification + Interaction + Communication schema | No unified spec | HIGH — adapt to our Django/MCP world |
| **Tool Discovery** | Keyword, Embedding, LLM-based search | Static config only | HIGH — lightweight registry first |
| **Tool Composition** | Sequential, Parallel, Feedback-driven chains | Manual AI orchestration | MEDIUM — build on Prompt Chain pattern |

### 1.4 Requirements

| Requirement | Priority | Notes |
|-------------|----------|-------|
| Unified tool specification schema | CRITICAL | Foundation for everything else |
| Machine-readable tool registry | HIGH | Enables dynamic discovery |
| Discovery endpoint for AI assistants | HIGH | AI can find tools at runtime |
| Consistent error handling contract | HIGH | Predictable for AI consumption |
| Tenant-awareness metadata | HIGH | DSGVO compliance visibility |
| Tool composition patterns | MEDIUM | Build on existing PromptChain |
| Backward compatibility | HIGH | Existing servers must keep working |
| Zero new infrastructure | MEDIUM | Registry as MCP resource, not new service |

---

## 2. Decision

### 2.1 Architecture Choice

**We adopt a Two-Phase MCP Governance Architecture** building incrementally:

1. **Phase 1 — Tool Specification Standard** (`ToolSpec`): Pydantic-based schema for all MCP tools + standardized error contract
2. **Phase 2 — Service Discovery**: Registry MCP server with discovery tools (hybrid JSON + DB-ready)

> **Note**: Composition patterns (tool chains, parallel execution) are deferred to a separate future ADR. The `inputs_from`/`outputs_to` graph metadata in ToolSpec provides AI assistants with composition hints without requiring a runtime engine.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           platform repository                               │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  packages/mcp-governance/                                             │  │
│  │  ├── mcp_governance/                                                  │  │
│  │  │   ├── spec/              # Phase 1: ToolSpec schema                │  │
│  │  │   │   ├── __init__.py                                              │  │
│  │  │   │   ├── models.py      # Pydantic models (ToolSpec, ParamSpec)   │  │
│  │  │   │   ├── enums.py       # ToolCategory, TenantMode, ErrorPolicy   │  │
│  │  │   │   └── validator.py   # Schema validation & compliance check    │  │
│  │  │   ├── response.py        # Shared error contract (from deployment_mcp) │
│  │  │   └── registry/          # Phase 2: Service Discovery              │  │
│  │  │       ├── __init__.py                                              │  │
│  │  │       ├── store.py       # Registry store (JSON file + DB-ready)   │  │
│  │  │       ├── search.py      # Keyword & tag-based discovery           │  │
│  │  │       └── server.py      # MCP server exposing registry            │  │
│  │  ├── pyproject.toml                                                   │  │
│  │  └── tests/                                                           │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  registry/                  # Generated registry data                 │  │
│  │  ├── tools.json             # Complete tool registry (auto-generated) │  │
│  │  └── servers.json           # Server metadata                         │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    imports mcp_governance.spec
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
   ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
   │  llm_mcp    │           │ deploy_mcp  │           │  ifc_mcp    │
   │─────────────│           │─────────────│           │─────────────│
   │ toolspec.py │           │ toolspec.py │           │ toolspec.py │
   │ (declares)  │           │ (declares)  │           │ (declares)  │
   └─────────────┘           └─────────────┘           └─────────────┘
```

### 2.2 Rejected Alternatives

#### Option A: Adopt ToolUniverse Directly

```
❌ Rejected because:
- 95% biomedical tools — no domain fit
- Harvard research project — unclear long-term stability
- Dependency bloat — pulls in bio-specific packages
- GPU requirement for embedding-based discovery
- No multi-tenancy or DSGVO awareness
```

#### Option B: MCP-Only (Rely on MCP Spec Alone)

```
❌ Rejected because:
- MCP spec defines wire protocol, not governance layer
- MCP tools/list returns raw tool schemas — no categorization, tags, tenancy
- No cross-server discovery (each server is independent)
- No platform-specific metadata (tenant mode, DSGVO, domain)
```

#### Option C: External Registry Service (e.g., Consul, etcd)

```
❌ Rejected because:
- Additional infrastructure to maintain (violates ADR-009 principle)
- Overkill for ~30 tools across 7 servers
- Adds operational complexity without proportional benefit
```

#### Option D: Revive existing `registry_mcp` (ADR-015, Postgres-based)

```
❌ Rejected because:
- Dead code: platform.reg_mcp_server tables never created in any database
- Over-engineered: 6+ tables with FK relationships, lkp_choice lookups,
  tsvector indices for ~30 tools (full-text search over 1KB of data)
- Uses raw psycopg2 instead of Django ORM — inconsistent with platform stack
- Couples registry to bfagent_prod database lifecycle
- No migration files, no tests, no deployment configuration

Decision: Archive existing code, build new lightweight registry.
The hybrid approach (JSON primary + optional DB store) provides a
cleaner migration path if tool count grows significantly.
```

---

## 3. Phase 1: Tool Specification Standard

### 3.1 ToolSpec Schema

The `ToolSpec` extends the MCP native tool schema with platform-specific governance metadata. It is **additive** — the MCP protocol itself remains unchanged.

```python
# packages/mcp-governance/mcp_governance/spec/enums.py

from enum import StrEnum


class ToolCategory(StrEnum):
    """Platform-wide tool categories."""

    AI_LLM = "ai.llm"
    AI_IMAGE = "ai.image"
    DATA_QUERY = "data.query"
    DATA_MUTATION = "data.mutation"
    DEVOPS_DEPLOY = "devops.deploy"
    DEVOPS_MONITOR = "devops.monitor"
    SEARCH_WEB = "search.web"
    SEARCH_INTERNAL = "search.internal"
    DOMAIN_TRAVEL = "domain.travel"
    DOMAIN_RISK = "domain.risk"
    DOMAIN_CAD = "domain.cad"
    DOMAIN_WRITING = "domain.writing"
    DOMAIN_TAX = "domain.tax"
    DOCUMENT_MGMT = "document.mgmt"
    UTILITY = "utility"


class TenantMode(StrEnum):
    """How the tool handles multi-tenancy."""

    TENANT_SCOPED = "tenant_scoped"      # Respects RLS, data isolated per tenant
    TENANT_AWARE = "tenant_aware"        # Receives tenant context, may use it
    GLOBAL = "global"                    # No tenant awareness (e.g., web search)


class SideEffect(StrEnum):
    """What side effects the tool produces."""

    NONE = "none"              # Pure read / computation
    DATABASE_WRITE = "db_write"
    EXTERNAL_API = "external_api"
    FILE_SYSTEM = "file_system"
    NOTIFICATION = "notification"
    DEPLOYMENT = "deployment"


class ErrorPolicy(StrEnum):
    """How errors are reported."""

    RESULT_OBJECT = "result_object"   # {"success": false, "error": "..."} — PREFERRED
    MCP_ERROR = "mcp_error"           # MCP protocol-level error
    EXCEPTION = "exception"           # Python exception (legacy, to migrate)
```

```python
# packages/mcp-governance/mcp_governance/spec/models.py

"""
MCP Tool Specification Standard for the BF Agent Platform.

Extends MCP native tool schema with platform governance metadata.
All schemas are Pydantic v2, immutable, JSON-serializable.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Any

from .enums import ToolCategory, TenantMode, SideEffect, ErrorPolicy


class ParamSpec(BaseModel):
    """Extended parameter specification beyond JSON Schema."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Parameter name in snake_case",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Clear description for AI consumption — what it does, valid values, edge cases",
    )
    param_type: str = Field(
        ...,
        description="JSON Schema type: string, integer, number, boolean, array, object",
    )
    required: bool = Field(default=True)
    default: Any = Field(default=None)
    examples: list[Any] = Field(
        default_factory=list,
        description="Concrete examples for AI to understand usage",
    )
    sensitive: bool = Field(
        default=False,
        description="Contains PII or credentials — must not be logged",
    )

    model_config = ConfigDict(frozen=True)


class ReturnSpec(BaseModel):
    """Specification for tool return values."""

    description: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="What the tool returns on success",
    )
    schema_type: str = Field(
        default="object",
        description="JSON Schema type of the return value",
    )
    example: Any = Field(
        default=None,
        description="Example return value for AI consumption",
    )

    model_config = ConfigDict(frozen=True)


class ToolSpec(BaseModel):
    """
    Platform Tool Specification — the core governance schema.

    Extends MCP's native tool definition (name, description, inputSchema)
    with platform-specific metadata for governance, discovery, and composition.

    Design principles:
      - Additive to MCP — does NOT replace or wrap the MCP tool decorator
      - Pydantic v2 with frozen=True — immutable after creation
      - JSON-serializable — can be exported to registry files
      - Aligned with PromptTemplateSpec pattern from creative-services
    """

    # === Identity ===
    schema_version: str = Field(
        default="1.0",
        pattern=r"^\d+\.\d+$",
        description="ToolSpec schema version — for future migration support",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Tool name — MUST match the @mcp.tool() function name exactly",
    )
    server: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="MCP server this tool belongs to (e.g., 'llm_mcp', 'travel_mcp')",
    )
    version: str = Field(
        default="1.0.0",
        pattern=r"^\d+\.\d+\.\d+$",
        description="Semantic version of this tool",
    )

    # === Documentation ===
    description: str = Field(
        ...,
        min_length=20,
        max_length=1000,
        description="AI-optimized description — what it does, when to use it, what to expect",
    )
    long_description: str | None = Field(
        default=None,
        max_length=5000,
        description="Extended documentation for human developers",
    )

    # === Classification ===
    category: ToolCategory = Field(
        ...,
        description="Platform tool category for discovery and grouping",
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Free-form tags for search (e.g., ['llm', 'generation', 'openai'])",
    )
    domain_codes: list[str] = Field(
        default_factory=list,
        description="Which platform domains use this tool (e.g., ['writing', 'travel'])",
    )

    # === Parameters & Returns ===
    parameters: list[ParamSpec] = Field(
        default_factory=list,
        description="Extended parameter specs (supplements MCP inputSchema)",
    )
    returns: ReturnSpec | None = Field(
        default=None,
        description="Return value specification",
    )

    # === Platform Governance ===
    tenant_mode: TenantMode = Field(
        default=TenantMode.GLOBAL,
        description="Multi-tenancy behavior — critical for DSGVO compliance",
    )
    side_effects: list[SideEffect] = Field(
        default_factory=lambda: [SideEffect.NONE],
        description="Side effects this tool produces — for safety classification",
    )
    error_policy: ErrorPolicy = Field(
        default=ErrorPolicy.RESULT_OBJECT,
        description="How errors are reported",
    )
    idempotent: bool = Field(
        default=False,
        description="Can this tool be safely retried without side effects?",
    )
    estimated_duration_ms: int | None = Field(
        default=None,
        ge=0,
        description="Expected execution time in milliseconds",
    )

    # === Composition ===
    inputs_from: list[str] = Field(
        default_factory=list,
        description="Tools whose output can serve as input (for composition graph)",
    )
    outputs_to: list[str] = Field(
        default_factory=list,
        description="Tools that can consume this tool's output",
    )

    # === Status ===
    is_active: bool = Field(
        default=True,
        description="Whether this tool is currently available",
    )
    deprecated: bool = Field(
        default=False,
        description="Marked for removal — AI should prefer alternatives",
    )
    deprecated_by: str | None = Field(
        default=None,
        description="Replacement tool name if deprecated",
    )

    model_config = ConfigDict(frozen=True)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Lowercase, strip, and validate individual tag format."""
        cleaned = []
        for tag in v:
            tag = tag.lower().strip()
            if len(tag) > 50:
                raise ValueError(f"Tag too long (max 50 chars): {tag[:20]}...")
            if not all(c.isalnum() or c in "-_" for c in tag):
                raise ValueError(f"Tag must be alphanumeric/dash/underscore: {tag}")
            cleaned.append(tag)
        return cleaned

    @field_validator("name")
    @classmethod
    def name_no_prefix(cls, v: str) -> str:
        """Tool names should not repeat the server name."""
        # e.g., "llm_mcp_generate_text" is bad — "generate_text" is good
        if v.endswith("_mcp"):
            raise ValueError("Tool name should not include server suffix '_mcp'")
        return v

    def qualified_name(self) -> str:
        """Fully qualified tool name: server.tool (e.g., 'llm_mcp.generate_text')."""
        return f"{self.server}.{self.name}"
```

### 3.2 Declaring ToolSpecs in MCP Servers

Each MCP server declares its tools via a `toolspec.py` file. This is **alongside** the MCP `@tool()` decorators — not replacing them.

```python
# mcp-hub/llm_mcp/toolspec.py

"""
Tool specifications for llm_mcp.

These declarations are the single source of truth for tool metadata.
The MCP @tool() decorators remain unchanged — these specs ADD governance.
"""

from mcp_governance.spec import ToolSpec, ParamSpec, ReturnSpec
from mcp_governance.spec.enums import (
    ToolCategory, TenantMode, SideEffect, ErrorPolicy,
)

TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="generate_text",
        server="llm_mcp",
        version="1.2.0",
        description=(
            "Generate text using an LLM provider. Supports OpenAI, Anthropic, "
            "Groq, and Ollama via the creative-services LLM client. Use for "
            "any text generation task: creative writing, analysis, summarization. "
            "Returns generated text with token usage metadata."
        ),
        category=ToolCategory.AI_LLM,
        tags=["llm", "generation", "text", "openai", "anthropic"],
        domain_codes=["writing", "travel", "risk"],
        parameters=[
            ParamSpec(
                name="prompt",
                description="The input prompt for text generation. Should be clear and specific.",
                param_type="string",
                required=True,
                examples=["Write a travel description for Kyoto in spring"],
            ),
            ParamSpec(
                name="model",
                description="LLM model identifier. Defaults to tier-based selection if omitted.",
                param_type="string",
                required=False,
                default=None,
                examples=["gpt-4o", "claude-sonnet-4-20250514", "llama-3.3-70b"],
            ),
            ParamSpec(
                name="max_tokens",
                description="Maximum tokens in the response. Higher values = longer output, more cost.",
                param_type="integer",
                required=False,
                default=1024,
                examples=[256, 1024, 4096],
            ),
            ParamSpec(
                name="temperature",
                description="Sampling temperature (0.0 = deterministic, 1.0 = creative). Use 0.0-0.3 for factual, 0.7-1.0 for creative.",
                param_type="number",
                required=False,
                default=0.7,
                examples=[0.0, 0.3, 0.7, 1.0],
            ),
        ],
        returns=ReturnSpec(
            description="Generated text with metadata including token counts and model used",
            schema_type="object",
            example={
                "success": True,
                "text": "Kyoto in spring is a canvas of pink...",
                "model": "gpt-4o",
                "tokens_used": 342,
                "cost_usd": 0.0051,
            },
        ),
        tenant_mode=TenantMode.TENANT_AWARE,
        side_effects=[SideEffect.EXTERNAL_API],
        error_policy=ErrorPolicy.RESULT_OBJECT,
        idempotent=True,
        estimated_duration_ms=3000,
        outputs_to=["add_feedback", "generate_itinerary"],
    ),
    ToolSpec(
        name="chat",
        server="llm_mcp",
        version="1.1.0",
        description=(
            "Multi-turn chat conversation with an LLM. Maintains conversation "
            "history within a single call. Use for interactive dialogues, "
            "follow-up questions, or when context from previous messages matters."
        ),
        category=ToolCategory.AI_LLM,
        tags=["llm", "chat", "conversation", "multi-turn"],
        domain_codes=["writing", "travel", "risk", "cad"],
        parameters=[
            ParamSpec(
                name="messages",
                description="List of message objects with 'role' (system/user/assistant) and 'content' fields.",
                param_type="array",
                required=True,
                examples=[[{"role": "user", "content": "Hello"}]],
            ),
        ],
        returns=ReturnSpec(
            description="Assistant response with conversation metadata",
            schema_type="object",
        ),
        tenant_mode=TenantMode.TENANT_AWARE,
        side_effects=[SideEffect.EXTERNAL_API],
        error_policy=ErrorPolicy.RESULT_OBJECT,
        idempotent=True,
        estimated_duration_ms=5000,
    ),
]
```

### 3.3 Schema Validator

A CI-integrated validator ensures all ToolSpecs pass quality gates:

```python
# packages/mcp-governance/mcp_governance/spec/validator.py

"""
ToolSpec compliance validator.

Runs in CI to ensure all declared ToolSpecs meet platform standards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from .models import ToolSpec
from .enums import ErrorPolicy, TenantMode


@dataclass
class ValidationResult:
    """Result of validating a ToolSpec."""

    tool_name: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def validate_toolspec(spec: ToolSpec) -> ValidationResult:
    """
    Validate a ToolSpec against platform governance rules.

    Rules:
      - Description must be AI-optimized (min 20 chars, action-oriented)
      - All parameters must have descriptions ≥ 10 chars
      - Tenant-scoped tools must not have GLOBAL tenant mode
      - Error policy should be RESULT_OBJECT (preferred)
      - At least one tag must be present
      - Examples should be provided for complex parameters
    """
    result = ValidationResult(tool_name=spec.qualified_name())

    # --- Errors (must fix) ---

    if len(spec.tags) == 0:
        result.errors.append("At least one tag is required for discovery")

    if spec.tenant_mode == TenantMode.TENANT_SCOPED:
        has_tenant_param = any(p.name == "tenant_id" for p in spec.parameters)
        if not has_tenant_param:
            result.warnings.append(
                "TENANT_SCOPED tools typically receive tenant_id via RLS, "
                "not as a parameter — verify this is handled in middleware"
            )

    for param in spec.parameters:
        if param.required and param.default is not None:
            result.errors.append(
                f"Parameter '{param.name}': required=True with default is contradictory"
            )

    # --- Warnings (should fix) ---

    if spec.error_policy != ErrorPolicy.RESULT_OBJECT:
        result.warnings.append(
            f"Error policy '{spec.error_policy}' is not preferred — "
            f"migrate to RESULT_OBJECT for consistent AI consumption"
        )

    if not spec.returns:
        result.warnings.append("No return spec defined — AI cannot predict output shape")

    for param in spec.parameters:
        if len(param.examples) == 0:
            result.warnings.append(
                f"Parameter '{param.name}' has no examples — "
                f"examples improve AI tool selection accuracy"
            )

    if spec.estimated_duration_ms is None:
        result.warnings.append(
            "No estimated_duration_ms — AI cannot manage user expectations"
        )

    if spec.deprecated and not spec.deprecated_by:
        result.warnings.append(
            "Tool is deprecated but no replacement specified"
        )

    return result


def validate_registry(specs: list[ToolSpec]) -> list[ValidationResult]:
    """Validate all specs and check cross-tool consistency."""
    results = [validate_toolspec(spec) for spec in specs]

    # Cross-tool checks
    names = [s.qualified_name() for s in specs]
    seen = set()
    for name in names:
        if name in seen:
            results.append(
                ValidationResult(
                    tool_name=name,
                    errors=[f"Duplicate qualified name: {name}"],
                )
            )
        seen.add(name)

    # Verify composition references are valid
    all_tool_names = {s.name for s in specs}
    for spec in specs:
        for ref in spec.inputs_from + spec.outputs_to:
            if ref not in all_tool_names:
                for r in results:
                    if r.tool_name == spec.qualified_name():
                        r.warnings.append(
                            f"Composition reference '{ref}' not found in registry"
                        )

    return results
```

### 3.4 Error Handling Contract

#### 3.4.1 Current State (Audit 2026-02-13)

| Server | Current Format | Migration Effort |
|--------|---------------|-----------------|
| `deployment_mcp` | ✅ `response.py` envelope `{success, data, error: {code, message}, suggestion}` | None (already compliant) |
| `llm_mcp` | ⚠️ Flat `{success, content, error: string}` | Low — wrap in `data`, structure `error` |
| `orchestrator_mcp` | ⚠️ Flat `{success, error: string, output}` | Low — same pattern |
| `ifc_mcp` | ❌ Raw `TextContent` with embedded JSON | Medium — add envelope layer |
| `travel_mcp` | ❌ No standard | Medium — implement from scratch |

#### 3.4.2 Target Envelope (aligned with `deployment_mcp/response.py`)

The target format is based on the **existing, tested** `deployment_mcp/response.py` pattern (the only server with a structured response contract today), extended with `retryable`:

```python
# Standard success response
{
    "success": True,
    "data": { ... },              # Tool-specific result payload
    "error": None,                # Null on success
    "suggestion": None,           # Optional: AI next-step hint
}

# Standard error response
{
    "success": False,
    "data": None,                 # May contain partial results
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",   # Machine-readable error code
        "message": "Rate limit exceeded, retry after 60s",  # Human-readable
    },
    "suggestion": "Wait 60 seconds and retry with a smaller prompt.",
    "retryable": True,            # Optional: Can the AI safely retry?
}
```

#### 3.4.3 Migration Rules

- **New servers** MUST use the target envelope from day one (via `mcp_governance.response`)
- **Existing servers** migrate gradually (one PR per server)
- `llm_mcp` backward compatibility: `content` stays as alias inside `data` for one release cycle
- Tools MUST NOT raise exceptions through the MCP protocol
- The `mcp_governance.response` module provides `ok()`, `fail()`, `from_ssh()` helpers (extracted from `deployment_mcp/response.py`)

#### 3.4.4 Invariant

> Every MCP tool response MUST contain `"success": bool` at the top level. On `success: false`, `error` MUST be present (string or `{code, message}` object). This is the **minimum contract** — servers in migration may not yet have the full envelope.

---

## 4. Phase 2: Service Discovery

### 4.1 Registry Architecture

The registry is a **generated JSON file** + **MCP server** — no new infrastructure.

> **Hybrid DB-ready**: The primary store is `tools.json` (zero-infrastructure). If tool count grows significantly, an optional single-table Postgres store (`platform.tool_registry` with `qualified_name TEXT PK, spec JSONB, updated_at TIMESTAMPTZ`) can be added without changing the MCP server interface.

```
┌─────────────────────────────────────────────────────┐
│                  CI Pipeline                         │
│                                                     │
│  1. Collect toolspec.py from each MCP server        │
│  2. Validate all ToolSpecs                          │
│  3. Generate registry/tools.json                    │
│  4. Generate registry/servers.json                  │
│  5. Publish to mcp-hub deployment                   │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  registry/tools.json (auto-generated, ~30 entries)  │
│                                                     │
│  [                                                  │
│    {                                                │
│      "qualified_name": "llm_mcp.generate_text",     │
│      "name": "generate_text",                       │
│      "server": "llm_mcp",                           │
│      "category": "ai.llm",                          │
│      "tags": ["llm", "generation", "text"],          │
│      "tenant_mode": "tenant_aware",                 │
│      "description": "Generate text using ...",      │
│      "side_effects": ["external_api"],              │
│      "is_active": true                              │
│    },                                               │
│    ...                                              │
│  ]                                                  │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  registry_mcp (new MCP server)                      │
│                                                     │
│  Tools:                                             │
│    discover_tools(category?, query?, tags?)          │
│    get_tool_spec(qualified_name)                     │
│    list_servers()                                    │
│    list_categories()                                 │
│                                                     │
│  Resources:                                         │
│    registry://tools    → Full tool registry          │
│    registry://servers  → Server metadata             │
└─────────────────────────────────────────────────────┘
```

### 4.2 Discovery MCP Server

```python
# mcp-hub/registry_mcp/server.py

"""
MCP Registry Server — Service Discovery for the BF Agent Platform.

Provides AI assistants with dynamic tool discovery capabilities.
Reads from the auto-generated registry/tools.json.
"""

import functools
import json
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("registry-mcp")

REGISTRY_PATH = Path(__file__).parent.parent / "registry" / "tools.json"


@functools.lru_cache(maxsize=1)
def _load_registry() -> tuple[dict, ...]:
    """Load tool registry from JSON file (cached, call _load_registry.cache_clear() to reload)."""
    if not REGISTRY_PATH.exists():
        return ()
    return tuple(json.loads(REGISTRY_PATH.read_text(encoding="utf-8")))


@app.tool()
async def discover_tools(
    category: str | None = None,
    query: str | None = None,
    tags: str | None = None,
    tenant_mode: str | None = None,
    active_only: bool = True,
) -> str:
    """
    Discover available MCP tools across all platform servers.

    Use this tool FIRST when you need to find what tools are available
    for a specific task. Supports filtering by category, keyword search,
    tags, and tenant mode.

    Args:
        category: Filter by ToolCategory (e.g., 'ai.llm', 'domain.travel')
        query: Keyword search across name, description, and tags
        tags: Comma-separated tags to filter by (e.g., 'llm,generation')
        tenant_mode: Filter by tenant mode ('tenant_scoped', 'tenant_aware', 'global')
        active_only: Only return active tools (default: true)

    Returns:
        JSON list of matching tool specifications with metadata.
    """
    registry = _load_registry()

    results = registry
    if active_only:
        results = [t for t in results if t.get("is_active", True)]
    if category:
        results = [t for t in results if t.get("category") == category]
    if tenant_mode:
        results = [t for t in results if t.get("tenant_mode") == tenant_mode]
    if tags:
        tag_set = {t.strip().lower() for t in tags.split(",")}
        results = [
            t for t in results
            if tag_set & set(t.get("tags", []))
        ]
    if query:
        q = query.lower()
        results = [
            t for t in results
            if q in t.get("name", "").lower()
            or q in t.get("description", "").lower()
            or any(q in tag for tag in t.get("tags", []))
        ]

    return json.dumps(
        {"success": True, "data": {"tools": results, "count": len(results)}, "error": None},
        indent=2,
    )


@app.tool()
async def get_tool_spec(qualified_name: str) -> str:
    """
    Get the full specification for a specific tool.

    Args:
        qualified_name: Fully qualified tool name (e.g., 'llm_mcp.generate_text')

    Returns:
        Complete ToolSpec with parameters, return schema, and governance metadata.
    """
    registry = _load_registry()
    for tool in registry:
        if tool.get("qualified_name") == qualified_name:
            return json.dumps(
                {"success": True, "data": tool, "error": None}, indent=2,
            )

    return json.dumps({
        "success": False,
        "data": None,
        "error": {"code": "TOOL_NOT_FOUND", "message": f"Tool not found: {qualified_name}"},
        "suggestion": "Use discover_tools() to find available tools.",
    })


@app.tool()
async def list_servers() -> str:
    """
    List all MCP servers in the platform with their status and tool count.

    Returns:
        JSON list of server metadata.
    """
    registry = _load_registry()
    servers: dict[str, dict] = {}
    for tool in registry:
        srv = tool.get("server", "unknown")
        if srv not in servers:
            servers[srv] = {"name": srv, "tool_count": 0, "categories": set()}
        servers[srv]["tool_count"] += 1
        servers[srv]["categories"].add(tool.get("category", ""))

    # Convert sets to lists for JSON serialization
    result = []
    for srv in servers.values():
        srv["categories"] = sorted(srv["categories"])
        result.append(srv)

    return json.dumps({"success": True, "data": {"servers": result}, "error": None}, indent=2)


@app.tool()
async def list_categories() -> str:
    """
    List all tool categories with counts.

    Returns:
        JSON mapping of category to tool count.
    """
    registry = _load_registry()
    categories: dict[str, int] = {}
    for tool in registry:
        cat = tool.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    return json.dumps(
        {"success": True, "data": {"categories": categories}, "error": None},
        indent=2,
    )


@app.resource("registry://tools")
async def get_full_registry() -> str:
    """Full tool registry as MCP resource."""
    return json.dumps(_load_registry(), indent=2)


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 4.3 Registry Generation (CI Integration)

```python
# packages/mcp-governance/mcp_governance/registry/build.py

"""
Registry builder — collects ToolSpecs from all MCP servers and generates
the unified registry JSON.

Usage:
    python -m mcp_governance.registry.build --mcp-hub /path/to/mcp-hub --output registry/

Runs in CI after each mcp-hub commit.

INVARIANT: Each toolspec.py MUST be a pure declaration file — only Pydantic
model instantiations and list assignments. No side effects (DB connections,
env var reads, network calls) on import. The builder uses importlib.import_module
which executes module-level code.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from mcp_governance.spec.models import ToolSpec
from mcp_governance.spec.validator import validate_registry


def collect_toolspecs(mcp_hub_path: Path) -> list[ToolSpec]:
    """Collect all ToolSpecs from MCP server toolspec.py files."""
    specs: list[ToolSpec] = []
    sys.path.insert(0, str(mcp_hub_path))

    for server_dir in sorted(mcp_hub_path.iterdir()):
        toolspec_file = server_dir / "toolspec.py"
        if not toolspec_file.exists():
            continue

        module_name = f"{server_dir.name}.toolspec"
        try:
            module = importlib.import_module(module_name)
            server_tools = getattr(module, "TOOLS", [])
            specs.extend(server_tools)
        except Exception as e:
            print(f"WARNING: Failed to load {toolspec_file}: {e}")

    return specs


def build_registry(mcp_hub_path: Path, output_path: Path) -> int:
    """Build the registry and return exit code (0=success, 1=errors)."""
    specs = collect_toolspecs(mcp_hub_path)
    print(f"Collected {len(specs)} tool specifications")

    # Validate
    results = validate_registry(specs)
    errors = [r for r in results if not r.is_valid]
    warnings = [r for r in results if r.warnings]

    for r in results:
        for e in r.errors:
            print(f"ERROR [{r.tool_name}]: {e}")
        for w in r.warnings:
            print(f"WARNING [{r.tool_name}]: {w}")

    if errors:
        print(f"\n❌ {len(errors)} tools have validation errors — fix before merge")
        return 1

    # Generate registry JSON
    output_path.mkdir(parents=True, exist_ok=True)
    tools_json = [spec.model_dump(mode="json") for spec in specs]

    # Add qualified_name for lookup
    for tool in tools_json:
        tool["qualified_name"] = f"{tool['server']}.{tool['name']}"

    (output_path / "tools.json").write_text(
        json.dumps(tools_json, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Generate server summary
    servers: dict[str, dict] = {}
    for spec in specs:
        if spec.server not in servers:
            servers[spec.server] = {
                "name": spec.server,
                "tool_count": 0,
                "tools": [],
                "categories": set(),
            }
        servers[spec.server]["tool_count"] += 1
        servers[spec.server]["tools"].append(spec.name)
        servers[spec.server]["categories"].add(spec.category.value)

    server_list = []
    for s in servers.values():
        s["categories"] = sorted(s["categories"])
        server_list.append(s)

    (output_path / "servers.json").write_text(
        json.dumps(server_list, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n✅ Registry generated: {len(specs)} tools across {len(servers)} servers")
    if warnings:
        print(f"⚠️  {sum(len(r.warnings) for r in warnings)} warnings to address")

    return 0
```

---

## 5. Composition Patterns (Deferred)

Tool composition (sequential chains, parallel execution, feedback-driven pipelines) is **deferred to a separate future ADR**. Rationale:

1. **AI-native orchestration**: Claude and Cascade already compose tools natively — a declarative chain engine duplicates their core capability
2. **No concrete use cases yet**: No production workflow currently requires deterministic multi-tool chains
3. **Avoid premature abstraction**: YAML+Jinja2 chain definitions introduce a DSL and template-injection risk without proven need

The `inputs_from` and `outputs_to` fields in `ToolSpec` provide **graph metadata** that AI assistants can use for ad-hoc composition decisions. This is sufficient for Phase 1+2.

When concrete, repeatable workflows emerge that AI-native orchestration handles poorly, a dedicated ADR should evaluate Python-based chain definitions (not YAML+Jinja2) to stay testable and avoid magic behavior.

---

## 6. Migration Plan

### Phase 1: Foundation (Weeks 1-2)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | Create `mcp-governance` package in `platform/packages/` | `pyproject.toml`, Pydantic models |
| 3-4 | Implement ToolSpec, ParamSpec, ReturnSpec + `response.py` | Core schemas with tests |
| 5 | Implement validator with CI integration | `validate_toolspec()`, GitHub Action |
| 6-7 | Write toolspec.py for `deployment_mcp` (pilot — already has response.py) | First compliant server |
| 8-9 | Write toolspec.py for `llm_mcp` + migrate to response envelope | 2 production servers covered |
| 10 | Registry builder script + CI pipeline | Auto-generated `tools.json` |

### Phase 2: Discovery (Weeks 3-4)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | Implement new `registry_mcp` server (replaces dead-code ADR-015) | Discovery tools working |
| 3-4 | Archive old `registry_mcp` code | Clean codebase |
| 5-7 | Write toolspec.py for remaining servers (`ifc_mcp`, `orchestrator_mcp`, `travel_mcp`, `illustration_mcp`) | All 6 production servers covered |
| 8-9 | Cascade/Claude integration testing | AI can discover tools dynamically |
| 10 | Documentation update (Sphinx) | MCP Hub docs reflect governance |

---

## 7. Consequences

### 7.1 Positive

- **Consistent governance**: All MCP tools follow the same specification standard
- **Dynamic discovery**: AI assistants can find tools at runtime — no static config drift
- **DSGVO transparency**: `tenant_mode` makes multi-tenancy compliance visible at tool level
- **Better AI tool selection**: Rich descriptions, examples, and metadata improve tool choice accuracy
- **Composition foundation**: `inputs_from`/`outputs_to` graph enables future automated workflows
- **CI quality gates**: Validation catches inconsistencies before deployment
- **Aligned patterns**: ToolSpec mirrors PromptTemplateSpec design — team familiarity

### 7.2 Negative

- **Dual maintenance**: `toolspec.py` must stay in sync with `@mcp.tool()` decorators — accepted trade-off (see 7.3)
- **ParamSpec duplication**: `param_type`, `required`, `default` repeat MCP `inputSchema` — accepted because build-time extraction from runtime schemas is fragile and introduces magic behavior
- **Migration effort**: ~6 production servers need toolspec.py files + error contract migration (gradual, not blocking)
- **Learning curve**: Team must understand ToolSpec schema and validation rules
- **Schema evolution**: Changes to ToolSpec require migration of existing specs

### 7.3 Mitigation

| Risk | Mitigation |
|------|------------|
| ToolSpec/MCP drift | CI validates that toolspec.py names match @tool() function names. ParamSpec duplication is intentional — explicit > magic. |
| Error contract migration | Gradual per-server migration. `mcp_governance.response` provides drop-in helpers. Minimum contract (`success` + `error`) enforced first. |
| Migration effort | Phased rollout — `deployment_mcp` first (already compliant), then `llm_mcp`, then rest |
| Schema evolution | `schema_version` field in ToolSpec + migration scripts (same pattern as PromptTemplateSpec) |
| Adoption resistance | Start with pilot (`deployment_mcp`) → demonstrate value → expand |

---

## 8. Metrics & Success Criteria

### 8.1 Quantitative

| Metric | Current | Phase 1 Target | Phase 2 Target | Measurement |
|--------|---------|----------------|----------------|-------------|
| Servers with ToolSpec | 0/6 | 2/6 | 6/6 | `tools.json` entry count |
| Spec validation pass rate | N/A | 100% | 100% | CI pipeline |
| Tools with examples | ~0% | 50% | 80% | Validator warnings |
| Tools with return specs | ~0% | 60% | 90% | Validator warnings |
| Discovery response time | N/A | < 50ms | < 50ms | Registry MCP benchmark |

### 8.2 Qualitative

- [ ] All production MCP servers have compliant `toolspec.py` files
- [ ] AI assistants (Claude, Cascade) can discover tools via `registry_mcp`
- [ ] `tenant_mode` metadata correctly reflects actual tenant behavior for all tools
- [ ] Error handling follows standardized contract across all servers
- [ ] New MCP servers are created with `toolspec.py` from day one (template provided)

---

## 9. References

- [MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25) — Wire protocol standard
- [MCP Tools Concept](https://modelcontextprotocol.info/docs/concepts/tools/) — Official tool documentation
- [ToolUniverse (Harvard/Zitnik Lab)](https://zitniklab.hms.harvard.edu/) — Architecture patterns (discovery, composition) — internal analysis only
- [Platform Architecture Master](../PLATFORM_ARCHITECTURE_MASTER.md) — Service/Provider patterns
- [Prompt Template System Concept](../PROMPT_TEMPLATE_SYSTEM_CONCEPT.md) — Schema design alignment
- [ADR-008: Infrastructure Services](./ADR-008-infrastructure-services.md) — Info service concept
- [ADR-009: Deployment Architecture](./ADR-009-deployment-architecture.md) — CI/CD patterns

---

## 10. Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-02-13 | Achim Dehnert | Initial draft — three-phase governance architecture |
| 2026-02-13 | Cascade (Review v2) | Revised: Two-phase (composition deferred). Fixed server inventory (7 real, not 14). Aligned error contract with existing `response.py`. Added rejected Option D (dead-code registry). Fixed Pydantic v2 `ConfigDict`. Added `schema_version`, tag validation. Documented ParamSpec duplication rationale. |
