"""Tests für die Fälligkeits-Vorhersage (#2176 Kriterium 5).

Kein Zugriff auf den Mail-Index: geprüft wird die Rechnung, nicht die Leitung.
Die Fixtures sind synthetisch — dieses Repo ist öffentlich.
"""

import importlib.util
import pathlib
import sys
from datetime import date

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "faelligkeit.py"
_spec = importlib.util.spec_from_file_location("faelligkeit", _SRC)
fk = importlib.util.module_from_spec(_spec)
sys.modules["faelligkeit"] = fk
_spec.loader.exec_module(fk)


def _msg(datum: str, ordner: str, von: str = "wer@beispiel.example", strang: str = "s1"):
    return {"datum": datum, "ordner": [ordner], "von": von, "strang": strang}


class TestPaare:
    def test_should_measure_the_gap_between_send_and_reply(self):
        p = fk.paare(
            [
                _msg("2026-08-01", "Gesendete Elemente"),
                _msg("2026-08-04", "Posteingang"),
            ]
        )
        assert [x.tage for x in p] == [3]

    def test_should_ignore_a_reply_without_a_preceding_send(self):
        """Ein Eingang ohne eigenen Versand davor misst keine Antwortzeit."""
        assert fk.paare([_msg("2026-08-04", "Posteingang")]) == []

    def test_should_keep_threads_apart(self):
        p = fk.paare(
            [
                _msg("2026-08-01", "Gesendete Elemente", strang="a"),
                _msg("2026-08-02", "Posteingang", strang="b"),
            ]
        )
        assert p == [], "der Eingang gehoert zu einem anderen Strang"

    def test_should_drop_absurdly_long_gaps(self):
        """Nach 90 Tagen ist es kein Antwortverhalten mehr, sondern ein neuer Vorgang."""
        p = fk.paare(
            [
                _msg("2026-01-01", "Gesendete Elemente"),
                _msg("2026-08-01", "Posteingang"),
            ]
        )
        assert p == []


class TestProfil:
    def _paare(self, tage, adresse="a@b.example"):
        return [fk.Paar(t, adresse.split("@")[-1], adresse) for t in tage]

    def test_should_use_the_own_address_when_there_is_enough_history(self):
        p = self._paare([1, 2, 3])
        erwartet, grenze, quelle = fk.profil(p, adresse="a@b.example")
        assert quelle.startswith("Adresse")
        assert erwartet <= grenze

    def test_should_fall_back_to_the_fleet_below_the_threshold(self):
        p = self._paare([1, 2])
        _, _, quelle = fk.profil(p, adresse="a@b.example")
        assert quelle.startswith("Flotte")

    def test_should_separate_expectation_from_overdue(self):
        """Median und 90-Prozent-Quantil duerfen nicht dasselbe sein."""
        p = self._paare([0, 0, 0, 1, 2, 9])
        erwartet, grenze, _ = fk.profil(p)
        assert erwartet < grenze


class TestLetzterVersand:
    def test_should_find_the_newest_send_entry(self):
        v = {"nr": 7, "notiz": "2026-08-01 GESENDET x | 2026-08-05 GESENDET y"}
        assert fk.letzter_versand(v) == date(2026, 8, 5)

    def test_should_also_look_into_the_archive(self):
        """Nach der Kappung steht der Versand oft nur noch im Archiv."""
        v = {"nr": 7, "notiz": "2026-08-05: kein neuer Eingang"}
        archiv = {"7": ["2026-08-01 GESENDET x"]}
        assert fk.letzter_versand(v, archiv) == date(2026, 8, 1)

    def test_should_return_nothing_without_a_send(self):
        assert fk.letzter_versand({"nr": 7, "notiz": "2026-08-05: gelesen"}) is None


def test_should_report_its_own_error_in_the_backtest():
    paare = [fk.Paar(t, "b.example", "a@b.example") for t in [0, 0, 1, 2, 3, 6, 11]]
    e = fk.backtest(paare)
    assert e["genug"] is True
    assert e["paare"] == 7
    assert 0 <= e["deckung_prozent"] <= 100


def test_should_refuse_a_statement_on_thin_history():
    """Vier Datenpunkte sind keine Aussage — das Werkzeug sagt das, statt zu raten."""
    assert fk.backtest([fk.Paar(1, "b", "a@b")] * 4)["genug"] is False


class TestQuantilBeiWenigDaten:
    """Ein 90-%-Quantil aus drei Werten ist das Maximum, kein Quantil."""

    def test_should_not_return_the_maximum_as_a_90_percent_quantile(self):
        assert fk.quantil([0, 0, 12], 0.9) < 12

    def test_should_interpolate_between_neighbours(self):
        assert fk.quantil([0, 10], 0.5) == 5

    def test_should_take_the_limit_from_the_fleet_when_the_own_history_is_thin(self):
        eigene = [fk.Paar(t, "b.example", "a@b.example") for t in (0, 0, 12)]
        flotte = [fk.Paar(t, "x.example", "z@x.example") for t in range(12)]
        _, grenze, quelle = fk.profil(eigene + flotte, adresse="a@b.example")
        assert "Flotte" in quelle
        assert grenze <= 12
