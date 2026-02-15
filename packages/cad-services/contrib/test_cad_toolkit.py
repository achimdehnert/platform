"""Tests for CADToolkit (DomainToolkit interface).

Non-DB tests only — verifies toolkit interface, tool schemas,
and error handling without requiring Django database.
"""

from __future__ import annotations

import pytest

from apps.ifc.chat.toolkit import CAD_TOOLS, CADToolkit
from chat_agent import AgentContext


class TestCADToolkit:
    def test_should_have_correct_name(self) -> None:
        toolkit = CADToolkit()
        assert toolkit.name == "cad"

    def test_should_expose_all_tool_schemas(self) -> None:
        toolkit = CADToolkit()
        names = {
            t["function"]["name"]
            for t in toolkit.tool_schemas
        }
        expected = {
            "query_rooms",
            "query_walls",
            "query_windows",
            "aggregate_quantities",
        }
        assert names == expected

    def test_should_have_four_tools(self) -> None:
        assert len(CAD_TOOLS) == 4

    @pytest.mark.asyncio
    async def test_should_return_error_for_unknown_tool(
        self,
    ) -> None:
        toolkit = CADToolkit()
        ctx = AgentContext(
            session_id="test", tenant_id=None
        )
        result = await toolkit.execute(
            "nonexistent_tool", {}, ctx
        )
        assert not result.success
        assert "Unknown tool" in result.error

    def test_should_require_element_type_for_aggregate(
        self,
    ) -> None:
        schema = next(
            t for t in CAD_TOOLS
            if t["function"]["name"] == "aggregate_quantities"
        )
        required = schema["function"]["parameters"]["required"]
        assert "element_type" in required

    def test_should_have_valid_group_by_enum(self) -> None:
        schema = next(
            t for t in CAD_TOOLS
            if t["function"]["name"] == "aggregate_quantities"
        )
        props = schema["function"]["parameters"]["properties"]
        group_enum = props["group_by"]["enum"]
        assert "floor" in group_enum
        assert "material" in group_enum
