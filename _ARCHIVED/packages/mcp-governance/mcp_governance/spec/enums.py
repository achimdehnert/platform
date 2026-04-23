"""MCP Tool Governance — Enumerations.

Defines platform-wide enums for tool classification, tenant modes,
side effects, and error policies. All enums are StrEnum for JSON
serialization compatibility.

See ADR-010 §3.1 for details.
"""

from __future__ import annotations

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

    TENANT_SCOPED = "tenant_scoped"
    TENANT_AWARE = "tenant_aware"
    GLOBAL = "global"


class SideEffect(StrEnum):
    """What side effects the tool produces."""

    NONE = "none"
    DATABASE_WRITE = "db_write"
    EXTERNAL_API = "external_api"
    FILE_SYSTEM = "file_system"
    NOTIFICATION = "notification"
    DEPLOYMENT = "deployment"


class ErrorPolicy(StrEnum):
    """How errors are reported."""

    RESULT_OBJECT = "result_object"
    MCP_ERROR = "mcp_error"
    EXCEPTION = "exception"
