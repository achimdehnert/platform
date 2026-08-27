"""Tests fuer tools/iil_cohort.py (ADR-234 P0.5a, KONZ-platform-052 V11).

Alles netzfrei: `resolve()` bekommt einen injizierten Fetcher, `cmd_build` schreibt
in ein tmp_path. Getestet werden die drei Invarianten, an denen die Kohorte haengt:
Kandidaten-Auswahl (Strategie + Dist-Name-Join), Render/Parse-Erhaltung, und dass ein
`unbekannt` die Datei WIRKLICH nicht entstehen laesst.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import iil_cohort as ic  # noqa: E402

# --------------------------------------------------------------------------
# Fixture-Daten (Form entspricht registry_api.flat() bzw. registry/pypi-fleet.yaml)
# --------------------------------------------------------------------------

FLAT = {
    "aifw": {"pypi": "aifw", "pypi_strategy": "aktiv"},
    "iil-django-commons": {"pypi": "iil-django-commons", "pypi_strategy": "einfrieren"},
    "riskfw": {"pypi": "riskfw", "pypi_strategy": "archivieren-kandidat"},
    "dev-hub": {"type": "django"},  # kein Paket
    "outlinefw": {"pypi": "outlinefw"},  # Strategie fehlt -> nicht in der Kohorte
}

FLEET = {
    "aifw": {"repo": "aifw", "dist_name": "iil-aifw"},
    "iil-django-commons": {
        "repo": "iil-django-commons",
        "dist_name": "iil-django-commons",
    },
    "riskfw": {"repo": "riskfw", "dist_name": "riskfw"},
}


def _payload(version, upload="2026-08-12T09:51:43.610983Z"):
    return {"info": {"version": version}, "urls": [{"upload_time_iso_8601": upload}]}


def _fetcher(table):
    """table: dist_name -> ('ok', payload) | ('missing', None) | ('unknown', None)"""

    def fetch(name, timeout=20):
        state, payload = table.get(name, ("unknown", None))
        return state, payload, "" if state == "ok" else state

    return fetch


# --------------------------------------------------------------------------
# Kandidaten
# --------------------------------------------------------------------------


def test_should_select_only_aktiv_and_einfrieren():
    cands = ic.collect_candidates(FLAT, FLEET)
    assert [c.repo for c in cands] == ["aifw", "iil-django-commons"]


def test_should_use_fleet_dist_name_not_registry_short_name():
    cands = {c.repo: c for c in ic.collect_candidates(FLAT, FLEET)}
    assert cands["aifw"].dist_name == "iil-aifw"


def test_should_fall_back_to_registry_name_without_fleet_entry():
    cands = ic.collect_candidates(
        {"gpufw": {"pypi": "iil-gpufw", "pypi_strategy": "aktiv"}}, {}
    )
    assert cands[0].dist_name == "iil-gpufw"


def test_should_sort_candidates_by_dist_name():
    flat = {
        "zeta": {"pypi": "zeta", "pypi_strategy": "aktiv"},
        "alpha": {"pypi": "alpha", "pypi_strategy": "aktiv"},
    }
    assert [c.dist_name for c in ic.collect_candidates(flat, {})] == ["alpha", "zeta"]


# --------------------------------------------------------------------------
# Supportfenster / Alter
# --------------------------------------------------------------------------


def test_should_default_support_window_to_60_days():
    assert ic.SUPPORT_DAYS_DEFAULT == 60
    assert ic.support_until(date(2026, 8, 27)) == date(2026, 10, 26)


def test_should_label_cohort_by_month():
    assert ic.cohort_label(date(2026, 8, 27)) == "2026.08"
    assert ic.cohort_label(date(2026, 12, 1)) == "2026.12"


@pytest.mark.parametrize(
    "until,today,expected",
    [
        (date(2026, 10, 26), date(2026, 8, 27), 60),
        (date(2026, 10, 26), date(2026, 10, 26), 0),
        (date(2026, 10, 26), date(2026, 10, 29), -3),
    ],
)
def test_should_compute_remaining_support_days(until, today, expected):
    assert ic.age_days(until, today) == expected


def test_should_format_age_line_for_report():
    assert ic.format_age_line("2026.08", 60) == "Kohorte 2026.08: 60 Tage Support"
    assert (
        ic.format_age_line("2026.08", -3)
        == "Kohorte 2026.08: ABGELAUFEN (seit 3 Tagen)"
    )


# --------------------------------------------------------------------------
# Render / Parse
# --------------------------------------------------------------------------


def _resolutions():
    cands = ic.collect_candidates(FLAT, FLEET)
    return ic.resolve(
        cands,
        fetch=_fetcher(
            {
                "iil-aifw": ("ok", _payload("0.13.0", "2026-08-25T10:00:00Z")),
                "iil-django-commons": ("ok", _payload("0.3.0", "2026-03-24T15:56:10Z")),
            }
        ),
    )


def test_should_render_pin_line_with_strategy_and_release_date():
    text = ic.render_cohort(
        "2026.08", date(2026, 8, 27), date(2026, 10, 26), 60, _resolutions()
    )
    assert "iil-aifw==0.13.0  # strategy=aktiv, released=2026-08-25" in text
    assert (
        "iil-django-commons==0.3.0  # strategy=einfrieren, released=2026-03-24" in text
    )


def test_should_render_machine_readable_header():
    text = ic.render_cohort(
        "2026.08", date(2026, 8, 27), date(2026, 10, 26), 60, _resolutions()
    )
    header, pins = ic.parse_cohort(text)
    assert header["cohort"] == "2026.08"
    assert header["generated_at"] == "2026-08-27"
    assert header["support_until"] == "2026-10-26"
    assert header["support_days"] == "60"
    assert "registry/canonical.yaml" in header["source"]
    assert len(pins) == 2


def test_should_roundtrip_pins_through_parse():
    text = ic.render_cohort(
        "2026.08", date(2026, 8, 27), date(2026, 10, 26), 60, _resolutions()
    )
    _, pins = ic.parse_cohort(text)
    by_name = {p.name: p for p in pins}
    assert by_name["iil-aifw"].version == "0.13.0"
    assert by_name["iil-aifw"].strategy == "aktiv"
    assert by_name["iil-aifw"].released == "2026-08-25"
    assert by_name["iil-django-commons"].strategy == "einfrieren"


def test_should_name_missing_packages_in_header_instead_of_dropping_silently():
    cands = ic.collect_candidates(FLAT, FLEET)
    res = ic.resolve(
        cands,
        fetch=_fetcher(
            {
                "iil-aifw": ("ok", _payload("0.13.0")),
                "iil-django-commons": ("missing", None),
            }
        ),
    )
    text = ic.render_cohort("2026.08", date(2026, 8, 27), date(2026, 10, 26), 60, res)
    assert "excluded_not_on_pypi: iil-django-commons (einfrieren)" in text
    assert "iil-django-commons==" not in text
    _, pins = ic.parse_cohort(text)
    assert [p.name for p in pins] == ["iil-aifw"]


def test_should_count_packages_by_strategy_in_header():
    text = ic.render_cohort(
        "2026.08", date(2026, 8, 27), date(2026, 10, 26), 60, _resolutions()
    )
    header, _ = ic.parse_cohort(text)
    assert header["packages"] == "2 (1 aktiv, 1 eingefroren)"


# --------------------------------------------------------------------------
# resolve()
# --------------------------------------------------------------------------


def test_should_mark_unknown_when_pypi_does_not_answer():
    res = ic.resolve(
        ic.collect_candidates(FLAT, FLEET),
        fetch=_fetcher(
            {"iil-aifw": ("ok", _payload("0.13.0"))}
        ),  # commons fehlt -> unknown
    )
    states = {r.candidate.dist_name: r.state for r in res}
    assert states == {"iil-aifw": "ok", "iil-django-commons": "unknown"}


def test_should_treat_payload_without_version_as_unknown():
    res = ic.resolve(
        [ic.Candidate(repo="x", dist_name="iil-x", strategy="aktiv")],
        fetch=_fetcher({"iil-x": ("ok", {"info": {}})}),
    )
    assert res[0].state == "unknown"


# --------------------------------------------------------------------------
# build: die harte Zusage — `unbekannt` schreibt KEINE Kohorte
# --------------------------------------------------------------------------


def _build_args(tmp_path, **kw):
    base = dict(
        month="2026.08",
        support_days=60,
        out_dir=str(tmp_path),
        today="2026-08-27",
        strict_missing=False,
        dry_run=False,
    )
    base.update(kw)
    return argparse.Namespace(**base)


def test_should_not_write_cohort_when_a_package_is_unknown(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(ic, "load_sources", lambda: (FLAT, FLEET))
    monkeypatch.setattr(
        ic,
        "resolve",
        lambda c, fetch=None: [
            ic.Resolution(
                candidate=c[0], state="ok", version="0.13.0", released="2026-08-25"
            ),
            ic.Resolution(candidate=c[1], state="unknown", detail="URLError"),
        ],
    )
    rc = ic.cmd_build(_build_args(tmp_path))
    assert rc == 3
    assert list(tmp_path.iterdir()) == []
    err = capsys.readouterr().err
    assert "# unbekannt" in err
    assert "NICHT geschrieben" in err


def test_should_write_cohort_and_latest_pointer(tmp_path, monkeypatch):
    monkeypatch.setattr(ic, "load_sources", lambda: (FLAT, FLEET))
    monkeypatch.setattr(
        ic,
        "resolve",
        lambda c, fetch=None: [
            ic.Resolution(
                candidate=x, state="ok", version="1.0.0", released="2026-08-01"
            )
            for x in c
        ],
    )
    assert ic.cmd_build(_build_args(tmp_path)) == 0
    cohort = tmp_path / "iil-cohort-2026.08.txt"
    latest = tmp_path / ic.LATEST_NAME
    assert cohort.exists() and latest.exists()
    assert latest.read_text() == cohort.read_text()


def test_should_write_cohort_despite_404_but_fail_with_strict_missing(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(ic, "load_sources", lambda: (FLAT, FLEET))
    monkeypatch.setattr(
        ic,
        "resolve",
        lambda c, fetch=None: [
            ic.Resolution(
                candidate=c[0], state="ok", version="0.13.0", released="2026-08-25"
            ),
            ic.Resolution(candidate=c[1], state="missing", detail="HTTP 404"),
        ],
    )
    assert ic.cmd_build(_build_args(tmp_path)) == 0
    assert (tmp_path / "iil-cohort-2026.08.txt").exists()

    other = tmp_path / "strict"
    assert (
        ic.cmd_build(_build_args(other, out_dir=str(other), strict_missing=True)) == 3
    )
    assert not other.exists() or list(other.iterdir()) == []


# --------------------------------------------------------------------------
# age: das Alterungs-Signal
# --------------------------------------------------------------------------


def _write_cohort(tmp_path, until="2026-10-26"):
    p = tmp_path / "c.txt"
    p.write_text(
        f"# cohort: 2026.08\n# support_until: {until}\niil-aifw==0.13.0  # strategy=aktiv\n"
    )
    return p


def test_should_report_remaining_days_and_exit_zero(tmp_path, capsys):
    p = _write_cohort(tmp_path)
    rc = ic.cmd_age(argparse.Namespace(file=str(p), today="2026-09-26"))
    assert rc == 0
    assert capsys.readouterr().out.strip() == "Kohorte 2026.08: 30 Tage Support"


def test_should_exit_two_when_support_window_expired(tmp_path, capsys):
    p = _write_cohort(tmp_path)
    rc = ic.cmd_age(argparse.Namespace(file=str(p), today="2026-11-01"))
    assert rc == 2
    assert "ABGELAUFEN (seit 6 Tagen)" in capsys.readouterr().out


def test_should_exit_two_when_no_cohort_exists(tmp_path, capsys):
    rc = ic.cmd_age(
        argparse.Namespace(file=str(tmp_path / "fehlt.txt"), today="2026-08-27")
    )
    assert rc == 2
    assert "Kohorte fehlt" in capsys.readouterr().out


def test_should_exit_two_when_header_lacks_support_until(tmp_path, capsys):
    p = tmp_path / "c.txt"
    p.write_text("# cohort: 2026.08\niil-aifw==0.13.0\n")
    rc = ic.cmd_age(argparse.Namespace(file=str(p), today="2026-08-27"))
    assert rc == 2
    assert "kein support_until" in capsys.readouterr().out


# --------------------------------------------------------------------------
# Die echte, committete Kohorte (Regression gegen Hand-Edits)
# --------------------------------------------------------------------------


def test_should_keep_committed_cohort_parseable_and_pointing_to_latest():
    latest = ic.CONSTRAINTS_DIR / ic.LATEST_NAME
    if not latest.exists():
        pytest.skip("noch keine Kohorte committet")
    header, pins = ic.parse_cohort(latest.read_text())
    assert header["cohort"] and header["support_until"] and header["support_days"]
    assert pins, "Zeiger ohne Pins"
    named = ic.CONSTRAINTS_DIR / f"iil-cohort-{header['cohort']}.txt"
    assert named.exists(), f"Zeiger nennt {header['cohort']}, Datei fehlt"
    assert named.read_text() == latest.read_text()
    assert all(p.strategy in ("aktiv", "einfrieren") for p in pins)
