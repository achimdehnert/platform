"""Tests für tools/todo_board/todo_board.py — Arbeitsliste aus dem Vorgangs-Ledger.

Geprüft wird das, was die Seite aussagekräftig macht: die Fristen-Arithmetik
inklusive Überfälligkeit, die Sortierung (Fristen zuerst, aufsteigend) und die
Zusicherung, dass kein Vorgang stillschweigend verschwindet, wenn seine
Bucket-Angabe fehlt oder unbekannt ist.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "todo_board"))

tb = pytest.importorskip("todo_board")

STICHTAG = date(2026, 8, 7)


@pytest.fixture(autouse=True)
def _kein_echter_anker(monkeypatch, tmp_path):
    """Kein Test liest die echte `~/.claude/mail-anker.json`.

    Ohne das haengt jeder Aufruf ohne ausdrueckliches `anker`-Argument am Home des
    Rechners, auf dem die Suite gerade laeuft: heute gruen, weil keine Fixture ein
    `nr` traegt — aber die erste Fixture mit `nr=109` wuerde auf dem Rechner des
    Owners verlinken und in CI nicht. Wer die Verankerung pruefen will, reicht sie
    ausdruecklich herein.
    """
    monkeypatch.setattr(tb, "ANKER_DATEI", tmp_path / "kein-anker.json")


def vorgang(**kw) -> dict:
    grund = {
        "konto": "iil",
        "thread_key": "Beispiel",
        "gegenueber": "Jemand",
        "bucket": "owner",
        "frist": None,
        "kurz": "etwas tun",
        "next_trigger": "etwas tun",
    }
    grund.update(kw)
    return grund


class TestFristTage:
    def test_should_return_none_without_frist(self):
        assert tb.frist_tage(vorgang(frist=None), STICHTAG) is None

    def test_should_count_days_until_frist(self):
        assert tb.frist_tage(vorgang(frist="2026-08-19"), STICHTAG) == 12

    def test_should_return_negative_when_overdue(self):
        assert tb.frist_tage(vorgang(frist="2026-08-01"), STICHTAG) == -6

    def test_should_return_none_for_unparsable_frist(self):
        # Ein kaputtes Datum darf die Seite nicht abreißen lassen.
        assert tb.frist_tage(vorgang(frist="19.08.2026"), STICHTAG) is None


class TestAmpel:
    @pytest.mark.parametrize(
        "tage,klasse",
        [(-1, "rot"), (0, "rot"), (3, "rot"), (4, "gelb"), (10, "gelb"), (11, "gruen")],
    )
    def test_should_classify_by_remaining_days(self, tage, klasse):
        assert tb.ampel(tage)[0] == klasse

    def test_should_name_overdue_days_explicitly(self):
        assert tb.ampel(-6)[1] == "6 Tage ueberfaellig"

    def test_should_stay_neutral_without_frist(self):
        assert tb.ampel(None) == ("keine", "—")


class TestSortierung:
    def test_should_put_deadlines_before_undated(self):
        mit = vorgang(frist="2026-09-30", thread_key="A")
        ohne = vorgang(frist=None, thread_key="B")
        geordnet = sorted([ohne, mit], key=lambda v: tb.sortschluessel(v, STICHTAG))
        assert [v["thread_key"] for v in geordnet] == ["A", "B"]

    def test_should_order_deadlines_ascending(self):
        spaet = vorgang(frist="2026-08-31", thread_key="spaet")
        frueh = vorgang(frist="2026-08-12", thread_key="frueh")
        geordnet = sorted([spaet, frueh], key=lambda v: tb.sortschluessel(v, STICHTAG))
        assert [v["thread_key"] for v in geordnet] == ["frueh", "spaet"]


class TestSeite:
    def test_should_render_every_vorgang(self):
        daten = {
            "letzte_pruefung": "2026-08-07",
            "vorgaenge": [
                vorgang(bucket="owner", thread_key="Alpha", frist="2026-08-19"),
                vorgang(bucket="agent", thread_key="Beta", frist="2026-08-22"),
                vorgang(bucket="warten", thread_key="Gamma"),
            ],
        }
        seite = tb.baue(daten, STICHTAG)
        for name in ("Alpha", "Beta", "Gamma"):
            assert name in seite

    def test_should_not_swallow_unknown_bucket(self):
        # Ein Tippfehler im Ledger darf einen Vorgang nicht unsichtbar machen —
        # er gehört sichtbar nach "Dein Zug", nicht ins Nichts.
        daten = {"vorgaenge": [vorgang(bucket="tippfehler", thread_key="Verwaist")]}
        seite = tb.baue(daten, STICHTAG)
        assert "Verwaist" in seite
        assert "Dein Zug" in seite

    def test_should_warn_about_imminent_deadlines(self):
        daten = {"vorgaenge": [vorgang(frist="2026-08-08", thread_key="Morgen")]}
        assert "1 in den naechsten 3 Tagen faellig" in tb.baue(daten, STICHTAG)

    def test_should_omit_empty_sections(self):
        daten = {"vorgaenge": [vorgang(bucket="owner")]}
        seite = tb.baue(daten, STICHTAG)
        assert "Dein Zug" in seite
        assert "Wartet auf andere" not in seite

    def test_should_escape_names_from_the_ledger(self):
        # Gegenüber-Namen kommen aus fremden Mails — sie dürfen kein Markup einschleusen.
        # Auf „<script> kommt gar nicht vor" lässt sich das nicht mehr stützen: die
        # Seite bringt seit dem Overlay ein eigenes, statisches Skript mit. Geprüft
        # wird darum die eingeschleuste Zeichenkette selbst, nicht das Tag an sich.
        boese = "<script>alert(1)</script>"
        daten = {"vorgaenge": [vorgang(gegenueber=boese)]}
        seite = tb.baue(daten, STICHTAG)
        assert boese not in seite
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in seite


class TestBindGuard:
    def test_should_refuse_public_bind_without_flag(self):
        import argparse

        args = argparse.Namespace(
            bind="0.0.0.0", port=8789, oeffentlich_hinter_auth=False
        )
        with pytest.raises(SystemExit) as exc:
            tb.cmd_serve(args)
        assert "verweigert" in str(exc.value)


class TestFrische:
    """Eine Liste, die stillschweigend alten Stand zeigt, beruhigt fälschlich."""

    def test_should_stay_silent_when_recent(self):
        daten = {"letzte_pruefung": "2026-08-07", "vorgaenge": []}
        assert tb.frische_banner(daten, STICHTAG) == ""

    def test_should_stay_silent_at_the_freshness_limit(self):
        daten = {"letzte_pruefung": "2026-08-05", "vorgaenge": []}
        assert tb.frische_banner(daten, STICHTAG) == ""

    def test_should_warn_one_day_past_the_limit(self):
        daten = {"letzte_pruefung": "2026-08-04", "vorgaenge": []}
        banner = tb.frische_banner(daten, STICHTAG)
        assert "3 Tage alt" in banner
        assert "2026-08-04" in banner

    def test_should_warn_when_date_is_missing(self):
        assert "Stand unbekannt" in tb.frische_banner({"vorgaenge": []}, STICHTAG)

    def test_should_warn_when_date_is_unparsable(self):
        banner = tb.frische_banner({"letzte_pruefung": "07.08.2026"}, STICHTAG)
        assert "unlesbar" in banner

    def test_should_surface_the_banner_on_the_page(self):
        daten = {"letzte_pruefung": "2026-07-01", "vorgaenge": [vorgang()]}
        assert "37 Tage alt" in tb.baue(daten, STICHTAG)


class TestVerlinkung:
    """Jede Zeile fuehrt zum Vorgang — und keine Zeile fuehrt ins Leere."""

    def test_should_link_the_thread_key(self):
        markup = tb.zeile(vorgang(thread_key="vorgang-a"), STICHTAG)
        assert "<a href='/t/vorgang-a'>" in markup

    def test_should_render_plain_text_without_thread_key(self):
        markup = tb.zeile(vorgang(thread_key=""), STICHTAG)
        assert "<a " not in markup
        assert "href=''" not in markup

    def test_should_encode_special_characters_in_the_target(self):
        markup = tb.zeile(vorgang(thread_key="Postfach #842 (neu)"), STICHTAG)
        assert "/t/Postfach%20%23842%20%28neu%29" in markup

    def test_should_prefix_an_absolute_base_when_given(self):
        markup = tb.zeile(vorgang(thread_key="x"), STICHTAG, "http://127.0.0.1:8789")
        assert "<a href='http://127.0.0.1:8789/t/x'>" in markup

    def test_should_escape_markup_from_the_ledger(self):
        boese = "<script>alert(1)</script>"
        markup = tb.zeile(vorgang(gegenueber=boese), STICHTAG)
        assert boese not in markup
        assert "&lt;script&gt;" in markup

    def test_should_carry_the_overlay_exactly_once(self):
        seite = tb.baue({"vorgaenge": [vorgang()]}, STICHTAG)
        assert seite.count("id=ovl-frame") == 1


class TestDetailseite:
    def test_should_show_the_notiz(self):
        seite = tb.detail(vorgang(notiz="erst dies | dann das"))
        assert "erst dies" in seite and "dann das" in seite

    def test_should_show_a_dash_for_empty_fields(self):
        seite = tb.detail(vorgang(zustand=None))
        assert "—" in seite

    def test_should_escape_markup_in_the_notiz(self):
        boese = "<img src=x onerror=alert(1)>"
        seite = tb.detail(vorgang(notiz=boese))
        assert boese not in seite
        assert "&lt;img" in seite

    def test_should_title_the_page_with_the_thread_key(self):
        seite = tb.detail(vorgang(thread_key="vorgang-a"))
        assert "<title>vorgang-a</title>" in seite


# --- Mail-Link und Aktionsvorschlaege auf der Vorgangsseite (#1869) ------------
#
# Die Vorgangsseite fuehrte bisher nicht in die zugehoerige Mail, und der
# `next_trigger` stand nur als Tabellenzeile da. Beides ist jetzt ein Abschnitt
# "Naechste Schritte" — mit der harten Grenze, dass dort ausschliesslich
# ANZEIGENDE Ziele stehen: kein Knopf loest etwas aus, und es gibt keinen
# Rueckkanal, ueber den die Seite einen Agenten beauftragen koennte.


def test_should_link_into_the_mail_when_a_reference_exists():
    v = vorgang(thread_key="Foerderaufruf", mail_ref="/a/118")
    html_out = tb.detail(v, mail_basis="https://mail.example", basis="")
    assert "https://mail.example/a/118" in html_out
    assert "Mail oeffnen" in html_out


def test_should_not_render_a_dead_link_without_a_mail_reference():
    """Gegenprobe: ohne `mail_ref` und ohne Anker entsteht kein Ziel.

    Geprueft wird jetzt das ANKER-ELEMENT, nicht mehr das blosse Vorkommen der
    Zeichenkette: seit das Overlay die erlaubte Mail-Basis an den Interceptor
    uebergibt, steht sie als JS-Konstante auf jeder Seite. Ein Substring-Verbot
    wuerde also anschlagen, ohne dass ein Link existiert — es haette die Aussage
    "kein toter Link" gegen "Basis kommt nirgends vor" getauscht.
    """
    v = vorgang(thread_key="Ohne Mail")
    html_out = tb.detail(v, mail_basis="https://mail.example", basis="")
    assert "Mail oeffnen" not in html_out
    assert "href='https://mail.example" not in html_out
    assert "keine Mail verknuepft" in html_out


def test_should_ignore_an_absolute_mail_ref_from_the_ledger():
    """Der Ledger speist sich aus fremden Mails — ein absoluter Wert waere ein
    offener Weiterleitungspunkt und darf nicht zum Ziel werden."""
    for boese in ("https://fremd.example/x", "//fremd.example/x"):
        v = vorgang(thread_key="Boese", mail_ref=boese)
        assert tb.aktionen(v, "https://mail.example", "") == []


def test_should_show_the_next_step_as_a_section():
    v = vorgang(thread_key="Foerderaufruf", next_trigger="Owner-Entscheidung")
    html_out = tb.detail(v, mail_basis="https://mail.example", basis="")
    assert "Naechste Schritte" in html_out
    assert "Owner-Entscheidung" in html_out


def test_should_keep_a_suggestion_without_target_as_plain_text():
    """Gegenprobe: kein ableitbares Ziel -> Text, kein Knopf."""
    v = vorgang(thread_key="", next_trigger="Owner-Entscheidung")
    html_out = tb.detail(v, mail_basis="https://mail.example", basis="")
    assert "Owner-Entscheidung" in html_out
    assert "class='aktion'" not in html_out


def test_should_render_unchanged_for_ledger_entries_without_the_new_field():
    """Rueckwaerts: die 17 Bestandsvorgaenge tragen `mail_ref` nicht.

    Geprueft wird Bruchfreiheit, nicht Pixelgleichheit: die Seite baut, traegt
    ihren Titel, und es taucht KEIN Mail-Ziel auf. Der Abschnitt selbst darf
    erscheinen — er ist der Zweck der Aenderung.
    """
    v = vorgang(thread_key="Bestand", next_trigger="Owner-Entscheidung")
    html_out = tb.detail(v)
    assert "<h1>Bestand</h1>" in html_out
    assert "Mail oeffnen" not in html_out
    assert "class='aktion'" not in html_out


def test_should_not_expose_any_write_endpoint():
    """Der Dienst bleibt read-only — Kriterium 5 aus #1869, mechanisch geprueft."""
    quelle = (
        Path(__file__).resolve().parents[1] / "todo_board" / "todo_board.py"
    ).read_text(encoding="utf-8")
    for verb in ("do_POST", "do_PUT", "do_DELETE", "do_PATCH"):
        assert verb not in quelle, f"{verb} widerspricht der read-only-Zusage"


