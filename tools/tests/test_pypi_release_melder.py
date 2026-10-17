"""Tests für die Regeln des PyPI-Release-Melders (KONZ-platform-072 §2.2, Retro 5c34f2 M3)."""

import io
import json
import subprocess
import sys
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import melder_ergebnis  # noqa: E402
import pypi_release_melder  # noqa: E402
from pypi_release_melder import (  # noqa: E402
    DATEN_DATEI,
    EXIT_BEFUND,
    EXIT_NICHT_PRUEFBAR,
    EXIT_OK,
    KURZ_FUNDE,
    OHNE_ERWARTUNG,
    OK,
    R1,
    R3,
    R4,
    UNBEKANNT,
    DatenFehler,
    bewerte_version,
    erwartete_orgs,
    erwartung,
    exit_code,
    kurzzeile,
    lade_daten,
    lade_flotte,
    lade_migration,
    lauf,
    pruefe_herkunft,
    pruefe_tag,
    repo_tags,
    tag_formen,
    versionen_im_fenster,
    zaehle,
)

DATEN = {
    "publisher_remote": {"kind": "platform-remote", "repo": "platform"},
    "tag_formen": ["v{version}"],
    "pakete": {"mehrform": {"tag_formen": ["v{version}", "{dist}@{version}"]}},
}
STANDARD = DATEN["tag_formen"]
SELF_PKG = {"repo": "beispiel", "publishers": [{"kind": "self", "workflows": [{"file": "publish.yml"}]}]}
REMOTE_PKG = {
    "repo": "beispiel",
    "publishers": [{"kind": "platform-remote", "workflows": [{"file": "publish-beispiel.yml"}]}],
}
SEIT = datetime(2026, 10, 1, tzinfo=timezone.utc)


def _heimat(_repo):
    return {"achimdehnert"}


def _erw(pkg=SELF_PKG):
    return erwartung(pkg, DATEN, _heimat)


def _bundle(repository: str, workflow: str) -> bytes:
    return json.dumps(
        {"attestation_bundles": [{"publisher": {"kind": "GitHub", "repository": repository, "workflow": workflow}}]}
    ).encode()


def _yaml(tmp_path, name: str, text: str) -> Path:
    pfad = tmp_path / name
    pfad.write_text(text)
    return pfad


# -- Erwartung und Org-Bindung (Befund 11) ------------------------------------


def test_should_expect_own_repo_for_self_publisher():
    e = _erw()
    assert e["repos"] == {"achimdehnert/beispiel"}
    assert e["workflows"] == {"publish.yml"}


def test_should_expect_platform_repo_for_remote_publisher_from_data():
    e = _erw(REMOTE_PKG)
    assert e["repos"] == {"achimdehnert/platform"}


def test_should_bind_origin_to_home_org_only():
    orgs = erwartete_orgs("beispiel", {}, owner=lambda _r: "iilgmbh")
    assert orgs == {"iilgmbh"}
    e = erwartung(SELF_PKG, DATEN, lambda _r: orgs)
    for fremde_org in ("achimdehnert", "ttz-lif", "meiki-lra"):
        ergebnis, _ = pruefe_herkunft(200, _bundle(f"{fremde_org}/beispiel", "publish.yml"), e)
        assert ergebnis == R3, fremde_org
    assert pruefe_herkunft(200, _bundle("iilgmbh/beispiel", "publish.yml"), e)[0] == OK


def test_should_add_publisher_org_while_migration_runs():
    migration = {"beispiel": {"publisher_current": "achimdehnert"}}
    assert erwartete_orgs("beispiel", migration, owner=lambda _r: "iilgmbh") == {"iilgmbh", "achimdehnert"}


def test_should_expect_no_org_for_unknown_repo():
    assert erwartete_orgs("tippfehler", {}, owner=lambda _r: None) == set()


def test_should_flag_inventory_gap_not_r3_when_no_publisher_known():
    ohne = erwartung({"repo": "beispiel", "publishers": []}, DATEN, _heimat)
    ergebnis, _ = pruefe_herkunft(200, _bundle("iilgmbh/beispiel", "publish.yml"), ohne)
    assert ergebnis == OHNE_ERWARTUNG


