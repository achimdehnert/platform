#!/usr/bin/env python3
"""ADR-Fleet-Inventar -> JSON. Usage: adr_inventory.py <out.json>  (liest $GITHUB_DIR bzw. ~/github)
Konsumenten: /adr-fleet-audit Phase 0.1, adr_analyze.py."""

import json
import os
import re
import sys
import glob

GH_DIR = os.environ.get("GITHUB_DIR", os.path.expanduser("~/github"))
OUT = sys.argv[1]

FM_KEYS = (
    "status",
    "date",
    "supersedes",
    "superseded_by",
    "superseded-by",
    "impl",
    "implementation_status",
    "title",
)


def parse_frontmatter(text):
    fm = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
                if m and m.group(1).lower() in FM_KEYS:
                    fm[m.group(1).lower().replace("-", "_")] = (
                        m.group(2).strip().strip('"').strip("'")
                    )
    return fm


def first_heading(text):
    # Bevorzugt "# ADR-NNN:"-Heading — Dateien können Config-Blöcke mit eigenem H1
    # VOR dem eigentlichen Titel tragen (Realfall: ADR-161 Drift-Detector-Block).
    m = re.search(r"^#\s+(ADR-\d+.*)$", text, re.M) or re.search(
        r"^#\s+(.+)$", text, re.M
    )
    return m.group(1).strip() if m else ""


rows = []
for path in sorted(glob.glob(f"{GH_DIR}/*/docs/adr/*.md")):
    base = os.path.basename(path)
    if base == "INDEX.md":
        continue
    repo = path[len(GH_DIR) + 1 :].split("/")[0]
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError as e:
        rows.append({"repo": repo, "file": base, "error": str(e)})
        continue
    fm = parse_frontmatter(text)
    num = re.match(r"ADR-(\d+)", base)
    rows.append(
        {
            "repo": repo,
            "file": base,
            "num": int(num.group(1)) if num else None,
            "title": fm.get("title") or first_heading(text),
            "status": fm.get("status", ""),
            "date": fm.get("date", ""),
            "supersedes": fm.get("supersedes", ""),
            "superseded_by": fm.get("superseded_by", ""),
            "impl": fm.get("impl") or fm.get("implementation_status", ""),
            "has_fm": text.startswith("---"),
            "bytes": len(text),
            # MADR-Grundgerüst grob: Context/Decision/Consequences-artige Headings
            "madr": bool(re.search(r"^#{1,3}\s*(Context|Kontext)", text, re.M | re.I))
            and bool(
                re.search(r"^#{1,3}\s*(Decision|Entscheidung)", text, re.M | re.I)
            ),
            "template_rest": bool(
                re.search(r"\{\{|TODO: FILL|Lorem ipsum|<platzhalter>", text, re.I)
            ),
        }
    )

json.dump(rows, open(OUT, "w"), ensure_ascii=False, indent=1)
print(f"rows={len(rows)} repos={len(set(r['repo'] for r in rows))}")
