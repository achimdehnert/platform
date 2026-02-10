"""
Tests: Tool Consolidation Pattern
==================================

Testet:
1. Action-Registry und Decorator
2. Schema-Generierung
3. Dispatch (happy path + error cases)
4. Confirm-Check für destruktive Actions
5. Hetzner Server Tool konkret

pytest tests/
"""

import pytest
import asyncio
from typing import Optional

from tool_consolidation.base import ConsolidatedTool, action, ActionMeta


# =============================================================================
# Test-Fixtures: Minimale ConsolidatedTool Subclass
# =============================================================================


class DemoTool(ConsolidatedTool):
    """Minimales Test-Tool."""

    category = "demo"
    description = "Demo tool for testing"

    @action("list", "List all items", read_only=True)
    async def list_items(self, tag: Optional[str] = None) -> str:
        if tag:
            return f"Items with tag={tag}"
        return "All items"

    @action("create", "Create a new item")
    async def create_item(self, name: str, count: int = 1) -> str:
        return f"Created: {name} (x{count})"

    @action("delete", "Delete an item permanently", destructive=True)
    async def delete_item(self, item_id: str) -> str:
        return f"Deleted: {item_id}"

    @action("reset", "Reset everything", destructive=True, confirm_required=True)
    async def reset_all(self) -> str:
        return "Reset complete"


@pytest.fixture
def demo_tool():
    return DemoTool()


# =============================================================================
# Test: Action Registry
# =============================================================================


class TestActionRegistry:
    """Teste @action Decorator und Sammlung."""

    def test_actions_collected(self, demo_tool):
        """Alle @action-Methoden werden gesammelt."""
        assert set(demo_tool.available_actions) == {"list", "create", "delete", "reset"}

    def test_action_metadata(self, demo_tool):
        """ActionMeta enthält korrekte Werte."""
        list_meta = demo_tool._actions["list"]
        assert list_meta.name == "list"
        assert list_meta.description == "List all items"
        assert list_meta.read_only is True
        assert list_meta.destructive is False

    def test_destructive_flag(self, demo_tool):
        """Destruktive Actions werden korrekt markiert."""
        delete_meta = demo_tool._actions["delete"]
        assert delete_meta.destructive is True
        assert delete_meta.confirm_required is True  # Auto-set

    def test_tool_name(self, demo_tool):
        """Tool-Name wird korrekt generiert."""
        assert demo_tool.tool_name == "demo_manage"


# =============================================================================
# Test: Schema Generation
# =============================================================================


class TestSchemaGeneration:
    """Teste Input-Schema Generierung."""

    def test_schema_has_action_enum(self, demo_tool):
        """Schema enthält action-Feld mit Enum."""
        schema = demo_tool.build_input_schema()
        assert "action" in schema["properties"]
        action_prop = schema["properties"]["action"]
        assert action_prop["type"] == "string"
        assert set(action_prop["enum"]) == {"list", "create", "delete", "reset"}

    def test_schema_has_confirm(self, demo_tool):
        """Schema enthält confirm-Feld (wegen destruktiver Actions)."""
        schema = demo_tool.build_input_schema()
        assert "confirm" in schema["properties"]
        assert schema["properties"]["confirm"]["type"] == "boolean"
        assert schema["properties"]["confirm"]["default"] is False

    def test_schema_collects_all_params(self, demo_tool):
        """Alle Parameter aller Actions sind im Schema."""
        schema = demo_tool.build_input_schema()
        props = schema["properties"]
        # Von list_items
        assert "tag" in props
        # Von create_item
        assert "name" in props
        assert "count" in props
        # Von delete_item
        assert "item_id" in props

    def test_schema_only_action_required(self, demo_tool):
        """Nur 'action' ist required auf Top-Level."""
        schema = demo_tool.build_input_schema()
        assert schema["required"] == ["action"]

    def test_schema_param_types(self, demo_tool):
        """Parameter-Typen werden korrekt konvertiert."""
        schema = demo_tool.build_input_schema()
        assert schema["properties"]["count"]["type"] == "integer"
        assert schema["properties"]["name"]["type"] == "string"


