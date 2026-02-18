"""Pre-commit hook for HTMX anti-pattern detection (ADR-048, AP-001..004).

Usage:
    python -m tools.check_htmx_patterns templates/**/*.html
    python -m tools.check_htmx_patterns --help

Skips:
    - Lines containing '{# noqa: AP-xxx #}' markers
    - Content inside {% comment %}...{% endcomment %} blocks
    - Content inside <!-- ... --> HTML comments
"""

import re
import sys
from pathlib import Path

PATTERNS: dict[str, tuple[str, str]] = {
    "AP-001": (
        r'hx-swap\s*=\s*"innerHTML"(?![^>]*hx-target)',
        "hx-swap='innerHTML' without hx-target",
    ),
    "AP-002": (
        r'<form[^>]*hx-boost\s*=\s*"true"',
        "hx-boost on <form> element",
    ),
    "AP-003": (
        r'onclick\s*=\s*"[^"]*"[^>]*hx-|hx-[^>]*onclick\s*=',
        "onclick combined with HTMX attribute",
    ),
    "AP-004": (
        r'style\s*=\s*"[^"]*(?:color|background|margin|padding)',
        "Inline style with layout/color property",
    ),
}


def _strip_comments(content: str) -> str:
    """Remove Django and HTML comments to avoid false positives."""
    content = re.sub(
        r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}",
        "",
        content,
        flags=re.DOTALL,
    )
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    return content


def check_file(path: Path) -> list[str]:
    """Check a single file for anti-patterns."""
    content = path.read_text(encoding="utf-8")
    content = _strip_comments(content)
    errors: list[str] = []

    for ap_id, (pattern, message) in PATTERNS.items():
        for match in re.finditer(
            pattern, content, re.DOTALL | re.IGNORECASE,
        ):
            line_start = content.rfind("\n", 0, match.start()) + 1
            line_end = content.find("\n", match.end())
            line = content[
                line_start:line_end if line_end != -1 else len(content)
            ]
            if f"noqa: {ap_id}" not in line and "noqa: AP-" not in line:
                errors.append(f"  {path}: {ap_id}: {message}")

    return errors


def main() -> int:
    """Entry point for pre-commit hook."""
    if "--help" in sys.argv:
        print(__doc__)
        return 0

    files = [Path(f) for f in sys.argv[1:] if f.endswith(".html")]
    all_errors: list[str] = []

    for f in files:
        if f.exists():
            all_errors.extend(check_file(f))

    if all_errors:
        print(f"HTMX Anti-Pattern violations ({len(all_errors)}):")
        for error in all_errors:
            print(error)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
