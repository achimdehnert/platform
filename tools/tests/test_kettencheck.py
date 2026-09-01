"""Tests für den Ketten-Melder (#2176 Kriterium 6).

Geprüft wird, ob der Melder den **Ort** benennt — nicht, ob er überhaupt etwas
sagt. „Etwas ist kaputt" wäre kein bestandener Test.
"""

import importlib.util
import json
import pathlib
import sys
import os
from datetime import date, datetime, timedelta

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
        # mtime explizit auf HEUTE setzen: die reale Uhr darf das Alter nicht bestimmen
        # (Zeitbombe 2026-08-28: HEUTE ist fix, die Datei war ploetzlich "frisch").
        ts = datetime.combine(HEUTE, datetime.min.time()).timestamp()
        os.utime(p, (ts, ts))
        befund = kc.pruefe_artefakt(
            "Board", p, HEUTE + timedelta(days=9), "make boards"
        )
        assert not befund.ok
        assert "Tage alt" in befund.ort
        assert befund.hinweis == "make boards"

    def test_should_flag_a_file_dated_in_the_future(self, tmp_path):
        """Ein Alarm, der Unmoegliches durchwinkt, prueft die falsche Richtung."""
        p = tmp_path / "board.md"
        p.write_text("x", encoding="utf-8")
        befund = kc.pruefe_artefakt(
            "Board", p, HEUTE - timedelta(days=5), "make boards"
        )
        assert not befund.ok
        assert "Zukunft" in befund.ort

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
        befund = kc.pruefe_dienst("Ansicht", "http://127.0.0.1:1/", "egal", "restart")
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


class TestReferenzen:
    """Zwei neue Glieder (#2592): Ordner-Pflicht und Verankerung je Referenz."""

    def _dateien(self, tmp_path, notiz, anker):
        ledger = tmp_path / "ledger.json"
        ledger.write_text(
            json.dumps({"vorgaenge": [{"nr": 1, "konto": "hnu", "notiz": notiz}]}),
            encoding="utf-8",
        )
        archiv = tmp_path / "archiv.json"
        anker_datei = tmp_path / "anker.json"
        anker_datei.write_text(json.dumps({k: {} for k in anker}), encoding="utf-8")
        return ledger, archiv, anker_datei

    def test_should_pass_when_every_number_has_folder_and_anchor(self, tmp_path):
        dateien = self._dateien(
            tmp_path, "2026-09-05: Klimm (INBOX #164024)", ["hnu-inbox-164024"]
        )
        befunde = kc.pruefe_referenzen(*dateien)
        assert [b.ok for b in befunde] == [True, True]
        assert "1 von 1" in befunde[1].ort

    def test_should_break_the_folder_link_for_a_bare_number_after_the_cutoff(
        self, tmp_path
    ):
        dateien = self._dateien(
            tmp_path, "2026-09-05: Entwurf UID 23611 liegt", ["hnu-23611"]
        )
        ordner, anker = kc.pruefe_referenzen(*dateien)
        assert not ordner.ok
        assert "referenzen.py --pruefe-ordner" in ordner.hinweis
        assert anker.ok

    def test_should_not_blame_an_entry_from_before_the_cutoff(self, tmp_path):
        dateien = self._dateien(
            tmp_path, "2026-08-10: Entwurf UID 23611 liegt", ["hnu-23611"]
        )
        ordner, _ = kc.pruefe_referenzen(*dateien)
        assert ordner.ok
        assert "1 Altbestand" in ordner.ort

    def test_should_break_the_anchor_link_for_an_unanchored_number(self, tmp_path):
        dateien = self._dateien(tmp_path, "2026-09-05: Klimm (INBOX #164024)", [])
        _, anker = kc.pruefe_referenzen(*dateien)
        assert not anker.ok
        assert "eintrag_anker.py" in anker.hinweis
        assert "0 von 1" in anker.ort
