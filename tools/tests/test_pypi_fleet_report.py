"""Pure Helfer des Befund-Reports (#2591 K2) — Zustandsklassifikation und TSV-Parsing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pypi_fleet_report as rep  # noqa: E402


def test_should_treat_v_prefixed_tag_as_equal_to_pypi_version():
    assert rep.version_state("0.14.0", "v0.14.0") == "gleich"


def test_should_flag_version_drift_between_pypi_and_tag():
    assert rep.version_state("0.13.0", "v0.14.0") == "drift"


def test_should_return_na_when_version_or_tag_missing():
    assert rep.version_state(None, "v1.0.0") == "n/a"
    assert rep.version_state("1.0.0", None) == "n/a"


def test_should_classify_shared_ci_pin_states():
    assert rep.pin_state("v1.1.11", "v1.1.14") == "lag"
    assert rep.pin_state("v1.1.14", "v1.1.14") == "aktuell"
    assert rep.pin_state("main", "v1.1.14") == "main"
    assert rep.pin_state("v1.1.14", None) == "n/a"
    assert rep.pin_state(None, "v1.1.14") == "n/a"


def test_should_parse_coldstart_tsv_last_row_wins():
    tsv = "achimdehnert/aifw\tmake setup+test\tok\tfail\t33s\nachimdehnert/aifw\tmake setup+test\tok\tok\t40s\n"
    rows = rep.parse_coldstart_tsv(tsv)
    assert rows["aifw"]["tests"] == "ok"
    assert rows["aifw"]["slug"] == "achimdehnert/aifw"


def test_should_ignore_short_or_empty_tsv_rows():
    assert rep.parse_coldstart_tsv("\nkaputt\tzeile\n") == {}


def test_should_apply_coldstart_pass_contract():
    ok = {"entry": "make setup+test", "setup": "ok", "tests": "ok"}
    assert rep.coldstart_verdict(ok) == "bestanden"
    assert rep.coldstart_verdict({**ok, "tests": "fail"}) == "fehlgeschlagen"
    assert rep.coldstart_verdict({**ok, "entry": "none"}) == "fehlgeschlagen"
    assert rep.coldstart_verdict(None) == "n/a"


def test_should_group_earlywarn_metrics_by_repo_sorted():
    findings = [
        {"repo": "aifw", "metric": "M4", "text": "x"},
        {"repo": "aifw", "metric": "M1", "text": "y"},
        {"repo": "gpufw", "metric": "K4", "text": "z"},
    ]
    assert rep.earlywarn_by_repo(findings) == {"aifw": ["M1", "M4"], "gpufw": ["K4"]}


def test_should_render_na_cells_instead_of_silent_blanks():
    row = {
        "repo": "x",
        "owner_repo": "o/x",
        "strategy": "aktiv",
        "dist": "x",
        "pypi_version": None,
        "pyproject_version": None,
        "tag": None,
        "version_state": "n/a",
        "provenance": "n/a (nicht auf PyPI)",
        "pins": [],
        "run": None,
        "coldstart": None,
        "coldstart_verdict": "n/a",
        "coldstart_sha": None,
        "inventory_findings": [],
        "earlywarn": [],
    }
    md = rep.render([row], "2026-09-02T00:00:00Z", {"Inventar": "test"})
    line = [ln for ln in md.splitlines() if ln.startswith("| [o/x]")][0]
    assert "n/a (nicht auf PyPI)" in line
    assert "n/a (kein shared-ci-Aufruf)" in line
    assert "n/a (kein push-Lauf auf main)" in line
    assert "n/a (nicht gelaufen)" in line
    assert "| — |" in line
