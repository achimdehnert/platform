"""Deep merge utility for Hub DNA inheritance."""

from __future__ import annotations

from typing import Any


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively merge override into base. Override wins on conflicts.

    - Dicts are merged recursively
    - Lists are replaced (not appended)
    - Scalars are replaced
    - Keys starting with '_' in override are ignored (metadata)
    """
    result = base.copy()
    for key, value in override.items():
        if key.startswith("_"):
            continue
        if key == "extends":
            continue
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
