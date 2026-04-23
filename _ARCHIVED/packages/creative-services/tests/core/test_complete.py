"""Tests for LLMClient.complete() and DynamicLLMClient.complete().

Tests tool-use functionality with mocked SDK responses.
Does NOT make real API calls.
"""

import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from creative_services.core.llm_client import (
    CompletionResponse,
    LLMClient,
    LLMConfig,
    LLMProvider,
    ToolCall,
)
from creative_services.core.llm_registry import (
    DictRegistry,
    DynamicLLMClient,
    LLMEntry,
    LLMTier,
)


# -- Fixtures --


SAMPLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        },
    }
]

SAMPLE_ANTHROPIC_TOOLS = [
    {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["location"],
        },
    }
]

SAMPLE_MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the weather in Berlin?"},
]


# -- ToolCall and CompletionResponse unit tests --


class TestToolCall:
    def test_should_create_frozen_tool_call(self) -> None:
        tc = ToolCall(id="tc_1", name="get_weather", arguments={"location": "Berlin"})
        assert tc.id == "tc_1"
        assert tc.name == "get_weather"
        assert tc.arguments == {"location": "Berlin"}

    def test_should_be_immutable(self) -> None:
        tc = ToolCall(id="tc_1", name="get_weather", arguments={"location": "Berlin"})
        with pytest.raises(AttributeError):
            tc.name = "other"  # type: ignore[misc]


class TestCompletionResponse:
    def test_should_report_no_tool_calls(self) -> None:
        resp = CompletionResponse(
            content="Hello!",
            model="gpt-4o-mini",
            provider=LLMProvider.OPENAI,
        )
        assert not resp.has_tool_calls
        assert resp.first_tool_call is None
        assert resp.content == "Hello!"

    def test_should_report_tool_calls(self) -> None:
        tc = ToolCall(id="tc_1", name="get_weather", arguments={"location": "Berlin"})
        resp = CompletionResponse(
            content=None,
            tool_calls=[tc],
            model="claude-3-5-sonnet-20241022",
            provider=LLMProvider.ANTHROPIC,
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )
        assert resp.has_tool_calls
        assert resp.first_tool_call == tc
        assert resp.total_tokens == 150

    def test_should_calculate_total_tokens_from_parts(self) -> None:
        resp = CompletionResponse(
            content="text",
            model="gpt-4o",
            provider=LLMProvider.OPENAI,
            usage={"prompt_tokens": 200, "completion_tokens": 80},
        )
        assert resp.total_tokens == 280


# -- Tool format conversion tests --


class TestToolConversion:
    def test_should_convert_openai_to_anthropic(self) -> None:
        result = LLMClient._to_anthropic_tool(SAMPLE_TOOLS[0])
        assert result["name"] == "get_weather"
        assert "input_schema" in result
        assert result["input_schema"]["type"] == "object"

    def test_should_pass_through_anthropic_format(self) -> None:
        result = LLMClient._to_anthropic_tool(SAMPLE_ANTHROPIC_TOOLS[0])
        assert result == SAMPLE_ANTHROPIC_TOOLS[0]

    def test_should_convert_anthropic_to_openai(self) -> None:
        result = LLMClient._to_openai_tool(SAMPLE_ANTHROPIC_TOOLS[0])
        assert result["type"] == "function"
        assert result["function"]["name"] == "get_weather"
        assert "parameters" in result["function"]

    def test_should_pass_through_openai_format(self) -> None:
        result = LLMClient._to_openai_tool(SAMPLE_TOOLS[0])
        assert result == SAMPLE_TOOLS[0]

    def test_should_handle_minimal_format(self) -> None:
        minimal = {
            "name": "my_tool",
            "parameters": {"type": "object", "properties": {}},
        }
        # To Anthropic
        anthropic_result = LLMClient._to_anthropic_tool(minimal)
        assert anthropic_result["name"] == "my_tool"
        assert "input_schema" in anthropic_result

        # To OpenAI
        openai_result = LLMClient._to_openai_tool(minimal)
        assert openai_result["type"] == "function"
        assert openai_result["function"]["name"] == "my_tool"


# -- Mock SDK responses --


