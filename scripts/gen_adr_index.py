#!/usr/bin/env python3
"""gen_adr_index.py — ADR-Frontmatter → index.json + INDEX.md (ADR-234 P0 / Issue #736).

Reads all docs/adr/ADR-*.md files, parses YAML frontmatter, and emits:
  - docs/adr/index.json  — machine-readable index with backward refs
  - docs/adr/INDEX.md    — human-readable table (replaces hand-maintained file)

Run: python3 scripts/gen_adr_index.py [--adr-dir docs/adr] [--root .]
CI:  python3 scripts/gen_adr_index.py && git diff --exit-code docs/adr/index.json docs/adr/INDEX.md

Design decisions:
- INDEX.md only contains ACTIVE ADRs (direct children of docs/adr/), not archived ones.
  adr_index_check.py only flags missing_row for active ADRs; including archived ones
  with different status would cause false status_drift findings.
- next_free is computed from active ADR numbers only (archive may have high historical numbers).
- index.json contains all ADRs (active + archived), deduplicated by number (active wins).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

# --- frontmatter parsing (stdlib only) ---

FRONT_RE = re.compile(r"^\s*---\n(.*?)\n---", re.DOTALL)
NUM_RE = re.compile(r"^ADR-(\d{3})\b")
H1_RE = re.compile(r"^#\s+(.+)", re.MULTILINE)

IMPL_EMOJI = {
    "implemented": "✅",
    "verified": "✅✅",
    "in_progress": "🔶",
    "in-progress": "🔶",
    "partial": "🔶",
    "none": "⬜",
    "": "⬜",
}
NO_IMPL_STATUSES = {"deprecated", "superseded", "archived"}


def _parse_yaml_value(val: str):
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1]
        return [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()]
    if val.lower() in ("true", "yes"):
        return True
    if val.lower() in ("false", "no"):
        return False
    return val.strip('"').strip("'")


def _parse_front(text: str) -> dict:
    """Extract YAML frontmatter as a flat dict; supports simple lists and scalars."""
    m = FRONT_RE.match(text)
    if not m:
        return {}
    block = m.group(1)
    result: dict = {}
    current_key: str | None = None
    list_items: list[str] = []
    for line in block.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line.startswith("  - ") or line.startswith("- "):
            item = line.lstrip().lstrip("- ").strip().strip('"').strip("'")
            if current_key:
                list_items.append(item)
            continue
        if ":" in line and not line.startswith(" "):
            if current_key and list_items:
                result[current_key] = list_items
            list_items = []
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            current_key = key
            if val:
                result[key] = _parse_yaml_value(val)
        # nested keys (e.g. scope.include_paths) — skip gracefully
    if current_key and list_items:
        result[current_key] = list_items
    return result


def _as_list(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if x]
    s = str(v).strip()
    return [s] if s else []


def _norm_status(s: str) -> str:
    return s.strip().lower()


def _impl_emoji(status: str, impl: str) -> str:
    if _norm_status(status) in NO_IMPL_STATUSES:
        return "—"
    return IMPL_EMOJI.get(impl.strip().lower(), "⬜")


def _extract_title(front: dict, body: str) -> str:
    if "title" in front and str(front["title"]).strip():
        return str(front["title"]).strip().strip('"').strip("'")
    m = H1_RE.search(body)
    if m:
        raw = m.group(1).strip()
        raw = re.sub(r"^ADR-\d{3}[:\s]+", "", raw)
        return raw.strip()
    return ""


def _extract_date(front: dict) -> str:
    for k in ("date", "decision_date", "decision-date"):
        v = front.get(k)
        if v:
            return str(v).strip()
    return ""


def _extract_related(front: dict) -> list[str]:
    combined = set()
    for k in ("related", "relates_to", "depends_on"):
        combined.update(_as_list(front.get(k)))
    return sorted(combined)


def _parse_file(f: Path, is_archived: bool) -> dict | None:
    """Parse a single ADR file into a record dict."""
    nm = NUM_RE.match(f.name)
    if not nm:
        return None
    number = int(nm.group(1))
    text = f.read_text(encoding="utf-8", errors="replace")
    front = _parse_front(text)
    status_raw = str(front.get("status", "")).strip()
    if is_archived and not status_raw:
        status_raw = "archived"
    impl_raw = str(front.get("implementation_status", "")).strip()
    return {
        "number": number,
        "id": f"ADR-{number:03d}",
        "file": f.name,
        "title": _extract_title(front, text),
        "status": status_raw,
        "date": _extract_date(front),
        "domains": _as_list(front.get("domains")),
        "supersedes": _as_list(front.get("supersedes")),
        "superseded_by": [],
        "amends": _as_list(front.get("amends")),
        "amended_by": [],
        "related": _extract_related(front),
        "implementation_status": impl_raw,
        "_impl_emoji": _impl_emoji(status_raw, impl_raw),
        "_is_archived": is_archived,
    }


def scan_adrs(adr_dir: Path) -> tuple[list[dict], list[dict]]:
    """Return (active_records, archived_records), each sorted by number.

    Active = direct children of adr_dir named ADR-NNN-*.md.
    Archived = ADR-NNN-*.md under _archive/ or archive/ subdirs.
    """
    active = []
    for f in sorted(adr_dir.glob("ADR-*.md")):
        r = _parse_file(f, is_archived=False)
        if r:
            active.append(r)
    active.sort(key=lambda r: r["number"])

    archived = []
    for sub in ("_archive", "archive"):
        d = adr_dir / sub
        if d.is_dir():
            for f in sorted(d.rglob("ADR-*.md")):
                r = _parse_file(f, is_archived=True)
                if r:
                    archived.append(r)
    archived.sort(key=lambda r: r["number"])

    return active, archived


def build_backward_refs(records: list[dict]) -> None:
    num_map = {r["id"]: r for r in records}
    for r in records:
        for sid in r["supersedes"]:
            t = num_map.get(sid)
            if t and r["id"] not in t["superseded_by"]:
                t["superseded_by"].append(r["id"])
        for aid in r["amends"]:
            t = num_map.get(aid)
            if t and r["id"] not in t["amended_by"]:
                t["amended_by"].append(r["id"])


def write_json(active: list[dict], archived: list[dict], out_path: Path) -> None:
    today = date.today().isoformat()
    nums = [r["number"] for r in active]
    next_free = (max(nums) + 1) if nums else 1

    # Merge: active wins on duplicate number
    active_nums = {r["number"] for r in active}
    merged = active + [r for r in archived if r["number"] not in active_nums]
    merged.sort(key=lambda r: r["number"])

    export = [{k: v for k, v in r.items() if not k.startswith("_")} for r in merged]

    doc = {
        "generated": today,
        "total": len(active),
        "next_free": next_free,
        "adrs": export,
    }
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_index_md(active: list[dict], out_path: Path) -> None:
    today = date.today().isoformat()
    nums = [r["number"] for r in active]
    next_free = (max(nums) + 1) if nums else 1

    lines = [
        "<!-- AUTO-GENERATED by scripts/gen_adr_index.py — do not edit manually -->",
        f"<!-- Last generated: {today} · Next free ADR number: **{next_free}** -->",
        "",
        "# Architecture Decision Records — Index",
        "",
        f"> **Next free ADR number:** {next_free}  ",
        f"> Auto-generated {today} from ADR frontmatter — edit ADR files, not this file.",
        "",
        "## Legend",
        "",
        "| Impl | Meaning |",
        "|------|---------|",
        "| ⬜ | `none` — not started |",
        "| 🔶 | `in_progress` / `partial` |",
        "| ✅ | `implemented` |",
        "| ✅✅ | `verified` in production |",
        "| — | not applicable (deprecated/superseded/archived) |",
        "",
        "## All ADRs",
        "",
        "| ADR# | Title | Status | Impl | Link |",
        "|------|-------|--------|------|------|",
    ]

    for r in active:
        num = f"{r['number']:03d}"
        title = r["title"] or f"ADR-{num}"
        status = r["status"].capitalize() if r["status"] else "—"
        impl = r["_impl_emoji"]
        link = f"[ADR-{num}]({r['file']})"
        lines.append(f"| {num} | {title} | {status} | {impl} | {link} |")

    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate ADR index.json + INDEX.md")
    ap.add_argument("--adr-dir", default="docs/adr", help="Path to docs/adr directory")
    ap.add_argument("--root", default=".", help="Repo root (for relative paths)")
    a = ap.parse_args()

    root = Path(a.root).resolve()
    adr_dir = (root / a.adr_dir).resolve()
    if not adr_dir.is_dir():
        print(f"ERROR: ADR directory not found: {adr_dir}", file=sys.stderr)
        return 1

    active, archived = scan_adrs(adr_dir)
    all_records = active + [r for r in archived if r["number"] not in {x["number"] for x in active}]
    build_backward_refs(all_records)

    json_path = adr_dir / "index.json"
    index_path = adr_dir / "INDEX.md"

    write_json(active, archived, json_path)
    write_index_md(active, index_path)

    print(f"✓ {len(active)} active ADRs + {len(archived)} archived indexed")
    print(f"  → {json_path.relative_to(root)}")
    print(f"  → {index_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
