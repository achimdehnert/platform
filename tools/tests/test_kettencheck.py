"""Tests für den Ketten-Melder (#2176 Kriterium 6).

Geprüft wird, ob der Melder den **Ort** benennt — nicht, ob er überhaupt etwas
sagt. „Etwas ist kaputt" wäre kein bestandener Test.
"""

import importlib.util
import json
import pathlib
import sys
from datetime import date, timedelta

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "kettencheck.py"
_spec = importlib.util.spec_from_file_location("kettencheck", _SRC)
kc = importlib.util.module_from_spec(_spec)
sys.modules["kettencheck"] = kc
_spec.loader.exec_module(kc)

HEUTE = date(2026, 8, 21)


class TestLedger:
    def test_should_pass_on_a_healthy_ledger(self, tmp_path):
        p = tmp_path / "l.json"
        p.write_text('{"vorgaenge": [{"nr": 1}]}', encoding="utf-8")
        befund = kc.pruefe_ledger(HEUTE, p)
        assert befund.ok and "1 Vorgaenge" in befund.ort

    def test_should_name_the_line_of_broken_json(self, tmp_path):
        """Der Ort ist die Stelle im JSON, nicht 'Ledger kaputt'."""
        p = tmp_path / "l.json"
        p.write_text('{"vorgaenge": [', encoding="utf-8")
        befund = kc.pruefe_ledger(HEUTE, p)
        assert not befund.ok
        assert "gueltiges JSON" in befund.ort and ":" in befund.ort

    def test_should_flag_a_missing_ledger(self, tmp_path):
        befund = kc.pruefe_ledger(HEUTE, tmp_path / "fehlt.json")
        assert not befund.ok and "fehlt" in befund.ort

    def test_should_flag_an_empty_ledger(self, tmp_path):
        p = tmp_path / "l.json"
        p.write_text('{"vorgaenge": []}', encoding="utf-8")
        assert not kc.pruefe_ledger(HEUTE, p).ok


class TestArtefakte:
    def test_should_flag_a_stale_artefact_with_its_age(self, tmp_path):
        p = tmp_path / "board.md"
        p.write_text("x", encoding="utf-8")
        befund = kc.pruefe_artefakt("Board", p, HEUTE + timedelta(days=9), "make boards")
        assert not befund.ok
        assert "Tage alt" in befund.ort
        assert befund.hinweis == "make boards"

    def test_should_accept_a_fresh_artefact(self, tmp_path):
        p = tmp_path / "board.md"
        p.write_text("x", encoding="utf-8")
        assert kc.pruefe_artefakt("Board", p, date.today(), "make boards").ok

    def test_should_flag_an_empty_forecast(self, tmp_path):
        p = tmp_path / "f.json"
        p.write_text("{}", encoding="utf-8")
        befund = kc.pruefe_vorhersage(date.today(), p)
        assert not befund.ok and "leer" in befund.ort

    def test_should_count_the_forecast_entries(self, tmp_path):
        p = tmp_path / "f.json"
        p.write_text(json.dumps({"1": {"erwartet": "2026-08-22"}}), encoding="utf-8")
        assert kc.pruefe_vorhersage(date.today(), p).ok


class TestDienst:
    def test_should_name_the_url_when_unreachable(self):
        befund = kc.pruefe_dienst(
            "Ansicht", "http://127.0.0.1:1/", "egal", "restart"
        )
        assert not befund.ok
        assert "http://127.0.0.1:1/" in befund.ort
        assert befund.hinweis == "restart"


def test_should_report_every_broken_link_by_name(tmp_path, monkeypatch):
    """Der Bericht nennt die gebrochenen Glieder einzeln, nicht als Summe."""
    monkeypatch.setattr(kc, "LEDGER", tmp_path / "fehlt.json")
    monkeypatch.setattr(kc, "FAELLIGKEIT", tmp_path / "fehlt2.json")
    monkeypatch.setattr(kc, "ACTION_BOARD", tmp_path / "fehlt3.md")
    monkeypatch.setattr(kc, "TODO_HTML", tmp_path / "fehlt4.html")
    befunde = kc.alle(HEUTE, mit_index=False)
    kaputt = {b.glied for b in befunde if not b.ok}
    assert {"Ledger", "Vorhersage", "Board", "Todo-HTML"} <= kaputt