def _mock_openai_response(
    content: str | None = None,
    tool_calls: list[dict] | None = None,
) -> MagicMock:
    """Create a mock OpenAI ChatCompletion response."""
    mock_message = MagicMock()
    mock_message.content = content

    if tool_calls:
        mock_tcs = []
        for tc in tool_calls:
            mock_tc = MagicMock()
            mock_tc.id = tc["id"]
            mock_tc.function.name = tc["name"]
            mock_tc.function.arguments = json.dumps(tc["arguments"])
            mock_tcs.append(mock_tc)
        mock_message.tool_calls = mock_tcs
    else:
        mock_message.tool_calls = None

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 100
    mock_usage.completion_tokens = 50
    mock_usage.total_tokens = 150

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage
    mock_response.model = "gpt-4o-mini"

    return mock_response


def _mock_anthropic_response(
    text: str | None = None,
    tool_uses: list[dict] | None = None,
) -> MagicMock:
    """Create a mock Anthropic Messages response."""
    blocks = []

    if text:
        text_block = MagicMock()
        text_block.text = text
        text_block.type = "text"
        blocks.append(text_block)

    if tool_uses:
        for tu in tool_uses:
            tool_block = MagicMock()
            tool_block.type = "tool_use"
            tool_block.id = tu["id"]
            tool_block.name = tu["name"]
            tool_block.input = tu["arguments"]
            # hasattr check for "text" must return False
            del tool_block.text
            blocks.append(tool_block)

    mock_usage = MagicMock()
    mock_usage.input_tokens = 120
    mock_usage.output_tokens = 60

    mock_response = MagicMock()
    mock_response.content = blocks
    mock_response.model = "claude-3-5-sonnet-20241022"
    mock_response.usage = mock_usage

    return mock_response


# -- Helpers for mocking lazy SDK imports --


def _fake_openai_module(mock_async_client: AsyncMock) -> MagicMock:
    """Create a fake 'openai' module for sys.modules patching."""
    mod = MagicMock()
    mod.AsyncOpenAI = MagicMock(return_value=mock_async_client)
    return mod


def _fake_anthropic_module(mock_async_client: AsyncMock) -> MagicMock:
    """Create a fake 'anthropic' module for sys.modules patching."""
    mod = MagicMock()
    mod.AsyncAnthropic = MagicMock(return_value=mock_async_client)
    return mod


# -- LLMClient.complete() tests --


class TestLLMClientCompleteOpenAI:
    @pytest.mark.anyio
    async def test_should_complete_text_only(self) -> None:
        client = LLMClient(LLMConfig(
            provider=LLMProvider.OPENAI,
            api_key="sk-test",
        ))

        mock_resp = _mock_openai_response(content="The weather in Berlin is 15C.")
        mock_async_client = AsyncMock()
        mock_async_client.chat.completions.create = AsyncMock(return_value=mock_resp)

        with patch.dict(sys.modules, {"openai": _fake_openai_module(mock_async_client)}):
            resp = await client.complete(SAMPLE_MESSAGES)

        assert resp.content == "The weather in Berlin is 15C."
        assert not resp.has_tool_calls
        assert resp.provider == LLMProvider.OPENAI
        assert resp.total_tokens == 150

    @pytest.mark.anyio
    async def test_should_complete_with_tool_calls(self) -> None:
        client = LLMClient(LLMConfig(
            provider=LLMProvider.OPENAI,
            api_key="sk-test",
        ))

        mock_resp = _mock_openai_response(
            content=None,
            tool_calls=[{
                "id": "call_abc",
                "name": "get_weather",
                "arguments": {"location": "Berlin", "unit": "celsius"},
            }],
        )
        mock_async_client = AsyncMock()
        mock_async_client.chat.completions.create = AsyncMock(return_value=mock_resp)

        with patch.dict(sys.modules, {"openai": _fake_openai_module(mock_async_client)}):
            resp = await client.complete(SAMPLE_MESSAGES, tools=SAMPLE_TOOLS)

        assert resp.has_tool_calls
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == "get_weather"
        assert resp.tool_calls[0].arguments["location"] == "Berlin"
        assert resp.content is None


