"""Tests for chat-agent package (ADR-034 §3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from chat_agent import (
    AgentContext,
    ChatAgent,
    CompositeToolkit,
    DomainToolkit,
    InMemorySessionBackend,
    ToolResult,
)
from chat_agent.registry import clear, get, list_registered, register


# ------------------------------------------------------------------
# Fake CompletionBackend for testing
# ------------------------------------------------------------------


@dataclass
class FakeToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class FakeCompletionResponse:
    content: str | None = None
    tool_calls: list[FakeToolCall] = field(default_factory=list)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class FakeCompletionBackend:
    """Returns pre-scripted responses."""

    def __init__(self, responses: list[FakeCompletionResponse]) -> None:
        self._responses = list(responses)
        self._call_count = 0

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
        **kwargs: Any,
    ) -> FakeCompletionResponse:
        resp = self._responses[self._call_count]
        self._call_count += 1
        return resp


# ------------------------------------------------------------------
# Fake DomainToolkit
# ------------------------------------------------------------------


class EchoToolkit(DomainToolkit):
    """Simple toolkit that echoes arguments back."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "echo",
                    "description": "Echo args back",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"},
                        },
                        "required": ["message"],
                    },
                },
            }
        ]

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        ctx: AgentContext,
    ) -> ToolResult:
        if tool_name == "echo":
            return ToolResult(
                success=True,
                data={"echoed": arguments.get("message", "")},
            )
        return ToolResult(
            success=False, error=f"Unknown tool: {tool_name}"
        )


# ------------------------------------------------------------------
# Tests: ChatAgent
# ------------------------------------------------------------------


class TestChatAgentSimpleResponse:
    @pytest.mark.asyncio
    async def test_should_return_text_without_tools(self) -> None:
        backend = FakeCompletionBackend([
            FakeCompletionResponse(content="Hello!"),
        ])
        agent = ChatAgent(
            toolkit=EchoToolkit(),
            completion=backend,
            session_backend=InMemorySessionBackend(),
            system_prompt="You are a test bot.",
        )

        resp = await agent.chat(
            session_id="s1",
            user_message="Hi",
        )

        assert resp.content == "Hello!"
        assert resp.rounds == 1
        assert resp.tool_calls_made == 0

    @pytest.mark.asyncio
    async def test_should_persist_session(self) -> None:
        session_backend = InMemorySessionBackend()
        backend = FakeCompletionBackend([
            FakeCompletionResponse(content="First reply"),
        ])
        agent = ChatAgent(
            toolkit=EchoToolkit(),
            completion=backend,
            session_backend=session_backend,
            system_prompt="Test",
        )

        await agent.chat(session_id="s2", user_message="Hello")

        session = await session_backend.load("s2")
        assert session is not None
        assert len(session.messages) == 3  # system + user + assistant


class TestChatAgentToolUse:
    @pytest.mark.asyncio
    async def test_should_execute_tool_and_continue(self) -> None:
        backend = FakeCompletionBackend([
            # Round 1: LLM calls a tool
            FakeCompletionResponse(
                content=None,
                tool_calls=[
                    FakeToolCall(
                        id="tc_1",
                        name="echo",
                        arguments={"message": "test"},
                    )
                ],
            ),
            # Round 2: LLM responds with text
            FakeCompletionResponse(content="Echo result: test"),
        ])

        agent = ChatAgent(
            toolkit=EchoToolkit(),
            completion=backend,
            session_backend=InMemorySessionBackend(),
            system_prompt="You are a test bot.",
        )

        resp = await agent.chat(
            session_id="s3",
            user_message="Echo test",
        )

        assert resp.content == "Echo result: test"
        assert resp.rounds == 2
        assert resp.tool_calls_made == 1

    @pytest.mark.asyncio
    async def test_should_handle_tool_error(self) -> None:
        backend = FakeCompletionBackend([
            FakeCompletionResponse(
                content=None,
                tool_calls=[
                    FakeToolCall(
                        id="tc_err",
                        name="nonexistent",
                        arguments={},
                    )
                ],
            ),
            FakeCompletionResponse(
                content="Tool not found"
            ),
        ])

        agent = ChatAgent(
            toolkit=EchoToolkit(),
            completion=backend,
            session_backend=InMemorySessionBackend(),
            system_prompt="Test",
        )

        resp = await agent.chat(
            session_id="s4",
            user_message="Call unknown",
        )

        assert resp.content == "Tool not found"
        assert resp.tool_calls_made == 1


