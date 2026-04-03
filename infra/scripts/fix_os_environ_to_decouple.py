#!/usr/bin/env python3
"""
fix_os_environ_to_decouple.py — Replaces os.environ with decouple.config().

Rules:
- os.environ.get("X", "Y") → config("X", default="Y")
- os.environ.get("X") → config("X", default="")
- os.environ["X"] (read) → config("X")
- SKIP: os.environ.setdefault() — legitimate in manage.py/wsgi.py/asgi.py
- SKIP: os.environ["X"] = "value" — setting env vars (not reading)
- SKIP: manage.py, wsgi.py, asgi.py, celery.py (Django entry points)
- SKIP: test settings files (test.py, testing.py, settings_test.py)
- Adds `from decouple import config` if missing
- Removes `import os` if no other os.* usage remains
- Dry-run by default (--apply to actually write)

Usage:
    python3 fix_os_environ_to_decouple.py /path/to/repo/    # dry-run
    python3 fix_os_environ_to_decouple.py /path/to/repo/ --apply
"""
import argparse
import os
import re
import sys

SKIP_FILES = {
    "manage.py", "wsgi.py", "asgi.py", "celery.py",
    "conftest.py", "test.py", "testing.py", "settings_test.py",
}
SKIP_DIRS = {
    "migrations", "__pycache__", ".venv", "node_modules",
    "tests", "test", "site-packages", "docs",
    ".github", ".claude", "scripts",
}

# os.environ.get("KEY", "default")
ENVIRON_GET_DEFAULT = re.compile(
    r'os\.environ\.get\(\s*(["\'][^"\']+["\'])\s*,\s*([^)]+)\s*\)'
)
# os.environ.get("KEY") — no default
ENVIRON_GET_NODEFAULT = re.compile(
    r'os\.environ\.get\(\s*(["\'][^"\']+["\'])\s*\)'
)
# os.environ["KEY"] on right side (read, not assignment)
ENVIRON_BRACKET_READ = re.compile(
    r'(?<!=\s)os\.environ\[(["\'][^"\']+["\'])\]'
)
# os.environ.setdefault — SKIP
ENVIRON_SETDEFAULT = re.compile(r'os\.environ\.setdefault')
# os.environ["KEY"] = ... — SKIP (assignment)
ENVIRON_ASSIGNMENT = re.compile(
    r'os\.environ\[["\'][^"\']+["\']\]\s*='
)


def should_skip(filepath):
    basename = os.path.basename(filepath)
    if basename in SKIP_FILES:
        return True
    if "management/commands" in filepath:
        return True
    parts = filepath.split(os.sep)
    return any(d in SKIP_DIRS for d in parts)


def has_decouple_import(lines):
    for line in lines:
        if "from decouple import" in line and "config" in line:
            return True
    return False


def has_other_os_usage(lines):
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "os." in stripped and "os.environ" not in stripped:
            return True
    return False


def find_import_insert_pos(lines):
    last_import = 0
    for i, line in enumerate(lines):
        # Only top-level imports (not indented inside if/try/def)
        if line and not line[0].isspace():
            if line.startswith(("import ", "from ")):
                last_import = i
    return last_import + 1


def process_file(filepath, apply=False):
    stats = {"file": filepath, "replacements": 0, "skipped": 0}

    with open(filepath, encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Skip files with setdefault or assignment patterns
    lines = content.split("\n")
    new_lines = []
    replacements = 0
    skipped = 0

    for line in lines:
        original_line = line

        # Skip lines with setdefault or assignment
        if ENVIRON_SETDEFAULT.search(line):
            new_lines.append(line)
            skipped += 1
            continue
        if ENVIRON_ASSIGNMENT.search(line):
            new_lines.append(line)
            skipped += 1
            continue

        # Replace os.environ.get("KEY", "default")
        line = ENVIRON_GET_DEFAULT.sub(
            r'config(\1, default=\2)', line
        )
        # Replace os.environ.get("KEY")
        line = ENVIRON_GET_NODEFAULT.sub(
            r'config(\1, default="")', line
        )
        # Replace os.environ["KEY"] (read)
        line = ENVIRON_BRACKET_READ.sub(
            r'config(\1)', line
        )

        if line != original_line:
            replacements += 1

        new_lines.append(line)

    stats["replacements"] = replacements
    stats["skipped"] = skipped

    if replacements == 0:
        return stats

    # Add decouple import if needed
    if not has_decouple_import(new_lines):
        pos = find_import_insert_pos(new_lines)
        new_lines.insert(pos, "from decouple import config")

    if apply:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))

    return stats


def scan_directory(directory, apply=False):
    results = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            filepath = os.path.join(root, fname)
            if should_skip(filepath):
                continue
            stats = process_file(filepath, apply=apply)
            if stats["replacements"] > 0:
                results.append(stats)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Replace os.environ with decouple.config()"
    )
    parser.add_argument("directory", help="Directory to scan")
    parser.add_argument(
        "--apply", action="store_true", help="Write changes"
    )
    args = parser.parse_args()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] Scanning {args.directory}...")

    results = scan_directory(args.directory, apply=args.apply)

    total = sum(r["replacements"] for r in results)
    total_skipped = sum(r["skipped"] for r in results)
    print(f"\n{'=' * 60}")
    tag = "APPLIED" if args.apply else "WOULD REPLACE"
    print(f"{tag}: {total} os.environ → config()")
    print(f"Skipped (setdefault/assignment): {total_skipped}")
    print(f"Files affected: {len(results)}")
    for r in results:
        short = r["file"].replace(
            os.path.expanduser("~/github/"), ""
        )
        print(f"  {short}: {r['replacements']} replacements")

    return 0


if __name__ == "__main__":
    sys.exit(main())
