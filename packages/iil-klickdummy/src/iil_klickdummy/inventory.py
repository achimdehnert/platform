"""S11 Cross-Repo Legacy-Class-Inventur (platform:ADR-211 Rev 12 §Migration).

Sucht nach Rev-≤10-Klassen-Begriffen (`mock-prototyp`, `demo-render`) in
allen bekannten Klickdummy-Repos. Exit 0 wenn 0 echte Treffer ⇒ Strict-Mode
(`LEGACY={}`) kann aktiviert werden.

Verwendung:
    python -m iil_klickdummy.inventory                # default-Repos
    python -m iil_klickdummy.inventory --base ~/github --repos meiki-hub,...
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

DEFAULT_REPOS = ["meiki-hub", "writing-hub", "risk-hub", "pptx-hub", "dev-hub", "ttz-hub"]
LEGACY_PATTERN = re.compile(r"mock-prototyp|demo-render")
INCLUDE_EXT = {".yaml", ".yml", ".json", ".md", ".html", ".py"}
EXCLUDE_PATH_PARTS = {"node_modules", ".venv", "__pycache__", "build", "dist", "_archiv"}
# Diese Pfade enthalten *beabsichtigte* History/Compat-Referenzen:
EXCLUDE_FILES_SUFFIX = ("feedback-log.md",)
# Zeilen, die LEGACY-Maps oder History-Kommentare definieren, sind kein Drift:
INTENTIONAL_LINE_PATTERNS = [
    re.compile(r'LEGACY\s*=\s*\{'),
    re.compile(r'"mock-prototyp"\s*:\s*"mock"'),
    re.compile(r'"demo-render"\s*:\s*"spec-demo"'),
    re.compile(r'#\s*vorher\s+(mock-prototyp|demo-render)'),
    re.compile(r'\(vorher\s+(mock-prototyp|demo-render)'),
    re.compile(r'in\s+\("mock",\s*"mock-prototyp"\)'),
    re.compile(r'in\s+\("demo-render",\s*"spec-demo"\)'),
]


def _is_intentional(line: str) -> bool:
    return any(p.search(line) for p in INTENTIONAL_LINE_PATTERNS)


def _scan_repo(repo_root: pathlib.Path) -> list[tuple[str, int, str]]:
    """Returns list of (relative_path, line_number, line_content) for real drift."""
    hits: list[tuple[str, int, str]] = []
    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix not in INCLUDE_EXT:
            continue
        if any(part in EXCLUDE_PATH_PARTS for part in p.parts):
            continue
        if p.name.endswith(EXCLUDE_FILES_SUFFIX):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if LEGACY_PATTERN.search(line) and not _is_intentional(line):
                hits.append((str(p.relative_to(repo_root)), i, line.strip()))
    return hits


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=os.path.expanduser("~/github"),
                        help="Base directory containing repo checkouts")
    parser.add_argument("--repos", default=",".join(DEFAULT_REPOS),
                        help="Comma-separated repo names")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 on first hit (default: report all then exit)")
    args = parser.parse_args(argv)

    base = pathlib.Path(args.base)
    repos = [r.strip() for r in args.repos.split(",") if r.strip()]

    print("== S11 Cross-Repo Legacy-Class-Inventur (platform:ADR-211 Rev 12) ==")
    print(f"Base: {base}")
    print(f"Repos: {', '.join(repos)}")
    print()

    total = 0
    for repo in repos:
        d = base / repo
        if not d.exists():
            print(f"=== {repo}: NOT PRESENT (skip) ===")
            continue
        hits = _scan_repo(d)
        if hits:
            print(f"=== {repo}: {len(hits)} echte Drift-Treffer ===")
            for rel, ln, content in hits[:10]:
                print(f"  {rel}:{ln}  {content[:120]}")
            if len(hits) > 10:
                print(f"  … und {len(hits) - 10} weitere")
            total += len(hits)
            if args.strict:
                return 1
        else:
            print(f"=== {repo}: ✓ clean ===")

    print()
    if total == 0:
        print("S11 → 0 echte Drift-Treffer cross-repo. Strict-Mode kann aktiviert werden.")
        return 0
    else:
        print(f"S11 → {total} Treffer. Strict-Mode noch nicht möglich.")
        return 1


def main_cli() -> int:
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main_cli())