# --- Luecke benennen statt verschweigen (#1869, Nachtrag) ---------------------
#
# Am 2026-08-10 trugen 13 von 17 Vorgaengen keinen Anker. Eine leere Stelle unter
# "Naechste Schritte" ist von einem kaputten Link nicht zu unterscheiden — der
# Hinweis macht den Unterschied sichtbar und zeigt, wo /mailcheck nachzutragen hat.


def test_should_name_the_gap_when_no_mail_is_linked():
    v = vorgang(thread_key="Ohne Anker", next_trigger="Owner-Entscheidung")
    html_out = tb.detail(v, mail_basis="https://mail.example", basis="")
    assert "keine Mail verknuepft" in html_out
    assert "Mail oeffnen" not in html_out


def test_should_not_name_a_gap_that_does_not_exist():
    """Gegenprobe: mit Anker kein Luecken-Hinweis."""
    v = vorgang(thread_key="Mit Anker", mail_ref="/a/118")
    html_out = tb.detail(v, mail_basis="https://mail.example", basis="")
    assert "keine Mail verknuepft" not in html_out
    assert "https://mail.example/a/118" in html_out


# --- Nummerierung -------------------------------------------------------------
#
# Die Nummer ist `nr` aus dem Ledger, nicht ein Laufindex je Abschnitt: sie bleibt
# ueber Bucket-Wechsel und ueber Tage hinweg dieselbe und ist genau die Nummer,
# unter der die Mail als `/a/<nr>` erreichbar ist.


