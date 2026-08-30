"""Tests für tools/pypi_fleet_earlywarn.py (pure functions, #2075 K3)."""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pypi_fleet_earlywarn import (  # noqa: E402
    ADR278_DATE,
    eol_status,
    parse_requires_python,
    parse_reusable_refs,
    unattested_release_finding,
    version_coupled,
)


def test_should_parse_requires_python_lower_bound():
    assert parse_requires_python(">=3.10,<4") == (3, 10)
    assert parse_requires_python(">= 3.12") == (3, 12)
    assert parse_requires_python("~=3.11") == (3, 11)
    assert parse_requires_python(None) is None


def test_should_classify_eol_and_eol_soon():
    assert eol_status((3, 9), dt.date(2026, 8, 19)) == "eol"
    assert eol_status((3, 10), dt.date(2026, 8, 19)) == "eol_soon"  # EOL 2026-10-31
    assert eol_status((3, 12), dt.date(2026, 8, 19)) is None
    assert eol_status(None, dt.date(2026, 8, 19)) is None


def test_should_find_version_coupled_interpreter_strings():
    text = "HEALTHCHECK CMD pidof /usr/local/bin/python3.12\nRUN python3 -m pip\n"
    assert version_coupled(text) == ["python3.12"]
    assert version_coupled("python3 -m pytest") == []


def test_should_parse_reusable_refs_with_ref():
    text = (
        "    uses: achimdehnert/platform/.github/workflows/_ci-pypi.yml@main\n"
        "    uses: achimdehnert/shared-ci/.github/workflows/_build-docker.yml@v1.1.10\n"
    )
    refs = parse_reusable_refs(text)
    assert ("achimdehnert/platform", "_ci-pypi.yml", "main") in refs
    assert ("achimdehnert/shared-ci", "_build-docker.yml", "v1.1.10") in refs


def test_should_order_semver_tags():
    from pypi_fleet_earlywarn import semver_key

    assert semver_key("v1.1.11") > semver_key("v1.1.10") > semver_key("v1.1.0")
    assert semver_key("v1") == (1, 0, 0)
    assert semver_key("main") is None


# --------------------------------------------------------------------------
# K4 unattested_release (KONZ-platform-052 V10, ADR-278)
# --------------------------------------------------------------------------


def test_should_flag_unattested_release_after_adr278():
    pkg = {
        "pypi": {
            "provenance": {"status": "unattested", "version": "0.6.0"},
            "last_upload": "2026-08-26T10:00:00Z",
        }
    }
    finding = unattested_release_finding(pkg)
    assert finding is not None
    assert finding.startswith("K4 unattested_release:")
    assert "0.6.0" in finding


def test_should_not_flag_unattested_release_before_adr278():
    pkg = {
        "pypi": {
            "provenance": {"status": "unattested", "version": "0.4.1"},
            "last_upload": "2026-06-01T10:00:00Z",
        }
    }
    assert unattested_release_finding(pkg) is None


def test_should_not_flag_release_exactly_on_adr278_date():
    pkg = {
        "pypi": {
            "provenance": {"status": "unattested", "version": "0.1.0"},
            "last_upload": f"{ADR278_DATE.isoformat()}T00:00:00Z",
        }
    }
    assert unattested_release_finding(pkg) is None


def test_should_not_flag_attested_release():
    pkg = {
        "pypi": {
            "provenance": {"status": "attested", "version": "0.5.0"},
            "last_upload": "2026-08-21T10:00:00Z",
        }
    }
    assert unattested_release_finding(pkg) is None


def test_should_not_flag_unbekannt_status_as_finding():
    """🌀 unbekannt ist keine Abwesenheit — es darf nie wie unattested gemeldet werden."""
    pkg = {
        "pypi": {
            "provenance": {"status": "unbekannt", "version": "0.1.0"},
            "last_upload": "2026-08-26T10:00:00Z",
        }
    }
    assert unattested_release_finding(pkg) is None


def test_should_not_flag_without_provenance_data():
    assert unattested_release_finding({"pypi": {}}) is None
    assert unattested_release_finding({}) is None
