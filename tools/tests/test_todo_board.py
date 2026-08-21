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
    monkeypatch.setattr(tb, "REGISTRY_DATEI", tmp_path / "keine-registry.json")


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
        """Die Kopfzeile nennt die Zahl — seit 2026-08-21 knapper formuliert."""
        daten = {"vorgaenge": [vorgang(frist="2026-08-08", thread_key="Morgen")]}
        assert "1 faellig in 3 Tagen" in tb.baue(daten, STICHTAG)

    def test_should_count_silent_vorgaenge_in_the_header(self, tmp_path, monkeypatch):
        """Der dritte Zustand ist der, der bisher fehlte: hier passiert nichts mehr."""
        datei = tmp_path / "f.json"
        datei.write_text(
            '{"1": {"erwartet": "2026-08-01", "spaetestens": "2026-08-05",'
            ' "ueberfaellig": true}}',
            encoding="utf-8",
        )
        monkeypatch.setattr(tb, "FAELLIGKEIT", datei)
        daten = {"vorgaenge": [vorgang(nr=1, bucket="warten", frist=None)]}
        assert "1 still" in tb.baue(daten, STICHTAG)

    def test_should_name_the_three_states(self, tmp_path, monkeypatch):
        datei = tmp_path / "f.json"
        datei.write_text(
            '{"1": {"erwartet": "2026-08-20", "spaetestens": "2026-08-30",'
            ' "ueberfaellig": false}}',
            encoding="utf-8",
        )
        monkeypatch.setattr(tb, "FAELLIGKEIT", datei)
        wartet = tb.zustand({"nr": 1, "bucket": "warten"}, STICHTAG)
        ohne = tb.zustand({"nr": 99, "bucket": "warten"}, STICHTAG)
        assert wartet[0] == "wartet"
        assert ohne == ("kein-signal", "kein Signal")

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


class TestEntwurfInDerListe:
    """Ein wartender Entwurf ist der haeufigste Grund fuer 'dein Zug' — und stand
    bisher einen Klick entfernt (Owner-Befund 2026-08-21: 'MUSS bekannt sein')."""

    def test_should_link_a_draft_from_the_newest_entry(self):
        v = vorgang(
            konto="hnu", notiz="alt | 2026-08-21 ENTWURF (HNU, Entwuerfe #23611)"
        )
        assert (
            tb.entwurf_link(v, "https://m.example")
            == "https://m.example/m/hnu/entwuerfe/23611"
        )

    def test_should_ignore_a_draft_from_an_older_entry(self):
        """Ein Entwurf von vorletzter Woche ist gesendet oder verworfen."""
        v = vorgang(
            konto="hnu",
            notiz="2026-08-01 ENTWURF (Entwuerfe #111) | 2026-08-21 gesendet",
        )
        assert tb.entwurf_link(v, "https://m.example") == ""

    def test_should_stay_silent_without_an_account(self):
        v = vorgang(konto="", notiz="ENTWURF (Entwuerfe #23611)")
        assert tb.entwurf_link(v, "https://m.example") == ""

    def test_should_show_the_marker_in_the_row(self):
        v = vorgang(konto="hnu", notiz="2026-08-21 ENTWURF (Entwuerfe #23611)")
        assert "entwurf-marke" in tb.zeile(v, STICHTAG, "", "https://m.example")


class TestVorgangsKopf:
    """Der erste Blick zeigt Information, nicht Stammdaten (Owner-Befund 2026-08-21)."""

    def test_should_keep_only_two_fields_in_the_head(self):
        seite = tb.detail(vorgang(gegenueber="Wer", frist="2026-08-30"))
        kopf = seite.split("Stammdaten")[0]
        assert "Gegenueber" in kopf and "Frist" in kopf
        assert "Zustand" not in kopf and "Angelegt" not in kopf

    def test_should_move_the_rest_into_a_collapsed_block(self):
        seite = tb.detail(vorgang())
        assert '<details class="stammdaten">' in seite
        assert "Zustand" in seite.split("Stammdaten")[1]

    def test_should_offer_the_other_order(self):
        seite = tb.detail(vorgang(notiz="a | b"))
        assert "aelteste zuerst" in seite
        umgedreht = tb.detail(vorgang(notiz="a | b"), alt_zuerst=True)
        assert "neueste zuerst" in umgedreht

    def test_should_reverse_the_entries_with_the_switch(self):
        seite = tb.detail(vorgang(notiz="erst dies | dann das"), alt_zuerst=True)
        rumpf = seite.split("Verlauf")[1]
        assert rumpf.index("erst dies") < rumpf.index("dann das")

    def test_should_name_what_the_mail_button_opens(self):
        """'Mail oeffnen' las sich wie 'die aktuelle' — es ist die erste."""
        seite = tb.detail(vorgang(mail_ref="/a/7"))
        assert "Erste Mail des Strangs" in seite


