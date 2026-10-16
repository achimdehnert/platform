"""Tests für die puren Regeln des PyPI-Release-Melders (KONZ-platform-072 §2.2)."""

import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pypi_release_melder  # noqa: E402
from pypi_release_melder import (  # noqa: E402
    OHNE_ERWARTUNG,
    OK,
    R1,
    R3,
    R4,
    UNBEKANNT,
    bewerte_version,
    erwartung,
    lauf,
    pruefe_herkunft,
    pruefe_tag,
    versionen_im_fenster,
)

SELF_PKG = {"repo": "beispiel", "publishers": [{"kind": "self", "workflows": [{"file": "publish.yml"}]}]}
REMOTE_PKG = {
    "repo": "beispiel",
    "publishers": [{"kind": "platform-remote", "workflows": [{"file": "publish-beispiel.yml"}]}],
}


def _bundle(repository: str, workflow: str) -> bytes:
    return json.dumps(
        {"attestation_bundles": [{"publisher": {"kind": "GitHub", "repository": repository, "workflow": workflow}}]}
    ).encode()


def test_should_expect_own_repo_for_self_publisher():
    e = erwartung(SELF_PKG)
    assert "achimdehnert/beispiel" in e["repos"]
    assert e["workflows"] == {"publish.yml"}


def test_should_expect_platform_repo_for_remote_publisher():
    e = erwartung(REMOTE_PKG)
    assert "achimdehnert/platform" in e["repos"]
    assert "achimdehnert/beispiel" not in e["repos"]


def test_should_select_only_versions_uploaded_inside_window():
    releases = {
        "1.0.0": [{"upload_time_iso_8601": "2026-01-01T00:00:00.000Z"}],
        "1.1.0": [{"upload_time_iso_8601": "2026-10-10T00:00:00.000Z"}],
        "leer": [],
    }
    seit = datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert list(versionen_im_fenster(releases, seit)) == ["1.1.0"]


def test_should_accept_all_fleet_tag_forms():
    assert pruefe_tag("beispiel", "1.2.0", {"v1.2.0"}) == OK
    assert pruefe_tag("beispiel", "1.2.0", {"1.2.0"}) == OK
    assert pruefe_tag("beispiel", "1.2.0", {"beispiel@1.2.0"}) == OK
    assert pruefe_tag("beispiel", "1.2.0", {"v1.1.0", "anderes@1.2.0"}) == R1


def test_should_report_unknown_not_missing_when_tags_unreadable():
    assert pruefe_tag("beispiel", "1.2.0", None) == UNBEKANNT


def test_should_flag_inventory_gap_not_r3_when_no_publisher_known():
    ohne = erwartung({"repo": "beispiel", "publishers": []})
    ergebnis, _ = pruefe_herkunft(200, _bundle("iilgmbh/beispiel", "publish.yml"), ohne)
    assert ergebnis == OHNE_ERWARTUNG


def test_should_pass_matching_attestation():
    ergebnis, _ = pruefe_herkunft(200, _bundle("achimdehnert/beispiel", "publish.yml"), erwartung(SELF_PKG))
    assert ergebnis == OK


def test_should_flag_foreign_repository_as_r3():
    ergebnis, _ = pruefe_herkunft(200, _bundle("fremd/beispiel", "publish.yml"), erwartung(SELF_PKG))
    assert ergebnis == R3


def test_should_flag_foreign_workflow_as_r3():
    ergebnis, _ = pruefe_herkunft(200, _bundle("achimdehnert/beispiel", "evil.yml"), erwartung(SELF_PKG))
    assert ergebnis == R3


def test_should_flag_missing_attestation_as_r4():
    assert pruefe_herkunft(404, b"", erwartung(SELF_PKG))[0] == R4
    assert pruefe_herkunft(200, b'{"attestation_bundles": []}', erwartung(SELF_PKG))[0] == R4


def test_should_report_unknown_on_network_error_or_broken_body():
    assert pruefe_herkunft(None, b"", erwartung(SELF_PKG))[0] == UNBEKANNT
    assert pruefe_herkunft(500, b"", erwartung(SELF_PKG))[0] == UNBEKANNT
    assert pruefe_herkunft(200, b"kaputt", erwartung(SELF_PKG))[0] == UNBEKANNT


def test_should_collect_each_finding_once_per_version():
    dateien = [{"filename": "a.whl"}, {"filename": "a.tar.gz"}]
    v = bewerte_version(
        "beispiel", "2.0.0", dateien, {"v1.0.0"}, erwartung(SELF_PKG), fetch=lambda *_: (404, b"")
    )
    assert v["befunde"] == [R1, R4]
    assert len(v["herkunft"]) == 2


def test_should_have_no_findings_for_expected_release():
    v = bewerte_version(
        "beispiel", "2.0.0", [{"filename": "a.whl"}], {"v2.0.0"}, erwartung(SELF_PKG),
        fetch=lambda *_: (200, _bundle("achimdehnert/beispiel", "publish.yml")),
    )
    assert v["befunde"] == []


def _lauf_mit_antwort(tmp_path, monkeypatch, antwort) -> dict:
    fleet = tmp_path / "fleet.yaml"
    fleet.write_text("packages:\n  beispiel: {}\n")
    monkeypatch.setattr(
        pypi_release_melder.urllib.request, "urlopen",
        lambda *_a, **_k: io.BytesIO(json.dumps(antwort).encode()),
    )
    return lauf(fleet, datetime(2026, 10, 1, tzinfo=timezone.utc))


def test_should_mark_package_unreadable_when_releases_missing(tmp_path, monkeypatch):
    bericht = _lauf_mit_antwort(tmp_path, monkeypatch, {"info": {}})
    assert bericht["pypi_unlesbar"] == ["beispiel"]


@pytest.mark.parametrize("antwort", [[], "kaputt", {"releases": []}])
def test_should_mark_package_unreadable_when_response_is_no_dict(tmp_path, monkeypatch, antwort):
    bericht = _lauf_mit_antwort(tmp_path, monkeypatch, antwort)
    assert bericht["pypi_unlesbar"] == ["beispiel"]
