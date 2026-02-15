# ADR-010: MCP Tool Governance — Specification Standard, Service Discovery & Composition

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-13 |
| **Author** | Achim Dehnert |
| **Reviewers** | — |
| **Supersedes** | — |
| **Related** | ADR-008 (Infrastructure Services), ADR-009 (Deployment Architecture) |
| **Inspired by** | ToolUniverse (Harvard/Zitnik Lab) — architecture patterns only |

---

## 1. Context

### 1.1 Current State

The MCP Hub provides 14 MCP servers with ~30+ tools across multiple domains:

| Server | Domain | Status | Tools | Spec Governance |
|--------|--------|--------|-------|-----------------|
| `llm_mcp` | AI/LLM | ✅ Production | `generate_text`, `chat`, `embed` | Ad-hoc |
| `bfagent_mcp` | Requirements | ✅ Production | `get_requirement`, `add_feedback`, `list_domains` | Ad-hoc |
| `bfagent_sqlite_mcp` | Data | ✅ Production | `query`, `schema` | Ad-hoc |
| `deployment_mcp` | DevOps | ✅ Production | `trigger_workflow`, `get_run_status` | Ad-hoc |
| `research_mcp` | Search | ✅ Production | `search_web`, `fetch_url` | Ad-hoc |
| `travel_mcp` | Travel | ✅ Production | `get_destination`, `generate_itinerary` | Ad-hoc |
| `illustration_mcp` | Creative | ✅ Production | `generate_image`, `edit_image` | Ad-hoc |
| `book_writing_mcp` | Creative | ✅ Production | Writing tools | Ad-hoc |
| `german_tax_mcp` | Finance | 🔧 Beta | Tax calculation tools | Ad-hoc |
| `ifc_mcp` | CAD/BIM | 🔧 Beta | IFC processing tools | Ad-hoc |
| `cad_mcp` | CAD | 🔧 Beta | DXF/CAD tools | Ad-hoc |
| `dlm_mcp` | Documents | 🔧 Beta | Document management | Ad-hoc |
| `physicals_mcp` | Engineering | 🔧 Beta | Physical calculations | Ad-hoc |
| `mcp_runner_ui` | Testing | ✅ Production | UI testing tools | Ad-hoc |

Every server defines its own conventions for tool naming, parameter schemas, error handling, return formats, and documentation. There is no centralized registry, no discovery mechanism, and no way for AI assistants to dynamically find tools.

### 1.2 Pain Points

1. **No Specification Standard**: Each MCP server defines tools in isolation — inconsistent naming, varying error formats, no return schema guarantees
2. **No Service Discovery**: AI assistants (Claude, Cascade) must be statically configured with known tools — adding a new tool requires prompt/config updates everywhere
3. **No Composition**: Multi-tool workflows (e.g., research → generate → feedback) are manually orchestrated by the AI with no structured chaining
4. **Inconsistent Error Handling**: Some tools return `{"success": false, "error": "..."}`, others raise exceptions, some return plain strings
5. **No Tenant Awareness Metadata**: No way for an AI to know which tools respect multi-tenancy and which operate globally
6. **Documentation Drift**: Tool descriptions in code diverge from Sphinx docs over time

### 1.3 External Analysis: ToolUniverse Patterns

A comprehensive evaluation of ToolUniverse (Harvard/Zitnik Lab, arXiv:2509.23426) revealed that while its 600+ biomedical tools have no domain relevance for our platform, three architectural patterns are directly applicable:

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

**We adopt a Three-Phase MCP Governance Architecture** building incrementally:

