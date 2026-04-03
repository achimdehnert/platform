#!/usr/bin/env python3
"""
fix_print_to_logging.py — Replaces print() with logging calls in Django code.

Rules:
- Adds `import logging` and `logger = logging.getLogger(__name__)` if missing
- print(f"...") → logger.info(...)
- print(f"Error...") / print(f"KRITISCH...") → logger.error(...)
- print(f"Warning...") / print(f"WARN...") → logger.warning(...)
- print(f"Debug...") → logger.debug(...)
- Skips manage.py, wsgi.py, asgi.py (Django entry points)
- Skips files in management/commands/ (management commands often use self.stdout)
- Dry-run by default (--apply to actually write)

Usage:
    python3 fix_print_to_logging.py /path/to/repo/apps/     # dry-run
    python3 fix_print_to_logging.py /path/to/repo/apps/ --apply
"""
import argparse
import os
import re
import sys

SKIP_FILES = {"manage.py", "wsgi.py", "asgi.py", "conftest.py"}
SKIP_DIRS = {"migrations", "__pycache__", ".venv", "node_modules", "tests", "test",
             "site-packages", "docs"}

ERROR_PATTERNS = re.compile(
    r"print\s*\(\s*f?[\"'].*(?:Error|FEHLER|KRITISCH|CRITICAL|Fehler|error:|ERROR)",
    re.IGNORECASE,
)
WARNING_PATTERNS = re.compile(
    r"print\s*\(\s*f?[\"'].*(?:Warning|WARN|Warnung|warning:|WARNUNG)",
    re.IGNORECASE,
)
DEBUG_PATTERNS = re.compile(
    r"print\s*\(\s*f?[\"'].*(?:Debug|DEBUG|debug:)",
    re.IGNORECASE,
)

# Match print(...) statements — simple single-line only
PRINT_RE = re.compile(r"^(\s*)print\s*\((.*)\)\s*$")


def should_skip_file(filepath: str) -> bool:
    basename = os.path.basename(filepath)
    if basename in SKIP_FILES:
        return True
    if "management/commands" in filepath:
        return True
    parts = filepath.split(os.sep)
    return any(d in SKIP_DIRS for d in parts)


def classify_print(line: str) -> str:
    if ERROR_PATTERNS.search(line):
        return "error"
    if WARNING_PATTERNS.search(line):
        return "warning"
    if DEBUG_PATTERNS.search(line):
        return "debug"
    return "info"


def has_logging_import(lines: list[str]) -> bool:
    for line in lines:
        if re.match(r"^import logging\b", line):
            return True
        if re.match(r"^from logging import", line):
            return True
    return False


def has_logger_definition(lines: list[str]) -> bool:
    for line in lines:
        if "getLogger(__name__)" in line:
            return True
    return False


def find_import_insert_pos(lines: list[str]) -> int:
    last_import = 0
    for i, line in enumerate(lines):
        if line and not line[0].isspace():
            if line.startswith(("import ", "from ")):
                last_import = i
    return last_import + 1


def process_file(filepath: str, apply: bool = False) -> dict:
    stats = {"file": filepath, "replacements": 0, "level_counts": {}}

    with open(filepath, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    original = lines[:]
    replacements = []

    for i, line in enumerate(lines):
        match = PRINT_RE.match(line)
        if not match:
            continue

        indent = match.group(1)
        content = match.group(2)
        level = classify_print(line)

        new_line = f"{indent}logger.{level}({content})\n"
        lines[i] = new_line
        replacements.append((i + 1, level, line.strip()))
        stats["level_counts"][level] = stats["level_counts"].get(level, 0) + 1

    if not replacements:
        return stats

    stats["replacements"] = len(replacements)

    # Add logging import + logger if needed
    needs_import = not has_logging_import(lines)
    needs_logger = not has_logger_definition(lines)

    if needs_import or needs_logger:
        insert_pos = find_import_insert_pos(lines)
        inserts = []
        if needs_import:
            inserts.append("import logging\n")
        if needs_logger:
            inserts.append("\nlogger = logging.getLogger(__name__)\n")
        for j, ins in enumerate(inserts):
            lines.insert(insert_pos + j, ins)

    if apply:
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)

    return stats


def scan_directory(directory: str, apply: bool = False) -> list[dict]:
    results = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            filepath = os.path.join(root, fname)
            if should_skip_file(filepath):
                continue
            stats = process_file(filepath, apply=apply)
            if stats["replacements"] > 0:
                results.append(stats)
    return results


def main():
    parser = argparse.ArgumentParser(description="Replace print() with logging calls")
    parser.add_argument("directory", help="Directory to scan")
    parser.add_argument("--apply", action="store_true", help="Actually write changes")
    args = parser.parse_args()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] Scanning {args.directory}...")

    results = scan_directory(args.directory, apply=args.apply)

    total = sum(r["replacements"] for r in results)
    print(f"\n{'=' * 60}")
    print(f"{'APPLIED' if args.apply else 'WOULD REPLACE'}: {total} print() → logger.X()")
    print(f"Files affected: {len(results)}")
    for r in results:
        short = r["file"].replace(os.path.expanduser("~/github/"), "")
        levels = ", ".join(f"{k}:{v}" for k, v in sorted(r["level_counts"].items()))
        print(f"  {short}: {r['replacements']} ({levels})")

    return 0 if total == 0 else (0 if args.apply else 1)


if __name__ == "__main__":
    sys.exit(main())
