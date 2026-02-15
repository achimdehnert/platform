"""CompositeToolkit — merges multiple DomainToolkits into one.

Allows ChatAgent to use tools from multiple domains
(e.g. TravelBeatToolkit + StoryToolkit) in a single session.
"""

from __future__ import annotations

import logging
from typing import Any

from .models import AgentContext, ToolResult
from .toolkit import DomainToolkit

logger = logging.getLogger(__name__)


class CompositeToolkit(DomainToolkit):
    """Merges multiple DomainToolkits into a single toolkit.

    Tool dispatch is resolved at init time by mapping each
    tool name to its owning toolkit. Collisions raise ValueError.

    Usage::

        composite = CompositeToolkit([
            TravelBeatToolkit(),
            StoryToolkit(),
        ])
        agent = ChatAgent(toolkit=composite, ...)
    """

    def __init__(
        self, toolkits: list[DomainToolkit],
    ) -> None:
        self._toolkits = list(toolkits)
        self._dispatch: dict[str, DomainToolkit] = {}

        for tk in self._toolkits:
            for schema in tk.tool_schemas:
                tool_name = schema["function"]["name"]
                if tool_name in self._dispatch:
                    existing = self._dispatch[tool_name].name
                    raise ValueError(
                        f"Tool name collision: '{tool_name}' "
                        f"exists in both '{existing}' and "
                        f"'{tk.name}' toolkits."
                    )
                self._dispatch[tool_name] = tk

        logger.info(
            "CompositeToolkit created: %s (%d tools)",
            self.name,
            len(self._dispatch),
        )

    @property
    def name(self) -> str:
        return "+".join(tk.name for tk in self._toolkits)

    @property
    def tool_schemas(self) -> list[dict[str, Any]]:
        schemas: list[dict[str, Any]] = []
        for tk in self._toolkits:
            schemas.extend(tk.tool_schemas)
        return schemas

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        ctx: AgentContext,
    ) -> ToolResult:
        """Dispatch tool call to the owning toolkit."""
        tk = self._dispatch.get(tool_name)
        if not tk:
            return ToolResult(
                success=False,
                data=None,
                error=(
                    f"Unknown tool: '{tool_name}'. "
                    f"Available: {list(self._dispatch.keys())}"
                ),
            )
        return await tk.execute(tool_name, arguments, ctx)
