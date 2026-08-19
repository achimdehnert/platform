"""Tests für tools/mail_agent/ablage.py — Zielauflösung, kein Schreibpfad.

Geprüft wird die Frage, an der die Automatik scheitern würde: Landet eine Mail in
der richtigen Schublade, und wird zugegeben, wenn keine passt? Kein Test fasst ein
Postfach an; der Ordnerbestand wird hereingereicht.
"""

from __future__ import annotations

import json
import sys
import tempfile
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
            _v(
                konto="hnu",
                typ="betreuung-masterarbeit",
                gegenueber="HNU / N. S. Winterhalt (Masterthesis)",
            ),
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


# --- Schreibpfad -------------------------------------------------------------
#
# Der Index ist ein Schnappschuss von 03:30. Zwischen ihm und dem Verschieben
# liegt eine Nacht, in der der Owner selbst Mails bewegt. Der Abgleich gegen den
# LEBENDEN Ordner ist deshalb kein Feinschliff, sondern die Bedingung dafür, dass
# überhaupt etwas Richtiges bewegt wird.


def _b(
    betreff="Vorgang X",
    datum="2026-08-18",
    konto="hnu",
    von="INBOX",
    nach="Archiv/2026",
    nr=5,
):
    return ablage.Bewegung(
        vorgang_nr=nr,
        konto=konto,
        betreff=betreff,
        von_ordner=von,
        nach_ordner=nach,
        datum=datum,
    )


class TestGraphAusgabeLesen:
    """`graph_mail --find` kennt kein --json — die eine Textstelle, hart getestet."""

    ROH = """3 Treffer in 'Posteingang' (letzte 365 Tage), neueste zuerst:
  · 2026-08-18T07:27  steffen.beispiel@example.com   AW: Abstimmung Termin
    id: AAMkAAA=
  · 2026-08-17T13:01  info@example.org               Ein anderer Betreff
    id: AAMkBBB=
"""

    def test_should_pair_each_hit_with_its_identifier(self):
        aus = ablage.graph_zeilen_lesen(self.ROH)
        assert [e["kennung"] for e in aus] == ["AAMkAAA=", "AAMkBBB="]

    def test_should_cut_the_date_to_ten_characters(self):
        assert ablage.graph_zeilen_lesen(self.ROH)[0]["datum"] == "2026-08-18"

    def test_should_keep_the_subject_without_the_sender(self):
        assert (
            ablage.graph_zeilen_lesen(self.ROH)[0]["betreff"] == "AW: Abstimmung Termin"
        )

    def test_should_ignore_a_hit_without_an_identifier(self):
        assert (
            ablage.graph_zeilen_lesen("  · 2026-08-18T07:27  a@b.de  Ohne ID\n") == []
        )


class TestDatumKern:
    def test_should_pass_an_iso_date_through(self):
        assert ablage._datum_kern("2026-08-18T07:27") == "2026-08-18"

    def test_should_understand_an_rfc_date_header(self):
        assert ablage._datum_kern("Tue, 18 Aug 2026 11:01:00 +0000") == "2026-08-18"

    def test_should_not_crash_on_nonsense(self):
        assert ablage._datum_kern("gestern") == "gestern"


class TestAbgleich:
    def test_should_match_subject_and_date_to_a_live_identifier(self):
        bestand = [{"kennung": "42", "betreff": "AW: Vorgang X", "datum": "2026-08-18"}]
        paare, fehlt = ablage.abgleichen([_b()], bestand)
        assert paare == [(paare[0][0], "42")]
        assert fehlt == []

    def test_should_skip_a_message_that_is_gone_from_the_source_folder(self):
        paare, fehlt = ablage.abgleichen([_b()], [])
        assert paare == []
        assert "nicht mehr vorhanden" in fehlt[0][1]

    def test_should_not_confuse_two_messages_of_the_same_thread(self):
        """Gleicher Betreff, verschiedene Tage — das Datum entscheidet."""
        bestand = [
            {"kennung": "1", "betreff": "AW: Vorgang X", "datum": "2026-08-17"},
            {"kennung": "2", "betreff": "AW: Vorgang X", "datum": "2026-08-18"},
        ]
        paare, _ = ablage.abgleichen([_b(datum="2026-08-18")], bestand)
        assert paare[0][1] == "2"

    def test_should_use_each_live_message_only_once(self):
        """Zwei erwartete Nachrichten, nur eine im Ordner — die zweite fehlt."""
        bestand = [{"kennung": "1", "betreff": "Vorgang X", "datum": "2026-08-18"}]
        paare, fehlt = ablage.abgleichen([_b(), _b()], bestand)
        assert len(paare) == 1
        assert len(fehlt) == 1


