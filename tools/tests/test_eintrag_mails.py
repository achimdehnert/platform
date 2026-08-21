"""Tests für die Zuordnung Verlaufseintrag → Mail.

Kein Index-Zugriff: geprüft wird die Zuordnung, nicht die Leitung. Fixtures sind
synthetisch — dieses Repo ist öffentlich.
"""

import importlib.util
import pathlib
import sys
from datetime import date

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "eintrag_mails.py"
_spec = importlib.util.spec_from_file_location("eintrag_mails", _SRC)
em = importlib.util.module_from_spec(_spec)
sys.modules["eintrag_mails"] = em
_spec.loader.exec_module(em)


def _msg(datum, betreff, ordner="Posteingang", id_=1):
    return {"datum": datum, "betreff": betreff, "ordner": [ordner], "id": id_}


class TestNormalisieren:
    def test_should_strip_reply_prefixes(self):
        assert em.normalisiere("AW: Re: Betreff") == "betreff"

    def test_should_collapse_whitespace(self):
        assert em.normalisiere("  Ein   Betreff ") == "ein betreff"


class TestDatum:
    def test_should_prefer_the_event_date_over_the_note_date(self):
        """Der Eintrag beginnt mit dem Datum der Notiz, meint aber die Kurzform."""
        text = "2026-08-21: Eigene Antwort 14.08. 05:23 im Nachbarstrang"
        assert em.eintrags_datum(text, 2026) == date(2026, 8, 14)

    def test_should_fall_back_to_the_iso_date(self):
        assert em.eintrags_datum("2026-08-21: irgendwas", 2026) == date(2026, 8, 21)

    def test_should_return_nothing_without_a_date(self):
        assert em.eintrags_datum("kein Datum hier", 2026) is None


class TestTreffer:
    def _nachrichten(self):
        return [
            _msg(
                "2026-08-14", "AW: Besprechungszusammenfassung", "Gesendete Objekte", 1
            ),
            _msg("2026-08-14", "Besprechungszusammenfassung", "Posteingang", 2),
        ]

    def test_should_match_subject_and_day(self):
        text = "2026-08-21: Antwort 14.08. zu 'Besprechungszusammenfassung'"
        m = em.treffer(text, [self._nachrichten()[1]], 2026)
        assert m and m["id"] == 2

    def test_should_use_direction_when_two_match(self):
        text = "2026-08-21: Eigene Antwort 14.08. 05:23 'Besprechungszusammenfassung'"
        m = em.treffer(text, self._nachrichten(), 2026)
        assert m and m["id"] == 1, "die eigene Antwort liegt im Sendeordner"

    def test_should_refuse_when_ambiguous(self):
        """Zwei gleiche Richtungen am selben Tag — lieber kein Treffer."""
        nachrichten = [
            _msg("2026-08-14", "Themenblock", "Posteingang", 1),
            _msg("2026-08-14", "AW: Themenblock", "Posteingang", 2),
        ]
        text = "2026-08-21: Rueckmeldung 14.08. zu 'Themenblock'"
        assert em.treffer(text, nachrichten, 2026) is None

    def test_should_need_a_quoted_subject(self):
        assert (
            em.treffer("2026-08-14: irgendwas ohne Betreff", self._nachrichten(), 2026)
            is None
        )


class TestUrl:
    def test_should_link_an_inbox_uid_from_the_text(self):
        url = em.url_aus_text(
            "Klimm 20.08. (INBOX #164024)", "hnu", "https://m.example"
        )
        assert url == "https://m.example/m/hnu/164024"

    def test_should_link_a_sent_number_into_the_sent_folder(self):
        url = em.url_aus_text(
            "Beleg im Ordner 'Gesendete Objekte' (#34349)", "hnu", "https://m.example"
        )
        assert url == "https://m.example/m/hnu/gesendete/34349"

    def test_should_stay_silent_without_an_addressable_number(self):
        """Der Index liefert nur eine Datenbank-Id — daraus gebaute Links waren 404."""
        assert (
            em.url_aus_text("Eigene Antwort 14.08. 05:23", "hnu", "https://m.example")
            == ""
        )

    def test_should_stay_silent_without_an_account(self):
        assert em.url_aus_text("UID 12345", "", "https://m.example") == ""


def test_should_number_entries_from_the_oldest_end():
    # Betreff mit mindestens sechs Zeichen: kuerzere Zitate sind zu oft Rauschen
    # ('AW:', 'ok'), und ein Fehltreffer waere schlimmer als eine Luecke.
    ledger = {
        "vorgaenge": [
            {"nr": 9, "konto": "hnu", "notiz": "alt | neu 'Themenblock' 14.08."}
        ]
    }
    nachrichten = [_msg("2026-08-14", "Themenblock")]
    zuordnung = em.zuordnen(ledger, {}, nachrichten, "https://m.example")
    assert list(zuordnung["9"].keys()) == ["2"], "der zweite Eintrag ist gemeint"