class TestChatAgentContext:
    @pytest.mark.asyncio
    async def test_should_pass_tenant_id_to_tools(self) -> None:
        captured_ctx: list[AgentContext] = []

        class CapturingToolkit(EchoToolkit):
            async def execute(
                self,
                tool_name: str,
                arguments: dict[str, Any],
                ctx: AgentContext,
            ) -> ToolResult:
                captured_ctx.append(ctx)
                return ToolResult(success=True, data="ok")

        backend = FakeCompletionBackend([
            FakeCompletionResponse(
                tool_calls=[
                    FakeToolCall(
                        id="tc_t",
                        name="echo",
                        arguments={"message": "x"},
                    )
                ],
            ),
            FakeCompletionResponse(content="Done"),
        ])

        agent = ChatAgent(
            toolkit=CapturingToolkit(),
            completion=backend,
            session_backend=InMemorySessionBackend(),
            system_prompt="Test",
        )

        await agent.chat(
            session_id="s5",
            user_message="Hi",
            tenant_id="tenant-abc",
        )

        assert len(captured_ctx) == 1
        assert captured_ctx[0].tenant_id == "tenant-abc"
        assert captured_ctx[0].session_id == "s5"


# ------------------------------------------------------------------
# Tests: Registry
# ------------------------------------------------------------------


