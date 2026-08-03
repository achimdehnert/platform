"""Tests für ci_relevant_paths.py — Relevanz-Entscheid des Zwilling-Jobs (#1414).

Deckt: Präfix-Semantik von `<dir>/**`, docs-only-PR → nicht relevant, leerer Diff
→ konservativ relevant, fehlende `on.push.paths` → harter Fehler, plus einen
Live-Check gegen den echten `tools-tests.yml` (die Muster müssen dort wirklich
stehen — sonst entscheidet der Zwilling gegen eine leere Liste).

Run: `python3 -m pytest tools/tests/test_ci_relevant_paths.py -q`
"""

import importlib.util
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "ci_relevant_paths.py"
_spec = importlib.util.spec_from_file_location("crp", _SRC)
crp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crp)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_REAL_WF = _REPO_ROOT / ".github" / "workflows" / "tools-tests.yml"

_PATTERNS = ["tools/**", "scripts/**", "skills/**"]


def _wf(root, paths_block):
    d = root / ".github" / "workflows"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "wf.yml"
    f.write_text(
        "name: X\n\non:\n  push:\n    paths:\n"
        + "".join(f'      - "{p}"\n' for p in paths_block)
        + "  pull_request:\n\njobs:\n  a:\n    runs-on: ubuntu-latest\n"
        "    steps:\n      - run: 'true'\n",
        encoding="utf-8",
    )
    return f


def test_should_match_file_inside_watched_directory():
    assert crp.is_relevant(["tools/foo.py"], _PATTERNS) is True
    assert crp.is_relevant(["skills/next/SKILL.md"], _PATTERNS) is True


def test_should_not_match_docs_only_change():
    changed = ["docs/adr/ADR-285.md", "AGENT_HANDOVER.md", "README.md"]
    assert crp.is_relevant(changed, _PATTERNS) is False


def test_should_not_match_directory_name_prefix_collision():
    # "toolsX/" darf nicht über das Muster "tools/**" als Treffer gelten
    assert crp.is_relevant(["toolsX/foo.py"], _PATTERNS) is False
    assert crp.is_relevant(["my-tools/foo.py"], _PATTERNS) is False


def test_should_match_directory_itself():
    assert crp.matches("tools", "tools/**") is True


def test_should_be_relevant_when_one_of_many_files_matches():
    changed = ["README.md", "docs/x.md", "scripts/drift_check.py"]
    assert crp.is_relevant(changed, _PATTERNS) is True


def test_should_treat_empty_diff_as_relevant(tmp_path, capsys):
    wf = _wf(tmp_path, _PATTERNS)
    changed = tmp_path / "changed.txt"
    changed.write_text("", encoding="utf-8")
    rc = crp.main(["--workflow", str(wf), "--changed-file", str(changed)])
    assert rc == 0
    assert "relevant=true" in capsys.readouterr().out


def test_should_write_github_output(tmp_path, capsys):
    wf = _wf(tmp_path, _PATTERNS)
    changed = tmp_path / "changed.txt"
    changed.write_text("docs/x.md\n", encoding="utf-8")
    out = tmp_path / "gh_output"
    rc = crp.main(
        [
            "--workflow",
            str(wf),
            "--changed-file",
            str(changed),
            "--github-output",
            str(out),
        ]
    )
    assert rc == 0
    assert out.read_text(encoding="utf-8").strip() == "relevant=false"


def test_should_fail_loudly_when_paths_block_missing(tmp_path):
    d = tmp_path / ".github" / "workflows"
    d.mkdir(parents=True)
    f = d / "wf.yml"
    f.write_text(
        "name: X\non:\n  push:\n    branches: [main]\njobs:\n  a:\n"
        "    runs-on: ubuntu-latest\n    steps:\n      - run: 'true'\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="on.push.paths"):
        crp.load_workflow_paths(f)


def test_should_read_patterns_from_real_workflow():
    """Positivkontrolle: der echte Workflow trägt die Liste, die der Zwilling liest.

    Ohne diesen Test könnte `on.push.paths` verschwinden und der Relevanz-Schritt
    entschiede gegen eine leere Liste — der Gate wäre still immer (oder nie) grün.
    """
    patterns = crp.load_workflow_paths(_REAL_WF)
    assert "tools/**" in patterns
    assert "skills/**" in patterns
    # Und die Entscheidung stimmt an beiden Enden
    assert crp.is_relevant(["tools/ci_relevant_paths.py"], patterns) is True
    # 2026-08-03: docs/adr ist JETZT relevant — mehrere Tests lesen den ADR-Baum
    # (test_check_deploy_adr_supersession, test_adr_citation_lint). Diese Zeile
    # behauptete bis dahin das Gegenteil und hielt die Luecke fest, durch die
    # ADR-292 main latent rot machen konnte, ohne einen Lauf auszuloesen.
    assert crp.is_relevant(["docs/adr/ADR-285.md"], patterns) is True
    assert crp.is_relevant(["README.md"], patterns) is False
