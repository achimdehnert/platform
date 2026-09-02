"""Tests für tools/gen_pkg_agents_md.py (#2075 K2)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_agents_md import check_text  # noqa: E402
from gen_pkg_agents_md import generate  # noqa: E402

PYPROJECT = """[project]
name = "iil-beispielfw"
description = "Beispiel-Framework fuer Tests"
requires-python = ">=3.11"

[project.optional-dependencies]
dev = ["pytest"]
http = ["httpx"]
"""


def _make_pkg(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(PYPROJECT)
    mod = tmp_path / "src" / "beispielfw"
    mod.mkdir(parents=True)
    (mod / "__init__.py").write_text("")
    return tmp_path


def test_should_generate_schema_conforming_agents_md(tmp_path):
    text = generate(_make_pkg(tmp_path))
    assert check_text(text) == []


def test_should_embed_real_facts_not_placeholders(tmp_path):
    text = generate(_make_pkg(tmp_path))
    assert "iil-beispielfw" in text
    assert "Beispiel-Framework fuer Tests" in text
    assert ">=3.11" in text
    assert "- `beispielfw`" in text
    assert "`iil-beispielfw[http]`" in text


def test_should_note_missing_publish_workflow(tmp_path):
    text = generate(_make_pkg(tmp_path))
    assert "Kein publish-Workflow im Repo" in text