class TestToolkitRegistry:
    def setup_method(self) -> None:
        clear()

    def test_should_register_and_retrieve(self) -> None:
        toolkit = EchoToolkit()
        register("echo", toolkit)
        assert get("echo") is toolkit

    def test_should_reject_duplicate(self) -> None:
        register("echo", EchoToolkit())
        with pytest.raises(ValueError, match="already registered"):
            register("echo", EchoToolkit())

    def test_should_raise_on_missing(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            get("missing")

    def test_should_list_all(self) -> None:
        register("a", EchoToolkit())
        register("b", EchoToolkit())
        assert set(list_registered().keys()) == {"a", "b"}


# ------------------------------------------------------------------
# Tests: InMemorySessionBackend
# ------------------------------------------------------------------


class TestInMemorySessionBackend:
    @pytest.mark.asyncio
    async def test_should_save_and_load(self) -> None:
        from chat_agent.models import ChatSession

        backend = InMemorySessionBackend()
        session = ChatSession(
            id="test-1",
            messages=[{"role": "system", "content": "Hi"}],
        )

        await backend.save(session)
        loaded = await backend.load("test-1")

        assert loaded is not None
        assert loaded.id == "test-1"
        assert len(loaded.messages) == 1

    @pytest.mark.asyncio
    async def test_should_return_none_for_missing(self) -> None:
        backend = InMemorySessionBackend()
        assert await backend.load("nope") is None

    @pytest.mark.asyncio
    async def test_should_delete(self) -> None:
        from chat_agent.models import ChatSession

        backend = InMemorySessionBackend()
        await backend.save(ChatSession(id="del-me", messages=[]))
        await backend.delete("del-me")
        assert await backend.load("del-me") is None


# ------------------------------------------------------------------
# Tests: AgentResponse error/success
# ------------------------------------------------------------------


class TestAgentResponse:
    def test_should_be_success_without_error(self) -> None:
        from chat_agent.models import AgentResponse

        resp = AgentResponse(content="Hello")
        assert resp.success
        assert resp.error is None

    def test_should_be_failure_with_error(self) -> None:
        from chat_agent.models import AgentResponse

        resp = AgentResponse(error="timeout")
        assert not resp.success
        assert resp.error == "timeout"

    def test_should_have_model_field(self) -> None:
        from chat_agent.models import AgentResponse

        resp = AgentResponse(content="ok", model="gpt-4")
        assert resp.model == "gpt-4"


# ------------------------------------------------------------------
# Tests: ChatAgent error handling
# ------------------------------------------------------------------


class TestChatAgentErrorHandling:
    @pytest.mark.asyncio
    async def test_should_return_error_on_completion_exception(
        self,
    ) -> None:
        class FailingBackend:
            async def complete(self, **kwargs: Any) -> Any:
                raise RuntimeError("API down")

        agent = ChatAgent(
            toolkit=EchoToolkit(),
            completion=FailingBackend(),
            session_backend=InMemorySessionBackend(),
            system_prompt="Test",
        )

        resp = await agent.chat(
            session_id="err1", user_message="Hi"
        )

        assert not resp.success
        assert "LLM call failed" in resp.error
        assert resp.content is None

    @pytest.mark.asyncio
    async def test_should_return_error_on_max_rounds(
        self,
    ) -> None:
        backend = FakeCompletionBackend([
            # Always returns tool calls — never stops
            FakeCompletionResponse(
                tool_calls=[
                    FakeToolCall(
                        id=f"tc_{i}",
                        name="echo",
                        arguments={"message": "loop"},
                    )
                ],
            )
            for i in range(5)
        ])

        agent = ChatAgent(
            toolkit=EchoToolkit(),
            completion=backend,
            session_backend=InMemorySessionBackend(),
            system_prompt="Test",
            max_rounds=3,
        )

        resp = await agent.chat(
            session_id="mr1", user_message="Loop"
        )

        assert not resp.success
        assert "Max tool rounds" in resp.error
        assert resp.rounds == 3
        assert resp.tool_calls_made == 3


# ------------------------------------------------------------------
# Tests: CompositeToolkit
# ------------------------------------------------------------------


class MathToolkit(DomainToolkit):
    """Second toolkit for composite tests."""

    @property
    def name(self) -> str:
        return "math"

    @property
    def tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "add",
                    "description": "Add two numbers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number"},
                            "b": {"type": "number"},
                        },
                        "required": ["a", "b"],
                    },
                },
            }
        ]

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        ctx: AgentContext,
    ) -> ToolResult:
        if tool_name == "add":
            return ToolResult(
                success=True,
                data={"sum": arguments["a"] + arguments["b"]},
            )
        return ToolResult(
            success=False, error=f"Unknown: {tool_name}"
        )


class TestCompositeToolkit:
    def test_should_merge_schemas(self) -> None:
        composite = CompositeToolkit([
            EchoToolkit(), MathToolkit()
        ])
        names = {
            s["function"]["name"]
            for s in composite.tool_schemas
        }
        assert names == {"echo", "add"}

    def test_should_combine_names(self) -> None:
        composite = CompositeToolkit([
            EchoToolkit(), MathToolkit()
        ])
        assert composite.name == "echo+math"

    def test_should_reject_name_collision(self) -> None:
        with pytest.raises(ValueError, match="collision"):
            CompositeToolkit([
                EchoToolkit(), EchoToolkit()
            ])

    @pytest.mark.asyncio
    async def test_should_dispatch_to_correct_toolkit(
        self,
    ) -> None:
        composite = CompositeToolkit([
            EchoToolkit(), MathToolkit()
        ])
        ctx = AgentContext(session_id="t1")

        echo_result = await composite.execute(
            "echo", {"message": "hi"}, ctx
        )
        assert echo_result.success
        assert echo_result.data == {"echoed": "hi"}

        math_result = await composite.execute(
            "add", {"a": 2, "b": 3}, ctx
        )
        assert math_result.success
        assert math_result.data == {"sum": 5}

    @pytest.mark.asyncio
    async def test_should_return_error_for_unknown_tool(
        self,
    ) -> None:
        composite = CompositeToolkit([EchoToolkit()])
        ctx = AgentContext(session_id="t2")

        result = await composite.execute(
            "nonexistent", {}, ctx
        )
        assert not result.success
        assert "Unknown tool" in result.error
