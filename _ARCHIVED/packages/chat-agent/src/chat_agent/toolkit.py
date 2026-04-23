"""DomainToolkit ABC — each app defines its tools + handlers.

Apps implement this interface to provide domain-specific tools
that the ChatAgent can use via LLM Tool-Use.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import AgentContext, ToolResult


class DomainToolkit(ABC):
    """Abstract base for app-specific tool collections.

    Each consuming app (cad-hub, travel-beat, bfagent, weltenhub)
    subclasses this to expose domain tools to the ChatAgent.

    Example::

        class CADToolkit(DomainToolkit):
            @property
            def tool_schemas(self) -> list[dict]:
                return [QUERY_ROOMS_TOOL, QUERY_WALLS_TOOL, ...]

            async def execute(self, tool_name, arguments, ctx):
                return await self._handlers[tool_name](arguments, ctx)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier, e.g. 'cad', 'travel', 'book'."""
        ...

    @property
    @abstractmethod
    def tool_schemas(self) -> list[dict[str, Any]]:
        """OpenAI-format tool definitions.

        Each entry should be::

            {
                "type": "function",
                "function": {
                    "name": "query_rooms",
                    "description": "...",
                    "parameters": { ... }
                }
            }
        """
        ...

    @abstractmethod
    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        ctx: AgentContext,
    ) -> ToolResult:
        """Execute a tool by name with given arguments."""
        ...

    def format_response(
        self, tool_results: list[ToolResult]
    ) -> str | None:
        """Optional: app-specific formatting of tool results.

        Return None to let the LLM formulate the response.
        """
        return None