class TestNummerierung:
    def test_should_show_the_ledger_number_in_the_row(self):
        markup = tb.zeile(vorgang(nr=118), STICHTAG)
        assert "<td class='nr'>118</td>" in markup

    def test_should_show_a_dash_when_the_number_is_missing(self):
        markup = tb.zeile(vorgang(), STICHTAG)
        assert "<td class='nr'>—</td>" in markup

    def test_should_keep_the_ledger_number_across_buckets(self):
        """Kein Laufindex: derselbe Vorgang traegt in jedem Bucket dieselbe Zahl."""
        for eimer in ("owner", "agent", "warten"):
            seite = tb.baue(
                {"vorgaenge": [vorgang(nr=118, bucket=eimer)]},
                STICHTAG,
                anker=frozenset(),
            )
            assert "<td class='nr'>118</td>" in seite

    def test_should_number_every_row_independently(self):
        seite = tb.baue(
            {
                "vorgaenge": [
                    vorgang(nr=107, thread_key="a"),
                    vorgang(nr=124, thread_key="b"),
                ]
            },
            STICHTAG,
            anker=frozenset(),
        )
        assert "<td class='nr'>107</td>" in seite and "<td class='nr'>124</td>" in seite

    def test_should_add_the_number_column_to_the_header(self):
        seite = tb.baue({"vorgaenge": [vorgang(nr=1)]}, STICHTAG, anker=frozenset())
        assert "<th>#</th>" in seite

    def test_should_show_the_number_on_the_detail_page(self):
        seite = tb.detail(
            vorgang(nr=118, thread_key="Foerderaufruf"), anker=frozenset()
        )
        assert "#118" in seite

    def test_should_escape_a_number_that_is_not_a_number(self):
        """Der Ledger ist eine Datei — `nr` ist nicht garantiert eine Zahl."""
        markup = tb.zeile(vorgang(nr="<script>x</script>"), STICHTAG)
        assert "<script>x</script>" not in markup
        assert "&lt;script&gt;" in markup


