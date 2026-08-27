"""Tests für die puren Klassifikationsfunktionen des PyPI-Fleet-Inventars (ADR-266)."""

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pypi_fleet_inventory import (  # noqa: E402
    FLEET_FILE,
    build_findings,
    classify_auth,
    parse_remote_publisher,
    provenance_counts,
    provenance_for,
    select_release_file,
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
    assert uses_reusable(
        "uses: achimdehnert/platform/.github/workflows/_ci-pypi.yml@main"
    )
    assert not uses_reusable(OIDC_WF)


def test_should_extract_remote_repo():
    assert parse_remote_publisher(REMOTE_WF) == {
        "remote_repo": "achimdehnert/iil-codeguard"
    }


def test_should_extract_package_dirs_deduped_without_dist_suffix():
    assert parse_remote_publisher(PACKAGES_WF) == {
        "package_dirs": ["packages/django-tenancy"]
    }


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


def test_should_flag_archival_candidate_when_stale_and_unused():
    pkg = {
        "in_registry": True,
        "publishers": [{"kind": "self", "workflows": [{"auth": "oidc"}]}],
        "pypi": {
            "version": "1.0",
            "last_upload": "2020-01-01T00:00:00Z",
            "downloads_30d": 3,
        },
        "pyproject_version": "1.0",
    }
    assert build_findings(pkg) == ["archival_candidate_stale_and_unused"]


def test_should_not_flag_archival_when_downloads_healthy():
    pkg = {
        "in_registry": True,
        "publishers": [{"kind": "self", "workflows": [{"auth": "oidc"}]}],
        "pypi": {
            "version": "1.0",
            "last_upload": "2020-01-01T00:00:00Z",
            "downloads_30d": 5000,
        },
        "pyproject_version": "1.0",
    }
    assert build_findings(pkg) == []


def test_should_flag_registry_missing_and_version_drift():
    pkg = {
        "in_registry": False,
        "publishers": [{"kind": "self", "workflows": [{"auth": "oidc"}]}],
        "pypi": {"version": "1.1"},
        "pyproject_version": "1.2",
    }
    assert build_findings(pkg) == [
        "registry_missing",
        "version_drift_pyproject_vs_pypi",
    ]


# --------------------------------------------------------------------------
# K4 am Artefakt (KONZ-platform-052 V10, ADR-278) — Provenance über die
# PyPI-Integrity-API. Fixtures statt echtem Netz (`fetch` injizierbar).
# --------------------------------------------------------------------------


def test_should_select_wheel_before_sdist():
    urls = [
        {"filename": "iil_weltenfw-0.5.0.tar.gz"},
        {"filename": "iil_weltenfw-0.5.0-py3-none-any.whl"},
    ]
    assert select_release_file(urls)["filename"].endswith(".whl")


def test_should_fall_back_to_sdist_without_wheel():
    urls = [{"filename": "iil_weltenfw-0.5.0.tar.gz"}]
    assert select_release_file(urls) == urls[0]


def test_should_return_none_without_release_files():
    assert select_release_file([]) is None


def test_should_mark_attested_on_200_with_bundle():
    def fake_fetch(dist, version, filename):
        assert (dist, version, filename) == (
            "iil-weltenfw",
            "0.5.0",
            "iil_weltenfw-0.5.0-py3-none-any.whl",
        )
        return 200, json.dumps({"attestation_bundles": [{"x": 1}]}).encode()

    result = provenance_for(
        "iil-weltenfw",
        "0.5.0",
        [{"filename": "iil_weltenfw-0.5.0-py3-none-any.whl"}],
        fetch=fake_fetch,
    )
    assert result["status"] == "attested"
    assert result["bundles"] == 1
    assert result["wheel"] == "iil_weltenfw-0.5.0-py3-none-any.whl"
    assert result["version"] == "0.5.0"


def test_should_mark_unattested_on_404():
    def fake_fetch(dist, version, filename):
        return 404, b""

    result = provenance_for(
        "iil-aifw",
        "0.13.0",
        [{"filename": "iil_aifw-0.13.0-py3-none-any.whl"}],
        fetch=fake_fetch,
    )
    assert result["status"] == "unattested"
    assert result["bundles"] == 0


def test_should_mark_unattested_on_200_with_empty_bundles():
    def fake_fetch(dist, version, filename):
        return 200, json.dumps({"attestation_bundles": []}).encode()

    result = provenance_for(
        "iil-testkit",
        "0.6.0",
        [{"filename": "iil_testkit-0.6.0-py3-none-any.whl"}],
        fetch=fake_fetch,
    )
    assert result["status"] == "unattested"
    assert result["bundles"] == 0


def test_should_mark_unbekannt_on_network_timeout():
    def fake_fetch(dist, version, filename):
        return None, b""

    result = provenance_for(
        "iil-x", "1.0", [{"filename": "iil_x-1.0-py3-none-any.whl"}], fetch=fake_fetch
    )
    assert result["status"] == "unbekannt"
    assert result["bundles"] is None


def test_should_mark_unbekannt_on_broken_json_body():
    def fake_fetch(dist, version, filename):
        return 200, b"not-json"

    result = provenance_for(
        "iil-x", "1.0", [{"filename": "iil_x-1.0-py3-none-any.whl"}], fetch=fake_fetch
    )
    assert result["status"] == "unbekannt"
    assert result["bundles"] is None


def test_should_mark_unbekannt_without_any_release_files():
    result = provenance_for("iil-x", "1.0", [])
    assert result["status"] == "unbekannt"
    assert result["bundles"] is None
    assert result["wheel"] is None


def test_should_count_provenance_status_across_fleet():
    packages = {
        "a": {"pypi": {"provenance": {"status": "attested"}}},
        "b": {"pypi": {"provenance": {"status": "unattested"}}},
        "c": {"pypi": {"provenance": {"status": "unbekannt"}}},
        "d": {"pypi": {}},  # kein provenance-Feld -> zaehlt nicht mit
        "e": {},  # kein pypi-Feld ueberhaupt (offline) -> zaehlt nicht mit
    }
    assert provenance_counts(packages) == {
        "attested": 1,
        "unattested": 1,
        "unbekannt": 1,
    }


def test_should_load_current_fleet_registry_schema():
    """Regression: das bestehende Fleet-YAML bleibt mit dem erweiterten Schema lesbar."""
    doc = yaml.safe_load(FLEET_FILE.read_text())
    assert "packages" in doc
    assert isinstance(doc["packages"], dict)
    for pkg in doc["packages"].values():
        assert "repo" in pkg
        assert "findings" in pkg
        assert isinstance(pkg["findings"], list)
