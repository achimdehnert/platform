"""
Consolidated Tool Base
======================

Generische Basis-Klasse für das Dispatch-Pattern.
Ermöglicht die Konsolidierung vieler Einzel-Tools auf ein Meta-Tool pro Kategorie.

Beispiel:
    Statt 8 separater server_* Tools → 1 `server_manage` Tool mit action-Parameter.

Usage:
    class ServerTool(ConsolidatedTool):
        category = "server"
        description = "Manage Hetzner Cloud servers"
        
        @action("list", "List all servers")
        async def list_servers(self, label_selector: str | None = None) -> str:
            ...
        
        @action("create", "Create a new server", destructive=True)
        async def create_server(self, name: str, server_type: str = "cx22") -> str:
            ...

Author: BF Agent Team
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, ClassVar, get_type_hints

from pydantic import BaseModel, Field, create_model

logger = logging.getLogger(__name__)


# =============================================================================
# Action Registry Decorator
# =============================================================================


@dataclass
class ActionMeta:
    """Metadata für eine registrierte Action."""

    name: str
    description: str
    handler: Callable
    destructive: bool = False
    confirm_required: bool = False
    read_only: bool = False


def action(
    name: str,
    description: str,
    *,
    destructive: bool = False,
    confirm_required: bool | None = None,
    read_only: bool = False,
) -> Callable:
    """Decorator um eine Methode als Action zu registrieren.
    
    Args:
        name: Action-Name (z.B. "list", "create", "delete")
        description: Kurze Beschreibung für LLM
        destructive: Ist die Action destruktiv? (delete, reset, ...)
        confirm_required: Erfordert confirm=True? (default: True wenn destructive)
        read_only: Nur lesend? (für MCP Annotations)
    
    Example:
        @action("delete", "Delete a server", destructive=True)
        async def delete_server(self, server_id: str) -> str:
            ...
    """
    if confirm_required is None:
        confirm_required = destructive

    def decorator(func: Callable) -> Callable:
        func._action_meta = ActionMeta(
            name=name,
            description=description,
            handler=func,
            destructive=destructive,
            confirm_required=confirm_required,
            read_only=read_only,
        )
        return func

    return decorator


# =============================================================================
# Consolidated Tool Base Class
# =============================================================================


class ConsolidatedTool:
    """Basis-Klasse für konsolidierte MCP Tools.
    
    Sammelt alle @action-dekorierten Methoden und erzeugt daraus:
    1. Ein Pydantic InputSchema mit action-Enum + Union aller Parameter
    2. Einen Dispatcher der anhand der action zum richtigen Handler routet
    3. Eine Beschreibung die alle verfügbaren Actions auflistet
    
    Subclass-Attribute:
        category: Tool-Kategorie (z.B. "server", "docker", "database")
        description: Übergeordnete Beschreibung
    """

    category: ClassVar[str] = "base"
    description: ClassVar[str] = "Base consolidated tool"

    def __init__(self) -> None:
        self._actions: dict[str, ActionMeta] = {}
        self._collect_actions()

    def _collect_actions(self) -> None:
        """Sammle alle @action-dekorierten Methoden."""
        for name in dir(self):
            if name.startswith("_"):
                continue
            method = getattr(self, name, None)
            if method and hasattr(method, "_action_meta"):
                meta: ActionMeta = method._action_meta
                self._actions[meta.name] = ActionMeta(
                    name=meta.name,
                    description=meta.description,
                    handler=method,  # Bound method
                    destructive=meta.destructive,
                    confirm_required=meta.confirm_required,
                    read_only=meta.read_only,
                )

    @property
    def tool_name(self) -> str:
        """MCP Tool-Name: z.B. 'server_manage'."""
        return f"{self.category}_manage"

    @property
    def available_actions(self) -> list[str]:
        """Liste aller verfügbaren Actions."""
        return sorted(self._actions.keys())

    def get_tool_description(self) -> str:
        """Generiere die Tool-Beschreibung für das LLM.
        
        Format optimiert für LLM-Verständnis:
        - Kompakte Action-Liste
        - Parameter-Hinweise bei destruktiven Actions
        """
        lines = [f"{self.description}\n"]
        lines.append("Available actions:")

        for name in sorted(self._actions):
            meta = self._actions[name]
            prefix = "⚠️" if meta.destructive else "📖" if meta.read_only else "🔧"
            confirm_hint = " (requires confirm=true)" if meta.confirm_required else ""
            lines.append(f"  {prefix} {name}: {meta.description}{confirm_hint}")

        return "\n".join(lines)

    def build_input_schema(self) -> dict[str, Any]:
        """Generiere das JSON Schema für das konsolidierte Tool.
        
        Erzeugt ein Schema mit:
        - action: Enum aller verfügbaren Actions
        - Alle Parameter aller Actions als optionale Felder
        - confirm: Boolean für destruktive Actions
        """
        # Sammle alle Parameter aus allen Actions
        all_params: dict[str, dict[str, Any]] = {}
        required_by_action: dict[str, list[str]] = {}

        for action_name, meta in self._actions.items():
            sig = inspect.signature(meta.handler)
            hints = get_type_hints(meta.handler)
            action_required = []

            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue

                type_hint = hints.get(param_name, str)
                json_type = _python_type_to_json(type_hint)

                param_schema: dict[str, Any] = {"type": json_type}
                if param.default != inspect.Parameter.empty:
                    param_schema["default"] = param.default
                else:
                    action_required.append(param_name)

                # Merge: Wenn Parameter schon existiert, ergänze nur Beschreibung
                if param_name not in all_params:
                    all_params[param_name] = param_schema
                    
            required_by_action[action_name] = action_required

        # Action Enum
        action_enum = {
            "type": "string",
            "enum": sorted(self._actions.keys()),
            "description": "Action to perform. " + ", ".join(
                f"{name}: {meta.description}"
                for name, meta in sorted(self._actions.items())
            ),
        }

        # Confirm-Feld (für destruktive Actions)
        has_destructive = any(m.confirm_required for m in self._actions.values())

        properties: dict[str, Any] = {"action": action_enum}
        properties.update(all_params)

        if has_destructive:
            properties["confirm"] = {
                "type": "boolean",
                "default": False,
                "description": "Set to true to confirm destructive actions (delete, reset, etc.)",
            }

        return {
            "type": "object",
            "properties": properties,
            "required": ["action"],
        }

    async def dispatch(self, arguments: dict[str, Any]) -> str:
        """Dispatch einen Tool-Call zur richtigen Action.
        
        Args:
            arguments: Die vom LLM übergebenen Argumente (inkl. "action")
            
        Returns:
            Formatiertes Ergebnis als String
            
        Raises:
            ValueError: Bei unbekannter Action oder fehlendem confirm
        """
        action_name = arguments.get("action")
        if not action_name:
            return self._format_help()

        if action_name not in self._actions:
            return (
                f"❌ Unknown action: '{action_name}'\n\n"
                f"Available actions: {', '.join(self.available_actions)}"
            )

        meta = self._actions[action_name]

        # Confirm-Check für destruktive Actions
        if meta.confirm_required and not arguments.get("confirm", False):
            return (
                f"⚠️ Action '{action_name}' is destructive.\n"
                f"Set confirm=true to proceed."
            )

        # Argumente filtern (nur die, die der Handler erwartet)
        sig = inspect.signature(meta.handler)
        valid_params = {
            k: v
            for k, v in arguments.items()
            if k in sig.parameters and k not in ("self", "action", "confirm")
        }

        try:
            result = meta.handler(**valid_params)
            # Async Support
            if inspect.isawaitable(result):
                result = await result
            return str(result)
        except TypeError as e:
            # Fehlende Parameter
            return f"❌ Parameter error for '{action_name}': {e}"
        except Exception as e:
            logger.error(f"Error in {self.tool_name}.{action_name}: {e}", exc_info=True)
            return f"❌ Error: {e}"

    def _format_help(self) -> str:
        """Hilfe-Text wenn keine Action angegeben."""
        return (
            f"# {self.tool_name}\n\n"
            f"{self.get_tool_description()}\n\n"
            f"Usage: Provide 'action' parameter with one of: "
            f"{', '.join(self.available_actions)}"
        )


# =============================================================================
# Helpers
# =============================================================================


def _python_type_to_json(type_hint: type) -> str:
    """Konvertiere Python Type Hint zu JSON Schema Type."""
    # Handle Optional (Union[X, None])
    origin = getattr(type_hint, "__origin__", None)
    if origin is type(None):
        return "string"

    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }

    # Unwrap Optional
    args = getattr(type_hint, "__args__", None)
    if args and type(None) in args:
        real_type = next(a for a in args if a is not type(None))
        return type_map.get(real_type, "string")

    return type_map.get(type_hint, "string")