1. **Phase 1 — Tool Specification Standard** (`ToolSpec`): Pydantic-based schema for all MCP tools
2. **Phase 2 — Service Discovery**: Registry MCP server with discovery tools
3. **Phase 3 — Composition Patterns**: Structured multi-tool workflows

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
│  │  │   │   ├── validator.py   # Schema validation & compliance check    │  │
│  │  │   │   └── exporter.py    # Export to JSON Schema, MCP native       │  │
│  │  │   ├── registry/          # Phase 2: Service Discovery              │  │
│  │  │   │   ├── __init__.py                                              │  │
│  │  │   │   ├── store.py       # Registry store (file-based + DB)        │  │
│  │  │   │   ├── search.py      # Keyword & tag-based discovery           │  │
│  │  │   │   └── server.py      # MCP server exposing registry            │  │
│  │  │   └── compose/           # Phase 3: Composition Patterns           │  │
│  │  │       ├── __init__.py                                              │  │
│  │  │       ├── chain.py       # Sequential tool chains                  │  │
│  │  │       ├── parallel.py    # Parallel execution                      │  │
│  │  │       └── pipeline.py    # Pipeline orchestrator                   │  │
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
   │  llm_mcp    │           │ travel_mcp  │           │  cad_mcp    │
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
- Overkill for ~30 tools across 14 servers
- Adds operational complexity without proportional benefit
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

from pydantic import BaseModel, Field, field_validator
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

    model_config = {"frozen": True}


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

    model_config = {"frozen": True}


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

    model_config = {"frozen": True}

    @field_validator("tags")
    @classmethod
    def lowercase_tags(cls, v: list[str]) -> list[str]:
        return [tag.lower().strip() for tag in v]

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

All MCP tools MUST return results in this standardized format:

```python
# Standard success response
{
    "success": True,
    "data": { ... },          # Tool-specific result
    "metadata": {             # Optional execution metadata
        "duration_ms": 1234,
        "source": "openai",
    }
}

# Standard error response
{
    "success": False,
    "error": "Human-readable error message",
    "error_code": "RATE_LIMIT_EXCEEDED",  # Machine-readable code
    "retryable": True,                     # Can the AI retry?
    "details": { ... }                     # Optional debug context
}
```

Tools MUST NOT raise exceptions through the MCP protocol. Errors belong in the result object so the AI can reason about them.

---

## 4. Phase 2: Service Discovery

### 4.1 Registry Architecture

The registry is a **generated JSON file** + **MCP server** — no new infrastructure:

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

import json
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("registry-mcp")

REGISTRY_PATH = Path(__file__).parent.parent / "registry" / "tools.json"


