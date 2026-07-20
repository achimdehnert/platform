"""Unit tests for ref-sweep.py `rewrite_uses` (KONZ-002 OOTB-A).

Closes the evidence gap from the session-retro (2026-06-04): PR #453 claimed
"unit-getestet" without a committed test. These tests pin the hardened behaviour
the retro verified manually — comment-skip, word-boundary, --pin, idempotency.

Run: `python3 -m pytest tools/tests/test_ref_sweep.py -q`
(ref-sweep.py has a hyphen → loaded via importlib.)
"""
import importlib.util
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "ref-sweep.py"
_spec = importlib.util.spec_from_file_location("ref_sweep", _SRC)
rs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rs)

OLD, NEW = "achimdehnert/platform", "iilgmbh/shared-ci"


def test_should_rewrite_real_uses_line():
    line = "    uses: achimdehnert/platform/.github/workflows/_ci-python.yml@main"
    out, n = rs.rewrite_uses(line, OLD, NEW, None)
    assert n == 1
    assert out == "    uses: iilgmbh/shared-ci/.github/workflows/_ci-python.yml@main"


def test_should_skip_comment_banner():
    # the retro's main defect: blind replace() would have rewritten this comment
    line = "# Usage: uses: achimdehnert/platform/.github/actions/gitleaks-scan@v1"
    out, n = rs.rewrite_uses(line, OLD, NEW, None)
    assert n == 0
    assert out == line


def test_should_not_rewrite_longer_repo_name():
    # achimdehnert/platform must NOT match achimdehnert/platform-tools (word boundary)
    line = "    uses: achimdehnert/platform-tools/x@main"
    out, n = rs.rewrite_uses(line, OLD, NEW, None)
    assert n == 0
    assert "platform-tools" in out


def test_should_rewrite_step_level_action_ref():
    line = "      - uses: achimdehnert/platform/.github/actions/gitleaks-scan@main"
    out, n = rs.rewrite_uses(line, OLD, NEW, None)
    assert n == 1
    assert "iilgmbh/shared-ci/.github/actions/gitleaks-scan@main" in out


def test_should_repin_ref_to_tag_when_pin_given():
    line = "    uses: achimdehnert/platform/.github/workflows/_ci-python.yml@main"
    out, n = rs.rewrite_uses(line, OLD, NEW, "v1.0.0")
    assert n == 1
    assert out.endswith("@v1.0.0")
    assert "@main" not in out


def test_should_be_idempotent_when_already_new():
    line = "    uses: iilgmbh/shared-ci/.github/actions/gitleaks-scan@v1.0.0"
    out, n = rs.rewrite_uses(line, OLD, NEW, "v1.0.0")
    assert n == 0
    assert out == line


def test_should_rewrite_only_real_uses_in_multiline():
    text = "\n".join([
        "# uses: achimdehnert/platform/x@v1   (banner, must stay)",
        "jobs:",
        "  ci:",
        "    uses: achimdehnert/platform/.github/workflows/_ci-python.yml@main",
        "    runs-on: ubuntu-latest",
    ])
    out, n = rs.rewrite_uses(text, OLD, NEW, "v1.0.0")
    assert n == 1  # only the real uses line, NOT the banner comment
    assert "iilgmbh/shared-ci/.github/workflows/_ci-python.yml@v1.0.0" in out
    assert out.splitlines()[0].startswith("# uses: achimdehnert/platform")  # banner untouched


def test_should_not_change_text_without_uses():
    text = "name: CI\non: [push]\njobs:\n  x:\n    runs-on: ubuntu-latest\n"
    out, n = rs.rewrite_uses(text, OLD, NEW, "v1.0.0")
    assert n == 0
    assert out == text


@pytest.mark.parametrize("trailer", ["@main", "@v1", "@v1.2.3", ""])
def test_should_preserve_ref_trailer_without_pin(trailer):
    line = f"    uses: achimdehnert/platform/.github/actions/gitleaks-scan{trailer}"
    out, n = rs.rewrite_uses(line, OLD, NEW, None)
    assert n == 1
    assert out == f"    uses: iilgmbh/shared-ci/.github/actions/gitleaks-scan{trailer}"
