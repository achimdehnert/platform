"""Tests fuer tools/check_publish_gate.py — Recurrence-Guard gegen ungegatete PyPI-Publishes."""

import importlib.util
import pathlib

_SPEC = importlib.util.spec_from_file_location(
    "check_publish_gate",
    pathlib.Path(__file__).resolve().parents[1] / "check_publish_gate.py",
)
cpg = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cpg)


def _offenders(yaml_text):
    return cpg.analyze_workflow(yaml_text)["offenders"]


# ---- GEGATET: test -> build(needs test) -> publish-pypi(needs build) --------
_GATED_LINEAR = """
jobs:
  test:
    name: Tests (publish gate)
    steps:
      - run: pytest tests/ -v
  build:
    needs: test
    steps:
      - run: hatch build
  publish-pypi:
    needs: build
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
"""

# ---- GEGATET: publish-pypi needs: [test, build] (Liste) ---------------------
_GATED_DIRECT_LIST = """
jobs:
  test:
    steps:
      - run: pytest
  build:
    steps:
      - run: hatch build
  publish-pypi:
    needs: [test, build]
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
"""

# ---- UNGEGATET: test-Job verwaist, build ohne needs (aifw/promptfw-Realfall) -
_UNGATED_ORPHAN_TEST = """
jobs:
  test:
    name: Tests (publish gate)
    steps:
      - run: pytest tests/ -v
  build:
    steps:
      - run: hatch build
  publish-pypi:
    needs: build
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
"""

# ---- UNGEGATET: einziger publish-Job, gar kein Test (researchfw/nl2cad-Realfall)
_UNGATED_NO_TEST = """
jobs:
  publish:
    steps:
      - run: hatch build
      - uses: pypa/gh-action-pypi-publish@release/v1
"""

# ---- GEGATET (single job): pytest-Schritt VOR dem Upload-Schritt ------------
_SELF_GATED_SINGLE = """
jobs:
  publish:
    steps:
      - run: pip install -e '.[dev]'
      - run: pytest tests/
      - run: hatch build
      - uses: pypa/gh-action-pypi-publish@release/v1
"""

# ---- UNGEGATET (single job): Upload-Schritt VOR pytest ----------------------
_UNGATED_WRONG_ORDER = """
jobs:
  publish:
    steps:
      - run: hatch build
      - uses: pypa/gh-action-pypi-publish@release/v1
      - run: pytest tests/
"""

# ---- GEGATET ueber Namens-Heuristik: ancestor heisst "test", ohne run:pytest -
_GATED_BY_NAME = """
jobs:
  unit-test:
    name: Run unit tests
    steps:
      - uses: ./.github/actions/run-tests
  publish-pypi:
    needs: unit-test
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
"""

# ---- Kein Publish-Workflow (normale CI) -------------------------------------
_NON_PUBLISH = """
jobs:
  lint:
    steps:
      - run: ruff check .
  test:
    steps:
      - run: pytest
"""


def test_should_pass_linear_gated_chain():
    assert _offenders(_GATED_LINEAR) == []


def test_should_pass_direct_needs_list():
    assert _offenders(_GATED_DIRECT_LIST) == []


def test_should_flag_orphaned_test_job():
    assert _offenders(_UNGATED_ORPHAN_TEST) == ["publish-pypi"]


def test_should_flag_publish_without_any_test():
    assert _offenders(_UNGATED_NO_TEST) == ["publish"]


def test_should_pass_self_gated_single_job():
    assert _offenders(_SELF_GATED_SINGLE) == []


def test_should_flag_single_job_with_test_after_upload():
    assert _offenders(_UNGATED_WRONG_ORDER) == ["publish"]


def test_should_pass_when_test_ancestor_detected_by_name():
    assert _offenders(_GATED_BY_NAME) == []


def test_should_report_no_publish_jobs_for_normal_ci():
    result = cpg.analyze_workflow(_NON_PUBLISH)
    assert result["publish_jobs"] == []
    assert result["offenders"] == []


def test_should_identify_publish_jobs():
    assert cpg.analyze_workflow(_GATED_LINEAR)["publish_jobs"] == ["publish-pypi"]


def test_should_return_offenders_via_check_file(tmp_path):
    wf = tmp_path / "publish.yml"
    wf.write_text(_UNGATED_NO_TEST, encoding="utf-8")
    assert cpg.check_file(wf) == ["publish"]


def test_should_ignore_malformed_yaml(tmp_path):
    wf = tmp_path / "broken.yml"
    wf.write_text("jobs: [unbalanced", encoding="utf-8")
    assert cpg.check_file(wf) == []


def test_should_exit_nonzero_on_offender(tmp_path, capsys):
    wf = tmp_path / "publish.yml"
    wf.write_text(_UNGATED_NO_TEST, encoding="utf-8")
    rc = cpg.main([str(wf)])
    assert rc == 1
    assert "UNGEGATET" in capsys.readouterr().out


def test_should_exit_zero_on_gated(tmp_path):
    wf = tmp_path / "publish.yml"
    wf.write_text(_GATED_LINEAR, encoding="utf-8")
    assert cpg.main([str(wf)]) == 0


def test_should_expand_repo_root(tmp_path):
    wfdir = tmp_path / ".github" / "workflows"
    wfdir.mkdir(parents=True)
    (wfdir / "publish.yml").write_text(_UNGATED_NO_TEST, encoding="utf-8")
    (wfdir / "ci.yml").write_text(_NON_PUBLISH, encoding="utf-8")  # ignoriert (kein publish/release im Namen)
    assert cpg.main([str(tmp_path)]) == 1
