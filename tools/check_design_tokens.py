"""Pre-commit hook for design token compliance (ADR-049).

Checks templates and CSS files for:
- Direct Tailwind color classes (bg-blue-500, text-red-600, etc.)
- Hardcoded hex colors in CSS/style attributes
- Suggests semantic token alternatives

Usage:
    python -m tools.check_design_tokens templates/**/*.html
    python -m tools.check_design_tokens --strict  # exit 1 on warnings too
"""

import re
import sys
from pathlib import Path

DIRECT_COLORS = re.compile(
    r"\b(?:bg|text|border)"
    r"-(?:blue|red|green|gray|amber|sky|purple)"
    r"-\d{2,3}\b"
)

HARDCODED_HEX = re.compile(
    r"(?:color|background|border-color)\s*:\s*#[0-9a-fA-F]{3,8}"
)

SEMANTIC_MAP: dict[str, str] = {
    # Primary
    "bg-blue-500": "bg-primary",
    "bg-blue-600": "bg-primary-hover",
    "text-blue-500": "text-primary",
    "text-blue-600": "text-primary",
    "border-blue-500": "border-primary",
    # Text
    "text-gray-900": "text-foreground",
    "text-gray-500": "text-muted",
    "text-gray-400": "text-muted",
    # Surfaces
    "bg-gray-50": "bg-surface-alt",
    "bg-gray-100": "bg-surface-alt",
    "bg-white": "bg-surface",
    # Status
    "bg-red-500": "bg-danger",
    "text-red-500": "text-danger",
    "text-red-600": "text-danger",
    "bg-green-500": "bg-success",
    "text-green-500": "text-success",
    "bg-amber-500": "bg-warning",
    "text-amber-500": "text-warning",
    # Borders
    "border-gray-200": "border-border",
    "border-gray-300": "border-border",
    "border-gray-500": "border-border-strong",
}


def check_file(path: Path) -> tuple[list[str], list[str]]:
    """Check a single file for token violations.

    Returns:
        Tuple of (errors, warnings).
    """
    content = path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []

    for match in DIRECT_COLORS.finditer(content):
        suggestion = SEMANTIC_MAP.get(match.group(), "a semantic token")
        warnings.append(
            f"  {path}: Direct color '{match.group()}'"
            f" -- use '{suggestion}' instead"
        )

    for match in HARDCODED_HEX.finditer(content):
        errors.append(
            f"  {path}: Hardcoded color '{match.group()}'"
            f" -- use --pui-* token"
        )

    return errors, warnings


def main() -> int:
    """Entry point for pre-commit hook."""
    if "--help" in sys.argv:
        print(__doc__)
        return 0

    strict = "--strict" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = [Path(f) for f in args]

    all_errors: list[str] = []
    all_warnings: list[str] = []

    for f in files:
        if f.exists() and f.suffix in (".html", ".css"):
            errors, warnings = check_file(f)
            all_errors.extend(errors)
            all_warnings.extend(warnings)

    if all_warnings:
        print(f"Design Token warnings ({len(all_warnings)}):")
        for w in all_warnings:
            print(w)

    if all_errors:
        print(f"Design Token errors ({len(all_errors)}):")
        for e in all_errors:
            print(e)

    if all_errors:
        return 1
    if strict and all_warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
