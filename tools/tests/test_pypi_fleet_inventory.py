"""Tests für die puren Klassifikationsfunktionen des PyPI-Fleet-Inventars (ADR-266)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pypi_fleet_inventory import (  # noqa: E402
    build_findings,
    classify_auth,
    parse_remote_publisher,
    uses_reusable,
)

OIDC_WF = """
permissions:
  id-token: write
steps:
  - uses: pypa/gh-action-pypi-publish@release/v1
"""

TOKEN_WF = """
steps:
  - uses: pypa/gh-action-pypi-publish@release/v1
    with:
      password: ${{ secrets.PYPI_API_TOKEN }}
"""

HYBRID_WF = OIDC_WF + TOKEN_WF

REMOTE_WF = """
steps:
  - uses: actions/checkout@v6
    with:
      repository: achimdehnert/iil-codeguard
"""

PACKAGES_WF = """
jobs:
  build:
    defaults:
      run:
        working-directory: packages/django-tenancy
    steps:
      - uses: actions/upload-artifact@v4
        with:
          path: packages/django-tenancy/dist
"""


def test_should_classify_pure_oidc():
    assert classify_auth(OIDC_WF) == "oidc"


def test_should_classify_pure_token():
    assert classify_auth(TOKEN_WF) == "token"


def test_should_classify_hybrid_when_both_present():
    assert classify_auth(HYBRID_WF) == "hybrid"


def test_should_classify_unknown_without_signals():
    assert classify_auth("jobs: {}") == "unknown"


def test_should_detect_reusable_caller():
    assert uses_reusable("uses: achimdehnert/platform/.github/workflows/_ci-pypi.yml@main")
    assert not uses_reusable(OIDC_WF)


def test_should_extract_remote_repo():
    assert parse_remote_publisher(REMOTE_WF) == {"remote_repo": "achimdehnert/iil-codeguard"}


def test_should_extract_package_dirs_deduped_without_dist_suffix():
    assert parse_remote_publisher(PACKAGES_WF) == {"package_dirs": ["packages/django-tenancy"]}


def test_should_flag_double_publisher_and_token_auth():
    pkg = {
        "in_registry": True,
        "publishers": [
            {"kind": "self", "workflows": [{"auth": "token"}]},
            {"kind": "platform-remote", "workflows": [{"auth": "oidc"}]},
        ],
        "pypi": {"version": "1.0"},
        "pyproject_version": "1.0",
    }
    assert build_findings(pkg) == ["double_publisher", "token_auth"]


def test_should_flag_registry_missing_and_version_drift():
    pkg = {
        "in_registry": False,
        "publishers": [{"kind": "self", "workflows": [{"auth": "oidc"}]}],
        "pypi": {"version": "1.1"},
        "pyproject_version": "1.2",
    }
    assert build_findings(pkg) == ["registry_missing", "version_drift_pyproject_vs_pypi"]