class TestErwartetesAntwortdatum:
    """Ohne gesetzte Frist tritt die Erwartung an ihre Stelle (#2176 Kriterium 5)."""

    def test_should_read_the_forecast_for_a_vorgang(self, tmp_path):
        datei = tmp_path / "f.json"
        datei.write_text(
            '{"7": {"erwartet": "2026-08-22", "spaetestens": "2026-08-28",'
            ' "ueberfaellig": false}}',
            encoding="utf-8",
        )
        assert tb._erwartung(7, datei)["spaetestens"] == "2026-08-28"

    def test_should_return_nothing_without_a_forecast_file(self, tmp_path):
        assert tb._erwartung(7, tmp_path / "fehlt.json") == {}

    def test_should_survive_a_broken_forecast_file(self, tmp_path):
        kaputt = tmp_path / "k.json"
        kaputt.write_text("{kaputt", encoding="utf-8")
        assert tb._erwartung(7, kaputt) == {}


class TestArchivierterVerlauf:
    """Gekappt heisst verschoben, nicht weg — die Ansicht setzt beides zusammen."""

    def test_should_show_archived_entries_before_the_active_ones(self, tmp_path):
        archiv = tmp_path / "archiv.json"
        archiv.write_text('{"7": ["ganz alt"]}', encoding="utf-8")
        assert tb._archiv_eintraege(7, archiv) == ["ganz alt"]

    def test_should_return_nothing_without_an_archive(self, tmp_path):
        assert tb._archiv_eintraege(7, tmp_path / "fehlt.json") == []

    def test_should_survive_a_broken_archive(self, tmp_path):
        """Eine unvollstaendige Ansicht ist besser als eine Fehlerseite."""
        kaputt = tmp_path / "kaputt.json"
        kaputt.write_text("{nicht json", encoding="utf-8")
        assert tb._archiv_eintraege(7, kaputt) == []


class TestMailSymbol:
    """Kein Briefsymbol, wo es nur auf die aelteste Mail zeigen wuerde."""

    def test_should_hide_mail_icon_when_a_vorgangsansicht_exists(self):
        z = tb.zeile(vorgang(thread_key="Mit Ansicht", mail_ref="/a/7"), STICHTAG)
        assert "maillink" not in z
        assert "/t/Mit%20Ansicht" in z

    def test_should_keep_mail_icon_without_thread_key(self):
        z = tb.zeile(vorgang(thread_key="", mail_ref="/a/7"), STICHTAG)
        assert "maillink" in z


