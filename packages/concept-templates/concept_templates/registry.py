"""Framework registry — register, retrieve and list concept frameworks."""

from __future__ import annotations

import logging
from copy import deepcopy

from concept_templates.schemas import ConceptScope, ConceptTemplate

logger = logging.getLogger(__name__)

# Module-level registry: framework_key → ConceptTemplate
_REGISTRY: dict[str, ConceptTemplate] = {}
_initialized: bool = False


def _ensure_builtins() -> None:
    """Lazy-load built-in frameworks on first access."""
    global _initialized  # noqa: PLW0603
    if _initialized:
        return
    from concept_templates.frameworks import BUILTIN_FRAMEWORKS

    for key, fw in BUILTIN_FRAMEWORKS.items():
        if key not in _REGISTRY:
            _REGISTRY[key] = fw
    _initialized = True


def register_framework(
    key: str,
    template: ConceptTemplate,
    *,
    overwrite: bool = False,
) -> None:
    """Register a concept framework.

    Args:
        key: Unique framework identifier (e.g. 'brandschutz_mbo').
        template: The ConceptTemplate defining the framework.
        overwrite: If True, replaces existing registration.

    Raises:
        ValueError: If key already registered and overwrite is False.
    """
    _ensure_builtins()
    if key in _REGISTRY and not overwrite:
        raise ValueError(
            f"Framework '{key}' already registered. "
            f"Use overwrite=True to replace."
        )
    _REGISTRY[key] = template
    logger.info("Framework registered: %s (%s)", key, template.name)


def unregister_framework(key: str) -> ConceptTemplate | None:
    """Remove a framework from the registry.

    Returns the removed template, or None if not found.
    """
    _ensure_builtins()
    removed = _REGISTRY.pop(key, None)
    if removed:
        logger.info("Framework unregistered: %s", key)
    return removed


def get_framework(key: str) -> ConceptTemplate:
    """Get a framework by key.

    Returns a deep copy to prevent mutation of the registry.

    Raises:
        KeyError: If framework not found.
    """
    _ensure_builtins()
    if key not in _REGISTRY:
        raise KeyError(
            f"Framework '{key}' not found. "
            f"Available: {', '.join(sorted(_REGISTRY.keys()))}"
        )
    return deepcopy(_REGISTRY[key])


def list_frameworks(
    scope: ConceptScope | str | None = None,
) -> dict[str, ConceptTemplate]:
    """List all registered frameworks, optionally filtered by scope.

    Returns deep copies.
    """
    _ensure_builtins()
    result = {}
    for key, fw in _REGISTRY.items():
        if scope is None or fw.scope == scope:
            result[key] = deepcopy(fw)
    return result


def clear_registry() -> None:
    """Clear all frameworks. Primarily for testing."""
    global _initialized  # noqa: PLW0603
    _REGISTRY.clear()
    _initialized = False
