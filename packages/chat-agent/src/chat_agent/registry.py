"""ToolkitRegistry — apps register DomainToolkits at startup.

Intended to be called from Django AppConfig.ready() or
equivalent startup hook.
"""

from __future__ import annotations

import logging
from typing import Any

from .toolkit import DomainToolkit

logger = logging.getLogger(__name__)

_registry: dict[str, DomainToolkit] = {}


def register(name: str, toolkit: DomainToolkit) -> None:
    """Register a DomainToolkit under a unique name.

    Args:
        name: Short identifier (e.g. 'cad', 'travel').
        toolkit: DomainToolkit instance.

    Raises:
        ValueError: If name is already registered.
    """
    if name in _registry:
        raise ValueError(
            f"Toolkit '{name}' already registered. "
            f"Use unregister() first."
        )
    _registry[name] = toolkit
    logger.info("Registered toolkit: %s", name)


def unregister(name: str) -> None:
    """Remove a toolkit from the registry."""
    _registry.pop(name, None)


def get(name: str) -> DomainToolkit:
    """Get a registered toolkit by name.

    Raises:
        KeyError: If toolkit not found.
    """
    if name not in _registry:
        available = ", ".join(_registry.keys()) or "(none)"
        raise KeyError(
            f"Toolkit '{name}' not found. "
            f"Available: {available}"
        )
    return _registry[name]


def list_registered() -> dict[str, DomainToolkit]:
    """Return all registered toolkits."""
    return dict(_registry)


def clear() -> None:
    """Clear all registered toolkits (for testing)."""
    _registry.clear()


def get_all_tool_schemas() -> list[dict[str, Any]]:
    """Collect tool schemas from all registered toolkits."""
    schemas: list[dict[str, Any]] = []
    for toolkit in _registry.values():
        schemas.extend(toolkit.tool_schemas)
    return schemas
