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
    """Der Kopfzeilen-Link zeigt nur auf Verankertes (#2592 K2)."""

    ANKER = frozenset({"hnu-inbox-164024", "hnu-gesendete-objekte-34349"})

    def test_should_link_an_anchored_inbox_uid_over_the_message_id_route(self):
        url = em.url_aus_text(
            "Klimm 20.08. (INBOX #164024)", "hnu", "https://m.example", self.ANKER
        )
        assert url == "https://m.example/a/hnu-inbox-164024"

    def test_should_link_a_sent_number_through_its_anchor(self):
        url = em.url_aus_text(
            "Beleg im Ordner 'Gesendete Objekte' (#34349)",
            "hnu",
            "https://m.example",
            self.ANKER,
        )
        assert url == "https://m.example/a/hnu-gesendete-objekte-34349"

    def test_should_stay_silent_for_an_unanchored_number(self):
        """Bis 2026-09-01 entstand hier `/m/hnu/entwuerfe/23611` — tot nach dem
        naechsten Ersetzen des Entwurfs. Ohne Anker kein Link."""
        assert (
            em.url_aus_text(
                "Entwuerfe #23611 liegt", "hnu", "https://m.example", self.ANKER
            )
            == ""
        )

    def test_should_stay_silent_without_an_addressable_number(self):
        """Der Index liefert nur eine Datenbank-Id — daraus gebaute Links waren 404."""
        assert (
            em.url_aus_text(
                "Eigene Antwort 14.08. 05:23", "hnu", "https://m.example", self.ANKER
            )
            == ""
        )

    def test_should_not_read_a_repo_issue_as_a_mail_uid(self):
        """`platform#2176` ist kein Postfach. Reproduziert in der Retro 2026-08-21."""
        anker = frozenset({"hnu-2176", "hnu-1460"})
        assert (
            em.url_aus_text("Siehe platform#2176", "hnu", "https://m.example", anker)
            == ""
        )
        assert (
            em.url_aus_text("Bezug: meiki-hub#1460", "hnu", "https://m.example", anker)
            == ""
        )

    def test_should_stay_silent_without_an_account(self):
        assert (
            em.url_aus_text("UID 12345", "", "https://m.example", frozenset({"-12345"}))
            == ""
        )

    def test_should_read_the_anchor_file_when_no_set_is_given(
        self, tmp_path, monkeypatch
    ):
        datei = tmp_path / "anker.json"
        datei.write_text('{"hnu-inbox-7007": {}}', encoding="utf-8")
        monkeypatch.setattr(em, "ANKER_DATEI", datei)
        assert (
            em.url_aus_text("INBOX #7007", "hnu", "https://m.example")
            == "https://m.example/a/hnu-inbox-7007"
        )