class TestAnwenden:
    def _lauf(self, tmp_path, paare):
        bewegt = []
        n = ablage.anwenden(
            paare,
            "lauf-1",
            verschieben=lambda k, q, ids, z: bewegt.append((k, q, tuple(ids), z)),
            protokoll=tmp_path / "protokoll.jsonl",
        )
        return n, bewegt

    def test_should_move_nothing_and_write_nothing_for_an_empty_plan(self, tmp_path):
        n, bewegt = self._lauf(tmp_path, [])
        assert (n, bewegt) == (0, [])
        assert not (tmp_path / "protokoll.jsonl").exists()

    def test_should_group_moves_by_account_and_folder_pair(self, tmp_path):
        paare = [
            (_b(konto="hnu", nach="Archiv/2026"), "1"),
            (_b(konto="hnu", nach="Archiv/2026"), "2"),
            (_b(konto="iil", von="Posteingang", nach="IIL.Kunden/Muster"), "AAMk="),
        ]
        n, bewegt = self._lauf(tmp_path, paare)
        assert n == 3
        assert len(bewegt) == 2
        hnu = next(x for x in bewegt if x[0] == "hnu")
        assert hnu[2] == ("1", "2")

    def test_should_write_the_protocol_before_moving(self, tmp_path):
        """Ein Abbruch mitten im Umzug darf den Lauf nicht unauffindbar machen."""
        pfad = tmp_path / "protokoll.jsonl"
        gesehen = {}

        def verschieben(k, q, ids, z):
            gesehen["protokoll_da"] = pfad.exists()

        ablage.anwenden(
            [(_b(), "1")], "lauf-2", verschieben=verschieben, protokoll=pfad
        )
        assert gesehen["protokoll_da"] is True

    def test_should_record_source_and_target_so_the_run_can_be_undone(self, tmp_path):
        import json as _json

        pfad = tmp_path / "protokoll.jsonl"
        ablage.anwenden(
            [(_b(), "1")], "lauf-3", verschieben=lambda *a: None, protokoll=pfad
        )
        eintrag = _json.loads(pfad.read_text(encoding="utf-8").splitlines()[0])
        assert eintrag["quellordner"] == "INBOX"
        assert eintrag["zielordner"] == "Archiv/2026"
        assert eintrag["lauf_id"] == "lauf-3"


# --- Ruecknahme: die protokollierte Kennung ist nach dem Umzug wertlos --------
# Beide Faelle sind am 2026-08-19 an einer echten Nachricht aufgetreten und
# waeren von einem Trockenlauf nie gefunden worden.


def test_should_carry_konto_through_ruecknahme():
    """Ohne Konto im Rueckplan greift die Ruecknahme zum falschen Transport.

    Realfall: der Eintrag war Graph (iil), der Rueckweg fiel auf IMAP zurueck
    und scheiterte an einem Ordner, den es dort nicht gibt.
    """
    import regeln

    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "protokoll.jsonl"
        regeln.protokollieren(
            [
                {
                    "id": "ID-ALT",
                    "konto": "iil",
                    "betreff": "Sache",
                    "datum": "2026-07-25",
                    "quellordner": "Posteingang",
                    "zielordner": "Kunden/Muster",
                    "aktion": "verschieben",
                }
            ],
            pfad,
            "lauf-1",
        )
        zurueck = regeln.ruecknahme(pfad, "lauf-1")

    assert zurueck[0]["konto"] == "iil"
    assert zurueck[0]["datum"] == "2026-07-25"


def test_should_resolve_ruecknahme_identifier_at_current_location():
    """Die Kennung wird am jetzigen Ort neu geholt, nicht aus dem Protokoll."""
    eintrag = {
        "id": "ID-ALT",
        "konto": "iil",
        "betreff": "AW: Sache",
        "datum": "2026-07-25",
        "quellordner": "Kunden/Muster",
        "zielordner": "Posteingang",
    }
    bestand = [{"kennung": "ID-NEU", "betreff": "Sache", "datum": "2026-07-25"}]

    paare, offen = ablage.ruecknahme_aufloesen(
        [eintrag], auflisten=lambda k, o: list(bestand)
    )

    assert offen == []
    assert paare[0][1] == "ID-NEU"


def test_should_skip_ruecknahme_when_subject_is_ambiguous_without_date():
    """Ohne Datum und mit mehreren gleichen Betreffen: lieber nichts bewegen."""
    eintrag = {
        "id": "ID-ALT",
        "konto": "hnu",
        "betreff": "Sache",
        "datum": "",
        "quellordner": "Archiv/2026",
        "zielordner": "INBOX",
    }
    bestand = [
        {"kennung": "7", "betreff": "Sache", "datum": "2026-07-25"},
        {"kennung": "9", "betreff": "AW: Sache", "datum": "2026-08-01"},
    ]

    paare, offen = ablage.ruecknahme_aufloesen(
        [eintrag], auflisten=lambda k, o: list(bestand)
    )

    assert paare == []
    assert "nicht eindeutig" in offen[0][1]


def test_should_record_date_in_protocol_for_later_ruecknahme():
    """Ohne Datum im Protokoll ist die Nachricht spaeter nicht eindeutig."""
    b = ablage.Bewegung(
        vorgang_nr=1,
        konto="iil",
        betreff="Sache",
        von_ordner="Posteingang",
        nach_ordner="Kunden/Muster",
        datum="2026-07-25",
    )
    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "protokoll.jsonl"
        ablage.anwenden(
            [(b, "ID-ALT")], "lauf-1", verschieben=lambda *a: None, protokoll=pfad
        )
        eintrag = json.loads(pfad.read_text(encoding="utf-8").splitlines()[0])

    assert eintrag["datum"] == "2026-07-25"
