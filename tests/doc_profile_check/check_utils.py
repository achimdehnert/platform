"""Shared min_inhalt_rule check logic — mirrors the embedded Python in doc_profile_check.sh.

Kept in sync manually; update both when the rule engine changes (ADR-218 OQ-1).
"""
from __future__ import annotations

import pathlib


def check_min_inhalt_rule(rule: dict, path: pathlib.Path) -> str | None:
    """Return error string or None if the rule passes.

    Returns None (no error) when the file is missing — existence is a
    separate concern checked by the caller.
    """
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "unreadable"

    rule_type = rule.get("type", "")

    if rule_type == "heading_count":
        count = sum(
            1 for ln in text.splitlines()
            if ln.startswith("## ") or ln.startswith("### ")
        )
        mn = int(rule.get("min", 1))
        return None if count >= mn else f"heading_count={count}<{mn}"

    if rule_type == "table_rows":
        rows = [
            ln for ln in text.splitlines()
            if ln.strip().startswith("|")
            and set(ln.replace("|", "").replace("-", "").replace(" ", "")) != set()
        ]
        data_rows = max(0, len(rows) - 1)
        mn = int(rule.get("min", 1))
        return None if data_rows >= mn else f"table_rows={data_rows}<{mn}"

    if rule_type == "lines":
        count = sum(1 for ln in text.splitlines() if ln.strip())
        mn = int(rule.get("min", 1))
        return None if count >= mn else f"lines={count}<{mn}"

    if rule_type == "frontmatter_status":
        import yaml
        required_val = rule.get("required_value", "ready")
        lines = text.splitlines()
        if lines and lines[0].strip() == "---":
            fm_lines = []
            for ln in lines[1:]:
                if ln.strip() == "---":
                    break
                fm_lines.append(ln)
            try:
                fm = yaml.safe_load("\n".join(fm_lines)) or {}
                actual = fm.get("status", "")
                return None if actual == required_val else f"status={actual!r}!={required_val!r}"
            except Exception:
                return "frontmatter-parse-error"
        return f"no-frontmatter (need status:{required_val})"

    return None  # unknown rule type → skip (forward-compatible)
