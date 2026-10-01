"""Tests für tools/gen_pkg_agents_md.py (#2075 K2)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_agents_md import check_text  # noqa: E402
from gen_pkg_agents_md import (  # noqa: E402
    END_MARKER,
    curated_tail,
    generate,
    generated_head,
)

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


def _with_workflow(pkg: Path, name: str, body: str) -> Path:
    wf = pkg / ".github" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    (wf / name).write_text(body)
    return pkg


def test_should_name_reusable_ci_when_a_workflow_calls_it(tmp_path):
    pkg = _with_workflow(
        _make_pkg(tmp_path),
        "ci.yml",
        "uses: iilgmbh/shared-ci/.github/workflows/_ci-pypi.yml@v1\n",
    )
    text = generate(pkg)
    assert "reusable `_ci-pypi.yml`" in text and "`ci.yml`" in text


def test_should_name_own_workflows_when_no_reusable_is_called(tmp_path):
    pkg = _with_workflow(_make_pkg(tmp_path), "test.yml", "jobs: {t: {runs-on: x}}\n")
    text = generate(pkg)
    assert "repo-eigene Workflows (`test.yml`)" in text
    assert "reusable `_ci-pypi.yml` (ADR-226, Aufrufer" not in text


def test_should_flag_missing_ci_as_finding(tmp_path):
    assert "kein CI-Workflow im Repo — Befund" in generate(_make_pkg(tmp_path))


def test_should_end_generated_text_with_marker_and_stay_schema_conform(tmp_path):
    text = generate(_make_pkg(tmp_path))
    assert text.rstrip().endswith(END_MARKER)
    assert check_text(text) == []


def test_should_keep_curated_tail_after_marker_or_heading():
    with_marker = "# x\n" + END_MARKER + "\n\n## Kuratierte Doku\n\ntext\n"
    assert curated_tail(with_marker) == "## Kuratierte Doku\n\ntext\n"
    assert generated_head(with_marker) == "# x\n" + END_MARKER
    legacy = "# x\n\n## Release\n\ny\n\n## Kuratierte Doku\n\ntext\n"
    assert curated_tail(legacy) == "## Kuratierte Doku\n\ntext\n"
    assert generated_head(legacy) == "# x\n\n## Release\n\ny\n"
    assert curated_tail("# nur kopf\n") == ""