def _load_registry() -> list[dict]:
    """Load tool registry from JSON file."""
    if not REGISTRY_PATH.exists():
        return []
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


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
        {"success": True, "tools": results, "count": len(results)},
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
            return json.dumps({"success": True, "tool": tool}, indent=2)

    return json.dumps({
        "success": False,
        "error": f"Tool not found: {qualified_name}",
        "error_code": "TOOL_NOT_FOUND",
        "retryable": False,
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

    return json.dumps({"success": True, "servers": result}, indent=2)


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
        {"success": True, "categories": categories},
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

## 5. Phase 3: Composition Patterns (Q3 2026)

### 5.1 Concept

Composition builds on the existing **PromptChain** pattern from `creative-services` but at the MCP tool level:

```python
# packages/mcp-governance/mcp_governance/compose/chain.py (Conceptual — Q3 2026)

"""
Tool chain composition for multi-step AI workflows.

Inspired by:
  - ToolUniverse's Tool Composer (sequential, parallel, feedback-driven)
  - creative-services PromptChain (input/output mapping, conditional execution)
  - Unix pipe philosophy (small tools, composed via data flow)
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any


class ChainStep(BaseModel):
    """Single step in a tool chain."""

    name: str
    tool: str                          # Qualified tool name (e.g., 'research_mcp.search_web')
    input_mapping: dict[str, str]      # chain_context_key → tool_param_name
    output_mapping: dict[str, str]     # tool_result_key → chain_context_key
    condition: str | None = None       # Jinja2 condition for conditional execution
    on_error: str = "stop"             # 'stop', 'skip', 'retry'


class ToolChain(BaseModel):
    """
    Declarative multi-tool workflow.

    Example: Research-Generate-Review Pipeline
      1. search_web("topic") → search_results
      2. generate_text(prompt=search_results) → draft
      3. add_feedback(content=draft) → review
    """

    key: str = Field(pattern=r"^[a-z][a-z0-9_.]*$")
    name: str
    description: str
    steps: list[ChainStep]
    initial_context: dict[str, Any] = Field(default_factory=dict)
```

### 5.2 Example Chain Definition

```yaml
# registry/chains/research_generate_review.yaml

key: workflow.research_generate_review
name: Research-Generate-Review Pipeline
description: |
  Three-step workflow: search the web for information, generate
  content based on findings, then submit for feedback review.

steps:
  - name: research
    tool: research_mcp.search_web
    input_mapping:
      query: topic
    output_mapping:
      search_results: data.results

  - name: generate
    tool: llm_mcp.generate_text
    input_mapping:
      prompt: "Synthesize these findings: {{ search_results }}"
    output_mapping:
      draft: data.text

  - name: review
    tool: bfagent_mcp.add_feedback
    input_mapping:
      content: draft
      feedback_type: "auto_review"
    output_mapping:
      feedback_id: data.feedback_id
    condition: "{{ draft | length > 100 }}"
    on_error: skip
```

---

## 6. Migration Plan

### Phase 1: Foundation (Weeks 1-2)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | Create `mcp-governance` package structure | `pyproject.toml`, Pydantic models |
| 3-4 | Implement ToolSpec, ParamSpec, ReturnSpec models | Core schemas with tests |
| 5 | Implement validator with CI integration | `validate_toolspec()`, GitHub Action |
| 6-7 | Write toolspec.py for `llm_mcp` (pilot) | First compliant server |
| 8-9 | Write toolspec.py for `research_mcp`, `bfagent_mcp` | 3 production servers covered |
| 10 | Registry builder script + CI pipeline | Auto-generated `tools.json` |

### Phase 2: Discovery (Weeks 3-4)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | Implement `registry_mcp` server | Discovery tools working |
| 3-5 | Write toolspec.py for remaining production servers | All 7 production servers covered |
| 6-7 | Cascade/Claude integration testing | AI can discover tools dynamically |
| 8 | Documentation update (Sphinx) | MCP Hub docs reflect governance |
| 9-10 | Migrate beta servers to ToolSpec | Full coverage |

### Phase 3: Composition (Q3 2026)

| Week | Task | Deliverable |
|------|------|-------------|
| 1-2 | Design ToolChain schema (aligned with PromptChain) | ADR amendment |
| 3-4 | Implement chain executor | Sequential chains working |
| 5-6 | Add parallel execution support | Parallel + sequential |
| 7-8 | Integration testing with real workflows | 3 example chains |

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

- **Dual maintenance**: `toolspec.py` must stay in sync with `@mcp.tool()` decorators
- **Migration effort**: ~14 servers need toolspec.py files (gradual, not blocking)
- **Learning curve**: Team must understand ToolSpec schema and validation rules
- **Schema evolution**: Changes to ToolSpec require migration of existing specs

### 7.3 Mitigation

| Risk | Mitigation |
|------|------------|
| ToolSpec/MCP drift | CI validates that toolspec.py names match @tool() function names |
| Migration effort | Phased rollout — production servers first, beta servers optional initially |
| Schema evolution | `schema_version` field + migration scripts (same pattern as PromptTemplateSpec) |
| Adoption resistance | Start with pilot (`llm_mcp`) → demonstrate value → expand |

---

## 8. Metrics & Success Criteria

### 8.1 Quantitative

| Metric | Current | Phase 1 Target | Phase 2 Target | Measurement |
|--------|---------|----------------|----------------|-------------|
| Servers with ToolSpec | 0/14 | 3/14 | 14/14 | `tools.json` entry count |
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
- [ToolUniverse (arXiv:2509.23426)](https://arxiv.org/abs/2509.23426) — Architecture patterns (discovery, composition)
- [Platform Architecture Master](../PLATFORM_ARCHITECTURE_MASTER.md) — Service/Provider patterns
- [Prompt Template System Concept](../PROMPT_TEMPLATE_SYSTEM_CONCEPT.md) — Schema design alignment
- [ADR-008: Infrastructure Services](./ADR-008-infrastructure-services.md) — Info service concept
- [ADR-009: Deployment Architecture](./ADR-009-deployment-architecture.md) — CI/CD patterns

---

## 10. Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-02-13 | Achim Dehnert | Initial draft — three-phase governance architecture |
