"""Tests fuer tools/check_publish_gate.py — Recurrence-Guard gegen ungegatete PyPI-Publishes.

Invariante (c): Upload-Job braucht (self- oder transitiv) mind. EINEN bindenden
Gate = Test (pytest) ODER Secret-Scan (gitleaks). Erkannte Uploads: pypa-Action
UND `twine upload`.
"""

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

# ---- UNGEGATET: einziger publish-Job, gar kein Gate (researchfw-Realfall) ----
_UNGATED_NO_GATE = """
jobs:
  publish:
    steps:
      - run: hatch build
      - uses: pypa/gh-action-pypi-publish@release/v1
"""

# ---- GEGATET (single job): pytest-Schritt VOR dem Upload-Schritt ------------
_SELF_GATED_TEST = """
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

# ---- UNGEGATET: Ancestor heisst "contest" — 'test' nur als Substring, KEIN Gate
# (Word-Boundary-Regression, Retro 2026-06-30 F2) ------------------------------
_UNGATED_SUBSTRING_TEST = """
jobs:
  contest:
    name: Attestation and protest build
    steps:
      - run: hatch build
  publish-pypi:
    needs: contest
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
"""

# ---- GEGATET ueber Plural-/Suffix-Jobnamen: 'tests' / 'run-tests' -----------
# `\btest\b` ließ diese als False-Negative durch (Retro-Increment 2026-06-30 F6);
# `tests?` fängt sie. Beide Jobnamen tragen KEIN singular-'test'-Token.
_GATED_BY_PLURAL_NAME = """
jobs:
  tests:
    name: run-tests
    steps:
      - uses: ./.github/actions/ci
  publish-pypi:
    needs: tests
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
"""

# ---- twine: UNGEGATET (iil-codeguard/iil-ingest-Realfall) -------------------
_TWINE_UNGATED = """
jobs:
  publish:
    steps:
      - run: python -m build
      - run: twine check dist/*
      - run: twine upload dist/*
"""

# ---- twine: GEGATET durch pytest davor --------------------------------------
_TWINE_SELF_GATED_TEST = """
jobs:
  publish:
    steps:
      - run: pytest
      - run: python -m build
      - run: twine upload dist/*
"""

# ---- GEGATET durch Secret-Scan (gitleaks) vor pypa-Upload, KEIN Test --------
# (platform/publish-iil-* ADR-226-Muster: secret-gated, test-ungegatet → unter (c) ok)
_SECRET_GATED_PYPA = """
jobs:
  publish:
    steps:
      - run: hatch build
      - name: Pre-publish secret gate
        uses: achimdehnert/platform/.github/actions/gitleaks-scan@main
      - uses: pypa/gh-action-pypi-publish@release/v1
"""

# ---- GEGATET durch Secret-Scan (gitleaks) vor twine upload ------------------
_SECRET_GATED_TWINE = """
jobs:
  publish:
    steps:
      - run: python -m build
      - name: Secret gate
        uses: achimdehnert/platform/.github/actions/gitleaks-scan@main
      - run: twine upload dist/*
"""

# ---- Kein Upload-Workflow (normale CI) --------------------------------------
_NON_UPLOAD = """
jobs:
  lint:
    steps:
      - run: ruff check .
  test:
    steps:
      - run: pytest
"""

# ---- Upload-Schritt in einer ci.yml (Scan-Scope: nicht *publish*-benannt) ----
_UPLOAD_IN_CI = """
jobs:
  release:
    steps:
      - run: hatch build
      - uses: pypa/gh-action-pypi-publish@release/v1
"""


def test_should_pass_linear_gated_chain():
    assert _offenders(_GATED_LINEAR) == []


def test_should_pass_direct_needs_list():
    assert _offenders(_GATED_DIRECT_LIST) == []


def test_should_flag_orphaned_test_job():
    assert _offenders(_UNGATED_ORPHAN_TEST) == ["publish-pypi"]


def test_should_flag_upload_without_any_gate():
    assert _offenders(_UNGATED_NO_GATE) == ["publish"]


def test_should_pass_self_gated_by_test():
    assert _offenders(_SELF_GATED_TEST) == []


def test_should_flag_single_job_with_test_after_upload():
    assert _offenders(_UNGATED_WRONG_ORDER) == ["publish"]


def test_should_pass_when_gate_ancestor_detected_by_name():
    assert _offenders(_GATED_BY_NAME) == []


def test_should_flag_when_ancestor_name_only_contains_test_as_substring():
    # 'contest'/'attestation'/'protest' enthalten 'test' nur als Substring → KEIN Gate.
    assert _offenders(_UNGATED_SUBSTRING_TEST) == ["publish-pypi"]


def test_should_pass_when_gate_ancestor_named_tests_plural():
    # Regression-Guard F6: Jobname 'tests'/'run-tests' (Plural) muss als Gate zählen.
    assert _offenders(_GATED_BY_PLURAL_NAME) == []


def test_should_flag_twine_upload_without_gate():
    assert _offenders(_TWINE_UNGATED) == ["publish"]


def test_should_pass_twine_self_gated_by_test():
    assert _offenders(_TWINE_SELF_GATED_TEST) == []


def test_should_pass_secret_scan_gate_before_pypa():
    assert _offenders(_SECRET_GATED_PYPA) == []


def test_should_pass_secret_scan_gate_before_twine():
    assert _offenders(_SECRET_GATED_TWINE) == []


def test_should_report_no_upload_jobs_for_normal_ci():
    result = cpg.analyze_workflow(_NON_UPLOAD)
    assert result["upload_jobs"] == []
    assert result["offenders"] == []


def test_should_identify_upload_jobs_for_pypa_and_twine():
    assert cpg.analyze_workflow(_GATED_LINEAR)["upload_jobs"] == ["publish-pypi"]
    assert cpg.analyze_workflow(_TWINE_UNGATED)["upload_jobs"] == ["publish"]


def test_should_return_offenders_via_check_file(tmp_path):
    wf = tmp_path / "publish.yml"
    wf.write_text(_TWINE_UNGATED, encoding="utf-8")
    assert cpg.check_file(wf) == ["publish"]


def test_should_ignore_malformed_yaml(tmp_path):
    wf = tmp_path / "broken.yml"
    wf.write_text("jobs: [unbalanced", encoding="utf-8")
    assert cpg.check_file(wf) == []


def test_should_exit_nonzero_on_offender(tmp_path, capsys):
    wf = tmp_path / "publish.yml"
    wf.write_text(_UNGATED_NO_GATE, encoding="utf-8")
    rc = cpg.main([str(wf)])
    assert rc == 1
    assert "UNGEGATET" in capsys.readouterr().out


def test_should_exit_zero_on_gated(tmp_path):
    wf = tmp_path / "publish.yml"
    wf.write_text(_GATED_LINEAR, encoding="utf-8")
    assert cpg.main([str(wf)]) == 0


def test_should_scan_all_workflows_not_only_publish_named(tmp_path):
    # Upload-Schritt in ci.yml (nicht *publish*-benannt) muss trotzdem gefunden werden.
    wfdir = tmp_path / ".github" / "workflows"
    wfdir.mkdir(parents=True)
    (wfdir / "ci.yml").write_text(_UPLOAD_IN_CI, encoding="utf-8")
    (wfdir / "lint.yml").write_text(_NON_UPLOAD, encoding="utf-8")  # irrelevant, still übersprungen
    assert cpg.main([str(tmp_path)]) == 1
