"""Tests fuer tools/deploy_config_lint.py — Org-Gate gegen Auto-Prod-Deploy-Drift."""

import importlib.util
import pathlib

_SPEC = importlib.util.spec_from_file_location(
    "deploy_config_lint",
    pathlib.Path(__file__).resolve().parents[1] / "deploy_config_lint.py",
)
dcl = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(dcl)


# ---- Anti-Pattern 1: push-Fallback auf production ---------------------------
_BAD_FALLBACK = """
jobs:
  deploy:
    uses: achimdehnert/platform/.github/workflows/_deploy-unified.yml@main
    with:
      target_environment: ${{ inputs.target_environment || 'production' }}
"""

# ---- Anti-Pattern 2: workflow_dispatch input default production -------------
_BAD_INPUT_DEFAULT = """
on:
  workflow_dispatch:
    inputs:
      target_environment:
        description: "Ziel"
        required: false
        default: "production"
        type: choice
"""

# ---- Konform (risk-hub nach #165/#166) --------------------------------------
_GOOD = """
on:
  workflow_dispatch:
    inputs:
      target_environment:
        default: "staging"
jobs:
  deploy:
    with:
      target_environment: ${{ inputs.target_environment || 'staging' }}
"""


def test_should_flag_push_fallback_to_production():
    out = dcl.lint_text("deploy.yml", _BAD_FALLBACK)
    assert out, "push->branch-Fallback auf production muss erkannt werden"
    assert "production" in out[0]


def test_should_flag_workflow_dispatch_default_production():
    out = dcl.lint_text("deploy.yml", _BAD_INPUT_DEFAULT)
    assert out, "workflow_dispatch-Default 'production' muss erkannt werden"


def test_should_pass_staging_default():
    assert dcl.lint_text("deploy.yml", _GOOD) == [], "staging-Default ist konform"


def test_should_lint_dir_clean_when_no_offenders(tmp_path):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "deploy.yml").write_text(_GOOD, encoding="utf-8")
    assert dcl.lint_dir(wf) == []


def test_should_lint_dir_flags_offender(tmp_path):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "deploy.yml").write_text(_BAD_FALLBACK, encoding="utf-8")
    assert dcl.lint_dir(wf)
