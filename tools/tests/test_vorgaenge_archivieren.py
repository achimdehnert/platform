"""Tests für das Archivieren erledigter Vorgänge.

Synthetische Fixtures — dieses Repo ist öffentlich.
"""

import importlib.util
import json
import pathlib
import sys
from datetime import date

_SRC = (
    pathlib.Path(__file__).resolve().parents[1]
    / "mail_agent"
    / "vorgaenge_archivieren.py"
)
_spec = importlib.util.spec_from_file_location("vorgaenge_archivieren", _SRC)
va = importlib.util.module_from_spec(_spec)
sys.modules["vorgaenge_archivieren"] = va
_spec.loader.exec_module(va)

HEUTE = date(2026, 8, 21)


def _v(nr=1, bucket="erledigt", **kv):
    basis = {
        "nr": nr,
        "bucket": bucket,
        "kurz": "irgendwas",
        "letzte_pruefung": "2026-08-10",
    }
    basis.update(kv)
    return basis


class TestReif:
    def test_should_archive_a_closed_vorgang_after_the_grace_period(self):
        assert va.reif(_v(erledigt_am="2026-08-10"), HEUTE) is True

    def test_should_keep_a_freshly_closed_vorgang(self):
        """Drei Tage decken 'ich schaue Montag nochmal nach' ab."""
        assert va.reif(_v(erledigt_am="2026-08-20"), HEUTE) is False

    def test_should_never_touch_an_open_vorgang(self):
        assert va.reif(_v(bucket="owner", erledigt_am="2026-01-01"), HEUTE) is False

    def test_should_leave_a_vorgang_without_any_date(self):
        """Ohne Datum keine automatische Bewegung."""
        v = {"nr": 1, "bucket": "erledigt"}
        assert va.reif(v, HEUTE) is False

    def test_should_fall_back_to_the_last_check_date(self):
        assert va.reif(_v(letzte_pruefung="2026-08-01"), HEUTE) is True


class TestTitellose:
    def test_should_report_an_open_vorgang_without_a_title(self):
        ledger = {"vorgaenge": [_v(nr=7, bucket="owner", kurz=None)]}
        assert va.ohne_titel(ledger) == [7]

    def test_should_ignore_closed_ones(self):
        ledger = {"vorgaenge": [_v(nr=7, kurz="")]}
        assert va.ohne_titel(ledger) == []

    def test_should_treat_whitespace_as_missing(self):
        ledger = {"vorgaenge": [_v(nr=7, bucket="warten", kurz="   ")]}
        assert va.ohne_titel(ledger) == [7]


class TestTeilen:
    def test_should_split_ledger_into_stay_and_move(self):
        ledger = {
            "vorgaenge": [
                _v(nr=1, erledigt_am="2026-08-01"),
                _v(nr=2, bucket="owner"),
                _v(nr=3, erledigt_am="2026-08-21"),
            ]
        }
        bleibt, wandert = va.teile(ledger, HEUTE)
        assert [v["nr"] for v in wandert] == [1]
        assert [v["nr"] for v in bleibt] == [2, 3]


def test_should_not_lose_anything_in_a_roundtrip(tmp_path):
    """Archivieren heisst verschieben — die Summe bleibt gleich."""
    ledger = {
        "vorgaenge": [_v(nr=1, erledigt_am="2026-08-01"), _v(nr=2, bucket="owner")]
    }
    bleibt, wandert = va.teile(ledger, HEUTE)
    datei = tmp_path / "a.json"
    datei.write_text(
        json.dumps({"vorgaenge": wandert}, ensure_ascii=False), encoding="utf-8"
    )
    zurueck = json.loads(datei.read_text(encoding="utf-8"))["vorgaenge"]
    assert len(bleibt) + len(zurueck) == len(ledger["vorgaenge"])