# --- Mail-Link aus der Nummer, gegen den Anker geprueft ------------------------
#
# `/a/<nr>` liesse sich blind aus `nr` ableiten. Gemessen am 2026-08-11 waeren das
# 14 von 18 Links, die 404 liefern — verankert sind nur 109, 110, 115, 118. Der
# Anker-Index entscheidet darum, ob ein Link entsteht.


class TestAnkerGate:
    def test_should_derive_the_link_when_the_number_is_anchored(self):
        ziel = tb.mail_ziel(vorgang(nr=109), "https://mail.example", frozenset({"109"}))
        assert ziel == "https://mail.example/a/109"

    def test_should_not_derive_a_link_for_an_unanchored_number(self):
        assert (
            tb.mail_ziel(vorgang(nr=107), "https://mail.example", frozenset({"109"}))
            is None
        )

    def test_should_prefer_an_explicit_mail_ref_over_the_number(self):
        v = vorgang(nr=109, mail_ref="/a/999")
        ziel = tb.mail_ziel(v, "https://mail.example", frozenset({"109"}))
        assert ziel == "https://mail.example/a/999"

    def test_should_reject_an_absolute_mail_ref_without_falling_back(self):
        """Ein vergifteter Eintrag wird nicht stillschweigend durch die Nummer geheilt."""
        v = vorgang(nr=109, mail_ref="https://fremd.example/x")
        assert tb.mail_ziel(v, "https://mail.example", frozenset({"109"})) is None

    def test_should_treat_a_missing_anchor_file_as_no_anchors(self):
        assert tb.anker_nummern(Path("/nicht/vorhanden/anker.json")) == frozenset()

    def test_should_treat_a_broken_anchor_file_as_no_anchors(self, tmp_path):
        kaputt = tmp_path / "anker.json"
        kaputt.write_text("{kein json", encoding="utf-8")
        assert tb.anker_nummern(kaputt) == frozenset()

    def test_should_read_the_numbers_from_the_anchor_file(self, tmp_path):
        gut = tmp_path / "anker.json"
        gut.write_text('{"109": {"ordner": "INBOX"}, "110": {}}', encoding="utf-8")
        assert tb.anker_nummern(gut) == frozenset({"109", "110"})

    def test_should_link_the_mail_from_the_overview_row(self):
        """Der Weg zur Mail kostet keinen Zwischenklick mehr."""
        markup = tb.zeile(
            vorgang(nr=109, thread_key="x"),
            STICHTAG,
            "",
            "https://mail.example",
            frozenset({"109"}),
        )
        assert "href='https://mail.example/a/109'" in markup

    def test_should_not_link_an_unanchored_row(self):
        markup = tb.zeile(
            vorgang(nr=107, thread_key="x"),
            STICHTAG,
            "",
            "https://mail.example",
            frozenset({"109"}),
        )
        assert "maillink" not in markup