# =============================================================================
# Test: Dispatch
# =============================================================================


class TestDispatch:
    """Teste den Action-Dispatcher."""

    @pytest.mark.asyncio
    async def test_dispatch_read_only(self, demo_tool):
        """Read-only Action wird korrekt dispatched."""
        result = await demo_tool.dispatch({"action": "list"})
        assert "All items" in result

    @pytest.mark.asyncio
    async def test_dispatch_with_params(self, demo_tool):
        """Action mit Parametern wird korrekt dispatched."""
        result = await demo_tool.dispatch({"action": "list", "tag": "production"})
        assert "tag=production" in result

    @pytest.mark.asyncio
    async def test_dispatch_create(self, demo_tool):
        """Create-Action mit required + optional Params."""
        result = await demo_tool.dispatch({"action": "create", "name": "test-server"})
        assert "Created: test-server (x1)" in result

    @pytest.mark.asyncio
    async def test_dispatch_create_with_count(self, demo_tool):
        """Create mit explizitem count."""
        result = await demo_tool.dispatch({
            "action": "create", "name": "batch", "count": 5
        })
        assert "Created: batch (x5)" in result

    @pytest.mark.asyncio
    async def test_dispatch_unknown_action(self, demo_tool):
        """Unbekannte Action gibt Hilfe-Text."""
        result = await demo_tool.dispatch({"action": "fly_to_moon"})
        assert "Unknown action" in result
        assert "list" in result  # Zeigt verfügbare Actions

    @pytest.mark.asyncio
    async def test_dispatch_no_action(self, demo_tool):
        """Ohne action wird Help angezeigt."""
        result = await demo_tool.dispatch({})
        assert "demo_manage" in result
        assert "Available actions" in result


# =============================================================================
# Test: Confirm Check
# =============================================================================


class TestConfirmCheck:
    """Teste Confirm-Mechanismus für destruktive Actions."""

    @pytest.mark.asyncio
    async def test_destructive_without_confirm_blocked(self, demo_tool):
        """Destruktive Action ohne confirm wird geblockt."""
        result = await demo_tool.dispatch({
            "action": "delete", "item_id": "server-1"
        })
        assert "destructive" in result.lower()
        assert "confirm=true" in result.lower()

    @pytest.mark.asyncio
    async def test_destructive_with_confirm_passes(self, demo_tool):
        """Destruktive Action mit confirm=True wird ausgeführt."""
        result = await demo_tool.dispatch({
            "action": "delete", "item_id": "server-1", "confirm": True
        })
        assert "Deleted: server-1" in result

    @pytest.mark.asyncio
    async def test_reset_without_confirm_blocked(self, demo_tool):
        """Reset ohne confirm wird geblockt."""
        result = await demo_tool.dispatch({"action": "reset"})
        assert "destructive" in result.lower()

    @pytest.mark.asyncio
    async def test_reset_with_confirm_passes(self, demo_tool):
        """Reset mit confirm wird ausgeführt."""
        result = await demo_tool.dispatch({"action": "reset", "confirm": True})
        assert "Reset complete" in result

    @pytest.mark.asyncio
    async def test_non_destructive_no_confirm_needed(self, demo_tool):
        """Nicht-destruktive Actions brauchen kein confirm."""
        result = await demo_tool.dispatch({
            "action": "create", "name": "safe-item"
        })
        assert "Created" in result  # Kein Confirm nötig


# =============================================================================
# Test: Tool Description
# =============================================================================


class TestToolDescription:
    """Teste generierte Tool-Beschreibung."""

    def test_description_lists_all_actions(self, demo_tool):
        """Beschreibung listet alle Actions."""
        desc = demo_tool.get_tool_description()
        assert "list:" in desc
        assert "create:" in desc
        assert "delete:" in desc
        assert "reset:" in desc

    def test_description_marks_destructive(self, demo_tool):
        """Destruktive Actions werden mit ⚠️ markiert."""
        desc = demo_tool.get_tool_description()
        assert "⚠️" in desc  # Für delete und reset

    def test_description_marks_readonly(self, demo_tool):
        """Read-only Actions werden mit 📖 markiert."""
        desc = demo_tool.get_tool_description()
        assert "📖" in desc  # Für list

    def test_description_shows_confirm_hint(self, demo_tool):
        """confirm-Hinweis bei destruktiven Actions."""
        desc = demo_tool.get_tool_description()
        assert "confirm=true" in desc.lower()


