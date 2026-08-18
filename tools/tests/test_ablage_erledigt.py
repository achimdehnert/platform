"""Tests für tools/mail_agent/ablage_erledigt.py — Zielauflösung, kein Schreibpfad.

Geprüft wird die Frage, an der die Automatik scheitern würde: Landet eine Mail in
der richtigen Schublade, und wird zugegeben, wenn keine passt? Kein Test fasst ein
Postfach an; der Ordnerbestand wird hereingereicht.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))

ablage = pytest.importorskip("ablage_erledigt")

IIL_ORDNER = [
    "Archiv/2025",
    "Archiv/2026",
    "IIL.Kunden/Talmuehle",
    "IIL.Kunden/Talmuehle/offen",
    "IIL.Kunden/Nordwind",
    "IIL.Kunden/Kastenmayer",
    "IIL.Kunden/Bärlach",
    "IIL.Kunden/Seewald",
]
HNU_ORDNER = [
    "Archiv/2026",
    "Betreuungen/Winterhalt-Nele-Sophie",
    "Betreuungen/.erledigt/Alt-Marius",
    "Betreuungen/Rosenbaum-Lea",
]


def _v(**felder):
    grund = {
        "konto": "iil",
        "bucket": "erledigt",
        "erledigt_am": "2026-08-18",
        "typ": "vorgang",
        "kurz": "K",
        "nr": 1,
    }
    return {**grund, **felder}


class TestZielauflösung:
    def test_should_prefer_an_explicit_target_written_into_the_vorgang(self):
        """Die Ansage des Owners sticht jede Konvention."""
        ziel, herkunft = ablage.ziel_fuer(
            _v(ablage_ziel="IIL.Kunden/Kastenmayer", gegenueber="Seewald"),
            IIL_ORDNER,
            {},
        )
        assert ziel == "IIL.Kunden/Kastenmayer"
        assert "ansage" in herkunft

    def test_should_find_the_customer_folder_from_the_counterpart(self):
        ziel, herkunft = ablage.ziel_fuer(
            _v(gegenueber="Seewald GmbH / m.beispiel@seewald.example"),
            IIL_ORDNER,
            {},
        )
        assert ziel == "IIL.Kunden/Seewald"
        assert "ordnerbestand" in herkunft

    def test_should_match_a_student_folder_despite_different_name_shape(self):
        """'Winterhalt, Nele Sophie' und 'Winterhalt-Nele-Sophie' sind derselbe Mensch."""
        ziel, _ = ablage.ziel_fuer(
            _v(konto="hnu", typ="betreuung-masterarbeit",
               gegenueber="HNU / N. S. Winterhalt (Masterthesis)"),
            HNU_ORDNER,
            {},
        )
        assert ziel == "Betreuungen/Winterhalt-Nele-Sophie"

    def test_should_fall_back_to_the_year_archive(self):
        ziel, herkunft = ablage.ziel_fuer(
            _v(gegenueber="Jemand voellig Unbekanntes"), IIL_ORDNER, {}
        )
        assert ziel == "Archiv/2026"
        assert herkunft == "jahresarchiv"

    def test_should_prefer_the_shorter_folder_over_its_subfolder(self):
        """Ein Ordner und sein Unterordner sind keine echte Mehrdeutigkeit."""
        ziel, _ = ablage.ziel_fuer(_v(gegenueber="Talmuehle GmbH"), IIL_ORDNER, {})
        assert ziel == "IIL.Kunden/Talmuehle"

    def test_should_refuse_to_guess_when_two_unrelated_folders_match(self):
        ordner = ["IIL.Kunden/Meier-Bau", "IIL.Kunden/Meier-Handel"]
        assert ablage.ordner_finden("Meier", ordner, "IIL.Kunden/") is None

    def test_should_never_target_the_done_subtree_of_the_supervision_folders(self):
        """Ein geschlossener Vorgang gehört in den laufenden Ordner, nicht nach .erledigt."""
        ziel, _ = ablage.ziel_fuer(
            _v(konto="hnu", typ="betreuung", gegenueber="Marius Alt"), HNU_ORDNER, {}
        )
        assert ziel is None or not ziel.startswith("Betreuungen/.erledigt")


class TestPlan:
    def _plane(self, vorgang, anker=None, ordner=None):
        return ablage.plane(
            {"vorgaenge": [vorgang]},
            anker if anker is not None else {"1": {}},
            ordner if ordner is not None else {"iil": IIL_ORDNER, "hnu": HNU_ORDNER},
        )

    def test_should_ignore_open_vorgaenge(self):
        assert self._plane(_v(bucket="owner")) == []

    def test_should_mark_a_row_ready_when_folder_and_anchor_exist(self):
        (zeile,) = self._plane(_v(gegenueber="Kastenmayer Technik"))
        assert zeile.status == "bereit"
        assert zeile.ziel == "IIL.Kunden/Kastenmayer"

    def test_should_report_a_missing_target_folder_instead_of_creating_it(self):
        (zeile,) = self._plane(_v(erledigt_am="2019-03-01", gegenueber="Unbekannt"))
        assert zeile.status == "ordner_fehlt"
        assert zeile.ziel == "Archiv/2019"

    def test_should_report_a_missing_anchor(self):
        (zeile,) = self._plane(_v(gegenueber="Kastenmayer"), anker={})
        assert zeile.status == "kein_anker"

    def test_should_report_a_closure_without_a_date(self):
        vorgang = _v(gegenueber="Kastenmayer")
        del vorgang["erledigt_am"]
        (zeile,) = self._plane(vorgang)
        assert zeile.status == "kein_datum"


class TestBericht:
    def test_should_state_plainly_that_nothing_was_moved(self):
        text = ablage.bericht(
            ablage.plane(
                {"vorgaenge": [_v(gegenueber="Kastenmayer")]},
                {"1": {}},
                {"iil": IIL_ORDNER},
            )
        )
        assert "nichts verschoben" in text

    def test_should_say_so_when_there_is_nothing_to_plan(self):
        assert "Kein geschlossener Vorgang" in ablage.bericht([])


class TestUmlautschreibweisen:
    """Gemessen im Trockenlauf am 2026-08-18: Umlaut- und Umschrift-Schreibweise fanden sich nicht.

    Reine Diakritika-Entfernung macht aus beiden verschiedene Zeichenketten. Der Vorgang
    wäre still im Jahresarchiv gelandet statt beim Kunden — ein Fehler, den man
    erst bemerkt, wenn man die Mail sucht.
    """

    def test_should_match_umlaut_and_transcribed_spelling(self):
        assert ablage._slug("Bärlach") == ablage._slug("Baerlach")

    def test_should_find_the_customer_folder_despite_the_spelling_difference(self):
        ziel, _ = ablage.ziel_fuer(
            _v(gegenueber="Baerlach Technik / S. Beispiel"), IIL_ORDNER, {}
        )
        assert ziel == "IIL.Kunden/Bärlach"

    def test_should_still_separate_names_that_only_look_similar(self):
        assert ablage._slug("Mueller") != ablage._slug("Moeller")
