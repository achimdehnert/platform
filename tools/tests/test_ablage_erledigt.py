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


# =============================================================================
# #2799 — Ordner live, Strang ueber die Konversation, Referenzen, Zaehlung, Melder
#
# Alle Fixtures sind SYNTHETISCH. Dieses Repo ist oeffentlich; echte Betreffs,
# Ordner- und Personennamen aus den Postfaechern haben hier nichts zu suchen.
# =============================================================================


class TestOrdnerbestandLive:
    """K1 — die leere Bestandsliste war eine Aussage ueber das Argument, nicht ueber das Postfach."""

    def test_should_fetch_the_folder_list_itself_when_none_was_given(self):
        bestand, fehlt = ablage.ordner_je_konto_live(
            ["iil", "hnu"], hole=lambda k: ["Archiv/2026", f"{k}-Ordner"]
        )
        assert bestand["iil"] == ["Archiv/2026", "iil-Ordner"]
        assert bestand["hnu"] == ["Archiv/2026", "hnu-Ordner"]
        assert fehlt == {}

    def test_should_report_an_unreachable_account_instead_of_an_empty_inventory(self):
        """`organize_mail.connect` beendet den Prozess (SystemExit) statt zu werfen."""

        def hole(konto):
            if konto == "ad":
                raise SystemExit("Maschine ist fuer Mail nicht freigegeben")
            return ["Archiv/2026"]

        bestand, fehlt = ablage.ordner_je_konto_live(["hnu", "ad"], hole=hole)
        assert list(bestand) == ["hnu"]
        assert "nicht freigegeben" in fehlt["ad"]

    def test_should_mark_the_vorgang_of_an_unreachable_account_as_such(self):
        (zeile,) = ablage.plane(
            {"vorgaenge": [_v(konto="ad", gegenueber="Unbekannt")]},
            {"1": {}},
            {},
            {},
            {},
            {"ad": "Capability-Profil"},
        )
        assert zeile.status == ablage.KONTO_NICHT_ERREICHBAR

    def test_should_never_call_a_missing_account_a_missing_folder(self):
        (zeile,) = ablage.plane(
            {"vorgaenge": [_v(konto="ad", gegenueber="Unbekannt")]},
            {"1": {}},
            {},
            {},
            {},
            {"ad": "Capability-Profil"},
        )
        assert zeile.status != "ordner_fehlt"

    def test_should_give_the_unreachable_account_its_own_line_in_the_report(self):
        zeilen = ablage.plane(
            {"vorgaenge": [_v(konto="ad", gegenueber="Unbekannt")]},
            {"1": {}},
            {},
            {},
            {},
            {"ad": "Capability-Profil"},
        )
        text = ablage.bericht(zeilen, {"ad": "Capability-Profil"})
        assert "Konto 'ad' nicht erreichbar" in text

    def test_should_ask_only_for_accounts_that_hold_a_closed_vorgang(self):
        ledger = {
            "vorgaenge": [
                _v(konto="hnu"),
                _v(konto="iil", nr=2),
                _v(konto="ad", nr=3, bucket="owner"),
            ]
        }
        assert ablage.konten_der_vorgaenge(ledger) == ["hnu", "iil"]


def _konversation_attrappe(nachrichten, fehler=None):
    def konversation(konto, message_id):
        if fehler is not None:
            raise fehler
        return list(nachrichten)

    return konversation