# -- Tag-Formen aus Daten -------------------------------------------------------


def test_should_use_standard_tag_forms_unless_package_overrides():
    assert tag_formen("beispiel", DATEN) == ["v{version}"]
    assert tag_formen("mehrform", DATEN) == ["v{version}", "{dist}@{version}"]


def test_should_accept_only_the_tag_forms_of_the_package():
    assert pruefe_tag("beispiel", "1.2.0", {"v1.2.0"}, STANDARD) == OK
    assert pruefe_tag("beispiel", "1.2.0", {"1.2.0"}, STANDARD) == R1
    assert pruefe_tag("beispiel", "1.2.0", {"beispiel@1.2.0"}, STANDARD) == R1
    formen = tag_formen("mehrform", DATEN)
    assert pruefe_tag("beispiel", "1.2.0", {"beispiel@1.2.0"}, formen) == OK
    assert pruefe_tag("beispiel", "1.2.0", {"v1.1.0", "anderes@1.2.0"}, formen) == R1


def test_should_report_unknown_not_missing_when_tags_unreadable():
    assert pruefe_tag("beispiel", "1.2.0", None, STANDARD) == UNBEKANNT


def test_should_load_repo_data_file():
    daten = lade_daten(DATEN_DATEI)
    assert daten["publisher_remote"]["kind"] == "platform-remote"
    assert daten["tag_formen"]


# -- repo_tags mit Double ------------------------------------------------------


class _Lauf:
    def __init__(self, rc=0, stdout=""):
        self.rc, self.stdout, self.aufrufe = rc, stdout, []

    def __call__(self, cmd, **_kw):
        self.aufrufe.append(cmd)
        return subprocess.CompletedProcess(cmd, self.rc, stdout=self.stdout, stderr="")


def test_should_read_tags_from_the_home_org_only():
    lauf_ = _Lauf(stdout="v1.0.0\nv1.1.0\n")
    assert repo_tags("beispiel", "iilgmbh", run=lauf_) == {"v1.0.0", "v1.1.0"}
    assert len(lauf_.aufrufe) == 1
    assert "repos/iilgmbh/beispiel/tags" in lauf_.aufrufe[0]


def test_should_report_tags_unreadable_when_gh_fails():
    assert repo_tags("beispiel", "iilgmbh", run=_Lauf(rc=1)) is None


def test_should_not_try_other_orgs_when_home_org_unknown():
    lauf_ = _Lauf(stdout="v1.0.0\n")
    assert repo_tags("beispiel", None, run=lauf_) is None
    assert lauf_.aufrufe == []


def test_should_report_tags_unreadable_on_timeout():
    def haengt(cmd, **_kw):
        raise subprocess.TimeoutExpired(cmd, 60)

    assert repo_tags("beispiel", "iilgmbh", run=haengt) is None


# -- Fenster und Herkunft ------------------------------------------------------


def test_should_select_only_versions_uploaded_inside_window():
    releases = {
        "1.0.0": [{"upload_time_iso_8601": "2026-01-01T00:00:00.000Z"}],
        "1.1.0": [{"upload_time_iso_8601": "2026-10-10T00:00:00.000Z"}],
        "leer": [],
    }
    assert list(versionen_im_fenster(releases, SEIT)) == ["1.1.0"]


def test_should_pass_matching_attestation():
    assert pruefe_herkunft(200, _bundle("achimdehnert/beispiel", "publish.yml"), _erw())[0] == OK


def test_should_flag_foreign_repository_as_r3():
    assert pruefe_herkunft(200, _bundle("fremd/beispiel", "publish.yml"), _erw())[0] == R3


def test_should_flag_foreign_workflow_as_r3():
    assert pruefe_herkunft(200, _bundle("achimdehnert/beispiel", "evil.yml"), _erw())[0] == R3


def test_should_flag_missing_attestation_as_r4():
    assert pruefe_herkunft(404, b"", _erw())[0] == R4
    assert pruefe_herkunft(200, b'{"attestation_bundles": []}', _erw())[0] == R4