# =============================================================================
# Test: HetznerServerTool
# =============================================================================


class TestHetznerServerTool:
    """Teste konkretes Hetzner Server Tool."""

    @pytest.fixture
    def server_tool(self):
        from tool_consolidation.hetzner_server import HetznerServerTool
        return HetznerServerTool()  # Ohne Client → Demo-Mode

    def test_has_expected_actions(self, server_tool):
        """Hat alle erwarteten Server-Actions."""
        expected = {"list", "status", "power", "create", "delete", "resize", "rebuild", "rename"}
        assert set(server_tool.available_actions) == expected

    def test_tool_name(self, server_tool):
        """Tool-Name ist server_manage."""
        assert server_tool.tool_name == "server_manage"

    @pytest.mark.asyncio
    async def test_list_servers_demo(self, server_tool):
        """List funktioniert im Demo-Mode."""
        result = await server_tool.dispatch({"action": "list"})
        assert "Demo" in result

    @pytest.mark.asyncio
    async def test_create_server_demo(self, server_tool):
        """Create zeigt Demo-Output."""
        result = await server_tool.dispatch({
            "action": "create",
            "server_name": "test-01",
            "server_type": "cx32",
        })
        assert "test-01" in result
        assert "cx32" in result

    @pytest.mark.asyncio
    async def test_delete_requires_confirm(self, server_tool):
        """Delete erfordert confirm."""
        result = await server_tool.dispatch({
            "action": "delete", "server_name": "test-01"
        })
        assert "confirm=true" in result.lower()

    @pytest.mark.asyncio
    async def test_delete_with_confirm(self, server_tool):
        """Delete mit confirm funktioniert."""
        result = await server_tool.dispatch({
            "action": "delete", "server_name": "test-01", "confirm": True
        })
        assert "Demo" in result
        assert "delete" in result.lower()

    @pytest.mark.asyncio
    async def test_rebuild_is_destructive(self, server_tool):
        """Rebuild ist destruktiv und braucht confirm."""
        result = await server_tool.dispatch({
            "action": "rebuild", "server_name": "test-01"
        })
        assert "destructive" in result.lower()

    def test_schema_generation(self, server_tool):
        """Schema wird korrekt generiert."""
        schema = server_tool.build_input_schema()
        assert schema["required"] == ["action"]
        actions = schema["properties"]["action"]["enum"]
        assert "list" in actions
        assert "delete" in actions
        assert len(actions) == 8

    def test_reduction_ratio(self, server_tool):
        """Reduktionsverhältnis: 8 Actions → 1 Tool."""
        assert len(server_tool.available_actions) == 8
        # Windsurf sieht: 1 Tool statt 8
        print(f"\n📊 Reduction: {len(server_tool.available_actions)} actions → 1 MCP tool")


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Teste Randfälle und Fehlerbehandlung."""

    @pytest.mark.asyncio
    async def test_extra_params_ignored(self, demo_tool):
        """Unbekannte Parameter werden ignoriert."""
        result = await demo_tool.dispatch({
            "action": "list",
            "nonexistent_param": "whatever",
        })
        assert "All items" in result

    @pytest.mark.asyncio
    async def test_missing_required_param_error(self, demo_tool):
        """Fehlender required Parameter gibt Fehler."""
        result = await demo_tool.dispatch({
            "action": "create",
            # 'name' fehlt!
        })
        assert "error" in result.lower() or "Parameter" in result

    @pytest.mark.asyncio
    async def test_confirm_false_explicit(self, demo_tool):
        """confirm=False wird korrekt als False behandelt."""
        result = await demo_tool.dispatch({
            "action": "delete", "item_id": "x", "confirm": False
        })
        assert "destructive" in result.lower()