class TestLLMClientCompleteAnthropic:
    @pytest.mark.anyio
    async def test_should_complete_text_only(self) -> None:
        client = LLMClient(LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            api_key="sk-ant-test",
        ))

        mock_resp = _mock_anthropic_response(text="Berlin is 15 degrees.")
        mock_async_client = AsyncMock()
        mock_async_client.messages.create = AsyncMock(return_value=mock_resp)

        with patch.dict(sys.modules, {"anthropic": _fake_anthropic_module(mock_async_client)}):
            resp = await client.complete(SAMPLE_MESSAGES)

        assert resp.content == "Berlin is 15 degrees."
        assert not resp.has_tool_calls
        assert resp.provider == LLMProvider.ANTHROPIC

    @pytest.mark.anyio
    async def test_should_complete_with_tool_calls(self) -> None:
        client = LLMClient(LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            api_key="sk-ant-test",
        ))

        mock_resp = _mock_anthropic_response(
            tool_uses=[{
                "id": "toolu_abc",
                "name": "get_weather",
                "arguments": {"location": "Berlin"},
            }],
        )
        mock_async_client = AsyncMock()
        mock_async_client.messages.create = AsyncMock(return_value=mock_resp)

        with patch.dict(sys.modules, {"anthropic": _fake_anthropic_module(mock_async_client)}):
            resp = await client.complete(
                SAMPLE_MESSAGES,
                tools=SAMPLE_TOOLS,
            )

        assert resp.has_tool_calls
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == "get_weather"
        assert resp.tool_calls[0].id == "toolu_abc"

    @pytest.mark.anyio
    async def test_should_separate_system_prompt(self) -> None:
        """Verify system messages are extracted for Anthropic API."""
        client = LLMClient(LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            api_key="sk-ant-test",
        ))

        mock_resp = _mock_anthropic_response(text="OK")
        mock_async_client = AsyncMock()
        mock_async_client.messages.create = AsyncMock(return_value=mock_resp)

        with patch.dict(sys.modules, {"anthropic": _fake_anthropic_module(mock_async_client)}):
            await client.complete(SAMPLE_MESSAGES)

        # Check that system was passed as kwarg, not in messages
        call_kwargs = mock_async_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == "You are a helpful assistant."
        for msg in call_kwargs["messages"]:
            assert msg["role"] != "system"


class TestLLMClientCompleteUnsupported:
    @pytest.mark.anyio
    async def test_should_raise_for_ollama(self) -> None:
        client = LLMClient(LLMConfig(
            provider=LLMProvider.OLLAMA,
            model="llama3.2",
        ))
        with pytest.raises(ValueError, match="complete\\(\\) not supported"):
            await client.complete(SAMPLE_MESSAGES)


# -- DynamicLLMClient.complete() tests --


class TestDynamicLLMClientComplete:
    @pytest.mark.anyio
    async def test_should_use_tier_selection(self) -> None:
        registry = DictRegistry([
            LLMEntry(
                id=1,
                name="Test Sonnet",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                tier=LLMTier.STANDARD,
                api_key="sk-ant-test",
            ),
        ])
        dynamic = DynamicLLMClient(registry)

        mock_resp = _mock_anthropic_response(text="Tier-based response")
        mock_async_client = AsyncMock()
        mock_async_client.messages.create = AsyncMock(return_value=mock_resp)

        with patch.dict(sys.modules, {"anthropic": _fake_anthropic_module(mock_async_client)}):
            resp = await dynamic.complete(
                messages=SAMPLE_MESSAGES,
                tier=LLMTier.STANDARD,
            )

        assert resp.content == "Tier-based response"
        assert resp.provider == LLMProvider.ANTHROPIC

    @pytest.mark.anyio
    async def test_should_pass_tools_through(self) -> None:
        registry = DictRegistry([
            LLMEntry(
                id=2,
                name="Test GPT",
                provider="openai",
                model="gpt-4o-mini",
                tier=LLMTier.STANDARD,
                api_key="sk-test",
            ),
        ])
        dynamic = DynamicLLMClient(registry)

        mock_resp = _mock_openai_response(
            tool_calls=[{
                "id": "call_xyz",
                "name": "get_weather",
                "arguments": {"location": "Munich"},
            }],
        )
        mock_async_client = AsyncMock()
        mock_async_client.chat.completions.create = AsyncMock(return_value=mock_resp)

        with patch.dict(sys.modules, {"openai": _fake_openai_module(mock_async_client)}):
            resp = await dynamic.complete(
                messages=SAMPLE_MESSAGES,
                tools=SAMPLE_TOOLS,
                tier=LLMTier.STANDARD,
            )

        assert resp.has_tool_calls
        assert resp.tool_calls[0].arguments["location"] == "Munich"
