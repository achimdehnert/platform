#!/usr/bin/env python3
"""check_workflow_index.py — Vollständigkeits-Gate für den Workflow-Index.

Stellt sicher, dass **jeder** Skill unter `.windsurf/workflows/*.md` im zentralen
`workflow-index.md` als `/<name>` referenziert wird (K-44, repo-optimize Spec B / #901).
Ohne dieses Gate driftet der Index still: neue Skills bleiben unsichtbar, tote Verweise
fallen niemandem auf. Deterministisch, strukturell, keine LLM.

Exit 0  = jeder Skill ist indexiert (oder bewusst auf der Allowlist).
Exit 1  = mindestens ein Skill fehlt im Index (Fehlliste auf stdout).
Exit 2  = Nutzungs-/Pfadfehler.

Ein Skill `<name>` gilt als indexiert, wenn der Index den Slash-Command `/<name>`
enthält — mit Wortgrenze, damit `/adr` nicht fälschlich in `/adr-review` matcht.

Standardmäßig ausgenommen (immer, unabhängig von --allowlist):
- `workflow-index.md` selbst (der Index indexiert sich nicht selbst)
- Workflows mit Frontmatter `distribute: false` (interne System-Prompts, keine
  Slash-Commands — sie werden nicht verteilt und brauchen keinen Index-Eintrag)

Zusätzliche bewusst nicht-indexierte Skills via `--allowlist name1,name2`.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

DISTRIBUTE_FALSE = re.compile(r"^distribute:\s*false\b", re.MULTILINE)


def _default_root() -> str:
    # tools/check_workflow_index.py -> repo root ist ein Verzeichnis höher.
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(here)


def is_distribute_false(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            head = fh.read(4096)
    except OSError:
        return False
    return bool(DISTRIBUTE_FALSE.search(head))


def command_indexed(name: str, index_text: str) -> bool:
    """True, wenn /<name> im Index steht — mit Wortgrenze (kein - oder \\w danach)."""
    pattern = re.compile(r"/" + re.escape(name) + r"(?![\w-])")
    return bool(pattern.search(index_text))


def check(
    workflows_dir: str,
    index_path: str,
    allowlist: set[str],
) -> tuple[list[str], list[str]]:
    """Gibt (missing, checked_names) zurück."""
    if not os.path.isdir(workflows_dir):
        raise FileNotFoundError(f"workflows dir not found: {workflows_dir}")
    if not os.path.isfile(index_path):
        raise FileNotFoundError(f"index not found: {index_path}")

    with open(index_path, "r", encoding="utf-8") as fh:
        index_text = fh.read()

    index_name = os.path.splitext(os.path.basename(index_path))[0]

    missing: list[str] = []
    checked: list[str] = []
    for fname in sorted(os.listdir(workflows_dir)):
        if not fname.endswith(".md"):
            continue
        name = fname[:-3]
        if name == index_name:
            continue
        if name in allowlist:
            continue
        if is_distribute_false(os.path.join(workflows_dir, fname)):
            continue
        checked.append(name)
        if not command_indexed(name, index_text):
            missing.append(name)
    return missing, checked


def main(argv: list[str] | None = None) -> int:
    root = _default_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workflows-dir",
        default=os.path.join(root, ".windsurf", "workflows"),
        help="Verzeichnis mit den Workflow-*.md (Default: <repo>/.windsurf/workflows)",
    )
    parser.add_argument(
        "--index",
        default=os.path.join(root, ".windsurf", "workflows", "workflow-index.md"),
        help="Pfad zur workflow-index.md",
    )
    parser.add_argument(
        "--allowlist",
        default="onboard-repo-testing-addendum",
        help="Kommagetrennte Skill-Namen, die bewusst NICHT indexiert sein müssen.",
    )
    args = parser.parse_args(argv)

    allowlist = {n.strip() for n in args.allowlist.split(",") if n.strip()}

    try:
        missing, checked = check(args.workflows_dir, args.index, allowlist)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if missing:
        print("FAIL: folgende Skills fehlen im workflow-index.md (als /<name>):")
        for name in missing:
            print(f"  - {name}")
        print(
            f"\n{len(missing)} von {len(checked)} geprüften Skills fehlen. "
            "Zeile in der Trigger-Matrix ergänzen oder --allowlist erweitern."
        )
        return 1

    print(f"OK: alle {len(checked)} verteilten Skills sind im workflow-index.md referenziert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