class TestDetailseite:
    def test_should_show_the_notiz(self):
        seite = tb.detail(vorgang(notiz="erst dies | dann das"))
        assert "erst dies" in seite and "dann das" in seite

    def test_should_show_the_newest_note_first(self):
        """Der Verlauf waechst durch Anhaengen — angezeigt wird er umgekehrt,
        damit der aktuelle Stand oben steht und nicht hinter 15.000 Zeichen."""
        seite = tb.detail(vorgang(notiz="erst dies | dann das | zuletzt jenes"))
        # Ab der ersten Verlaufskarte, nicht ab der Ueberschrift: die trug bis
        # 2026-08-21 keine Klasse, und der Test hing an ihrem genauen Wortlaut.
        rumpf = seite[seite.index("<article class='eintrag'>") :]
        assert (
            rumpf.index("zuletzt jenes")
            < rumpf.index("dann das")
            < rumpf.index("erst dies")
        )

    def test_should_drop_empty_note_segments(self):
        """Zwei Eintraege, nicht drei — das leere Segment faellt raus.

        Gezaehlt werden seit 2026-08-21 die Karten selbst statt der Leerzeilen
        zwischen ihnen: die alte Zusicherung mass die Darstellung (`\n\n` im
        <pre>) und nicht die Sache, und ist mit der Darstellung gefallen.
        """
        seite = tb.detail(vorgang(notiz="a |  | b"))
        assert seite.count("<article class='eintrag'>") == 2
        assert "a" in seite and "b" in seite

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
    # Beschriftung seit 2026-08-21 praeziser: der Link fuehrt zur ERSTEN Mail des
    # Strangs, nicht zur aktuellen (platform#2160 haelt die offene Faehigkeit fest).
    assert "Erste Mail des Strangs" in html_out


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
                anker={},
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
            anker={},
        )
        assert "<td class='nr'>107</td>" in seite and "<td class='nr'>124</td>" in seite

    def test_should_add_the_number_column_to_the_header(self):
        seite = tb.baue({"vorgaenge": [vorgang(nr=1)]}, STICHTAG, anker={})
        assert "<th>#</th>" in seite

    def test_should_show_the_number_on_the_detail_page(self):
        seite = tb.detail(vorgang(nr=118, thread_key="Foerderaufruf"), anker={})
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
        ziel = tb.mail_ziel(vorgang(nr=109), "https://mail.example", {"109": "/a/"})
        assert ziel == "https://mail.example/a/109"

    def test_should_not_derive_a_link_for_an_unanchored_number(self):
        assert (
            tb.mail_ziel(vorgang(nr=107), "https://mail.example", {"109": "/a/"})
            is None
        )

    def test_should_prefer_an_explicit_mail_ref_over_the_number(self):
        v = vorgang(nr=109, mail_ref="/a/999")
        ziel = tb.mail_ziel(v, "https://mail.example", {"109": "/a/"})
        assert ziel == "https://mail.example/a/999"

    def test_should_reject_an_absolute_mail_ref_without_falling_back(self):
        """Ein vergifteter Eintrag wird nicht stillschweigend durch die Nummer geheilt."""
        v = vorgang(nr=109, mail_ref="https://fremd.example/x")
        assert tb.mail_ziel(v, "https://mail.example", {"109": "/a/"}) is None

    def test_should_treat_a_missing_anchor_file_as_no_anchors(self, tmp_path):
        fehlt = Path("/nicht/vorhanden/anker.json")
        assert tb.aufloesbare_nummern(fehlt, tmp_path / "auch-nicht.json") == {}

    def test_should_treat_a_broken_anchor_file_as_no_anchors(self, tmp_path):
        kaputt = tmp_path / "anker.json"
        kaputt.write_text("{kein json", encoding="utf-8")
        assert tb.aufloesbare_nummern(kaputt, tmp_path / "leer.json") == {}

    def test_should_read_the_numbers_from_the_anchor_file(self, tmp_path):
        gut = tmp_path / "anker.json"
        gut.write_text('{"109": {"ordner": "INBOX"}, "110": {}}', encoding="utf-8")
        assert tb.aufloesbare_nummern(gut, tmp_path / "leer.json") == {
            "109": "/a/",
            "110": "/a/",
        }

    def test_should_resolve_a_graph_number_via_the_registry(self, tmp_path):
        """Der gemeldete Fehler: IIL-Vorgaenge blieben unverlinkt (2026-08-11).

        `anker.py --setze` laeuft ueber IMAP und erreicht nur die HNU-Konten.
        Wer nur die Ankerdatei prueft, laesst jeden IIL-Vorgang ohne Link —
        obwohl der Mail-Dienst ihn ueber die Kurz-ID-Registry aufloesen kann.
        """
        reg = tmp_path / "links.json"
        reg.write_text('{"107": {"graph_id": "AAA"}}', encoding="utf-8")
        assert tb.aufloesbare_nummern(tmp_path / "leer.json", reg) == {"107": "/r/"}

    def test_should_prefer_the_imap_anchor_over_the_registry(self, tmp_path):
        """Der Anker traegt Ordner+UID und zieht bei Ordnerwechsel nach."""
        ank = tmp_path / "anker.json"
        ank.write_text('{"107": {"ordner": "INBOX"}}', encoding="utf-8")
        reg = tmp_path / "links.json"
        reg.write_text('{"107": {"graph_id": "AAA"}}', encoding="utf-8")
        assert tb.aufloesbare_nummern(ank, reg) == {"107": "/a/"}

    def test_should_render_the_graph_prefix_in_the_row(self):
        """Graph-Praefix, gemessen an einer Zeile ohne Vorgangsansicht."""
        markup = tb.zeile(
            vorgang(nr=107, thread_key=""),
            STICHTAG,
            "",
            "https://mail.example",
            {"107": "/r/"},
        )
        assert "href='https://mail.example/r/107'" in markup

    def test_should_link_the_mail_from_the_overview_row(self):
        """Der Weg zur Mail kostet keinen Zwischenklick — dort, wo es ihn noch gibt.

        Seit 2026-08-20 traegt eine Zeile MIT Vorgangsansicht kein Briefsymbol mehr
        (es zeigte auf die aelteste Mail); geprueft wird die Form also an einer
        Zeile ohne thread_key.
        """
        markup = tb.zeile(
            vorgang(nr=109, thread_key=""),
            STICHTAG,
            "",
            "https://mail.example",
            {"109": "/a/"},
        )
        assert "href='https://mail.example/a/109'" in markup

    def test_should_not_link_an_unanchored_row(self):
        markup = tb.zeile(
            vorgang(nr=107, thread_key="x"),
            STICHTAG,
            "",
            "https://mail.example",
            {"109": "/a/"},
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
        """Ohne thread_key bleibt das Briefsymbol — dann muss es sauber oeffnen."""
        markup = tb.zeile(
            vorgang(nr=109, thread_key=""),
            STICHTAG,
            "",
            "https://mail.example",
            {"109": "/a/"},
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
        seite = tb.baue({"vorgaenge": [vorgang()]}, STICHTAG, anker={})
        assert "mail.iil.pet'" not in seite.split("<script>")[1]
        assert "lastIndexOf(MB" not in seite

    def test_should_still_intercept_vorgang_links(self):
        seite = tb.baue({"vorgaenge": [vorgang()]}, STICHTAG, anker={})
        assert "h.indexOf('/t/')>=0" in seite

    def test_should_keep_the_overlay_on_the_index_only(self):
        """Die Detailseite traegt kein Overlay — sie hat keinen `/t/`-Link."""
        assert tb.baue({"vorgaenge": [vorgang()]}, STICHTAG).count("id=ovl-frame") == 1
        assert "id=ovl-frame" not in tb.detail(vorgang(thread_key="x"))


class TestVerlaufZerlegung:
    """Der Verlauf ist nicht mehr ein Prosa-Block, sondern Karten mit Bahnen.

    Die Faelle hier sind KEINE erfundenen Beispiele: alle vier Textformen standen
    so im Ledger und haben je eine Fassung des Renderers widerlegt.
    """

    ECHTER_EINTRAG = (
        "2026-08-21 (/mailcheck): DB bis 20.08. (12.498 Nachr./145 Ordner/3 Konten), "
        "Restfenster 21.08. live nachgezogen (HNU/AD IMAP + IIL Graph) — leer, "
        "juengste Nachricht im Bestand ist vhb 20.08. 16:41. "
        "Klimm 20.08. 14:48 (INBOX #164024): 'Kurze Bestaetigung.' — Teil damit "
        "abgeschlossen. Offen bleibt nur noch der Termin nach der Sommerpause."
    )

    def test_should_read_date_and_source_out_of_the_entry_head(self):
        t = tb.zerlege_eintrag(self.ECHTER_EINTRAG)
        assert t["datum"] == "2026-08-21"
        assert t["quelle"] == "/mailcheck"

    def test_should_read_an_event_marker_that_follows_a_time(self):
        t = tb.zerlege_eintrag("2026-08-20 13:41 GESENDET (Owner): Text.")
        assert (t["datum"], t["zeit"], t["ereignis"], t["quelle"]) == (
            "2026-08-20",
            "13:41",
            "GESENDET",
            "Owner",
        )

    def test_should_move_the_coverage_boilerplate_out_of_the_reading_line(self):
        """Rund die Haelfte des Eintrags ist Erhebungsprotokoll — es darf nicht im Inhalt stehen."""
        t = tb.zerlege_eintrag(self.ECHTER_EINTRAG)
        assert "Restfenster" in t["deckung"]
        assert "Restfenster" not in t["inhalt"]
        assert len(t["deckung"]) > len(t["inhalt"]) / 2

    def test_should_pull_a_self_marked_open_item_into_its_own_lane(self):
        t = tb.zerlege_eintrag(self.ECHTER_EINTRAG)
        assert t["action"].startswith("Offen bleibt")
        assert "Offen bleibt" not in t["inhalt"]

    def test_should_not_invent_an_analysis_lane_for_unmarked_prose(self):
        """Der Falsifikationstest: "… damit abgeschlossen" ist inhaltlich eine
        Analyse — aber der Satz sagt es nicht, also bleibt er Inhalt. Raten waere
        schlimmer als nicht trennen: es behauptet eine Gliederung des Autors."""
        t = tb.zerlege_eintrag(self.ECHTER_EINTRAG)
        assert t["analyse"] == ""
        assert "abgeschlossen" in t["inhalt"]

    def test_should_keep_a_date_from_splitting_the_sentence(self):
        """ "20.08. Klimm" darf keine Satzgrenze sein — sonst zerfaellt jeder Eintrag."""
        t = tb.zerlege_eintrag("2026-08-21: Eingang 20.08. Klimm meldet sich.")
        assert t["inhalt"] == "Eingang 20.08. Klimm meldet sich."

    def test_should_read_the_head_behind_a_leading_marker(self):
        """Reale Form aus dem Ledger: "NEU 2026-08-20 (/mailcheck): …".

        Ohne diesen Zweig faellt der ganze Kopf durch und das Datum landet als
        Fliesstext im Inhalt — auf der gerenderten Seite von Vorgang 142 war
        genau der aelteste Eintrag als einziger ohne Kopfzeile zu sehen.
        """
        t = tb.zerlege_eintrag("NEU 2026-08-20 (/mailcheck): Klimm meldet sich.")
        assert (t["datum"], t["quelle"]) == ("2026-08-20", "/mailcheck")
        assert t["inhalt"] == "Klimm meldet sich."

    def test_should_recognise_an_open_item_behind_a_qualifier(self):
        """ "Unveraendert offen: …" ist dieselbe Ansage wie "Offen bleibt …".

        Der reine Wortanfangs-Vergleich der ersten Fassung sah sie nicht, und der
        Satz blieb im Fliesstext eines 1.300-Zeichen-Eintrags stehen.
        """
        t = tb.zerlege_eintrag(
            "2026-08-20: Drift korrigiert. Unveraendert offen: Ist-Aufwand."
        )
        assert t["action"] == "Unveraendert offen: Ist-Aufwand."
        assert "Unveraendert" not in t["inhalt"]

    def test_should_not_mistake_offenbar_for_an_open_item(self):
        """Die Gegenprobe zur Lockerung: "offenbar" ist kein offener Punkt."""
        t = tb.zerlege_eintrag("2026-08-20: Der Vorgang ist offenbar abgeschlossen.")
        assert t["action"] == ""
        assert "offenbar" in t["inhalt"]

    def test_should_read_the_span_chronologically_in_both_orders(self):
        """Die Spanne beschreibt einen Zeitraum — '12. bis 10.' ist keiner."""
        stille = " | ".join(
            f"2026-08-1{i} (/mailcheck): kein neuer Eingang im Strang."
            for i in range(3)
        )
        for umgedreht in (False, True):
            seite = tb.detail(vorgang(notiz=stille), alt_zuerst=umgedreht)
            assert "2026-08-10 bis 2026-08-12" in seite

    def test_should_show_an_entry_that_is_only_coverage_as_a_check_that_happened(self):
        nur_deckung = (
            "2026-08-19 (/mailcheck): kein neuer Eingang im Strang (DB bis 19.08.)."
        )
        assert "Nur Erhebung" in tb.verlauf([nur_deckung], "hnu")


class TestEntwurfLink:
    """Der Link zeigt auf einen Entwurf, den es noch gibt — oder auf nichts."""

    def test_should_link_a_waiting_draft(self):
        v = vorgang(
            konto="hnu", notiz="2026-08-21 ENTWURF (Entwuerfe #23611) liegt bereit"
        )
        assert tb.entwurf_link(v).endswith("/m/hnu/entwuerfe/23611")

    def test_should_stay_silent_when_the_same_entry_says_it_was_sent(self):
        v = vorgang(
            konto="hnu",
            notiz="2026-08-21 GESENDET: Entwurf aus Entwuerfe #23611 wurde versendet.",
        )
        assert tb.entwurf_link(v) == "", "ein toter Link ist schlechter als keiner"


class TestArchivLeser:
    """Archivieren darf aus Sicht eines Lesezeichens kein Loeschen sein."""

    def test_should_read_the_archive_file(self, tmp_path):
        ziel = tmp_path / "erledigt.json"
        ziel.write_text('{"vorgaenge": [{"nr": 9}]}', encoding="utf-8")
        assert tb.archivierte_vorgaenge(ziel) == [{"nr": 9}]

    def test_should_survive_a_missing_archive(self, tmp_path):
        assert tb.archivierte_vorgaenge(tmp_path / "gibt-es-nicht.json") == []


class TestVerlaufVerweise:
    """Verlinkt wird nur, wo der Zielordner feststeht — sonst nur ausgezeichnet."""

    def test_should_link_a_uid_whose_folder_stands_next_to_it(self):
        html = tb.verweise(
            "Klimm (INBOX #164024) meldet", "hnu", "https://mail.example"
        )
        assert "https://mail.example/m/hnu/inbox/164024" in html

    def test_should_reach_the_folder_through_quotes_and_a_bracket(self):
        """Reale Form: "Beleg im Ordner 'Gesendete Objekte' (#34349)"."""
        roh = "Beleg im Ordner &#x27;Gesendete Objekte&#x27; (#34349)."
        html = tb.verweise(roh, "hnu", "https://mail.example")
        assert "https://mail.example/m/hnu/gesendete-objekte/34349" in html

    def test_should_not_claim_a_folder_it_did_not_verify(self):
        """Ein Satz nennt zwei Entwuerfe und EINEN Ordner — die zweite Nummer
        liegt dort gerade nicht.

        Bis 2026-08-21 blieben beide Nummern unverlinkt, weil `/m/<konto>/<uid>`
        nur gegen INBOX aufloeste und ein Link ins Leere gezeigt haette. Seit
        der Dienst eine UID ohne Ordnerangabe selbst sucht
        (`mail_link_server._ordner_ohne_angabe`), sind sie klickbar — aber
        ueber die **unqualifizierte** Route. Die Zusicherung ist damit nicht
        mehr "kein Link", sondern die schaerfere: kein Link behauptet einen
        Ordner, der nicht danebensteht.
        """
        roh = "Vorfassung UID 23588 in Geloeschte Objekte verschoben, gueltig ist UID 23589."
        html = tb.verweise(roh, "hnu", "https://mail.example")
        assert "https://mail.example/m/hnu/23589" in html
        assert "geloeschte-objekte/23589" not in html

    def test_should_link_a_bare_number_over_the_unqualified_route(self):
        """Der Grund fuer die ganze Umstellung: eine Nummer, die niemand
        verlinken konnte, zwang die Prosa daneben dazu, ihren Inhalt zu
        erklaeren. Klickbarkeit ist hier die Voraussetzung fuers Kuerzen."""
        html = tb.verweise(
            "Der Entwurf (UID 23597) liegt im Papierkorb.", "hnu", "https://m.x"
        )
        assert "https://m.x/m/hnu/23597" in html
        assert "Ordner wird beim Oeffnen gesucht" in html

    def test_should_link_a_github_reference_instead_of_calling_it_unresolvable(self):
        html = tb.verweise(
            "korrigiert in meiki-lra/meiki-hub#146.", "hnu", "https://mail.example"
        )
        assert "https://github.com/meiki-lra/meiki-hub/issues/146" in html
        assert "ref-roh" not in html

    def test_should_fall_back_to_the_default_org_without_an_owner(self):
        html = tb.verweise("siehe platform#2183", "hnu", "https://mail.example")
        assert "https://github.com/achimdehnert/platform/issues/2183" in html

    def test_should_link_nothing_without_an_account(self):
        """Ohne Konto ginge `/m/<uid>` auf das Default-Konto des Dienstes — eine
        fremde Mailbox, in der dieselbe Nummer eine andere Nachricht ist."""
        roh = "Klimm (INBOX #164024) meldet"
        assert tb.verweise(roh, "") == roh

    def test_should_mark_an_attachment_without_linking_it(self):
        html = tb.verweise("Anhang Bericht_2026-08-20.docx dabei", "hnu")
        assert "class='datei'" in html
        assert "<a" not in html