class TestStrangUeberKonversation:
    """K2 — der Betreff ist die schwaechste Art, einen Strang zu bestimmen."""

    VORGANG = {"nr": 1, "konto": "hnu", "thread_key": "Vorgang X"}
    ANKER = {"1": {"message_id": "<a1@example.invalid>"}}

    def test_should_resolve_the_thread_via_the_conversation_before_the_subject(self):
        strang = ablage.strang_aufloesen(
            self.VORGANG,
            _suche_attrappe({"begriff": [_n(strang="aus-dem-index")]}),
            _konversation_attrappe([_n(ordner="INBOX")]),
            self.ANKER,
        )
        assert strang.quelle == ablage.KONVERSATION
        assert strang.kennung == "<a1@example.invalid>"

    def test_should_fall_back_to_the_subject_when_the_conversation_is_empty(self):
        strang = ablage.strang_aufloesen(
            self.VORGANG,
            _suche_attrappe({"begriff": [_n(strang="s1")]}),
            _konversation_attrappe([]),
            self.ANKER,
        )
        assert (strang.quelle, strang.kennung) == (ablage.BETREFF, "s1")

    def test_should_fall_back_when_the_mailbox_is_unreachable(self):
        """Ein Netzfehler darf den Lauf nicht abbrechen — nur den besseren Weg kosten."""
        strang = ablage.strang_aufloesen(
            self.VORGANG,
            _suche_attrappe({"begriff": [_n(strang="s1")]}),
            _konversation_attrappe([], fehler=OSError("Verbindung weg")),
            self.ANKER,
        )
        assert strang.kennung == "s1"
        assert "nicht abfragbar" in strang.grund

    def test_should_use_the_subject_path_when_no_anchor_holds_a_message_id(self):
        strang = ablage.strang_aufloesen(
            self.VORGANG,
            _suche_attrappe({"begriff": [_n(strang="s1")]}),
            _konversation_attrappe([_n()]),
            {},
        )
        assert strang.quelle == ablage.BETREFF

    def test_should_read_the_message_id_from_the_graph_registry_too(self):
        mid = ablage.anker_message_id(
            self.VORGANG, {}, {"1": {"internet_message_id": "<g1@example.invalid>"}}
        )
        assert mid == "<g1@example.invalid>"

    def test_should_move_the_conversation_messages_without_asking_the_index(self):
        """Der Index kennt diesen Strang nicht — er darf auch nicht gefragt werden."""

        def suche(**_):
            raise AssertionError("Index wurde trotz Konversation befragt")

        strang = ablage.Strang(
            "<a1@example.invalid>",
            ablage.KONVERSATION,
            nachrichten=[_n(ordner="INBOX"), _n(ordner="Gesendete Objekte")],
        )
        bewegungen, liegen = ablage.bewegungen_fuer(
            {"nr": 1, "konto": "hnu"}, "Archiv/2026", strang, suche
        )
        assert len(bewegungen) == 1
        assert liegen == {"Gesendete Objekte": 1}

    def test_should_name_the_source_of_every_thread_in_the_report(self):
        zeilen = ablage.plane(
            {"vorgaenge": [_v(konto="hnu", gegenueber="Unbekannt", thread_key="X")]},
            {"1": {"message_id": "<a1@example.invalid>"}},
            {"hnu": HNU_ORDNER},
        )
        text = ablage.strang_bericht(
            zeilen,
            {"vorgaenge": [_v(konto="hnu", gegenueber="Unbekannt", thread_key="X")]},
            _suche_attrappe({}),
            _konversation_attrappe([_n(ordner="INBOX")]),
            {"1": {"message_id": "<a1@example.invalid>"}},
        )
        assert "[konversation]" in text
        assert "Strang-Quellen: 1x konversation" in text


class _FakeImap:
    """IMAP-Attrappe: beantwortet UID SEARCH je Kopfzeile, sonst nichts."""

    def __init__(self, treffer):
        self.treffer = treffer
        self.gefragt = []

    def uid(self, befehl, _none, _header, kopf, wert):
        self.gefragt.append((befehl, kopf, wert))
        gefunden = self.treffer.get(kopf, b"")
        return ("OK", [gefunden]) if gefunden else ("OK", [b""])


class TestKonversationsSuche:
    def test_should_search_all_three_thread_headers(self):
        imap = _FakeImap({"References": b"7 9"})
        uids = ablage._uids_der_konversation(imap, "<a1@example.invalid>")
        assert uids == ["7", "9"]
        assert [k for _, k, _ in imap.gefragt] == [
            "References",
            "In-Reply-To",
            "Message-ID",
        ]

    def test_should_report_every_uid_only_once(self):
        imap = _FakeImap({"References": b"7", "Message-ID": b"7"})
        assert ablage._uids_der_konversation(imap, "<a1@example.invalid>") == ["7"]

    def test_should_map_graph_messages_onto_their_folder_path(self):
        werte = [
            {
                "id": "AAMkAAA=",
                "subject": "Beispielbetreff",
                "receivedDateTime": "2026-09-01T08:00:00Z",
                "parentFolderId": "F1",
                "conversationId": "C1",
            }
        ]
        (nachricht,) = ablage.graph_nachrichten_aus_antwort(
            werte, {"F1": "Posteingang"}
        )
        assert nachricht["ordner"] == ["Posteingang"]
        assert nachricht["datum"] == "2026-09-01"
        assert nachricht["kennung"] == "AAMkAAA="


def _ergebnis(zustand, nr=1, eintrag=1, schluessel="hnu-inbox-1000", hinweis="x"):
    import types

    return types.SimpleNamespace(
        fund=types.SimpleNamespace(nr=nr, eintrag=eintrag, schluessel=schluessel),
        zustand=zustand,
        hinweis=hinweis,
    )


