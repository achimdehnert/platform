"""Tests fuer den hygiene-melder.

Ein SessionStart-Melder darf unter keinen Umstaenden blockieren und im Normalfall
nichts sagen — sonst wird er nach drei Tagen ignoriert. Die Faelle unten pruefen
deshalb vor allem: schweigt er, wenn alles in Ordnung ist, und ueberlebt er
kaputte Eingaben.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import io
import json
import pathlib
import sys

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "hygiene_melder.py"
_spec = importlib.util.spec_from_file_location("hygiene_melder", _SRC)
hm = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = hm
_spec.loader.exec_module(hm)

JETZT = dt.datetime(2026, 8, 2, 12, 0, tzinfo=dt.timezone.utc)


def lease(d: pathlib.Path, name: str, expires: str | None) -> pathlib.Path:
    p = d / f"{name}.json"
    p.write_text(json.dumps({"repo": "x", "expires_at": expires}), encoding="utf-8")
    return p


@pytest.fixture()
def stdin_leer(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))


# --- Leases ------------------------------------------------------------------


def test_should_find_no_expired_lease_in_an_empty_dir(tmp_path):
    assert hm.abgelaufene_leases(JETZT, tmp_path) == []


def test_should_report_an_expired_lease_with_its_age(tmp_path):
    lease(tmp_path, "alt", "2026-07-26T12:00:00+00:00")

    assert hm.abgelaufene_leases(JETZT, tmp_path) == [("alt", 7)]


def test_should_ignore_a_lease_that_is_still_valid(tmp_path):
    lease(tmp_path, "frisch", "2026-08-09T12:00:00+00:00")

    assert hm.abgelaufene_leases(JETZT, tmp_path) == []


def test_should_sort_the_oldest_lease_first(tmp_path):
    lease(tmp_path, "a", "2026-07-30T12:00:00+00:00")
    lease(tmp_path, "b", "2026-06-01T12:00:00+00:00")

    assert [n for n, _ in hm.abgelaufene_leases(JETZT, tmp_path)] == ["b", "a"]


def test_should_accept_a_zulu_timestamp(tmp_path):
    lease(tmp_path, "z", "2026-07-26T12:00:00Z")

    assert hm.abgelaufene_leases(JETZT, tmp_path) == [("z", 7)]


def test_should_treat_a_naive_timestamp_as_utc(tmp_path):
    lease(tmp_path, "naiv", "2026-07-26T12:00:00")

    assert hm.abgelaufene_leases(JETZT, tmp_path) == [("naiv", 7)]


@pytest.mark.parametrize("wert", [None, "", "kein-datum"])
def test_should_skip_a_lease_without_a_usable_expiry(tmp_path, wert):
    lease(tmp_path, "kaputt", wert)

    assert hm.abgelaufene_leases(JETZT, tmp_path) == []


def test_should_skip_unreadable_json(tmp_path):
    (tmp_path / "muell.json").write_text("{{{", encoding="utf-8")

    assert hm.abgelaufene_leases(JETZT, tmp_path) == []


def test_should_return_empty_for_a_missing_lease_dir(tmp_path):
    assert hm.abgelaufene_leases(JETZT, tmp_path / "gibtsnicht") == []


# --- Kopien-Drift ------------------------------------------------------------


@pytest.fixture()
def welt(tmp_path):
    platform = tmp_path / "platform" / "tools" / "claude-hooks"
    platform.mkdir(parents=True)
    kopien = tmp_path / "hooks"
    kopien.mkdir()
    return tmp_path / "platform", platform, kopien


def test_should_report_no_drift_for_identical_files(welt):
    wurzel, quelle, kopien = welt
    (quelle / "a.py").write_text("gleich\n", encoding="utf-8")
    (kopien / "a.py").write_text("gleich\n", encoding="utf-8")

    assert hm.driftende_kopien(wurzel, kopien) == []


def test_should_report_a_diverging_copy(welt):
    wurzel, quelle, kopien = welt
    (quelle / "a.py").write_text("neu\n", encoding="utf-8")
    (kopien / "a.py").write_text("alt\n", encoding="utf-8")

    assert hm.driftende_kopien(wurzel, kopien) == ["a.py"]


def test_should_ignore_a_copy_without_a_source(welt):
    """Nur lokal vorhandene Hooks sind kein Drift — sie haben keine Quelle."""
    wurzel, _, kopien = welt
    (kopien / "nur-lokal.py").write_text("x\n", encoding="utf-8")

    assert hm.driftende_kopien(wurzel, kopien) == []


def test_should_also_look_in_the_second_source_dir(welt):
    wurzel, _, kopien = welt
    zweite = wurzel / "tools" / "hooks"
    zweite.mkdir(parents=True)
    (zweite / "b.sh").write_text("neu\n", encoding="utf-8")
    (kopien / "b.sh").write_text("alt\n", encoding="utf-8")

    assert hm.driftende_kopien(wurzel, kopien) == ["b.sh"]


def test_should_return_empty_when_the_copy_dir_is_missing(welt):
    wurzel, _, _ = welt

    assert hm.driftende_kopien(wurzel, wurzel / "gibtsnicht") == []


# --- main(): schweigen im Normalfall, nie blockieren -------------------------


def test_should_stay_silent_when_everything_is_healthy(tmp_path, capsys, stdin_leer):
    (tmp_path / "leases").mkdir()

    rc = hm.main(["--platform", str(tmp_path), "--leases", str(tmp_path / "leases")])

    assert rc == 0
    assert capsys.readouterr().out == ""


def test_should_report_expired_leases_via_additional_context(
    tmp_path, capsys, stdin_leer
):
    d = tmp_path / "leases"
    d.mkdir()
    lease(d, "alt", "2026-01-01T00:00:00+00:00")

    hm.main(["--platform", str(tmp_path), "--leases", str(d)])

    text = json.loads(capsys.readouterr().out)["hookSpecificOutput"][
        "additionalContext"
    ]
    assert "abgelaufene repo-session-Leases" in text
    assert "dirty Baeume bleiben bewusst stehen" in text


def test_should_exit_0_on_broken_stdin(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("kein json {{{"))
    (tmp_path / "leases").mkdir()

    assert (
        hm.main(["--platform", str(tmp_path), "--leases", str(tmp_path / "leases")])
        == 0
    )


def test_should_exit_0_when_nothing_exists_at_all(tmp_path, stdin_leer):
    assert (
        hm.main(
            ["--platform", str(tmp_path / "weg"), "--leases", str(tmp_path / "weg")]
        )
        == 0
    )
