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


class TestGraphBindung:
    """Graph-Konten binden über eine Kurz-ID-Registry, nicht über den IMAP-Anker.

    Nur `anker` zu prüfen hätte jeden Vorgang eines Graph-Kontos fälschlich als
    ungebunden gemeldet — `board.anker_zustand()` akzeptiert seit jeher beide.
    """

    def test_should_accept_a_graph_link_instead_of_an_imap_anchor(self):
        (zeile,) = ablage.plane(
            {"vorgaenge": [_v(gegenueber="Kastenmayer")]},
            {},
            {"iil": IIL_ORDNER},
            {},
            {"1": {"graph_id": "AAMk="}},
        )
        assert zeile.status == "bereit"

    def test_should_still_report_a_vorgang_bound_by_neither(self):
        (zeile,) = ablage.plane(
            {"vorgaenge": [_v(gegenueber="Kastenmayer")]},
            {},
            {"iil": IIL_ORDNER},
            {},
            {},
        )
        assert zeile.status == "kein_anker"


def _suche_attrappe(treffer_je_kriterium):
    """Index-Attrappe: bildet Aufrufe auf feste Antworten ab.

    Bewusst eine Attrappe und keine echte Abfrage — der Index haengt an einer
    Datenbank hinter SSH, und ein Test, der davon abhaengt, prüfte die Verbindung
    statt der Logik.
    """

    def suche(**kriterien):
        if "strang" in kriterien:
            return treffer_je_kriterium.get("strang", [])
        return treffer_je_kriterium.get("begriff", [])

    return suche


def _n(betreff="Vorgang X", ordner="INBOX", strang="s1", datum="2026-08-18"):
    return {"betreff": betreff, "ordner": [ordner], "strang": strang, "datum": datum}


class TestStrangAufloesung:
    def test_should_find_the_thread_via_the_subject(self):
        strang, grund = ablage.strang_fuer(
            {"thread_key": "Vorgang X", "konto": "hnu"},
            _suche_attrappe({"begriff": [_n(), _n()]}),
        )
        assert strang == "s1"
        assert "Betreff" in grund

    def test_should_refuse_when_two_threads_share_the_subject(self):
        """Zwei Stränge unter einem Betreff sind zwei Gespräche."""
        strang, grund = ablage.strang_fuer(
            {"thread_key": "Vorgang X", "konto": "hnu"},
            _suche_attrappe({"begriff": [_n(strang="s1"), _n(strang="s2")]}),
        )
        assert strang is None
        assert "mehrdeutig" in grund

    def test_should_report_a_vorgang_without_a_thread_key(self):
        strang, grund = ablage.strang_fuer({"konto": "hnu"}, _suche_attrappe({}))
        assert strang is None
        assert "thread_key" in grund


class TestBewegungen:
    def test_should_move_only_from_the_inbox(self):
        """Gemessen an einem echten Strang: Gesendetes und bereits Abgelegtes bleiben."""
        bewegungen, liegen = ablage.bewegungen_fuer(
            {"nr": 5, "konto": "hnu"},
            "Archiv/2026",
            "s1",
            _suche_attrappe(
                {
                    "strang": [
                        _n(ordner="INBOX"),
                        _n(ordner="INBOX"),
                        _n(ordner="Gesendete Objekte"),
                        _n(ordner="MEIKI/Landkreis"),
                    ]
                }
            ),
        )
        assert len(bewegungen) == 2
        assert all(b.von_ordner == "INBOX" for b in bewegungen)
        assert liegen == {"Gesendete Objekte": 1, "MEIKI/Landkreis": 1}

    def test_should_carry_the_target_into_every_movement(self):
        bewegungen, _ = ablage.bewegungen_fuer(
            {"nr": 5, "konto": "iil"},
            "IIL.Kunden/Talmuehle",
            "s1",
            _suche_attrappe({"strang": [_n(ordner="Posteingang")]}),
        )
        assert bewegungen[0].nach_ordner == "IIL.Kunden/Talmuehle"

    def test_should_produce_nothing_when_the_inbox_holds_none_of_the_thread(self):
        bewegungen, liegen = ablage.bewegungen_fuer(
            {"nr": 5, "konto": "hnu"},
            "Archiv/2026",
            "s1",
            _suche_attrappe({"strang": [_n(ordner="Archiv/2025")]}),
        )
        assert bewegungen == []
        assert liegen == {"Archiv/2025": 1}


class TestBetreffkern:
    """Der Index sucht in Betreff, Text UND Anhängen — das ist zu grob.

    Gemessen am 2026-08-18: 18 von 23 Vorgängen kamen als „mehrdeutig" zurück,
    weil ein `thread_key` wie „Lizenz" Dutzende fremder Gespräche traf.
    """

    def test_should_treat_reply_prefixes_as_the_same_subject(self):
        assert ablage.betreff_kern("AW: RE: Postsortierung") == ablage.betreff_kern(
            "Postsortierung"
        )

    def test_should_ignore_a_full_text_hit_with_a_different_subject(self):
        strang, grund = ablage.strang_fuer(
            {"thread_key": "Lizenz", "konto": "hnu"},
            _suche_attrappe(
                {
                    "begriff": [
                        _n(betreff="Lizenz", strang="s1"),
                        _n(betreff="Ganz anderes Thema", strang="s2"),
                    ]
                }
            ),
        )
        assert strang == "s1"

    def test_should_say_so_when_only_body_hits_remain(self):
        strang, grund = ablage.strang_fuer(
            {"thread_key": "Lizenz", "konto": "hnu"},
            _suche_attrappe({"begriff": [_n(betreff="Etwas anderes", strang="s2")]}),
        )
        assert strang is None
        assert "kein gleicher Betreff" in grund