def test_should_report_unknown_on_network_error_or_broken_body():
    assert pruefe_herkunft(None, b"", _erw())[0] == UNBEKANNT
    assert pruefe_herkunft(500, b"", _erw())[0] == UNBEKANNT
    assert pruefe_herkunft(200, b"kaputt", _erw())[0] == UNBEKANNT


def test_should_collect_each_finding_once_per_version():
    dateien = [{"filename": "a.whl"}, {"filename": "a.tar.gz"}]
    v = bewerte_version(
        "beispiel", "2.0.0", dateien, {"v1.0.0"}, _erw(), STANDARD, fetch=lambda *_: (404, b"")
    )
    assert v["befunde"] == [R1, R4]
    assert len(v["herkunft"]) == 2


def test_should_have_no_findings_for_expected_release():
    v = bewerte_version(
        "beispiel", "2.0.0", [{"filename": "a.whl"}], {"v2.0.0"}, _erw(), STANDARD,
        fetch=lambda *_: (200, _bundle("achimdehnert/beispiel", "publish.yml")),
    )
    assert v["befunde"] == []


# -- Je Datenpfad: fehlender Schlüssel = unlesbar, nicht 0 (Befund 17) ----------


def _lauf_mit_antwort(tmp_path, monkeypatch, antwort) -> dict:
    fleet = _yaml(tmp_path, "fleet.yaml", "packages:\n  beispiel: {}\n")
    if isinstance(antwort, Exception):
        def urlopen(*_a, **_k):
            raise antwort
    else:
        def urlopen(*_a, **_k):
            return io.BytesIO(json.dumps(antwort).encode())
    monkeypatch.setattr(pypi_release_melder.urllib.request, "urlopen", urlopen)
    return lauf(fleet, SEIT, DATEN, {}, owner=lambda _r: "achimdehnert")


def test_should_mark_package_unreadable_when_releases_missing(tmp_path, monkeypatch):
    bericht = _lauf_mit_antwort(tmp_path, monkeypatch, {"info": {}})
    assert bericht["pypi_unlesbar"] == ["beispiel"]


@pytest.mark.parametrize("antwort", [[], "kaputt", {"releases": []}])
def test_should_mark_package_unreadable_when_response_is_no_dict(tmp_path, monkeypatch, antwort):
    bericht = _lauf_mit_antwort(tmp_path, monkeypatch, antwort)
    assert bericht["pypi_unlesbar"] == ["beispiel"]


def test_should_mark_package_unreadable_when_upload_time_missing(tmp_path, monkeypatch):
    antwort = {"releases": {"9.9.9": [{"filename": "a.whl"}]}}
    bericht = _lauf_mit_antwort(tmp_path, monkeypatch, antwort)
    assert bericht["pypi_unlesbar"] == ["beispiel"]
    assert bericht["versionen"] == []


def test_should_count_pypi_404_as_not_published_not_unreadable(tmp_path, monkeypatch):
    fehler = urllib.error.HTTPError("https://pypi.org/x", 404, "Not Found", {}, None)
    bericht = _lauf_mit_antwort(tmp_path, monkeypatch, fehler)
    assert bericht["pypi_fehlt"] == ["beispiel"]
    assert bericht["pypi_unlesbar"] == []


def test_should_report_unknown_when_attestation_bundles_key_missing():
    assert pruefe_herkunft(200, b'{"andere": 1}', _erw())[0] == UNBEKANNT
    assert pruefe_herkunft(200, b"[]", _erw())[0] == UNBEKANNT


def test_should_report_unknown_when_bundle_has_no_publisher():
    body = json.dumps({"attestation_bundles": [{"attestations": []}]}).encode()
    assert pruefe_herkunft(200, body, _erw())[0] == UNBEKANNT


def test_should_refuse_fleet_file_without_packages(tmp_path):
    with pytest.raises(DatenFehler):
        lade_flotte(_yaml(tmp_path, "fleet.yaml", "_meta: {}\n"))


def test_should_refuse_migration_file_without_packages(tmp_path):
    with pytest.raises(DatenFehler):
        lade_migration(_yaml(tmp_path, "mig.yaml", "meta: {}\n"))


