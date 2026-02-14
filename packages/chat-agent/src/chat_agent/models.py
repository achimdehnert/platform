"""Pydantic models for the chat-agent package.

Defines the core data structures for chat sessions, messages,
tool results, and agent context.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolResult(BaseModel):
    """Result of a single tool execution."""

    model_config = ConfigDict(frozen=True)

    success: bool = Field(description="Whether the tool call succeeded")
    data: Any = Field(
        default=None, description="Result data (dict, list, str)"
    )
    error: str | None = Field(
        default=None, description="Error message if failed"
    )


class AgentContext(BaseModel):
    """Context passed to every tool execution."""

    model_config = ConfigDict(frozen=True)

    user: Any = Field(
        default=None, description="Authenticated user object"
    )
    tenant_id: str | None = Field(
        default=None, description="Tenant ID for multi-tenancy"
    )
    session_id: str = Field(description="Current chat session ID")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (e.g. project_id)",
    )


class ChatMessage(BaseModel):
    """Single message in a chat session."""

    model_config = ConfigDict(frozen=True)

    role: str = Field(description="system, user, assistant, or tool")
    content: str | None = Field(
        default=None, description="Text content"
    )
    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Tool calls (assistant role only)",
    )
    tool_call_id: str | None = Field(
        default=None,
        description="ID of the tool call this message responds to",
    )
    name: str | None = Field(
        default=None, description="Tool name (tool role only)"
    )

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to API-compatible dict for LLM calls."""
        d: dict[str, Any] = {"role": self.role}
        if self.content is not None:
            d["content"] = self.content
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            d["name"] = self.name
        return d


class ChatSession(BaseModel):
    """Persistent chat session with message history."""

    id: str = Field(description="Unique session identifier")
    messages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Message history (API-format dicts)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Session-level metadata",
    )


class AgentResponse(BaseModel):
    """Response from ChatAgent.chat()."""

    model_config = ConfigDict(frozen=True)

    content: str | None = Field(
        description="Final text response from the agent"
    )
    rounds: int = Field(
        default=1,
        description="Number of LLM rounds used",
    )
    tool_calls_made: int = Field(
        default=0,
        description="Total tool calls executed",
    )