class TestReferenzenUeberlebenDenUmzug:
    """K3 — eine tote UID laesst sich nachtraeglich nicht mehr binden."""

    def test_should_refuse_the_run_when_a_reference_stays_ambiguous(self):
        blockiert = ablage.verankerung_blockiert([_ergebnis("mehrdeutig")])
        assert len(blockiert) == 1
        assert "mehrdeutig" in blockiert[0]

    def test_should_refuse_the_run_when_an_account_could_not_be_checked(self):
        assert ablage.verankerung_blockiert([_ergebnis("unpruefbar")])

    def test_should_not_block_on_a_reference_that_was_already_dead(self):
        """Die UID lag in keinem Suchordner — also auch nicht im Quellordner."""
        assert ablage.verankerung_blockiert([_ergebnis("nicht-gefunden")]) == []

    def test_should_not_block_on_a_reference_that_is_anchored(self):
        assert (
            ablage.verankerung_blockiert([_ergebnis("neu"), _ergebnis("vorhanden")])
            == []
        )

    def test_should_limit_the_follow_up_to_the_anchors_of_moved_vorgaenge(self):
        import types

        funde = {
            "hnu-inbox-1000": types.SimpleNamespace(nr=5),
            "hnu-inbox-2000": types.SimpleNamespace(nr=6),
        }
        anker = {"5": "A", "6": "B", "hnu-inbox-1000": "C", "hnu-inbox-2000": "D"}
        assert ablage.anker_auswahl({5}, funde, anker) == {
            "5": "A",
            "hnu-inbox-1000": "C",
        }

    def test_should_count_followed_and_dead_anchors_from_both_worlds(self):
        import types

        befunde = [
            types.SimpleNamespace(zustand="verschoben"),
            types.SimpleNamespace(zustand="nachgezogen"),
            types.SimpleNamespace(zustand="geloescht"),
            types.SimpleNamespace(zustand="tot"),
            types.SimpleNamespace(zustand="unveraendert"),
        ]
        assert ablage.nachzug_bilanz(befunde) == (2, 2)


class TestZaehlungBeiderSeiten:
    """K4 — Realfall 2026-08-18: 89 Mails kopiert statt verschoben, Werkzeug meldete OK."""

    PAARE = [
        (_b(von="INBOX", nach="Archiv/2026"), "1"),
        (_b(von="INBOX", nach="Archiv/2026"), "2"),
    ]

    def test_should_expect_the_source_to_shrink_and_the_target_to_grow(self):
        deltas = ablage.erwartete_deltas(self.PAARE)
        assert deltas == {("hnu", "INBOX"): -2, ("hnu", "Archiv/2026"): 2}

    def test_should_print_both_sides_before_and_after(self):
        deltas = ablage.erwartete_deltas(self.PAARE)
        zeilen, abweichungen = ablage.zaehl_bericht(
            {("hnu", "INBOX"): 41, ("hnu", "Archiv/2026"): 120},
            {("hnu", "INBOX"): 39, ("hnu", "Archiv/2026"): 122},
            deltas,
        )
        assert abweichungen == []
        assert "Quelle INBOX: 41 → 39" in zeilen[0]
        assert "Ziel Archiv/2026: 120 → 122" in zeilen[0]

    def test_should_report_a_source_that_did_not_shrink(self):
        """Kopieren statt Verschieben sieht in der Erfolgszeile genauso aus."""
        zeilen, abweichungen = ablage.zaehl_bericht(
            {("hnu", "INBOX"): 41, ("hnu", "Archiv/2026"): 120},
            {("hnu", "INBOX"): 41, ("hnu", "Archiv/2026"): 122},
            ablage.erwartete_deltas(self.PAARE),
        )
        assert len(abweichungen) == 1
        assert "erwartet 39, gezaehlt 41" in abweichungen[0]

    def test_should_count_every_folder_exactly_once(self):
        gezaehlt = []

        def auflisten(konto, ordner):
            gezaehlt.append((konto, ordner))
            return [{"kennung": "1"}]

        stand = ablage.zaehle(ablage.erwartete_deltas(self.PAARE), auflisten)
        assert sorted(gezaehlt) == [("hnu", "Archiv/2026"), ("hnu", "INBOX")]
        assert stand == {("hnu", "INBOX"): 1, ("hnu", "Archiv/2026"): 1}