# --- Overlay auf der Vorgangsseite + Praefix-Pruefung --------------------------
#
# K2 aus #1869 verlangte, dass die Vorgangsseite in die Mail fuehrt — urspruenglich
# als Overlay gedacht. Am 2026-08-11 im Browser gemessen: das Modal ist fuer
# Mail-Links strukturell unmoeglich. mail.iil.pet steht hinter Cloudflare Access;
# Access leitet auf iil-team.cloudflareaccess.com um, das `frame-ancestors 'none'`
# sendet. Der Rahmen oeffnete sich und zeigte "hat die Verbindung abgelehnt".
#
# Konsequenz, hier festgeschrieben: Mail-Links gehen in einen NEUEN TAB, das
# Overlay bleibt den eigenen `/t/`-Seiten vorbehalten. Diese Tests halten beide
# Haelften fest, damit niemand das Modal spaeter "repariert", ohne die Ursache
# (getrennte Adressen) beseitigt zu haben.


class TestMailLinkOeffnetNeuenTab:
    def test_should_open_the_mail_in_a_new_tab_from_the_row(self):
        markup = tb.zeile(
            vorgang(nr=109, thread_key="x"),
            STICHTAG,
            "",
            "https://mail.example",
            frozenset({"109"}),
        )
        assert "target='_blank'" in markup
        assert "rel='noreferrer'" in markup

    def test_should_open_the_mail_in_a_new_tab_from_the_detail_page(self):
        seite = tb.detail(
            vorgang(thread_key="x", mail_ref="/a/109"), "https://mail.example"
        )
        assert "class='aktion'" in seite
        assert "target='_blank'" in seite

    def test_should_not_intercept_the_mail_basis(self):
        """Gegenprobe: kein Interceptor-Zweig auf die Mail-Basis.

        Faellt absichtlich um, wenn jemand das Modal fuer Mail-Links wieder
        einbaut — dann muss zuerst die Ursache weg (gemeinsame Adresse), sonst
        zeigt der Rahmen erneut nur "Verbindung abgelehnt".
        """
        seite = tb.baue({"vorgaenge": [vorgang()]}, STICHTAG, anker=frozenset())
        assert "mail.iil.pet'" not in seite.split("<script>")[1]
        assert "lastIndexOf(MB" not in seite

    def test_should_still_intercept_vorgang_links(self):
        seite = tb.baue({"vorgaenge": [vorgang()]}, STICHTAG, anker=frozenset())
        assert "h.indexOf('/t/')>=0" in seite

    def test_should_keep_the_overlay_on_the_index_only(self):
        """Die Detailseite traegt kein Overlay — sie hat keinen `/t/`-Link."""
        assert tb.baue({"vorgaenge": [vorgang()]}, STICHTAG).count("id=ovl-frame") == 1
        assert "id=ovl-frame" not in tb.detail(vorgang(thread_key="x"))
