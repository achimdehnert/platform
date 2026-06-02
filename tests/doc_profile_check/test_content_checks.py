"""Tests for doc_profile_check.sh min_inhalt_rule engine (ADR-218 OQ-1, Issue #292).

Fixtures: stub (empty) → FAIL, filled → PASS.
"""
import pathlib
import textwrap

import pytest

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from check_utils import check_min_inhalt_rule


# ---------------------------------------------------------------------------
# heading_count
# ---------------------------------------------------------------------------

def test_heading_count_empty_stub_fails(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# Title\n\nStub — keine Einträge.\n")
    err = check_min_inhalt_rule({"type": "heading_count", "min": 2}, f)
    assert err is not None, "Empty stub should FAIL heading_count"
    assert "heading_count=0<2" in err


def test_heading_count_filled_passes(tmp_path):
    f = tmp_path / "doc.md"
    headings = "\n".join(f"## Begriff {i}" for i in range(10))
    f.write_text(f"# Domain-Glossar\n\n{headings}\n")
    err = check_min_inhalt_rule({"type": "heading_count", "min": 10}, f)
    assert err is None, f"Filled doc should PASS heading_count, got: {err}"


def test_heading_count_partial_fails(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# Title\n\n## Only One\n")
    err = check_min_inhalt_rule({"type": "heading_count", "min": 2}, f)
    assert err is not None
    assert "heading_count=1<2" in err


# ---------------------------------------------------------------------------
# table_rows
# ---------------------------------------------------------------------------

def test_table_rows_empty_stub_fails(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# Glossar\n\nStub.\n")
    err = check_min_inhalt_rule({"type": "table_rows", "min": 3}, f)
    assert err is not None
    assert "table_rows=0<3" in err


def test_table_rows_filled_passes(tmp_path):
    f = tmp_path / "doc.md"
    table = "| Begriff | Definition |\n|---|---|\n| A | Beschreibung A |\n| B | Beschreibung B |\n| C | Beschreibung C |\n"
    f.write_text(f"# Glossar\n\n{table}")
    err = check_min_inhalt_rule({"type": "table_rows", "min": 3}, f)
    assert err is None, f"Should PASS table_rows, got: {err}"


# ---------------------------------------------------------------------------
# lines
# ---------------------------------------------------------------------------

def test_lines_empty_stub_fails(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# Title\n")
    err = check_min_inhalt_rule({"type": "lines", "min": 5}, f)
    assert err is not None
    assert "<5" in err


def test_lines_filled_passes(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("\n".join(f"Zeile {i}" for i in range(10)))
    err = check_min_inhalt_rule({"type": "lines", "min": 5}, f)
    assert err is None


# ---------------------------------------------------------------------------
# frontmatter_status
# ---------------------------------------------------------------------------

def test_frontmatter_status_missing_fails(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# No Frontmatter\n\nContent.\n")
    err = check_min_inhalt_rule({"type": "frontmatter_status", "required_value": "ready"}, f)
    assert err is not None
    assert "no-frontmatter" in err


def test_frontmatter_status_draft_fails(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("---\nstatus: draft\n---\n# Content\n")
    err = check_min_inhalt_rule({"type": "frontmatter_status", "required_value": "ready"}, f)
    assert err is not None
    assert "draft" in err


def test_frontmatter_status_ready_passes(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("---\nstatus: ready\nauthor: test\n---\n# Content\n")
    err = check_min_inhalt_rule({"type": "frontmatter_status", "required_value": "ready"}, f)
    assert err is None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_missing_file_returns_none(tmp_path):
    f = tmp_path / "does_not_exist.md"
    err = check_min_inhalt_rule({"type": "heading_count", "min": 1}, f)
    assert err is None  # existence check is caller's responsibility


def test_unknown_rule_type_passes(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("content")
    err = check_min_inhalt_rule({"type": "future_rule_type", "min": 999}, f)
    assert err is None  # forward-compatible: unknown types are skipped