@pytest.mark.parametrize(
    "text",
    [
        'tag_formen: ["v{version}"]\n',
        'publisher_remote: {kind: platform-remote, repo: platform}\n',
        'publisher_remote: {kind: platform-remote}\ntag_formen: ["v{version}"]\n',
        'publisher_remote: {kind: platform-remote, repo: platform}\ntag_formen: []\n',
        'publisher_remote: {kind: platform-remote, repo: platform}\ntag_formen: ["v{version}"]\n'
        "pakete:\n  x: {}\n",
    ],
)
def test_should_refuse_data_file_with_missing_key(tmp_path, text):
    with pytest.raises(DatenFehler):
        lade_daten(_yaml(tmp_path, "daten.yaml", text))


def test_should_exit_not_checkable_when_data_file_broken(tmp_path, capsys):
    rc = pypi_release_melder.main(["--kurz", "--daten-datei", str(_yaml(tmp_path, "d.yaml", "x: 1\n"))])
    assert rc == EXIT_NICHT_PRUEFBAR
    assert "nicht prüfbar" in capsys.readouterr().out


# -- Exit-Code, Kurzzeile, Drosselung --------------------------------------------


def _bericht(befunde_je_version, unlesbar=()):
    return {
        "seit": "2026-10-01T00:00:00Z",
        "pakete": 1,
        "versionen": [{"paket": "p", "version": f"{i}.0", "befunde": b} for i, b in enumerate(befunde_je_version)],
        "pypi_unlesbar": list(unlesbar),
        "pypi_fehlt": [],
    }


def test_should_exit_with_finding_code_when_any_rule_hits():
    assert exit_code(zaehle(_bericht([[R1]]))) == EXIT_BEFUND
    assert exit_code(zaehle(_bericht([[OHNE_ERWARTUNG]], unlesbar=["q"]))) == EXIT_BEFUND


def test_should_exit_not_checkable_when_only_unknown():
    assert exit_code(zaehle(_bericht([[UNBEKANNT]]))) == EXIT_NICHT_PRUEFBAR
    assert exit_code(zaehle(_bericht([[]], unlesbar=["q"]))) == EXIT_NICHT_PRUEFBAR


def test_should_exit_ok_without_findings():
    assert exit_code(zaehle(_bericht([[], []]))) == EXIT_OK


def test_should_name_first_findings_in_short_line():
    zeile = kurzzeile(_bericht([[R1]] * (KURZ_FUNDE + 2)))
    assert zeile.count("(kein_tag)") == KURZ_FUNDE
    assert zeile.endswith("; +2")


def test_should_read_fresh_result_without_network(tmp_path, monkeypatch, capsys):
    ergebnis = tmp_path / "pypi-release.json"
    melder_ergebnis.schreibe(ergebnis, pypi_release_melder.MELDER, _bericht([[R3]]))

    def kein_netz(*_a, **_k):
        raise AssertionError("frisches Ergebnis darf nicht neu messen")

    monkeypatch.setattr(pypi_release_melder, "lauf", kein_netz)
    rc = pypi_release_melder.main(["--kurz", "--ergebnis-datei", str(ergebnis), "--frisch-stunden", "6"])
    assert rc == EXIT_BEFUND
    assert "[Stand " in capsys.readouterr().out


def test_should_measure_again_when_result_is_stale(tmp_path, monkeypatch):
    ergebnis = tmp_path / "pypi-release.json"
    alt = datetime(2026, 1, 1, tzinfo=timezone.utc)
    melder_ergebnis.schreibe(ergebnis, pypi_release_melder.MELDER, _bericht([[R3]]), gemessen_am=alt)
    gemessen = []

    def neu(*_a, **_k):
        gemessen.append(True)
        return _bericht([[]])

    monkeypatch.setattr(pypi_release_melder, "lauf", neu)
    rc = pypi_release_melder.main(["--kurz", "--ergebnis-datei", str(ergebnis), "--frisch-stunden", "6"])
    assert gemessen and rc == EXIT_OK
    assert melder_ergebnis.lies(ergebnis)["ergebnis"]["versionen"][0]["befunde"] == []
