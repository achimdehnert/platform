"""ChatAgent — domain-agnostic Tool-Use agent.

The core loop: user message → LLM → (tool calls → execute → LLM)* → response.

Decoupled from any specific LLM client via the CompletionBackend protocol.
Apps provide domain logic via DomainToolkit.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .models import AgentContext, AgentResponse, ChatSession, ToolResult
from .session import SessionBackend
from .toolkit import DomainToolkit

logger = logging.getLogger(__name__)


@runtime_checkable
class CompletionBackend(Protocol):
    """Protocol for LLM completion with tool-use.

    Matches creative_services.DynamicLLMClient.complete() signature.
    """

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
        **kwargs: Any,
    ) -> Any:
        """Call LLM with messages and optional tools.

        Must return an object with:
        - content: str | None
        - tool_calls: list with .id, .name, .arguments
        - has_tool_calls: bool
        """
        ...


@dataclass
class ChatAgent:
    """Domain-agnostic Tool-Use agent.

    Extracted from travel-beat ConversationalTripAgent,
    generalized for all apps per ADR-034 §3.

    Usage::

        agent = ChatAgent(
            toolkit=CADToolkit(db_pool),
            completion=DynamicLLMClient(registry),
            session_backend=RedisSessionBackend(redis),
            system_prompt="You are a CAD assistant...",
        )
        response = await agent.chat(
            session_id="cad-user-123",
            user_message="Wie viele tragende Wände im 2.OG?",
            user=request.user,
        )
    """

    toolkit: DomainToolkit
    completion: CompletionBackend
    session_backend: SessionBackend
    system_prompt: str
    max_rounds: int = 10
    action_code: str = "chat"

    async def chat(
        self,
        session_id: str,
        user_message: str,
        *,
        user: Any = None,
        tenant_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """Process a user message through the Tool-Use loop.

        Args:
            session_id: Unique session identifier.
            user_message: The user's natural language input.
            user: Authenticated user object (passed to tools).
            tenant_id: Tenant ID for multi-tenant isolation.
            metadata: Additional context for tool execution.

        Returns:
            AgentResponse with the final text and stats.
        """
        session = await self.session_backend.load(session_id)
        if session is None:
            session = ChatSession(
                id=session_id,
                messages=[
                    {"role": "system", "content": self.system_prompt}
                ],
            )

        session.messages.append(
            {"role": "user", "content": user_message}
        )

        ctx = AgentContext(
            user=user,
            tenant_id=tenant_id,
            session_id=session_id,
            metadata=metadata or {},
        )

        total_tool_calls = 0
        content: str | None = None
        round_num = 0

        for round_num in range(self.max_rounds):
            result = await self.completion.complete(
                messages=session.messages,
                tools=self.toolkit.tool_schemas,
                tool_choice="auto",
            )

            if not result.has_tool_calls:
                content = result.content
                session.messages.append(
                    {"role": "assistant", "content": content}
                )
                break

            # Build assistant message with tool calls
            assistant_msg = _build_assistant_msg(result)
            session.messages.append(assistant_msg)

            # Execute each tool call
            for tc in result.tool_calls:
                total_tool_calls += 1
                tool_result = await self._execute_tool(
                    tc, ctx
                )
                tool_msg = _build_tool_result_msg(
                    tc.id, tc.name, tool_result
                )
                session.messages.append(tool_msg)
        else:
            logger.warning(
                "Max rounds (%d) reached for session %s",
                self.max_rounds,
                session_id,
            )
            content = result.content if hasattr(result, "content") else None

        await self.session_backend.save(session)

        return AgentResponse(
            content=content,
            rounds=round_num + 1,
            tool_calls_made=total_tool_calls,
        )

    async def _execute_tool(
        self,
        tool_call: Any,
        ctx: AgentContext,
    ) -> ToolResult:
        """Execute a single tool call with error handling."""
        try:
            return await self.toolkit.execute(
                tool_name=tool_call.name,
                arguments=tool_call.arguments,
                ctx=ctx,
            )
        except Exception as exc:
            logger.exception(
                "Tool %s failed: %s", tool_call.name, exc
            )
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool execution failed: {exc}",
            )


def _build_assistant_msg(result: Any) -> dict[str, Any]:
    """Build assistant message dict from completion result."""
    msg: dict[str, Any] = {
        "role": "assistant",
        "content": result.content,
    }
    if result.tool_calls:
        msg["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments),
                },
            }
            for tc in result.tool_calls
        ]
    return msg


def _build_tool_result_msg(
    tool_call_id: str,
    tool_name: str,
    result: ToolResult,
) -> dict[str, Any]:
    """Build tool result message dict for the LLM."""
    if result.success:
        content = json.dumps(result.data, default=str)
    else:
        content = json.dumps({"error": result.error})

    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": tool_name,
        "content": content,
    }