class TestMelder:
    """K5 — 0 ist gruen, alles andere ist eine offene Aufraeum-Haelfte."""

    LEDGER = {
        "vorgaenge": [
            _v(konto="hnu", nr=1, thread_key="Vorgang X"),
            _v(konto="iil", nr=2, thread_key="Vorgang Y"),
        ]
    }
    ANKER = {"1": {"message_id": "<a1@example.invalid>"}}

    #: Lebender Posteingang, in dem der Index-Treffer noch liegt.
    BESTAND = [{"kennung": "42", "betreff": "Vorgang X", "datum": "2026-08-18"}]

    def test_should_count_inbox_mails_of_closed_vorgaenge_per_account(self):
        zaehler, quellen, _ = ablage.pruefe_posteingang(
            self.LEDGER,
            _suche_attrappe({}),
            _konversation_attrappe([_n(ordner="INBOX"), _n(ordner="INBOX")]),
            self.ANKER,
        )
        assert zaehler["hnu"] == 2
        assert quellen["hnu"] == {ablage.KONVERSATION: 1}

    def test_should_be_green_when_the_inbox_holds_nothing_closed(self):
        zaehler, _, _ = ablage.pruefe_posteingang(
            self.LEDGER,
            _suche_attrappe({}),
            _konversation_attrappe([_n(ordner="Archiv/2026")]),
            self.ANKER,
        )
        assert sum(zaehler.values()) == 0

    def test_should_use_the_same_thread_resolution_as_the_dry_run(self):
        """Ohne Konversation bleibt der Index-Weg — dieselbe Funktion, dieselbe Reihenfolge."""
        zaehler, quellen, _ = ablage.pruefe_posteingang(
            self.LEDGER,
            _suche_attrappe(
                {"begriff": [_n(betreff="Vorgang X")], "strang": [_n(ordner="INBOX")]}
            ),
            None,
            self.ANKER,
            auflisten=lambda *_: list(self.BESTAND),
        )
        assert quellen["hnu"] == {ablage.BETREFF: 1}
        assert zaehler["hnu"] == 1

    def test_should_not_count_index_hits_that_left_the_inbox(self):
        """Der Index von 03:30 fuehrt eine eben abgelegte Mail weiter im Posteingang.

        Gemessen am 2026-09-04 direkt nach dem ersten scharfen Lauf: 18 Mails
        bewegt, Zaehlung beider Seiten stimmte — und der Melder meldete trotzdem
        `hnu: 7` und `iil: 1`. Ein Melder, der nach jeder erfolgreichen Ablage
        rot ist, wird nicht mehr gelesen.
        """
        zaehler, quellen, veraltet = ablage.pruefe_posteingang(
            self.LEDGER,
            _suche_attrappe(
                {"begriff": [_n(betreff="Vorgang X")], "strang": [_n(ordner="INBOX")]}
            ),
            None,
            self.ANKER,
            auflisten=lambda *_: [],  # der Posteingang ist leer — die Mail ist weg
        )
        assert zaehler["hnu"] == 0
        assert veraltet["hnu"] == 1
        assert quellen["hnu"] == {ablage.BETREFF: 1}

    def test_should_keep_counting_when_the_mailbox_cannot_confirm(self):
        """Nicht bestaetigbar ist nicht dasselbe wie bestaetigt-abwesend."""

        def auflisten(*_):
            raise OSError("Postfach nicht erreichbar")

        zaehler, _, veraltet = ablage.pruefe_posteingang(
            self.LEDGER,
            _suche_attrappe(
                {"begriff": [_n(betreff="Vorgang X")], "strang": [_n(ordner="INBOX")]}
            ),
            None,
            self.ANKER,
            auflisten=auflisten,
        )
        assert zaehler["hnu"] == 1
        assert veraltet["hnu"] == 0

    def test_should_confirm_the_live_mailbox_only_once_per_folder(self):
        aufrufe = []

        def auflisten(konto, ordner):
            aufrufe.append((konto, ordner))
            return list(self.BESTAND)

        ablage.pruefe_posteingang(
            {
                "vorgaenge": [
                    _v(konto="hnu", nr=1, thread_key="K"),
                    _v(konto="hnu", nr=2, thread_key="K"),
                ]
            },
            _suche_attrappe(
                {
                    "begriff": [_n(betreff="K")],
                    "strang": [_n(betreff="K", ordner="INBOX")],
                }
            ),
            None,
            {"1": {}, "2": {}},
            auflisten=auflisten,
        )
        assert aufrufe == [("hnu", "INBOX")]

    def test_should_name_the_snapshot_the_count_rests_on(self):
        text = ablage.pruefe_bericht({"hnu": 3}, {"hnu": {ablage.KONVERSATION: 1}})
        assert "3 Posteingangs-Mails gehoeren zu geschlossenen Vorgaengen" in text
        assert "03:30" in text

    def test_should_report_the_stale_index_hits_as_their_own_number(self):
        text = ablage.pruefe_bericht(
            {"hnu": 0}, {"hnu": {ablage.BETREFF: 14}}, {"hnu": 7}
        )
        assert "davon 7 im Index veraltet" in text
