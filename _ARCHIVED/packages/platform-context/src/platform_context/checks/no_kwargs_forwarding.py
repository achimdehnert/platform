"""
platform_context/checks/no_kwargs_forwarding.py

Guardian-Regel: Kein blindes **kwargs-Forwarding in Adapter-Dateien.

Fix K2: Erweiterte Erkennung — deckt sowohl direkte als auch indirekte
**kwargs-Weitergabe ab:

  DIREKT (Original-Regex):
    return self._router.completion(messages=messages, **kwargs)

  INDIREKT (neu — Fix K2):
    result = self._router.completion(**kwargs)
    return result

  ZUWEISUNG (neu):
    response = self._provider.call(**kwargs)

ADR: ADR-155 §4.3
"""
from __future__ import annotations

import re
from pathlib import Path


# Fix K2: Erweiterte Patterns — erkennt direktes UND indirektes Forwarding
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "Direktes return-Forwarding",
        re.compile(
            r"return\s+self\._\w+\.\w+\([^)]*\*\*kwargs[^)]*\)",
            re.MULTILINE,
        ),
    ),
    (
        "Indirektes Forwarding via Zuweisung",
        re.compile(
            # Erkennt: result = self._x.method(..., **kwargs, ...)
            r"\w+\s*=\s*self\._\w+\.\w+\([^)]*\*\*kwargs[^)]*\)",
            re.MULTILINE,
        ),
    ),
    (
        "Reines **kwargs-Forwarding (gesamter Aufruf)",
        re.compile(
            # Erkennt: self._x.method(**kwargs) ohne andere Args
            r"self\._\w+\.\w+\(\*\*kwargs\)",
            re.MULTILINE,
        ),
    ),
]

# Erlaubte Ausnahmen (z.B. explizit dokumentiertes Forwarding mit Kommentar)
_ALLOWLIST_COMMENT = "# adr155-allow-kwargs"


def check(repo_path: Path) -> list[dict[str, str]]:
    """Prüft alle Adapter-Dateien auf blindes **kwargs-Forwarding.

    Returns:
        Liste von Violations als Dicts mit 'file', 'line', 'pattern', 'code'.
    """
    violations: list[dict[str, str]] = []

    adapter_files = list(repo_path.glob("apps/*/adapters/*.py"))
    if not adapter_files:
        return violations

    for adapter_file in adapter_files:
        content = adapter_file.read_text(encoding="utf-8")
        lines = content.splitlines()
        rel_path = str(adapter_file.relative_to(repo_path))

        for pattern_name, pattern in _PATTERNS:
            for match in pattern.finditer(content):
                # Zeilennummer ermitteln
                line_num = content[: match.start()].count("\n") + 1
                line_content = lines[line_num - 1].strip()

                # Allowlist-Kommentar prüfen
                if _ALLOWLIST_COMMENT in line_content:
                    continue

                # Auch die nachfolgende Zeile auf Allowlist prüfen
                if line_num < len(lines) and _ALLOWLIST_COMMENT in lines[line_num]:
                    continue

                violations.append({
                    "file": rel_path,
                    "line": str(line_num),
                    "pattern": pattern_name,
                    "code": line_content,
                    "message": (
                        f"{rel_path}:{line_num}: Blindes **kwargs-Forwarding "
                        f"({pattern_name}) verboten (ADR-155 §4.3). "
                        f"→ Parameter explizit mappen. "
                        f"Ausnahme: '{_ALLOWLIST_COMMENT}'-Kommentar setzen."
                    ),
                })

    return violations


def check_as_strings(repo_path: Path) -> list[str]:
    """Convenience-Wrapper der Violations als Strings zurückgibt."""
    return [v["message"] for v in check(repo_path)]


# ── CLI-Aufruf für GitHub Actions ────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    found = check(repo)

    if found:
        print(f"❌ ADR-155 Violation: {len(found)} **kwargs-Forwarding(s) gefunden:\n")
        for v in found:
            print(f"  {v['message']}")
        sys.exit(1)
    else:
        print("✓ ADR-155: Kein **kwargs-Forwarding in Adaptern gefunden.")
        sys.exit(0)
